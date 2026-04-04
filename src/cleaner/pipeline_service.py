from cleaner.profiler import DataProfiler
from cleaner.decision_engine import DecisionEngine
from cleaner.cleaning_executor import CleaningExecutor


def run_pipeline_from_df(df, config_path=None, scale_columns=None):
    profiler = DataProfiler()
    profile_report = profiler.profile(df)

    decision_engine = DecisionEngine()
    decision_report = decision_engine.decide(profile_report)

    executor = CleaningExecutor(config_path=config_path)
    cleaned_df, audit = executor.clean(
        df,
        decision_report=decision_report,
        scale_columns=scale_columns,
    )

    return {
        "cleaned_df": cleaned_df,
        "audit": audit,
        "profile_report": profile_report,
        "decision_report": decision_report,
    }