# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: CC0-1.0
# privacyIDEA single-node Docker stack — common operations.
# Run from the deployment directory.  "make help" lists the available targets.

# No "-f": compose then reads the compose files from COMPOSE_FILE in .env, or
# compose.yaml and an optional compose.override.yaml when that is unset.
COMPOSE := docker compose

.DEFAULT_GOAL := help

.PHONY: help init up down restart ps logs smoke backup restore upgrade build pimanage

help:  ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-9s\033[0m %s\n", $$1, $$2}'

init:  ## Generate secrets and create the config files from their templates (idempotent)
	@./scripts/init-secrets.sh
	@for file in .env privacyidea.env caddy.env mariadb.cnf; do \
	  [ -f "$$file" ] || { cp "$$file.template" "$$file" && chmod 644 "$$file" && \
	    echo "[init] created $$file from $$file.template — review it"; }; \
	done

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

# Pulls before the backup, so a failed pull changes nothing and the backup is
# taken right before the switch.
upgrade:  ## Pull the configured images, back up, and restart on them (safe upgrade)
	@$(COMPOSE) pull || { \
	  echo "[upgrade] Pulling failed, nothing was changed. An image built with 'make build'" >&2; \
	  echo "          is not pulled: update it with 'make build' and 'make up' instead." >&2; \
	  exit 1; }
	./scripts/backup.sh
	$(COMPOSE) up -d

build:  ## Build the image from the source tree as PI_IMAGE (development; see compose.build.yaml)
	$(COMPOSE) -f compose.yaml -f compose.build.yaml build

pimanage:  ## Run a one-off pi-manage command (ARGS="admin list"); needs db running
	@[ -n "$(ARGS)" ] || { echo 'usage: make pimanage ARGS="admin list"'; exit 1; }
	$(COMPOSE) run --rm --no-deps pi pi-manage $(ARGS)
