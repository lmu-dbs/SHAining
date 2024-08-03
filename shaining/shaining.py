import numpy as np
import os
import pandas as pd
import shap

from datetime import datetime as dt
from shaining.utils.io_helpers import get_keys_abbreviation
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from utils.param_keys import OUTPUT_PATH
from utils.param_keys.shain import METRICS_PATH, FEATURES_PATH, EVALUATION_METRICS, EVENTLOG_FEATURES
from utils.param_keys.shain import METHODS, MODEL, AGGREGATION
from xgboost import XGBRegressor

class ShainingTask:
    def __init__(self, params=None):
        start = dt.now()
        print("=========================== ShainingTask =============================")

        print(f"INFO: Running with {params}")
        dfs = []
        methods = params[METHODS]
        model_name = params[MODEL]#"XGBRegressor", "LinearRegression"
        agg = params[AGGREGATION]#"all"
        feat_path = params[FEATURES_PATH]
        bench_path = params[METRICS_PATH]
        X_cols = params[EVENTLOG_FEATURES]
        y_cols = params[EVALUATION_METRICS]
        dump_path= os.path.join(params[OUTPUT_PATH],"shaining",
                                os.path.join(*os.path.normpath(
                                    os.path.commonprefix([params[FEATURES_PATH], params[METRICS_PATH]]))
                                             .split(os.path.sep)[1:]))+"shaining_"+model_name+".csv"
        ft = pd.read_csv(feat_path).sort_values("log")
        bench = pd.read_csv(bench_path).sort_values("log")
        bench = bench.dropna(axis=0)

        #TODO: Fix this in GEDI, redundancy between feature extraction and ED generation
        if bench['log'].str.startswith("genEL").all():
            bench['log'] = bench.apply(lambda x: "_".join(x['log'].split("genEL")[1].split("_", 2)[:2]), axis=1)

        ft_ben = pd.merge(ft, bench, on=['log'], how='inner').reset_index(drop=True)
        print(ft.shape, bench.shape, ft_ben.shape)
        print(X_cols)
        print(y_cols)

        imp_mean = SimpleImputer(missing_values=np.nan, strategy='mean')
        imp_mean.fit(ft_ben._get_numeric_data())
        imp_ft_ben = imp_mean.transform(ft_ben._get_numeric_data())

        X_fb = ft_ben[X_cols]
        for y_col in y_cols:
            per_miner = [metric for metric in ft_ben.columns if metric.startswith(y_col)]
            if agg:
                ft_ben[y_col+"_"+agg] = ft_ben.apply(lambda x: [x['fitness_imf'], x['fitness_ilp'], x['fitness_heuristics']] , axis=1)
                ft_ben[y_col+"_"+agg] = ft_ben.apply(lambda x: self.aggregation_helper(x, per_miner) , axis=1)
                ft_ben = ft_ben.explode(y_col+"_"+agg).reset_index(drop=True)
                per_miner = [y_col+"_"+agg]

            for metric_per_miner in per_miner:
                method='_'.join(metric_per_miner.split("_")[1:])
                if method in methods:
                    short_ft_names = get_keys_abbreviation(X_cols).split("_")

                    y_fb = ft_ben[metric_per_miner].values
                    col_mean = np.nanmean(y_fb, axis=0)
                    inds = np.where(np.isnan(y_fb))
                    y_fb[inds] = col_mean

                    shap_values = self.shapley_wrapper(X_fb, y_fb, model = model_name)
                    explanations = pd.DataFrame(data=shap_values, columns=short_ft_names)
                    explanations = explanations.set_index(ft_ben['log']).reset_index()

                    explanations['metric']=y_col
                    #TODO: If methods empty
                    explanations['method']= method
                    dfs.append(explanations)
        shaining_result = pd.concat(dfs, ignore_index= True)
        shaining_result = shaining_result.sort_values(["log", "method", "metric"]).reset_index(drop=True)

        os.makedirs(os.path.split(dump_path)[0], exist_ok=True)
        shaining_result.to_csv(dump_path, index=False)

        print(f"SUCCESS: ShainBenchmark took {dt.now()-start} sec for {len(y_cols)} metrics {y_cols}, "+\
              f"{len(shaining_result['method'].unique())} miners {shaining_result['method'].unique()}"+\
              f" and {len(shaining_result)} explanations. Saved shaining results to {dump_path}.")

        print("========================= ~ ShainingTask =============================")

    def shapley_wrapper(self, X, y, model = "LinearRegression"):
        imp_mean = SimpleImputer(missing_values=np.nan, strategy='mean')
        imp_mean.fit(X)
        imp_X = imp_mean.transform(X)

        model = eval(model+"()")
        model.fit(imp_X, y)

        """
        print("Model coefficients:\n")
        for i in range(X.shape[1]):
            print(X.columns[i], "=", model.coef_[i].round(4))
        """

        background = shap.maskers.Independent(X, max_samples=1000)
        explainer = shap.Explainer(model.predict, background)
        shap_values = explainer(X)

        #print(shap_values.shape)
        sample_ind = 1
        #shap.plots.waterfall(shap_values[sample_ind], max_display=14)
        return np.round(shap_values.values, 10)
