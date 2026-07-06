# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is this project

privacyIDEA is an open-source MFA platform (AGPLv3). It has a Flask/Python backend and an Angular frontend (`privacyidea/static_new/`). The two run independently during development.

---

## Backend (Python/Flask)

### Commands

```bash
# Run all tests (always unset PRIVACYIDEA_CONFIGFILE — see critical note below)
env -u PRIVACYIDEA_CONFIGFILE python -m pytest -v -n auto --dist=loadfile -m "not migration" tests/

# Single test file
env -u PRIVACYIDEA_CONFIGFILE python -m pytest -v tests/test_api_token.py

# Single test
env -u PRIVACYIDEA_CONFIGFILE python -m pytest -v tests/test_api_token.py::TestTokenApi::test_enable

# Migration tests (require a running DB)
TEST_DATABASE_URL="mysql+pymysql://privacyidea:privacyidea@127.0.0.1:3306/privacyidea_test" \
  env -u PRIVACYIDEA_CONFIGFILE python -m pytest -m migration tests/test_migrations.py tests/test_migration_*.py -v

# Lint
ruff check privacyidea/

# Start dev containers (MariaDB/Postgres/Oracle for migration tests)
docker compose -f docker-compose.dev.yml up -d
```

### CRITICAL: `PRIVACYIDEA_CONFIGFILE` env hazard

If `PRIVACYIDEA_CONFIGFILE` is exported in your shell, `create_app()` (in `privacyidea/app.py`) **silently honors it over** the `config_file` argument and the named config object — so even `create_app('testing')` loads your real config, whose `SQLALCHEMY_DATABASE_URI` points at the live dev DB (`data.sqlite`). **Always prefix pytest and any Python script with `env -u PRIVACYIDEA_CONFIGFILE`.**

### Architecture

```
privacyidea/
  api/           # Flask blueprints — one per resource (token, user, container, policy…)
  api/before_after.py  # Central before/after request hooks: JWT verify, policy load, audit
  lib/           # All business logic — called by API layer, never by templates
  lib/tokens/    # One file per token type (hotp, totp, push, passkey, certificate…)
  lib/policy.py  # Policy evaluation engine
  models/        # SQLAlchemy ORM models
  migrations/    # Alembic migration scripts (Flask-Migrate)
  cli/           # pi-manage CLI entry points
```

**Request flow**: Blueprint endpoint → `before_after.py` (auth, policy object, audit setup) → `lib/` functions → ORM models. The `g` object carries `policy_object`, `audit_object`, and `logged_in_user` throughout a request.

**Token architecture**: Every token type inherits from `TokenClass` (`lib/tokenclass.py`). `lib/token.py` contains the top-level functions (`check_user_pass`, `assign_token`, etc.) that delegate to the appropriate token class.

### Testing conventions

- Tests use `unittest.TestCase` via `MyTestCase` from `tests/base.py`, which sets up a SQLite in-memory database via `TestingConfig`.
- `pytest-xdist` runs tests in parallel; per-worker DB isolation is handled in `tests/conftest.py`.
- Migration tests are marked `@pytest.mark.migration` and require `TEST_DATABASE_URL`. They have their own skeleton — see `tests/README.md`.
- `PristineSqliteFixtures` mixin (in `tests/base.py`) must be used for tests that mutate fixture SQLite files; list files in `pristine_fixtures`.

---

## Frontend (Angular)

All frontend commands run from `privacyidea/static_new/`.

### Commands

```bash
cd privacyidea/static_new

npm install               # install dependencies (after checkout / package-lock changes)
npm start                 # dev server on :4200, proxies API calls to target in proxy.conf.json
npm test                  # Jest unit tests
npm run test:coverage     # Jest with lcov coverage output → coverage/
npm test -- --testPathPattern=token-details  # single spec file
npm run lint              # ESLint (non-blocking in CI — ~2000-error backlog; don't add to it)
npm run format:write      # Prettier
npm run build             # production build → dist/
```

To change which privacyIDEA server the dev build proxies to, edit `src/proxy.conf.json`.

### Architecture

```
src/app/
  app.config.ts       # Root providers: zoneless CD, router, HTTP interceptors, app initializers
  app.routes.ts       # Route tree: /login + authenticated shell (LayoutComponent)
  admin.routes.ts     # Lazy-loaded admin route subtree
  self-service.routes.ts  # Lazy-loaded self-service subtree
  components/         # Feature UI components
  services/           # Injectable services (one per API resource + cross-cutting concerns)
  models/             # TypeScript interfaces / types
  constants/          # Shared constants
  guards/             # AuthGuard + canMatch fns for admin vs self-service split
  interceptor/        # HTTP interceptors (loading indicator, user-agent header)
  utils/              # Pure utility functions
  core/               # App-wide constants and models
```

**Service scope**: All feature services (TokenService, PolicyService, ContainerService, etc.) are provided on the authenticated route (the `LayoutComponent` route in `app.routes.ts`), not globally. This means they require an `EnvironmentInjector` captured at route scope — pass it explicitly when opening dialogs from outside the route hierarchy.

**Path aliases** (defined in `tsconfig.json`, also mapped in `jest.config.ts`):

| Alias | Path |
|---|---|
| `@services/*` | `src/app/services/*` |
| `@components/*` | `src/app/components/*` |
| `@models/*` | `src/app/models/*` |
| `@utils/*` | `src/app/utils/*` |
| `@constants/*` | `src/app/constants/*` |
| `@core/*` | `src/app/core/*` |
| `@testing/*` | `src/testing/*` |
| `@styles/*` | `src/styles/*` |
| `@env/*` | `src/environments/*` |
| `@app/*` | `src/app/*` |

### Forms

The codebase is migrating from `FormsModule`/`ReactiveFormsModule` to **Angular Signal Forms** (`@angular/forms/signals`). New form work should use Signal Forms. Key rules:

- `validate(f, (ctx) => ...)` — the callback receives a **context object**; use `ctx.value()`, not the raw value.
- `maxlength` and `required` HTML attributes are **not allowed** on `[formField]` nodes (NG8022). Use `required(f)` and length checks in the `validate()` callback.
- `mat-select`, `mat-checkbox`, `mat-datepicker` don't support `[formField]` — use `[value]` + `(selectionChange)`/`(dateChange)`/`(change)` and track dirty state manually with `isDirty = signal<boolean>(false)`.
- In tests: replace `xControl.setValue("v")` with `x.set("v")`; check validity via `xForm().valid()` / `.errors()`; validate errors by `kind` property, not `.hasError()`.

### CI notes

- **`codecov/patch/frontend`** is the check that usually blocks PRs — not Jest. Target is ~81.6% patch coverage. Compute locally: `npm run test:coverage`, then cross-reference `coverage/lcov.info` against `git diff origin/master..HEAD`.
- ESLint CI runs with `continue-on-error: true` — failures are reported but never block.
- **Do not commit** `proxy.conf.json`, `angular.json`, or `package-lock.json` changes that are local-only dev configuration (proxy target, removed lint target).
