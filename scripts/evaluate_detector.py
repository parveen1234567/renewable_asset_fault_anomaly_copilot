"""Run a reproducible synthetic stress test for the demo anomaly detector."""

from pathlib import Path

import pandas as pd

from backend.detector import detect_anomalies

BASE = Path(__file__).resolve().parents[1]
DATA_FILE = BASE / "data" / "asset_telemetry.csv"


def main() -> None:
    baseline = pd.read_csv(DATA_FILE)
    baseline_result = detect_anomalies(baseline)
    baseline_alert_ids = {
        (alert["asset_id"], alert["timestamp_id"])
        for alert in baseline_result["alerts"]
    }

    solar_normal = baseline.loc[
        (baseline["asset_id"] == "SOLAR_INV_01")
        & (baseline["irradiance_wm2"] >= 500)
    ].iloc[0].copy()
    solar_case = solar_normal.copy()
    solar_case["timestamp_id"] = 1000
    solar_case["power_mw"] = 0.05

    wind_normal = baseline.loc[baseline["asset_id"] == "WTG_07"].iloc[30].copy()
    wind_case = wind_normal.copy()
    wind_case["timestamp_id"] = 1001
    wind_case["temperature_c"] = 75.0
    wind_case["vibration_mm_s"] = 4.5

    stress_data = pd.concat(
        [baseline, pd.DataFrame([solar_case, wind_case])],
        ignore_index=True,
    )
    stress_result = detect_anomalies(stress_data)
    stress_alert_ids = {
        (alert["asset_id"], alert["timestamp_id"])
        for alert in stress_result["alerts"]
    }
    injected_cases = {
        ("SOLAR_INV_01", 1000),
        ("WTG_07", 1001),
    }
    detected = injected_cases.intersection(stress_alert_ids)
    baseline_false_alerts = len(baseline_alert_ids)

    print("Synthetic stress-test summary")
    print(f"Bundled rows: {len(baseline)}")
    print(
        "Baseline alerts on unlabelled bundled data: "
        f"{baseline_false_alerts} ({baseline_false_alerts / len(baseline):.1%} of rows)"
    )
    print(f"Injected cases detected: {len(detected)} / {len(injected_cases)}")
    for asset_id, timestamp_id in sorted(injected_cases):
        state = "DETECTED" if (asset_id, timestamp_id) in detected else "MISSED"
        print(f"  {asset_id}, row {timestamp_id}: {state}")
    print(
        "Caution: these are hand-crafted positive stress cases, not a labelled "
        "benchmark. The baseline alert fraction is not a measured false-positive rate."
    )


if __name__ == "__main__":
    main()
