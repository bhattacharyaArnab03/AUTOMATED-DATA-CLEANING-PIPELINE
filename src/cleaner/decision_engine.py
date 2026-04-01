class DecisionEngine:
    def __init__(self, config=None):
        default_config = {
            "drop_missing_threshold": 0.60,
            "high_missing_threshold": 0.30,
            "high_outlier_ratio_threshold": 0.05,
            "high_skew_threshold": 1.0,
            "high_cardinality_threshold": 50,
            "low_confidence_threshold": 0.45,
        }

        self.config = default_config if config is None else {**default_config, **config}

    def _safe_get(self, dct, keys, default=None):
        current = dct
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return default
            current = current[key]
        return current

    def _normalize_anomaly_ratio(self, anomaly_rate, fallback_outlier_ratio):
        if anomaly_rate is None:
            return fallback_outlier_ratio
        return float(anomaly_rate)

    def _fuse_signals(self, col_name, profile, n_rows):
        col_type = profile.get("type", "unknown")
        missing_pct = self._safe_get(profile, ["missing", "missing_pct"], 0.0)
        n_unique = profile.get("n_unique", 0)

        # 🔥 FIXED: Handle structured outliers safely
        outlier_info = profile.get("outliers", {})

        if isinstance(outlier_info, dict):
            outlier_count = outlier_info.get("count", 0)
        else:
            outlier_count = outlier_info  # backward compatibility

        fallback_outlier_ratio = (
            0.0 if not n_rows else float(outlier_count) / float(n_rows)
        )

        anomaly_rate = self._safe_get(profile, ["anomaly", "anomaly_rate"], None)
        anomaly_ratio = self._normalize_anomaly_ratio(
            anomaly_rate, fallback_outlier_ratio
        )

        stats = profile.get("stats", {})
        skew = (
            abs(float(stats.get("skew", 0.0)))
            if isinstance(stats, dict)
            else 0.0
        )

        pattern = profile.get("pattern", "unknown")
        quality_flags = profile.get("quality_flags", {})

        # -------------------------
        # SIGNAL FUSION SCORE
        # -------------------------
        score = 0.0
        score += 0.35 * min(missing_pct, 1.0)
        score += 0.30 * min(
            anomaly_ratio / max(self.config["high_outlier_ratio_threshold"], 1e-9),
            1.0,
        )
        score += 0.15 * min(
            skew / max(self.config["high_skew_threshold"], 1e-9), 1.0
        )
        score += 0.10 if quality_flags.get("high_cardinality", False) else 0.0
        score += 0.10 if pattern == "mixed" else 0.0

        score = max(0.0, min(score, 1.0))

        # -------------------------
        # REASONS
        # -------------------------
        reasons = []

        if missing_pct >= self.config["high_missing_threshold"]:
            reasons.append(f"missing_pct={missing_pct:.2f} is high")

        if anomaly_ratio >= self.config["high_outlier_ratio_threshold"]:
            reasons.append(f"anomaly_ratio={anomaly_ratio:.2f} is high")

        if skew >= self.config["high_skew_threshold"] and col_type == "numeric":
            reasons.append(f"skew={skew:.2f} suggests robust treatment")

        if quality_flags.get("high_cardinality", False):
            reasons.append("high cardinality detected")

        if pattern == "mixed" and col_type in ["text", "categorical"]:
            reasons.append("format inconsistency detected")

        return {
            "fused_score": round(score, 4),
            "reasons": reasons,
            "signals": {
                "type": col_type,
                "missing_pct": round(float(missing_pct), 4),
                "anomaly_ratio": round(float(anomaly_ratio), 4),
                "skew": round(float(skew), 4),
                "n_unique": int(n_unique),
                "pattern": pattern,
            },
        }

    def decide_column(self, col_name, profile, n_rows):
        fused = self._fuse_signals(col_name, profile, n_rows)
        signals = fused["signals"]
        score = fused["fused_score"]
        reasons = list(fused["reasons"])

        col_type = signals["type"]
        missing_pct = signals["missing_pct"]
        anomaly_ratio = signals["anomaly_ratio"]
        skew = signals["skew"]
        pattern = signals["pattern"]
        n_unique = signals["n_unique"]

        action = "keep"
        parameters = {}
        confidence = round(1.0 - score, 4)

        # -------------------------
        # DECISION LOGIC
        # -------------------------

        if (
            missing_pct >= self.config["drop_missing_threshold"]
            and col_type != "numeric"
        ):
            action = "drop_column"
            reasons.append("missingness too high for reliable recovery")

        elif col_type == "numeric":
            if missing_pct > 0.0 or anomaly_ratio > 0.0:

                if (
                    anomaly_ratio
                    >= self.config["high_outlier_ratio_threshold"]
                    and missing_pct > 0.0
                ):
                    action = "median_impute_then_robust_scale"
                    parameters = {"imputer": "median", "scaler": "robust"}
                    reasons.append(
                        "numeric column with missing values and anomalies"
                    )

                elif missing_pct > 0.0 and skew >= self.config["high_skew_threshold"]:
                    action = "median_impute"
                    parameters = {"imputer": "median"}
                    reasons.append("skewed numeric distribution")

                elif missing_pct > 0.0:
                    action = "mean_impute"
                    parameters = {"imputer": "mean"}
                    reasons.append("numeric column with missing values")

                elif (
                    anomaly_ratio
                    >= self.config["high_outlier_ratio_threshold"]
                ):
                    action = "robust_scale"
                    parameters = {"scaler": "robust"}
                    reasons.append("anomalies present; robust scaling preferred")

                else:
                    action = "median_impute"
                    parameters = {"imputer": "median"}
                    reasons.append("numeric column needs stabilization")

            else:
                action = "keep_numeric"

        elif col_type == "categorical":
            if (
                missing_pct > 0.0
                and n_unique <= self.config["high_cardinality_threshold"]
            ):
                action = "mode_impute"
                parameters = {"imputer": "most_frequent"}
                reasons.append("categorical column with manageable cardinality")

            elif (
                missing_pct > 0.0
                and n_unique > self.config["high_cardinality_threshold"]
            ):
                action = "unknown_label_impute"
                parameters = {"imputer": "constant", "fill_value": "Unknown"}
                reasons.append("high-cardinality categorical column")

            elif pattern == "mixed":
                action = "normalize_and_review"
                parameters = {"normalize": True}
                reasons.append("categorical formatting appears inconsistent")

            else:
                action = "keep_categorical"

        elif col_type == "datetime":
            if missing_pct > 0.0:
                action = "datetime_parse_then_ffill"
                parameters = {"parse": True, "fill_strategy": "ffill"}
                reasons.append("datetime column with missing values")
            else:
                action = "parse_datetime"

        elif col_type == "text":
            if pattern in ["email", "phone", "zipcode"] or "phone" in col_name.lower():
                action = "validate_and_standardize_pattern"
                parameters = {
                    "pattern": pattern if pattern != "mixed" else "phone"
                }
                reasons.append(
                    "structured column detected (pattern or column name)"
                )

            elif pattern == "mixed":
                action = "normalize_text_then_review"
                parameters = {"normalize": True}
                reasons.append("text formatting inconsistent")

            else:
                action = "keep_text"

        elif col_type == "boolean":
            if missing_pct > 0.0:
                action = "boolean_impute_mode"
                parameters = {"imputer": "most_frequent"}
                reasons.append("boolean column with missing values")
            else:
                action = "keep_boolean"

        # -------------------------
        # CONFIDENCE GATING
        # -------------------------
        if (
            confidence < self.config["low_confidence_threshold"]
            and action.startswith("keep")
        ):
            action = "manual_review"
            reasons.append("confidence too low for passive action")

        return {
            "column": col_name,
            "action": action,
            "confidence": round(confidence, 4),
            "signals": signals,
            "fusion_score": fused["fused_score"],
            "reasons": reasons,
            "parameters": parameters,
        }

    def decide(self, profile_report):
        meta = profile_report.get("__meta__", {})
        n_rows = int(meta.get("n_rows", 0))

        decisions = {}
        for col_name, profile in profile_report.items():
            if col_name.startswith("__"):
                continue
            decisions[col_name] = self.decide_column(
                col_name, profile, n_rows
            )

        return {
            "__meta__": meta,
            "decisions": decisions,
        }