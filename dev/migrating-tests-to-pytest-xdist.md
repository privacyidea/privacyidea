# Migrating Tests to pytest-xdist

This document describes the ongoing effort to run the privacyIDEA test
suite in parallel using [`pytest-xdist`](https://pytest-xdist.readthedocs.io/).
It covers only the *light plan* — parallelize the existing suite as-is,
without restructuring the ~136 files or rewriting any `unittest`-style
`TestCase` classes.

## Starting point

- 136 test files, ~2,441 tests, all inheriting from
  `MyTestCase` / `MyApiTestCase` in `tests/base.py`.
- CI ran `pytest -v tests/` serially on both MariaDB and PostgreSQL
  across the full Python matrix. Wall time: 16-20 minutes per backend /
  interpreter combination.
- Only one pytest fixture existed (`setup_local_ca` in
  `tests/conftest.py`); everything else used unittest `setUp` /
  `tearDown` inheritance.
- 503 tests encode their ordering in `test_NN_` method-name prefixes —
  the class-level state built up by earlier tests is what later tests
  rely on. This is incompatible with `pytest-randomly` but does not by
  itself prevent parallel execution at the *file* granularity.

## The light plan

Run the existing suite under `pytest-xdist` with **zero test changes**
by distributing at the file level. One worker gets a whole file, runs
it in source order, so the `test_NN_` ordering contract holds. Each
worker gets its own database so `setUpClass` / `tearDownClass` cycles
(`db.create_all` / `db.drop_all`) do not collide.

Measured gain: ~2× CI wall time. No refactor, no fixture migration,
no order-dependence fixes. Nothing shipped here blocks a more
ambitious full migration later (fixture library, test-level order
independence) — the per-worker shim is exactly what that work would
need anyway.

### Step L1 — Per-worker DB namespacing

A shim at the top of `tests/conftest.py` (before any `privacyidea`
import, because `TestingConfig.SQLALCHEMY_DATABASE_URI` is a class
attribute evaluated at import time) rewrites `TEST_DATABASE_URL` per
xdist worker:

```python
import os

_worker = os.environ.get("PYTEST_XDIST_WORKER")
if _worker:
    _base = os.environ.get("TEST_DATABASE_URL", "")
    if not _base:
        os.environ["TEST_DATABASE_URL"] = f"sqlite:////tmp/pi-test-{_worker}.sqlite"
    elif _base.startswith("sqlite"):
        os.environ["TEST_DATABASE_URL"] = _base.replace(".sqlite", f"-{_worker}.sqlite")
    else:  # mysql / postgres — suffix the DB name
        os.environ["TEST_DATABASE_URL"] = f"{_base}_{_worker}"
```

Serial runs (no `PYTEST_XDIST_WORKER` set) keep working unchanged.
`pytest-xdist` is pinned in `tests/requirements.txt`.

### Step L2 — Pre-create per-worker databases in CI

`db.create_all()` creates tables inside a database that already exists.
It does **not** create the database itself. Every backend except sqlite
therefore needs the worker databases pre-created.

**sqlite (local dev):** nothing to do — sqlite creates
`pi-test-gw0.sqlite`, `pi-test-gw1.sqlite`, … on first connect.

**MariaDB and PostgreSQL (CI):** a workflow step before `Test with
pytest` creates `privacyidea_test_gw0` through `privacyidea_test_gw7`.
Eight is plenty — GitHub runners have 2-4 cores and xdist won't spawn
more workers than cores. The base `TEST_DATABASE_URL` ends in the
canonical `/privacyidea_test`; the conftest shim appends the worker
suffix.

Separate databases rather than Postgres schemas: `db.create_all()`
creates tables in the default search path, so schemas would require a
per-connection `SET search_path` that pollutes every SQLAlchemy session
setup. Separate databases work identically on MariaDB and PostgreSQL
with no code changes.

### Step L3 — Flip pytest to xdist

In both workflows:

```diff
- python -b -m pytest -v -m "not migration" tests/
+ python -b -m pytest -v -n auto --dist=loadfile -m "not migration" tests/
```

`--dist=loadfile` is the key: tests within a file stay on the same
worker and run in source order. The coverage-only branch
(`if [ "$PYTHON_VERSION" = "3.10" ]`) stays as-is —
`pytest-cov` aggregates coverage data across workers automatically.

### Step L4 — Expected failure modes

The plan anticipates these, and we have hit all of them except the last
one during rollout:

1. **Fixed ports in mock servers.** `radiusmock.py`, `smtpmock.py`,
   `smppmock.py`, `queuemock.py` — any that bind to a fixed port
   collide between workers. *Status:* audit pending; no collision seen
   so far in the runs we've done.
2. **Filesystem state beyond the DB.** See *Findings* below — this
   turned out to be the real blocker.
3. **Cross-file dependency within a worker.** `--dist=loadfile` puts
   multiple files on one worker sequentially. Each `TestCase` already
   cycles its schema, so DB residue is rare, but filesystem residue can
   bleed across. Fix per-case when it shows up.
5. **Long-pole files cap the speedup.** Under `--dist=loadfile` each
   file runs end-to-end on one worker, so the slowest file sets the
   floor on wall time. The four largest files have been split (see
   *What shipped*) to raise that ceiling.

## Findings during rollout

### The real blocker: shared-file state in `ldap3mock`

The most interesting failure we hit was not in the test code or in
privacyIDEA, but in the LDAP mock in `tests/ldap3mock.py`. It used a
hardcoded scratch path

```python
DIRECTORY = "tests/testdata/tmp_directory"
```

that every worker shared. `setLDAPDirectory()` writes the mock
directory tree to this file; `_on_Connection()` re-reads it on every
bind. Two workers running LDAP-using tests in parallel would clobber
each other's directory — or one would read a partially-written file —
and the mock would fail to find a user's DN. That returned `False`
from the password check, which silently broke passthru, which
cascaded into a cloud of downstream test failures.

**Diagnostic sequence:**

- Reproduced `test_04`/`05`/`06`/`07`/`08` failures in
  `tests/test_api_validate_multichallenge_enroll.py` on py3.10 +
  `pytest-cov` + `-n 4 --dist=loadfile`. Same five fail on sqlite,
  PostgreSQL, and MariaDB — so not a DB issue.
- Matrix of worker count × coverage showed the trigger was
  *specifically* `n ≥ 4 AND coverage enabled`. Coverage alone: passes.
  n=4 without coverage: passes. Coverage's trace hook wasn't the bug,
  it just slowed workers enough that the pre-existing filesystem race
  actually hit.
- Instrumented the policy cache, the request pipeline, the passthru
  decorator, and eventually `User.check_password`. Finally saw
  `resolver.checkPass(...) → False` for a valid user+password, which
  pointed at the mock layer.

**Fix** (one file, ~5 lines): namespace the scratch file per worker.

```python
DIRECTORY = "tests/testdata/tmp_directory" + (
    "_" + os.environ["PYTEST_XDIST_WORKER"]
    if os.environ.get("PYTEST_XDIST_WORKER") else ""
)
```

With that in place, three consecutive runs of the previously-flaky set
on py3.10 + postgres + coverage + `-n 4` go **106/106, 106/106, 106/106**.

### What this tells us about the rollout strategy

The light plan's step L4 #2 ("filesystem state beyond the DB") names
`PI_ENCFILE` and `PI_PEPPER` as suspects but misses the mocks
themselves. In practice the mocks *are* filesystem state and need the
same worker-namespacing treatment. Future mock audits should check for
any hardcoded path written during `setUp` and read during a test.

The coverage-race symptom was a red herring. The underlying bug was a
real data race between workers; coverage just made it observable. A
`--cov`-free CI run would have shipped the bug quietly and we'd have
seen sporadic flakes forever. Keeping coverage on at least one matrix
entry is what flushed this out.

## What shipped

Landed on the `reorganize-tests` branch:

- Per-worker DB shim in `tests/conftest.py` (L1).
- Pre-create-DB step + `-n auto --dist=loadfile` in
  `.github/workflows/unit-tests-postgres.yml` and
  `.github/workflows/unit-tests-mariadb.yml` (L2, L3).
- Worker-namespaced `tests/ldap3mock.py` scratch file (the findings
  above).
- Splits of the four mega-files that were capping the speedup:
  `test_lib_token.py` → 7 files (84 tests), `test_api_validate.py` →
  11 files + `api_validate_common.py` (105 tests),
  `test_api_lib_policy.py` → 7 files + `api_lib_policy_common.py`
  (120 tests), `test_api_container.py` → 8 files +
  `api_container_common.py` (221 tests).
- Self-contained fix for `test_lib_tokens_certificate.py` (explicit
  `LocalCAConnector` import) and the `test_41_set_realm_conditions`
  Node1/Node2 collision (`db.session.merge`).

Measured result: ~2× speedup on CI wall time under
`-n auto --dist=loadfile`.

This closes out the light plan. The suite runs green in parallel on
sqlite, MariaDB and PostgreSQL.

## Future work: the full migration

The light plan deliberately preserved unittest-style `TestCase`
inheritance and `test_NN_` ordering. That was the right call to ship a
2× speedup without rewriting 2,400 tests, but it leaves real costs on
the table:

- **Ordered tests.** 503 tests encode dependencies in their method-name
  prefixes. This blocks `pytest-randomly`, makes individual tests
  hard to run in isolation, and turns any "add a test in the middle"
  change into a renumbering exercise.
- **Inheritance-based setup.** `MyTestCase` / `MyApiTestCase` do
  everything in `setUp` / `tearDown` / `setUpClass`. Fixtures would
  make scope explicit (session / module / function), enable
  composition, and let pytest parallelise at the *test* level instead
  of the file level.
- **File-level distribution.** `--dist=loadfile` keeps each file on
  one worker. Moving to `--dist=loadscope` or `--dist=worksteal`
  requires test-level order independence first.
- **Mock audit.** `smtpmock`, `radiusmock`, `smppmock`, `queuemock`,
  `redismock`, `pkcs11mock`, `mscamock` have not been checked for the
  same pattern of fixed paths / fixed ports that bit `ldap3mock`.
  None have surfaced in CI so far, but the audit is still open.

A full overhaul would:

1. Migrate `MyTestCase` / `MyApiTestCase` to a pytest fixture library
   (session-scoped app + function-scoped DB transaction rollback, or
   per-test DB truncation where rollback is not viable).
2. Remove the `test_NN_` ordering contract — every test sets up and
   tears down its own state, so tests can be reordered, selected,
   and parallelised individually.
3. Finish the mock audit and namespace any shared filesystem / port
   state the same way `ldap3mock` was fixed.
4. Switch xdist to `--dist=loadscope` or `worksteal` once ordering is
   gone.

This is a multi-week effort touching every test file and is out of
scope for the light plan. The per-worker DB shim shipped here is
exactly the primitive the full migration will reuse — nothing done on
this branch needs to be undone to take the next step.
