"""Centralized console output utilities using rich.

Provides consistent, styled terminal output throughout the application.
All user-facing print statements should go through these functions
to ensure consistent formatting and respect the verbosity setting.
"""

from __future__ import annotations

from enum import IntEnum

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from repobrief.errors import RepoBriefError


class Verbosity(IntEnum):
    """Output verbosity levels."""

    QUIET = 0  # Only errors and final output
    NORMAL = 1  # Standard progress messages (default)
    VERBOSE = 2  # Detailed debug-level output


# Module-level console instance -- import this throughout the app
console = Console(stderr=True)  # Status messages go to stderr
output_console = Console()  # Actual digest output goes to stdout

# Current verbosity level (set by CLI flags)
_verbosity: Verbosity = Verbosity.NORMAL


def set_verbosity(level: Verbosity) -> None:
    """Set the global verbosity level."""
    global _verbosity
    _verbosity = level


def get_verbosity() -> Verbosity:
    """Get the current verbosity level."""
    return _verbosity


# -- Output Functions ---------------------------------------------------------


def info(message: str) -> None:
    """Print an informational message (hidden in quiet mode)."""
    if _verbosity >= Verbosity.NORMAL:
        console.print(message)


def success(message: str) -> None:
    """Print a success message (hidden in quiet mode)."""
    if _verbosity >= Verbosity.NORMAL:
        console.print(f"[bold green]{message}[/]")


def warning(message: str) -> None:
    """Print a warning message (always shown, even in quiet mode)."""
    console.print(f"[yellow]{message}[/]")


def error(message: str, hint: str = "") -> None:
    """Print an error message (always shown).

    Args:
        message: The error description.
        hint: Optional actionable suggestion.
    """
    console.print(f"[bold red]{message}[/]")
    if hint:
        console.print(f"[dim]   {hint}[/]")


def debug(message: str) -> None:
    """Print a debug message (only in verbose mode)."""
    if _verbosity >= Verbosity.VERBOSE:
        console.print(f"[dim]{message}[/]")


def print_repobrief_error(err: RepoBriefError) -> None:
    """Pretty-print a RepoBriefError with its hint."""
    error(err.message, err.hint)


def print_unexpected_error(err: Exception) -> None:
    """Print an unexpected internal error with a traceback hint."""
    console.print(
        Panel(
            f"[bold red]Unexpected error: {type(err).__name__}[/]\n\n"
            f"[white]{err}[/]\n\n"
            f"[dim]This is likely a bug in RepoBrief. Please report it at:\n"
            f"https://github.com/yourusername/repobrief/issues\n\n"
            f"Run with --verbose for a full traceback.[/]",
            title="[red]Internal Error[/]",
            border_style="red",
        )
    )


# -- Summary Helpers ----------------------------------------------------------


def print_scan_summary(
    total_scanned: int,
    after_secrets: int,
    selected: int,
    tokens_used: int,
    token_budget: int,
    secrets_found: int = 0,
    warnings: list[str] | None = None,
) -> None:
    """Print a formatted summary table of the scan/pack operation.

    Args:
        total_scanned: Files found by scanner.
        after_secrets: Files remaining after secret filtering.
        selected: Files included in the digest.
        tokens_used: Tokens consumed by selected files.
        token_budget: Maximum token budget.
        secrets_found: Number of secret findings.
        warnings: List of warning messages to display.
    """
    if _verbosity < Verbosity.NORMAL:
        return

    table = Table(title="Packing Summary", show_header=False, border_style="blue")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Files scanned", str(total_scanned))
    if secrets_found > 0:
        table.add_row("Secrets found", f"[yellow]{secrets_found}[/]")
    table.add_row("Files after filtering", str(after_secrets))
    table.add_row("Files selected", f"[green]{selected}[/]")

    pct = (tokens_used / token_budget * 100) if token_budget > 0 else 0
    color = "green" if pct < 80 else ("yellow" if pct < 95 else "red")
    table.add_row(
        "Token usage",
        f"[{color}]{tokens_used:,} / {token_budget:,} ({pct:.1f}%)[/]",
    )

    console.print(table)

    if warnings:
        for w in warnings:
            warning(w)
