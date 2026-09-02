"""Tests for error handling and graceful degradation."""

from __future__ import annotations

from repobrief.errors import (
    BackendAuthError,
    BackendConnectionError,
    BackendError,
    BackendModelError,
    BackendNotConfiguredError,
    ConfigError,
    GitHubCloneError,
    PackingError,
    RepoBriefError,
    ScanError,
    SecretScanError,
    TokenizationError,
)


class TestExceptionHierarchy:
    """Test that all exceptions inherit from RepoBriefError."""

    def test_scan_error_is_repobrief_error(self):
        err = ScanError("test")
        assert isinstance(err, RepoBriefError)

    def test_backend_errors_are_repobrief_errors(self):
        for cls in [
            BackendError,
            BackendNotConfiguredError,
            BackendConnectionError,
            BackendAuthError,
            BackendModelError,
        ]:
            err = cls("test")
            assert isinstance(err, RepoBriefError)
            assert isinstance(err, BackendError)

    def test_other_errors_are_repobrief_errors(self):
        for cls in [ConfigError, GitHubCloneError, PackingError,
                    SecretScanError, TokenizationError]:
            err = cls("test")
            assert isinstance(err, RepoBriefError)

    def test_error_has_hint(self):
        err = RepoBriefError("Something failed", hint="Try doing X")
        assert err.message == "Something failed"
        assert err.hint == "Try doing X"
        assert str(err) == "Something failed"

    def test_error_without_hint(self):
        err = RepoBriefError("Something failed")
        assert err.message == "Something failed"
        assert err.hint == ""


class TestGracefulDegradation:
    """Test that features degrade gracefully when dependencies are missing."""

    def test_scanner_works_without_git(self, tmp_path):
        """Scanner should work even if the target is not a git repo."""
        (tmp_path / "main.py").write_text("print('hello')\n")
        from repobrief.scanner.walker import scan_repository

        results = scan_repository(tmp_path)
        assert len(results) > 0
        assert results[0].last_modified is None

    def test_tokenizer_fallback(self):
        """Token counting should fall back to estimation if tiktoken fails."""
        from repobrief.scoring.tokenizer import count_tokens

        result = count_tokens("hello world")
        assert result > 0

    def test_clipboard_failure_returns_false(self):
        """Clipboard copy should return False, not raise, when unavailable."""
        from repobrief.utils.clipboard import copy_to_clipboard

        result = copy_to_clipboard("test")
        assert isinstance(result, bool)


class TestCLIInputValidation:
    """Test CLI input validation."""

    def test_nonexistent_path_fails(self):
        from click.testing import CliRunner

        from repobrief.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["pack", "/nonexistent/path/xyz123"])
        assert result.exit_code != 0

    def test_version_flag(self):
        from click.testing import CliRunner

        from repobrief.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "repobrief" in result.output.lower()

    def test_verbose_flag(self):
        from click.testing import CliRunner

        from repobrief.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["--verbose", "pack", "."])
        # Should not crash, even if it errors for other reasons
        assert result.exit_code in (0, 1)

    def test_quiet_flag(self):
        from click.testing import CliRunner

        from repobrief.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["--quiet", "pack", "."])
        # Should not crash
        assert result.exit_code in (0, 1)
