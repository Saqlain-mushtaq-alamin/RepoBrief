# Changelog

All notable changes to RepoBrief will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-09-02

### Added
- **Core scanner**: Recursive directory walker with `.gitignore` support and binary detection
- **Secret detection**: Regex-based scanning for API keys, tokens, passwords, and credentials with `--redact` mode
- **Token counting**: Accurate token counting via `tiktoken` with character-based fallback
- **File scoring**: Multi-factor relevance scoring (git recency, file size, import centrality, keyword match)
- **Budget selection**: Greedy file selector that fits files within configurable token budget
- **Output formats**: Markdown, XML, and plain text digest generation
- **Export mode**: `repobrief pack` command with file, clipboard, and stdout output
- **Cloud backend**: Anthropic (Claude) and OpenAI (GPT) API integration with real-time streaming
- **Ollama backend**: Fully offline local LLM chat via Ollama REST API
- **Chat mode**: One-shot (`-q`) and interactive REPL modes
- **GitHub URL support**: Direct packing from `https://github.com/user/repo` URLs
- **Config file**: `.repobrief.yml` for persistent project-level settings
- **Error handling**: Graceful degradation, helpful error messages, first-run setup guide
- **Packaging & CI**: Full PyPI packaging configuration, GitHub Actions CI workflow, issue templates
