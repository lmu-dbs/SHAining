import config
import pandas as pd
import warnings

from datetime import datetime as dt
#from shaining.features import EventLogFeatures
from shaining.benchmark import BenchmarkTest
from shaining.shaining import ShainingTask
#from shaining.plotter import BenchmarkPlotter, FeaturesPlotter, AugmentationPlotter, GenerationPlotter
from utils.default_argparse import ArgParser
from utils.param_keys import *
from utils.param_keys.run_options import *
warnings.filterwarnings("ignore")

def run(kwargs:dict, model_paramas_list: list, filename_list:list):
    """
    This function chooses the running option for the program.
    @param kwargs: dict
        contains the running parameters and the event-log file information
    @param model_params_list: list
        contains a list of model parameters, which are used to analyse this different models.
    @param filename_list: list
        contains the list of the filenames to load multiple event-logs
    @return:
    """
    params = kwargs[PARAMS]
    run_option = 'baseline'
    gen = pd.DataFrame(columns=['log'])

    if run_option == BASELINE:
        for model_params in model_params_list:
            if model_params.get(PIPELINE_STEP) == 'benchmark_test':
                benchmark = BenchmarkTest(model_params, event_logs=gen['log'])
                # BenchmarkPlotter(benchmark.features, output_path="output/plots")
            elif model_params.get(PIPELINE_STEP) == 'feature_extraction':
                ft = EventLogFeatures(**kwargs, logs=gen['log'], ft_params=model_params)
                FeaturesPlotter(ft.feat, model_params)
            elif model_params.get(PIPELINE_STEP) == "evaluation_plotter":
                GenerationPlotter(gen, model_params, output_path=model_params['output_path'], input_path=model_params['input_path'])
            elif model_params.get(PIPELINE_STEP) == 'shaining_task':
                ShainingTask(params = model_params)

    elif run_option == COMPARE:
        if params[N_COMPONENTS] != 2:
            raise ValueError(f'The parameter `{N_COMPONENTS}` has to be 2, but it\'s {params[N_COMPONENTS]}.')
        ft = EventLogFeatures(**kwargs)
        FeatureAnalyser(ft, params).compare(model_params_list)
    else:
        raise InvalidRunningOptionError(f'The run_option: `{run_option}` in the (json) configuration '
                                        f'does not exists or it is not a loading option.\n')


if __name__=='__main__':
    start_tag = dt.now()
    print(f'INFO: SHAMPU starting {start_tag}')

    args = ArgParser().parse('SHAMPU main')

    model_params_list = config.get_model_params_list(args.alg_params_json)
    run({'params':""}, model_params_list, [])

    print(f'SUCCESS: SHAMPU took {dt.now()-start_tag} sec.')
