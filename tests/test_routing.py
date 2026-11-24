import unittest

from backend.routing import RouteRequest, calculate_route


def route(nodes, edges, origin="A", destination="B"):
    return calculate_route(RouteRequest(
        nodes=[{"id": name, "depth_m": depth} for name, depth in nodes.items()],
        edges=[{"source": a, "target": b, "length_m": length, "depth_m": depth}
               for a, b, length, depth in edges],
        origin=origin,
        destination=destination,
    ))


class RoutingTests(unittest.TestCase):
    def test_dry_shortest_path_and_flood_detour(self):
        nodes = {name: 0 for name in "ABCD"}
        edges = [("A", "C", 1, 0), ("C", "B", 1, 0),
                 ("A", "D", 3, 0), ("D", "B", 3, 0)]
        self.assertEqual(route(nodes, edges)["node_ids"], ["A", "C", "B"])
        edges[1] = ("C", "B", 1, 0.2)
        result = route(nodes, edges)
        self.assertEqual(result["node_ids"], ["A", "D", "B"])
        self.assertEqual(result["route_type"], "shortest_dry")

    def test_flooded_origin_prefers_shallower_exit_over_shorter_exit(self):
        nodes = {"A": 0.5, "C": 0.4, "D": 0.1, "E": 0, "F": 0, "B": 0}
        edges = [("A", "C", 1, 0.4), ("C", "E", 1, 0.4),
                 ("E", "B", 1, 0), ("A", "D", 3, 0.1),
                 ("D", "F", 3, 0.1), ("F", "B", 3, 0)]
        result = route(nodes, edges)
        self.assertEqual(result["node_ids"], ["A", "D", "F", "B"])
        self.assertEqual(result["route_type"], "minimum_exposure")
        self.assertEqual(result["max_depth_m"], 0.1)
        self.assertEqual(result["flooded_length_m"], 6)

    def test_unknown_depth_is_not_traversed(self):
        result = route({"A": 0, "B": 0}, [("A", "B", 1, None)])
        self.assertEqual(result, {"status": "no_route", "reason": "no_verified_path"})

    def test_flooded_destination_has_no_route(self):
        result = route({"A": 0, "B": 0.2}, [("A", "B", 1, 0.2)])
        self.assertEqual(result, {"status": "no_route", "reason": "destination_flooded"})

    def test_no_reentry_after_dry_exit(self):
        nodes = {"A": 0.2, "C": 0, "D": 0.1, "B": 0}
        edges = [("A", "C", 1, 0.1), ("C", "D", 1, 0.1), ("D", "B", 1, 0.1)]
        self.assertEqual(route(nodes, edges)["status"], "no_route")

    def test_later_deep_bottleneck_breaks_early_depth_tie(self):
        nodes = {"A": 0.5, "C": 0.1, "D": 0.2, "X": 0.1, "B": 0}
        edges = [("A", "C", 50, 0.1), ("C", "X", 50, 0.1),
                 ("A", "D", 1, 0.2), ("D", "X", 1, 0.2),
                 ("X", "B", 1, 0.3)]
        result = route(nodes, edges)
        self.assertEqual(result["node_ids"], ["A", "D", "X", "B"])
        self.assertEqual(result["max_depth_m"], 0.3)


if __name__ == "__main__":
    unittest.main()
