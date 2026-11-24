import unittest

from fastapi.testclient import TestClient

from backend.main import app, routing_network


class MapRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.network = routing_network()
        cls.nodes = {node["id"]: node for node in cls.network["nodes"]}

    @staticmethod
    def middle(edge, nodes):
        a, b = nodes[edge["source"]], nodes[edge["target"]]
        return {"lat": (a["lat"] + b["lat"]) / 2,
                "lon": (a["lon"] + b["lon"]) / 2}

    def test_flooded_road_midpoint_is_treated_as_flooded_origin(self):
        wet = next(edge for edge in self.network["edges"] if edge["source"] == "296250804"
                   and edge["depth_m"] is not None and edge["depth_m"] > 0)
        dry = next(edge for edge in self.network["edges"] if edge["source"] == "443403786"
                   and edge["depth_m"] == 0)
        response = self.client.post("/api/routing/plan", json={
            "origin": self.middle(wet, self.nodes),
            "destination": self.middle(dry, self.nodes),
        })
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["route_type"], "minimum_exposure")
        self.assertGreater(result["max_depth_m"], 0)
        self.assertGreater(result["flooded_length_m"], 0)
        self.assertIn("normal_route", result)
        self.assertLessEqual(result["normal_route"]["length_m"], result["length_m"])

    def test_point_outside_the_street_network_has_no_route(self):
        response = self.client.post("/api/routing/plan", json={
            "origin": {"lat": -30.1, "lon": -51.3},
            "destination": {"lat": -30.03, "lon": -51.23},
        })
        self.assertEqual(response.json()["reason"], "point_too_far_from_network")


if __name__ == "__main__":
    unittest.main()
