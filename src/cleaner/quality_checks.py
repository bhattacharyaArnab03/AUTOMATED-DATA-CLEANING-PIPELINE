import pandas as pd
import numpy as np

def missing_stats(series):
    return {
        "missing_count": int(series.isna().sum()),
        "missing_pct": float(series.isna().mean())
    }


def numeric_stats(series):
    s = pd.to_numeric(series, errors="coerce")
    s = s.dropna()

    if len(s) == 0:
        return {
            "mean": None,
            "median": None,
            "std": None,
            "min": None,
            "max": None,
            "skew": None
        }

    mean = s.mean()
    median = s.median()
    std = s.std()
    min_val = s.min()
    max_val = s.max()
    skew = s.skew()

    return {
        "mean": float(mean) if pd.notna(mean) else 0.0,
        "median": float(median) if pd.notna(median) else 0.0,
        "std": float(std) if pd.notna(std) else 0.0,
        "min": float(min_val) if pd.notna(min_val) else 0.0,
        "max": float(max_val) if pd.notna(max_val) else 0.0,
        "skew": float(skew) if pd.notna(skew) else 0.0
    }


def categorical_stats(series):
    return {
        "unique_values": int(series.nunique()),
        "top_values": series.value_counts().head(5).to_dict()
    }


def detect_outliers_iqr(series):
    import pandas as pd

    # 🔥 FORCE NUMERIC
    s = pd.to_numeric(series, errors="coerce")

    # Remove NA
    s = s.dropna()

    if len(s) == 0:
        return {
            "count": 0,
            "lower_bound": None,
            "upper_bound": None
        }

    q1 = s.quantile(0.25)
    q3 = s.quantile(0.75)

    iqr = q3 - q1

    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    outliers = (s < lower) | (s > upper)

    return {
        "count": int(outliers.sum()),
        "lower_bound": float(lower),
        "upper_bound": float(upper)
    }