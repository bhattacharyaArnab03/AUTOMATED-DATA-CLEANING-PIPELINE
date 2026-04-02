import pandas as pd


class StrategySelector:

    def select_best_numeric(self, s):
        s = pd.to_numeric(s, errors="coerce")
        return "median", s.fillna(s.median())

    def select_scaler(self, stats):
        if stats["n_unique"] <= 2:
            return None
        return "standard" if abs(stats["skew"]) < 1 else "minmax"