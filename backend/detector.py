"""Explainable baseline anomaly detection for the bundled telemetry dataset."""

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

REQUIRED_COLUMNS = {
    "timestamp_id",
    "asset_id",
    "hour",
    "irradiance_wm2",
    "wind_speed_ms",
    "temperature_c",
    "vibration_mm_s",
    "power_mw",
}
SENSOR_COLUMNS = [
    "irradiance_wm2",
    "wind_speed_ms",
    "temperature_c",
    "vibration_mm_s",
    "power_mw",
]
ROBUST_Z_THRESHOLD = 3.5
MODEL_CONTAMINATION = 0.05


def _validate_data(data: pd.DataFrame) -> pd.DataFrame:
    missing_columns = sorted(REQUIRED_COLUMNS.difference(data.columns))
    if missing_columns:
        raise ValueError(f"Dataset is missing required columns: {missing_columns}")
    if data.empty:
        raise ValueError("Dataset contains no telemetry rows.")
    if data["asset_id"].isna().any():
        raise ValueError("asset_id must be present for every telemetry row.")

    frame = data.copy()
    for column in SENSOR_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if frame[SENSOR_COLUMNS].isna().any().any():
        raise ValueError("Telemetry sensor columns must contain numeric values.")
    if not np.isfinite(frame[SENSOR_COLUMNS].to_numpy(dtype=float)).all():
        raise ValueError("Telemetry sensor columns must contain finite values.")
    for column in ("timestamp_id", "hour"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
        if frame[column].isna().any() or not np.isfinite(
            frame[column].to_numpy(dtype=float)
        ).all():
            raise ValueError(f"{column} must contain finite numeric values.")
    if not np.equal(frame["timestamp_id"] % 1, 0).all():
        raise ValueError("timestamp_id must contain whole numbers.")
    if not np.equal(frame["hour"] % 1, 0).all():
        raise ValueError("hour must contain whole numbers.")
    return frame


def _robust_z_scores(values: pd.Series) -> np.ndarray:
    """Calculate median/MAD scores, handling constant or nearly constant data."""
    numbers = values.to_numpy(dtype=float)
    median = float(np.median(numbers))
    absolute_deviation = np.abs(numbers - median)
    mad = float(np.median(absolute_deviation))

    if mad > 1e-9:
        scale = 1.4826 * mad
        return absolute_deviation / scale

    q25, q75 = np.percentile(numbers, [25, 75])
    iqr = float(q75 - q25)
    if iqr > 1e-9:
        return absolute_deviation / (iqr / 1.349)

    deviations = np.where(absolute_deviation > 1e-9, 99.0, 0.0)
    return deviations


def _sensor_reason(
    sensor: str, value: float, baseline: float, z_score: float
) -> Tuple[str, str, str]:
    direction = "high" if value >= baseline else "low"
    label = "Vibration" if sensor == "vibration_mm_s" else "Temperature"
    if sensor == "vibration_mm_s":
        unit = "mm/s"
        recommendation = (
            "Check the vibration trend, sensor mounting, and the asset-specific "
            "inspection procedure."
        )
    else:
        unit = "°C"
        recommendation = (
            "Verify the temperature sensor and inspect cooling/ventilation "
            "and recent operating conditions."
        )
    reason = (
        f"{label} is unusually {direction} for this asset's observed baseline "
        f"({value:.2f} {unit}; robust deviation {z_score:.1f})."
    )
    severity = "high" if z_score >= 5.0 else "medium"
    return reason, recommendation, severity


def _detect_asset(group: pd.DataFrame) -> List[dict]:
    asset_id = str(group["asset_id"].iloc[0])
    features = group[SENSOR_COLUMNS].astype(float)
    scaled_features = StandardScaler().fit_transform(features)
    model = IsolationForest(
        n_estimators=200,
        contamination=MODEL_CONTAMINATION,
        random_state=42,
    )
    model_predictions = model.fit_predict(scaled_features)
    model_scores = -model.score_samples(scaled_features)

    vibration_z = _robust_z_scores(group["vibration_mm_s"])
    temperature_z = _robust_z_scores(group["temperature_c"])

    is_solar_asset = asset_id.upper().startswith("SOLAR")
    daylight = group["irradiance_wm2"] >= 150
    expected_solar_ratio = None
    if is_solar_asset and daylight.any():
        valid_daylight = group.loc[
            daylight & (group["power_mw"] >= 0), ["irradiance_wm2", "power_mw"]
        ]
        ratios = valid_daylight["power_mw"] / valid_daylight["irradiance_wm2"]
        if not ratios.empty:
            expected_solar_ratio = float(ratios.median())

    alerts: List[dict] = []
    for position, (_, row) in enumerate(group.iterrows()):
        reasons: List[str] = []
        recommendations: List[str] = []
        severities: List[str] = []
        evidence: List[dict] = []

        for sensor, score in (
            ("vibration_mm_s", float(vibration_z[position])),
            ("temperature_c", float(temperature_z[position])),
        ):
            if score >= ROBUST_Z_THRESHOLD:
                reason, recommendation, severity = _sensor_reason(
                    sensor,
                    float(row[sensor]),
                    float(group[sensor].median()),
                    score,
                )
                reasons.append(reason)
                recommendations.append(recommendation)
                severities.append(severity)
                evidence.append(
                    {
                        "sensor": sensor,
                        "observed": round(float(row[sensor]), 3),
                        "baseline_median": round(
                            float(group[sensor].median()), 3
                        ),
                        "robust_deviation": round(min(score, 99.0), 2),
                    }
                )

        solar_power_deficit = None
        if is_solar_asset and expected_solar_ratio is not None and daylight.iloc[position]:
            expected_power = float(row["irradiance_wm2"]) * expected_solar_ratio
            solar_power_deficit = (
                1.0 - float(row["power_mw"]) / expected_power
                if expected_power > 1e-9
                else 0.0
            )
            if solar_power_deficit >= 0.4:
                reasons.append(
                    "Power output is materially below this asset's typical "
                    "daylight output for the measured irradiance "
                    f"({float(row['power_mw']):.3f} MW observed vs "
                    f"{expected_power:.3f} MW baseline)."
                )
                recommendations.append(
                    "Compare inverter status, curtailment/grid events, and "
                    "irradiance and power sensor readings for this interval."
                )
                severities.append(
                    "high" if solar_power_deficit >= 0.7 else "medium"
                )
                evidence.append(
                    {
                        "sensor": "power_mw",
                        "observed": round(float(row["power_mw"]), 3),
                        "estimated_baseline": round(expected_power, 3),
                        "deficit_fraction": round(solar_power_deficit, 3),
                    }
                )

        model_flag = bool(model_predictions[position] == -1)
        if model_flag and not reasons:
            reasons.append(
                "The combination of telemetry values is unusual compared with "
                "the other observations for this asset."
            )
            recommendations.append(
                "Review the sensor readings and nearby time intervals before "
                "raising a maintenance work order."
            )
            severities.append("low")

        if not reasons:
            continue

        severity_order = {"low": 1, "medium": 2, "high": 3}
        severity = max(severities, key=severity_order.get)
        alerts.append(
            {
                "asset_id": asset_id,
                "timestamp_id": int(row["timestamp_id"]),
                "hour": int(row["hour"]),
                "severity": severity,
                "reasons": reasons,
                "recommended_checks": list(dict.fromkeys(recommendations)),
                "evidence": evidence,
                "model_flag": model_flag,
                "model_score": round(float(model_scores[position]), 4),
                "telemetry": {
                    column: round(float(row[column]), 3)
                    for column in SENSOR_COLUMNS
                },
            }
        )
    return alerts


def detect_anomalies(data: pd.DataFrame) -> Dict[str, object]:
    """Return asset-level anomaly alerts and a summary for a telemetry frame."""
    frame = _validate_data(data)
    alerts: List[dict] = []
    for _, group in frame.groupby("asset_id", sort=True):
        if len(group) < 20:
            raise ValueError(
                "Each analyzed asset needs at least 20 rows for the baseline model."
            )
        alerts.extend(_detect_asset(group.reset_index(drop=True)))

    severity_order = {"high": 0, "medium": 1, "low": 2}
    alerts.sort(
        key=lambda alert: (
            severity_order[alert["severity"]],
            -alert["model_score"],
            alert["asset_id"],
            alert["timestamp_id"],
        )
    )
    assets = sorted(frame["asset_id"].astype(str).unique().tolist())
    return {
        "total_rows": int(len(frame)),
        "analyzed_assets": assets,
        "alert_count": len(alerts),
        "alerts": alerts,
        "model": {
            "name": "Domain rules + Isolation Forest",
            "rule_threshold": f"robust deviation >= {ROBUST_Z_THRESHOLD}",
            "isolation_forest_contamination": MODEL_CONTAMINATION,
            "interpretation": (
                "Contamination sets the model's approximate flagged fraction; "
                "it is not a probability that a row is faulty."
            ),
        },
        "limitations": [
            "The bundled 240-row dataset is synthetic and has no ground-truth labels.",
            "Thresholds and the expected solar power ratio are demo baselines, not OEM limits.",
            "Isolation Forest is fit on the analyzed data for this demo; this is not a production time split.",
            "An alert is a review prompt, not proof of a fault or a maintenance instruction.",
            "No maintenance-document retrieval or external LLM diagnosis is used.",
        ],
    }
