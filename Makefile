# Makefile - NetCore Systems KB generator (Enterprise RAG demo)
# Requires: GNU make, uv. Works from cmd, PowerShell or Git Bash.

UV          ?= uv
GEN         := scripts/generate_kb.py
VERIFY      := scripts/verify_kb.py
POPULATE    := scripts/populate_vector_dbs.py
TESTQUERY   := scripts/test_query_vector_dbs.py
ACCESS      := scripts/assign_access_levels.py
D           ?= all
U           ?= bob
M           ?= plan
COMPOSE     ?= docker compose
export PYTHONPATH := scripts   # makes `python -m agentic_rag` (scripts/agentic_rag) importable

.DEFAULT_GOAL := help
.PHONY: help install generate generate-networking generate-meetings regenerate verify clean clean-data \
        chroma-up chroma-down chroma-logs chroma-reset populate populate-networking populate-meetings db-stats \
        test-query query redis-up redis-down assign-access-levels agent-ask

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
	@echo Vector DB:
	@echo   chroma-up            Start the Chroma server - docker compose
	@echo   chroma-down          Stop the Chroma server - data is kept
	@echo   chroma-logs          Follow the Chroma server logs
	@echo   chroma-reset         Stop the server and DELETE ./chroma-data
	@echo   populate             Read, chunk, describe, embed and store both domains
	@echo   populate-networking  Populate the networking database only
	@echo   populate-meetings    Populate the meetings database only
	@echo   db-stats             Show chunk counts and sample metadata per database
	@echo   test-query           DB info + similarity, keyword, filter, hybrid, cross-domain demos
	@echo   query Q=... D=...    Ad-hoc query, D = networking, meetings or all - default all
	@echo Agentic RAG:
	@echo   redis-up             Start the Redis Stack semantic cache - docker compose
	@echo   redis-down           Stop Redis - data is kept
	@echo   assign-access-levels Patch RBAC access_level metadata into Chroma - no re-embedding
	@echo   agent-ask Q=... U=.. Ask the agent as a demo user: alice=guest, bob=employee, carol=admin
	@echo                        M=plan - Plan-and-Execute, default - or M=react - agent routes with tools

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
	$(UV) run python $(VERIFY)

clean:
	$(UV) run python -c "import pathlib, shutil; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__') if '.venv' not in p.parts]"

clean-data:
	$(UV) run python -c "import shutil; shutil.rmtree('data/raw', ignore_errors=True)"

# ---------------------------- Vector DB ----------------------------

chroma-up:
	$(COMPOSE) up -d --wait chroma

chroma-down:
	$(COMPOSE) stop chroma

chroma-logs:
	$(COMPOSE) logs -f chroma

chroma-reset:
	$(COMPOSE) rm -s -f chroma
	$(UV) run python -c "import shutil; shutil.rmtree('chroma-data', ignore_errors=True)"

populate:
	$(UV) run $(POPULATE) --domain all

populate-networking:
	$(UV) run $(POPULATE) --domain networking

populate-meetings:
	$(UV) run $(POPULATE) --domain meetings

db-stats:
	$(UV) run $(POPULATE) --stats

test-query:
	$(UV) run $(TESTQUERY)

query:
ifndef Q
	$(error Usage: make query Q="your question" [D=networking|meetings|all])
endif
	$(UV) run $(TESTQUERY) --query "$(Q)" --domain $(D)

# ---------------------------- Agentic RAG ----------------------------

redis-up:
	$(COMPOSE) up -d --wait redis

redis-down:
	$(COMPOSE) stop redis

assign-access-levels:
	$(UV) run $(ACCESS)

agent-ask:
ifndef Q
	$(error Usage: make agent-ask Q="your question" [U=alice|bob|carol])
endif
	$(UV) run python -m agentic_rag --question "$(Q)" --user $(U) --mode $(M)
