"""Rotas a pé sobre a rede da área alagada em 2024, com a água do modelo por nível."""

import unittest

from fastapi.testclient import TestClient

from backend import rotas
from backend.main import app

FARRAPOS = {"lat": -30.0012, "lon": -51.1994}  # 4º Distrito, alaga no recorde de 2024 no modelo


class MapRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def plan(self, **body):
        response = self.client.post("/api/routing/plan", json=body)
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_streets_and_depths_line_up(self):
        streets = self.client.get("/api/routing/streets").json()
        depths = self.client.get("/api/routing/depths", params={"level": 5.35}).json()
        self.assertGreater(len(streets["edges"]), 10000)
        self.assertEqual(len(streets["edges"]), len(depths["edge_depth_m"]))
        self.assertGreater(depths["wet_length_m"], 100_000)

    def test_no_wet_streets_at_normal_river_level(self):
        self.assertEqual(self.client.get("/api/routing/depths", params={"level": 1.7}).json()["wet_length_m"], 0)

    def test_exit_from_flooded_point_reaches_dry_safe_point(self):
        result = self.plan(origin=FARRAPOS, level_regua_m=5.35)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["route_type"], "minimum_exposure")
        self.assertGreaterEqual(result["safe_point"]["margin_m"], rotas.SAFE_MARGIN_M)
        self.assertGreater(len(result["coordinates"]), 2)

    def test_same_point_is_already_safe_at_normal_level(self):
        self.assertEqual(self.plan(origin=FARRAPOS, level_regua_m=1.7)["status"], "already_safe")

    def test_a_to_b_has_dry_baseline_no_longer_than_route(self):
        result = self.plan(origin={"lat": -30.0273, "lon": -51.2273}, destination={"lat": -30.0330, "lon": -51.2205}, level_regua_m=5.35)
        self.assertEqual(result["status"], "ok")
        self.assertLessEqual(result["normal_route"]["length_m"], result["length_m"] + 1)

    def test_point_outside_the_street_network_has_no_route(self):
        result = self.plan(origin={"lat": -30.1, "lon": -51.3}, level_regua_m=5.35)
        self.assertEqual(result["reason"], "point_too_far_from_network")

    def test_overlay_is_png(self):
        response = self.client.get("/api/water/overlay.png", params={"level": 5.35})
        self.assertEqual(response.headers["content-type"], "image/png")
        self.assertTrue(response.content.startswith(b"\x89PNG"))


if __name__ == "__main__":
    unittest.main()
