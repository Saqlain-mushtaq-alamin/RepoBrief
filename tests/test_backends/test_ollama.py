"""Tests for the Ollama local backend.

These tests mock HTTP calls -- they don't require a running Ollama server.
For actual Ollama testing, see the manual test section.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from repobrief.backends.ollama import OllamaBackend


class TestOllamaServerDetection:
    """Test server status detection."""

    @patch("repobrief.backends.ollama.requests.get")
    def test_detects_running_server(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)
        backend = OllamaBackend()
        assert backend._is_server_running()

    @patch("repobrief.backends.ollama.requests.get")
    def test_detects_stopped_server(self, mock_get):
        mock_get.side_effect = requests.ConnectionError()
        backend = OllamaBackend()
        assert not backend._is_server_running()


class TestOllamaModelListing:
    """Test model availability checking."""

    @patch("repobrief.backends.ollama.requests.get")
    def test_lists_available_models(self, mock_get):
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3.1:8b"},
                {"name": "phi3:mini"},
            ]
        }
        mock_get.return_value = mock_response

        backend = OllamaBackend(model="llama3.1:8b")
        models = backend._list_models()
        assert "llama3.1:8b" in models
        assert "phi3:mini" in models

    @patch("repobrief.backends.ollama.requests.get")
    def test_model_available(self, mock_get):
        tags_resp = MagicMock(status_code=200)
        tags_resp.json.return_value = {"models": [{"name": "llama3.1:8b"}]}
        mock_get.return_value = tags_resp

        backend = OllamaBackend(model="llama3.1:8b")
        assert backend._is_model_available()


class TestOllamaValidation:
    """Test the validate() method."""

    @patch("repobrief.backends.ollama.requests.get")
    def test_server_not_running(self, mock_get):
        mock_get.side_effect = requests.ConnectionError()
        backend = OllamaBackend()
        is_valid, msg = backend.validate()
        assert not is_valid
        assert "not running" in msg.lower()
        assert "ollama.com" in msg.lower()  # Installation link

    @patch("repobrief.backends.ollama.requests.get")
    def test_model_not_available(self, mock_get):
        health_resp = MagicMock(status_code=200)
        tags_resp = MagicMock(status_code=200)
        tags_resp.json.return_value = {"models": [{"name": "phi3:mini"}]}
        # validate() calls: _is_server_running (GET /), _is_model_available (GET /api/tags),
        # then _list_models again for the error message (GET /api/tags)
        mock_get.side_effect = [health_resp, tags_resp, tags_resp]

        backend = OllamaBackend(model="llama3.1:8b")
        is_valid, msg = backend.validate()
        assert not is_valid
        assert "not available" in msg.lower()
        assert "ollama pull" in msg.lower()

    @patch("repobrief.backends.ollama.requests.get")
    def test_all_good(self, mock_get):
        health_resp = MagicMock(status_code=200)
        tags_resp = MagicMock(status_code=200)
        tags_resp.json.return_value = {"models": [{"name": "llama3.2:3b"}]}
        mock_get.side_effect = [health_resp, tags_resp]

        backend = OllamaBackend(model="llama3.2:3b")
        is_valid, msg = backend.validate()
        assert is_valid
        assert "ready" in msg.lower()


class TestOllamaGeneration:
    """Test the generate() method with mocked HTTP responses."""

    @patch("repobrief.backends.ollama.requests.post")
    def test_streams_response(self, mock_post):
        chunks = [
            json.dumps({"message": {"role": "assistant", "content": "Hello"}, "done": False}),
            json.dumps({"message": {"role": "assistant", "content": " world"}, "done": False}),
            json.dumps({"message": {"role": "assistant", "content": ""}, "done": True}),
        ]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = iter(chunks)
        mock_post.return_value = mock_response

        backend = OllamaBackend(model="llama3.2:3b")
        result = list(backend.generate("system", "user question"))
        assert result == ["Hello", " world"]

    @patch("repobrief.backends.ollama.requests.post")
    def test_connection_error(self, mock_post):
        mock_post.side_effect = requests.ConnectionError()
        backend = OllamaBackend()
        with pytest.raises(ConnectionError):
            list(backend.generate("system", "question"))

    def test_name_property(self):
        backend = OllamaBackend(model="llama3.1:8b")
        assert "Ollama" in backend.name
        assert "llama3.1:8b" in backend.name
