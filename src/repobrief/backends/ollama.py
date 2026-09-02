"""Ollama local backend -- fully offline LLM chat via Ollama's REST API.

Communicates with a locally running Ollama server (default: http://localhost:11434).
No data leaves the user's machine. Requires Ollama to be installed and running
with at least one model pulled.
"""

from __future__ import annotations

import json
from collections.abc import Iterator

import requests

from repobrief.backends.base import ChatMessage, LLMBackend

# Default Ollama server URL
DEFAULT_OLLAMA_HOST = "http://localhost:11434"

# Timeout for health checks and model listing (seconds)
CHECK_TIMEOUT = 5

# Timeout for generation requests -- set high because local models can be slow
GENERATE_TIMEOUT = 300  # 5 minutes


class OllamaBackend(LLMBackend):
    """Ollama local backend.

    Connects to a locally running Ollama server and sends chat requests.
    All processing happens on the user's machine -- no data is sent externally.

    Usage:
        backend = OllamaBackend(model="llama3.1:8b")
        is_valid, msg = backend.validate()
        if is_valid:
            for chunk in backend.generate(system_prompt, question):
                print(chunk, end="")
    """

    def __init__(
        self,
        model: str = "llama3.2:3b",
        host: str = DEFAULT_OLLAMA_HOST,
    ):
        """Initialize the Ollama backend.

        Args:
            model: Name of the Ollama model to use (e.g., 'llama3.1:8b').
            host: Ollama server URL (default: http://localhost:11434).
        """
        self._model = model
        self._host = host.rstrip("/")

    @property
    def name(self) -> str:
        return f"Ollama ({self._model})"

    # -- Server Communication --------------------------------------------------

    def _is_server_running(self) -> bool:
        """Check if the Ollama server is responding."""
        try:
            resp = requests.get(f"{self._host}/", timeout=CHECK_TIMEOUT)
            return resp.status_code == 200
        except (requests.ConnectionError, requests.Timeout):
            return False

    def _list_models(self) -> list[str]:
        """Get list of locally available models.

        Returns:
            List of model name strings (e.g., ['llama3.1:8b', 'phi3:mini']).
        """
        try:
            resp = requests.get(f"{self._host}/api/tags", timeout=CHECK_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("models", [])
                return [m["name"] for m in models]
        except (requests.ConnectionError, requests.Timeout, ValueError, KeyError):
            pass
        return []

    def _is_model_available(self) -> bool:
        """Check if the configured model is available locally."""
        available = self._list_models()
        # Check exact match and partial match (with/without tag)
        model_base = self._model.split(":")[0]
        return (
            self._model in available
            or any(m.startswith(model_base) for m in available)
        )

    # -- LLMBackend Interface --------------------------------------------------

    def validate(self) -> tuple[bool, str]:
        """Check if Ollama is running and the model is available.

        Returns:
            (True, "Ready") if everything is configured.
            (False, "detailed error message") if there's a problem.
        """
        # Check 1: Is Ollama running?
        if not self._is_server_running():
            return (
                False,
                f"Ollama server is not running at {self._host}.\n"
                f"\n"
                f"To fix this:\n"
                f"  1. Install Ollama: https://ollama.com/download\n"
                f"  2. Start the server: ollama serve\n"
                f"  3. Pull a model: ollama pull {self._model}\n"
                f"  4. Try again",
            )

        # Check 2: Is the model available?
        if not self._is_model_available():
            available = self._list_models()
            available_str = ", ".join(available[:5]) if available else "(none)"
            return (
                False,
                f"Model '{self._model}' is not available locally.\n"
                f"\n"
                f"Available models: {available_str}\n"
                f"\n"
                f"To fix this:\n"
                f"  Pull the model: ollama pull {self._model}\n"
                f"\n"
                f"Recommended models for limited RAM:\n"
                f"  - llama3.2:3b  (~2GB RAM) -- fast, good quality\n"
                f"  - phi3:mini    (~2.3GB RAM) -- fast, good for code\n"
                f"  - llama3.1:8b  (~4.5GB RAM) -- better quality, needs more RAM",
            )

        return (True, f"Ready -- using {self.name} (local, fully offline)")

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        history: list[ChatMessage] | None = None,
    ) -> Iterator[str]:
        """Send a prompt to the local Ollama server and stream back response tokens.

        Args:
            system_prompt: System instructions (includes the repo digest).
            user_message: The user's question.
            history: Previous conversation messages.

        Yields:
            String chunks of the response as they arrive.
        """
        # Build messages array
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
        ]
        if history:
            for msg in history:
                if msg.role in ("user", "assistant"):
                    messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": user_message})

        # Send request with streaming
        payload = {
            "model": self._model,
            "messages": messages,
            "stream": True,
        }

        try:
            resp = requests.post(
                f"{self._host}/api/chat",
                json=payload,
                stream=True,
                timeout=GENERATE_TIMEOUT,
            )

            if resp.status_code != 200:
                error_text = resp.text[:500]
                raise RuntimeError(
                    f"Ollama returned HTTP {resp.status_code}: {error_text}"
                )

            # Parse streaming response (newline-delimited JSON)
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if data.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue  # Skip malformed lines

        except requests.ConnectionError as err:
            raise ConnectionError(
                f"Lost connection to Ollama server at {self._host}. "
                f"Make sure Ollama is still running."
            ) from err
        except requests.Timeout as err:
            raise RuntimeError(
                f"Ollama request timed out after {GENERATE_TIMEOUT} seconds. "
                f"The model may be too large for your system, or the server "
                f"is overloaded."
            ) from err
