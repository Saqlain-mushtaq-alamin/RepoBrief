# Phase 7 Implementation Notes

## What Was Built

Cloud backend for `repobrief chat` — supports Anthropic (Claude) and OpenAI (GPT) APIs with streaming responses.

## Files Created/Modified

| File | Action |
|------|--------|
| `src/repobrief/backends/base.py` | **New** — Abstract `LLMBackend` interface + `ChatMessage` dataclass |
| `src/repobrief/backends/cloud.py` | **New** — `CloudBackend` with Anthropic + OpenAI streaming |
| `src/repobrief/backends/prompts.py` | **New** — System prompt template for code Q&A |
| `src/repobrief/cli.py` | **Modified** — `chat` command wired up with CloudBackend |
| `tests/test_backends/test_cloud.py` | **New** — 12 tests (provider detection, validation, prompts) |
| `tests/test_cli.py` | **Modified** — Updated chat command tests for new behavior |

## Architecture

```
backends/
├── __init__.py
├── base.py          # Abstract LLMBackend + ChatMessage
├── cloud.py         # CloudBackend (Anthropic + OpenAI)
└── prompts.py       # System prompt template
```

### Backend Interface (`base.py`)

```python
class LLMBackend(ABC):
    @abstractmethod
    def generate(self, system_prompt, user_message, history=None) -> Iterator[str]: ...
    @abstractmethod
    def validate(self) -> tuple[bool, str]: ...
    @property
    @abstractmethod
    def name(self) -> str: ...
```

### Provider Detection (`cloud.py`)

The `CloudBackend` auto-detects the provider from the model name:
- `claude-*` → Anthropic API
- `gpt-*`, `o1-*`, `o3-*` → OpenAI API
- Explicit: `anthropic:my-model` or `openai:my-model`

### CLI Integration (`cli.py`)

The `chat` command now has two modes:
1. **One-shot**: `repobrief chat . -q "question"` — ask once, get answer, exit
2. **Interactive REPL**: `repobrief chat .` — loop with conversation history

Both modes stream tokens to the terminal as they arrive.

## CLI Usage

```bash
# Set API key
export ANTHROPIC_API_KEY=sk-ant-...
# or
export OPENAI_API_KEY=sk-...

# One-shot question
repobrief chat . --backend cloud -q "What is the main entry point?"

# Interactive mode
repobrief chat . --backend cloud

# With GitHub URL
repobrief chat https://github.com/user/repo -q "How does auth work?"
```

## Configuration

Uses existing `.repobrief.yml` from Phase 6:

```yaml
backend: cloud          # or ollama (Phase 8)
model: claude-sonnet-4-20250514
api_key: sk-ant-...     # or use env var
max_tokens: 100000
```

## Key Design Decisions

1. **Streaming first** — Tokens stream to terminal in real-time via `Iterator[str]`
2. **Provider auto-detection** — No need to configure provider separately; inferred from model name
3. **Conversation history** — REPL mode maintains `ChatMessage` history across turns
4. **Graceful error handling** — Auth errors, rate limits, and connection failures show clear messages
5. **Extensible** — Abstract base class makes it easy to add Ollama (Phase 8) or other backends

## Tests

12 new tests in `tests/test_backends/test_cloud.py`:
- Provider detection from model names (5 tests)
- Provider prefix stripping (2 tests)
- Validation logic (3 tests)
- System prompt construction (2 tests)

## Remaining Work

- **Phase 8**: Ollama local backend (`repobrief chat . --backend ollama`)
- **Phase 9**: Integration tests + end-to-end testing
- **Phase 10**: Packaging + distribution
