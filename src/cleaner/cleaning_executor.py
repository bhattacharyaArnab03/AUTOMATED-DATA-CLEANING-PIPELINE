import pandas as pd
from sklearn.preprocessing import RobustScaler

from cleaner.strategy_selector import StrategySelector
from cleaner.validator import Validator
from cleaner.domain_rules import DomainRules
from cleaner.anomaly_detector import EnsembleAnomalyDetector

# OPTIONAL (for dynamic re-decision)
from cleaner.profiler import DataProfiler
from cleaner.decision_engine import DecisionEngine


class CleaningExecutor:
    def __init__(self, confidence_threshold=0.6, config_path=None, dynamic_redecision=True):
        self.audit = {}
        self.confidence_threshold = confidence_threshold
        self.current_invalid_count = 0

        self.selector = StrategySelector()
        self.validator = Validator()
        self.domain_rules = DomainRules(config_path) if config_path else None
        self.anomaly_detector = EnsembleAnomalyDetector()

        # NEW 🔥
        self.dynamic_redecision = dynamic_redecision
        self.profiler = DataProfiler()
        self.decision_engine = DecisionEngine()

    # -------------------------
    # TEXT CLEANING
    # -------------------------

    def _normalize_text(self, series):
        s = series.astype("string").str.strip()
        s = s.str.replace(r"\s+", " ", regex=True)
        s = s.str.lower()
        s = s.replace({"": pd.NA, "nan": pd.NA, "none": pd.NA})
        return s

    # -------------------------
    # PATTERN VALIDATION
    # -------------------------

    def _validate_pattern(self, series, pattern_name):
        patterns = {
            "email": r"^[\w\.-]+@[\w\.-]+\.\w+$",
            "phone": r"^\+?\d{10,13}$",
            "zipcode": r"^\d{5,6}$"
        }

        regex = patterns.get(pattern_name)
        if not regex:
            self.current_invalid_count = 0
            return series

        s = series.astype("string")
        valid_mask = s.str.match(regex, na=False)

        self.current_invalid_count = int((~valid_mask).sum())

        return s.where(valid_mask, pd.NA)

    # -------------------------
    # DOMAIN VALIDATION
    # -------------------------

    def _apply_domain_rules(self, series, col_name):
        if not self.domain_rules:
            return series

        rule = self.domain_rules.get_rule(col_name)
        if not rule:
            return series

        s = pd.to_numeric(series, errors="coerce")

        if "min" in rule and "max" in rule:
            s = s.where((s >= rule["min"]) & (s <= rule["max"]), pd.NA)

        if rule.get("type") == "int":
            s = s.round().astype("Int64")

        return s

    # -------------------------
    # TRANSFORMATIONS
    # -------------------------

    def _robust_scale(self, series):
        s = pd.to_numeric(series, errors="coerce")
        scaler = RobustScaler()
        return pd.Series(scaler.fit_transform(s.to_frame()).ravel(), index=series.index)

    def _parse_datetime(self, series):
        return pd.to_datetime(series, errors="coerce")

    # -------------------------
    # ANOMALY FILTER
    # -------------------------

    def _apply_ensemble_anomaly_filter(self, series):
        numeric_series = pd.to_numeric(series, errors="coerce")
        anomaly = self.anomaly_detector.detect(numeric_series)

        filtered = numeric_series.copy()
        filtered.loc[anomaly["mask"]] = pd.NA

        self.current_invalid_count = int(anomaly["count"])
        return filtered, anomaly

    # -------------------------
    # AUDIT
    # -------------------------

    def _record_audit(self, action, reason, before, after):
        return {
            "action": action,
            "reason": reason,
            "before_missing": int(before.isna().sum()),
            "after_missing": int(after.isna().sum()),
            "invalid_detected": int(self.current_invalid_count)
        }

    # -------------------------
    # SINGLE PASS CLEAN
    # -------------------------

    def _single_pass_clean(self, df, decision_report):
        cleaned = df.copy()

        audit = {
            "__meta__": {
                "rows_before": int(df.shape[0]),
                "cols_before": int(df.shape[1]),
                "dropped_columns": []
            },
            "columns": {}
        }

        for col, decision in decision_report.get("decisions", {}).items():

            if col not in cleaned.columns:
                continue

            action = decision.get("action", "keep")
            reason = decision.get("reasons", [])
            params = decision.get("parameters", {})
            confidence = decision.get("confidence", 1.0)

            before = cleaned[col].copy()

            # CONFIDENCE CONTROL
            if confidence < self.confidence_threshold and action.startswith("keep"):
                cleaned[col] = before
                audit["columns"][col] = {
                    "action": "manual_review",
                    "reason": reason + ["low confidence"],
                    "before_missing": int(before.isna().sum()),
                    "after_missing": int(before.isna().sum()),
                    "invalid_detected": 0
                }
                continue

            # ACTIONS

            if action == "validate_and_standardize_pattern":
                s = self._normalize_text(before)
                s = self._validate_pattern(s, params.get("pattern"))
                cleaned[col] = s

            elif action in ["mean_impute", "median_impute", "median_impute_then_robust_scale"]:

                numeric_series = pd.to_numeric(before, errors="coerce")

                # 🔥 PASS 1: anomaly removal
                filtered_series, anomaly_info = self._apply_ensemble_anomaly_filter(numeric_series)

                # 🔥 PASS 2: imputation strategy
                strategy, best_series = self.selector.select_best_numeric(filtered_series)

                # 🔥 PASS 3: statistical validation
                validated, low, high = self.validator.validate_numeric(best_series)

                # 🔥 PASS 4: domain rules
                validated = self._apply_domain_rules(validated, col)

                if action == "median_impute_then_robust_scale":
                    cleaned[col] = self._robust_scale(validated)
                else:
                    cleaned[col] = validated

                reason.append(f"ensemble anomalies flagged: {anomaly_info['count']}")
                reason.append(f"best strategy: {strategy}")
                reason.append(f"IQR bounds: [{low:.2f}, {high:.2f}]")

            elif action == "robust_scale":
                numeric_series = pd.to_numeric(before, errors="coerce")
                filtered_series, anomaly_info = self._apply_ensemble_anomaly_filter(numeric_series)
                cleaned[col] = self._robust_scale(filtered_series)

            elif action == "mode_impute":
                cleaned[col] = before.fillna(before.mode().iloc[0] if not before.mode().empty else "Unknown")

            elif action == "normalize_text_then_review":
                cleaned[col] = self._normalize_text(before)

            else:
                cleaned[col] = before

            after = cleaned[col]

            audit["columns"][col] = self._record_audit(action, reason, before, after)

        audit["__meta__"]["rows_after"] = int(cleaned.shape[0])
        audit["__meta__"]["cols_after"] = int(cleaned.shape[1])

        return cleaned, audit

    # -------------------------
    # MULTI-PASS CLEANING 🔥
    # -------------------------

    def clean(self, df, decision_report, max_passes=3):
        current_df = df.copy()
        overall_audit = {"passes": []}

        for pass_num in range(1, max_passes + 1):

            print(f"\n🔁 PASS {pass_num} STARTED")

            # 🔥 dynamic re-decision
            if self.dynamic_redecision:
                profile = self.profiler.profile(current_df)
                decision_report = self.decision_engine.decide(profile)

            cleaned_df, audit = self._single_pass_clean(current_df, decision_report)

            # detect changes
            changes = (current_df != cleaned_df).sum().sum()

            overall_audit["passes"].append({
                "pass": pass_num,
                "changes": int(changes),
                "audit": audit
            })

            print(f"Changes in pass {pass_num}: {changes}")

            if changes == 0:
                print("✅ Converged — no further changes")
                break

            current_df = cleaned_df.copy()

        return current_df, overall_audit