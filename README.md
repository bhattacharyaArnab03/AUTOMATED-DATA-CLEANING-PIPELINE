# Automated Data Cleaning Pipeline

A modular Python project for safe, intelligent, and user-controlled automated data cleaning for tabular datasets.

## Overview

This project profiles a dataset, infers column types, detects missing values and inconsistencies, makes column-wise cleaning decisions, and executes transformations with a strong focus on preserving valid data.

The current implementation is designed to be **non-destructive**:

- clean numeric columns are left untouched unless modification is required
- binary columns are preserved exactly
- names, addresses, and date-like strings are preserved as-is
- categorical values are normalized and label encoded when appropriate
- numeric scaling is applied **only** to user-selected columns
- every run produces audit logs and JSON reports

## Key Features

- **Data profiling** with type inference, missingness analysis, statistics, and pattern detection
- **Decision engine** that fuses multiple signals before choosing a cleaning action
- **Safe cleaning executor** that avoids unnecessary data distortion
- **Binary-column protection** so 0/1 features are not accidentally altered
- **Semantic text handling** for names, addresses, and dates
- **User-controlled scaling** using Min-Max normalization on selected columns
- **Audit trail** for transparency and debugging
- **Console runner** for local use
- **FastAPI service** for upload-and-clean workflows
- **CSV-to-ZIP output** that includes cleaned data plus reports

## Project Structure

```text
AUTOMATED-DATA-CLEANING-PIPELINE/
├── app/
│   ├── __init__.py
│   └── main.py
├── configs/
│   └── default.yaml
├── examples/
│   ├── adult.csv
│   ├── diabetes_prediction_dataset.csv
│   ├── healthcare_dataset.csv
│   └── run_*.py
├── reports/
├── src/
│   └── cleaner/
│       ├── anomaly_detector.py
│       ├── cleaning_executor.py
│       ├── decision_engine.py
│       ├── domain_rules.py
│       ├── pattern_detection.py
│       ├── pipeline_service.py
│       ├── profiler.py
│       ├── quality_checks.py
│       ├── strategy_selector.py
│       ├── type_inference.py
│       └── validator.py
├── run_pipeline.py
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## How It Works

### 1. Profiling
The profiler inspects each column and generates a structured report containing:

- inferred type
- missing value statistics
- numeric summary statistics
- categorical frequency statistics
- outlier / anomaly signals
- quality flags

### 2. Decision Making
The decision engine combines multiple signals such as:

- missingness
- skewness
- anomaly ratio
- cardinality
- pattern consistency

It then decides how each column should be treated.

### 3. Cleaning Execution
The executor applies the decision conservatively:

- missing categorical values are imputed using mode
- ordinary categorical fields are label encoded
- human-readable text is preserved
- date-like fields are preserved
- numeric columns remain unchanged unless missing values need imputation
- selected numeric columns can be scaled to `[0, 1]`

### 4. Reporting
Each execution generates:

- cleaned dataset
- cleaning audit report
- final profile report
- decision report

## FastAPI Service

The project includes a FastAPI-based interface for browser-based upload and cleaning.

### Endpoints

- `GET /`  
  Opens the web UI for file upload, column selection, and cleaning.

- `GET /health`  
  Returns service health status.

- `POST /columns`  
  Reads a CSV file and returns the column list for the scaling dropdown.

- `POST /clean`  
  Accepts a CSV upload, selected scaling columns, and returns a ZIP file containing:
  - `cleaned.csv`
  - `audit.json`
  - `profile.json`
  - `decision.json`

### UI Behavior

- Upload a CSV file
- Click **Load Columns**
- Select the numeric columns you want to scale
- Click **Clean & Download**

## Console Runner

The same pipeline can be executed from the terminal using `run_pipeline.py`.

### Example

```bash
python run_pipeline.py --input examples/adult.csv --use-config --scale-column fnlwgt capital.loss
```

### Notes

- Use `--scale-column` followed by one or more column names
- Multiword column names should be wrapped in quotes when needed
- Columns not selected for scaling remain untouched unless missing-value handling is required

### Example with a multiword column

```bash
python run_pipeline.py --input examples/healthcare_dataset.csv --use-config --scale-column "Billing Amount"
```

## Installation

### 1. Create and activate a virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

For development tools:

```bash
pip install -r requirements-dev.txt
```

## Running the Project

### Console mode

```bash
python run_pipeline.py --input examples/adult.csv --use-config --scale-column fnlwgt capital.loss
```

### FastAPI mode

```bash
python -m uvicorn app.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/
```

## Configuration

The file `configs/default.yaml` stores domain rules and configurable missing-value tokens.

Typical uses:

- define allowed ranges for known columns
- add dataset-specific missing tokens such as `"No Info"`
- keep the core pipeline generic while allowing optional dataset rules

## Design Principles

- **Preserve valid data**
- **Transform only when needed**
- **Keep pipeline modular**
- **Keep actions explainable**
- **Prefer explicit user control over automatic distortion**

## Input / Output Summary

### Input
- CSV file with tabular data

### Output
- cleaned dataset
- audit log
- profile summary
- decision summary

## Example Use Cases

- healthcare datasets
- census / demographic data
- financial tabular data
- student / survey datasets
- mixed-type structured CSVs

## Limitations

- This project is optimized for structured tabular data
- Free-form natural language cleaning is limited
- Highly domain-specific rules may still need custom entries in the config file
- It is not a full replacement for domain expert review in critical workflows

## Future Work

- reversible transformations
- saved encoders/scalers for inference mode
- richer datetime feature extraction
- automatic column role detection
- drift detection
- interactive dashboards
- model-ready pipeline export

## Tech Stack

- Python
- pandas
- scikit-learn
- FastAPI
- Uvicorn
- PyCharm
- python-docx

## Acknowledgements / Literature Inspiration

This project builds on ideas from automated preprocessing, workflow optimization, explainable cleaning, anomaly detection, and multi-signal decision systems discussed in the literature survey.
