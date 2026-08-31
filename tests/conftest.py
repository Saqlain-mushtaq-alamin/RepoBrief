"""Shared pytest fixtures for all RepoBrief tests."""

from pathlib import Path

import pytest


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """Create a minimal fake repository structure for testing.

    Returns the path to the temporary directory containing:
      - main.py (small Python file)
      - utils/helper.py (nested file)
      - README.md (markdown file)
      - .gitignore (with node_modules ignored)
      - node_modules/pkg/index.js (should be ignored)
    """
    # Root files
    (tmp_path / "main.py").write_text("print('hello world')\n")
    (tmp_path / "README.md").write_text("# Test Repo\n\nA test repository.\n")
    (tmp_path / ".gitignore").write_text("node_modules/\n__pycache__/\n*.pyc\n")

    # Nested source file
    utils_dir = tmp_path / "utils"
    utils_dir.mkdir()
    (utils_dir / "helper.py").write_text("def add(a: int, b: int) -> int:\n    return a + b\n")
    (utils_dir / "__init__.py").write_text("")

    # node_modules (should be ignored)
    nm_dir = tmp_path / "node_modules" / "pkg"
    nm_dir.mkdir(parents=True)
    (nm_dir / "index.js").write_text("module.exports = {}\n")

    return tmp_path


@pytest.fixture
def tmp_repo_with_secrets(tmp_repo: Path) -> Path:
    """Extend tmp_repo with files containing fake secrets.

    Adds:
      - .env (contains API_KEY=sk-...)
      - config.py (contains hardcoded token)
    """
    (tmp_repo / ".env").write_text(
        "DATABASE_URL=postgres://user:pass@localhost/db\n"
        "API_KEY=sk-proj-abc123def456ghi789jkl012mno345pqr678stu901vwx234\n"
        "SECRET=mysupersecretvalue\n"
    )
    (tmp_repo / "config.py").write_text(
        'API_TOKEN = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef12"\nDB_HOST = "localhost"\n'
    )
    return tmp_repo
