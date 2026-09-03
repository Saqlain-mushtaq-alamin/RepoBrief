<div align="center">

# 🧠 RepoBrief

**Pack any repo into clean LLM context, then chat with it.**

*Using Claude, GPT, or a fully offline Ollama model. No vector DB. No GPU. One command.*

[![PyPI version](https://img.shields.io/pypi/v/repobrief.svg)](https://pypi.org/project/repobrief/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

[Installation](#installation) • [Quick Start](#quick-start) • [Chat Mode](#chat-mode) • [Configuration](#configuration) • [How It Works](#how-it-works)

</div>

---

## Why RepoBrief?

You need to explain your codebase to an LLM — for code review, debugging, onboarding, or docs. Today, you either:
- **Copy-paste files manually** — slow, error-prone, easy to forget files or include secrets
- **Use a packing tool** (Repomix, Gitingest) — great, but they just dump text. No follow-up.
- **Use a RAG chatbot** (ollama-chat, etc.) — needs ChromaDB, embeddings, GPU, and 16GB+ RAM

**RepoBrief does both — packing AND chatting — without the RAM cost:**

| Feature | Repomix | Gitingest | RAG chatbots | **RepoBrief** |
|---------|---------|-----------|--------------|---------------|
| Pack repo into LLM context | ✅ | ✅ | ❌ | ✅ |
| Chat with codebase | ❌ | ❌ | ✅ | ✅ |
| No vector DB / embeddings | ✅ | ✅ | ❌ | ✅ |
| Works on 8GB RAM laptop | ✅ | ✅ | ❌ | ✅ |
| Cloud + local LLM support | ❌ | ❌ | Partial | ✅ |
| Secret detection & redaction | ✅ | ❌ | ❌ | ✅ |
| GitHub repository pack/chat | ✅ | ✅ | ❌ | ✅ |

---

## Installation

```bash
pip install repobrief
```

For cloud LLM support (Claude/GPT):
```bash
pip install repobrief[cloud]
```

That's it. No Docker, no database, no GPU required.

---

## Quick Start

### Pack a repo (export mode)

```bash
# Pack the current directory into a markdown digest
repobrief pack .

# Save to a file, limit to 50k tokens
repobrief pack ./my-project --max-tokens 50000 -o context.md

# XML format for structured parsing
repobrief pack . --format xml -o context.xml

# Copy directly to clipboard
repobrief pack . --clipboard

# Pack directly from a GitHub URL
repobrief pack https://github.com/pallets/flask
```

### Chat with a repo

```bash
# Ask a question using Claude
export ANTHROPIC_API_KEY=sk-ant-...
repobrief chat . --backend cloud -q "Where is user authentication handled?"

# Fully offline using Ollama (no API key needed)
repobrief chat . --backend ollama --model llama3.2:3b -q "What does the payment module do?"

# Interactive mode — ask follow-up questions
repobrief chat . --backend ollama --model llama3.2:3b
> Where is the rate limiter implemented?
> How would I add a new middleware?
> exit
```

---

## Chat Mode

RepoBrief's chat mode doesn't use RAG, embeddings, or vector databases. Instead, it:

1. **Packs** your repo into a token-budgeted digest (like export mode)
2. **Scores** files by relevance to your question (keyword matching, git recency, import centrality)
3. **Sends** the digest + your question to the chosen LLM backend
4. **Streams** the answer back to your terminal with real-time markdown rendering

This means it works on any machine that can run Python — even an old laptop with 4GB of free RAM.

### Supported Backends

| Backend | Setup | Best For |
|---------|-------|----------|
| **Anthropic (Claude)** | `export ANTHROPIC_API_KEY=sk-ant-...` | Best quality, fast streaming |
| **OpenAI (GPT)** | `export OPENAI_API_KEY=sk-...` | Great quality, widely available |
| **Ollama (local)** | `ollama pull llama3.2:3b` | Free, 100% private, offline |

---

## Configuration

### CLI Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--max-tokens` | Token budget for file selection | `100000` |
| `--format` | Output format: `markdown`, `xml`, `plain` | `markdown` |
| `-o, --output` | Write digest to file | stdout |
| `--clipboard` | Copy digest to clipboard | off |
| `--exclude` | Extra glob patterns to exclude (repeatable) | none |
| `--redact / --no-redact` | Redact secrets vs exclude files | exclude |
| `--backend` | LLM backend: `cloud` or `ollama` | `cloud` |
| `--model` | Model identifier | `claude-sonnet-4-20250514` |
| `-q, --question` | Question for one-shot chat mode | interactive |
| `-v, --verbose` | Show detailed debug output | off |
| `--quiet` | Suppress all output except errors | off |

### Config File

Create `.repobrief.yml` in your project root for persistent settings:

```yaml
backend: ollama
model: llama3.2:3b
max_tokens: 40000
format: markdown
exclude:
  - "*.test.js"
  - "docs/"
```

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `REPOBRIEF_API_KEY` | Generic API key (auto-detects provider) |
| `OLLAMA_HOST` | Ollama server URL (default: `http://localhost:11434`) |

---

## How It Works

```
repobrief pack/chat <path>
        │
        ▼
  ┌─── SCAN ──────── Walk repo, respect .gitignore, skip binaries
  │
  ├─── SECRET SCAN ── Regex detection of API keys, tokens, passwords
  │
  ├─── SCORE ──────── Rank files by recency, size, centrality, keyword match
  │
  ├─── SELECT ─────── Greedily pick best files within token budget
  │
  ├─── PACK ───────── Build directory tree + concatenated file content
  │
  └─── OUTPUT
        ├── Export: save to file / clipboard / stdout
        └── Chat: send digest + question to Cloud API or local Ollama
```

### Secret Detection

RepoBrief automatically detects and excludes files containing:
- AWS access keys, GitHub PATs, OpenAI/Anthropic API keys
- Private keys (RSA, EC, DSA, OPENSSH)
- `.env` files with credentials
- Hardcoded passwords and generic secret assignments
- Slack tokens, Stripe keys

Use `--redact` to include files with secrets replaced by `[REDACTED]` instead of excluding them entirely.

---

## Development

```bash
# Clone and setup
git clone https://github.com/yourusername/repobrief.git
cd repobrief
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev,cloud]"

# Run tests
pytest

# Lint and format
ruff check src/ tests/
ruff format src/ tests/

# Type check
mypy src/
```

---

## License

MIT — see [LICENSE](./LICENSE) for details.
