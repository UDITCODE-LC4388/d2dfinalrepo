import networkx as nx


def build_graph(commit_data: list) -> dict:
    G = nx.Graph()

    for commit in commit_data:
        author = commit["author"]
        commit_hash = commit["hash"]

        G.add_node(author, type="developer")
        G.add_node(commit_hash, type="commit")
        G.add_edge(author, commit_hash)

    nodes = [
        {"id": node_id, "type": attrs["type"]}
        for node_id, attrs in G.nodes(data=True)
    ]
    edges = [
        {"source": source, "target": target}
        for source, target in G.edges()
    ]

    return {"nodes": nodes, "edges": edges}
