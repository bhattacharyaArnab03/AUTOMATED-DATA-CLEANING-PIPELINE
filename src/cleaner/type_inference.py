import pandas as pd
from dateutil.parser import parse

def is_date(series, threshold=0.7):
    sample = series.dropna().astype(str).head(50)
    if len(sample) == 0:
        return False

    success = 0
    for val in sample:
        try:
            parse(val, fuzzy=False)
            success += 1
        except:
            pass

    return (success / len(sample)) >= threshold


def is_numeric_like(series, threshold=0.9):
    sample = series.dropna().astype(str)
    if len(sample) == 0:
        return False

    success = 0
    for val in sample:
        try:
            float(val)
            success += 1
        except:
            pass

    return (success / len(sample)) >= threshold


def is_boolean_like(series):
    values = set(series.dropna().astype(str).str.lower().unique())
    return values.issubset({"true", "false", "yes", "no", "0", "1"})


def infer_type(series):
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"

    if pd.api.types.is_bool_dtype(series) or is_boolean_like(series):
        return "boolean"

    if is_numeric_like(series):
        return "numeric"

    if is_date(series):
        return "datetime"

    unique_ratio = series.nunique(dropna=True) / max(len(series), 1)

    if unique_ratio < 0.05:
        return "categorical"

    return "text"