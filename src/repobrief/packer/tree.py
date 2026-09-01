"""Directory tree renderer.

Generates a visual tree representation of the repository structure,
similar to the Unix `tree` command output.
"""

from __future__ import annotations

from pathlib import Path


def render_directory_tree(
    file_paths: list[Path],
    root_name: str = ".",
) -> str:
    """Render a visual directory tree from a list of file paths.

    Args:
        file_paths: List of relative file paths to include in the tree.
        root_name: Name to show as the root directory.

    Returns:
        String containing the rendered tree with box-drawing characters.

    Example output:
        my-project/
        +-- main.py
        +-- utils/
        |   +-- __init__.py
        |   +-- helper.py
        +-- README.md
    """
    if not file_paths:
        return f"{root_name}/\n  (empty)\n"

    # Build a nested dict representing the directory structure
    # Each key is a directory or file name, values are sub-dicts (dirs) or None (files)
    tree: dict = {}
    for path in sorted(file_paths):
        parts = path.parts
        current = tree
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                # Leaf (file)
                current[part] = None
            else:
                # Directory
                if part not in current:
                    current[part] = {}
                current = current[part]

    # Render the tree
    lines: list[str] = [f"{root_name}/"]
    _render_subtree(tree, lines, prefix="")

    return "\n".join(lines) + "\n"


def _render_subtree(
    tree: dict,
    lines: list[str],
    prefix: str,
) -> None:
    """Recursively render a subtree.

    Args:
        tree: Dict representing the current level of the tree.
        lines: List to append rendered lines to.
        prefix: Current indentation prefix (for nested levels).
    """
    # Sort: directories first, then files, both alphabetical
    dirs = sorted([k for k in tree if tree[k] is not None])
    files = sorted([k for k in tree if tree[k] is None])
    entries = dirs + files

    for i, name in enumerate(entries):
        is_last = i == len(entries) - 1
        connector = "\u2514\u2500\u2500 " if is_last else "\u251c\u2500\u2500 "
        child_prefix = "    " if is_last else "\u2502   "

        if tree[name] is None:
            # File
            lines.append(f"{prefix}{connector}{name}")
        else:
            # Directory
            lines.append(f"{prefix}{connector}{name}/")
            _render_subtree(tree[name], lines, prefix + child_prefix)
