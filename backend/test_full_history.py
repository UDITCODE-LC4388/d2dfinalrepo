"""Validate full-history analysis."""
import json
import sys
import time

from analyzer.git_analyzer import analyze_repo
from analyzer.response_mapper import map_to_frontend


def main():
    repo_url = sys.argv[1] if len(sys.argv) > 1 else "https://github.com/pallets/flask.git"
    print(f"Testing full history: {repo_url}\n")

    t0 = time.perf_counter()
    raw = analyze_repo(repo_url)
    mapped = map_to_frontend(raw)
    elapsed = time.perf_counter() - t0

    total = raw["total_commits"]
    analyzed = raw["commits_analyzed"]
    graph_nodes = len(mapped["graph"]["nodes"])

    print(f"total_commits (git):     {total:,}")
    print(f"commits_analyzed:        {analyzed:,}")
    print(f"match:                   {total == analyzed}")
    print(f"graph nodes:             {graph_nodes:,}")
    print(f"graph_meta:              {json.dumps(mapped.get('graph_meta', {}), indent=2)}")
    print(f"warnings:                {mapped.get('warnings', [])}")
    print(f"analysis_seconds (raw):  {raw.get('analysis_seconds')}")
    print(f"wall clock:              {elapsed:.1f}s")

    json.dumps(mapped)
    print("\nJSON serialization: OK")

    assert analyzed == total, f"Mismatch: analyzed {analyzed} vs total {total}"
    assert len(mapped["health_timeline"]) == analyzed
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
