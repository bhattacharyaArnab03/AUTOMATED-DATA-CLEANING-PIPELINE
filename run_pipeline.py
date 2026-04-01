import argparse
import json
import os
import sys

import pandas as pd

sys.path.append(os.path.abspath("src"))

from cleaner.profiler import DataProfiler
from cleaner.decision_engine import DecisionEngine
from cleaner.cleaning_executor import CleaningExecutor


def run_pipeline(input_path: str, output_dir: str = "reports", config_path: str | None = None):
    os.makedirs(output_dir, exist_ok=True)

    # 1) Load data
    df = pd.read_csv(input_path, na_values=["?", "NA", "", "null", "None"])

    # 2) Profile
    profiler = DataProfiler()
    profile_report = profiler.profile(df)

    with open(os.path.join(output_dir, "final_profile.json"), "w", encoding="utf-8") as f:
        json.dump(profile_report, f, indent=4, default=str)

    # 3) Decide
    engine = DecisionEngine()
    decision_report = engine.decide(profile_report)

    with open(os.path.join(output_dir, "decision_report.json"), "w", encoding="utf-8") as f:
        json.dump(decision_report, f, indent=4, default=str)

    # 4) Clean
    executor = CleaningExecutor(config_path=config_path)
    cleaned_df, audit = executor.clean(df, decision_report)

    cleaned_path = os.path.join(output_dir, "cleaned_dataset.csv")
    audit_path = os.path.join(output_dir, "cleaning_audit.json")

    cleaned_df.to_csv(cleaned_path, index=False)

    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=4, default=str)

    print("Pipeline completed successfully.")
    print(f"Cleaned dataset saved to: {cleaned_path}")
    print(f"Audit saved to: {audit_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run automated data cleaning pipeline")
    parser.add_argument("input", help="Path to input CSV dataset")
    parser.add_argument("--output", default="reports", help="Output directory")
    parser.add_argument("--config", default="configs/default.yaml", help="Optional config YAML path")

    args = parser.parse_args()
    run_pipeline(args.input, args.output, args.config)