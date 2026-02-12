# SketchOnFace Makefile
# Requires uv: https://github.com/astral-sh/uv

.PHONY: help install test test-quick lint format check clean

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dev dependencies using uv
	uv sync --dev

test:  ## Run test suite with verbose output
	uv run pytest tests/ -v

test-quick:  ## Run tests without verbose output
	uv run pytest tests/

lint:  ## Run ruff linter
	uv run ruff check .

format:  ## Format code with ruff
	uv run ruff format .

check:  ## Run both linting and tests
	@echo "🔍 Running linter..."
	@$(MAKE) lint
	@echo "\n✅ Linting passed!\n"
	@echo "🧪 Running tests..."
	@$(MAKE) test
	@echo "\n✅ All checks passed!\n"

clean:  ## Clean up cache files
	rm -rf .pytest_cache __pycache__ **/__pycache__ **/*.pyc

.DEFAULT_GOAL := help
