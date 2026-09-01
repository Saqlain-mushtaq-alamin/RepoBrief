"""Tests for token counting, file scoring, and budget selection."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from repobrief.scanner.models import ScannedFile
from repobrief.scoring.scorer import (
    _centrality_score,
    _extract_keywords,
    _keyword_score,
    _recency_score,
    _size_score,
    compute_centrality_map,
)
from repobrief.scoring.selector import select_files_within_budget
from repobrief.scoring.tokenizer import count_tokens, estimate_tokens_fast


class TestTokenCounting:
    """Test the tiktoken wrapper."""

    def test_empty_string_is_zero_tokens(self):
        assert count_tokens("") == 0

    def test_hello_world_has_tokens(self):
        tokens = count_tokens("Hello, world!")
        assert tokens > 0
        assert tokens < 10  # Should be ~4 tokens

    def test_code_tokenization(self):
        code = "def hello():\n    print('world')\n"
        tokens = count_tokens(code)
        assert tokens > 0

    def test_fast_estimate_is_reasonable(self):
        text = "This is a test sentence with some words in it."
        exact = count_tokens(text)
        estimate = estimate_tokens_fast(text)
        # Estimate should be in the right ballpark (within 3x)
        assert estimate > 0
        assert 0.3 < (estimate / exact) < 3.0


class TestScoringFunctions:
    """Test individual scoring functions."""

    def test_recency_today_scores_high(self):
        now = datetime.now(timezone.utc)
        assert _recency_score(now) > 0.9

    def test_recency_old_scores_low(self):
        old = datetime.now(timezone.utc) - timedelta(days=365)
        assert _recency_score(old) < 0.2

    def test_recency_none_scores_neutral(self):
        assert _recency_score(None) == 0.5

    def test_size_small_scores_high(self):
        assert _size_score(100) > 0.9

    def test_size_large_scores_low(self):
        assert _size_score(500_000) < 0.01

    def test_centrality_zero_is_zero(self):
        assert _centrality_score(0) == 0.0

    def test_centrality_high_approaches_one(self):
        assert _centrality_score(10) > 0.9

    def test_keyword_full_overlap(self):
        file = ScannedFile(
            path=Path("/repo/auth.py"),
            relative_path=Path("auth.py"),
            size_bytes=100,
            content="def authenticate(user, password): pass",
        )
        keywords = {"authenticate", "password"}
        score = _keyword_score(file, keywords)
        assert score > 0.5

    def test_keyword_no_overlap(self):
        file = ScannedFile(
            path=Path("/repo/math.py"),
            relative_path=Path("math.py"),
            size_bytes=100,
            content="def add(a, b): return a + b",
        )
        keywords = {"authentication", "login"}
        score = _keyword_score(file, keywords)
        assert score == 0.0

    def test_extract_keywords_removes_stop_words(self):
        keywords = _extract_keywords("Where is the user authentication handled?")
        assert "the" not in keywords
        assert "is" not in keywords
        assert "authentication" in keywords
        assert "user" in keywords


class TestCentralityMap:
    """Test import-based centrality computation."""

    def test_imported_file_has_higher_centrality(self):
        files = [
            ScannedFile(
                path=Path("/repo/main.py"),
                relative_path=Path("main.py"),
                size_bytes=100,
                content="from helper import add\n",
            ),
            ScannedFile(
                path=Path("/repo/helper.py"),
                relative_path=Path("helper.py"),
                size_bytes=50,
                content="def add(a, b): return a + b\n",
            ),
        ]
        centrality = compute_centrality_map(files)
        assert centrality[Path("helper.py")] > centrality[Path("main.py")]


class TestBudgetSelection:
    """Test the greedy budget selector."""

    def _make_file(self, name: str, content: str, score: float) -> tuple[ScannedFile, float]:
        f = ScannedFile(
            path=Path(f"/repo/{name}"),
            relative_path=Path(name),
            size_bytes=len(content),
            content=content,
        )
        return (f, score)

    def test_selects_highest_scored_first(self):
        files = [
            self._make_file("a.py", "x" * 100, 0.9),
            self._make_file("b.py", "y" * 100, 0.5),
            self._make_file("c.py", "z" * 100, 0.1),
        ]
        selected, tokens = select_files_within_budget(files, max_tokens=10000)
        assert len(selected) == 3  # All fit

    def test_respects_budget_limit(self):
        # Each "word " * 4000 is roughly 1000 tokens
        files = [
            self._make_file("a.py", "word " * 4000, 0.9),
            self._make_file("b.py", "word " * 4000, 0.5),
            self._make_file("c.py", "word " * 4000, 0.1),
        ]
        selected, tokens = select_files_within_budget(files, max_tokens=2500)
        # Should only fit ~2 files
        assert len(selected) < 3
        assert tokens <= 2500

    def test_empty_input_returns_empty(self):
        selected, tokens = select_files_within_budget([], max_tokens=10000)
        assert selected == []
        assert tokens == 0
