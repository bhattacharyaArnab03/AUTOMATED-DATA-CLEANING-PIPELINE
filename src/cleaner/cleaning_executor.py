import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler, MinMaxScaler

from cleaner.strategy_selector import StrategySelector
from cleaner.validator import Validator
from cleaner.domain_rules import DomainRules


class CleaningExecutor:

    def __init__(self, config_path=None):
        self.selector = StrategySelector()
        self.validator = Validator()
        self.rules = DomainRules(config_path)

    def _is_binary(self, s):
        s = pd.to_numeric(s, errors="coerce").dropna()
        return set(s.unique()).issubset({0, 1})

    def _encode(self, s):
        return LabelEncoder().fit_transform(s.astype(str))

    def _scale(self, s, method):
        scaler = StandardScaler() if method == "standard" else MinMaxScaler()
        return scaler.fit_transform(s.to_frame()).ravel()

    def clean(self, df, scale_columns=None):

        df = df.copy()
        scale_columns = set(scale_columns or [])
        audit = {"columns": {}}

        for col in df.columns:
            s = df[col]

            # Categorical
            if s.dtype == "object":
                s = s.fillna(s.mode()[0])
                df[col] = self._encode(s)
                audit["columns"][col] = {"action": "encoded"}
                continue

            # Numeric
            s = pd.to_numeric(s, errors="coerce")

            # 🔥 Binary fix
            if self._is_binary(s):
                s = s.fillna(s.mode()[0])
                df[col] = s
                audit["columns"][col] = {"action": "binary_preserved"}
                continue

            # Impute
            strategy, s = self.selector.select_best_numeric(s)
            s, _, _ = self.validator.validate_numeric(s)

            s = s.fillna(s.median() if strategy == "median" else s.mean())

            # User scaling
            if col in scale_columns:
                scaler = self.selector.select_scaler({
                    "skew": s.skew(),
                    "n_unique": s.nunique()
                })
                if scaler:
                    s = self._scale(s, scaler)

            df[col] = s
            audit["columns"][col] = {"action": strategy}

        return df, audit