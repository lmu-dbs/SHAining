import json
import multiprocessing
import os
import pandas as pd
import subprocess
import random
import numpy as np

from datetime import datetime as dt
from datetime import timedelta
from functools import partial, partialmethod
from pathlib import Path
from pm4py import read_xes, convert_to_bpmn, read_bpmn, convert_to_petri_net, check_soundness
from pm4py import discover_petri_net_inductive, discover_petri_net_ilp, discover_petri_net_heuristics
from pm4py import fitness_alignments, fitness_token_based_replay
from pm4py import precision_alignments, precision_token_based_replay
from pm4py.algo.evaluation.generalization import algorithm as generalization_evaluator
from pm4py.algo.evaluation.simplicity import algorithm as simplicity_evaluator
from pm4py.objects.bpmn.obj import BPMN
from pm4py.objects.log.importer.xes import importer as xes_importer
from shaining.utils.io_helpers import dump_features_json
from tqdm import tqdm
from utils.param_keys import INPUT_PATH, OUTPUT_PATH
from utils.param_keys.benchmark import MINERS

RANDOM_SEED = 10
random.seed(RANDOM_SEED)

class BenchmarkTest:
    def __init__(self, params=None, event_logs=None):
        start = dt.now()
        print("=========================== BenchmarkTest =============================")

        print(f"INFO: Running with {params}")

        if len(event_logs) == 0:
            log_path = params[INPUT_PATH]
            if log_path.endswith(".xes"):
                event_logs = [""]
            else:
                try:
                    event_logs = sorted([filename for filename in os.listdir(log_path) if filename.endswith(".xes")])
                except FileNotFoundError:
                    print(f"        FAILED: Cannot find {params[INPUT_PATH]}" )
                    return
        if params != None:
            self.params = params


        if True:
             num_cores = multiprocessing.cpu_count() if len(
                        event_logs) >= multiprocessing.cpu_count() else len(event_logs)
             #self.benchmark_wrapper(event_logs[0], miners=self.params[MINERS])# TESTING
             with multiprocessing.Pool(num_cores) as p:
                 print(f"INFO: Benchmark starting at {start.strftime('%H:%M:%S')} using {num_cores} cores for {len(event_logs)} files...")
                 random.seed(RANDOM_SEED)
                 p.map(partial(self.benchmark_wrapper, miners = self.params[MINERS]), event_logs)

             # Aggregates metafeatures in saved Jsons into dataframe
             self.root_path = self.params[INPUT_PATH]
             path_to_json = f"output/benchmark/{str(self.root_path).split('/',1)[1]}"
             if path_to_json.endswith(".xes"):
                path_to_json = path_to_json.rsplit("/",1)[0]
             df = pd.DataFrame()
             # Iterate over the files in the directory
             for filename in os.listdir(path_to_json):
                 if filename.endswith('.json'):
                     i_path = os.path.join(path_to_json, filename)
                     with open(i_path) as f:
                         data = json.load(f)
                         temp_df = pd.DataFrame([data])
                         df = pd.concat([df, temp_df], ignore_index = True)
             benchmark_results = df
             #print(benchmark_results)

        self.filename = os.path.split(self.root_path)[-1].replace(".xes","") + '_benchmark.csv'
        self.filepath = os.path.join("output", "benchmark", self.filename)
        os.makedirs(os.path.split(self.filepath)[0], exist_ok=True)
        benchmark_results.to_csv(self.filepath, index=False)

        self.results = benchmark_results
        print(f"SUCCESS: BenchmarkTest took {dt.now()-start} sec for {len(params[MINERS])} miners"+\
              f" and {len(benchmark_results)} event-logs. Saved benchmark to {self.filepath}.")
        print("========================= ~ BenchmarkTest =============================")

    def benchmark_wrapper(self, event_log="test", miners=['inductive'], log_counter=0):
        random.seed(RANDOM_SEED)
        dump_path = os.path.join(self.params[OUTPUT_PATH],
                                 os.path.split(self.params[INPUT_PATH])[-1])
        dump_path= os.path.join(self.params[OUTPUT_PATH],
                                os.path.join(*os.path.normpath(self.params[INPUT_PATH]).split(os.path.sep)[1:]))
        if dump_path.endswith(".xes"):
            event_log = os.path.split(dump_path)[-1]
            dump_path = os.path.split(dump_path)[0]
        
        if len(miners) == 1:
            dump_path = dump_path + f"_{miners[0]}"
        benchmark_results = pd.DataFrame()
        # TODO: Use iteratevely generated name for log name in dataframe for passed unnamed logs instead of whole log. E.g. gen_el_1, gen_el_2,...
        if isinstance(event_log, str):
            log_name = event_log.replace(".xes", "")
            results = {'log': log_name}
        else:
            log_name = "gen_el_"+str(log_counter)
            results = {"log": event_log}
            #results = {"log": log_name}

        for miner in miners:
            miner_cols = [f"fitness_{miner}", f"precision_{miner}", f"fscore_{miner}", f"size_{miner}", f"cfc_{miner}", f"pnsize_{miner}"]# f"generalization_{miner}",f"simplicity_{miner}"]
            start_miner = dt.now()
            benchmark_results =  self.benchmark_discovery(results['log'],  miner, self.params)
            results[f"fitness_{miner}"] = benchmark_results[0]
            results[f"precision_{miner}"] = benchmark_results[1]
            results[f"fscore_{miner}"] = 2*(benchmark_results[0]*benchmark_results[1]/(benchmark_results[0]+ benchmark_results[1]))
            results[f"size_{miner}"]=benchmark_results[2]
            results[f"pnsize_{miner}"]=benchmark_results[4]
            results[f"cfc_{miner}"]=benchmark_results[3]
            results[f"exectime_{miner}"]=benchmark_results[5]
            results[f"benchtime_{miner}"]=benchmark_results[6]

        print(f"    SUCCESS: {len(miners)} miners for {results['log']} took {dt.now()-start_miner} sec.")
        dump_features_json(results, dump_path, log_name, content_type="benchmark")
        return

    def split_miner_wrapper(self, log_path="data/real_event_logs/BPI_Challenges/BPI_Challenge_2012.xes", version=1.0):
        random.seed(RANDOM_SEED)
        os.environ["DISPLAY"] = ":99" # For running on github CI
        filename = os.path.split(log_path)[-1].rsplit(".",1)[0]
        bpmn_path = os.path.join("output", "bpmns_split", filename)
        os.makedirs(os.path.split(bpmn_path)[0], exist_ok=True)
        if version==2.0:
            command = [
                    "java",
                    "-cp",
                    f"{os.getcwd()}/miners/split-miner-2.0/sm2.jar:{os.getcwd()}/miners/split-miner-2.0/lib/*",
                    "au.edu.unimelb.services.ServiceProvider",
                    "SM2",
                    f"{os.getcwd()}/{log_path}",
                    f"{os.getcwd()}/{bpmn_path}",
                    "0.05"
                    ]
        elif version==1.0:
            command = [
                "java",
                "-cp",
                f"{os.getcwd()}/miners/splitminer/splitminer.jar:{os.getcwd()}/miners/splitminer/lib/*",
                "au.edu.unimelb.services.ServiceProvider",
                "SMD",
                "0.1",
                "0.4",
                "false",
                f"{os.getcwd()}/{log_path}",
                f"{os.getcwd()}/{bpmn_path}",
            ]

        print("        COMMAND", " ".join(command))
        output = subprocess.run(
            command,
            capture_output=True,
            text=True,
        )
        try:
            if "\nERROR:" in output.stdout:
                print("FAILED: SplitMiner v{version} could not create BPMN for", log_path)
                print("     SplitMiner:", output.stderr)
                return None
            return read_bpmn(bpmn_path+'.bpmn')
        except ValueError:
            print(output.stdout)

    def benchmark_discovery(self, log, miner, params=None):
        """
        Runs discovery algorithms on a specific log and returns their performance.

        :param str/EventLog log: log from pipeline step before or string to .xes file.
        :param str miner: Specifies process discovery miner to be run on log.
        :param Dict params: Params from config file

        """
        #print("Running benchmark_discovery with", self, log, miner, params)
        random.seed(RANDOM_SEED)
        NOISE_THRESHOLD = 0.2
        miner_params=''
        tqdm.__init__ = partialmethod(tqdm.__init__, disable=True)
        start_bench = dt.now()
        start_bench = start_bench-timedelta(days=0)

        if type(log) is str:
            if params[INPUT_PATH].endswith('.xes'):
                log_path = params[INPUT_PATH]
            else:
                log_path = os.path.join(params[INPUT_PATH], log+".xes")
            success_msg = f"        SUCCESS: Benchmarking event-log {log} with {miner} took "# {dt.now()-start_bench} sec."
            try:
                log = xes_importer.apply(f"{log_path}", parameters={"show_progress_bar": False})
            except FileNotFoundError:
                print(f"        FAILED: Cannot find {log_path}" )
        else:
            log=log
            success_msg = f"        SUCCESS: Benchmarking one event-log with {miner} took "# {dt.now()-start_bench} sec."
        if miner == 'sm1':
            bpmn_graph = self.split_miner_wrapper(log_path, version=1.0)
            if bpmn_graph is None:
                return None
            '''TESTING
            from pm4py.visualization.bpmn.visualizer import apply as get_bpmn_fig
            from pm4py.visualization.bpmn.visualizer import matplotlib_view as view_bpmn_fig
            bpmn_fig = get_bpmn_fig(bpmn_graph)
            view_bpmn_fig(bpmn_fig)
            '''
            net, im, fm = convert_to_petri_net(bpmn_graph)
        elif miner == 'sm2':
            bpmn_graph = self.split_miner_wrapper(log_path, version=2.0)
            if bpmn_graph is None:
                return None
            net, im, fm = convert_to_petri_net(bpmn_graph)
        else:
            if miner == 'imf':
                miner = 'inductive'
                miner_params = f', noise_threshold={NOISE_THRESHOLD}'
            net, im, fm = eval(f"discover_petri_net_{miner}(log {miner_params})")
            bpmn_graph = convert_to_bpmn(net, im, fm)
        now = dt.now()
        time_m = round((now-start_bench).total_seconds(),2)
        try:
            fitness = fitness_alignments(log, net, im, fm)['log_fitness']
            precision = precision_alignments(log, net, im, fm)
        except Exception: 
            print(f"ERROR: Alignment for {log_path}")
            fitness = -1
            precision = -1
        pn_size = len(net._PetriNet__places)
        size = len(bpmn_graph._BPMN__nodes)
        cfc = sum([isinstance(node, BPMN.ExclusiveGateway) for node in bpmn_graph._BPMN__nodes])
        #generalization = generalization_evaluator.apply(log, net, im, fm)
        #simplicity = simplicity_evaluator.apply(net)
        now = dt.now()
        metric_time = round((now-start_bench).total_seconds(),2)
        print(success_msg + f"{now-start_bench} sec. Miner time {time_m} sec. Complete computation time including metrics {metric_time} sec.")
        return fitness, precision, size, cfc, pn_size, time_m, metric_time  #, generalization, simplicity