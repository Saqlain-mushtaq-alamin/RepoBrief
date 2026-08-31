"""Tests for the repository scanner."""

from pathlib import Path

import pytest

from repobrief.scanner.ignore import IgnoreRules
from repobrief.scanner.walker import is_binary_file, scan_repository


class TestIgnoreRules:
    """Test the ignore rule engine."""

    def test_default_ignores_node_modules(self, tmp_repo: Path):
        rules = IgnoreRules(tmp_repo)
        assert rules.should_ignore(Path("node_modules/pkg/index.js"))

    def test_default_ignores_pycache(self, tmp_repo: Path):
        rules = IgnoreRules(tmp_repo)
        assert rules.should_ignore(Path("__pycache__/module.pyc"))

    def test_does_not_ignore_source_files(self, tmp_repo: Path):
        rules = IgnoreRules(tmp_repo)
        assert not rules.should_ignore(Path("main.py"))
        assert not rules.should_ignore(Path("utils/helper.py"))

    def test_respects_gitignore(self, tmp_path: Path):
        (tmp_path / ".gitignore").write_text("secret_stuff/\n")
        rules = IgnoreRules(tmp_path)
        assert rules.should_ignore(Path("secret_stuff/file.txt"))

    def test_extra_exclude_patterns(self, tmp_repo: Path):
        rules = IgnoreRules(tmp_repo, extra_exclude=["*.test.js"])
        assert rules.should_ignore(Path("src/app.test.js"))


class TestBinaryDetection:
    """Test binary file detection."""

    def test_text_file_is_not_binary(self, tmp_path: Path):
        f = tmp_path / "code.py"
        f.write_text("print('hello world')\n")
        assert not is_binary_file(f)

    def test_binary_file_is_detected(self, tmp_path: Path):
        f = tmp_path / "image.dat"
        f.write_bytes(bytes(range(256)) * 100)
        assert is_binary_file(f)

    def test_empty_file_is_not_binary(self, tmp_path: Path):
        f = tmp_path / "empty.txt"
        f.write_text("")
        assert not is_binary_file(f)


class TestScanRepository:
    """Test the main scan_repository function."""

    def test_finds_source_files(self, tmp_repo: Path):
        results = scan_repository(tmp_repo)
        rel_paths = {str(f.relative_path) for f in results}
        assert "main.py" in rel_paths
        assert any("helper.py" in str(p) for p in rel_paths)

    def test_excludes_node_modules(self, tmp_repo: Path):
        results = scan_repository(tmp_repo)
        rel_paths = {str(f.relative_path) for f in results}
        assert not any("node_modules" in p for p in rel_paths)

    def test_loads_file_content(self, tmp_repo: Path):
        results = scan_repository(tmp_repo, load_content=True)
        main_file = next(f for f in results if f.relative_path.name == "main.py")
        assert "hello world" in main_file.content

    def test_no_content_when_disabled(self, tmp_repo: Path):
        results = scan_repository(tmp_repo, load_content=False)
        for f in results:
            assert f.content == ""

    def test_raises_on_nonexistent_path(self):
        with pytest.raises(FileNotFoundError):
            scan_repository(Path("/nonexistent/path"))

    def test_results_sorted_by_path(self, tmp_repo: Path):
        results = scan_repository(tmp_repo)
        paths = [str(f.relative_path) for f in results]
        assert paths == sorted(paths)

    def test_extra_exclude_respected(self, tmp_repo: Path):
        results = scan_repository(tmp_repo, extra_exclude=["*.md"])
        rel_paths = {str(f.relative_path) for f in results}
        assert not any(p.endswith(".md") for p in rel_paths)
