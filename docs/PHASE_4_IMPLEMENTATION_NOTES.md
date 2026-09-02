# Phase 4 Implementation Notes

**Date**: 2026-08-28
**Status**: Completed

---

## What Was Implemented

### 1. `src/repobrief/scoring/tokenizer.py` — Token Counting

- `count_tokens(text, encoding_name)` — Accurate token counting using tiktoken `cl100k_base` encoding
- `estimate_tokens_fast(text)` — Fast approximate count (~4 chars per token)
- `_get_encoding(encoding_name)` — Cached encoding loader (singleton)

### 2. `src/repobrief/scoring/scorer.py` — File Relevance Scoring

#### Weight Configurations
| Mode | Recency | Size | Centrality | Keyword |
|------|---------|------|------------|---------|
| Export | 0.35 | 0.25 | 0.40 | 0.0 |
| Chat | 0.25 | 0.20 | 0.25 | 0.30 |

#### Score Functions
- `_recency_score(last_modified)` — `1.0 / (1.0 + days_ago / 30.0)`, neutral 0.5 if no git data
- `_size_score(size_bytes)` — `1.0 / (1.0 + size_bytes / 2048.0)`
- `_centrality_score(num_importers)` — `log(1 + n) / log(11)`, clamped to [0, 1]
- `_keyword_score(file, question_keywords)` — Fraction of question keywords found in file

#### Import Detection
- `IMPORT_PATTERNS` — 5 regex patterns for Python, JS/TS, Go, Rust, Java/Kotlin
- `_extract_imports(content)` — Extracts import strings from source code
- `compute_centrality_map(files)` — Counts how many files import each file

#### Main Functions
- `_extract_keywords(text)` — Removes stop words, returns lowercased unique words
- `score_files(files, question)` — Returns `(ScannedFile, score)` tuples sorted by relevance

### 3. `src/repobrief/scoring/selector.py` — Budget-Aware Selection

- `DEFAULT_TOKEN_BUDGET` — 100,000 tokens
- `PER_FILE_OVERHEAD_TOKENS` — 20 tokens (header overhead)
- `select_files_within_budget(scored_files, max_tokens)` — Greedy selection, no partial files
- `get_budget_summary(...)` — Human-readable selection summary

---

## Verification Results

| Check | Result |
|-------|--------|
| `pytest tests/test_scoring/ -v` | 18 passed |
| `ruff check src/ tests/` | All checks passed |
| `ruff format --check src/ tests/` | All files formatted |
| Full test suite | 46/46 passed |

---

## Files Created

| File | Purpose |
|------|---------|
| `src/repobrief/scoring/tokenizer.py` | tiktoken wrapper for token counting |
| `src/repobrief/scoring/scorer.py` | Multi-factor file relevance scoring |
| `src/repobrief/scoring/selector.py` | Budget-aware greedy file selection |
| `tests/test_scoring/test_scoring.py` | 18 tests across 4 test classes |

---

## Notes

- Used `from __future__ import annotations` for modern type syntax
- Fixed import ordering and removed unused imports for ruff compliance
- Token counting uses `cl100k_base` (GPT-4/Claude compatible)
- Budget selector enforces hard limit — no partial file inclusion
- No git commits made per instructions
- Ready for Phase 5 implementation
