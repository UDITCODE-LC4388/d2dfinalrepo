from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Callable

from app.analyzers.file_analyzer import AnalysisResult, FileAnalyzer
from app.core.config import Settings
from app.services.git_client import CommitChange, GitClient
from app.storage.database import Database, utc_now


@dataclass(slots=True)
class FileState:
    path: str
    language: str
    complexity: float = 0.0
    symbol_count: int = 0
    import_count: int = 0
    line_count: int = 0
    total_churn: int = 0
    touch_count: int = 0
    contributors: dict[str, float] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    last_commit_sha: str | None = None
    last_author_email: str | None = None
    last_modified_at: str | None = None
    is_deleted: bool = False

    @property
    def contributor_count(self) -> int:
        return len(self.contributors)

    def ownership_entropy(self) -> float:
        total = sum(self.contributors.values())
        if total <= 0 or len(self.contributors) <= 1:
            return 0.0
        entropy = 0.0
        for contribution in self.contributors.values():
            share = contribution / total
            entropy -= share * math.log(share)
        return entropy / math.log(len(self.contributors))

    def owner_share(self, author_email: str) -> float:
        total = sum(self.contributors.values())
        if total <= 0:
            return 0.0
        return self.contributors.get(author_email, 0.0) / total

    def hotspot_score(self) -> float:
        return round(
            0.55 * math.log1p(self.total_churn)
            + 0.25 * self.complexity
            + 0.10 * self.contributor_count
            + 0.10 * (self.ownership_entropy() * 10.0),
            4,
        )


class RepositoryAnalyzer:
    def __init__(
        self,
        database: Database,
        settings: Settings,
        git_client: GitClient,
        file_analyzer: FileAnalyzer,
    ) -> None:
        self.database = database
        self.settings = settings
        self.git_client = git_client
        self.file_analyzer = file_analyzer

    def analyze_repository(
        self,
        repo: dict,
        progress_callback: Callable[[float, str], None],
        branch: str | None = None,
        max_commits: int | None = None,
        force_reanalyze: bool = False,
    ) -> dict:
        clone_path = Path(repo["clone_path"])
        progress_callback(0.02, "Preparing Git mirror")
        self.git_client.prepare_repository(repo["repo_url"], clone_path)

        target_branch = self.git_client.infer_default_branch(clone_path, branch or repo["default_branch"])
        commit_limit = max_commits or repo["max_commits"] or self.settings.max_commits_per_sync
        commit_shas = self.git_client.list_commits(clone_path, target_branch, commit_limit)
        if not commit_shas:
            raise RuntimeError("No commits found for the selected branch.")

        progress_callback(0.08, f"Indexed {len(commit_shas)} commits on {target_branch}")
        self.database.clear_analysis(repo["id"])

        file_states: dict[str, FileState] = {}
        commit_rows: list[dict] = []
        commit_file_rows: list[dict] = []
        timeline_rows: list[dict] = []

        for index, sha in enumerate(commit_shas, start=1):
            progress = 0.10 + 0.68 * (index / max(1, len(commit_shas)))
            progress_callback(progress, f"Analyzing commit {index}/{len(commit_shas)} {sha[:8]}")
            commit_row, file_rows, timeline = self._analyze_commit(
                repo_id=repo["id"],
                clone_path=clone_path,
                sha=sha,
                commit_index=index,
                file_states=file_states,
            )
            commit_rows.append(commit_row)
            commit_file_rows.extend(file_rows)
            timeline_rows.extend(timeline)

        head_sha = commit_shas[-1]
        progress_callback(0.82, "Building dependency graph and health projections")
        dependency_edges, architecture_metrics = self._build_dependency_graph(
            repo_id=repo["id"],
            file_states=file_states,
            head_sha=head_sha,
        )
        file_snapshot_rows, hotspot_rows = self._build_file_snapshots(repo["id"], file_states)
        repo_metrics = self._build_repo_metrics(
            repo_id=repo["id"],
            commit_rows=commit_rows,
            file_snapshot_rows=file_snapshot_rows,
            dependency_edges=dependency_edges,
            architecture_metrics=architecture_metrics,
        )

        progress_callback(0.92, "Persisting analysis results")
        self.database.replace_commits(repo["id"], commit_rows, commit_file_rows, timeline_rows)
        self.database.replace_file_snapshots(repo["id"], file_snapshot_rows)
        self.database.replace_dependency_edges(repo["id"], dependency_edges)
        self.database.replace_hotspots(repo["id"], hotspot_rows)
        self.database.replace_repo_metrics(repo["id"], repo_metrics)

        self.database.update_repository(
            repo["id"],
            status="ready",
            default_branch=target_branch,
            last_synced_at=utc_now(),
            last_analyzed_commit=head_sha,
            max_commits=commit_limit,
        )
        progress_callback(1.0, "Analysis complete")
        return {
            "repo_id": repo["id"],
            "default_branch": target_branch,
            "commit_count": len(commit_rows),
            "head_sha": head_sha,
        }

    def _analyze_commit(
        self,
        repo_id: str,
        clone_path,
        sha: str,
        commit_index: int,
        file_states: dict[str, FileState],
    ) -> tuple[dict, list[dict], list[dict]]:
        metadata = self.git_client.read_commit_metadata(clone_path, sha, commit_index)
        changes = self.git_client.read_commit_changes(clone_path, sha)
        trimmed_changes = sorted(
            changes,
            key=lambda change: change.additions + change.deletions,
            reverse=True,
        )[: self.settings.max_changed_files_per_commit]
        parent_ref = f"{sha}^"

        additions = sum(change.additions for change in changes)
        deletions = sum(change.deletions for change in changes)
        complexity_delta_total = 0.0
        commit_languages = Counter()
        touched_hotspots: list[float] = []
        touched_entropies: list[float] = []
        familiarity_scores: list[float] = []
        commit_file_rows: list[dict] = []

        for change in trimmed_changes:
            before_result = self._analyze_revision_file(clone_path, parent_ref, change.old_path or change.path)
            after_result = self._analyze_revision_file(clone_path, sha, change.path)
            language = (
                after_result.language
                if after_result is not None
                else before_result.language
                if before_result is not None
                else self.file_analyzer.detect_language(change.path)
            )

            key_path = change.path
            state = file_states.get(key_path)
            if state is None and change.old_path:
                state = file_states.pop(change.old_path, None)
            if state is None:
                state = FileState(path=key_path, language=language)
            state.path = key_path
            state.language = language

            prior_owner_share = state.owner_share(str(metadata["author_email"]))
            familiarity_scores.append(prior_owner_share)

            before_complexity = before_result.complexity if before_result else 0.0
            before_symbols = before_result.symbol_count if before_result else 0
            before_import_count = before_result.import_count if before_result else 0

            if after_result is not None:
                state.complexity = after_result.complexity
                state.symbol_count = after_result.symbol_count
                state.import_count = after_result.import_count
                state.line_count = after_result.line_count
                state.dependencies = after_result.dependencies
                state.is_deleted = False
            else:
                state.complexity = 0.0
                state.symbol_count = 0
                state.import_count = 0
                state.line_count = 0
                state.dependencies = []
                state.is_deleted = True

            churn = change.additions + change.deletions
            state.total_churn += churn
            state.touch_count += 1
            state.contributors[str(metadata["author_email"])] = (
                state.contributors.get(str(metadata["author_email"]), 0.0) + max(1, churn)
            )
            state.last_commit_sha = sha
            state.last_author_email = str(metadata["author_email"])
            state.last_modified_at = str(metadata["authored_at"])

            current_entropy = state.ownership_entropy()
            current_hotspot = state.hotspot_score()
            touched_entropies.append(current_entropy)
            touched_hotspots.append(current_hotspot)
            complexity_delta_total += state.complexity - before_complexity
            commit_languages[state.language] += 1

            commit_file_rows.append(
                {
                    "repo_id": repo_id,
                    "commit_sha": sha,
                    "path": change.path,
                    "old_path": change.old_path,
                    "change_type": change.change_type,
                    "language": language,
                    "additions": change.additions,
                    "deletions": change.deletions,
                    "complexity_before": round(before_complexity, 4),
                    "complexity_after": round(state.complexity, 4),
                    "symbols_before": before_symbols,
                    "symbols_after": state.symbol_count,
                    "import_count_before": before_import_count,
                    "import_count_after": state.import_count,
                }
            )
            file_states[state.path] = state

        familiarity = sum(familiarity_scores) / len(familiarity_scores) if familiarity_scores else 0.0
        hotspot_exposure = sum(touched_hotspots) / len(touched_hotspots) if touched_hotspots else 0.0
        ownership_entropy = sum(touched_entropies) / len(touched_entropies) if touched_entropies else 0.0
        risk_score = self._score_commit_risk(
            files_changed=len(changes),
            churn=additions + deletions,
            complexity_delta=complexity_delta_total,
            hotspot_exposure=hotspot_exposure,
            familiarity=familiarity,
        )

        commit_row = {
            "repo_id": repo_id,
            "sha": sha,
            "commit_index": commit_index,
            "author_name": metadata["author_name"],
            "author_email": metadata["author_email"],
            "authored_at": metadata["authored_at"],
            "message": metadata["message"],
            "parent_count": metadata["parent_count"],
            "files_changed": len(changes),
            "additions": additions,
            "deletions": deletions,
            "risk_score": risk_score,
            "hotspot_score": round(hotspot_exposure, 4),
            "complexity_delta": round(complexity_delta_total, 4),
            "ownership_entropy": round(ownership_entropy, 4),
            "primary_language": commit_languages.most_common(1)[0][0] if commit_languages else "unknown",
        }
        timeline_rows = [
            self._metric_row(repo_id, sha, commit_index, "commit_risk", risk_score, metadata["authored_at"]),
            self._metric_row(repo_id, sha, commit_index, "commit_churn", float(additions + deletions), metadata["authored_at"]),
            self._metric_row(repo_id, sha, commit_index, "files_changed", float(len(changes)), metadata["authored_at"]),
            self._metric_row(repo_id, sha, commit_index, "complexity_delta", round(complexity_delta_total, 4), metadata["authored_at"]),
            self._metric_row(repo_id, sha, commit_index, "hotspot_exposure", round(hotspot_exposure, 4), metadata["authored_at"]),
        ]
        return commit_row, commit_file_rows, timeline_rows

    def _analyze_revision_file(self, clone_path, rev: str, path: str | None) -> AnalysisResult | None:
        if not path:
            return None
        if not self._should_analyze_path(path):
            return None
        content = self.git_client.read_file_text(clone_path, rev, path, self.settings.max_file_bytes)
        if content is None:
            return None
        return self.file_analyzer.analyze(path, content)

    def _should_analyze_path(self, path: str) -> bool:
        parts = PurePosixPath(path).parts
        if any(part in self.settings.vendor_roots for part in parts):
            return False
        suffix = PurePosixPath(path).suffix.lower()
        return suffix in self.settings.text_extensions

    def _score_commit_risk(
        self,
        files_changed: int,
        churn: int,
        complexity_delta: float,
        hotspot_exposure: float,
        familiarity: float,
    ) -> float:
        files_component = min(files_changed / 25.0, 1.0) * 18.0
        churn_component = min(churn / 800.0, 1.0) * 24.0
        complexity_component = min(abs(complexity_delta) / 30.0, 1.0) * 22.0
        hotspot_component = min(hotspot_exposure / 18.0, 1.0) * 20.0
        familiarity_component = (1.0 - min(max(familiarity, 0.0), 1.0)) * 16.0
        return round(files_component + churn_component + complexity_component + hotspot_component + familiarity_component, 4)

    def _build_dependency_graph(
        self,
        repo_id: str,
        file_states: dict[str, FileState],
        head_sha: str,
    ) -> tuple[list[dict], dict[str, float]]:
        active_states = [state for state in file_states.values() if not state.is_deleted]
        all_paths = {state.path for state in active_states}
        python_modules = self._build_python_module_index(all_paths)

        edges: list[dict] = []
        adjacency: dict[str, set[str]] = defaultdict(set)
        reverse_adjacency: dict[str, set[str]] = defaultdict(set)
        for state in active_states:
            for dependency in state.dependencies:
                target = self._resolve_dependency(state.path, dependency, all_paths, python_modules)
                if not target or target == state.path:
                    continue
                adjacency[state.path].add(target)
                reverse_adjacency[target].add(state.path)
                edges.append(
                    {
                        "repo_id": repo_id,
                        "source_path": state.path,
                        "target_path": target,
                        "edge_type": "imports",
                        "strength": 1.0,
                        "last_seen_commit_sha": head_sha,
                    }
                )

        sccs = self._strongly_connected_components(adjacency, all_paths)
        cycles = [component for component in sccs if len(component) > 1]
        average_out_degree = (sum(len(targets) for targets in adjacency.values()) / len(active_states)) if active_states else 0.0
        average_instability = 0.0
        if active_states:
            instability_total = 0.0
            for state in active_states:
                fan_out = len(adjacency.get(state.path, set()))
                fan_in = len(reverse_adjacency.get(state.path, set()))
                instability_total += fan_out / (fan_in + fan_out) if (fan_in + fan_out) else 0.0
            average_instability = instability_total / len(active_states)

        architecture_metrics = {
            "cyclic_dependencies": float(len(cycles)),
            "coupling_score": round(average_out_degree, 4),
            "instability_score": round(average_instability, 4),
            "dependency_edges": float(len(edges)),
        }
        return edges, architecture_metrics

    def _build_file_snapshots(
        self,
        repo_id: str,
        file_states: dict[str, FileState],
    ) -> tuple[list[dict], list[dict]]:
        snapshot_rows: list[dict] = []
        hotspot_rows: list[dict] = []
        active_states = [state for state in file_states.values() if not state.is_deleted]
        for state in file_states.values():
            snapshot = {
                "repo_id": repo_id,
                "path": state.path,
                "language": state.language,
                "complexity": round(state.complexity, 4),
                "symbol_count": state.symbol_count,
                "import_count": state.import_count,
                "line_count": state.line_count,
                "total_churn": state.total_churn,
                "touch_count": state.touch_count,
                "contributor_count": state.contributor_count,
                "ownership_entropy": round(state.ownership_entropy(), 4),
                "hotspot_score": round(state.hotspot_score(), 4),
                "dependencies_json": json.dumps(state.dependencies),
                "contributors_json": json.dumps(state.contributors),
                "last_commit_sha": state.last_commit_sha,
                "last_author_email": state.last_author_email,
                "last_modified_at": state.last_modified_at,
                "is_deleted": int(state.is_deleted),
            }
            snapshot_rows.append(snapshot)
            if not state.is_deleted:
                hotspot_rows.append(
                    {
                        "repo_id": repo_id,
                        "path": state.path,
                        "language": state.language,
                        "churn": state.total_churn,
                        "complexity": round(state.complexity, 4),
                        "contributors": state.contributor_count,
                        "ownership_entropy": round(state.ownership_entropy(), 4),
                        "hotspot_score": round(state.hotspot_score(), 4),
                        "last_commit_sha": state.last_commit_sha,
                    }
                )

        hotspot_rows.sort(key=lambda row: (row["hotspot_score"], row["churn"]), reverse=True)
        return snapshot_rows, hotspot_rows[: max(25, len(active_states))]

    def _build_repo_metrics(
        self,
        repo_id: str,
        commit_rows: list[dict],
        file_snapshot_rows: list[dict],
        dependency_edges: list[dict],
        architecture_metrics: dict[str, float],
    ) -> dict[str, dict]:
        active_files = [row for row in file_snapshot_rows if row["is_deleted"] == 0]
        languages = Counter(row["language"] for row in active_files)
        avg_complexity = (
            sum(row["complexity"] for row in active_files) / len(active_files) if active_files else 0.0
        )
        avg_hotspot = (
            sum(row["hotspot_score"] for row in active_files) / len(active_files) if active_files else 0.0
        )
        avg_commit_risk = (
            sum(row["risk_score"] for row in commit_rows) / len(commit_rows) if commit_rows else 0.0
        )
        ownership_entropy = (
            sum(row["ownership_entropy"] for row in active_files) / len(active_files) if active_files else 0.0
        )
        bus_factor = self._estimate_bus_factor(active_files)
        code_health = max(0.0, 100.0 - min(65.0, avg_complexity * 1.8 + avg_hotspot * 1.7 + avg_commit_risk * 0.3))
        team_health = max(0.0, 100.0 - min(65.0, ownership_entropy * 35.0 + max(0.0, 4.0 - bus_factor) * 10.0))
        architecture_health = max(
            0.0,
            100.0
            - min(
                65.0,
                architecture_metrics["cyclic_dependencies"] * 8.0
                + architecture_metrics["coupling_score"] * 6.0
                + architecture_metrics["instability_score"] * 18.0,
            ),
        )
        temporal_health = max(0.0, 100.0 - min(65.0, avg_commit_risk * 0.45 + avg_hotspot * 1.25))
        health_index = round(
            0.35 * code_health
            + 0.20 * team_health
            + 0.25 * architecture_health
            + 0.20 * temporal_health,
            4,
        )

        top_risks: list[str] = []
        if architecture_metrics["cyclic_dependencies"] > 0:
            top_risks.append("Cyclic dependencies detected in the current import graph.")
        if avg_hotspot > 8:
            top_risks.append("High hotspot concentration in frequently changed files.")
        if avg_commit_risk > 45:
            top_risks.append("Recent commit stream shows elevated merge and regression risk.")
        if bus_factor < 3:
            top_risks.append("Low bus factor across active files.")
        if not top_risks:
            top_risks.append("No critical repository-wide risks detected in the latest analysis window.")

        return {
            "health_index": {
                "value": health_index,
                "payload": {"languages": dict(languages), "top_risks": top_risks},
            },
            "code_health": {"value": round(code_health, 4)},
            "team_health": {"value": round(team_health, 4)},
            "architecture_health": {"value": round(architecture_health, 4)},
            "temporal_health": {"value": round(temporal_health, 4)},
            "total_commits": {"value": float(len(commit_rows))},
            "active_files": {"value": float(len(active_files))},
            "avg_complexity": {"value": round(avg_complexity, 4)},
            "avg_hotspot_score": {"value": round(avg_hotspot, 4)},
            "avg_commit_risk": {"value": round(avg_commit_risk, 4)},
            "bus_factor": {"value": float(bus_factor)},
            "ownership_entropy": {"value": round(ownership_entropy, 4)},
            "cyclic_dependencies": {"value": architecture_metrics["cyclic_dependencies"]},
            "coupling_score": {"value": architecture_metrics["coupling_score"]},
            "instability_score": {"value": architecture_metrics["instability_score"]},
            "dependency_edges": {"value": architecture_metrics["dependency_edges"]},
        }

    def _build_python_module_index(self, paths: set[str]) -> dict[str, str]:
        module_index: dict[str, str] = {}
        for path in paths:
            pure_path = PurePosixPath(path)
            if pure_path.suffix != ".py":
                continue
            if pure_path.name == "__init__.py":
                module_name = ".".join(pure_path.parts[:-1])
            else:
                module_name = ".".join(pure_path.with_suffix("").parts)
            module_index[module_name] = path
        return module_index

    def _resolve_dependency(
        self,
        source_path: str,
        dependency: str,
        all_paths: set[str],
        python_modules: dict[str, str],
    ) -> str | None:
        language = self.file_analyzer.detect_language(source_path)
        if language in {"javascript", "typescript"} and dependency.startswith("."):
            return self._resolve_relative_import(source_path, dependency, all_paths)
        if language == "python":
            normalized = dependency.strip()
            if normalized.startswith("."):
                relative = self._resolve_python_relative_import(source_path, normalized)
                return python_modules.get(relative)
            return python_modules.get(normalized)
        if language == "java":
            candidate = dependency.replace(".", "/") + ".java"
            if candidate in all_paths:
                return candidate
        if language in {"c", "cpp"}:
            candidate = self._resolve_relative_include(source_path, dependency, all_paths)
            if candidate:
                return candidate
        return None

    def _resolve_relative_import(self, source_path: str, dependency: str, all_paths: set[str]) -> str | None:
        base = PurePosixPath(source_path).parent
        raw_target = (base / dependency).as_posix()
        candidates = [
            raw_target,
            f"{raw_target}.ts",
            f"{raw_target}.tsx",
            f"{raw_target}.js",
            f"{raw_target}.jsx",
            f"{raw_target}/index.ts",
            f"{raw_target}/index.tsx",
            f"{raw_target}/index.js",
            f"{raw_target}/index.jsx",
        ]
        for candidate in candidates:
            normalized = PurePosixPath(candidate).as_posix()
            if normalized in all_paths:
                return normalized
        return None

    def _resolve_python_relative_import(self, source_path: str, dependency: str) -> str:
        leading_dots = len(dependency) - len(dependency.lstrip("."))
        module_part = dependency.lstrip(".")
        source_module = PurePosixPath(source_path).with_suffix("")
        base_parts = list(source_module.parts[:-1])
        keep = max(0, len(base_parts) - max(leading_dots - 1, 0))
        resolved_parts = base_parts[:keep]
        if module_part:
            resolved_parts.extend(module_part.split("."))
        return ".".join(part for part in resolved_parts if part)

    def _resolve_relative_include(self, source_path: str, dependency: str, all_paths: set[str]) -> str | None:
        candidate = PurePosixPath(source_path).parent / dependency
        normalized = candidate.as_posix()
        return normalized if normalized in all_paths else None

    def _estimate_bus_factor(self, active_files: list[dict]) -> int:
        contributor_weights: Counter[str] = Counter()
        total_weight = 0.0
        for row in active_files:
            contributors = json.loads(row["contributors_json"])
            if not contributors:
                continue
            weight = max(row["hotspot_score"], 1.0)
            total_weight += weight
            primary_owner, share = max(contributors.items(), key=lambda item: item[1])
            contributor_weights[primary_owner] += weight * (share / max(sum(contributors.values()), 1.0))
        covered = 0.0
        owners_used = 0
        for _, contribution in contributor_weights.most_common():
            owners_used += 1
            covered += contribution
            if total_weight and covered / total_weight >= 0.65:
                return owners_used
        return owners_used

    def _strongly_connected_components(
        self,
        adjacency: dict[str, set[str]],
        all_nodes: set[str],
    ) -> list[list[str]]:
        index = 0
        stack: list[str] = []
        indices: dict[str, int] = {}
        lowlinks: dict[str, int] = {}
        on_stack: set[str] = set()
        components: list[list[str]] = []

        def strong_connect(node: str) -> None:
            nonlocal index
            indices[node] = index
            lowlinks[node] = index
            index += 1
            stack.append(node)
            on_stack.add(node)

            for neighbor in adjacency.get(node, set()):
                if neighbor not in indices:
                    strong_connect(neighbor)
                    lowlinks[node] = min(lowlinks[node], lowlinks[neighbor])
                elif neighbor in on_stack:
                    lowlinks[node] = min(lowlinks[node], indices[neighbor])

            if lowlinks[node] == indices[node]:
                component: list[str] = []
                while stack:
                    member = stack.pop()
                    on_stack.remove(member)
                    component.append(member)
                    if member == node:
                        break
                components.append(component)

        for node in all_nodes:
            if node not in indices:
                strong_connect(node)
        return components

    def _metric_row(
        self,
        repo_id: str,
        sha: str,
        commit_index: int,
        metric_key: str,
        value: float,
        measured_at: str,
    ) -> dict:
        return {
            "repo_id": repo_id,
            "commit_sha": sha,
            "commit_index": commit_index,
            "metric_key": metric_key,
            "value": float(value),
            "measured_at": measured_at,
        }
