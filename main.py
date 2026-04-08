from webtris_graph import ClientCalculations

start = "M25 J7"
end = "Heathrow"


def main():
    graph = ClientCalculations.build_graph_from_api(
        "19012026", 8
    )  # example date and time period

    path1 = graph.dfs(start, end)
    print(f"Path from {start} to {end} using DFS: {path1}")

    path2 = graph.bfs(start, end)
    print(f"Path from {start} to {end} using BFS: {path2}")

    path3 = graph.dijkstra(start, end)
    print(f"Path from {start} to {end} using Dijkstra's: {path3}")


if __name__ == "__main__":
    main()
