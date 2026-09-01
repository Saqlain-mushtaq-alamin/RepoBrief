"""GitHub URL handling -- detect and clone repositories."""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

# Matches: https://github.com/user/repo or https://github.com/user/repo.git
GITHUB_URL_PATTERN = re.compile(r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$")


def is_github_url(input_path: str) -> bool:
    """Check if a string looks like a GitHub repository URL.

    Args:
        input_path: The user-provided path string.

    Returns:
        True if it matches the GitHub URL pattern.
    """
    return GITHUB_URL_PATTERN.match(input_path) is not None


def extract_repo_name(url: str) -> str:
    """Extract the repository name from a GitHub URL.

    Args:
        url: GitHub repository URL.

    Returns:
        Repository name (e.g., 'my-repo').
    """
    match = GITHUB_URL_PATTERN.match(url)
    if match:
        return match.group(2)
    return "unknown-repo"


def clone_repo(url: str, target_dir: Path | None = None) -> Path:
    """Clone a GitHub repository to a temporary directory.

    Uses a shallow clone (--depth=1) for speed, since we only need
    the latest state of the code.

    Args:
        url: GitHub repository URL.
        target_dir: Where to clone. If None, uses a temp directory.

    Returns:
        Path to the cloned repository.

    Raises:
        RuntimeError: If cloning fails (git not installed, private repo, etc.).
    """
    if target_dir is None:
        target_dir = Path(tempfile.mkdtemp(prefix="repobrief_"))

    try:
        result = subprocess.run(
            ["git", "clone", "--depth=1", url, str(target_dir)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to clone repository: {result.stderr.strip()}\n"
                f"If this is a private repo, ensure git has access "
                f"(SSH key or credential manager configured)."
            )
        return target_dir
    except FileNotFoundError as err:
        raise RuntimeError(
            "git is not installed or not in PATH. "
            "Install git to clone GitHub repositories, "
            "or download the repo manually and point RepoBrief at the local directory."
        ) from err
    except subprocess.TimeoutExpired as err:
        raise RuntimeError(
            "Cloning timed out after 120 seconds. Check your internet connection and try again."
        ) from err
