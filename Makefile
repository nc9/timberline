.PHONY: dev test lint fmt check link unlink

dev: ## Install in development mode
	uv sync
	@echo "✓ Development mode ready"

test: ## Run tests
	uv run pytest -v

lint: ## Lint + type check
	uv run ruff check lumberjack/ tests/
	uv run basedpyright lumberjack/

fmt: ## Format + fix imports
	uv run ruff format lumberjack/ tests/
	uv run ruff check --fix lumberjack/ tests/

check: fmt lint test ## Format, lint, type check, test

link: dev ## Symlink lj to ~/.local/bin for testing
	@mkdir -p $(HOME)/.local/bin
	@ln -sf $(CURDIR)/.venv/bin/lj $(HOME)/.local/bin/lj
	@echo "✓ lj linked to ~/.local/bin/lj"

unlink: ## Remove lj symlink
	@rm -f $(HOME)/.local/bin/lj
	@echo "✓ lj unlinked"

.DEFAULT_GOAL := dev
