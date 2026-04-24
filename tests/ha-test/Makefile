# Failover test scaffolding for the tier F HA stack.
#
# All compose invocations below pass both the base HA compose file and the
# test override, and export HA_TEST_USERS_FILE (required by the override) as
# an absolute path to testdata/users.

HA_DIR       := ../../deploy/docker/ha
BASE         := $(HA_DIR)/ha-compose.yaml
OVERRIDE     := ha-compose.test.yaml
USERS_FILE   := $(abspath testdata/users)
PYTHON       ?= python3

export HA_TEST_USERS_FILE := $(USERS_FILE)

COMPOSE := docker compose -f $(BASE) -f $(OVERRIDE)

.PHONY: test fresh stress down status logs clean help

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Test run:"
	@echo "  test         Failover test at ~40% capacity (10 users) — clean signal"
	@echo "  stress       Failover test at saturation (50 users) — worst-case behavior"
	@echo "  fresh        Wipe volumes first, then run — use after a broken/aborted run"
	@echo ""
	@echo "Stack control (with the test override applied):"
	@echo "  down         Stop and remove containers + volumes"
	@echo "  status       Show container state"
	@echo "  logs         Follow logs for all services (SERVICE=x for one)"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean        Remove results/ and test_tokens.json"
	@echo ""
	@echo "Override PYTHON to use a specific interpreter, e.g.:"
	@echo "  make test PYTHON=../../.venv313/bin/python"

test:
	$(PYTHON) run_failover_test.py

stress:
	$(PYTHON) run_failover_test.py --users 50

fresh:
	$(PYTHON) run_failover_test.py --fresh

down:
	$(COMPOSE) down -v

status:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f $(SERVICE)

clean:
	rm -rf results/ test_tokens.json
