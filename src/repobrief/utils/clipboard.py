"""Cross-platform clipboard utility."""

from __future__ import annotations


def copy_to_clipboard(text: str) -> bool:
    """Copy text to the system clipboard.

    Uses pyperclip for cross-platform support. Falls back gracefully
    if clipboard access is unavailable (e.g., headless server).

    Args:
        text: The text to copy.

    Returns:
        True if copy succeeded, False if clipboard is unavailable.
    """
    try:
        import pyperclip

        pyperclip.copy(text)
        return True
    except Exception:
        # pyperclip raises various exceptions if no clipboard mechanism
        # is available (no xclip, xsel, pbcopy, etc.)
        return False
