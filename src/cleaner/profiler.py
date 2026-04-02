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
        self.anomaly_detector = EnsembleAnomalyDetector()
        self.missing_tokens = {
            "", "na", "n/a", "null", "none",
            "nan", "unknown", "no info", "not available"
        }

    def _normalize_missing(self, s):
        if s.dtype == "object" or pd.api.types.is_string_dtype(s):
            s = s.astype("string").str.strip()
            s = s.mask(s.str.lower().isin(self.missing_tokens), pd.NA)
        return s

    def profile_column(self, series):
        series = self._normalize_missing(series)
        col_type = infer_type(series)

        col_report = {
            "type": col_type,
            "missing": missing_stats(series),
            "n_unique": int(series.nunique(dropna=True)),
        }

        if col_type in ["text", "categorical"]:
            col_report["pattern"] = detect_pattern(series)

        if col_type == "numeric":
            stats = numeric_stats(series)
            col_report["stats"] = stats
            col_report["outliers"] = detect_outliers_iqr(series)

            anomaly = self.anomaly_detector.detect(series)
            col_report["anomaly"] = {
                "anomaly_count": anomaly["count"],
                "anomaly_rate": anomaly["rate"],
            }

        if col_type == "categorical":
            col_report["stats"] = categorical_stats(series)

        return col_report

    def profile(self, df):
        report = {
            "__meta__": {
                "n_rows": int(df.shape[0]),
                "n_columns": int(df.shape[1]),
                "columns": list(df.columns),
            }
        }

        for col in df.columns:
            report[col] = self.profile_column(df[col])

        return report