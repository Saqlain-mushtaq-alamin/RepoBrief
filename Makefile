.PHONY: help install dev test test-cov lint format typecheck build clean check

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install the package
	pip install -e .

dev:  ## Install with all development dependencies
	pip install -e ".[dev,cloud]"

test:  ## Run all tests
	pytest -v

test-cov:  ## Run tests with coverage report
	pytest --cov=repobrief --cov-report=html --cov-report=term-missing

lint:  ## Run linter
	ruff check src/ tests/

format:  ## Format code
	ruff format src/ tests/

typecheck:  ## Run type checker
	mypy src/

build:  ## Build the package for PyPI
	python -m build

clean:  ## Clean build artifacts
	rm -rf dist/ build/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

check: lint typecheck test  ## Run all checks (lint + typecheck + test)
