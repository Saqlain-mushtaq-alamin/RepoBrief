"""Configuration loading -- CLI flags, config file, and environment variables.

Priority order (highest wins):
1. CLI flags (--max-tokens, --format, etc.)
2. Environment variables (REPOBRIEF_API_KEY, etc.)
3. Config file (.repobrief.yml in the repo root)
4. Built-in defaults
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class RepoBriefConfig:
    """Merged configuration from all sources.

    Attributes:
        backend: LLM backend to use ('cloud' or 'ollama').
        model: Model name/identifier.
        max_tokens: Token budget for file selection.
        output_format: Output format ('markdown', 'xml', 'plain').
        exclude: Extra glob patterns to exclude.
        secret_action: What to do with secrets ('exclude' or 'redact').
        api_key: API key for cloud backend (from env or config).
        ollama_host: Ollama server URL.
    """

    backend: str = "cloud"
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 100_000
    output_format: str = "markdown"
    exclude: list[str] = field(default_factory=list)
    secret_action: str = "exclude"
    api_key: str | None = None
    ollama_host: str = "http://localhost:11434"


def load_config_file(repo_root: Path) -> dict:
    """Load .repobrief.yml from the repository root.

    Args:
        repo_root: Path to the repository root.

    Returns:
        Dict of config values, or empty dict if no config file.
    """
    config_path = repo_root / ".repobrief.yml"
    if not config_path.is_file():
        # Also check .repobrief.yaml
        config_path = repo_root / ".repobrief.yaml"

    if not config_path.is_file():
        return {}

    try:
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
            return config if isinstance(config, dict) else {}
    except (yaml.YAMLError, OSError):
        return {}


def build_config(
    repo_root: Path,
    cli_overrides: dict | None = None,
) -> RepoBriefConfig:
    """Build a merged config from file + env vars + CLI flags.

    Args:
        repo_root: Path to the repository root (to find .repobrief.yml).
        cli_overrides: Dict of CLI flag values (None values are ignored).

    Returns:
        Merged RepoBriefConfig.
    """
    # Start with defaults
    config = RepoBriefConfig()

    # Layer 1: Config file
    file_config = load_config_file(repo_root)
    if "backend" in file_config:
        config.backend = file_config["backend"]
    if "model" in file_config:
        config.model = file_config["model"]
    if "max_tokens" in file_config:
        config.max_tokens = int(file_config["max_tokens"])
    if "format" in file_config:
        config.output_format = file_config["format"]
    if "exclude" in file_config:
        config.exclude = list(file_config["exclude"])
    if "secret_action" in file_config:
        config.secret_action = file_config["secret_action"]
    if "ollama_host" in file_config:
        config.ollama_host = file_config["ollama_host"]

    # Layer 2: Environment variables
    env_key = (
        os.environ.get("REPOBRIEF_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
    )
    if env_key:
        config.api_key = env_key

    env_host = os.environ.get("OLLAMA_HOST")
    if env_host:
        config.ollama_host = env_host

    # Layer 3: CLI overrides (highest priority)
    if cli_overrides:
        for key, value in cli_overrides.items():
            if value is not None and hasattr(config, key):
                setattr(config, key, value)

    return config
