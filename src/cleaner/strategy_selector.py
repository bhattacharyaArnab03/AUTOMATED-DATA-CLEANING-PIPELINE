import numpy as np
import pandas as pd


class StrategySelector:

    def evaluate_numeric(self, s, candidate):
        # 🔥 Ensure numeric + float (CRITICAL FIX)
        s = pd.to_numeric(s, errors="coerce").astype(float)
        s = s.dropna()

        if len(s) == 0:
            return float("inf")

        var_before = s.var()

        # 🔥 Handle invalid variance
        if pd.isna(var_before) or var_before == 0:
            return float("inf")

        # 🔥 Candidate must also be numeric float
        s_candidate = pd.to_numeric(candidate, errors="coerce").astype(float)
        s_candidate = s_candidate.dropna()

        if len(s_candidate) == 0:
            return float("inf")

        var_after = s_candidate.var()

        if pd.isna(var_after):
            return float("inf")

        # Lower variance ratio = better
        score = var_after / var_before

        return float(score)

    def select_best_numeric(self, series):
        # 🔥 CRITICAL FIX: force float dtype
        s = pd.to_numeric(series, errors="coerce").astype(float)

        # 🔥 Safe strategy generation
        strategies = {
            "mean": s.fillna(s.mean()),
            "median": s.fillna(s.median()),
        }

        if not s.mode().empty:
            strategies["mode"] = s.fillna(s.mode()[0])

        best_score = -np.inf
        best_strategy = "median"
        best_series = s.fillna(s.median())

        for name, candidate in strategies.items():

            # Skip useless candidates
            if candidate.isna().all():
                continue

            score = self.evaluate_numeric(s, candidate)

            if score > best_score:
                best_score = score
                best_strategy = name
                best_series = candidate

        return best_strategy, best_series