import pandas as pd

from cleaner.type_inference import infer_type
from cleaner.pattern_detection import detect_pattern
from cleaner.quality_checks import (
    missing_stats,
    numeric_stats,
    categorical_stats,
    detect_outliers_iqr,
)
from cleaner.anomaly_detector import EnsembleAnomalyDetector


class DataProfiler:
    def __init__(self):
        self.report = {}
        self.anomaly_detector = EnsembleAnomalyDetector()

    def profile_column(self, series):
        col_type = infer_type(series)

        col_report = {
            "type": col_type,
            "missing": missing_stats(series),
            "n_unique": int(series.nunique(dropna=True)),
        }

        # -------------------------
        # TEXT / CATEGORICAL
        # -------------------------
        if col_type in ["text", "categorical"]:
            col_report["pattern"] = detect_pattern(series)

        # -------------------------
        # NUMERIC
        # -------------------------
        if col_type == "numeric":
            stats = numeric_stats(series)
            col_report["stats"] = stats

            outlier_info = detect_outliers_iqr(series)
            col_report["outliers"] = outlier_info

            anomaly = self.anomaly_detector.detect(series)
            col_report["anomaly"] = {
                "anomaly_count": anomaly["count"],
                "anomaly_rate": round(anomaly["rate"], 4),
                "indices": anomaly["indices"][:20],
                "method_counts": anomaly["method_counts"],
                "active_methods": anomaly["active_methods"],
            }

        # -------------------------
        # CATEGORICAL STATS
        # -------------------------
        if col_type == "categorical":
            col_report["stats"] = categorical_stats(series)

        # -------------------------
        # QUALITY FLAGS (🔥 FIXED)
        # -------------------------
        outlier_info = col_report.get("outliers", {})
        outlier_count = outlier_info.get("count", 0)

        col_report["quality_flags"] = {
            "high_missing": col_report["missing"]["missing_pct"] > 0.3,
            "high_cardinality": col_report["n_unique"] > 50,
            "has_outliers": outlier_count > 0,
            "potential_id_column": col_report["n_unique"] == len(series),
        }

        return col_report

    def profile(self, df: pd.DataFrame):
        self.report = {
            "__meta__": {
                "n_rows": int(df.shape[0]),
                "n_columns": int(df.shape[1]),
                "columns": list(df.columns),
            }
        }

        for col in df.columns:
            self.report[col] = self.profile_column(df[col])

        return self.report