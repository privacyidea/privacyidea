# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: CC0-1.0
# privacyIDEA single-node Docker stack — common operations.
# Run from deploy/docker/.  "make help" lists the available targets.

COMPOSE := docker compose -f compose.yaml

.DEFAULT_GOAL := help

.PHONY: help init up down restart ps logs smoke backup restore upgrade build pimanage

help:  ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-9s\033[0m %s\n", $$1, $$2}'

init:  ## Generate secrets and create .env (idempotent)
	@./scripts/init-secrets.sh
	@[ -f .env ] || { cp .env.template .env && echo "[init] created .env from .env.template — review it"; }

up:  ## Start the stack
	$(COMPOSE) up -d

down:  ## Stop and remove containers (keeps the db volume)
	$(COMPOSE) down

restart:  ## Restart the app services
	$(COMPOSE) restart pi pi-cron

ps:  ## Show service status
	$(COMPOSE) ps

logs:  ## Follow logs from all services
	$(COMPOSE) logs -f

smoke:  ## Run the smoke test against the running stack
	./scripts/smoke-test.sh

backup:  ## Back up database + secrets (ARGS="--encrypt" to encrypt)
	./scripts/backup.sh $(ARGS)

restore:  ## Restore from a backup (FILE=backups/<archive>)
	@[ -n "$(FILE)" ] || { echo "usage: make restore FILE=backups/<archive>"; exit 1; }
	./scripts/restore.sh $(FILE)

upgrade:  ## Back up, pull the new image, and restart (safe upgrade)
	./scripts/backup.sh
	$(COMPOSE) pull
	$(COMPOSE) up -d

build:  ## Build the image locally (development; not needed when pulling)
	$(COMPOSE) build

pimanage:  ## Run a one-off pi-manage command (ARGS="admin list"); needs db running
	@[ -n "$(ARGS)" ] || { echo 'usage: make pimanage ARGS="admin list"'; exit 1; }
	$(COMPOSE) run --rm --no-deps pi pi-manage $(ARGS)
