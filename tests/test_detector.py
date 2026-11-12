import unittest
from pathlib import Path

import pandas as pd

from backend.detector import detect_anomalies

BASE = Path(__file__).resolve().parents[1]


class DetectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = pd.read_csv(BASE / "data" / "asset_telemetry.csv")

    def test_solar_nighttime_zero_output_is_not_a_rule_alert(self) -> None:
        data = self.data.loc[self.data["asset_id"] == "SOLAR_INV_01"].copy()
        result = detect_anomalies(data)
        night_alerts = [
            alert
            for alert in result["alerts"]
            if alert["hour"] < 6 and alert["timestamp_id"] < 24
        ]
        self.assertFalse(
            any(
                "Power output is materially below" in " ".join(alert["reasons"])
                for alert in night_alerts
            )
        )

    def test_power_drop_during_sunlight_is_explained(self) -> None:
        data = self.data.copy()
        row = data.loc[
            (data["asset_id"] == "SOLAR_INV_01")
            & (data["irradiance_wm2"] >= 500)
        ].iloc[0].copy()
        row["timestamp_id"] = 1000
        row["power_mw"] = 0.05
        result = detect_anomalies(pd.concat([data, row.to_frame().T], ignore_index=True))
        alert = next(
            item
            for item in result["alerts"]
            if item["timestamp_id"] == 1000
        )
        self.assertTrue(
            any("Power output is materially below" in reason for reason in alert["reasons"])
        )
        self.assertTrue(alert["recommended_checks"])

    def test_high_vibration_and_temperature_produce_evidence(self) -> None:
        data = self.data.copy()
        row = data.loc[data["asset_id"] == "WTG_07"].iloc[30].copy()
        row["timestamp_id"] = 1001
        row["temperature_c"] = 75.0
        row["vibration_mm_s"] = 4.5
        result = detect_anomalies(pd.concat([data, row.to_frame().T], ignore_index=True))
        alert = next(
            item
            for item in result["alerts"]
            if item["timestamp_id"] == 1001
        )
        self.assertEqual(alert["severity"], "high")
        self.assertGreaterEqual(len(alert["evidence"]), 2)

    def test_missing_columns_fail_with_actionable_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing required columns"):
            detect_anomalies(pd.DataFrame({"asset_id": ["WTG_07"]}))


if __name__ == "__main__":
    unittest.main()
