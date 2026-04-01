import os
import sys
import json
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from typing import Optional

import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import StreamingResponse

# Make src/ importable when running from PyCharm/terminal
sys.path.append(os.path.abspath("src"))

from cleaner.pipeline_service import run_pipeline_from_df  # noqa: E402

app = FastAPI(
    title="Automated Data Cleaning Pipeline API",
    version="1.0.0",
    description="Upload a CSV file and receive a cleaned dataset plus audit reports.",
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/clean")
async def clean_dataset(
    file: UploadFile = File(...),
    use_config: bool = Query(True, description="Use default YAML domain rules"),
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    try:
        content = await file.read()
        df = pd.read_csv(
            BytesIO(content),
            na_values=["?", "NA", "", "null", "None"]
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Unable to read CSV: {e}")

    config_path = "configs/default.yaml" if use_config else None

    try:
        result = run_pipeline_from_df(df, config_path=config_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {e}")

    cleaned_df = result["cleaned_df"]
    audit = result["audit"]
    profile_report = result["profile_report"]
    decision_report = result["decision_report"]

    # Package all outputs into a ZIP for a single response
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, "w", ZIP_DEFLATED) as zf:
        zf.writestr("cleaned_dataset.csv", cleaned_df.to_csv(index=False))
        zf.writestr("cleaning_audit.json", json.dumps(audit, indent=4, default=str))
        zf.writestr("final_profile.json", json.dumps(profile_report, indent=4, default=str))
        zf.writestr("decision_report.json", json.dumps(decision_report, indent=4, default=str))

    zip_buffer.seek(0)

    headers = {
        "Content-Disposition": 'attachment; filename="cleaning_result.zip"'
    }

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers=headers,
    )