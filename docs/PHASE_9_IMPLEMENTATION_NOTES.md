# Phase 9 Implementation Notes

## What Was Built

Production-quality error handling, graceful degradation, centralized exception hierarchy, rich terminal output, and CLI polish (`--verbose`/`--quiet`, first-run detection, input validation).

## Files Created/Modified

| File | Action |
|------|--------|
| `src/repobrief/errors.py` | **New** -- Centralized exception hierarchy (12 exception classes) |
| `src/repobrief/utils/console.py` | **New** -- Rich-based output utilities (info/success/warning/error/debug) |
| `src/repobrief/cli.py` | **Modified** -- Added `--verbose`/`--quiet`, first-run detection, error wrapping, input validation |
| `src/repobrief/scanner/walker.py` | **Modified** -- Wrapped git metadata in try/except for graceful degradation |
| `src/repobrief/scoring/tokenizer.py` | **Modified** -- Added tiktoken fallback to character-based estimation |
| `tests/test_errors.py` | **New** -- 14 tests (exception hierarchy, degradation, CLI validation) |

## Exception Hierarchy

```
RepoBriefError
├── ScanError
├── SecretScanError
├── TokenizationError
├── PackingError
├── BackendError
│   ├── BackendNotConfiguredError
│   ├── BackendConnectionError
│   ├── BackendAuthError
│   └── BackendModelError
├── ConfigError
└── GitHubCloneError
```

All exceptions support a `hint` attribute for actionable user-facing suggestions.

## Console Utilities (`utils/console.py`)

| Function | Purpose |
|----------|---------|
| `info(msg)` | Standard progress (hidden in `--quiet`) |
| `success(msg)` | Success message (hidden in `--quiet`) |
| `warning(msg)` | Warning (always shown) |
| `error(msg, hint)` | Error with optional hint (always shown) |
| `debug(msg)` | Debug info (only in `--verbose`) |
| `print_repobrief_error(err)` | Pretty-print RepoBriefError |
| `print_unexpected_error(err)` | Show internal error with report link |
| `print_scan_summary(...)` | Formatted packing summary table |

## CLI Flags

```bash
# Standard mode (default)
repobrief pack .

# Verbose mode (debug output, full tracebacks)
repobrief --verbose pack .

# Quiet mode (errors + output only)
repobrief --quiet pack .
```

## First-Run Detection

When `repobrief chat` runs without any backend configured, it shows a setup guide:

```
First-Time Setup
No LLM backend is configured yet. Choose one:

1) Cloud API (Claude / OpenAI)
   - Needs an API key
   - Set: export ANTHROPIC_API_KEY=sk-ant-...

2) Local model via Ollama
   - Fully offline, free, private
   - Install: https://ollama.com/download
```

## Graceful Degradation

- **Git metadata**: If git operations fail, scanner continues without recency data (neutral scores)
- **tiktoken**: If tiktoken is unavailable, falls back to character-based estimation (~4 chars/token)
- **Clipboard**: Returns `False` on headless systems, never crashes

## Input Validation

| Input | Validation |
|-------|------------|
| `--max-tokens` | Must be 1-2,000,000 |
| `--model` | Non-empty string |
| `--output` | Parent directory must exist |
| `path` | Must exist and be a directory |

## Tests

14 new tests in `tests/test_errors.py`:
- Exception hierarchy (5 tests) -- all inherit from RepoBriefError
- Graceful degradation (3 tests) -- scanner without git, tokenizer fallback, clipboard failure
- CLI input validation (4 tests) -- nonexistent path, version, verbose, quiet flags

## Polish Checklist

- Every `requests.get/post()` has `timeout` parameter
- File reads use `errors="replace"` for encoding
- `KeyboardInterrupt` exits cleanly (exit code 130)
- `--verbose` shows tracebacks for unexpected errors
- `--quiet` suppresses progress, shows only errors + output
- Empty repos show helpful message, not crash
- No bare `except:` clauses

## Remaining Work

- **Phase 10**: Packaging, distribution, and final documentation
