"""Confere a integração entre geometrias oficiais e INCT."""

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

if __name__ == "__main__":
    unittest.main()
