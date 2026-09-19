SHELL := /bin/bash
PYTHON ?= python3.12
VENV_PY := .venv/bin/python scripts/project_python.py
COMPOSE := docker compose --project-directory . -f infra/compose.yaml

.PHONY: help bootstrap install-hooks test test-core test-golden lint typecheck check lock-python infra-config infra-up infra-down infra-status migration-history migration-sql migrate test-db-start test-db-status test-db-stop test-redis-start test-redis-status test-redis-stop

help:
	@echo "bootstrap | check | test | test-core | test-golden | lint | typecheck"
	@echo "infra-config | infra-up | infra-down | infra-status | migration-history | migration-sql | migrate"

bootstrap:
	PYTHON="$(PYTHON)" bash scripts/bootstrap

install-hooks:
	$(VENV_PY) scripts/install_hooks.py

test:
	$(VENV_PY) scripts/run_tests.py tests

test-core:
	$(VENV_PY) scripts/run_tests.py tests/core

test-golden:
	$(VENV_PY) scripts/run_tests.py tests/golden

lint:
	.venv/bin/ruff check .
	.venv/bin/ruff format --check .
	$(VENV_PY) scripts/check_policy.py
	$(VENV_PY) scripts/generate_concepts.py --check
	npm run lint

typecheck:
	$(VENV_PY) -m mypy
	npm run typecheck

check: lint typecheck test test-core test-golden

lock-python:
	CUSTOM_COMPILE_COMMAND="make lock-python" $(VENV_PY) -m piptools compile --extra dev --allow-unsafe --strip-extras --output-file requirements-dev.lock pyproject.toml

infra-config:
	$(COMPOSE) config --quiet

infra-up:
	$(COMPOSE) up -d --wait

infra-down:
	$(COMPOSE) down

infra-status:
	$(COMPOSE) ps

migration-history:
	$(VENV_PY) -m alembic history

migration-sql:
	$(VENV_PY) -m alembic upgrade head --sql

migrate:
	$(VENV_PY) -m alembic upgrade head

# Separate disposable PG16 runtime; never uses the application DATABASE_URL.
test-db-start:
	$(VENV_PY) scripts/test_postgres.py start

test-db-status:
	$(VENV_PY) scripts/test_postgres.py status

test-db-stop:
	$(VENV_PY) scripts/test_postgres.py stop

# Only the repository-owned test rate coordinator; never application Redis.
test-redis-start:
	$(VENV_PY) scripts/test_redis.py start

test-redis-status:
	$(VENV_PY) scripts/test_redis.py status

test-redis-stop:
	$(VENV_PY) scripts/test_redis.py stop

.PHONY: test-db-setup-timescale
test-db-setup-timescale:
	$(VENV_PY) scripts/setup_test_timescale.py
