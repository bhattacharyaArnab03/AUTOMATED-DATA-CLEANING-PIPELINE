import json
import sys
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from typing import List

import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import StreamingResponse, HTMLResponse

# -------------------------
# Fix import path
# -------------------------
BASE_DIR = Path(__file__).resolve().parents[1]
SRC_PATH = BASE_DIR / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from cleaner.pipeline_service import run_pipeline_from_df

app = FastAPI(title="Data Cleaning Pipeline API")


# -------------------------
# JSON FIX
# -------------------------
def convert_numpy(obj):
    import numpy as np

    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)

    return str(obj)


# -------------------------
# ROOT UI
# -------------------------
@app.get("/", response_class=HTMLResponse)
def root():
    return """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Automated Data Cleaning Pipeline</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      background: #f5f7fa;
      margin: 0;
      padding: 40px;
    }
    .container {
      max-width: 900px;
      margin: auto;
      background: white;
      padding: 30px;
      border-radius: 12px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    h1 { color: #333; }
    select {
      width: 100%;
      height: 150px;
    }
    button {
      background: #007bff;
      color: white;
      padding: 10px 18px;
      border: none;
      border-radius: 6px;
      cursor: pointer;
    }
    button:hover { background: #0056b3; }
  </style>
</head>

<body>
<div class="container">
  <h1>Automated Data Cleaning Pipeline</h1>

  <input type="file" id="file">
  <button onclick="loadColumns()">Load Columns</button>

  <br><br>

  <select id="cols" multiple></select>

  <br><br>

  <button onclick="clean()">Clean & Download</button>

  <p id="status"></p>
</div>

<script>
let fileInput = document.getElementById("file");
let cols = document.getElementById("cols");
let status = document.getElementById("status");

// -------------------------
// LOAD COLUMNS
// -------------------------
async function loadColumns() {
    let file = fileInput.files[0];

    if (!file) {
        status.innerText = "Please select a file first.";
        return;
    }

    let fd = new FormData();
    fd.append("file", file);

    let res = await fetch("/columns", { method: "POST", body: fd });

    if (!res.ok) {
        status.innerText = "Failed to load columns.";
        return;
    }

    let data = await res.json();

    cols.innerHTML = "";
    data.columns.forEach(c => {
        let opt = document.createElement("option");
        opt.value = c;
        opt.text = c;
        cols.appendChild(opt);
    });

    status.innerText = "Columns loaded";
}


// -------------------------
// CLEAN FUNCTION (FIXED)
// -------------------------
async function clean() {
    let file = fileInput.files[0];

    if (!file) {
        status.innerText = "Please upload a file.";
        return;
    }

    let fd = new FormData();
    fd.append("file", file);

    [...cols.selectedOptions].forEach(o => {
        fd.append("scale_columns", o.value);
    });

    status.innerText = "Processing...";

    try {
        let res = await fetch("/clean", {
            method: "POST",
            body: fd
        });

        if (!res.ok) {
            let err = await res.text();   // 🔥 CRITICAL FIX
            console.error(err);
            status.innerText = "Error: " + err;
            return;
        }

        let blob = await res.blob();

        if (blob.size === 0) {
            status.innerText = "Empty response from server.";
            return;
        }

        let url = window.URL.createObjectURL(blob);

        let a = document.createElement("a");
        a.href = url;
        a.download = "cleaned_output.zip";
        document.body.appendChild(a);
        a.click();
        a.remove();

        status.innerText = "Download started.";

    } catch (e) {
        console.error(e);
        status.innerText = "Unexpected error occurred.";
    }
}
</script>

</body>
</html>
"""


# -------------------------
# GET COLUMNS
# -------------------------
@app.post("/columns")
async def columns(file: UploadFile = File(...)):
    df = pd.read_csv(BytesIO(await file.read()), nrows=0)
    return {"columns": list(df.columns)}


# -------------------------
# CLEAN PIPELINE
# -------------------------
@app.post("/clean")
async def clean(
    file: UploadFile = File(...),
    scale_columns: List[str] = Form(default=[]),
):
    try:
        df = pd.read_csv(
            BytesIO(await file.read()),
            na_values=["?", "NA", "", "null", "None", "No Info"]
        )

        result = run_pipeline_from_df(df, scale_columns=scale_columns)

        zip_buffer = BytesIO()

        with ZipFile(zip_buffer, "w", ZIP_DEFLATED) as zf:
            zf.writestr("cleaned.csv", result["cleaned_df"].to_csv(index=False))

            zf.writestr(
                "audit.json",
                json.dumps(result["audit"], indent=2, default=convert_numpy)
            )

            if "decision_report" in result:
                zf.writestr(
                    "decision.json",
                    json.dumps(result["decision_report"], indent=2, default=convert_numpy)
                )

            if "profile_report" in result:
                zf.writestr(
                    "profile.json",
                    json.dumps(result["profile_report"], indent=2, default=convert_numpy)
                )

        zip_buffer.seek(0)

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=cleaned_output.zip"}
        )

    except Exception as e:
        print("ERROR:", e)  # 🔥 DEBUG LINE
        raise HTTPException(status_code=500, detail=str(e))