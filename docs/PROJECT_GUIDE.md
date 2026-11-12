# Project guide: build, reason about, and present the demo

This guide explains what the project now does, why the baseline was chosen, how to run it, what its results mean, and what you should say when presenting it. The application is deliberately small enough to understand end-to-end.

## 1. Start the project

From the project directory in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn backend.app:app --reload
```

Then open:

- `http://127.0.0.1:8000` for the dashboard
- `http://127.0.0.1:8000/docs` for interactive API documentation
- `http://127.0.0.1:8000/api/health` to check the service

If PowerShell prevents environment activation, either allow activation for your user according to your organization's policy, or run the venv interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --reload
```

Run the automated checks and the synthetic stress test in a second terminal:

```powershell
python -m unittest discover -s tests -v
python -m scripts.evaluate_detector
```

## 2. Understand the problem and data

The goal is not to claim that a model can diagnose equipment from a handful of numbers. The goal is to surface telemetry intervals that look unusual and give an operator a traceable reason to investigate.

The included `data/asset_telemetry.csv` has 240 records: 120 rows for a solar inverter and 120 for a wind turbine. It contains `timestamp_id`, `asset_id`, `hour`, irradiance, wind speed, temperature, vibration, and power. It is a small synthetic demonstration dataset and has no labelled `normal`/`fault` target.

That means a standard accuracy, recall, or production false-alarm rate cannot be honestly calculated from the bundled data alone. The values in it are not a validated operating envelope, and there is no guarantee they represent a real site, OEM thresholds, sensor quality, seasonal changes, curtailment, maintenance, or all operating modes.

The detector handles one important energy-domain example explicitly: zero solar output at night is expected. Its solar power check only runs when irradiance is at least 150 W/m². This avoids treating every zero-power record as a solar fault.

## 3. Files and responsibilities

| File | Responsibility |
|---|---|
| `backend/app.py` | FastAPI routes, request validation, data loading, and API error responses |
| `backend/detector.py` | Data validation, sensor rules, Isolation Forest, explanations, and response structure |
| `frontend/index.html` | Dashboard for asset selection and alert review |
| `data/asset_telemetry.csv` | Self-contained synthetic telemetry input |
| `tests/test_detector.py` | Regression tests for normal night behavior, injected faults, and invalid input |
| `scripts/evaluate_detector.py` | Reproducible, hand-crafted anomaly stress check |
| `Procfile` | Railway web process command |
| `.python-version` | Selects Python 3.11 for a predictable deployment runtime |

## 4. How one analysis request flows

1. The dashboard calls `GET /api/demo` to get the asset list.
2. The operator chooses one asset or all assets and clicks **Analyze telemetry**.
3. The browser sends `POST /api/run`, for example `{"asset_id": "SOLAR_INV_01", "text": ""}`.
4. FastAPI reads the bundled CSV. Unknown assets receive an HTTP 404; invalid telemetry is returned as an HTTP 422 with an explanation.
5. The detector validates required columns and numeric sensor values, then analyzes each asset separately.
6. It collects domain-rule evidence and the Isolation Forest flag. Only flagged rows are returned.
7. The UI displays severity, row/hour, reasons, recommendations, and the measured sensor values. The user must verify those values against site context.

Useful requests:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/demo

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/run `
  -ContentType "application/json" `
  -Body '{"asset_id":"SOLAR_INV_01","text":""}'
```

The API also accepts `{"asset_id": null, "text": ""}` to analyze every asset. The `text` field is currently retained as an operator-note placeholder; it does not change model behavior.

## 5. Detector logic, in detail

### A. Asset-by-asset baselines

Solar and wind assets behave differently, so rows are grouped by `asset_id`; the model is not trained across both asset types together. Each group needs at least 20 records for the Isolation Forest baseline.

### B. Robust sensor deviations

For temperature and vibration, the detector calculates each sensor's median and median absolute deviation (MAD). It uses the robust score:

```text
robust deviation = |observed value - median| / (1.4826 * MAD)
```

MAD is less sensitive to extreme values than standard deviation. When MAD is zero, the code falls back to the interquartile range. If the observations are effectively constant, any non-median value is treated as an extreme deviation.

A robust deviation of at least 3.5 adds an alert reason. At 5.0 or above, that rule is marked high severity; otherwise it is medium. These are demo thresholds, not industry or OEM limits. A high vibration may merit inspection but does not establish a mechanical fault; temperature can also be affected by load, ambient conditions, cooling, or sensor quality.

### C. Solar power versus irradiance

For an asset whose ID begins with `SOLAR`, the baseline power-to-irradiance ratio is the median of daylight rows (irradiance at least 150 W/m²). For each daylight row, estimated power is:

```text
estimated power = irradiance * median(daylight power / irradiance)
```

If observed output is at least 40% below that estimate, the detector recommends checking inverter status, curtailment/grid events, and sensors. A deficit of 70% or more is marked high severity. This is intentionally a simple comparison; it does not account for panel temperature, shading, degradation, inverter clipping, weather, curtailment, or nameplate capacity.

### D. Isolation Forest

The detector standardizes the five sensor columns and fits a scikit-learn Isolation Forest per asset. It uses 200 trees, a fixed random seed for repeatability, and a 5% contamination setting. The model helps find combinations of readings that look unusual even when no individual rule crosses its threshold.

`contamination=0.05` is an approximate expected outlier fraction used by the algorithm to set a decision threshold. It is **not** a probability of failure, a confidence score, or a target production alarm rate. The response includes a raw model score for sorting/context, but that score is not calibrated as a risk probability.

If the model flags a row without an explicit rule, the API says that its telemetry combination is unusual and recommends review. The output never presents that as a confirmed cause.

### E. Severity and recommended checks

The response severity is the highest severity reached by any explicit rule on that row. A model-only flag is low. Recommendations are generic next checks, not instructions to dispatch or operate equipment. Follow the site safety process, alarm hierarchy, and approved maintenance procedures.

## 6. Read the API response

Each alert includes:

- `asset_id`, `timestamp_id`, `hour`: where the row belongs in this demo data
- `severity`: rule-derived triage label; not a probability
- `reasons`: plain-language descriptions of the triggered rules/model signal
- `evidence`: observed values and comparison values used by explicit rules
- `recommended_checks`: suggestions for verification
- `telemetry`: sensor values for quick operator review
- `model_flag`, `model_score`: Isolation Forest output; score is uncalibrated

Top-level fields describe analyzed rows/assets, alert count, model settings, and limitations. The UI uses those values rather than inventing additional diagnostic language.

## 7. Evaluation: what the tests prove—and do not prove

Run:

```powershell
python -m unittest discover -s tests -v
python -m scripts.evaluate_detector
```

The unit tests check several specific behaviors: a nighttime zero-power solar row is not given the daylight power-deficit reason; an artificial low-output daylight row produces evidence and recommended checks; a synthetic high-temperature/high-vibration wind row produces a high-severity alert; and missing columns fail clearly.

The evaluation script makes a baseline run on the bundled rows, injects two artificial test cases, and checks whether those two injected timestamps are flagged. It prints the number of unlabelled baseline alerts and injection detections.

This is a **stress test**, not a benchmark:

- The injected values were chosen by the author, not sampled from verified failure events.
- Baseline alerts cannot be called false positives because the original rows have no verified labels.
- The injected cases are added before re-fitting the unsupervised model, so this does not represent a clean train/test split.
- It cannot demonstrate field reliability, alert lead time, false-alarm rate, or avoided downtime.

For a credible evaluation, obtain reviewed event labels and maintenance/work-order outcomes, preserve time order, fit on earlier periods, test on later periods, avoid leakage across the split, and report precision/recall, PR-AUC, per-asset false alerts per day, detection delay, and operator review feedback. Thresholds should be chosen with asset engineers based on the cost of missed events versus nuisance alarms.

## 8. Production gaps and next improvements

Before any real operational use:

1. Replace demo telemetry with access-controlled, quality-checked time-series ingestion and real timestamps.
2. Confirm sensor units, asset class, operating states, and maintenance labels with domain experts.
3. Fit on an earlier training period and score later observations; monitor drift and recalibrate per asset/site.
4. Add alert deduplication, persistence rules, alert acknowledgement, audit history, and observability.
5. Treat missing/stale/stuck sensors explicitly; do not silently infer them as normal.
6. Add authentication, authorization, rate controls, and secure deployment/network configuration.
7. Validate explanations and workflow with operators. Keep human approval in the loop.
8. If maintenance manuals are added, build retrieval over approved documents, return cited passages and document revisions, and keep retrieved evidence separate from model evidence. Do not have a language model invent diagnoses.

The project intentionally does not include RAG or an external LLM: the repository has no maintenance documents to retrieve and no labelled diagnostic corpus. Rule and model evidence is more transparent for this small demo.

## 9. Railway deployment

The app is deployed and available at:

**Live dashboard:** https://renewableassetfaultanomalycopilot-production-1681132b.up.railway.app

The public dashboard loaded successfully. The `/api/health` endpoint returned `ok`, `/api/demo` reported 240 rows across two assets, and `/docs` returned HTTP 200. The browser dashboard also ran an analysis and displayed the returned alerts.

The deployment uses the repository root, `.python-version` selects Python 3.11, and the included `Procfile` starts:

```text
uvicorn backend.app:app --host 0.0.0.0 --port $PORT
```

For future updates, push changes to the GitHub branch connected to Railway and verify the resulting deployment from the Railway dashboard. Railway supplies `PORT`; do not commit a fixed port or secrets.

The app has no authentication and currently uses synthetic demo data. Do not connect sensitive operational data or treat alerts as production maintenance decisions.

If the service fails, check Railway build/deploy logs first. Confirm the requirements install successfully, the dataset and frontend files are included in the repository, and the process binds to `0.0.0.0` and the supplied `$PORT`. Deployment settings and account credentials are managed in Railway, not stored in this repository.

## 10. A concise presentation explanation

You can explain the solution like this:

> “I built a small operator decision-support demo, not an automatic fault diagnosis system. It validates the telemetry, analyzes each asset separately, applies robust-deviation checks for temperature and vibration, and compares solar output to a simple daylight baseline so night-time zero output is not treated as an anomaly. Isolation Forest adds a multivariate outlier signal. The API returns the readings, rule evidence, reasons, and suggested checks to a FastAPI-backed dashboard. Because this synthetic dataset has no verified labels, I only report unit checks and injected stress-case results; I do not claim production accuracy. The next step is evaluation on time-separated, labelled site history with engineers reviewing thresholds and alerts.”

Be prepared to explain limitations: small synthetic dataset, uncalibrated model scores, no ground-truth labels, no RAG/manual corpus, simple solar baseline, and no production authentication or monitoring.
