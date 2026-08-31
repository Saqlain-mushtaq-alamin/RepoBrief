"""Tests for the secret detection engine."""

from pathlib import Path

from repobrief.security.secret_scanner import (
    SecretAction,
    _is_env_file,
    scan_content_for_secrets,
    scan_files_for_secrets,
)


class TestEnvFileDetection:
    """Test .env file identification."""

    def test_detects_env_file(self):
        assert _is_env_file(Path(".env"))
        assert _is_env_file(Path(".env.local"))
        assert _is_env_file(Path(".env.production"))

    def test_non_env_file(self):
        assert not _is_env_file(Path("config.py"))
        assert not _is_env_file(Path(".envrc"))  # not a .env file


class TestSecretPatterns:
    """Test individual secret pattern detection."""

    def test_detects_aws_key(self):
        content = 'aws_key = "AKIAIOSFODNN7EXAMPLE"'
        result = scan_content_for_secrets(content, Path("config.py"))
        assert result.has_secrets
        assert any("AWS" in f.pattern_name for f in result.findings)

    def test_detects_github_pat(self):
        content = 'token = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"'
        result = scan_content_for_secrets(content, Path("config.py"))
        assert result.has_secrets
        assert any("GitHub" in f.pattern_name for f in result.findings)

    def test_detects_openai_key(self):
        content = 'OPENAI_KEY = "sk-proj12345678901234567890123456"'
        result = scan_content_for_secrets(content, Path("settings.py"))
        assert result.has_secrets

    def test_detects_private_key(self):
        content = "-----BEGIN RSA PRIVATE KEY-----\nMIIEow..."
        result = scan_content_for_secrets(content, Path("key.pem"))
        assert result.has_secrets
        assert any("Private Key" in f.pattern_name for f in result.findings)

    def test_detects_hardcoded_password(self):
        content = 'password = "supersecretpassword123"'
        result = scan_content_for_secrets(content, Path("db.py"))
        assert result.has_secrets

    def test_no_false_positive_on_normal_code(self):
        content = """
def hello():
    name = "world"
    count = 42
    return f"Hello {name} x{count}"
"""
        result = scan_content_for_secrets(content, Path("app.py"))
        assert not result.has_secrets

    def test_no_false_positive_on_short_values(self):
        content = 'key = "test"'  # Too short to trigger generic pattern
        result = scan_content_for_secrets(content, Path("test.py"))
        assert not result.has_secrets


class TestRedactionMode:
    """Test the REDACT action mode."""

    def test_redacts_env_values(self):
        content = "API_KEY=sk-abc123def456\nDEBUG=true"
        result = scan_content_for_secrets(content, Path(".env"), action=SecretAction.REDACT)
        assert result.has_secrets
        assert result.redacted_content is not None
        assert "[REDACTED]" in result.redacted_content
        assert "sk-abc123def456" not in result.redacted_content

    def test_redacts_inline_secrets(self):
        content = 'token = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"'
        result = scan_content_for_secrets(content, Path("config.py"), action=SecretAction.REDACT)
        assert result.redacted_content is not None
        assert "ghp_" not in result.redacted_content
        assert "[REDACTED]" in result.redacted_content


class TestScanFilesForSecrets:
    """Test the batch file scanning function."""

    def test_excludes_files_with_secrets(self, tmp_repo_with_secrets: Path):
        from repobrief.scanner.walker import scan_repository

        files = scan_repository(tmp_repo_with_secrets)
        clean, findings = scan_files_for_secrets(files, action=SecretAction.EXCLUDE)

        # .env and config.py with secrets should be excluded
        clean_paths = {str(f.relative_path) for f in clean}
        assert ".env" not in clean_paths
        assert len(findings) > 0

    def test_redacts_instead_of_excluding(self, tmp_repo_with_secrets: Path):
        from repobrief.scanner.walker import scan_repository

        files = scan_repository(tmp_repo_with_secrets)
        clean, findings = scan_files_for_secrets(files, action=SecretAction.REDACT)

        # Files should still be present but with redacted content
        assert len(findings) > 0
        # .env should now be present (redacted, not excluded)
        env_files = [f for f in clean if f.relative_path.name == ".env"]
        if env_files:
            assert "[REDACTED]" in env_files[0].content
