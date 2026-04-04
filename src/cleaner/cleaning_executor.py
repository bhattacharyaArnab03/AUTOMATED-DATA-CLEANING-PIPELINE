import pandas as pd
from sklearn.preprocessing import LabelEncoder, MinMaxScaler

from cleaner.strategy_selector import StrategySelector
from cleaner.validator import Validator
from cleaner.domain_rules import DomainRules
from cleaner.profiler import DataProfiler
from cleaner.decision_engine import DecisionEngine


class CleaningExecutor:

    def __init__(self, config_path=None):
        self.selector = StrategySelector()
        self.validator = Validator()
        self.domain_rules = DomainRules(config_path) if config_path else None
        self.profiler = DataProfiler()
        self.decision_engine = DecisionEngine()

    # -------------------------
    # HELPERS
    # -------------------------
    def _missing_tokens(self):
        if self.domain_rules:
            return self.domain_rules.get_missing_tokens()
        return {"", "na", "null", "none", "no info", "nan"}

    def _normalize_missing(self, s):
        tokens = self._missing_tokens()

        if s.dtype == "object" or pd.api.types.is_string_dtype(s):
            s = s.astype("string").str.strip()
            s = s.mask(s.str.lower().isin(tokens), pd.NA)

        return s

    def _is_binary(self, s):
        s = pd.to_numeric(s, errors="coerce").dropna()
        return not s.empty and set(s.unique()).issubset({0, 1})

    def _is_date_column(self, s):
        try:
            parsed = pd.to_datetime(s, errors="coerce")
            return parsed.notna().mean() > 0.8
        except:
            return False

    def _is_human_text(self, s):
        if not (s.dtype == "object" or pd.api.types.is_string_dtype(s)):
            return False

        non_null = s.dropna().astype(str)
        if non_null.empty:
            return False

        space_ratio = non_null.str.contains(" ").mean()
        unique_ratio = non_null.nunique() / len(non_null)

        return space_ratio > 0.4 and unique_ratio > 0.5

    def _label_encode(self, s):
        s = s.astype("string").fillna("unknown")
        le = LabelEncoder()
        encoded = le.fit_transform(s)
        return pd.Series(encoded, index=s.index)

    def _scale(self, s):
        scaler = MinMaxScaler()
        return pd.Series(
            scaler.fit_transform(s.to_frame()).ravel(),
            index=s.index
        )

    # -------------------------
    # MAIN CLEAN FUNCTION
    # -------------------------
    def clean(self, df, decision_report=None, scale_columns=None):

        df = df.copy()
        scale_columns = set(scale_columns or [])

        if decision_report is None:
            profile = self.profiler.profile(df)
            decision_report = self.decision_engine.decide(profile)

        audit = {"columns": {}}

        for col in df.columns:
            before = df[col].copy()
            s = self._normalize_missing(before)

            decision = decision_report.get("decisions", {}).get(col, {})
            col_type = decision.get("signals", {}).get("type", "unknown")
            signals = decision.get("signals", {})

            # -------------------------
            # TEXT / CATEGORICAL
            # -------------------------
            if col_type in ["categorical", "text"] or s.dtype == "object":

                if self._is_date_column(s):
                    df[col] = before
                    audit["columns"][col] = {"action": "date_preserved"}
                    continue

                if self._is_human_text(s):
                    df[col] = before
                    audit["columns"][col] = {"action": "text_preserved"}
                    continue

                mode = s.mode(dropna=True)
                fill = mode.iloc[0] if not mode.empty else "unknown"
                s = s.fillna(fill)

                df[col] = self._label_encode(s)
                audit["columns"][col] = {"action": "label_encoded"}
                continue

            # -------------------------
            # NUMERIC (STRICT PRESERVE MODE)
            # -------------------------
            if col_type == "numeric":
                s = pd.to_numeric(s, errors="coerce")

                # ✅ Preserve binary
                if self._is_binary(s):
                    df[col] = s
                    audit["columns"][col] = {"action": "binary_preserved"}
                    continue

                has_missing = s.isna().any()

                # 🔥 CRITICAL: DO NOT MODIFY CLEAN DATA
                if not has_missing and col not in scale_columns:
                    df[col] = before
                    audit["columns"][col] = {"action": "untouched_clean"}
                    continue

                s_clean = s.copy()

                # -------------------------
                # Missing handling ONLY
                # -------------------------
                if has_missing:
                    skew = signals.get("skew", 0)

                    if abs(skew) > 1:
                        fill_value = s_clean.median()
                        strategy = "median"
                    else:
                        fill_value = s_clean.mean()
                        strategy = "mean"

                    s_clean = s_clean.fillna(fill_value)
                else:
                    strategy = "none"

                # -------------------------
                # Scaling ONLY if user selected
                # -------------------------
                if col in scale_columns:
                    s_clean = self._scale(s_clean)
                    action = f"{strategy}_then_scaled" if has_missing else "scaled_only"
                else:
                    action = strategy

                df[col] = s_clean

                audit["columns"][col] = {
                    "action": action,
                    "missing_handled": has_missing,
                    "scaled": col in scale_columns
                }

                continue

            # -------------------------
            # DEFAULT
            # -------------------------
            df[col] = before
            audit["columns"][col] = {"action": "kept"}

        return df, audit