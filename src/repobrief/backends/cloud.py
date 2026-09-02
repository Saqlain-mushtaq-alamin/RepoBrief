"""Cloud LLM backend -- supports Anthropic (Claude) and OpenAI (GPT) APIs.

Determines which provider to use based on the model name:
- Models starting with 'claude' -> Anthropic API
- Models starting with 'gpt' or 'o1' -> OpenAI API
- Explicit provider prefix: 'anthropic:model-name' or 'openai:model-name'
"""

from __future__ import annotations

import os
from collections.abc import Iterator

from repobrief.backends.base import ChatMessage, LLMBackend

# -- Provider Detection --------------------------------------------------------


def _detect_provider(model: str) -> str:
    """Detect the API provider from the model name.

    Args:
        model: Model name string.

    Returns:
        'anthropic' or 'openai'.

    Raises:
        ValueError: If the provider cannot be determined.
    """
    model_lower = model.lower()

    # Explicit prefix
    if model_lower.startswith("anthropic:"):
        return "anthropic"
    if model_lower.startswith("openai:"):
        return "openai"

    # Infer from model name
    if model_lower.startswith("claude"):
        return "anthropic"
    if model_lower.startswith(("gpt", "o1", "o3")):
        return "openai"

    raise ValueError(
        f"Cannot determine provider for model '{model}'. "
        f"Use a prefix: 'anthropic:{model}' or 'openai:{model}'"
    )


def _strip_provider_prefix(model: str) -> str:
    """Remove the provider prefix from a model name."""
    if ":" in model:
        return model.split(":", 1)[1]
    return model


class CloudBackend(LLMBackend):
    """Cloud LLM backend using Anthropic or OpenAI APIs.

    Usage:
        backend = CloudBackend(model="claude-sonnet-4-20250514", api_key="sk-...")
        for chunk in backend.generate(system_prompt, question):
            print(chunk, end="")
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: str | None = None,
        max_output_tokens: int = 4096,
    ):
        """Initialize the cloud backend.

        Args:
            model: Model identifier (e.g., 'claude-sonnet-4-20250514', 'gpt-4o').
            api_key: API key. If None, reads from environment variables.
            max_output_tokens: Maximum tokens in the response.
        """
        self._model = _strip_provider_prefix(model)
        self._provider = _detect_provider(model)
        self._max_output_tokens = max_output_tokens

        # Resolve API key
        if api_key:
            self._api_key = api_key
        elif self._provider == "anthropic":
            self._api_key = os.environ.get("ANTHROPIC_API_KEY")
        elif self._provider == "openai":
            self._api_key = os.environ.get("OPENAI_API_KEY")
        else:
            self._api_key = None

    @property
    def name(self) -> str:
        provider_name = "Anthropic Claude" if self._provider == "anthropic" else "OpenAI"
        return f"{provider_name} ({self._model})"

    def validate(self) -> tuple[bool, str]:
        """Check that the API key is set and the SDK is installed."""
        if not self._api_key:
            env_var = "ANTHROPIC_API_KEY" if self._provider == "anthropic" else "OPENAI_API_KEY"
            return (
                False,
                f"No API key found. Set the {env_var} environment variable, "
                f"or pass it in .repobrief.yml under 'api_key'.\n"
                f"Example: export {env_var}=sk-your-key-here",
            )

        # Check if the SDK is installed
        try:
            if self._provider == "anthropic":
                import anthropic  # noqa: F401
            else:
                import openai  # noqa: F401
        except ImportError:
            sdk = "anthropic" if self._provider == "anthropic" else "openai"
            return (
                False,
                f"The '{sdk}' package is not installed. "
                f"Install it with: pip install repobrief[cloud]",
            )

        return (True, f"Ready -- using {self.name}")

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        history: list[ChatMessage] | None = None,
    ) -> Iterator[str]:
        """Send a prompt to the cloud API and stream back response tokens.

        Args:
            system_prompt: System instructions (includes the repo digest).
            user_message: The user's question.
            history: Previous conversation messages.

        Yields:
            String chunks of the response.
        """
        if self._provider == "anthropic":
            yield from self._generate_anthropic(system_prompt, user_message, history)
        else:
            yield from self._generate_openai(system_prompt, user_message, history)

    def _generate_anthropic(
        self,
        system_prompt: str,
        user_message: str,
        history: list[ChatMessage] | None = None,
    ) -> Iterator[str]:
        """Generate using the Anthropic API."""
        import anthropic

        client = anthropic.Anthropic(api_key=self._api_key)

        # Build messages list
        messages = []
        if history:
            for msg in history:
                if msg.role in ("user", "assistant"):
                    messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": user_message})

        try:
            with client.messages.stream(
                model=self._model,
                max_tokens=self._max_output_tokens,
                system=system_prompt,
                messages=messages,
            ) as stream:
                yield from stream.text_stream
        except anthropic.AuthenticationError as err:
            raise PermissionError(
                "Invalid Anthropic API key. Check your ANTHROPIC_API_KEY."
            ) from err
        except anthropic.RateLimitError as err:
            raise RuntimeError(
                "Anthropic API rate limit exceeded. Wait a moment and try again."
            ) from err
        except anthropic.APIConnectionError as err:
            raise ConnectionError(
                "Could not connect to the Anthropic API. Check your internet connection."
            ) from err

    def _generate_openai(
        self,
        system_prompt: str,
        user_message: str,
        history: list[ChatMessage] | None = None,
    ) -> Iterator[str]:
        """Generate using the OpenAI API."""
        import openai

        client = openai.OpenAI(api_key=self._api_key)

        # Build messages list
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for msg in history:
                if msg.role in ("user", "assistant"):
                    messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": user_message})

        try:
            stream = client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=self._max_output_tokens,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except openai.AuthenticationError as err:
            raise PermissionError(
                "Invalid OpenAI API key. Check your OPENAI_API_KEY."
            ) from err
        except openai.RateLimitError as err:
            raise RuntimeError(
                "OpenAI API rate limit exceeded. Wait a moment and try again."
            ) from err
        except openai.APIConnectionError as err:
            raise ConnectionError(
                "Could not connect to the OpenAI API. Check your internet connection."
            ) from err
