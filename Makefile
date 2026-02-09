.PHONY: dev test lint fmt check link unlink

dev: ## Install in development mode
	uv sync
	@echo "✓ Development mode ready"

test: ## Run tests
	uv run pytest -v

lint: ## Lint + type check
	uv run ruff check timberline/ tests/
	uv run basedpyright timberline/

fmt: ## Format + fix imports
	uv run ruff format timberline/ tests/
	uv run ruff check --fix timberline/ tests/

check: fmt lint test ## Format, lint, type check, test

link: dev ## Symlink tl to ~/.local/bin for testing
	@mkdir -p $(HOME)/.local/bin
	@ln -sf $(CURDIR)/.venv/bin/tl $(HOME)/.local/bin/tl
	@echo "✓ tl linked to ~/.local/bin/tl"

unlink: ## Remove tl symlink
	@rm -f $(HOME)/.local/bin/tl
	@echo "✓ tl unlinked"

.DEFAULT_GOAL := dev
