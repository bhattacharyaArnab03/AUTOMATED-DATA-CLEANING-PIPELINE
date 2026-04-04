import argparse
import json
import sys
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
SRC_PATH = BASE_DIR / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from cleaner.pipeline_service import run_pipeline_from_df  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the automated data cleaning pipeline from the console."
    )
    parser.add_argument(
        "--input",
        type=str,
        default="examples/sample.csv",
        help="Path to the input CSV file.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports/console_run",
        help="Directory where output files will be saved.",
    )
    parser.add_argument(
        "--scale-column",
        "--scale-columns",
        dest="scale_columns_raw",
        action="append",
        nargs="+",
        default=[],
        help=(
            "One or more columns to scale. Example: "
            '--scale-column age bmi or --scale-column "Billing Amount"'
        ),
    )
    parser.add_argument(
        "--use-config",
        action="store_true",
        help="Use configs/default.yaml for domain rules.",
    )
    return parser.parse_args()


def _resolve_scale_columns(raw_groups, available_columns):
    available_lookup = {col.lower(): col for col in available_columns}
    tokenized_headers = {
        tuple(col.lower().split()): col for col in available_columns
    }

    resolved = []
    seen = set()

    for group in raw_groups:
        if not group:
            continue

        tokens = [str(token).strip().lower() for token in group if str(token).strip()]
        if not tokens:
            continue

        joined = " ".join(tokens)
        if joined in available_lookup:
            col = available_lookup[joined]
            if col not in seen:
                resolved.append(col)
                seen.add(col)
            continue

        i = 0
        while i < len(tokens):
            match = None
            match_len = 0

            for j in range(len(tokens), i, -1):
                candidate = tuple(tokens[i:j])
                if candidate in tokenized_headers:
                    match = tokenized_headers[candidate]
                    match_len = j - i
                    break

            if match is not None:
                if match not in seen:
                    resolved.append(match)
                    seen.add(match)
                i += match_len
                continue

            single = tokens[i]
            if single in available_lookup:
                col = available_lookup[single]
                if col not in seen:
                    resolved.append(col)
                    seen.add(col)
                i += 1
                continue

            raise ValueError(
                f"Could not match scale column token '{tokens[i]}' "
                f"to any column in the input file."
            )

    return resolved


def main():
    args = parse_args()

    input_path = (
        (BASE_DIR / args.input).resolve()
        if not Path(args.input).is_absolute()
        else Path(args.input)
    )
    output_dir = (
        (BASE_DIR / args.output_dir).resolve()
        if not Path(args.output_dir).is_absolute()
        else Path(args.output_dir)
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    df = pd.read_csv(
        input_path,
        na_values=["?", "NA", "", "null", "None", "No Info", "no info", "NO INFO"],
    )

    scale_columns = _resolve_scale_columns(args.scale_columns_raw, df.columns.tolist())

    config_path = str(BASE_DIR / "configs" / "default.yaml") if args.use_config else None

    result = run_pipeline_from_df(
        df,
        config_path=config_path,
        scale_columns=scale_columns,
    )

    cleaned_df = result["cleaned_df"]
    audit = result["audit"]
    profile_report = result["profile_report"]
    decision_report = result["decision_report"]

    cleaned_path = output_dir / "cleaned_dataset.csv"
    audit_path = output_dir / "cleaning_audit.json"
    profile_path = output_dir / "final_profile.json"
    decision_path = output_dir / "decision_report.json"

    cleaned_df.to_csv(cleaned_path, index=False)
    audit_path.write_text(json.dumps(audit, indent=2, default=str), encoding="utf-8")
    profile_path.write_text(json.dumps(profile_report, indent=2, default=str), encoding="utf-8")
    decision_path.write_text(json.dumps(decision_report, indent=2, default=str), encoding="utf-8")

    print("\nPipeline completed successfully.")
    print(f"Input file     : {input_path}")
    print(f"Cleaned CSV    : {cleaned_path}")
    print(f"Audit JSON     : {audit_path}")
    print(f"Profile JSON   : {profile_path}")
    print(f"Decision JSON  : {decision_path}")
    print(f"Scaled columns : {scale_columns if scale_columns else 'None'}")


if __name__ == "__main__":
    main()