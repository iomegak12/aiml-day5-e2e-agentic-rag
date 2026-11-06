# Makefile - NetCore Systems KB generator (Enterprise RAG demo)
# Requires: GNU make, uv. Works from cmd, PowerShell or Git Bash.

UV          ?= uv
GEN         := scripts/generate_kb.py
VERIFY      := scripts/verify_kb.py
VERIFY_DEPS := --with langchain-community --with pypdf --with beautifulsoup4 --with lxml

.DEFAULT_GOAL := help
.PHONY: help install generate generate-networking generate-meetings regenerate verify clean clean-data

help:  ## List available targets
	@echo Targets:
	@echo   install              Sync dependencies with uv
	@echo   generate             Generate missing KB articles for both domains
	@echo   generate-networking  Generate missing networking articles only
	@echo   generate-meetings    Generate missing meetings articles only
	@echo   regenerate           Regenerate ALL articles - overwrites, calls the LLM 20 times
	@echo   verify               Load every article with LangChain loaders and run sanity checks
	@echo   clean                Remove Python caches
	@echo   clean-data           Delete generated articles under data/raw

install:
	$(UV) sync

generate:
	$(UV) run $(GEN) --domain all

generate-networking:
	$(UV) run $(GEN) --domain networking

generate-meetings:
	$(UV) run $(GEN) --domain meetings

regenerate:
	$(UV) run $(GEN) --domain all --force

verify:
	$(UV) run $(VERIFY_DEPS) python $(VERIFY)

clean:
	$(UV) run python -c "import pathlib, shutil; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__') if '.venv' not in p.parts]"

clean-data:
	$(UV) run python -c "import shutil; shutil.rmtree('data/raw', ignore_errors=True)"
