"""Tests for the cloud backend.

Note: These tests mock the API calls -- they don't make real HTTP requests.
For actual API testing, see the manual test section in the acceptance criteria.
"""

from unittest.mock import MagicMock, patch

import pytest

from repobrief.backends.cloud import CloudBackend, _detect_provider, _strip_provider_prefix
from repobrief.backends.prompts import build_system_prompt


class TestProviderDetection:
    """Test automatic provider detection from model names."""

    def test_claude_is_anthropic(self):
        assert _detect_provider("claude-sonnet-4-20250514") == "anthropic"

    def test_gpt_is_openai(self):
        assert _detect_provider("gpt-4o") == "openai"

    def test_explicit_prefix_anthropic(self):
        assert _detect_provider("anthropic:my-model") == "anthropic"

    def test_explicit_prefix_openai(self):
        assert _detect_provider("openai:my-model") == "openai"

    def test_unknown_raises(self):
        with pytest.raises(ValueError):
            _detect_provider("unknown-model-xyz")


class TestStripPrefix:
    def test_strips_anthropic(self):
        assert _strip_provider_prefix("anthropic:claude-3") == "claude-3"

    def test_no_prefix_unchanged(self):
        assert _strip_provider_prefix("gpt-4o") == "gpt-4o"


class TestCloudBackendValidation:
    """Test the validate() method."""

    def test_no_api_key_fails(self):
        backend = CloudBackend(model="claude-sonnet-4-20250514", api_key=None)
        # Clear env var too
        with patch.dict("os.environ", {}, clear=True):
            backend._api_key = None
            is_valid, msg = backend.validate()
            assert not is_valid
            assert "API key" in msg

    def test_with_api_key_and_sdk(self):
        backend = CloudBackend(model="claude-sonnet-4-20250514", api_key="sk-test-key")
        # Mock the anthropic import
        with patch.dict("sys.modules", {"anthropic": MagicMock()}):
            is_valid, msg = backend.validate()
            assert is_valid

    def test_name_property(self):
        backend = CloudBackend(model="claude-sonnet-4-20250514", api_key="test")
        assert "Anthropic" in backend.name
        assert "claude" in backend.name.lower()


class TestSystemPrompt:
    """Test system prompt construction."""

    def test_contains_digest(self):
        digest = "# Repository: test\n## Files\n..."
        prompt = build_system_prompt(digest)
        assert digest in prompt

    def test_contains_instructions(self):
        prompt = build_system_prompt("test digest")
        assert "RepoBrief" in prompt
        assert "answer" in prompt.lower()
