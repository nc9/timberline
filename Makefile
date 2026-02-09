.PHONY: dev test lint fmt check link unlink bump publish release

BUMP ?= patch

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

bump: ## Bump version (BUMP=major|minor|patch)
	uv version --bump $(BUMP)

publish: ## Build + publish to PyPI
	rm -rf dist/
	uv build
	uv publish

release: check ## Full release: fmt, lint, test, bump, tag, push, publish
	@if [ -n "$$(git status --porcelain)" ]; then echo "ERROR: dirty working tree" && exit 1; fi
	uv version --bump $(BUMP)
	$(eval VERSION := $(shell uv version --short))
	git add pyproject.toml uv.lock
	git commit -m "chore(release): v$(VERSION)"
	git tag "v$(VERSION)"
	git push && git push --tags
	$(MAKE) publish

.DEFAULT_GOAL := dev
