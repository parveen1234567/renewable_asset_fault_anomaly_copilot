from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from backend.detector import detect_anomalies

BASE = Path(__file__).resolve().parents[1]
DATA_FILE = BASE / "data" / "asset_telemetry.csv"
FRONTEND_FILE = BASE / "frontend" / "index.html"

app = FastAPI(
    title="Renewable Asset Fault & Anomaly Detection Copilot",
    description=(
        "A demo decision-support API. Alerts are screening signals and require "
        "operator review; they are not confirmed diagnoses."
    ),
    version="1.0.0",
)


class Query(BaseModel):
    text: str = Field(default="", description="Optional operator note for this run.")
    asset_id: Optional[str] = Field(
        default=None, description="Limit analysis to one known asset."
    )


def load_telemetry() -> pd.DataFrame:
    if not DATA_FILE.is_file():
        raise RuntimeError(f"Telemetry dataset is missing: {DATA_FILE}")
    return pd.read_csv(DATA_FILE)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home() -> HTMLResponse:
    if not FRONTEND_FILE.is_file():
        raise RuntimeError(f"Frontend file is missing: {FRONTEND_FILE}")
    return HTMLResponse(FRONTEND_FILE.read_text(encoding="utf-8"))


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/demo")
def demo() -> dict:
    data = load_telemetry()
    assets = sorted(data["asset_id"].dropna().astype(str).unique().tolist())
    return {
        "case_study": "Renewable Asset Fault & Anomaly Detection Copilot",
        "status": "ready",
        "expected_outcome": (
            "Screen asset telemetry for unusual patterns and explain why an "
            "operator may want to investigate."
        ),
        "total_rows": int(len(data)),
        "assets": assets,
        "note": "The bundled dataset is synthetic demo data without ground-truth labels.",
    }


@app.post("/api/run")
def run_case(query: Query) -> dict:
    data = load_telemetry()
    if query.asset_id is not None:
        known_assets = set(data["asset_id"].dropna().astype(str))
        if query.asset_id not in known_assets:
            raise HTTPException(
                status_code=404, detail=f"Unknown asset_id: {query.asset_id}"
            )
        data = data.loc[data["asset_id"].astype(str) == query.asset_id].copy()

    try:
        analysis = detect_anomalies(data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "input": query.text,
        "result": "Detection complete",
        **analysis,
    }
