# 📖 RepoBrief User Guide

Welcome to the **RepoBrief User Guide**. This document explains how to install, configure, and use RepoBrief for packing codebases into clean LLM context and chatting with codebases offline or in the cloud.

---

## Table of Contents

1. [Installation](#1-installation)
2. [Basic Usage & Export Mode (`pack`)](#2-basic-usage--export-mode-pack)
3. [Chat Mode (`chat`)](#3-chat-mode-chat)
4. [Secret Detection & Redaction](#4-secret-detection--redaction)
5. [Configuration File (`.repobrief.yml`)](#5-configuration-file-repobriefyml)
6. [GitHub Remote Repositories](#6-github-remote-repositories)
7. [Advanced CLI Reference](#7-advanced-cli-reference)
8. [Troubleshooting & FAQs](#8-troubleshooting--faqs)

---

## 1. Installation

RepoBrief requires Python 3.9 or higher.

### Standard Installation
```bash
pip install repobrief
```

### Installation with Cloud LLM Support (Claude & GPT)
```bash
pip install repobrief[cloud]
```

### Verification
Check that RepoBrief is installed correctly:
```bash
repobrief --version
```

---

## 2. Basic Usage & Export Mode (`pack`)

Export mode gathers project source files, applies secret filters, scores relevance, enforces a token budget, and generates a structured digest.

### Common Examples

```bash
# 1. Output digest to standard output (terminal)
repobrief pack .

# 2. Save digest to a file
repobrief pack . -o context.md

# 3. Limit token size to 50,000 tokens
repobrief pack . --max-tokens 50000 -o context.md

# 4. Export in XML format (great for Claude XML prompt style)
repobrief pack . --format xml -o context.xml

# 5. Export in Plain text format
repobrief pack . --format plain -o context.txt

# 6. Copy digest directly to clipboard
repobrief pack . --clipboard

# 7. Exclude additional custom file patterns
repobrief pack . --exclude "*.spec.ts" --exclude "docs/"
```

---

## 3. Chat Mode (`chat`)

Chat mode allows you to ask questions about your codebase directly from the CLI.

### Option A: Cloud LLMs (Anthropic Claude & OpenAI GPT)

Set your API key in environment variables:

```bash
# For Anthropic Claude
export ANTHROPIC_API_KEY=sk-ant-...

# For OpenAI GPT
export OPENAI_API_KEY=sk-...

# One-shot query mode
repobrief chat . --backend cloud -q "Where is user authentication logic located?"
```

### Option B: Local Offline LLMs (Ollama)

Run 100% private, free LLMs locally with zero API key requirement:

1. Download & start [Ollama](https://ollama.com).
2. Pull your preferred model:
   ```bash
   ollama pull llama3.2:3b
   ```
3. Chat with your repository:
   ```bash
   # One-shot mode
   repobrief chat . --backend ollama --model llama3.2:3b -q "Explain how the database connection is initialized."

   # Interactive REPL mode
   repobrief chat . --backend ollama --model llama3.2:3b
   ```

### Interactive REPL Session Example
```text
Interactive mode (type 'exit' or 'quit' to leave)

> How are CLI flags parsed?
[RepoBrief streams answer here...]

> Where is error handling defined for backend failures?
[RepoBrief streams answer here...]

> quit
Goodbye!
```

---

## 4. Secret Detection & Redaction

RepoBrief automatically inspects files for secrets (API keys, private keys, passwords, database tokens).

### Default Behavior (Exclusion)
By default, files containing secrets are completely excluded from the digest to protect sensitive data:
```bash
repobrief pack .
# Output: Found 2 potential secret(s) -- excluded 1 file(s)
```

### Redaction Mode (`--redact`)
If you want to keep the file structure while hiding the actual secret values, use `--redact`:
```bash
repobrief pack . --redact
```
Detected secrets will be replaced with `[REDACTED]` in the output text.

---

## 5. Configuration File (`.repobrief.yml`)

You can create a `.repobrief.yml` file in your repository root to save persistent defaults:

```yaml
backend: ollama
model: llama3.2:3b
max_tokens: 40000
format: markdown
exclude:
  - "*.test.js"
  - "dist/"
  - "docs/legacy/"
```

CLI flags override settings in `.repobrief.yml`.

---

## 6. GitHub Remote Repositories

You can pack or chat with public GitHub repositories directly without manual cloning:

```bash
# Pack a GitHub repo into a file
repobrief pack https://github.com/pallets/flask -o flask_context.md

# Chat with a GitHub repo
repobrief chat https://github.com/pallets/flask --backend cloud -q "How are routes registered?"
```

---

## 7. Advanced CLI Reference

| Flag / Option | Command | Description | Default |
|---------------|---------|-------------|---------|
| `-o, --output` | `pack` | Write digest output to specified file path | stdout |
| `--clipboard` | `pack` | Copy output digest directly to system clipboard | `False` |
| `-f, --format` | `pack` | Format of output digest (`markdown`, `xml`, `plain`) | `markdown` |
| `--max-tokens` | `pack`, `chat` | Maximum token budget for selected files | `100000` |
| `--exclude` | `pack`, `chat` | Extra glob exclusion pattern (repeatable) | `[]` |
| `--redact / --no-redact` | `pack` | Redact secret strings instead of excluding files | `False` (Exclude) |
| `--backend` | `chat` | Choice of LLM backend (`cloud` or `ollama`) | `cloud` |
| `--model` | `chat` | Identifier of model to query | `claude-sonnet-4-20250514` |
| `-q, --question` | `chat` | Question string for one-shot chat mode | Interactive REPL |
| `-v, --verbose` | All | Enable detailed debug logs and tracebacks | `False` |
| `--quiet` | All | Suppress all progress bars and summaries except output/errors | `False` |

---

## 8. Troubleshooting & FAQs

### Q: Why am I getting an API key missing error?
**A:** Ensure `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` is exported in your active terminal session, or use local Ollama (`--backend ollama`).

### Q: Why did Ollama connection fail?
**A:** Ensure the Ollama desktop app or service is running (`ollama serve`). By default RepoBrief connects to `http://localhost:11434`. You can customize the URL via `OLLAMA_HOST`.

### Q: Why were some files omitted from my digest?
**A:** Files are omitted if:
1. They match ignore rules (`.gitignore`, binary files, built-in exclusions).
2. They triggered secret detection (override with `--redact`).
3. The total token count exceeded `--max-tokens` budget (increase budget with `--max-tokens 150000`).
