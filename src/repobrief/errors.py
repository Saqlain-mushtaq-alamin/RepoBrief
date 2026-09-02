"""Centralized exception hierarchy for RepoBrief.

All RepoBrief-specific exceptions inherit from RepoBriefError.
This makes it easy for callers to catch "any RepoBrief error" while
still distinguishing specific error types.
"""

from __future__ import annotations


class RepoBriefError(Exception):
    """Base exception for all RepoBrief errors.

    Attributes:
        message: Human-readable error description.
        hint: Actionable suggestion for the user (displayed after the error).
    """

    def __init__(self, message: str, hint: str = "") -> None:
        self.message = message
        self.hint = hint
        super().__init__(message)


class ScanError(RepoBriefError):
    """Error during repository scanning (path not found, permission denied, etc.)."""


class SecretScanError(RepoBriefError):
    """Error during secret detection (regex compilation failure, etc.)."""


class TokenizationError(RepoBriefError):
    """Error during token counting (tiktoken encoding not found, etc.)."""


class PackingError(RepoBriefError):
    """Error during digest packing (output format error, etc.)."""


class BackendError(RepoBriefError):
    """Base error for all LLM backend issues."""


class BackendNotConfiguredError(BackendError):
    """No backend has been configured (first-run scenario)."""


class BackendConnectionError(BackendError):
    """Cannot connect to the backend (Ollama not running, API unreachable)."""


class BackendAuthError(BackendError):
    """Authentication failed (bad API key)."""


class BackendModelError(BackendError):
    """Model not found or not available."""


class ConfigError(RepoBriefError):
    """Error in configuration file or environment variables."""


class GitHubCloneError(RepoBriefError):
    """Error cloning a GitHub repository."""
