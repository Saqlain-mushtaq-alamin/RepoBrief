# Phase 8 Implementation Notes

## What Was Built

Ollama local backend for `repobrief chat` -- fully offline LLM chat using Ollama's REST API. No data leaves the user's machine.

## Files Created/Modified

| File | Action |
|------|--------|
| `src/repobrief/backends/ollama.py` | **New** -- `OllamaBackend` with REST API streaming |
| `src/repobrief/cli.py` | **Modified** -- Enabled Ollama backend in chat command |
| `tests/test_backends/test_ollama.py` | **New** -- 10 tests (server detection, model listing, validation, generation) |

## Architecture

```
backends/
├── base.py          # Abstract LLMBackend + ChatMessage
├── cloud.py         # CloudBackend (Anthropic + OpenAI)
├── ollama.py        # OllamaBackend (local, fully offline)  <-- NEW
└── prompts.py       # System prompt template
```

### OllamaBackend (`ollama.py`)

Communicates with Ollama's local REST API:

| Endpoint | Purpose |
|----------|---------|
| `GET /` | Health check |
| `GET /api/tags` | List locally available models |
| `POST /api/chat` | Chat completion with streaming |

### Validation Flow

`validate()` performs two checks:
1. **Is Ollama running?** -- `GET /` → if fails, shows install/serve instructions
2. **Is the model available?** -- `GET /api/tags` → if missing, shows pull instructions + recommended models

### Streaming

Responses are streamed via newline-delimited JSON from `POST /api/chat`:
```
{"model":"llama3.1:8b","message":{"role":"assistant","content":"Hello"},"done":false}
{"model":"llama3.1:8b","message":{"role":"assistant","content":" world"},"done":true}
```

## CLI Usage

```bash
# One-shot question
repobrief chat . --backend ollama --model llama3.2:3b -q "What is this project?"

# Interactive REPL
repobrief chat . --backend ollama --model llama3.1:8b
> What files are in this project?
> How would I add a new feature?
> exit
```

## Configuration

```yaml
# .repobrief.yml
backend: ollama
model: llama3.2:3b
ollama_host: http://localhost:11434
```

## Key Design Decisions

1. **REST API** -- Uses Ollama's HTTP API directly (no Python SDK dependency)
2. **Streaming first** -- Tokens appear incrementally via `iter_lines()`
3. **Actionable errors** -- Missing model shows exact `ollama pull` command + recommended models
4. **Graceful degradation** -- Handles connection errors, timeouts, malformed JSON

## Tests

10 new tests in `tests/test_backends/test_ollama.py`:
- Server detection (running/stopped) -- 2 tests
- Model listing and availability -- 2 tests
- Validation (server down, missing model, all good) -- 3 tests
- Generation (streaming, connection error) -- 2 tests
- Name property -- 1 test

## Remaining Work

- **Phase 9**: Integration tests + end-to-end testing
- **Phase 10**: Packaging + distribution
