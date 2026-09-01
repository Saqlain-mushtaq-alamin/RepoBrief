"""File relevance scoring engine.

Assigns a relevance score (0.0-1.0) to each ScannedFile based on:
- Git recency (how recently the file was modified)
- File size (smaller files score higher)
- Centrality (how many other files import/reference this file)
- Keyword overlap (in chat mode, overlap with the user's question)
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from pathlib import Path

from repobrief.scanner.models import ScannedFile

# -- Weight Configurations -----------------------------------------------------

# Weights for EXPORT mode (no user question)
EXPORT_WEIGHTS = {
    "recency": 0.35,
    "size": 0.25,
    "centrality": 0.40,
    "keyword": 0.0,
}

# Weights for CHAT mode (user asked a question)
CHAT_WEIGHTS = {
    "recency": 0.25,
    "size": 0.20,
    "centrality": 0.25,
    "keyword": 0.30,
}

# -- Import/Reference Parsing --------------------------------------------------

# Regex patterns to detect imports in various languages
IMPORT_PATTERNS = [
    # Python: import foo, from foo import bar
    re.compile(r"^\s*(?:from|import)\s+([\w.]+)", re.MULTILINE),
    # JavaScript/TypeScript: import ... from 'foo', require('foo')
    re.compile(r"""(?:import\s+.*\s+from\s+|require\s*\(\s*)['"]([^'"]+)['"]""", re.MULTILINE),
    # Go: import "foo/bar"
    re.compile(r'import\s+"([^"]+)"', re.MULTILINE),
    # Rust: use foo::bar
    re.compile(r"^\s*use\s+([\w:]+)", re.MULTILINE),
    # Java/Kotlin: import foo.bar.Baz
    re.compile(r"^\s*import\s+([\w.]+)", re.MULTILINE),
]


def _extract_imports(content: str) -> set[str]:
    """Extract imported module/file names from source code.

    Returns a set of raw import strings (module names, relative paths, etc.).
    This is intentionally simple -- it doesn't resolve paths, just extracts
    the string used in the import statement.
    """
    imports: set[str] = set()
    for pattern in IMPORT_PATTERNS:
        for match in pattern.finditer(content):
            imports.add(match.group(1))
    return imports


def compute_centrality_map(files: list[ScannedFile]) -> dict[Path, int]:
    """Compute how many other files reference each file (import centrality).

    For each file, we:
    1. Extract its import statements
    2. Check if any import string matches another file's name/path
    3. Increment that file's centrality counter

    Args:
        files: List of ScannedFile objects.

    Returns:
        Dict mapping each file's relative_path to its centrality count
        (number of other files that import it).
    """
    # Build a lookup: filename stem -> relative path
    # e.g., "helper" -> Path("utils/helper.py")
    file_stems: dict[str, Path] = {}
    file_names: dict[str, Path] = {}
    for f in files:
        file_stems[f.relative_path.stem] = f.relative_path
        file_names[f.relative_path.name] = f.relative_path

    centrality: dict[Path, int] = {f.relative_path: 0 for f in files}

    for f in files:
        if not f.content:
            continue
        imports = _extract_imports(f.content)
        for imp in imports:
            # Try to match import to a file in the repo
            # Check: import path ends with a file stem we know
            imp_parts = imp.replace("::", ".").replace("/", ".").split(".")
            for part in imp_parts:
                if part in file_stems and file_stems[part] != f.relative_path:
                    centrality[file_stems[part]] += 1
                    break

    return centrality


# -- Individual Score Functions ------------------------------------------------


def _recency_score(last_modified: datetime | None) -> float:
    """Score based on how recently the file was modified in git.

    Returns:
        0.0-1.0: 1.0 for just modified, approaches 0 for very old files.
        0.5 if no git data available (neutral).
    """
    if last_modified is None:
        return 0.5  # Neutral -- no data

    now = datetime.now(timezone.utc)
    if last_modified.tzinfo is None:
        # Assume UTC if no timezone
        last_modified = last_modified.replace(tzinfo=timezone.utc)

    days_ago = max(0, (now - last_modified).days)
    return 1.0 / (1.0 + days_ago / 30.0)


def _size_score(size_bytes: int) -> float:
    """Score based on file size -- smaller files score higher.

    Returns:
        0.0-1.0: 1.0 for tiny files, approaches 0 for very large files.
    """
    return 1.0 / (1.0 + size_bytes / 2048.0)


def _centrality_score(num_importers: int) -> float:
    """Score based on how many other files import this one.

    Returns:
        0.0-1.0: 0.0 for unreferenced files, approaches 1.0 for heavily imported files.
    """
    if num_importers <= 0:
        return 0.0
    return min(1.0, math.log(1 + num_importers) / math.log(1 + 10))


def _keyword_score(file: ScannedFile, question_keywords: set[str]) -> float:
    """Score based on keyword overlap between the file and the user's question.

    Checks both the file path and the first 500 chars of content.

    Args:
        file: The ScannedFile to score.
        question_keywords: Set of lowercased keywords from the user's question.

    Returns:
        0.0-1.0: fraction of question keywords found in the file.
    """
    if not question_keywords:
        return 0.0

    # Build file text to search (path + start of content)
    file_text = str(file.relative_path).lower() + " "
    file_text += file.content[:500].lower() if file.content else ""

    file_words = set(re.findall(r"\w+", file_text))
    overlap = question_keywords & file_words

    return len(overlap) / len(question_keywords)


def _extract_keywords(text: str) -> set[str]:
    """Extract meaningful keywords from a text string (e.g., user's question).

    Strips common stop words and returns lowercased unique words.
    """
    stop_words = {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "can",
        "shall",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "and",
        "but",
        "or",
        "not",
        "no",
        "nor",
        "so",
        "yet",
        "both",
        "either",
        "neither",
        "each",
        "every",
        "all",
        "any",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "than",
        "too",
        "very",
        "just",
        "about",
        "up",
        "out",
        "if",
        "then",
        "what",
        "where",
        "when",
        "how",
        "why",
        "who",
        "which",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "i",
        "me",
        "my",
        "we",
        "our",
        "you",
        "your",
        "he",
        "she",
        "they",
        "them",
        "their",
        "him",
        "her",
    }
    words = set(re.findall(r"\w+", text.lower()))
    return words - stop_words


# -- Main Scoring Function -----------------------------------------------------


def score_files(
    files: list[ScannedFile],
    question: str | None = None,
) -> list[tuple[ScannedFile, float]]:
    """Score all files and return them sorted by relevance (highest first).

    Args:
        files: List of ScannedFile objects to score.
        question: Optional user question (enables keyword scoring).

    Returns:
        List of (ScannedFile, score) tuples, sorted by score descending.
    """
    # Choose weight configuration
    weights = CHAT_WEIGHTS if question else EXPORT_WEIGHTS

    # Compute centrality map
    centrality_map = compute_centrality_map(files)

    # Extract question keywords if in chat mode
    question_keywords = _extract_keywords(question) if question else set()

    scored: list[tuple[ScannedFile, float]] = []

    for file in files:
        r_score = _recency_score(file.last_modified)
        s_score = _size_score(file.size_bytes)
        c_score = _centrality_score(centrality_map.get(file.relative_path, 0))
        k_score = _keyword_score(file, question_keywords) if question else 0.0

        total = (
            weights["recency"] * r_score
            + weights["size"] * s_score
            + weights["centrality"] * c_score
            + weights["keyword"] * k_score
        )

        scored.append((file, round(total, 4)))

    # Sort by score descending, then by path for stability
    scored.sort(key=lambda x: (-x[1], str(x[0].relative_path)))

    return scored
