"""Git metadata extraction utilities."""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path


def is_git_repo(directory: Path) -> bool:
    """Check if a directory is inside a git repository.

    Args:
        directory: Path to check.

    Returns:
        True if the directory is within a git repo.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(directory),
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0 and result.stdout.strip() == "true"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_file_last_commit_dates(
    repo_root: Path, file_paths: list[Path]
) -> dict[Path, datetime | None]:
    """Get the last commit date for each file in a git repository.

    Args:
        repo_root: Root of the git repository.
        file_paths: List of absolute file paths to look up.

    Returns:
        Dict mapping each file path to its last commit datetime (or None if unknown).
    """
    results: dict[Path, datetime | None] = {}

    for file_path in file_paths:
        try:
            relative = file_path.relative_to(repo_root)
            result = subprocess.run(
                ["git", "log", "-1", "--format=%aI", "--", str(relative)],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                date_str = result.stdout.strip()
                results[file_path] = datetime.fromisoformat(date_str)
            else:
                results[file_path] = None
        except (subprocess.TimeoutExpired, ValueError, OSError):
            results[file_path] = None

    return results
