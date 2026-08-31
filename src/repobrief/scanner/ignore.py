"""Ignore-rule management: .gitignore parsing + built-in default rules."""

from __future__ import annotations

from pathlib import Path

import pathspec

# Built-in ignore patterns — ALWAYS excluded regardless of .gitignore content.
# Format: gitignore-style glob patterns.
DEFAULT_IGNORE_PATTERNS: list[str] = [
    # Version control
    ".git/",
    ".svn/",
    ".hg/",
    # Dependencies
    "node_modules/",
    "vendor/",
    "bower_components/",
    ".venv/",
    "venv/",
    "env/",
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    # Build outputs
    "dist/",
    "build/",
    "out/",
    "target/",
    "*.egg-info/",
    # Lock files (large, low-information-density)
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "Pipfile.lock",
    "poetry.lock",
    "composer.lock",
    "Gemfile.lock",
    "Cargo.lock",
    # IDE / editor
    ".idea/",
    ".vscode/",
    "*.swp",
    "*.swo",
    ".DS_Store",
    "Thumbs.db",
    # Media / binary (common extensions)
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.bmp",
    "*.ico",
    "*.svg",
    "*.webp",
    "*.mp3",
    "*.mp4",
    "*.avi",
    "*.mov",
    "*.wav",
    "*.flac",
    "*.pdf",
    "*.zip",
    "*.tar",
    "*.gz",
    "*.rar",
    "*.7z",
    "*.exe",
    "*.dll",
    "*.so",
    "*.dylib",
    "*.bin",
    "*.dat",
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    "*.woff",
    "*.woff2",
    "*.ttf",
    "*.eot",
    "*.otf",
    # Misc
    ".coverage",
    "htmlcov/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    ".tox/",
    ".nox/",
]


class IgnoreRules:
    """Combines .gitignore rules with built-in default ignore patterns.

    Usage:
        rules = IgnoreRules(repo_root=Path("/path/to/repo"))
        if rules.should_ignore(Path("node_modules/express/index.js")):
            # skip this file
    """

    def __init__(self, repo_root: Path, extra_exclude: list[str] | None = None):
        """Initialize ignore rules.

        Args:
            repo_root: Root directory of the repository being scanned.
            extra_exclude: Additional glob patterns to exclude (from user config / CLI flags).
        """
        patterns: list[str] = list(DEFAULT_IGNORE_PATTERNS)

        # Load .gitignore if it exists
        gitignore_path = repo_root / ".gitignore"
        if gitignore_path.is_file():
            gitignore_content = gitignore_path.read_text(encoding="utf-8", errors="ignore")
            for line in gitignore_content.splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    patterns.append(stripped)

        # Load .git/info/exclude if it exists
        git_exclude_path = repo_root / ".git" / "info" / "exclude"
        if git_exclude_path.is_file():
            exclude_content = git_exclude_path.read_text(encoding="utf-8", errors="ignore")
            for line in exclude_content.splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    patterns.append(stripped)

        # Add user-supplied extra excludes
        if extra_exclude:
            patterns.extend(extra_exclude)

        self._spec = pathspec.PathSpec.from_lines("gitignore", patterns)

    def should_ignore(self, relative_path: Path) -> bool:
        """Check if a file (given as a path relative to repo root) should be ignored.

        Args:
            relative_path: Path relative to the repository root.

        Returns:
            True if the file matches any ignore rule.
        """
        # pathspec expects forward-slash separated strings
        return self._spec.match_file(str(relative_path.as_posix()))
