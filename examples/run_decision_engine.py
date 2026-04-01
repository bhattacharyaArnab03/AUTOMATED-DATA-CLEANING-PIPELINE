import sys
import os
sys.path.append(os.path.abspath("src"))

import json
from cleaner.decision_engine import DecisionEngine

with open("reports/final_profile.json", "r") as f:
    profile_report = json.load(f)

engine = DecisionEngine()
decision_report = engine.decide(profile_report)

print("=== DECISION ENGINE OUTPUT ===\n")

for col, details in decision_report["decisions"].items():
    print(f"\n🔹 Column: {col}")
    print(f"Action: {details['action']}")
    print(f"Confidence: {details['confidence']}")
    print(f"Fusion score: {details['fusion_score']}")
    print(f"Reasons: {details['reasons']}")
    print(f"Signals: {details['signals']}")

os.makedirs("reports", exist_ok=True)

with open("reports/decision_report.json", "w") as f:
    json.dump(decision_report, f, indent=4)

print("\n✅ Decision report saved to reports/decision_report.json")