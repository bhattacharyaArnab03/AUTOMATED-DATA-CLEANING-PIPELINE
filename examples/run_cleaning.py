import sys
import os
sys.path.append(os.path.abspath("src"))

import json
import pandas as pd
from cleaner.cleaning_executor import CleaningExecutor

# -------------------------
# CONFIGURATION (OPTIONAL)
# -------------------------

USE_CONFIG = True   # 🔁 Set False for fully generic mode

CONFIG_PATH = "configs/default.yaml" if USE_CONFIG else None


# -------------------------
# LOAD DATA
# -------------------------

df = pd.read_csv("examples/healthcare_dataset.csv", na_values=["?", "NA", ""])

with open("reports/decision_report.json", "r") as f:
    decision_report = json.load(f)


# -------------------------
# RUN CLEANING PIPELINE
# -------------------------

executor = CleaningExecutor(config_path=CONFIG_PATH)

cleaned_df, audit = executor.clean(df, decision_report)


# -------------------------
# PRINT SUMMARY
# -------------------------

print("=== PASS SUMMARY ===\n")

for p in audit.get("passes", []):
    print(f"Pass {p['pass']} → Changes: {p['changes']}")

print("\n=== CLEANING SUMMARY ===\n")

if "passes" in audit and len(audit["passes"]) > 0:
    final_audit = audit["passes"][-1]["audit"]
else:
    final_audit = audit  # fallback (single-pass mode)

for col, details in final_audit.get("columns", {}).items():
    print(f"\n🔹 Column: {col}")
    print(f"Action: {details.get('action')}")
    print(f"Reason: {details.get('reason')}")
    print(f"Missing before: {details.get('before_missing')}")
    print(f"Missing after: {details.get('after_missing')}")
    print(f"Invalid detected: {details.get('invalid_detected', 0)}")


# -------------------------
# PREVIEW CLEANED DATA
# -------------------------

print("\n=== FINAL DATA PREVIEW ===\n")
print(cleaned_df.head())


# -------------------------
# SAVE OUTPUTS
# -------------------------

os.makedirs("reports", exist_ok=True)

cleaned_df.to_csv("reports/cleaned_dataset.csv", index=False)

with open("reports/cleaning_audit.json", "w") as f:
    json.dump(audit, f, indent=4, default=str)


# -------------------------
# FINAL LOG
# -------------------------

print("\n✅ Cleaned dataset saved to reports/cleaned_dataset.csv")
print("✅ Audit saved to reports/cleaning_audit.json")

if USE_CONFIG:
    print("⚙️ Domain rules applied from:", CONFIG_PATH)
else:
    print("⚙️ Running in fully generic mode (no domain rules)")