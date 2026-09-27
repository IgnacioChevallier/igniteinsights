.PHONY: build check dev dev-docker dev-docker-simulation dev-infra dev-simulation stop

COMPOSE_DEV = docker compose -f docker-compose.yml -f docker-compose.dev.yml

build:
	docker compose build

# Everything CI runs. ~30s; run it before calling a change done.
check:
	uv run ruff check app/ scripts/ tests/
	uv run mypy app/
	uv run pytest -q
	cd frontend && npx tsc --noEmit && npx eslint .

# Fastest macOS workflow: Docker for the API/database, host Node for Next.js.
dev:
	$(COMPOSE_DEV) stop frontend
	$(COMPOSE_DEV) up -d db api
	npm --prefix frontend run dev

dev-infra:
	$(COMPOSE_DEV) up -d db api

dev-simulation:
	$(COMPOSE_DEV) up -d db api elmfire-runner

# Fully containerized hot reload. ELMFIRE remains opt-in.
dev-docker:
	$(COMPOSE_DEV) up db api frontend

dev-docker-simulation:
	$(COMPOSE_DEV) up db api frontend elmfire-runner

stop:
	docker compose down
