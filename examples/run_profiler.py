import sys
import os
sys.path.append(os.path.abspath("src"))

import pandas as pd
import json
from cleaner.profiler import DataProfiler

# Load dataset
df = pd.read_csv("examples/healthcare_dataset.csv")

# Run profiler
profiler = DataProfiler()
report = profiler.profile(df)

# Print output
print("=== FINAL PROFILE REPORT ===\n")

for col, details in report.items():
    print(f"\n🔹 Column: {col}")
    for key, value in details.items():
        print(f"{key}: {value}")

# Save JSON
os.makedirs("reports", exist_ok=True)

with open("reports/final_profile.json", "w") as f:
    json.dump(report, f, indent=4)

print("\nReport saved to reports/final_profile.json")