"""Data models for the scanner module."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class ScannedFile:
    """Represents a single file discovered during repository scanning.

    Attributes:
        path: Absolute path to the file on disk.
        relative_path: Path relative to the repository root (used for display).
        size_bytes: File size in bytes.
        content: The text content of the file (loaded lazily or eagerly).
        last_modified: Last git commit date touching this file (None if not a git repo).
        extension: File extension including the dot (e.g., ".py"), empty string if none.
    """

    path: Path
    relative_path: Path
    size_bytes: int
    content: str = ""
    last_modified: Optional[datetime] = None
    extension: str = ""

    def __post_init__(self):
        if not self.extension:
            self.extension = self.path.suffix.lower()
