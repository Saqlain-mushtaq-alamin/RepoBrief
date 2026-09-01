"""Tests for the packing and formatting module."""

from pathlib import Path

import pytest

from repobrief.packer.formatter import (
    OutputFormat,
    PackingMetadata,
    _detect_language,
    format_markdown,
    format_plain,
    format_xml,
    pack_digest,
)
from repobrief.packer.tree import render_directory_tree
from repobrief.scanner.models import ScannedFile


@pytest.fixture
def sample_files() -> list[ScannedFile]:
    """Create a list of sample ScannedFile objects for testing."""
    return [
        ScannedFile(
            path=Path("/repo/main.py"),
            relative_path=Path("main.py"),
            size_bytes=21,
            content="print('hello world')\n",
        ),
        ScannedFile(
            path=Path("/repo/utils/helper.py"),
            relative_path=Path("utils/helper.py"),
            size_bytes=48,
            content="def add(a: int, b: int) -> int:\n    return a + b\n",
        ),
        ScannedFile(
            path=Path("/repo/README.md"),
            relative_path=Path("README.md"),
            size_bytes=30,
            content="# My Project\n\nA cool project.\n",
        ),
    ]


@pytest.fixture
def sample_metadata() -> PackingMetadata:
    return PackingMetadata(
        repo_name="my-project",
        files_included=3,
        files_scanned=50,
        tokens_used=1500,
        token_budget=100000,
    )


class TestDirectoryTree:
    """Test the tree renderer."""

    def test_renders_flat_files(self):
        paths = [Path("a.py"), Path("b.py")]
        tree = render_directory_tree(paths, root_name="repo")
        assert "repo/" in tree
        assert "a.py" in tree
        assert "b.py" in tree

    def test_renders_nested_directories(self):
        paths = [Path("src/main.py"), Path("src/utils/helper.py")]
        tree = render_directory_tree(paths, root_name="repo")
        assert "src/" in tree
        assert "utils/" in tree
        assert "main.py" in tree
        assert "helper.py" in tree

    def test_uses_box_drawing_characters(self):
        paths = [Path("a.py"), Path("b.py")]
        tree = render_directory_tree(paths, root_name="repo")
        assert "\u251c\u2500\u2500" in tree or "\u2514\u2500\u2500" in tree

    def test_empty_list(self):
        tree = render_directory_tree([], root_name="repo")
        assert "empty" in tree.lower()


class TestMarkdownFormat:
    """Test Markdown output generation."""

    def test_contains_header(self, sample_files, sample_metadata):
        output = format_markdown(sample_files, sample_metadata)
        assert "# Repository: my-project" in output

    def test_contains_summary(self, sample_files, sample_metadata):
        output = format_markdown(sample_files, sample_metadata)
        assert "Files included" in output
        assert "3" in output

    def test_contains_file_content(self, sample_files, sample_metadata):
        output = format_markdown(sample_files, sample_metadata)
        assert "hello world" in output
        assert "def add" in output

    def test_has_syntax_highlighting_hints(self, sample_files, sample_metadata):
        output = format_markdown(sample_files, sample_metadata)
        assert "```python" in output


class TestXMLFormat:
    """Test XML output generation."""

    def test_valid_xml_structure(self, sample_files, sample_metadata):
        output = format_xml(sample_files, sample_metadata)
        assert output.startswith("<?xml")
        assert "<repository" in output
        assert "</repository>" in output

    def test_contains_file_content(self, sample_files, sample_metadata):
        output = format_xml(sample_files, sample_metadata)
        assert "hello world" in output


class TestPlainFormat:
    """Test plain text output generation."""

    def test_contains_separators(self, sample_files, sample_metadata):
        output = format_plain(sample_files, sample_metadata)
        assert "=" * 80 in output

    def test_contains_file_labels(self, sample_files, sample_metadata):
        output = format_plain(sample_files, sample_metadata)
        assert "FILE: main.py" in output


class TestPackDigest:
    """Test the main pack_digest entry point."""

    def test_markdown_format(self, sample_files, sample_metadata):
        output = pack_digest(sample_files, sample_metadata, OutputFormat.MARKDOWN)
        assert "# Repository" in output

    def test_xml_format(self, sample_files, sample_metadata):
        output = pack_digest(sample_files, sample_metadata, OutputFormat.XML)
        assert "<?xml" in output

    def test_plain_format(self, sample_files, sample_metadata):
        output = pack_digest(sample_files, sample_metadata, OutputFormat.PLAIN)
        assert "====" in output

    def test_invalid_format_raises(self, sample_files, sample_metadata):
        with pytest.raises(ValueError):
            pack_digest(sample_files, sample_metadata, "invalid")


class TestLanguageDetection:
    """Test file extension to language mapping."""

    def test_python(self):
        assert _detect_language(Path("main.py")) == "python"

    def test_javascript(self):
        assert _detect_language(Path("app.js")) == "javascript"

    def test_unknown_extension(self):
        assert _detect_language(Path("file.xyz")) == ""

    def test_dockerfile(self):
        assert _detect_language(Path("Dockerfile")) == "dockerfile"
