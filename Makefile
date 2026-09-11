SHELL := /bin/bash
PYTHON ?= python3.12
VENV_PY := .venv/bin/python
COMPOSE := docker compose --project-directory . -f infra/compose.yaml

.PHONY: help bootstrap install-hooks test test-core test-golden lint typecheck check lock-python infra-config infra-up infra-down infra-status migration-history migration-sql migrate

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
	npm run lint

typecheck:
	.venv/bin/mypy
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
	.venv/bin/alembic history

migration-sql:
	.venv/bin/alembic upgrade head --sql

migrate:
	.venv/bin/alembic upgrade head
