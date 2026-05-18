def calculate_health(commit: dict) -> int:
    score = 100

    files_changed = commit.get("files_changed", 0)
    insertions = commit.get("insertions", 0)
    deletions = commit.get("deletions", 0)

    if files_changed > 10:
        score -= 10

    if insertions > 500:
        score -= 15

    if deletions > 300:
        score -= 10

    return max(score, 0)
