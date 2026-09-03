# Contributing to RepoBrief

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/yourusername/repobrief.git
   cd repobrief
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. **Install in development mode**
   ```bash
   pip install -e ".[dev,cloud]"
   ```

4. **Verify your setup**
   ```bash
   pytest                     # All tests should pass
   ruff check src/ tests/     # No lint errors
   ```

## Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Write tests first** — every new feature or bugfix should include tests.

3. **Follow existing code style** — run `ruff format` before committing.

4. **Keep commits focused** — one logical change per commit.

## Running Tests

```bash
# All tests
pytest

# Specific module
pytest tests/test_scanner/ -v

# With coverage
pytest --cov=repobrief --cov-report=html
```

## Code Style

- **Formatter**: `ruff format` (line length: 100)
- **Linter**: `ruff check` with rules: `E`, `F`, `W`, `I`, `N`, `UP`, `B`, `SIM`
- **Type hints**: Use type hints for all public function signatures
- **Docstrings**: Google-style docstrings for all public functions and classes

## Pull Request Process

1. Ensure all tests pass (`pytest`)
2. Ensure linting passes (`ruff check src/ tests/`)
3. Update the `CHANGELOG.md` if appropriate
4. Open a PR against `main` with a clear description of the change

## Adding a New LLM Backend

RepoBrief is designed to make adding new backends easy:

1. Create a new file in `src/repobrief/backends/` (e.g., `lmstudio.py`)
2. Implement the `LLMBackend` abstract class from `base.py`
3. Add the backend option to `cli.py`
4. Write tests in `tests/test_backends/`
5. Update the README

The interface requires only two methods:
- `generate(system_prompt, user_message, history) -> Iterator[str]`
- `validate() -> Tuple[bool, str]`
