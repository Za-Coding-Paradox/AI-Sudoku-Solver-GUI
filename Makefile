.PHONY: install run test lint format typecheck clean help

PYTHON  := python3
VENV    := .venv
BIN     := $(VENV)/bin

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

install: ## Create venv and install all dependencies
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -e ".[dev]"
	@echo "✓ Environment ready — activate with: source $(VENV)/bin/activate"

run: ## Launch the Sudoku Solver
	$(BIN)/python -m sudoku.app

test: ## Run the test suite with coverage
	$(BIN)/pytest

lint: ## Run ruff linter
	$(BIN)/ruff check src/ tests/

format: ## Auto-format with ruff
	$(BIN)/ruff format src/ tests/
	$(BIN)/ruff check --fix src/ tests/

typecheck: ## Run mypy static type checker
	$(BIN)/mypy src/

clean: ## Remove build artefacts and caches
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
