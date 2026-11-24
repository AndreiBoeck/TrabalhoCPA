"""Modelo de água por nível e previsão estatística da Tela 2."""

import json
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from backend import water

ROOT = Path(__file__).resolve().parents[1]
NETWORK = json.loads((ROOT / "dados/processados/rotas_centro_2024_05_06.json").read_text(encoding="utf-8"))


class WaterModelTests(unittest.TestCase):
    def test_reference_conversion_matches_2024_peak(self):
        self.assertAlmostEqual(water.msl_to_regua(4.17), 5.35)
        self.assertAlmostEqual(water.regua_to_msl(5.35), 4.17)

    def test_flooded_streets_never_decrease_when_level_rises(self):
        previous = -1
        for level in [1.7, 3.0, 4.0, 5.35, 7.0, 10.0]:
            edges = water.network_at_level(NETWORK, level)["edges"]
            wet = sum(1 for edge in edges if edge["depth_m"])
            self.assertGreaterEqual(wet, previous)
            previous = wet
        self.assertEqual(sum(1 for e in water.network_at_level(NETWORK, 1.7)["edges"] if e["depth_m"]), 0)

    def test_unknown_depth_stays_unknown(self):
        original = [edge["depth_m"] is None for edge in NETWORK["edges"]]
        modelled = [edge["depth_m"] is None for edge in water.network_at_level(NETWORK, 6.0)["edges"]]
        self.assertEqual(original, modelled)

    def test_point_window_shape_and_outside_area(self):
        window = water.point_window(-30.0225, -51.2190)
        self.assertEqual(len(window["ground_msl_m"]), 60)
        self.assertTrue(window["point"]["inside_poa"])
        self.assertIsNone(water.point_window(-23.55, -46.63))

    def test_validation_recorded_for_four_dates(self):
        dates = [row["date"] for row in water.validation()["validation"]]
        self.assertEqual(dates, ["2024-05-04", "2024-05-06", "2024-05-08", "2024-05-10"])


class ForecastTests(unittest.TestCase):
    def series(self, slope_per_hour=0.0):
        start = datetime(2026, 11, 1)
        return [(start + timedelta(hours=h), 0.5 + slope_per_hour * h) for h in range(24 * 25)]

    def test_forecast_has_72_hours_with_band(self):
        result = water.forecast(self.series())
        self.assertEqual(result["status"], "ok")
        self.assertEqual([p["hours"] for p in result["points"]][-1], 72)
        for point in result["points"]:
            self.assertLessEqual(point["low_regua_m"], point["regua_m"])
            self.assertGreaterEqual(point["high_regua_m"], point["regua_m"])

    def test_short_series_is_unavailable(self):
        self.assertEqual(water.forecast(self.series()[:100])["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
