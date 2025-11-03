# Solo-Git Makefile
# Phase 2: Audit and Refactor Automation

.PHONY: help audit refactor preflight ci clean install test lint format type-check

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "Solo-Git Phase 2 Automation"
	@echo "============================"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation
install: ## Install Solo-Git in development mode
	pip install -e .[dev,test]

install-ci: ## Install dependencies for CI
	pip install -e .[dev,test]
	pip install coverage pytest-cov pytest-xdist

# Audit commands
audit: audit-coverage audit-gaps audit-complexity ## Run complete audit (coverage, gaps, complexity)

audit-coverage: ## Generate coverage matrix
	@echo "Generating coverage matrix..."
	@python3 scripts/generate_coverage_matrix.py

audit-gaps: ## Analyze code gaps and inconsistencies
	@echo "Analyzing code gaps..."
	@python3 scripts/analyze_gaps.py

audit-complexity: ## Analyze code complexity
	@echo "Analyzing code complexity..."
	@python3 scripts/analyze_complexity.py

# Code quality
lint: ## Run linters (ruff, flake8)
	@echo "Running linters..."
	@ruff check sologit/ tests/ || true
	@echo "Lint check complete"

format: ## Format code (black, isort)
	@echo "Formatting code..."
	@black sologit/ tests/
	@isort sologit/ tests/
	@echo "Code formatted"

format-check: ## Check code formatting without modifying
	@echo "Checking code format..."
	@black --check sologit/ tests/
	@isort --check sologit/ tests/

type-check: ## Run type checker (mypy)
	@echo "Running type checker..."
	@mypy sologit/ --config-file=pyproject.toml || true

# Testing
test: ## Run all tests
	@echo "Running all tests..."
	@pytest tests/ -v

test-fast: ## Run tests in parallel (faster)
	@echo "Running tests in parallel..."
	@pytest tests/ -n auto

test-coverage: ## Run tests with coverage report
	@echo "Running tests with coverage..."
	@pytest --cov=sologit --cov-report=term-missing --cov-report=html tests/
	@echo "Coverage report generated in htmlcov/"

test-unit: ## Run only unit tests
	@pytest tests/ -v -m "not integration"

test-integration: ## Run only integration tests
	@pytest tests/ -v -m integration

# Pre-flight test suite
preflight: preflight-startup preflight-core preflight-errors preflight-io preflight-contracts ## Run complete pre-flight test suite

preflight-startup: ## Test startup and initialization
	@echo "Running startup tests..."
	@python3 scripts/preflight/test_startup.py

preflight-core: ## Test core features A-Z
	@echo "Running core feature tests..."
	@python3 scripts/preflight/test_core_features.py

preflight-errors: ## Test error paths and edge cases
	@echo "Running error path tests..."
	@python3 scripts/preflight/test_error_paths.py

preflight-io: ## Test persistence and I/O
	@echo "Running I/O tests..."
	@python3 scripts/preflight/test_persistence.py

preflight-contracts: ## Test CLI/API/GUI contracts
	@echo "Running contract tests..."
	@python3 scripts/preflight/test_contracts.py

# Refactoring
refactor: refactor-duplicates refactor-extract refactor-naming ## Run safe refactoring steps

refactor-duplicates: ## Consolidate duplicate code
	@echo "Consolidating duplicate code..."
	@python3 scripts/refactor/consolidate_duplicates.py

refactor-extract: ## Extract large functions
	@echo "Extracting large functions..."
	@python3 scripts/refactor/extract_functions.py

refactor-naming: ## Standardize naming conventions
	@echo "Standardizing naming..."
	@python3 scripts/refactor/standardize_naming.py

# CI pipeline
ci: ci-lint ci-type ci-test ci-coverage ci-preflight ## Run complete CI pipeline

ci-lint: lint ## CI: Linting step

ci-type: type-check ## CI: Type checking step

ci-test: test ## CI: Run all tests

ci-coverage: ## CI: Coverage check (fails if below threshold)
	@echo "Checking coverage threshold..."
	@pytest --cov=sologit --cov-report=term --cov-fail-under=76 tests/

ci-preflight: preflight ## CI: Pre-flight test suite

# Documentation
docs: ## Generate documentation
	@echo "Generating documentation..."
	@python3 scripts/generate_docs.py

# Cleanup
clean: clean-pyc clean-test clean-build ## Clean all generated files

clean-pyc: ## Remove Python file artifacts
	@echo "Cleaning Python artifacts..."
	@find . -type f -name '*.py[co]' -delete
	@find . -type d -name '__pycache__' -delete

clean-test: ## Remove test and coverage artifacts
	@echo "Cleaning test artifacts..."
	@rm -rf .pytest_cache
	@rm -rf .coverage
	@rm -rf htmlcov/
	@rm -rf .mypy_cache

clean-build: ## Remove build artifacts
	@echo "Cleaning build artifacts..."
	@rm -rf build/
	@rm -rf dist/
	@rm -rf *.egg-info

# Report generation
report: ## Generate audit report
	@echo "Generating audit report..."
	@python3 scripts/generate_audit_report.py

# Development helpers
watch-test: ## Watch for changes and run tests automatically
	@echo "Watching for changes..."
	@pytest-watch tests/

shell: ## Start interactive Python shell with Solo-Git imported
	@python3 -c "import sologit; import IPython; IPython.embed()"

# Version info
version: ## Show version information
	@python3 -c "import sologit; print(f'Solo-Git v{sologit.__version__}')"

# Quick validation
quick-check: format-check lint type-check test-fast ## Quick validation (format, lint, type, fast tests)
	@echo "✓ Quick check passed!"

# Full validation
full-check: format-check lint type-check test-coverage preflight ## Full validation
	@echo "✓ Full check passed!"
