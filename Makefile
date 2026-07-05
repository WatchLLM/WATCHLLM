# WatchLLM Monorepo Makefile
# Usage: make install-dev    — install all Python packages in editable mode
#        make test-all       — run all tests across the ecosystem
#        make status         — check component health
#        make clean          — remove build artifacts

.PHONY: install-dev test-all status clean build-runtime build-vscode help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------

install-dev: ## Install all Python packages in editable mode (correct dependency order)
	pip install -e kernel/
	pip install -e klyd/
	pip install -e orchestrator/
	pip install -e benchmarks/
	pip install -e reliability/
	pip install -e watchllm-cli/
	@echo ""
	@echo "All packages installed. Run 'make status' to verify."

# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

test-all: test-kernel test-klyd test-orchestrator test-reliability test-vscode ## Run all test suites

test-kernel: ## Run kernel Python tests
	cd kernel && python -m pytest tests/ -v

test-klyd: ## Run klyd tests
	cd klyd && python -m pytest tests/ -v

test-orchestrator: ## Run orchestrator tests
	cd orchestrator && python -m pytest tests/ -v

test-reliability: ## Run reliability tests
	cd reliability && python -m pytest tests/ -v

test-vscode: ## Run VS Code extension tests
	cd vscode && npm test

test-runtime: ## Run Rust runtime tests
	cd runtime && cargo test --workspace

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

build-runtime: ## Build the Rust runtime (release mode)
	cd runtime && cargo build --release

build-vscode: ## Build the VS Code extension
	cd vscode && npm install && npm run build

# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

status: ## Check health of all installed WatchLLM components
	@watchllm status 2>/dev/null || python -m watchllm_cli.cli status 2>/dev/null || echo "watchllm CLI not installed. Run 'make install-dev' first."

# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------

clean: ## Remove build artifacts and caches
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -not -path "./.git/*" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned."
