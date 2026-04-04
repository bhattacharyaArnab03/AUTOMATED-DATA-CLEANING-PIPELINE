import numpy as np
import pandas as pd


class StrategySelector:
    def evaluate_numeric(self, s, candidate):
        s = pd.to_numeric(s, errors="coerce").astype(float).dropna()
        if len(s) == 0:
            return float("inf")

        var_before = s.var()
        if pd.isna(var_before) or var_before == 0:
            return float("inf")

        candidate = pd.to_numeric(candidate, errors="coerce").astype(float).dropna()
        if len(candidate) == 0:
            return float("inf")

        var_after = candidate.var()
        if pd.isna(var_after):
            return float("inf")

        return float(var_after / var_before)

    def select_best_numeric(self, series):
        s = pd.to_numeric(series, errors="coerce").astype(float)

        strategies = {
            "mean": s.fillna(s.mean()),
            "median": s.fillna(s.median()),
        }

        best_score = -np.inf
        best_strategy = "median"
        best_series = strategies["median"]

        for name, candidate in strategies.items():
            if candidate.isna().all():
                continue
            score = self.evaluate_numeric(s, candidate)
            if score > best_score:
                best_score = score
                best_strategy = name
                best_series = candidate

        return best_strategy, best_series

    def select_scaler(self, stats):
        n_unique = stats.get("n_unique", 0)

        if n_unique <= 2:
            return None

        return "minmax"