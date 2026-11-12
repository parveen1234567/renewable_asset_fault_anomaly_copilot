# Renewable Asset Fault & Anomaly Detection Copilot

<p align="center">
  <strong>A renewable-energy operations demo that flags unusual telemetry and gives operators evidence to review.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white" alt="Python 3.11">
  <img src="https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/ML-scikit--learn-F7931E?logo=scikitlearn&logoColor=white" alt="scikit-learn">
  <img src="https://img.shields.io/badge/UI-HTML%20%2F%20CSS%20%2F%20JS-E34F26?logo=html5&logoColor=white" alt="HTML, CSS, and JavaScript">
  <img src="https://img.shields.io/badge/Railway-ready%20to%20deploy-8B5CF6?logo=railway&logoColor=white" alt="Railway deployment configuration included">
</p>

<p align="center">
  <a href="https://github.com/parveen1234567/renewable_asset_fault_anomaly_copilot">Source Code</a>
  &nbsp;•&nbsp;
  <a href="./docs/PROJECT_GUIDE.md">Deep Project Guide</a>
  &nbsp;•&nbsp;
  <a href="#api-reference">API Reference</a>
  &nbsp;•&nbsp;
  <a href="#deploy-to-railway">Railway Deployment</a>
</p>

> **Deployment status:** The application is Railway-ready, but no public Railway URL has been configured yet. Alerts are decision-support signals, not confirmed diagnoses.

## 🚀 Product Overview

Renewable Asset Fault & Anomaly Detection Copilot is a small, runnable prototype for reviewing solar and wind telemetry. It combines domain-informed rules with an unsupervised outlier model, then presents the observations, reasons, and suggested next checks in a browser dashboard.

The bundled CSV makes the project runnable without credentials or external data services. The dataset is synthetic and has no verified fault labels, so the project demonstrates a workflow rather than production accuracy.

## ✨ Key Features

- **Asset-level analysis:** solar and wind telemetry are analyzed separately.
- **Explainable sensor checks:** robust deviations highlight unusual temperature and vibration readings.
- **Solar context:** the power-versus-irradiance check runs in daylight, avoiding alerts for expected night-time zero output.
- **Multivariate screening:** Isolation Forest can flag unusual combinations of sensor values.
- **Operator-facing results:** alerts include observed telemetry, evidence, severity, and suggested verification steps.
- **Browser dashboard and API:** select an asset in the UI or call the FastAPI endpoints directly.
- **Reproducible demo:** unit tests and a synthetic stress check are included.

## 🧭 How It Works

```text
Browser dashboard
      │  POST /api/run
      ▼
FastAPI backend ── reads ──► data/asset_telemetry.csv
      │
      ├── robust temperature / vibration checks
      ├── daylight solar power comparison
      └── per-asset Isolation Forest
      │
      ▼
Evidence, review alerts, and recommended checks
```

### Detection approach

1. **Robust deviation:** compares temperature and vibration with the asset's median and median absolute deviation. A robust deviation of at least `3.5` creates a rule alert.
2. **Solar power comparison:** for solar assets during daylight (irradiance at least `150 W/m²`), compares measured power with a median historical power-to-irradiance baseline. A deficit of at least `40%` creates a review alert.
3. **Isolation Forest:** fits separately for each asset to find unusual combinations across the sensor values. Its `5%` contamination setting controls the approximate outlier fraction; it is **not** a probability of failure.
4. **Explanation:** returns the measured values, rule evidence when available, and generic checks for an operator. It does not assert a root cause.

Thresholds are demonstration settings, not OEM operating limits.

## 📊 Dataset

The included [telemetry CSV](./data/asset_telemetry.csv) contains **240 synthetic rows** for two demo assets: `SOLAR_INV_01` and `WTG_07`.

| Field | Meaning |
|---|---|
| `timestamp_id` | Sequential row/time identifier |
| `asset_id` | Demo asset name |
| `hour` | Hour of day |
| `irradiance_wm2` | Solar irradiance in W/m² |
| `wind_speed_ms` | Wind speed in m/s |
| `temperature_c` | Temperature in °C |
| `vibration_mm_s` | Vibration in mm/s |
| `power_mw` | Measured power in MW |

There is no ground-truth anomaly label. Treat detected rows as **review candidates**, not known faults.

## 🛠️ Run Locally

From the project directory in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn backend.app:app --reload
```

Open:

- Dashboard: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Interactive API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health check: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

To run the checks:

```powershell
python -m unittest discover -s tests -v
python -m scripts.evaluate_detector
```

## 🔌 API Reference

| Method | Route | Description |
|---|---|---|
| `GET` | `/` | Serves the dashboard |
| `GET` | `/api/health` | Confirms the API is responding |
| `GET` | `/api/demo` | Returns the data row count and asset list |
| `POST` | `/api/run` | Analyzes all assets or one selected asset |

Example request to analyze one asset:

```json
{
  "asset_id": "SOLAR_INV_01",
  "text": ""
}
```

Use `"asset_id": null` to analyze all assets. The `text` field is currently a placeholder for an operator note and does not affect detection.

Alerts return the asset and row, severity, reasons, telemetry, available rule evidence, recommended checks, and the Isolation Forest flag/score. The score is not a calibrated risk probability.

## 🧪 Evaluation

The automated tests cover expected night-time solar behavior, injected daylight power loss, high temperature/vibration, and invalid input.

The synthetic stress script currently detects **2 of 2 hand-crafted injected examples**. On the unlabelled bundled dataset it produces **12 review alerts**. That is not a measured false-positive rate: the dataset has no verified labels, and the injected cases are not a representative benchmark.

For trustworthy evaluation, use reviewed fault labels and later-in-time holdout data. Report precision/recall, false alerts per asset per day, detection delay, and operator feedback. See the [deep project guide](./docs/PROJECT_GUIDE.md) for the evaluation caveats and production recommendations.

## 🚧 Limitations and Safety

- Synthetic, small dataset with no verified normal/fault labels.
- Simple solar power baseline that does not account for weather, curtailment, clipping, degradation, or OEM operating limits.
- Isolation Forest is fit on the data being analyzed in this demo; this is not a production time-separated training/evaluation workflow.
- Alerts and recommendations require operator review and must not replace site procedures or safety controls.
- No maintenance-manual retrieval (RAG), external LLM, authentication, or production monitoring is included.

## ☁️ Deploy to Railway

The repository includes a [Procfile](./Procfile) and a [.python-version](./.python-version) file for Railway deployment.

1. In Railway, create a new project and deploy from the GitHub repository.
2. Select the repository root as the service root.
3. Allow Railway to install dependencies from `requirements.txt` and start the web process from the `Procfile`; it binds to Railway's provided `$PORT`.
4. After deployment, verify `/`, `/api/health`, `/api/demo`, `/api/run`, and `/docs`.
5. Add the generated public URL above once the service is deployed and verified.

**This project has not yet been deployed to Railway.** Deployment requires access to the owner's Railway account.

## 📁 Project Structure

```text
backend/
  app.py                 FastAPI routes and dataset loading
  detector.py            Detection rules and Isolation Forest
data/
  asset_telemetry.csv    Synthetic runnable dataset
docs/
  PROJECT_GUIDE.md       Detailed explanation and presentation guide
frontend/
  index.html             Browser dashboard
scripts/
  evaluate_detector.py   Synthetic anomaly stress check
tests/
  test_detector.py       Focused behavior tests
Procfile                Railway web process
requirements.txt        Python dependencies
```
