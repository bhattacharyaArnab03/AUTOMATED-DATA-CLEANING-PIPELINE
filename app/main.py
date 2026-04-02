import json
import sys
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from typing import List

import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import StreamingResponse, HTMLResponse

# 🔥 Fix import path
BASE_DIR = Path(__file__).resolve().parents[1]
SRC_PATH = BASE_DIR / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from cleaner.pipeline_service import run_pipeline_from_df

app = FastAPI(title="Data Cleaning Pipeline API")


@app.get("/", response_class=HTMLResponse)
def root():
    return """
<!doctype html>
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

    h1 {
      margin-bottom: 10px;
      color: #333;
    }

    .section {
      margin-top: 25px;
    }

    label {
      font-weight: bold;
      display: block;
      margin-bottom: 8px;
    }

    input[type=file] {
      margin-bottom: 10px;
    }

    select {
      width: 100%;
      height: 150px;
      padding: 8px;
      border-radius: 6px;
      border: 1px solid #ccc;
    }

    button {
      background: #007bff;
      color: white;
      border: none;
      padding: 10px 18px;
      border-radius: 6px;
      cursor: pointer;
      margin-top: 10px;
    }

    button:hover {
      background: #0056b3;
    }

    .status {
      margin-top: 10px;
      font-weight: bold;
      color: #444;
    }

    small {
      color: #666;
    }
  </style>
</head>

<body>

<div class="container">
  <h1>Automated Data Cleaning Pipeline</h1>
  <p>Upload your dataset, select features to scale, and download cleaned output.</p>

  <div class="section">
    <label>Upload CSV</label>
    <input type="file" id="file">
    <button onclick="loadColumns()">Load Columns</button>
    <div class="status" id="status"></div>
  </div>

  <div class="section">
    <label>Select Columns to Scale</label>
    <small>Hold Ctrl / Cmd to select multiple</small>
    <select id="cols" multiple></select>
  </div>

  <div class="section">
    <button onclick="clean()">Clean & Download</button>
  </div>
</div>

<script>
let fileInput = document.getElementById("file");
let cols = document.getElementById("cols");
let status = document.getElementById("status");

async function loadColumns() {
    let file = fileInput.files[0];
    if (!file) {
        status.innerText = "Please upload a file first.";
        return;
    }

    let fd = new FormData();
    fd.append("file", file);

    status.innerText = "Loading columns...";

    let res = await fetch("/columns", {
        method: "POST",
        body: fd
    });

    let data = await res.json();

    cols.innerHTML = "";
    data.columns.forEach(c => {
        let opt = document.createElement("option");
        opt.value = c;
        opt.text = c;
        cols.appendChild(opt);
    });

    status.innerText = "Columns loaded successfully.";
}

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

    let res = await fetch("/clean", {
        method: "POST",
        body: fd
    });

    if (!res.ok) {
        status.innerText = "Error during processing.";
        return;
    }

    let blob = await res.blob();
    let url = window.URL.createObjectURL(blob);

    let a = document.createElement("a");
    a.href = url;
    a.download = "cleaned_output.zip";
    a.click();

    status.innerText = "Download started.";
}
</script>

</body>
</html>
"""


@app.post("/columns")
async def columns(file: UploadFile = File(...)):
    df = pd.read_csv(BytesIO(await file.read()), nrows=0)
    return {"columns": list(df.columns)}


@app.post("/clean")
async def clean(
    file: UploadFile = File(...),
    scale_columns: List[str] = Form(default=[]),
):
    df = pd.read_csv(BytesIO(await file.read()),
                     na_values=["?", "NA", "", "null", "None", "No Info"])

    result = run_pipeline_from_df(df, scale_columns=scale_columns)

    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, "w", ZIP_DEFLATED) as zf:
        zf.writestr("cleaned.csv", result["cleaned_df"].to_csv(index=False))
        zf.writestr("audit.json", json.dumps(result["audit"], indent=2))

    zip_buffer.seek(0)

    return StreamingResponse(zip_buffer, media_type="application/zip")