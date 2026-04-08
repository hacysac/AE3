import pytest
from unittest.mock import patch
from webtris_graph import Graph, Node, ClientCalculations


mock_data = {
    "7-12": [
        {"id": 138,  "average_mph": 62},
        {"id": 144,  "average_mph": 36},
        {"id": 479,  "average_mph": 48},
        {"id": 544,  "average_mph": 23},
        {"id": 547,  "average_mph": 55},
        {"id": 699,  "average_mph": 59},
        {"id": 752,  "average_mph": 60},
        {"id": 778,  "average_mph": None},
        {"id": 885,  "average_mph": 60},
        {"id": 1135, "average_mph": None},
        {"id": 1221, "average_mph": None},
        {"id": 1270, "average_mph": 63},
        {"id": 1442, "average_mph": 51},
        {"id": 1990, "average_mph": None},
        {"id": 2005, "average_mph": None},
        {"id": 2089, "average_mph": None},
        {"id": 2097, "average_mph": 61},
        {"id": 2149, "average_mph": 54},
        {"id": 2419, "average_mph": None},
        {"id": 2486, "average_mph": 55},
        {"id": 2530, "average_mph": None},
        {"id": 2636, "average_mph": 45},
        {"id": 3003, "average_mph": 29},
        {"id": 3323, "average_mph": 55},
        {"id": 3437, "average_mph": 62},
        {"id": 3714, "average_mph": 53},
        {"id": 3835, "average_mph": 30},
        {"id": 3897, "average_mph": 51},
        {"id": 4000, "average_mph": None},
        {"id": 4092, "average_mph": 58},
        {"id": 4145, "average_mph": 57},
        {"id": 4202, "average_mph": 47},
        {"id": 4223, "average_mph": None},
        {"id": 4714, "average_mph": None},
        {"id": 4719, "average_mph": 59},
        {"id": 4761, "average_mph": None},
        {"id": 4894, "average_mph": 47},
        {"id": 5107, "average_mph": 50},
        {"id": 5118, "average_mph": 30},
        {"id": 5138, "average_mph": None},
        {"id": 5176, "average_mph": 38},
        {"id": 5261, "average_mph": 34},
        {"id": 5288, "average_mph": 46},
        {"id": 5526, "average_mph": 54},
        {"id": 5546, "average_mph": 37},
        {"id": 5712, "average_mph": None},
        {"id": 5875, "average_mph": 56},
        {"id": 5990, "average_mph": None},
        {"id": 6156, "average_mph": 65},
    ],
    "12-13": [
        {"id": 8,    "average_mph": 62},
        {"id": 1811, "average_mph": 63},
        {"id": 1910, "average_mph": None},
        {"id": 2952, "average_mph": 63},
        {"id": 2992, "average_mph": 60},
        {"id": 3319, "average_mph": 65},
        {"id": 5245, "average_mph": 61},
        {"id": 5662, "average_mph": None},
        {"id": 5681, "average_mph": 61},
    ],
    "13-14": [
        {"id": 279,  "average_mph": 41},
        {"id": 737,  "average_mph": 63},
        {"id": 3671, "average_mph": 54},
        {"id": 4053, "average_mph": 40},
        {"id": 4354, "average_mph": 62},
        {"id": 5317, "average_mph": 57},
    ],
    "14-Heathrow": [
        {"id": 746,  "average_mph": 34},
        {"id": 2153, "average_mph": None},
        {"id": 2977, "average_mph": None},
    ],
    "A30": [
        {"id": 9005, "average_mph": 57},
    ],
}

# Build a lookup from sensor ID -> average_mph so the side_effect can
# identify which edge it's being called for and return the right average.
sensor_id_to_edge = {
    sensor["id"]: edge_key
    for edge_key, sensors in mock_data.items()
    for sensor in sensors
}


def avg_speed(edge_key):
    speeds = [s["average_mph"] for s in mock_data[edge_key] if s["average_mph"] is not None]
    return sum(speeds) / len(speeds) if speeds else None


def travel_time(distance, speed):
    if not speed or speed <= 0:
        return 20.0
    return (distance / speed) * 60


def mock_get_avg_speed(sensor_ids, date, time_period):
    """
    Replacement for ClientCalculations.get_avg_speed_for_edge in order to use mock data.
    """
    if not sensor_ids:
        return None
    edge_key = sensor_id_to_edge.get(sensor_ids[0])
    if edge_key is None:
        return None
    return avg_speed(edge_key)


@pytest.fixture
def road_graph():
    """Full M25 road network built using mock sensor data instead of the API."""
    with patch.object(ClientCalculations, "get_avg_speed_for_edge", side_effect=mock_get_avg_speed):
        return ClientCalculations.build_graph_from_api("19012026", 8)

# Node tests
def test_node_creation():
    node = Node("M25 J7")
    assert node.value == "M25 J7"
    assert node.adjacent_nodes == []

def test_add_adjacent_node():
    n1, n2 = Node("A"), Node("B")
    n1.add_adjacent_node(n2, 5.0)
    assert len(n1.adjacent_nodes) == 1
    assert n1.adjacent_nodes[0] == (n2, 5.0)

def test_no_duplicate_adjacent_nodes():
    n1, n2 = Node("A"), Node("B")
    n1.add_adjacent_node(n2, 5.0)
    n1.add_adjacent_node(n2, 5.0)
    assert len(n1.adjacent_nodes) == 1

# Graph tests
def test_edge_is_directed():
    g = Graph()
    g.add_edge("A", "B", 1.0)
    assert any(n.value == "B" for n, _ in g.get_node("A").adjacent_nodes)
    assert g.get_node("B").adjacent_nodes == []

def test_get_node_missing_raises():
    g = Graph()
    try:
        g.get_node("MISSING")
        assert False, "Expected KeyError"
    except KeyError:
        pass

def test_graph_has_all_nodes(road_graph):
    for name in ["M25 J7", "M25 J12", "M25 J13", "M25 J14", "Heathrow"]:
        assert name in road_graph.nodes

def test_graph_has_six_edges(road_graph):
    total = sum(len(n.adjacent_nodes) for n in road_graph.nodes.values())
    assert total == 6

# BFS tests
def test_bfs_fewest_hops(road_graph):
    # Route B (J7 -> J12 -> Heathrow) is 3 nodes — fewest possible
    path = road_graph.bfs("M25 J7", "Heathrow")
    assert path == ["M25 J7", "M25 J12", "Heathrow"]

def test_bfs_no_path(road_graph):
    road_graph.add_node("Isolated")
    assert road_graph.bfs("M25 J7", "Isolated") == []

def test_bfs_same_start_end(road_graph):
    assert road_graph.bfs("M25 J7", "M25 J7") == ["M25 J7"]

def test_bfs_simple_graph():
    g = Graph()
    g.add_edge("A", "B", 1); g.add_edge("A", "C", 1)
    g.add_edge("B", "D", 1); g.add_edge("C", "D", 1)
    path = g.bfs("A", "D")
    assert len(path) == 3 and path[0] == "A" and path[-1] == "D"

# DFS tests
def test_dfs_finds_valid_path(road_graph):
    path = road_graph.dfs("M25 J7", "Heathrow")
    assert path[0] == "M25 J7" and path[-1] == "Heathrow"

def test_dfs_no_path(road_graph):
    road_graph.add_node("Isolated")
    assert road_graph.dfs("M25 J7", "Isolated") == []

def test_dfs_same_start_end(road_graph):
    assert road_graph.dfs("M25 J7", "M25 J7") == ["M25 J7"]

def test_dfs_linear_graph():
    g = Graph()
    g.add_edge("A", "B", 1); g.add_edge("B", "C", 1)
    assert g.dfs("A", "C") == ["A", "B", "C"]

# Dijkstra tests
def test_dijkstra_no_path(road_graph):
    road_graph.add_node("Isolated")
    path, cost = road_graph.dijkstra("M25 J7", "Isolated")
    assert path == [] and cost == float("inf")

def test_dijkstra_same_start_end(road_graph):
    path, cost = road_graph.dijkstra("M25 J7", "M25 J7")
    assert path == ["M25 J7"] and cost == 0.0

def test_dijkstra_known_graph():
    # A->B costs 10, A->C->B costs 2 — must pick A->C->B
    g = Graph()
    g.add_edge("A", "B", 10.0); g.add_edge("A", "C", 1.0); g.add_edge("C", "B", 1.0)
    path, cost = g.dijkstra("A", "B")
    assert path == ["A", "C", "B"] and cost == 2.0

def test_dijkstra_picks_minimum_route(road_graph):
    _, dijkstra_cost = road_graph.dijkstra("M25 J7", "Heathrow")

    route_a = travel_time(23.0, avg_speed("7-12")) + travel_time(3.0, avg_speed("12-13")) + travel_time(3.0, avg_speed("13-14")) + travel_time(0.0, avg_speed("14-Heathrow"))
    route_b = travel_time(23.0, avg_speed("7-12")) + 20.0
    route_c = travel_time(23.0, avg_speed("7-12")) + travel_time(3.0, avg_speed("12-13")) + travel_time(3.8, avg_speed("A30"))

    assert dijkstra_cost == min(route_a, route_b, route_c)


# helper tests
def test_avg_speed_ignores_none():
    # 12-13 valid speeds: 62, 63, 63, 60, 65, 61, 61
    expected = (62 + 63 + 63 + 60 + 65 + 61 + 61) / 7
    assert avg_speed("12-13") == expected

def test_travel_time_formula():
    assert travel_time(23.0, 60.0) == 23.0

def test_travel_time_defaults_to_20():
    assert travel_time(10.0, None) == 20.0
    assert travel_time(10.0, 0) == 20.0
    assert travel_time(10.0, -1) == 20.0

def test_route_b_fixed_20_minutes(road_graph):
    j12 = road_graph.get_node("M25 J12")
    heathrow_weights = [w for n, w in j12.adjacent_nodes if n.value == "Heathrow"]
    assert len(heathrow_weights) == 1 and heathrow_weights[0] == 20.0

def test_calculate_travel_time_static():
    assert ClientCalculations.calculate_travel_time(60.0, 60.0) == 60
    assert ClientCalculations.calculate_travel_time(10.0, None) == 20