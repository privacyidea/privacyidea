COMPOSE := docker compose -f ha-compose.yaml

.PHONY: start stop restart logs status build backup restore scale help

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Stack management:"
	@echo "  start          Start the full stack in the background"
	@echo "  stop           Stop and remove containers (data volumes are preserved)"
	@echo "  restart        Restart all services"
	@echo "  build          Rebuild the privacyIDEA image"
	@echo "  status         Show running containers and health"
	@echo "  logs           Follow logs for all services (Ctrl+C to stop)"
	@echo "  logs SERVICE=x Follow logs for a specific service (e.g. make logs SERVICE=pi)"
	@echo "  scale N=3      Scale privacyIDEA workers to N replicas (default: 2)"
	@echo ""
	@echo "Backup / restore:"
	@echo "  backup         Create an encrypted or plain backup (see scripts/backup.sh --help)"
	@echo "  restore        Restore a backup: make restore BACKUP=backups/privacyidea_....tar.gz"
	@echo ""
	@echo "Monitoring:"
	@echo "  stats          Open the HAProxy stats page in the default browser"

start:
	$(COMPOSE) up -d

stop:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart

build:
	$(COMPOSE) build

status:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f $(SERVICE)

scale:
	@if [ -z "$(N)" ]; then echo "Usage: make scale N=<number>"; exit 1; fi
	$(COMPOSE) up -d --scale pi=$(N)

backup:
	./scripts/backup.sh

restore:
	@if [ -z "$(BACKUP)" ]; then echo "Usage: make restore BACKUP=<path-to-archive>"; exit 1; fi
	./scripts/restore.sh "$(BACKUP)"

stats:
	xdg-open http://localhost:8404/stats 2>/dev/null || open http://localhost:8404/stats 2>/dev/null || echo "Open http://localhost:8404/stats in your browser"
