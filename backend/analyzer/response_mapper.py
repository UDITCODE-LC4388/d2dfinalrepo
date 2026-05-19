"""Map internal analysis results to the frontend API contract."""


def _risk_level(avg_health: float) -> str:
    if avg_health >= 80:
        return "Low"
    if avg_health >= 60:
        return "Medium"
    return "High"


def _build_risks(commits: list) -> list:
    risks = []
    risky = [c for c in commits if c["health_score"] < 70]
    large = [c for c in commits if c["files_changed"] > 10 or c["insertions"] > 500]

    if risky:
        count = len(risky)
        risks.append({
            "id": "r-health",
            "type": "maintainability",
            "severity": "high" if count > 5 else "medium",
            "title": f"{count} commit{'s' if count != 1 else ''} hurt repo health",
            "description": (
                "These changes were very large or touched many files, "
                "so the health score dropped. Smaller, focused commits are easier to review and safer."
            ),
        })
    if large:
        count = len(large)
        risks.append({
            "id": "r-churn",
            "type": "instability",
            "severity": "medium",
            "title": f"{count} commit{'s' if count != 1 else ''} changed a lot of code at once",
            "description": (
                "“Churn” means a commit added, removed, or rewrote many lines or files. "
                "That makes bugs more likely and code reviews harder."
            ),
        })

    authors = {c["author"] for c in commits}
    if len(authors) <= 2 and len(commits) >= 10:
        risks.append({
            "id": "r-bus",
            "type": "drift",
            "severity": "medium",
            "title": "Only a few people are making most changes",
            "description": (
                f"Just {len(authors)} contributor{'s' if len(authors) != 1 else ''} wrote most of the recent commits. "
                "If they leave, the team may struggle to maintain the project."
            ),
        })

    if not risks:
        risks.append({
            "id": "r-ok",
            "type": "maintainability",
            "severity": "low",
            "title": "Recent changes look healthy",
            "description": (
                "Commits in this window were a reasonable size. "
                "No major warnings from the health checks."
            ),
        })

    return risks


def _graph_for_frontend(graph: dict) -> dict:
    nodes = []
    for node in graph.get("nodes", []):
        node_id = node["id"]
        node_type = node["type"]
        if node_type == "commit":
            label = node_id[:7]
        else:
            label = node_id.split("<")[0].strip() or node_id
        nodes.append({"id": node_id, "label": label, "type": node_type})
    return {"nodes": nodes, "edges": graph.get("edges", [])}


def map_to_frontend(raw: dict) -> dict:
    commits_raw = raw.get("commit_analysis", [])
    ai_summary = raw.get("ai_summary", "")

    commits = []
    # If commits_raw is extremely large, only map the most recent 1000 commits to frontend to save bandwidth/DOM rendering lag!
    display_commits_raw = commits_raw[:1000]
    for i, c in enumerate(display_commits_raw):
        if i == 0:
            explanation = ai_summary
        else:
            explanation = (
                f"Health score: {c['health_score']}/100. "
                f"Changed {c['files_changed']} file(s), added {c['insertions']} lines, "
                f"removed {c['deletions']} lines."
            )
        commits.append({
            "hash": c["hash"][:7],
            "author": c["author"],
            "message": c["message"],
            "files_changed": c["files_changed"],
            "insertions": c["insertions"],
            "deletions": c["deletions"],
            "health_score": c["health_score"],
            "ai_explanation": explanation,
            "timestamp": c.get("timestamp", ""),
        })

    scores = [c["health_score"] for c in commits_raw] or [100]
    avg_health = round(sum(scores) / len(scores))
    authors = {c["author"] for c in commits_raw}

    timeline = []
    chronological = list(reversed(commits_raw))
    total_timeline_len = len(chronological)
    if total_timeline_len > 100:
        # Downsample to 100 points using systematic step sampling
        step = total_timeline_len / 100
        sampled = []
        for index in range(100):
            idx = int(index * step)
            if idx < total_timeline_len:
                sampled.append(chronological[idx])
        # Always make sure the absolute latest commit is included as the final point!
        if chronological and chronological[-1] not in sampled:
            sampled[-1] = chronological[-1]
        chronological = sampled

    for i, c in enumerate(chronological):
        commit_index = i + 1 if total_timeline_len <= 100 else int((i / 99) * total_timeline_len)
        timeline.append({
            "commit": commit_index,
            "score": c["health_score"],
            "date": (c.get("timestamp") or "")[:10] or f"commit-{commit_index}",
        })

    repo_slug = raw.get("repo", "unknown")
    repo_name = repo_slug if "/" in repo_slug else f"repo/{repo_slug}"

    graph_raw = raw.get("graph", {})
    graph_payload = _graph_for_frontend(graph_raw)
    graph_meta = graph_raw.get("meta", {})

    return {
        "repo_name": repo_name,
        "total_commits": raw.get("total_commits", len(commits_raw)),
        "commits_analyzed": raw.get("commits_analyzed", len(commits_raw)),
        "health_score": avg_health,
        "risk_level": _risk_level(avg_health),
        "bus_factor": len(authors) or 1,
        "architecture_stability": min(100, avg_health + 5),
        "health_timeline": timeline,
        "ai_insight": ai_summary,
        "commits": commits,
        "graph": graph_payload,
        "graph_meta": graph_meta,
        "risks": _build_risks(commits_raw),
        "analysis_seconds": raw.get("analysis_seconds"),
        "warnings": raw.get("warnings", []),
        "languages": raw.get("languages", []),
        "hotspots": raw.get("hotspots", []),
        "dangerous_commit": raw.get("dangerous_commit"),
    }
