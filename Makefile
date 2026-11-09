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
VERSION     := 0.10.0
IMAGE       := localhost/netcore-rag-api:$(VERSION)
WEB_IMAGE   := localhost/netcore-rag-web:$(VERSION)
MCP_IMAGE   := localhost/netcore-rag-mcp:$(VERSION)
HUB_USER    ?= iomega
TF          := $(UV) run --no-sync --env-file .env -- terraform -chdir=iac
API_PORT    ?= 8080
WEB_PORT    ?= 80
MCP_PORT    ?= 9090
NPM         ?= npm
WEB_NPM     := $(NPM) --prefix web

.DEFAULT_GOAL := help
.PHONY: help tui engine install generate generate-networking generate-meetings regenerate verify clean clean-data \
        chroma-up chroma-down chroma-logs chroma-reset populate populate-networking populate-meetings db-stats \
        test-query query redis-up redis-down assign-access-levels agent-ask \
        db-up db-down db-migrate api-run api-test api-build api-up api-down api-logs stack-up stack-down \
        bootstrap up-all agent-api-test \
        web-install web-dev web-lint web-test web-build web-image web-up web-down web-logs \
        mcp-run mcp-test mcp-migrate mcp-build mcp-up mcp-down mcp-logs \
        publish iac-init iac-prepare iac-plan iac-up iac-output iac-ssh iac-down

# Every target carries its metadata in a "##" comment; `make help` and the terminal UI (`uv run tui.py`) read it.
#   ##@ Group name                      starts a group
#   target: deps  ## Description [tags] {params}
#   tags  : [danger] deletes/overwrites data   [cost] calls OpenAI or creates Jira issues   [long] runs until stopped
#   params: NAME! required text   NAME=default   NAME=default:a|b|c choice   NAME? flag (passed as NAME=1)

##@ Tools

help:  ## List the targets, generated from the ## comments in this Makefile
	@$(UV) run --no-sync python -m make_tui.help

tui:  ## Terminal UI for every target: search, parameter forms, live output, history [long]
	$(UV) run tui.py

engine:  ## Show the detected container engine (override with ENGINE=podman)
	@echo ENGINE=$(ENGINE) COMPOSE=$(COMPOSE)

##@ KB generation

install:  ## Sync dependencies with uv
	$(UV) sync

generate:  ## Generate missing KB articles for both domains [cost]
	$(UV) run $(GEN) --domain all

generate-networking:  ## Generate missing networking articles only [cost]
	$(UV) run $(GEN) --domain networking

generate-meetings:  ## Generate missing meetings articles only [cost]
	$(UV) run $(GEN) --domain meetings

regenerate:  ## Regenerate ALL 20 articles (overwrites; 20 LLM calls) [danger] [cost]
	$(UV) run $(GEN) --domain all --force

verify:  ## Load every article with LangChain loaders and run sanity checks
	$(UV) run python $(VERIFY)

clean:  ## Remove Python caches
	$(UV) run python -c "import pathlib, shutil; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__') if '.venv' not in p.parts]"

clean-data:  ## Delete the generated articles under data/raw [danger]
	$(UV) run python -c "import shutil; shutil.rmtree('data/raw', ignore_errors=True)"

##@ Vector DB

chroma-up:  ## Start the Chroma server (compose)
	$(COMPOSE) up -d $(UP_WAIT) chroma
	$(call healthy,netcore-chroma)

chroma-down:  ## Stop the Chroma server (data is kept)
	$(COMPOSE) stop chroma

chroma-logs:  ## Follow the Chroma server logs [long]
	$(COMPOSE) logs -f chroma

chroma-reset:  ## Stop the Chroma server and DELETE its volume (re-run populate afterwards) [danger]
	$(COMPOSE) stop chroma
	$(ENGINE) rm -f netcore-chroma
	$(ENGINE) volume rm -f $(PROJECT)_chroma-data

populate:  ## Read, chunk, describe, embed and store both domains [cost]
	$(UV) run $(POPULATE) --domain all

populate-networking:  ## Populate the networking database only [cost]
	$(UV) run $(POPULATE) --domain networking

populate-meetings:  ## Populate the meetings database only [cost]
	$(UV) run $(POPULATE) --domain meetings

db-stats:  ## Show chunk counts and sample metadata per database
	$(UV) run $(POPULATE) --stats

test-query:  ## DB info + similarity, keyword, filter, hybrid and cross-domain demos [cost]
	$(UV) run $(TESTQUERY)

query:  ## Ad-hoc query: similarity, BM25 and hybrid results [cost] {Q! D=all:all|networking|meetings}
ifndef Q
	$(error Usage: make query Q="your question" [D=networking|meetings|all])
endif
	$(UV) run $(TESTQUERY) --query "$(Q)" --domain $(D)

##@ Agentic RAG

redis-up:  ## Start the Redis Stack semantic cache (compose)
	$(COMPOSE) up -d $(UP_WAIT) redis
	$(call healthy,netcore-redis)

redis-down:  ## Stop Redis (data is kept)
	$(COMPOSE) stop redis

assign-access-levels:  ## Patch RBAC access_level metadata into Chroma (no re-embedding)
	$(UV) run $(ACCESS)

agent-ask:  ## Ask the agent as a demo user (alice=guest, bob=employee, carol=admin) [cost] {Q! U=bob:alice|bob|carol M=plan:plan|react}
ifndef Q
	$(error Usage: make agent-ask Q="your question" [U=alice|bob|carol])
endif
	$(UV) run python -m agentic_rag --question "$(Q)" --user $(U) --mode $(M)

##@ REST API

db-up:  ## Start Postgres (audit log, agent runs, tickets)
	$(COMPOSE) up -d $(UP_WAIT) postgres
	$(call healthy,netcore-postgres)

db-down:  ## Stop Postgres (data is kept)
	$(COMPOSE) stop postgres

db-migrate:  ## Apply the API's Alembic migrations (public schema)
	$(UV) run alembic -c api/alembic.ini upgrade head

api-run:  ## Run the API locally with auto-reload on http://localhost:8080/docs [long]
	$(UV) run uvicorn app.main:create_app --factory --app-dir api --reload --reload-dir api --reload-dir scripts --port $(API_PORT) --no-access-log

api-test:  ## Run all Python unit tests (API, agent, MCP, TUI parser) - no network needed
	$(UV) run pytest

agent-api-test:  ## Planning smoke test against the running API [cost] {U=bob:alice|bob|carol TRACE?}
	$(UV) run $(APITEST) --user $(U) $(if $(TRACE),--trace,)

api-build:  ## Build the API image
	$(ENGINE) build -f Containerfile $(BUILD_FLAGS) -t $(IMAGE) .

api-up: api-build  ## Build and start the API container with its dependencies
	$(COMPOSE) up -d $(UP_WAIT) api
	$(call healthy,netcore-api)

api-down:  ## Stop the API container
	$(COMPOSE) stop api

api-logs:  ## Follow the API container logs [long]
	$(COMPOSE) logs -f api

##@ Web UI

web-install:  ## npm ci in web/ (Node 22 LTS)
	$(WEB_NPM) ci --no-audit --no-fund

web-dev:  ## Vite dev server on http://localhost:5173 (proxies /api to :8080) [long]
	$(WEB_NPM) run dev

web-lint:  ## ESLint + Prettier check
	$(WEB_NPM) run lint
	$(WEB_NPM) run format:check

web-test:  ## Vitest unit and component tests (no API needed)
	$(WEB_NPM) test

web-build:  ## Production build into web/dist
	$(WEB_NPM) run build

web-image:  ## Build the web image (Nginx gateway + static build)
	$(ENGINE) build -f web/Containerfile $(BUILD_FLAGS) -t $(WEB_IMAGE) web

web-up: api-build web-image  ## Build and start the web container on http://localhost/ (starts the API if needed)
	$(COMPOSE) up -d $(UP_WAIT) web
	$(call healthy,netcore-web)

web-down:  ## Stop the web container
	$(COMPOSE) stop web

web-logs:  ## Follow the web (Nginx) container logs [long]
	$(COMPOSE) logs -f web

##@ IT ticket MCP server

mcp-run:  ## Run the MCP server locally on http://localhost:9090/mcp [long]
	$(UV) run python -m netcore_mcp

mcp-test:  ## MCP server tests (fakes only, no Postgres or Jira)
	$(UV) run pytest netcore_mcp/tests

mcp-migrate:  ## Apply the itsm schema migrations (own Alembic chain)
	$(UV) run alembic -c netcore_mcp/alembic.ini upgrade head

mcp-build:  ## Build the MCP server image
	$(ENGINE) build -f netcore_mcp/Containerfile $(BUILD_FLAGS) -t $(MCP_IMAGE) .

mcp-up: mcp-build  ## Build and start the MCP container (starts Postgres if needed)
	$(COMPOSE) up -d $(UP_WAIT) mcp
	$(call healthy,netcore-mcp)

mcp-down:  ## Stop the MCP container
	$(COMPOSE) stop mcp

mcp-logs:  ## Follow the MCP container logs [long]
	$(COMPOSE) logs -f mcp

##@ Whole stack

stack-up: mcp-build api-build web-image  ## Build images and start every container (data already in place)
	$(COMPOSE) up -d $(UP_WAIT)
	$(call healthy,netcore-mcp)
	$(call healthy,netcore-api)
	$(call healthy,netcore-web)

stack-down:  ## Stop and remove every container (volumes are kept)
	$(COMPOSE) down

bootstrap: chroma-up redis-up db-up populate assign-access-levels db-migrate mcp-migrate  ## First run: infrastructure + populate + access levels + both migrations [cost]
	@echo Ready. Next: make api-run - or make api-up

# Whole stack in dependency order. Prerequisites run left to right: infrastructure first (each waits until healthy),
# then the images. The recipe then fills Chroma only when a domain is empty (REPOPULATE=1 forces it; populate costs
# OpenAI calls), patches RBAC access levels, applies both migration chains (api: public, mcp: itsm) and starts
# mcp -> api -> web (each waits until healthy; the api needs the MCP server for its ticket tools).
up-all: chroma-up redis-up db-up mcp-build api-build web-image  ## Everything in one go: infra, populate if empty, access levels, migrations, mcp, api, web [cost] {REPOPULATE?}
	$(UV) run $(POPULATE) --domain all $(if $(filter 1,$(REPOPULATE)),,--if-empty)
	$(UV) run $(ACCESS)
	$(UV) run alembic -c api/alembic.ini upgrade head
	$(UV) run alembic -c netcore_mcp/alembic.ini upgrade head
	$(COMPOSE) up -d $(UP_WAIT) mcp api web
	$(call healthy,netcore-mcp)
	$(call healthy,netcore-api)
	$(call healthy,netcore-web)
	@echo Ready: web http://localhost:$(WEB_PORT)/ - API http://localhost:$(API_PORT)/docs - MCP http://localhost:$(MCP_PORT)/mcp

##@ Deploy (Docker Hub + AWS)

publish: mcp-build api-build web-image  ## Push the api, mcp and web images to Docker Hub as iomega/netcore-rag-*:<VERSION> and :latest [cost]
	$(UV) run --no-sync --env-file .env scripts/publish_images.py --version $(VERSION) --user $(HUB_USER) --engine $(ENGINE)

iac-init:  ## terraform init in iac/ (providers; state stays local in iac/)
	$(TF) init

iac-prepare:  ## Write iac/.build: app.env without AWS_/DOCKERHUB_ secrets + Chroma volume snapshot {CHROMA_REFRESH?}
	$(UV) run --no-sync python iac/prepare.py --engine $(ENGINE) $(if $(filter 1,$(CHROMA_REFRESH)),--refresh-chroma,)

iac-plan: iac-prepare  ## Show what terraform would create or change on AWS
	$(TF) plan -var app_version=$(VERSION) -var hub_user=$(HUB_USER)

iac-up: iac-prepare  ## Create or update the EC2 instance (t3.small, Docker CE) and deploy every container [cost]
	$(TF) apply -auto-approve -var app_version=$(VERSION) -var hub_user=$(HUB_USER)
	$(TF) output

iac-output:  ## Show the deployment outputs: IP, web URL, ssh and tunnel commands
	$(TF) output

iac-ssh:  ## SSH into the instance (interactive in a terminal), or run CMD there, e.g. CMD="docker ps" {CMD=}
	$(UV) run --no-sync python iac/ssh.py

iac-down:  ## Destroy the EC2 instance, EIP, key pair and security group (all remote data is lost) [danger]
	$(TF) destroy -auto-approve -var app_version=$(VERSION) -var hub_user=$(HUB_USER)
