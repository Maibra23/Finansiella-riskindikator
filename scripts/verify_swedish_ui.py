#!/usr/bin/env python3
"""
scripts/verify_swedish_ui.py
-----------------------------
Scan all Streamlit UI files under app/ for user-facing English text and
for typographic dashes (em/en dash) that must not appear in UI copy.

Only checks strings that are actually shown to the end user (under app/).
Skips docstrings, DataFrame column names used internally, CSS fragments
inside theme strings, and Streamlit API keys.

Exit code 0  all clean, no violations found.
Exit code 1  violations detected (printed to stdout).

Usage:
    python3 scripts/verify_swedish_ui.py
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = PROJECT_ROOT / "app"

# ---------------------------------------------------------------------------
# English words that should NEVER appear in user-facing strings.
# ---------------------------------------------------------------------------

FORBIDDEN_PHRASES: set[str] = {
    "dashboard", "overview", "score", "average", "download", "filter",
    "select year", "select municipality", "loading", "risk class",
    "contribution", "national average", "high risk", "medium risk",
    "low risk", "number of", "previous year", "current year",
    "compare municipalities",
}

FORBIDDEN_STANDALONE: set[str] = {
    "vs",
}

# Internal DataFrame column names that are NOT user-facing (always skip).
INTERNAL_COLUMN_NAMES: set[str] = {
    "municipality_code", "municipality_name", "year", "kri_score",
    "z_debt", "z_unemployment", "z_dependency", "z_population", "z_tax_base",
    "contribution_debt", "contribution_unemployment", "contribution_dependency",
    "contribution_population", "contribution_tax_base",
    "risk_class", "rank", "debt_per_capita", "unemployment",
    "dependency_ratio", "population_growth", "tax_base_relative",
    "risk_numeric", "geo_code",
}

# Streamlit API keys that MUST be English (framework requirement).
STREAMLIT_API_KEYS: set[str] = {
    "Get Help", "Report a bug", "About",
}

# Strings that are always acceptable regardless of content.
SKIP_PREFIXES = (
    "properties.", "data-testid", "cursor:", "rgba(", "https://", "http://",
)


class Violation:
    __slots__ = ("file", "line", "col", "snippet", "word", "kind")

    def __init__(
        self,
        file: str,
        line: int,
        col: int,
        snippet: str,
        word: str,
        kind: str = "english",
    ):
        self.file = file
        self.line = line
        self.col = col
        self.snippet = snippet
        self.word = word
        self.kind = kind

    def __str__(self) -> str:
        if self.kind == "dash":
            return (
                f"  {self.file}:{self.line}:{self.col}  "
                f'Typographic dash "{self.word}" in UI string: {self.snippet!r}'
            )
        return (
            f"  {self.file}:{self.line}:{self.col}  "
            f'English word "{self.word}" in: {self.snippet!r}'
        )


def _should_skip(raw: str) -> bool:
    """Return True if the string should be entirely skipped."""
    stripped = raw.strip()

    if stripped in INTERNAL_COLUMN_NAMES:
        return True

    if stripped in STREAMLIT_API_KEYS:
        return True

    if any(stripped.startswith(p) for p in SKIP_PREFIXES):
        return True

    # Pure CSS/HTML structural content (no Swedish text expected)
    if stripped.startswith("<style>") or stripped.startswith("<!--"):
        return True
    if stripped.startswith("<link "):
        return True

    return False


def _is_css_or_comment_fragment(raw: str) -> bool:
    """True for theme/CSS chunks where em dash in comments is allowed."""
    if "/*" in raw or "*/" in raw:
        return True
    if "@media" in raw or "!important" in raw:
        return True
    if "rgba(" in raw or "font-family:" in raw:
        return True
    if "stroke-width" in raw and "{" in raw:
        return True
    return False


def _check_dashes(raw: str, filepath: str, lineno: int, col: int) -> list[Violation]:
    """
    Forbid Unicode em dash (U+2014) and en dash (U+2013) in user-facing copy.
    ASCII hyphen in compounds (e.g. z-poäng, KPI-rad) remains allowed.
    """
    if not raw or _should_skip(raw) or _is_css_or_comment_fragment(raw):
        return []

    violations: list[Violation] = []
    snippet = raw[:100].replace("\n", " ")
    if "\u2014" in raw:
        violations.append(
            Violation(filepath, lineno, col, snippet, "em dash (U+2014)", kind="dash")
        )
    if "\u2013" in raw:
        violations.append(
            Violation(filepath, lineno, col, snippet, "en dash (U+2013)", kind="dash")
        )
    return violations


def _clean_for_check(text: str) -> str:
    """Strip HTML tags, format specifiers, CSS, URLs, hex colors."""
    cleaned = re.sub(r"<[^>]+>", " ", text)
    cleaned = re.sub(r"\{[^}]*\}", " ", cleaned)
    cleaned = re.sub(r"%\{[^}]*\}", " ", cleaned)
    cleaned = re.sub(r"&[a-z]+;", " ", cleaned)
    cleaned = re.sub(r"#[0-9A-Fa-f]{3,8}", " ", cleaned)
    cleaned = re.sub(r"https?://\S+", " ", cleaned)
    cleaned = re.sub(r"[\d.,;:!?()\[\]{}<>=/\\|@#$%^&*+~`\"']", " ", cleaned)
    return cleaned.lower()


def _check_string(raw: str, filepath: str, lineno: int, col: int) -> list[Violation]:
    """Check a single user-facing string for forbidden English words."""
    if not raw or len(raw) < 3:
        return []

    if _should_skip(raw):
        return []

    cleaned = _clean_for_check(raw)

    violations: list[Violation] = []

    for phrase in FORBIDDEN_PHRASES:
        pattern = r"\b" + re.escape(phrase) + r"\b"
        if re.search(pattern, cleaned):
            snippet = raw[:80].replace("\n", " ")
            violations.append(Violation(filepath, lineno, col, snippet, phrase))

    words = set(cleaned.split())
    for w in FORBIDDEN_STANDALONE:
        if w in words:
            snippet = raw[:80].replace("\n", " ")
            violations.append(Violation(filepath, lineno, col, snippet, w))

    return violations


def _is_docstring(node: ast.AST, parent_body: list[ast.stmt]) -> bool:
    """Return True if the node is a docstring (first Expr(Constant) in a body)."""
    if not parent_body:
        return False
    first = parent_body[0]
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
        return first.value is node or (hasattr(node, 'lineno') and first.value.lineno == getattr(node, 'lineno', -1) and first.value.col_offset == getattr(node, 'col_offset', -1))
    return False


def _collect_docstring_locations(tree: ast.Module) -> set[tuple[int, int]]:
    """Collect (lineno, col_offset) of all docstrings in the module."""
    locs: set[tuple[int, int]] = set()

    def _check_body(body: list[ast.stmt]) -> None:
        if not body:
            return
        first = body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
            locs.add((first.value.lineno, first.value.col_offset))

    _check_body(tree.body)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            _check_body(node.body)

    return locs


def _collect_dict_keys(tree: ast.Module) -> set[tuple[int, int]]:
    """Collect (lineno, col_offset) of string constants used as dict keys."""
    locs: set[tuple[int, int]] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key in node.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    locs.add((key.lineno, key.col_offset))
    return locs


def _collect_subscript_keys(tree: ast.Module) -> set[tuple[int, int]]:
    """Collect (lineno, col_offset) of strings used in df["col"] subscript access."""
    locs: set[tuple[int, int]] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
            if node.slice.value in INTERNAL_COLUMN_NAMES:
                locs.add((node.slice.lineno, node.slice.col_offset))
    return locs


def _walk_user_facing(tree: ast.Module, filepath: str) -> list[Violation]:
    """Walk AST checking only user-facing strings."""
    violations: list[Violation] = []

    docstring_locs = _collect_docstring_locations(tree)
    dict_key_locs = _collect_dict_keys(tree)
    subscript_locs = _collect_subscript_keys(tree)
    skip_locs = docstring_locs | subscript_locs

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            loc = (node.lineno, node.col_offset)

            if loc in skip_locs:
                continue

            if loc in dict_key_locs:
                if node.value in INTERNAL_COLUMN_NAMES or node.value in STREAMLIT_API_KEYS:
                    continue

            violations.extend(
                _check_string(node.value, filepath, node.lineno, node.col_offset)
            )
            violations.extend(
                _check_dashes(node.value, filepath, node.lineno, node.col_offset)
            )

        elif isinstance(node, ast.JoinedStr):
            for val in node.values:
                if isinstance(val, ast.Constant) and isinstance(val.value, str):
                    loc = (val.lineno, val.col_offset)
                    if loc in skip_locs:
                        continue
                    violations.extend(
                        _check_string(val.value, filepath, val.lineno, val.col_offset)
                    )
                    violations.extend(
                        _check_dashes(val.value, filepath, val.lineno, val.col_offset)
                    )

    return violations


def scan_file(path: Path) -> list[Violation]:
    """Parse a single Python file and return violations."""
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    rel = str(path.relative_to(PROJECT_ROOT))
    return _walk_user_facing(tree, rel)


def main() -> int:
    py_files = sorted(APP_DIR.rglob("*.py"))

    if not py_files:
        print("No Python files found under app/. Nothing to check.")
        return 0

    all_violations: list[Violation] = []

    for pf in py_files:
        all_violations.extend(scan_file(pf))

    seen: set[tuple[str, int, str, str]] = set()
    unique: list[Violation] = []
    for v in all_violations:
        key = (v.file, v.line, v.word, v.kind)
        if key not in seen:
            seen.add(key)
            unique.append(v)

    if not unique:
        print(f"PASS  All {len(py_files)} files under app/ are Swedish-clean.")
        return 0

    print(f"FAIL  {len(unique)} violation(s) in {len(py_files)} files:\n")
    for v in sorted(unique, key=lambda x: (x.file, x.line)):
        print(v)
    print()
    return 1


if __name__ == "__main__":
    sys.exit(main())
