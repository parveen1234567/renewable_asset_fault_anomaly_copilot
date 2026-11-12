# Renewable Asset Fault & Anomaly Detection Copilot

A small, runnable decision-support demo that screens renewable-asset telemetry for unusual patterns and shows evidence-based operator checks.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn backend.app:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) for the UI or [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for the API.

## What it does

- Groups telemetry by asset and checks robust deviations in temperature and vibration.
- Compares solar daylight power with that asset's typical power-to-irradiance ratio.
- Uses a per-asset Isolation Forest to add multivariate outlier flags.
- Returns the evidence, suggestions for operator checks, a severity label, and limitations.
- Has no external LLM, secrets, or internet dependency at runtime.

The provided CSV contains 240 synthetic rows across `SOLAR_INV_01` and `WTG_07`; it has no ground-truth anomaly labels. The app is a screening prototype. It is not a fault diagnosis, safety system, or maintenance dispatch tool.

## API at a glance

- `GET /api/health` — service health
- `GET /api/demo` — data and asset summary
- `POST /api/run` — analyze all assets or one selected asset

Example request:

```json
{"asset_id": "SOLAR_INV_01", "text": ""}
```

## Test and run the synthetic stress check

```powershell
python -m unittest discover -s tests -v
python -m scripts.evaluate_detector
```

The stress check injects two artificial anomalies. This checks that selected failure patterns trigger alerts; it is not a substitute for evaluation against labelled operating history.

## Understand and explain the project

Read [docs/PROJECT_GUIDE.md](docs/PROJECT_GUIDE.md) for a step-by-step explanation of the architecture, detector logic, output fields, evaluation, limitations, presentation talking points, and Railway deployment.

## Deploy to Railway

Push this project to a GitHub repository, create a Railway project from that repository, and deploy from the repository root. Railway can use the included `Procfile`; it starts `uvicorn backend.app:app` on the platform-provided port. Once deployed, verify `/`, `/api/health`, and `/docs`, then record your live URL. Deployment requires your own Railway account and access; no credentials are stored in this project.
