# Makefile - NetCore Systems KB generator (Enterprise RAG demo)
# Requires: GNU make, uv, and Docker or Podman (+ podman-compose). Works from cmd, PowerShell or Git Bash.

UV          ?= uv
GEN         := scripts/generate_kb.py
VERIFY      := scripts/verify_kb.py
POPULATE    := scripts/populate_vector_dbs.py
TESTQUERY   := scripts/test_query_vector_dbs.py
ACCESS      := scripts/assign_access_levels.py
APITEST     := scripts/test_agent_api.py
D           ?= all
U           ?= bob
M           ?= plan
export PYTHONPATH := scripts   # makes `python -m agentic_rag` (scripts/agentic_rag) importable

# Container engine: docker if installed, else podman. Override: make <target> ENGINE=podman
ifndef ENGINE
ENGINE := $(shell $(UV) run --no-sync python -c "import shutil; print('docker' if shutil.which('docker') else 'podman' if shutil.which('podman') else 'docker')")
endif
ifeq ($(ENGINE),podman)
COMPOSE     ?= podman-compose
UP_WAIT     :=
healthy      = podman wait --condition=healthy $(1)
BUILD_FLAGS := --format docker
else
COMPOSE     ?= docker compose
UP_WAIT     := --wait
healthy      =
BUILD_FLAGS :=
endif
PROJECT     := netcore-rag
IMAGE       := localhost/netcore-rag-api:0.7.0
API_PORT    ?= 8080

.DEFAULT_GOAL := help
.PHONY: help install generate generate-networking generate-meetings regenerate verify clean clean-data \
        chroma-up chroma-down chroma-logs chroma-reset populate populate-networking populate-meetings db-stats \
        test-query query redis-up redis-down assign-access-levels agent-ask         db-up db-down db-migrate api-run api-test api-build api-up api-down api-logs stack-up stack-down         bootstrap engine agent-api-test

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
	@echo   chroma-reset         Stop the server and DELETE its volume - re-run make populate afterwards
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
	@echo REST API:
	@echo   db-up / db-down      Start / stop Postgres - audit log and agent runs
	@echo   db-migrate           Apply Alembic migrations
	@echo   api-run              Run the API locally with auto-reload - http://localhost:$(API_PORT)/docs
	@echo   api-test             Run the API unit tests - no network or containers needed
	@echo   agent-api-test       Planning smoke test against the running API: U=bob, TRACE=1 for traces
	@echo   api-build            Build the API image from the Containerfile
	@echo   api-up / api-down    Start / stop the API container with its dependencies
	@echo   api-logs             Follow the API container logs
	@echo   stack-up/stack-down  Start / stop everything: chroma, redis, postgres, api
	@echo   bootstrap            First run: start chroma, redis, postgres + populate + access levels + migrate
	@echo   engine               Show the detected container engine - override with ENGINE=podman

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
	$(COMPOSE) up -d $(UP_WAIT) chroma
	$(call healthy,netcore-chroma)

chroma-down:
	$(COMPOSE) stop chroma

chroma-logs:
	$(COMPOSE) logs -f chroma

chroma-reset:
	$(COMPOSE) stop chroma
	$(ENGINE) rm -f netcore-chroma
	$(ENGINE) volume rm -f $(PROJECT)_chroma-data

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
	$(COMPOSE) up -d $(UP_WAIT) redis
	$(call healthy,netcore-redis)

redis-down:
	$(COMPOSE) stop redis

assign-access-levels:
	$(UV) run $(ACCESS)

agent-ask:
ifndef Q
	$(error Usage: make agent-ask Q="your question" [U=alice|bob|carol])
endif
	$(UV) run python -m agentic_rag --question "$(Q)" --user $(U) --mode $(M)

# ---------------------------- REST API ----------------------------

engine:
	@echo ENGINE=$(ENGINE) COMPOSE=$(COMPOSE)

db-up:
	$(COMPOSE) up -d $(UP_WAIT) postgres
	$(call healthy,netcore-postgres)

db-down:
	$(COMPOSE) stop postgres

db-migrate:
	$(UV) run alembic -c api/alembic.ini upgrade head

api-run:
	$(UV) run uvicorn app.main:create_app --factory --app-dir api --reload --reload-dir api --reload-dir scripts --port $(API_PORT) --no-access-log

api-test:
	$(UV) run pytest

agent-api-test:
	$(UV) run $(APITEST) --user $(U) $(if $(TRACE),--trace,)

api-build:
	$(ENGINE) build -f Containerfile $(BUILD_FLAGS) -t $(IMAGE) .

api-up: api-build
	$(COMPOSE) up -d $(UP_WAIT) api
	$(call healthy,netcore-api)

api-down:
	$(COMPOSE) stop api

api-logs:
	$(COMPOSE) logs -f api

stack-up: api-build
	$(COMPOSE) up -d $(UP_WAIT)
	$(call healthy,netcore-api)

stack-down:
	$(COMPOSE) down

bootstrap: chroma-up redis-up db-up populate assign-access-levels db-migrate
	@echo Ready. Next: make api-run - or make api-up
