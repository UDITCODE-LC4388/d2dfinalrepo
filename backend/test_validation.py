"""One-off validation script for hackathon backend."""
import json
import sys
import time

from analyzer.git_analyzer import analyze_repo


def validate_graph(graph):
    assert "nodes" in graph and "edges" in graph
    for node in graph["nodes"]:
        assert "id" in node and "type" in node
        assert node["type"] in ("developer", "commit")
    node_ids = {n["id"] for n in graph["nodes"]}
    for edge in graph["edges"]:
        assert "source" in edge and "target" in edge
        assert edge["source"] in node_ids
        assert edge["target"] in node_ids


def main():
    repo_url = "https://github.com/pallets/flask.git"
    print(f"Analyzing {repo_url} ...")
    t0 = time.perf_counter()
    result = analyze_repo(repo_url)
    elapsed = time.perf_counter() - t0
    print(f"Done in {elapsed:.1f}s")

    assert result["repo"] == "flask"
    assert result["total_commits"] > 0
    assert result["commits_analyzed"] > 0
    assert len(result["commit_analysis"]) == result["commits_analyzed"]
    assert all("health_score" in c for c in result["commit_analysis"])
    validate_graph(result["graph"])
    assert result["ai_summary"]
    if result["ai_summary"].startswith("AI summary unavailable"):
        print("WARNING: AI summary failed (check GROQ_API_KEY / network)")

    json.dumps(result)
    print("ALL CHECKS PASSED")
    print(json.dumps({
        "repo": result["repo"],
        "total_commits": result["total_commits"],
        "commits_analyzed": result["commits_analyzed"],
        "commit_sample": result["commit_analysis"][0],
        "health_scores_sample": [c["health_score"] for c in result["commit_analysis"][:5]],
        "graph_node_count": len(result["graph"]["nodes"]),
        "graph_edge_count": len(result["graph"]["edges"]),
        "graph_sample_nodes": result["graph"]["nodes"][:3],
        "graph_sample_edges": result["graph"]["edges"][:3],
        "ai_summary_preview": result["ai_summary"][:500],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
