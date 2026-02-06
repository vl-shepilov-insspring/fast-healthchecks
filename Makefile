.PHONY: help bash install-hooks update-uv lint test

# colors
GREEN = $(shell tput -Txterm setaf 2)
YELLOW = $(shell tput -Txterm setaf 3)
WHITE = $(shell tput -Txterm setaf 7)
RESET = $(shell tput -Txterm sgr0)
GRAY = $(shell tput -Txterm setaf 6)
TARGET_MAX_CHAR_NUM = 20

# Help

## Shows help.
help:
	@echo 'DEBUG_MODE: ${DEBUG_MODE}'
	@echo ''
	@echo 'Usage:'
	@echo ''
	@echo '  ${YELLOW}make${RESET} ${GREEN}<target>${RESET}'
	@echo ''
	@echo 'Targets:'
	@awk '/^[a-zA-Z\-\_]+:/ { \
		helpMessage = match(lastLine, /^## (.*)/); \
		if (helpMessage) { \
			if (index(lastLine, "|") != 0) { \
				stage = substr(lastLine, index(lastLine, "|") + 1); \
				printf "\n ${GRAY}%s: \n\n", stage;  \
			} \
			helpCommand = substr($$1, 0, index($$1, ":")-1); \
			helpMessage = substr(lastLine, RSTART + 3, RLENGTH); \
			if (index(lastLine, "|") != 0) { \
				helpMessage = substr(helpMessage, 0, index(helpMessage, "|")-1); \
			} \
			printf "  ${YELLOW}%-$(TARGET_MAX_CHAR_NUM)s${RESET} ${GREEN}%s${RESET}\n", helpCommand, helpMessage; \
		} \
	} \
	{ lastLine = $$0 }' $(MAKEFILE_LIST)
	@echo ''

.DEFAULT_GOAL := help

# Common

## Run bash environment | Common
bash:
	@source .venv/bin/activate

# Development

## Install pre-commit hooks. | Development
install-hooks:
	pre-commit install --hook-type pre-commit
	pre-commit install --install-hooks

## Update uv dependencies
update-uv:
	@uv sync --all-extras --upgrade

## Run linters
lint:
	@uv run pre-commit run --all-files

## Run imports tests
tests-imports:
	@uv sync --group=dev
	@uv run pytest -p no:xdist --cov --cov-append -m 'imports' tests/unit/test_imports.py

## Run integration tests (if DOCKER_SERVICES_UP=1, skip compose up/down)
tests-integration:
ifneq ($(DOCKER_SERVICES_UP),1)
	@docker compose up -d --wait
endif
	@uv sync --group=dev --all-extras
	@uv run pytest -n auto --cov --cov-append -m 'integration'
ifneq ($(DOCKER_SERVICES_UP),1)
	@echo "Stopping services..."
	@docker compose down --remove-orphans --volumes
endif

## Run unit tests
tests-unit:
	@uv run pytest -n auto --cov --cov-append -m 'unit'

## Run all tests
tests-all:
	@rm -rf .coverage
	@make tests-imports
	@make tests-integration
	@make tests-unit
	@uv run coverage report

## Serve documentation locally
serve-docs:
	@uv run mkdocs serve

## Run SonarQube analysis (requires sonar-scanner)
sonar:
	@./scripts/sonar.sh
