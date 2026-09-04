"""RepoBrief CLI -- main entry point.

Usage:
    repobrief pack <path> [options]    Pack a repo into a digest
    repobrief chat <path> [options]    Chat with a repo using an LLM
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from repobrief import __version__
from repobrief.backends.base import ChatMessage, LLMBackend
from repobrief.backends.cloud import CloudBackend
from repobrief.backends.prompts import build_system_prompt
from repobrief.config.settings import build_config
from repobrief.errors import RepoBriefError
from repobrief.packer.formatter import OutputFormat, PackingMetadata, pack_digest
from repobrief.scanner.walker import scan_repository
from repobrief.scoring.scorer import score_files
from repobrief.scoring.selector import select_files_within_budget
from repobrief.security.secret_scanner import SecretAction, scan_files_for_secrets
from repobrief.utils.clipboard import copy_to_clipboard
from repobrief.utils.console import (
    Verbosity,
    console,
    debug,
    error,
    get_verbosity,
    info,
    print_repobrief_error,
    print_scan_summary,
    print_unexpected_error,
    set_verbosity,
    success,
    warning,
)
from repobrief.utils.github import clone_repo, extract_repo_name, is_github_url

# -- Format mapping ------------------------------------------------------------

FORMAT_MAP = {
    "markdown": OutputFormat.MARKDOWN,
    "md": OutputFormat.MARKDOWN,
    "xml": OutputFormat.XML,
    "plain": OutputFormat.PLAIN,
    "txt": OutputFormat.PLAIN,
    "text": OutputFormat.PLAIN,
}


def _write_stdout(text: str) -> None:
    """Safely print text to stdout with UTF-8 encoding on all platforms."""
    try:
        sys.stdout.buffer.write(text.encode("utf-8"))
        if not text.endswith("\n"):
            sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()
    except Exception:
        print(text)


def _check_first_run(config, explicit_backend: bool = False) -> None:
    """Detect first-run scenario and guide the user through setup."""
    from rich.panel import Panel

    has_cloud_key = config.api_key is not None
    has_ollama = False
    try:
        from repobrief.backends.ollama import OllamaBackend

        backend = OllamaBackend(host=config.ollama_host)
        has_ollama = backend._is_server_running()
    except Exception:
        pass

    if has_cloud_key or has_ollama or explicit_backend:
        return  # Already configured or explicitly chosen

    console.print(
        Panel(
            "[bold]Welcome to RepoBrief![/]\n\n"
            "No LLM backend is configured yet. Choose one:\n\n"
            "[bold cyan]1) Cloud API (Claude / OpenAI)[/]\n"
            "   - Needs an API key\n"
            "   - Best quality, fastest responses\n"
            "   - Set: [green]export ANTHROPIC_API_KEY=sk-ant-...[/]\n\n"
            "[bold cyan]2) Local model via Ollama[/]\n"
            "   - Fully offline, free, private\n"
            "   - Install: [green]https://ollama.com/download[/]\n"
            "   - Then: [green]ollama pull llama3.2:3b[/]\n\n"
            "[dim]After setup, run:[/]\n"
            "  [green]repobrief chat . --backend cloud -q \"What does this do?\"[/]\n"
            "  [green]repobrief chat . --backend ollama -q \"What does this do?\"[/]",
            title="[bold blue]First-Time Setup[/]",
            border_style="blue",
        )
    )
    sys.exit(0)


@click.group()
@click.version_option(version=__version__, prog_name="repobrief")
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Show detailed debug output.",
)
@click.option(
    "--quiet",
    is_flag=True,
    default=False,
    help="Suppress all output except errors and the final result.",
)
def main(verbose: bool, quiet: bool) -> None:
    """RepoBrief -- Pack any repo into clean LLM context, then chat with it."""
    if quiet:
        set_verbosity(Verbosity.QUIET)
    elif verbose:
        set_verbosity(Verbosity.VERBOSE)
    else:
        set_verbosity(Verbosity.NORMAL)


@main.command()
@click.argument("path")
@click.option(
    "-o",
    "--output",
    type=click.Path(),
    default=None,
    help="Write digest to this file (default: stdout).",
)
@click.option(
    "--clipboard",
    is_flag=True,
    default=False,
    help="Copy digest to clipboard.",
)
@click.option(
    "-f",
    "--format",
    "output_format",
    default="markdown",
    type=click.Choice(["markdown", "xml", "plain"], case_sensitive=False),
    help="Output format (default: markdown).",
)
@click.option(
    "--max-tokens",
    type=int,
    default=None,
    help="Token budget for file selection (default: 100000).",
)
@click.option(
    "--exclude",
    multiple=True,
    help="Extra glob patterns to exclude (can be repeated).",
)
@click.option(
    "--redact/--no-redact",
    default=False,
    help="Redact secrets instead of excluding files (default: exclude).",
)
def pack(
    path: str,
    output: str | None,
    clipboard: bool,
    output_format: str,
    max_tokens: int | None,
    exclude: tuple,
    redact: bool,
) -> None:
    """Pack a repository into a clean, LLM-ready digest.

    PATH can be a local directory or a GitHub URL.

    Examples:

        repobrief pack .

        repobrief pack ./my-project --max-tokens 50000 --format xml -o context.xml

        repobrief pack https://github.com/user/repo
    """
    try:
        # -- Step 1: Resolve the input path ------------------------------------
        if is_github_url(path):
            repo_name = extract_repo_name(path)
            info(f"Cloning {path}...")
            try:
                repo_path = clone_repo(path)
            except RuntimeError as e:
                error(str(e))
                sys.exit(1)
        else:
            repo_path = Path(path).resolve()
            repo_name = repo_path.name
            if not repo_path.is_dir():
                error(f"Not a directory: {repo_path}")
                sys.exit(1)

        # -- Step 2: Load config -----------------------------------------------
        cli_overrides: dict = {}
        if max_tokens is not None:
            if max_tokens <= 0 or max_tokens > 2_000_000:
                error("Token budget must be between 1 and 2,000,000")
                sys.exit(1)
            cli_overrides["max_tokens"] = max_tokens
        if output_format:
            cli_overrides["output_format"] = output_format

        config = build_config(repo_path, cli_overrides)
        extra_excludes = list(exclude) + config.exclude
        token_budget = config.max_tokens

        # -- Step 3: Scan ------------------------------------------------------
        info("Scanning repository...")
        scanned_files = scan_repository(repo_path, extra_exclude=extra_excludes)
        total_scanned = len(scanned_files)
        debug(f"Found {total_scanned} text files")

        if total_scanned == 0:
            warning("No files found. Check your path and ignore rules.")
            sys.exit(0)

        # -- Step 4: Secret scan -----------------------------------------------
        secret_action = SecretAction.REDACT if redact else SecretAction.EXCLUDE
        clean_files, findings = scan_files_for_secrets(
            scanned_files, action=secret_action
        )

        if findings:
            action_word = "redacted in" if redact else "excluded"
            warning(
                f"Found {len(findings)} potential secret(s) -- "
                f"{action_word} {len(scanned_files) - len(clean_files)} file(s)"
            )
            for finding in findings[:5]:
                debug(f"  - {finding.file_path}: {finding.pattern_name}")
            if len(findings) > 5:
                debug(f"  ... and {len(findings) - 5} more")

        # -- Step 5: Score & Select --------------------------------------------
        info("Scoring and selecting files...")
        scored = score_files(clean_files)
        selected, tokens_used = select_files_within_budget(
            scored, max_tokens=token_budget
        )

        print_scan_summary(
            total_scanned=total_scanned,
            after_secrets=len(clean_files),
            selected=len(selected),
            tokens_used=tokens_used,
            token_budget=token_budget,
            secrets_found=len(findings),
        )

        # -- Step 6: Pack ------------------------------------------------------
        fmt = FORMAT_MAP.get(output_format.lower(), OutputFormat.MARKDOWN)
        metadata = PackingMetadata(
            repo_name=repo_name,
            files_included=len(selected),
            files_scanned=total_scanned,
            tokens_used=tokens_used,
            token_budget=token_budget,
        )
        digest = pack_digest(selected, metadata, output_format=fmt)

        # -- Step 7: Output ----------------------------------------------------
        if output:
            output_path = Path(output)
            if not output_path.parent.is_dir():
                error(f"Output directory does not exist: {output_path.parent}")
                sys.exit(1)
            output_path.write_text(digest, encoding="utf-8")
            info(f"Digest written to {output_path}")
        elif clipboard:
            if copy_to_clipboard(digest):
                info("Digest copied to clipboard!")
            else:
                warning("Could not copy to clipboard. Printing to stdout instead.")
                _write_stdout(digest)
        else:
            _write_stdout(digest)

        success("Done!")

    except RepoBriefError as e:
        print_repobrief_error(e)
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/]")
        sys.exit(130)
    except Exception as e:
        if get_verbosity() >= Verbosity.VERBOSE:
            console.print_exception()
        else:
            print_unexpected_error(e)
        sys.exit(1)


def _ask_question(
    backend: LLMBackend,
    system_prompt: str,
    question: str,
    history: list[ChatMessage],
) -> str:
    """Send a question to the backend and stream the response.

    Returns the complete response text (for conversation history).
    """
    console.print()  # Blank line before response
    full_response: list[str] = []

    try:
        for chunk in backend.generate(system_prompt, question, history):
            console.print(chunk, end="", highlight=False)
            full_response.append(chunk)
    except PermissionError as e:
        console.print(f"\n[bold red]Authentication error: {e}[/]")
        return ""
    except ConnectionError as e:
        console.print(f"\n[bold red]Connection error: {e}[/]")
        return ""
    except RuntimeError as e:
        console.print(f"\n[bold red]Error: {e}[/]")
        return ""

    console.print("\n")  # Blank line after response
    return "".join(full_response)


@main.command()
@click.argument("path")
@click.option(
    "-q",
    "--question",
    type=str,
    default=None,
    help="Question to ask about the codebase (one-shot mode).",
)
@click.option(
    "--backend",
    type=click.Choice(["cloud", "ollama"]),
    default=None,
    help="LLM backend to use.",
)
@click.option(
    "--model",
    type=str,
    default=None,
    help="Model name/identifier.",
)
@click.option(
    "--max-tokens",
    "max_tokens",
    type=int,
    default=None,
    help="Token budget for file selection.",
)
@click.option(
    "--exclude",
    multiple=True,
    help="Extra glob patterns to exclude.",
)
def chat(
    path: str,
    question: str | None,
    backend: str | None,
    model: str | None,
    max_tokens: int | None,
    exclude: tuple,
) -> None:
    """Chat with a repository using an LLM backend.

    PATH can be a local directory or a GitHub URL.

    Examples:

        repobrief chat . --backend cloud -q "Where is auth handled?"

        repobrief chat . --backend ollama --model llama3.1:8b
    """
    try:
        # -- Step 1: Resolve path -----------------------------------------------
        if is_github_url(path):
            repo_name = extract_repo_name(path)
            info(f"Cloning {path}...")
            try:
                repo_path = clone_repo(path)
            except RuntimeError as e:
                error(str(e))
                sys.exit(1)
        else:
            repo_path = Path(path).resolve()
            repo_name = repo_path.name
            if not repo_path.is_dir():
                error(f"Not a directory: {repo_path}")
                sys.exit(1)

        # -- Step 2: Load config -----------------------------------------------
        cli_overrides: dict = {}
        if backend:
            cli_overrides["backend"] = backend
        if model:
            if not model.strip():
                error("Model name cannot be empty")
                sys.exit(1)
            cli_overrides["model"] = model
        if max_tokens:
            if max_tokens <= 0 or max_tokens > 2_000_000:
                error("Token budget must be between 1 and 2,000,000")
                sys.exit(1)
            cli_overrides["max_tokens"] = max_tokens

        config = build_config(repo_path, cli_overrides)
        extra_excludes = list(exclude) + config.exclude

        # -- Step 3: First-run check -------------------------------------------
        _check_first_run(config, explicit_backend=(backend is not None))

        # -- Step 4: Initialize backend ----------------------------------------
        if config.backend == "ollama":
            from repobrief.backends.ollama import OllamaBackend

            llm_backend = OllamaBackend(
                model=config.model,
                host=config.ollama_host,
            )
        else:
            llm_backend = CloudBackend(
                model=config.model,
                api_key=config.api_key,
            )

        # Validate backend
        is_valid, message = llm_backend.validate()
        if not is_valid:
            error("Backend not ready", hint=message)
            sys.exit(1)
        debug(f"Backend: {llm_backend.name}")

        # -- Step 5: Build digest ----------------------------------------------
        info("Scanning repository...")
        scanned_files = scan_repository(repo_path, extra_exclude=extra_excludes)
        clean_files, _ = scan_files_for_secrets(scanned_files)

        # Score with question awareness (if provided)
        scored = score_files(clean_files, question=question)
        selected, tokens_used = select_files_within_budget(
            scored, max_tokens=config.max_tokens
        )

        debug(f"{len(selected)} files selected ({tokens_used:,} tokens)")

        metadata = PackingMetadata(
            repo_name=repo_name,
            files_included=len(selected),
            files_scanned=len(scanned_files),
            tokens_used=tokens_used,
            token_budget=config.max_tokens,
        )
        digest = pack_digest(selected, metadata, OutputFormat.MARKDOWN)
        system_prompt = build_system_prompt(digest)

        # -- Step 6: One-shot or REPL ------------------------------------------
        if question:
            _ask_question(llm_backend, system_prompt, question, history=[])
        else:
            console.print(
                "\n[bold]Interactive mode[/] (type 'exit' or 'quit' to leave)\n"
            )
            history: list[ChatMessage] = []
            while True:
                try:
                    user_input = console.input("[bold cyan]> [/]").strip()
                except (EOFError, KeyboardInterrupt):
                    console.print("\n[dim]Goodbye![/]")
                    break

                if user_input.lower() in ("exit", "quit", "q"):
                    console.print("[dim]Goodbye![/]")
                    break

                if not user_input:
                    continue

                response = _ask_question(
                    llm_backend, system_prompt, user_input, history
                )
                history.append(ChatMessage(role="user", content=user_input))
                history.append(ChatMessage(role="assistant", content=response))

    except RepoBriefError as e:
        print_repobrief_error(e)
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/]")
        sys.exit(130)
    except Exception as e:
        if get_verbosity() >= Verbosity.VERBOSE:
            console.print_exception()
        else:
            print_unexpected_error(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
