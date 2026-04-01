import json
from typing import Dict, Any, Optional

import pandas as pd

from cleaner.profiler import DataProfiler
from cleaner.decision_engine import DecisionEngine
from cleaner.cleaning_executor import CleaningExecutor


def run_pipeline_from_df(
    df: pd.DataFrame,
    config_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run the complete cleaning pipeline on an in-memory dataframe.
    Returns all intermediate and final artifacts.
    """

    profiler = DataProfiler()
    profile_report = profiler.profile(df)

    decision_engine = DecisionEngine()
    decision_report = decision_engine.decide(profile_report)

    executor = CleaningExecutor(config_path=config_path)
    cleaned_df, audit = executor.clean(df, decision_report)

    return {
        "profile_report": profile_report,
        "decision_report": decision_report,
        "cleaned_df": cleaned_df,
        "audit": audit,
    }