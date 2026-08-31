"""Recursive directory walker — the core of the scanner module."""

from __future__ import annotations

import os
from pathlib import Path

from repobrief.scanner.git_utils import get_file_last_commit_dates, is_git_repo
from repobrief.scanner.ignore import IgnoreRules
from repobrief.scanner.models import ScannedFile

# Maximum file size to read (5 MB). Files larger than this are skipped.
MAX_FILE_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB

# Heuristic: if more than this fraction of a file's first N bytes are
# non-text characters, treat it as binary.
BINARY_CHECK_BYTES: int = 8192
BINARY_THRESHOLD: float = 0.30  # 30% non-text bytes -> binary


def is_binary_file(file_path: Path) -> bool:
    """Heuristically detect whether a file is binary.

    Reads the first 8KB of the file and checks the ratio of
    non-text bytes (control characters excluding common whitespace).

    Args:
        file_path: Path to the file to check.

    Returns:
        True if the file appears to be binary.
    """
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(BINARY_CHECK_BYTES)
    except (OSError, PermissionError):
        return True  # If we can't read it, treat as binary (skip it)

    if not chunk:
        return False  # Empty file is not binary

    # Count bytes that are NOT normal text characters
    # Normal text: printable ASCII (32-126), tab (9), newline (10), carriage return (13)
    text_chars = set(range(32, 127)) | {9, 10, 13}
    non_text = sum(1 for byte in chunk if byte not in text_chars)

    return (non_text / len(chunk)) > BINARY_THRESHOLD


def scan_repository(
    repo_root: Path,
    extra_exclude: list[str] | None = None,
    max_file_size: int = MAX_FILE_SIZE_BYTES,
    load_content: bool = True,
) -> list[ScannedFile]:
    """Scan a repository directory and return a list of ScannedFile objects.

    This is the main entry point for the scanner module. It:
    1. Validates the repo_root path
    2. Builds ignore rules (.gitignore + defaults + user overrides)
    3. Recursively walks the directory tree
    4. Filters out ignored, binary, and oversized files
    5. Optionally loads file content
    6. Optionally fetches git metadata (last commit dates)

    Args:
        repo_root: Absolute path to the repository root directory.
        extra_exclude: Additional glob patterns to exclude.
        max_file_size: Skip files larger than this (bytes). Default 5MB.
        load_content: If True, read and store file content. If False, content is empty.

    Returns:
        List of ScannedFile objects, sorted by relative path.

    Raises:
        FileNotFoundError: If repo_root does not exist.
        NotADirectoryError: If repo_root is not a directory.
    """
    repo_root = Path(repo_root).resolve()

    if not repo_root.exists():
        raise FileNotFoundError(f"Repository path does not exist: {repo_root}")
    if not repo_root.is_dir():
        raise NotADirectoryError(f"Repository path is not a directory: {repo_root}")

    ignore_rules = IgnoreRules(repo_root, extra_exclude)
    scanned_files: list[ScannedFile] = []

    for dirpath, dirnames, filenames in os.walk(repo_root, topdown=True):
        current_dir = Path(dirpath)

        # Filter out ignored directories IN PLACE (prevents os.walk from descending)
        dirnames[:] = [
            d
            for d in dirnames
            if not ignore_rules.should_ignore((current_dir / d).relative_to(repo_root))
        ]

        for filename in filenames:
            file_path = current_dir / filename
            relative_path = file_path.relative_to(repo_root)

            # Check ignore rules
            if ignore_rules.should_ignore(relative_path):
                continue

            # Check file size
            try:
                file_size = file_path.stat().st_size
            except OSError:
                continue  # Can't stat -> skip

            if file_size > max_file_size:
                continue

            if file_size == 0:
                continue  # Skip empty files

            # Check if binary
            if is_binary_file(file_path):
                continue

            # Read content
            content = ""
            if load_content:
                try:
                    content = file_path.read_text(encoding="utf-8", errors="replace")
                except (OSError, PermissionError):
                    continue  # Can't read -> skip

            scanned_files.append(
                ScannedFile(
                    path=file_path,
                    relative_path=relative_path,
                    size_bytes=file_size,
                    content=content,
                    extension=file_path.suffix.lower(),
                )
            )

    # Sort by relative path for deterministic output
    scanned_files.sort(key=lambda f: str(f.relative_path))

    # Fetch git metadata if this is a git repo
    try:
        if is_git_repo(repo_root) and scanned_files:
            dates = get_file_last_commit_dates(
                repo_root, [f.path for f in scanned_files]
            )
            for scanned_file in scanned_files:
                scanned_file.last_modified = dates.get(scanned_file.path)
    except Exception:
        # Git metadata is a nice-to-have -- if it fails, continue without it
        # The scoring module will use neutral scores for recency
        pass

    return scanned_files
