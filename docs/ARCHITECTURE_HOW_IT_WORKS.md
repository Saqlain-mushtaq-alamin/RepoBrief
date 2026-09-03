# 🏗️ RepoBrief Architecture & How It Works

This document provides a comprehensive technical architectural breakdown of **RepoBrief** — how it scans repositories, detects secrets, calculates token budgets, scores code files, formats context digests, and streams responses from cloud APIs or local LLMs.

---

## 1. High-Level Architecture Overview

RepoBrief follows a clean 6-stage pipeline design where each component is isolated, modular, and testable:

```
                  ┌─────────────────────────────────────┐
                  │          CLI / User Entry           │
                  └──────────────────┬──────────────────┘
                                     │
                                     ▼
                  ┌─────────────────────────────────────┐
                  │ 1. SCANNER (walker, ignore, git)    │
                  └──────────────────┬──────────────────┘
                                     │ Scanned Files
                                     ▼
                  ┌─────────────────────────────────────┐
                  │ 2. SECURITY (secret scanner)        │
                  └──────────────────┬──────────────────┘
                                     │ Clean / Redacted Files
                                     ▼
                  ┌─────────────────────────────────────┐
                  │ 3. SCORING & SELECTION              │
                  │    - Tokenizer (tiktoken)           │
                  │    - Scorer (4-factor relevance)    │
                  │    - Selector (greedy budget fit)   │
                  └──────────────────┬──────────────────┘
                                     │ Selected Files
                                     ▼
                  ┌─────────────────────────────────────┐
                  │ 4. PACKER & FORMATTER               │
                  │    - Directory Tree Renderer        │
                  │    - Markdown / XML / Plain Digest │
                  └──────────────────┬──────────────────┘
                                     │ Packed Digest
                                     │
                 ┌───────────────────┴───────────────────┐
                 ▼                                       ▼
    ┌───────────────────────────┐           ┌───────────────────────────┐
    │   EXPORT MODE             │           │   CHAT MODE               │
    │   - Output File / STDOUT  │           │   - Cloud (Claude / GPT)  │
    │   - System Clipboard      │           │   - Ollama (Local REST)   │
    └───────────────────────────┘           └───────────────────────────┘
```

---

## 2. Component Deep Dive

### Stage 1: Core Scanner (`repobrief.scanner`)

- **Walker (`walker.py`)**: Recursively iterates through target directory paths. Detects text vs. binary files using byte inspections (null-byte checks, non-printable characters) and MIME type heuristics.
- **Ignore Engine (`ignore.py`)**: Parses `.gitignore`, `.ignore`, `.repobriefignore`, and built-in rules (e.g., `.git/`, `node_modules/`, `__pycache__/`, `.venv/`, build artifacts). Uses `pathspec` for exact glob pattern matching.
- **Git Metadata (`git_utils.py`)**: Integrates with local Git repo metadata to determine file last-modified timestamps and commit recency. Operates with fallback mode if Git is unavailable.

### Stage 2: Secret Detection & Redaction (`repobrief.security`)

- **Secret Scanner (`secret_scanner.py`)**: Scans all candidate text files against regex rules covering high-risk secret patterns:
  - AWS Access Key IDs & Secret Keys
  - GitHub Personal Access Tokens (Classic & Fine-Grained)
  - OpenAI, Anthropic, Cohere, and HuggingFace API Keys
  - Slack Tokens, Stripe API Keys
  - Private RSA, EC, DSA, OPENSSH Keys
  - `.env` credential assignments & generic password patterns
- **Actions**:
  - `EXCLUDE` (Default): Excludes any file containing secret patterns entirely from the digest.
  - `REDACT`: Keeps the file but replaces detected secret substrings with `[REDACTED]`.

### Stage 3: Token Counting, Scoring & Budgeting (`repobrief.scoring`)

- **Tokenizer (`tokenizer.py`)**: Counts tokens using `tiktoken` (using `cl100k_base` encoding). Includes an LRU-cached instance and a character-based fallback estimate (~4 characters per token) for offline/restricted environments.
- **File Scorer (`scorer.py`)**: Computes a dynamic relevance score for each file using four normalized metrics:
  1. **Git Recency Weight**: Recently modified files receive higher relevance scores.
  2. **File Size / Quality**: Rewards concise, code-dense source files while penalizing massive generated files or huge logs.
  3. **Import Centrality**: Ranks files that are imported heavily across the codebase higher (core utility/model modules).
  4. **Question Relevance**: In chat mode (`-q`), computes TF-IDF style keyword match scores between the user query and file contents.
- **Greedy Budget Selector (`selector.py`)**: Sorts files by descending relevance score and greedily selects files until the specified token budget (default: 100,000 tokens) is met.

### Stage 4: Packing & Formatting (`repobrief.packer`)

- **Tree Renderer (`tree.py`)**: Generates an ASCII/Unicode directory structure visualization representing the selected files.
- **Formatter (`formatter.py`)**: Concatenates selected files into structured digests in one of three output formats:
  - **Markdown (`markdown`)**: Markdown headings, syntax-highlighted code blocks, and metadata header summary.
  - **XML (`xml`)**: Structured `<repository>` tags containing `<file path="...">` nodes for precise programmatic parsing by LLMs.
  - **Plain Text (`plain`)**: Simple separator bars and text headers.

### Stage 5: LLM Backends (`repobrief.backends`)

- **Base Class (`base.py`)**: Defines `LLMBackend` abstract interface with `generate()` token iterator and `validate()` health check.
- **Cloud Backend (`cloud.py`)**:
  - **Anthropic Claude**: Connects via `anthropic` SDK with SSE event streaming.
  - **OpenAI GPT**: Connects via `openai` SDK with real-time stream chunking.
  - Auto-selects provider based on environment variables (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `REPOBRIEF_API_KEY`).
- **Ollama Backend (`ollama.py`)**:
  - Direct REST integration with Ollama server (`http://localhost:11434/api/generate` or `/api/chat`).
  - Supports streaming HTTP JSON lines. Requires 0 external cloud dependencies and 0 API keys.

### Stage 6: CLI & User Interfaces (`repobrief.cli`)

- Powered by `click` and `rich` console output.
- Cross-platform clipboard support (`repobrief.utils.clipboard`).
- Direct GitHub repository cloning and packing support (`repobrief.utils.github`).
- First-run wizard and robust exception handling (`repobrief.errors`).
- Cross-platform safe stdout printing (`_write_stdout`).

---

## 3. Data Flow Diagram

```
User Command: repobrief chat . -q "How is scoring calculated?"
  │
  ├─> 1. Read .repobrief.yml & CLI options
  ├─> 2. Walk directory & filter ignored patterns
  ├─> 3. Scan for secrets (exclude/redact matches)
  ├─> 4. Tokenize & score files against question "How is scoring calculated?"
  ├─> 5. Greedily select highest scoring files up to token limit (e.g. 100,000)
  ├─> 6. Generate Markdown digest containing tree & file contents
  ├─> 7. Format System Prompt with embedded digest
  └─> 8. Stream response from Claude / GPT / Ollama to terminal stdout
```
