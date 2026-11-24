"""Confere a integração entre geometrias oficiais, INCT e malha histórica 3D."""

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SpatialDataTests(unittest.TestCase):
    def test_all_inct_neighborhoods_have_geometry(self):
        geometry = json.loads((ROOT / "dados/processados/bairros_poa.geojson").read_text(encoding="utf-8"))
        inct = json.loads((ROOT / "dados/processados/inct_simai_limpo.json").read_text(encoding="utf-8"))
        self.assertEqual({feature["properties"]["bairro"] for feature in geometry["features"]},
                         {row["bairro"] for row in inct})
        self.assertEqual(len(geometry["features"]), 94)

    def test_terrain_regions_have_valid_heights_and_historical_water(self):
        data = json.loads((ROOT / "dados/processados/relevo_3d_2024_05_06.json").read_text(encoding="utf-8"))
        self.assertEqual(data["metadata"]["scenario_date"], "2024-05-06")
        for region in data["regions"].values():
            heights, depths = region["elevation_m"], region["water_depth_m"]
            self.assertEqual(len(heights), len(depths))
            self.assertTrue(any(value > 0 for row in depths for value in row))
            self.assertTrue(all(value is None or -100 < value < 1000 for row in heights for value in row))


if __name__ == "__main__":
    unittest.main()
