.PHONY: build check test-unit test-e2e dev dev-docker dev-docker-simulation dev-infra dev-simulation stop

COMPOSE_DEV = docker compose -f docker-compose.yml -f docker-compose.dev.yml

build:
	docker compose build

# Everything CI runs; run it before calling a release candidate done.
check:
	uv run ruff check app/ scripts/ tests/
	uv run mypy app/
	$(MAKE) test-unit
	cd frontend && npm run typecheck && npm run lint
	$(MAKE) test-e2e
	cd frontend && BETTER_AUTH_SECRET=Qq7vF4mN9xL2sK8wC5rT1yH6uJ3pD0bG7zA4eS9nM2cV8fR1 BETTER_AUTH_URL=http://localhost:3000 DATABASE_URL=postgresql://igniteinsights:igniteinsights@127.0.0.1:5433/igniteinsights npm run build

test-unit:
	uv run pytest -q

# Starts only the database; Playwright owns the stub API and Next.js lifecycles.
test-e2e:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --wait db-e2e
	@sleep 2 # Docker Desktop can report container health before publishing the host port.
	DATABASE_URL=postgresql+asyncpg://igniteinsights:igniteinsights@127.0.0.1:5433/igniteinsights uv run alembic upgrade head
	cd frontend && DATABASE_URL=postgresql://igniteinsights:igniteinsights@127.0.0.1:5433/igniteinsights npm run test:e2e

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
