"""Tests for the CLI interface."""

from click.testing import CliRunner

from repobrief.cli import main


class TestPackCommand:
    """Test the 'pack' subcommand."""

    def test_pack_basic(self, tmp_repo):
        runner = CliRunner()
        result = runner.invoke(main, ["pack", str(tmp_repo)])
        assert result.exit_code == 0
        assert "Repository" in result.output

    def test_pack_to_file(self, tmp_repo, tmp_path):
        runner = CliRunner()
        output_file = tmp_path / "digest.md"
        result = runner.invoke(main, ["pack", str(tmp_repo), "-o", str(output_file)])
        assert result.exit_code == 0
        assert output_file.exists()
        content = output_file.read_text()
        assert "Repository" in content

    def test_pack_xml_format(self, tmp_repo):
        runner = CliRunner()
        result = runner.invoke(main, ["pack", str(tmp_repo), "--format", "xml"])
        assert result.exit_code == 0
        assert "<?xml" in result.output

    def test_pack_plain_format(self, tmp_repo):
        runner = CliRunner()
        result = runner.invoke(main, ["pack", str(tmp_repo), "--format", "plain"])
        assert result.exit_code == 0
        assert "====" in result.output

    def test_pack_with_max_tokens(self, tmp_repo):
        runner = CliRunner()
        result = runner.invoke(main, ["pack", str(tmp_repo), "--max-tokens", "500"])
        assert result.exit_code == 0

    def test_pack_with_exclude(self, tmp_repo):
        runner = CliRunner()
        result = runner.invoke(main, ["pack", str(tmp_repo), "--exclude", "*.md"])
        assert result.exit_code == 0
        assert "README.md" not in result.output  # Excluded

    def test_pack_nonexistent_path(self):
        runner = CliRunner()
        result = runner.invoke(main, ["pack", "/nonexistent/path"])
        assert result.exit_code != 0

    def test_version_flag(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.1" in result.output

    def test_help_flag(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "pack" in result.output.lower()


class TestChatCommand:
    """Test that the chat command exists and validates backend config."""

    def test_chat_requires_backend(self, tmp_repo):
        """Chat without backend configured should show a config error."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["chat", str(tmp_repo), "--backend", "cloud"],
            env={"ANTHROPIC_API_KEY": None, "OPENAI_API_KEY": None, "REPOBRIEF_API_KEY": None}
        )
        # Exit code 1 because no API key is set
        assert result.exit_code == 1

    def test_chat_ollama_not_yet(self, tmp_repo):
        """Ollama backend should show a not-yet message."""
        runner = CliRunner()
        result = runner.invoke(
            main, ["chat", str(tmp_repo), "--backend", "ollama"]
        )
        assert result.exit_code == 1
        assert "ollama" in result.output.lower()
