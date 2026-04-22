import heapq
from collections import deque
from webtris_client import APIClient, SingleSite, APIConnector


class Node:
    """
    Represents a node in the graph, with a value and a list of adjacent nodes with weights.
    """

    def __init__(self, value):
        """
        Initialize a node with a value and an empty list of adjacent nodes with weights.
        """
        self.value = value
        self.adjacent_nodes: list[tuple[Node, float]] = []  # (neighbour, weight)

    def __repr__(self):
        """
        Return a string representation of the node, showing its value and adjacent nodes with weights.
        """
        neighbours = [str(n.value) + ": " + str(w) for (n, w) in self.adjacent_nodes]
        return f"Node(value={self.value}, adjacent_nodes={neighbours})"

    def add_adjacent_node(self, node, weight):
        """
        Add an adjacent node with a weight.
        """
        if (node, weight) not in self.adjacent_nodes:
            self.adjacent_nodes.append((node, weight))


class Graph:
    """
    Weighted directed graph representing the road network.
    """

    def __init__(self):
        """
        Initialize an empty graph.
        """
        self.nodes: dict[str, Node] = {}

    def add_node(self, name: str) -> Node:
        """
        Add a node if not already present.
        """
        if name not in self.nodes:
            self.nodes[name] = Node(name)
        return self.nodes[name]

    def add_edge(self, from_name: str, to_name: str, weight: float) -> None:
        """
        Add a directed edge between two named nodes.
        """
        from_node = self.add_node(from_name)
        to_node = self.add_node(to_name)
        from_node.add_adjacent_node(to_node, weight)

    def get_node(self, name: str) -> Node:
        """
        Get a node by its name.
        """
        if name not in self.nodes:
            raise KeyError(f"Node '{name}' not found in graph.")
        return self.nodes[name]

    def bfs(self, start_name: str, end_name: str) -> tuple[list[str], float]:
        """
        Breadth first search to finds the path with the fewest nodes.
        """

        start = self.get_node(start_name)
        end = self.get_node(end_name)

        # Mark as visited on enqueue, not dequeue (prevents duplicates in queue)
        visited: set[str] = {start.value}

        # Queue entries: (current_node, path_so_far, total_weight)
        queue: deque[tuple[Node, list[str], float]] = deque(
            [(start, [start.value], 0.0)]
        )

        while queue:
            current, path, total_weight = queue.popleft()

            if current is end:
                return path, total_weight

            for neighbour, weight in current.adjacent_nodes:
                if neighbour.value not in visited:
                    visited.add(neighbour.value)  # mark on enqueue
                    queue.append(
                        (neighbour, path + [neighbour.value], total_weight + weight)
                    )

        return [], float(
            "inf"
        )  # return empty path and infinite weight if no path found

    def dfs(
        self, start_name: str, end_name: str, visited: set[str] = None
    ) -> tuple[list[str], float]:
        """
        Depth first search to recursively find a valid path to the destination.
        """
        if visited is None:
            visited = set()

        current = self.get_node(start_name)
        end = self.get_node(end_name)

        visited.add(current.value)

        if current is end:
            return [current.value], 0.0  # return the final node as a 1-element path

        for neighbour, weight in current.adjacent_nodes:
            if neighbour.value not in visited:
                result = self.dfs(neighbour.value, end_name, visited)
                if result[0]:
                    return [current.value] + result[0], result[
                        1
                    ] + weight  # build the path

        return [], float("inf")

    def dijkstra(self, start_name: str, end_name: str) -> tuple[list[str], float]:
        """
        Dijkstra algorithm to find the path with the minimum total weight.
        """
        # Stores the cheapest known travel time from start to each node
        cheapest_times = {start_name: 0.0}

        # For each node, the previous node on the cheapest route
        previous_node: dict[str, str] = {}

        # Nodes we have fully processed
        visited: set[str] = set()

        # Min-heap ordered by travel time
        pq: list[tuple[float, str]] = [(0.0, start_name)]

        while pq:
            # Pop the unvisited node with the lowest known travel time
            current_time, current_name = heapq.heappop(pq)

            # Skip if already processed
            if current_name in visited:
                continue
            visited.add(current_name)

            current = self.get_node(current_name)

            for neighbour, weight in current.adjacent_nodes:
                if neighbour.value in visited:
                    continue

                # Cost to reach this neighbour via the current node
                new_time = current_time + weight

                # Update if this is the cheapest route found so far
                if (
                    neighbour.value not in cheapest_times
                    or new_time < cheapest_times[neighbour.value]
                ):
                    cheapest_times[neighbour.value] = new_time
                    previous_node[neighbour.value] = current_name
                    heapq.heappush(pq, (new_time, neighbour.value))

        # Reconstruct path by walking back through previous_node
        if end_name not in cheapest_times:
            return [], float("inf")

        path = []
        current_name = end_name
        while current_name in previous_node:
            path.append(current_name)
            current_name = previous_node[current_name]
        path.append(start_name)
        path.reverse()

        return path, cheapest_times[end_name]


class ClientCalculations:
    """
    Helper class to perform calculations using the WebTRIS API.
    """

    # Define distances between nodes
    distances: dict[tuple[str, str], float] = {
        ("M25 J7", "M25 J12"): 23.0,
        # Route A: J12 -> J13 -> J14 (Heathrow)
        ("M25 J12", "M25 J13"): 3.0,
        ("M25 J13", "M25 J14"): 3.0,
        ("M25 J14", "Heathrow"): 0.0,
        # Route B: J12 -> Heathrow
        ("M25 J12", "Heathrow"): 12.0,
        # Route C: J13 -> Heathrow
        ("M25 J13", "Heathrow"): 3.8,
    }

    # WebTRIS sensor IDs associated with each edge
    sensors: dict[tuple[str, str], list[int]] = {
        # Route A: J12 -> J13 -> J14 (Heathrow)
        ("M25 J7", "M25 J12"): [
            138,
            144,
            479,
            544,
            547,
            598,
            699,
            752,
            778,
            885,
            1069,
            1135,
            1221,
            1270,
            1442,
            1479,
            1914,
            1990,
            2005,
            2089,
            2097,
            2149,
            2419,
            2486,
            2530,
            2636,
            3003,
            3323,
            3437,
            3714,
            3835,
            3897,
            4000,
            4092,
            4145,
            4202,
            4223,
            4714,
            4719,
            4761,
            4894,
            5107,
            5118,
            5138,
            5176,
            5261,
            5288,
            5457,
            5526,
            5546,
            5712,
            5842,
            5875,
            5914,
            5990,
            6156,
            6252,
        ],
        ("M25 J12", "M25 J13"): [8, 1811, 1910, 2952, 2992, 3319, 5245, 5662, 5681],
        ("M25 J13", "M25 J14"): [279, 737, 3671, 4053, 4354, 5317],
        ("M25 J14", "Heathrow"): [746, 2153, 2977],
        ("M25 J12", "Heathrow"): [],  # No sensor data for this edge (fixed 20 min)
        ("M25 J13", "Heathrow"): [9005],
    }

    @staticmethod
    def get_avg_speed_for_edge(
        sensor_ids: list[int], date: str, time_period: int
    ) -> float | None:
        """
        Get the average speed for a road segment based on its sensor IDs.
        """
        client = APIClient(connector=APIConnector())
        speeds = []
        for site_id in sensor_ids:
            try:
                site = SingleSite(site_id, f"Site {site_id}")
                site.get_data(client, date)
                avg_speed = site.calculate_avg_speed_for_hour(time_period)
                if avg_speed is not None:
                    speeds.append(avg_speed)
            except Exception as e:
                print(f"Skipping sensor {site_id}: {e}")
        if not speeds:
            return None
        return sum(speeds) / len(speeds)

    @staticmethod
    def calculate_travel_time(distance_km: float, avg_speed: float) -> float:
        """
        Convert distance and speed into travel time in minutes.
        """
        if not avg_speed or avg_speed <= 0:
            return 20  # assume 20 minutes if speed is invalid
        return (distance_km / avg_speed) * 60

    @classmethod
    def build_graph_from_api(cls, date: str, time_period: int) -> Graph:
        """
        Build the road network graph using live data from the api.
        """

        graph = Graph()

        for (from_name, to_name), distance in cls.distances.items():
            sensor_ids = cls.sensors.get((from_name, to_name), [])
            avg_speed = cls.get_avg_speed_for_edge(sensor_ids, date, time_period)
            weight = cls.calculate_travel_time(distance, avg_speed)
            graph.add_edge(from_name, to_name, weight)

        return graph
