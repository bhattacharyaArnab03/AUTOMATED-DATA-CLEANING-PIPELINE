from cleaner.profiler import DataProfiler
from cleaner.decision_engine import DecisionEngine
from cleaner.cleaning_executor import CleaningExecutor


def run_pipeline_from_df(df, config_path=None, scale_columns=None):

    profiler = DataProfiler()
    profile = profiler.profile(df)

    decision_engine = DecisionEngine()
    decision = decision_engine.decide(profile)

    executor = CleaningExecutor(config_path=config_path)
    cleaned_df, audit = executor.clean(df, scale_columns=scale_columns)

    return {
        "cleaned_df": cleaned_df,
        "audit": audit,
        "profile_report": profile,
        "decision_report": decision,
    }