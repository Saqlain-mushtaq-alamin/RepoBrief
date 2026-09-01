"""Budget-aware file selector.

Takes scored files and greedily selects them until the token budget is exhausted.
"""

from __future__ import annotations

from repobrief.scanner.models import ScannedFile
from repobrief.scoring.tokenizer import count_tokens

# Default token budget (128k is common for modern LLMs, but we default lower
# to leave room for the system prompt + user question)
DEFAULT_TOKEN_BUDGET: int = 100_000

# Overhead per file: the file header (path, separator lines) adds ~20 tokens
PER_FILE_OVERHEAD_TOKENS: int = 20


def select_files_within_budget(
    scored_files: list[tuple[ScannedFile, float]],
    max_tokens: int = DEFAULT_TOKEN_BUDGET,
) -> tuple[list[ScannedFile], int]:
    """Select files greedily by score until the token budget is exhausted.

    Files are already sorted by score (highest first). We iterate through them
    and include each file if adding it would not exceed the budget.

    No partial file inclusion -- each file is either fully included or skipped.

    Args:
        scored_files: List of (ScannedFile, score) tuples, sorted by score descending.
        max_tokens: Maximum total tokens for all selected files.

    Returns:
        Tuple of:
        - List of selected ScannedFile objects (in score order)
        - Total tokens used by selected files
    """
    selected: list[ScannedFile] = []
    total_tokens: int = 0

    for file, _score in scored_files:
        file_tokens = count_tokens(file.content) + PER_FILE_OVERHEAD_TOKENS

        if total_tokens + file_tokens <= max_tokens:
            selected.append(file)
            total_tokens += file_tokens
        # else: skip this file -- doesn't fit

    return selected, total_tokens


def get_budget_summary(
    total_files_scanned: int,
    files_after_secrets: int,
    files_selected: int,
    tokens_used: int,
    max_tokens: int,
) -> str:
    """Generate a human-readable summary of the file selection process.

    Args:
        total_files_scanned: Number of files found by the scanner.
        files_after_secrets: Number of files after secret filtering.
        files_selected: Number of files included in the digest.
        tokens_used: Total tokens used by selected files.
        max_tokens: The token budget.

    Returns:
        Formatted summary string.
    """
    return (
        f"Selection Summary:\n"
        f"   Files scanned:   {total_files_scanned}\n"
        f"   After filtering: {files_after_secrets}\n"
        f"   Files selected:  {files_selected}\n"
        f"   Tokens used:     {tokens_used:,} / {max_tokens:,} "
        f"({tokens_used / max_tokens * 100:.1f}%)\n"
    )
