"""Abstract base class for LLM backends.

All backends (cloud, Ollama, future local runtimes) must implement this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass


@dataclass
class ChatMessage:
    """A single message in a conversation.

    Attributes:
        role: 'user', 'assistant', or 'system'.
        content: The message text.
    """

    role: str  # "user" | "assistant" | "system"
    content: str


class LLMBackend(ABC):
    """Abstract interface for LLM backends.

    Implementing classes must provide:
    - generate(): Send a prompt and stream back response tokens
    - validate(): Check that the backend is properly configured and reachable
    """

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_message: str,
        history: list[ChatMessage] | None = None,
    ) -> Iterator[str]:
        """Send a prompt and yield response tokens as they stream in.

        Args:
            system_prompt: System-level instructions (includes the repo digest).
            user_message: The user's question.
            history: Previous conversation messages (for REPL mode).

        Yields:
            String chunks of the response as they arrive.

        Raises:
            ConnectionError: If the backend is unreachable.
            PermissionError: If authentication fails (bad API key).
            RuntimeError: For other backend errors.
        """

    @abstractmethod
    def validate(self) -> tuple[bool, str]:
        """Check if the backend is properly configured and reachable.

        Returns:
            Tuple of (is_valid, message).
            - (True, "Ready") if everything is configured.
            - (False, "Missing API key...") if there's a problem.
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this backend (e.g., 'Anthropic Claude')."""
