import logging

import networkx as nx

from analyzer.config import GRAPH_DISPLAY_MAX_COMMITS

logger = logging.getLogger(__name__)


def build_graph(commit_data: list, max_commits: int | None = None) -> dict:
    """
    Build developer ↔ commit graph.
    For very large histories, only the most recent `max_commits` are included
    in the graph payload (full commit analysis is unchanged).
    """
    if max_commits is None:
        max_commits = GRAPH_DISPLAY_MAX_COMMITS

    graph_commits = commit_data
    truncated = False
    if max_commits > 0 and len(commit_data) > max_commits:
        graph_commits = commit_data[:max_commits]
        truncated = True
        logger.info(
            "Graph uses %s most recent commits (%s total analyzed)",
            len(graph_commits),
            len(commit_data),
        )

    G = nx.Graph()

    for commit in graph_commits:
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

    return {
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "commits_in_graph": len(graph_commits),
            "commits_analyzed_total": len(commit_data),
            "truncated_for_display": truncated,
        },
    }
