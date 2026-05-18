from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import PurePosixPath


@dataclass(slots=True)
class AnalysisResult:
    language: str
    line_count: int
    code_lines: int
    blank_lines: int
    comment_lines: int
    function_count: int
    class_count: int
    symbol_count: int
    import_count: int
    complexity: float
    dependencies: list[str]


class FileAnalyzer:
    LANGUAGE_BY_EXTENSION = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".mjs": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".mts": "typescript",
        ".cts": "typescript",
        ".java": "java",
        ".go": "go",
        ".c": "c",
        ".h": "c",
        ".cc": "cpp",
        ".cpp": "cpp",
        ".cxx": "cpp",
        ".hpp": "cpp",
        ".hh": "cpp",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".sql": "sql",
        ".md": "markdown",
    }

    COMPLEXITY_PATTERNS = {
        "javascript": re.compile(r"\b(if|for|while|case|catch|switch)\b|&&|\|\|"),
        "typescript": re.compile(r"\b(if|for|while|case|catch|switch)\b|&&|\|\|"),
        "java": re.compile(r"\b(if|for|while|case|catch|switch)\b|&&|\|\|"),
        "go": re.compile(r"\b(if|for|switch|select|case)\b|&&|\|\|"),
        "c": re.compile(r"\b(if|for|while|case|switch)\b|&&|\|\|"),
        "cpp": re.compile(r"\b(if|for|while|case|switch|catch)\b|&&|\|\|"),
        "sql": re.compile(r"\b(CASE|WHEN|AND|OR)\b"),
    }

    def detect_language(self, path: str) -> str:
        suffix = PurePosixPath(path).suffix.lower()
        return self.LANGUAGE_BY_EXTENSION.get(suffix, "text")

    def analyze(self, path: str, content: str) -> AnalysisResult:
        language = self.detect_language(path)
        if language == "python":
            return self._analyze_python(content)
        return self._analyze_generic(language=language, content=content)

    def _line_stats(self, content: str) -> tuple[int, int, int, int]:
        line_count = 0
        blank_lines = 0
        comment_lines = 0
        code_lines = 0
        for line in content.splitlines():
            line_count += 1
            stripped = line.strip()
            if not stripped:
                blank_lines += 1
                continue
            if stripped.startswith(("#", "//", "/*", "*", "--")):
                comment_lines += 1
                continue
            code_lines += 1
        return line_count, code_lines, blank_lines, comment_lines

    def _analyze_python(self, content: str) -> AnalysisResult:
        line_count, code_lines, blank_lines, comment_lines = self._line_stats(content)
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return AnalysisResult(
                language="python",
                line_count=line_count,
                code_lines=code_lines,
                blank_lines=blank_lines,
                comment_lines=comment_lines,
                function_count=0,
                class_count=0,
                symbol_count=0,
                import_count=0,
                complexity=1.0 if code_lines else 0.0,
                dependencies=[],
            )

        function_count = 0
        class_count = 0
        import_count = 0
        dependencies: list[str] = []
        complexity = 1.0 if code_lines else 0.0

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_count += 1
            elif isinstance(node, ast.ClassDef):
                class_count += 1
            elif isinstance(node, ast.Import):
                import_count += len(node.names)
                dependencies.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                import_count += len(node.names)
                prefix = "." * node.level
                module = node.module or ""
                dependencies.append(f"{prefix}{module}".strip())
            elif isinstance(
                node,
                (
                    ast.If,
                    ast.For,
                    ast.AsyncFor,
                    ast.While,
                    ast.Try,
                    ast.With,
                    ast.AsyncWith,
                    ast.ExceptHandler,
                    ast.Match,
                ),
            ):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += max(1, len(node.values) - 1)

        return AnalysisResult(
            language="python",
            line_count=line_count,
            code_lines=code_lines,
            blank_lines=blank_lines,
            comment_lines=comment_lines,
            function_count=function_count,
            class_count=class_count,
            symbol_count=function_count + class_count,
            import_count=import_count,
            complexity=complexity,
            dependencies=sorted({dep for dep in dependencies if dep}),
        )

    def _extract_dependencies(self, language: str, content: str) -> list[str]:
        dependencies: set[str] = set()
        if language in {"javascript", "typescript"}:
            patterns = [
                re.compile(r"""import\s+.*?\s+from\s+['"]([^'"]+)['"]"""),
                re.compile(r"""require\(\s*['"]([^'"]+)['"]\s*\)"""),
                re.compile(r"""export\s+.*?\s+from\s+['"]([^'"]+)['"]"""),
                re.compile(r"""import\(\s*['"]([^'"]+)['"]\s*\)"""),
            ]
            for pattern in patterns:
                dependencies.update(pattern.findall(content))
        elif language == "java":
            dependencies.update(re.findall(r"^\s*import\s+([\w\.]+);", content, re.MULTILINE))
        elif language == "go":
            dependencies.update(re.findall(r'"([^"]+)"', content))
        elif language in {"c", "cpp"}:
            dependencies.update(re.findall(r'#include\s+[<"]([^">]+)[">]', content))
        elif language == "sql":
            dependencies.update(
                match[1].lower()
                for match in re.findall(r"\b(from|join)\s+([A-Za-z0-9_\.]+)", content, re.IGNORECASE)
            )
        return sorted(dep for dep in dependencies if dep)

    def _analyze_generic(self, language: str, content: str) -> AnalysisResult:
        line_count, code_lines, blank_lines, comment_lines = self._line_stats(content)
        dependencies = self._extract_dependencies(language, content)
        function_count = 0
        class_count = 0

        if language in {"javascript", "typescript"}:
            function_count = len(
                re.findall(r"\bfunction\b|\=\>\s*\{|\b[a-zA-Z_][\w]*\s*\([^)]*\)\s*\{", content)
            )
            class_count = len(re.findall(r"\bclass\s+[A-Za-z_]\w*", content))
        elif language == "java":
            function_count = len(
                re.findall(
                    r"(public|private|protected)?\s*(static\s+)?[\w<>\[\]]+\s+[A-Za-z_]\w*\s*\([^;]*\)\s*\{",
                    content,
                )
            )
            class_count = len(re.findall(r"\b(class|interface|enum)\s+[A-Za-z_]\w*", content))
        elif language == "go":
            function_count = len(re.findall(r"\bfunc\s+(\([^)]+\)\s+)?[A-Za-z_]\w*\s*\(", content))
            class_count = len(re.findall(r"\btype\s+[A-Za-z_]\w*\s+(struct|interface)\b", content))
        elif language in {"c", "cpp"}:
            function_count = len(
                re.findall(r"\b[A-Za-z_]\w*\s+\*?[A-Za-z_]\w*\s*\([^;{)]*\)\s*\{", content)
            )
            class_count = len(re.findall(r"\b(class|struct)\s+[A-Za-z_]\w*", content))

        complexity_pattern = self.COMPLEXITY_PATTERNS.get(language)
        complexity = float(1 + len(complexity_pattern.findall(content))) if complexity_pattern else float(1 if code_lines else 0)

        return AnalysisResult(
            language=language,
            line_count=line_count,
            code_lines=code_lines,
            blank_lines=blank_lines,
            comment_lines=comment_lines,
            function_count=function_count,
            class_count=class_count,
            symbol_count=function_count + class_count,
            import_count=len(dependencies),
            complexity=complexity,
            dependencies=dependencies,
        )
