# Renewable Asset Fault & Anomaly Detection Copilot

<p align="center">
  <strong>An operator-focused demo for screening renewable energy telemetry, surfacing unusual readings, and showing what to verify next.</strong>
</p>

<p align="center">
  <img alt="Python 3.11" src="https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white">
  <img alt="scikit-learn" src="https://img.shields.io/badge/ML-scikit--learn-F7931E?logo=scikitlearn&logoColor=white">
  <img alt="HTML CSS JavaScript" src="https://img.shields.io/badge/UI-HTML%20%2F%20CSS%20%2F%20JavaScript-E34F26?logo=html5&logoColor=white">
  <img alt="Railway deployment live" src="https://img.shields.io/badge/Railway-live-8B5CF6?logo=railway&logoColor=white">
</p>

<p align="center">
  <a href="https://renewableassetfaultanomalycopilot-production-1681132b.up.railway.app">Live Application</a>
  &nbsp;•&nbsp;
  <a href="https://github.com/parveen1234567/renewable_asset_fault_anomaly_copilot">Source Code</a>
  &nbsp;•&nbsp;
  <a href="./docs/PROJECT_GUIDE.md">Detailed Project Guide</a>
  &nbsp;•&nbsp;
  <a href="#api-reference">API Reference</a>
  &nbsp;•&nbsp;
  <a href="#deploy-to-railway">Railway Deployment</a>
</p>

> **Project status:** The Railway app is publicly deployed and verified. Model results are review signals—not diagnoses or maintenance instructions.

---

## 🚀 Project Overview

Renewable Asset Fault & Anomaly Detection Copilot is a compact decision-support prototype for reviewing solar and wind asset telemetry. It combines simple energy-domain checks with an unsupervised anomaly detector, then returns the evidence and suggested verification steps through a FastAPI service and browser dashboard.

The project is designed to make the reasoning visible:

```text
Telemetry → Asset-specific checks → Review alert + evidence → Operator verification
```

It is **not** an autonomous fault-diagnosis or safety system. The included data is synthetic and has no verified fault labels; the demo demonstrates an end-to-end workflow without claiming field accuracy.

### Intended users

| User | How the demo may help |
|---|---|
| Operations personnel | Review unusual sensor readings and nearby context |
| Reliability or maintenance engineers | Inspect potential patterns and discuss suitable site-specific thresholds |
| Data and ML practitioners | Explore a small time-series screening baseline and its evaluation gaps |
| Developers | See a simple Python API connected to a browser interface |

These are intended audiences, not users or customers of a deployed production service.

---

## 💡 The Decision-Support Workflow

1. The dashboard loads the available assets and the size of the bundled dataset.
2. The operator analyzes all assets or selects a single asset.
3. The backend validates telemetry and evaluates each asset separately.
4. Domain rules and Isolation Forest identify candidate rows.
5. The dashboard shows severity, observations, rule evidence, and suggested checks.
6. A qualified operator verifies the readings against site conditions and approved procedures.

An alert can indicate an unusual pattern, a sensor issue, a normal operating condition not represented by the baseline, or an actual asset concern. The demo cannot distinguish those possibilities with certainty.

---

## ✨ Capabilities

### Telemetry screening

- Validates the expected CSV columns and numeric sensor values.
- Processes each asset independently rather than mixing solar and wind behavior.
- Rejects malformed or undersized analysis input with an API error.

### Energy-domain rules

- Uses robust deviations to flag unusual temperature and vibration readings.
- Compares solar output with a simple daylight power-to-irradiance baseline.
- Avoids treating solar zero-power readings at night as a daylight power deficit.
- Includes observed values and comparison evidence in rule-based alerts.

### Multivariate anomaly detection

- Standardizes the telemetry values and fits a per-asset Isolation Forest.
- Uses the model as a screening signal alongside the explicit rules.
- Does not interpret the model score as a failure probability.

### Operator-facing interface

- Serves a responsive dashboard from the FastAPI application.
- Supports all-asset analysis or filtering to a known asset.
- Shows the alert reason, current telemetry, and suggested follow-up checks.
- Displays a clear demo-data and operator-review notice.

### Reproducible project

- Runs using only the supplied dataset.
- Does not need an external LLM, API key, or document service.
- Includes focused unit tests and a synthetic stress-test script.
- Includes a detailed explanation in [`docs/PROJECT_GUIDE.md`](./docs/PROJECT_GUIDE.md).

---

## 🏗️ Architecture

### System view

~~~mermaid
flowchart LR
    OP["Operator"] --> UI["Browser dashboard<br/>HTML / CSS / JavaScript"]
    UI -->|"GET /api/demo<br/>POST /api/run"| API["FastAPI application"]
    API --> CSV["Bundled telemetry CSV"]
    API --> DET["Per-asset detector"]
    DET --> RULES["Robust sensor rules<br/>Solar power comparison"]
    DET --> IF["Isolation Forest"]
    RULES --> OUT["Alerts + evidence + limitations"]
    IF --> OUT
    OUT --> API
    API --> UI
~~~

### Request flow

~~~text
Browser
   │
   ├── GET /api/demo ──► Asset list and dataset summary
   │
   └── POST /api/run ──► FastAPI request validation
                             │
                             ├── Load CSV
                             ├── Select requested asset(s)
                             ├── Run domain rules
                             ├── Fit Isolation Forest per asset
                             └── Return alert evidence and limitations
~~~

### Architecture at a glance

| Layer | Responsibility | Technology |
|---|---|---|
| User interface | Asset selection and alert review | HTML, CSS, browser JavaScript |
| API | Health, data summary, and analysis routes | FastAPI, Pydantic |
| Data handling | CSV loading and numeric checks | pandas, NumPy |
| Detection | Robust deviations and multivariate screening | Python, scikit-learn |
| Demo data | Self-contained telemetry input | CSV |
| Deployment entry point | Web process bound to the platform port | Procfile, Railway |

---

## 🧠 Detection Method

The implementation is in [`backend/detector.py`](./backend/detector.py). It returns review candidates, not fault diagnoses.

### 1. Input validation and grouping

The detector checks required fields, numeric sensor values, finite values, and whole-number `timestamp_id` and `hour` values. It groups data by `asset_id`; each analyzed asset needs at least 20 rows for the baseline model.

### 2. Temperature and vibration deviations

For each sensor, it compares a reading with the asset's median using a median-absolute-deviation score:

~~~text
robust deviation = |observed - median| / (1.4826 × MAD)
~~~

If MAD is zero, the code falls back to the interquartile range; for effectively constant values, a non-median value is treated as an extreme deviation.

- A robust deviation of **3.5 or greater** produces a rule alert.
- At **5.0 or greater**, the sensor rule is marked high severity; otherwise it is medium.
- The explanation says whether the reading is high or low compared with the asset's observed median.

These are demonstration thresholds, not operating limits from an equipment manufacturer.

### 3. Solar daylight power comparison

For an asset whose ID begins with `SOLAR`, the detector considers rows with irradiance of at least **150 W/m²**. It estimates a reference power using the median power-to-irradiance ratio from the asset's daylight data:

~~~text
estimated power = irradiance × median(daylight power / irradiance)
~~~

A measured output at least **40% below** that estimate creates a review alert; a deficit of at least **70%** is high severity. This simplified baseline does not model weather, panel temperature, shading, degradation, clipping, curtailment, or nameplate capacity.

### 4. Isolation Forest

The detector standardizes five sensor columns and fits an Isolation Forest separately for each asset. The current demo uses 200 trees, a fixed random seed, and a contamination setting of `0.05`.

Contamination guides the model's approximate flagged fraction. It is not a probability that the asset is faulty, and the raw model score is not calibrated as a risk level. In this demo, the model is fit on the data being analyzed; a production system should train on earlier time periods and evaluate on later periods.

### 5. Explanation and severity

Rule alerts include observed and reference values where available. If the model flags a row without an explicit rule, the output only says its multivariate telemetry combination is unusual and recommends review. Severity reflects the strongest explicit rule; model-only alerts are low severity.

Recommended checks are generic prompts. They do not replace site procedures, safety controls, or an engineer's assessment.

---

## 📊 Dataset

[`data/asset_telemetry.csv`](./data/asset_telemetry.csv) contains **240 synthetic rows**: 120 rows for `SOLAR_INV_01` and 120 for `WTG_07`.

| Column | Description | Unit / format |
|---|---|---|
| `timestamp_id` | Sequential row/time identifier | Integer |
| `asset_id` | Demo asset name | Text |
| `hour` | Hour value repeated across the sample | 0–23 |
| `irradiance_wm2` | Solar irradiance | W/m² |
| `wind_speed_ms` | Wind speed | m/s |
| `temperature_c` | Temperature reading | °C |
| `vibration_mm_s` | Vibration reading | mm/s |
| `power_mw` | Measured power | MW |

There is no ground-truth `normal`/`fault` label. The data is not a validated operating envelope and should not be used to set real-world maintenance thresholds.

---

## 🔌 API Reference

### Live API

- **Interactive Swagger docs:** [Open the deployed API documentation](https://renewableassetfaultanomalycopilot-production-1681132b.up.railway.app/docs)
- **Health check:** [Check API status](https://renewableassetfaultanomalycopilot-production-1681132b.up.railway.app/api/health)
- **Demo data summary:** [View assets and row count](https://renewableassetfaultanomalycopilot-production-1681132b.up.railway.app/api/demo)

| Method | Route | Description |
|---|---|---|
| `GET` | `/` | Serves the browser dashboard |
| `GET` | `/api/health` | Returns service health |
| `GET` | `/api/demo` | Returns the case summary, row count, and asset list |
| `POST` | `/api/run` | Analyzes all assets or one selected asset |
| `GET` | `/docs` | Interactive OpenAPI / Swagger documentation |

### Example request

Analyze one asset:

~~~json
{
  "asset_id": "SOLAR_INV_01",
  "text": ""
}
~~~

Set `asset_id` to `null` or omit it to analyze all assets. The `text` field is retained as a placeholder for an operator note; it currently does not affect detection. An unknown asset returns HTTP `404`; invalid or insufficient telemetry returns HTTP `422`.

### Response shape

The `/api/run` response includes:

| Field | Meaning |
|---|---|
| `total_rows` | Number of rows analyzed |
| `analyzed_assets` | Asset IDs included in this run |
| `alert_count` | Number of review candidates |
| `alerts` | Per-row severity, reasons, evidence, telemetry, and checks |
| `model` | Detector name, rule threshold, and model settings |
| `limitations` | Important interpretation and data caveats |

Each alert includes `asset_id`, `timestamp_id`, `hour`, `severity`, `reasons`, `recommended_checks`, `evidence`, `model_flag`, `model_score`, and `telemetry`.

### Try the API with PowerShell

With the app running locally:

~~~powershell
Invoke-RestMethod http://127.0.0.1:8000/api/demo

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/run `
  -ContentType "application/json" `
  -Body '{"asset_id":"SOLAR_INV_01","text":""}'
~~~

---

## 🧪 Testing and Evaluation

### Automated tests

Run the focused regression tests:

~~~powershell
python -m unittest discover -s tests -v
~~~

The tests cover:

- Nighttime solar zero output is not treated as a daylight power deficit.
- Injected daylight solar power loss produces an explained alert.
- Synthetic high temperature and vibration produce evidence.
- Missing required columns fail with an actionable validation error.

### Synthetic stress check

Run:

~~~powershell
python -m scripts.evaluate_detector
~~~

The script injects two artificial cases and checks whether those rows are detected. In the latest local run, the two injected examples were detected (**2/2**); the baseline detector returned **12 review alerts** on the unlabelled 240-row dataset.

These figures are not accuracy or false-positive metrics:

- The bundled rows have no verified labels.
- Hand-crafted injection cases are not a representative failure benchmark.
- The baseline alerts cannot be classified as true or false without expert-reviewed labels.
- The demo fits the unsupervised model on the data being analyzed, not a held-out future period.

For a meaningful operational evaluation, use reviewed fault events and time-separated train/test periods. Measure precision, recall, PR-AUC, false alerts per asset per day, detection delay, and operator feedback. Select thresholds with asset engineers based on the cost of missed faults and nuisance alarms.

---

## 🔒 Safety, Security, and Production Gaps

This repository is a local/demo prototype:

- It has no authentication or authorization.
- It has no production telemetry ingestion, alert history, or audit trail.
- It has no maintenance-manual retrieval (RAG) or external LLM.
- It does not detect stale or stuck sensors as a dedicated workflow.
- It does not have a production monitoring, drift-management, or retraining process.
- It has no validated failure labels, OEM thresholds, or site-specific operating procedures.

Do not expose it to sensitive operational data or rely on its alerts to make safety-critical decisions without an appropriate security and engineering review.

### Production readiness next steps

1. Integrate quality-checked time-series data with real timestamps and asset metadata.
2. Validate units, operating states, event labels, and thresholds with asset engineers.
3. Train on earlier periods and test on later periods; prevent data leakage across the split.
4. Add authentication, authorization, secure network configuration, and input limits.
5. Add sensor-health handling, alert deduplication, acknowledgements, and audit history.
6. Monitor false alarms, missed events, drift, model changes, and operator feedback.
7. If manuals are added, retrieve approved, versioned passages and cite them; keep retrieved evidence separate from model evidence.

---

## 🛠️ Run Locally

The project targets Python 3.11, as recorded in [`.python-version`](./.python-version). From the repository root in PowerShell:

~~~powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn backend.app:app --reload
~~~

Open the following local URLs:

| Service | URL |
|---|---|
| Dashboard | [http://127.0.0.1:8000](http://127.0.0.1:8000) |
| Swagger / OpenAPI UI | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) |
| API health | [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health) |
| Data and asset summary | [http://127.0.0.1:8000/api/demo](http://127.0.0.1:8000/api/demo) |

If activating the virtual environment is restricted by local PowerShell policy, run its interpreter directly:

~~~powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --reload
~~~

---

## ☁️ Railway Deployment

The app is deployed from the GitHub repository and is publicly reachable:

| Resource | URL |
|---|---|
| Live dashboard | [https://renewableassetfaultanomalycopilot-production-1681132b.up.railway.app](https://renewableassetfaultanomalycopilot-production-1681132b.up.railway.app) |
| API health | [`/api/health`](https://renewableassetfaultanomalycopilot-production-1681132b.up.railway.app/api/health) |
| Data and assets | [`/api/demo`](https://renewableassetfaultanomalycopilot-production-1681132b.up.railway.app/api/demo) |
| Interactive API docs | [`/docs`](https://renewableassetfaultanomalycopilot-production-1681132b.up.railway.app/docs) |

The public dashboard, health route, data summary, and API docs have been checked. The repository includes a [`Procfile`](./Procfile) that binds the web process to Railway's provided `$PORT` and a [`.python-version`](./.python-version) for Python 3.11.

The API has no authentication and currently uses synthetic demo data. Do not connect sensitive operational data or treat the alerts as production maintenance decisions.

---

## 📁 Repository Structure

~~~text
renewable_asset_fault_anomaly_copilot/
├── backend/
│   ├── app.py                  FastAPI routes and dataset loading
│   └── detector.py             Validation, rules, Isolation Forest, explanations
├── data/
│   └── asset_telemetry.csv     Synthetic example telemetry
├── docs/
│   └── PROJECT_GUIDE.md        Deep explanation and presentation guide
├── frontend/
│   └── index.html              Browser dashboard
├── scripts/
│   └── evaluate_detector.py    Synthetic stress check
├── tests/
│   └── test_detector.py        Focused behavior tests
├── .gitignore
├── .python-version
├── Procfile                    Railway web process
├── requirements.txt
└── README.md
~~~

---

## 🧭 Design Decisions

### Why use both rules and Isolation Forest?

Rules make important domain assumptions explicit and provide concrete evidence for solar daylight power and robust temperature/vibration deviations. Isolation Forest adds a multivariate signal for rows whose combination of readings is unusual. The two signals complement each other, but neither establishes a fault.

### Why no LLM or RAG?

The repository does not include maintenance manuals or a labelled diagnostic knowledge base. An LLM-generated diagnosis would add unsupported claims. The current demo therefore returns deterministic checks and model evidence. If approved documents are added later, retrieval should return cited source passages and revisions.

### Why synthetic anomaly injection?

There are no labelled incidents in the bundled file. Injected values let tests check that certain known examples trigger the expected rules, but do not substitute for evaluation on verified historical events.

---

## 🗺️ Possible Next Steps

Future work could include:

- A validated dataset with expert-reviewed event labels.
- Time-aware training, evaluation, and drift monitoring.
- Site/OEM-approved thresholds and asset operating modes.
- Real timestamps, sensor quality checks, and missing-data handling.
- Alert acknowledgement and operator feedback.
- Approved maintenance-document retrieval with citations.
- Authentication, access controls, and a secured production deployment.

These are future enhancements, not capabilities currently implemented.

---

## 📚 Learn More

For a detailed walkthrough of the detection logic, example API requests, limitations, evaluation approach, Railway instructions, and presentation notes, see [`docs/PROJECT_GUIDE.md`](./docs/PROJECT_GUIDE.md).

**Repository:** [parveen1234567/renewable_asset_fault_anomaly_copilot](https://github.com/parveen1234567/renewable_asset_fault_anomaly_copilot)
