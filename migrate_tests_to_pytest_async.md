# Test Suite Migration Plan

Migrating `tests/` to a modern, parallelizable, order-independent pytest layout — as a single PR.

---

## Goals

1. **Use pytest fixtures** instead of unittest `setUp`/`tearDown` inheritance for shared state.
2. **Eliminate test order dependence** so the suite can run under `pytest-xdist` and `pytest-randomly`.
3. **Reduce CI runtime** from 16-20 min toward ~5 min via parallelization.
4. **Restructure `tests/` directory** so files map cleanly to the source tree and no file is a multi-thousand-line monster.

## Non-goals (explicitly out of scope for this PR)

- Converting every `self.assertEqual` → `assert`. Mechanical, reviewable per-file, belongs in follow-up PRs.
- Rewriting every unittest `TestCase` class as pytest function tests. Same reasoning — `TestCase` classes coexist with pytest fixtures fine.
- Building a tiered CI (fast/slow/nightly). Add the markers; wire the tiers up later.
- Fixing bugs discovered in the `machine`/`machinetoken` subsystem during migration (known-broken; flag only).

## Current state (snapshot)

- 136 test files, ~2,441 tests.
- All tests inherit from `MyTestCase` / `MyApiTestCase` in `tests/base.py` (unittest style).
- Only one pytest fixture exists (`setup_local_ca` in `tests/conftest.py`).
- No parallelization: CI runs `pytest -v tests/` serially.
- Only marker defined: `migration`.
- 503 tests use `test_NN_` numeric prefixes — the suite's ordering is encoded in method names, not enforced by fixtures.
- Four mega-files dominate total runtime:
  - `test_api_validate.py` (7,141 lines)
  - `test_api_lib_policy.py` (6,640 lines)
  - `test_api_container.py` (6,275 lines)
  - `test_lib_token.py` (2,985 lines)

---

## Execution order

Each step lists **what** is done and **why** that step comes where it does. Steps are designed so that after each one, the suite still passes — you can stop, commit, and resume without a broken tree.

### Step 0 — Cut the branch, announce the freeze

**What:** Create the migration branch. Notify anyone else working in `tests/` that the branch is live and they should merge their test PRs first or rebase after.

**Why:** This PR will rename ~136 files. Concurrent test work will merge-conflict catastrophically. A 10-minute heads-up prevents days of rebase pain.

---

### Step 1 — Pytest config foundation

**What:**
- Add to `pyproject.toml` `[tool.pytest.ini_options]`:
  - `addopts = "--strict-markers -p no:randomly"` (keep randomly installed but off for now)
  - Register markers: `slow`, `ldap`, `integration`, `smtp`, `radius`
- Add dev dependencies: `pytest-xdist`, `pytest-randomly`.

**Why:** `--strict-markers` catches typos in marker names. Registering markers upfront lets later steps tag tests without warnings. `pytest-randomly` is installed but disabled so step 6 can flip it on file-by-file as ordering is fixed, instead of breaking the whole suite at once.

---

### Step 2 — Directory skeleton and mock relocation

**What:**
- Create empty directories:
  ```
  tests/lib/
  tests/lib/tokens/
  tests/lib/eventhandler/
  tests/api/
  tests/api/validate/
  tests/api/container/
  tests/ui/
  tests/migrations/
  tests/mocks/
  ```
- Add a placeholder `conftest.py` in each.
- `git mv` the mock modules into `tests/mocks/`:
  `ldap3mock.py`, `smtpmock.py`, `radiusmock.py`, `redismock.py`, `smppmock.py`, `pkcs11mock.py`, `queuemock.py`, `mscamock.py`, `passkey_base.py`.
- Update imports across the test suite accordingly.

**Why:** Directory structure has to exist before fixtures can be scoped to subdirectories (step 3) and before files can be moved into it (step 4). Moving mocks first is low-risk and gets them out of the top-level namespace where they clash with real test files alphabetically.

---

### Step 3 — Fixture library in `conftest.py`

**What:** Build a fixture layer that `TestCase` classes can opt into. Do **not** remove `MyTestCase` or rewrite existing tests yet.

Root `tests/conftest.py`:
- `app` (session-scoped) — Flask app instance
- `db` (session-scoped) — schema created once
- `db_session` (function-scoped, autouse) — commit+rollback after each test
- `admin_user`, `admin_token` (session / function)

`tests/api/conftest.py`:
- `authenticated_client` — test client with admin token
- API-specific teardown helpers

`tests/lib/conftest.py` (and subdirs):
- `user_realm1`, `user_realm2`, `user_realm_ldap_sql` — factored out of `setUp_user_realms`/`setUp_user_realm4_with_2_resolvers` in `base.py`
- Token-type fixtures in `tests/lib/tokens/conftest.py`

`tests/mocks/conftest.py`:
- `ldap_mock`, `smtp_mock`, `radius_mock`, `redis_mock` as fixtures replacing the `@activate` decorators

**Why:** Fixtures must exist before we can eliminate test-order dependence — the typical fix for "test_00 creates the realm the rest of the class needs" is to express that realm as a class-scoped fixture. Building the fixture library now unblocks step 6. Keeping `MyTestCase` alive means step 6 is additive and incremental, not a rewrite.

---

### Step 4 — Move existing files into new tree

**What:** Pure `git mv` with no content changes. Mapping rules:

| Old path | New path |
|---|---|
| `test_lib_tokens_<x>.py` | `tests/lib/tokens/test_<x>.py` |
| `test_lib_eventhandler_<x>.py` | `tests/lib/eventhandler/test_<x>.py` |
| `test_api_<x>.py` | `tests/api/test_<x>.py` |
| `test_lib_<x>.py` | `tests/lib/test_<x>.py` |
| `test_ui_*.py` | `tests/ui/` |
| `test_migration_*.py`, `test_migrations.py` | `tests/migrations/` |
| `test_mod_apache.py` | `tests/` (top-level, special case) |

Run the full suite after. Zero behavioral changes should be introduced here.

**Why:** Renames are large-diff but trivially reviewable. Doing them as a dedicated commit (or set of commits) lets reviewers approve the file moves at a glance, without having to interleave move-review with logic-review. This is the cheapest step per line of diff.

---

### Step 5 — Split the four mega-files

**What:** Split each of the four largest files by their top-level `TestCase` class into separate files.

- `tests/api/validate/` gets one file per class from old `test_api_validate.py`
- `tests/api/container/` gets one file per class from old `test_api_container.py`
- `tests/api/policy/` gets one file per class from old `test_api_lib_policy.py`
- `tests/lib/tokens/` / `tests/lib/` gets split `test_lib_token.py` classes

Still unittest-style. No logic changes.

**Why:** `pytest-xdist` distributes work at the file level. A 7,000-line file is a 7,000-line serial block to any worker that picks it up — it becomes the long pole of the parallel run regardless of how many workers exist. Splitting by class is the minimum granularity needed for xdist to actually parallelize these.

Also: reviewer attention scales inversely with file size. Splitting here is a prerequisite for step 6 review to be tractable.

---

### Step 6 — Eliminate order dependence (the real work)

**What:** For each `TestCase` class with `test_NN_` numeric prefixes or shared test-to-test state:

1. Identify `test_00_*` / `test_01_*` methods whose purpose is fixture setup (create realm, create token, create policy).
2. Move their state into a class-scoped pytest fixture applied via `@pytest.mark.usefixtures(...)`.
3. Drop the `test_NN_` numeric prefixes.
4. Enable `pytest-randomly` for that file (remove the `-p no:randomly` for it, or run locally with `-p randomly`).
5. Fix whatever breaks. Some breakages will be real bugs in the code under test, not the tests — these get flagged or fixed separately.
6. Commit per file so the history bisects cleanly.

Order of attack: start with the split mega-files from step 5 (highest-impact), then work through the rest.

**Why:** This is the step that actually unlocks parallel CI. `pytest-xdist` runs files in arbitrary order across workers — if your class-under-test needs `test_00_create_realm` to run before `test_05_use_realm`, xdist will either serialize them (negating the parallelism) or fail randomly (worse).

This is also the step most likely to surface real bugs. A test that passes only because an earlier test polluted the DB is hiding something — either unnecessary coupling or a real dependency on global state that production would also have.

Expected to take 40-60% of total project time.

---

### Step 7 — Enable parallelization in CI

**What:**
- Update `.github/workflows/unit-tests-mariadb.yml` to run `pytest -n auto tests/`.
- Remove `-p no:randomly` from pytest `addopts`.
- Tune `-n` if wall time is worse than expected (may benefit from a fixed number matching runner cores).

**Why:** Has to come after step 6, not before. If xdist is turned on while ordering bugs remain, CI becomes flaky-random and the team loses trust in the signal. Flipping it on *after* step 6 is the payoff moment.

---

### Step 8 — Mark slow, LDAP, integration tests

**What:** Apply `@pytest.mark.slow`, `@pytest.mark.ldap`, `@pytest.mark.integration`, `@pytest.mark.smtp`, `@pytest.mark.radius` to the obvious candidates:
- Tests using `ldap_mock` / the old `@ldap3mock.activate` decorator → `@pytest.mark.ldap`
- Tests hitting external-service mocks with substantial setup → `@pytest.mark.integration`
- Tests that take >1 sec locally → `@pytest.mark.slow`

Do **not** build a tiered CI workflow in this PR. Just lay the groundwork.

**Why:** Markers are free to add. Once they exist, future PRs can split CI into fast/slow tiers without touching test code again. Doing it in this PR while the context is fresh is cheap; doing it later means re-reading every test to categorize it.

---

### Step 9 — Rewrite `tests/README.md`

**What:** Document:
- New directory structure and what goes where
- The fixture catalog (`app`, `db_session`, `user_realm1`, `admin_token`, `authenticated_client`, `ldap_mock`, …)
- How to run: full suite, single file, single class, by marker, with randomization
- How to add a new test (which directory, which fixtures)
- Explicit note: unittest-style `TestCase` is still supported; new tests may use either style.

**Why:** Anyone onboarding after this PR will read `tests/README.md` first. Without it, they'll copy the style of the file closest to what they're working on — which might be a half-migrated hybrid. Clear guidance locks in the new conventions.

---

## Commit strategy inside the branch

Suggested commit shape (reviewer-friendly):

1. `tests: add pytest config, markers, dev deps`
2. `tests: introduce fixture library (coexists with unittest base)`
3. `tests: create directory skeleton and relocate mocks`
4. `tests: reorganize files into lib/ api/ ui/ migrations/` ← pure renames
5. `tests: split test_api_validate.py by class`
6. `tests: split test_api_lib_policy.py by class`
7. `tests: split test_api_container.py by class`
8. `tests: split test_lib_token.py by class`
9. `tests: fix order-dependence in <file>` × N (one commit per file)
10. `ci: enable pytest-xdist and pytest-randomly`
11. `tests: add slow/ldap/integration markers`
12. `docs: tests/README for the new structure`

Reviewers can approve commits 3-4 and 5-8 by glancing at the diff summary and spend real attention on 2, 9, and 10.

---

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Step 6 reveals real bugs in production code | Flag and triage separately; do not expand PR scope. Document in PR description. |
| Subtle test coupling that `pytest-randomly` can't catch on one seed | Run randomized suite multiple times locally before declaring a file done. |
| Merge conflicts with concurrent test work | Step 0 freeze. Hold the line. |
| Reviewer burnout on a 136-file PR | Commit hygiene above. Consider splitting into (a) restructure + fixtures, (b) order-dependence fixes — two PRs, same branch sequence. |
| CI green locally, red remotely after xdist | Validate on a branch push before merge. Expect 1-2 iterations of `-n` tuning. |
| `machine`/`machinetoken` tests break in ways that look like migration issues but are pre-existing | Known-broken subsystem; flag bugs but don't fix unless explicitly in scope. |

---

## Timeline (honest, with AI assistance)

| Phase | Effort |
|---|---|
| Steps 0-4 (config, skeleton, fixtures, renames) | ~1 day |
| Step 5 (split mega-files) | ~0.5-1 day |
| Step 6 (order-dependence) | ~1.5-3 days |
| Steps 7-9 (CI, markers, docs) | ~0.5 day |
| **Total focused** | **3-5 days** |
| **Calendar w/ other work** | **1.5-2 weeks** |

Iteration speed during step 6 is bounded by local test execution time, not authoring speed. A faster dev machine materially shortens this phase because the full suite can be run more often, catching ordering bugs earlier.

---

## Success criteria

Before merging the PR, all of these must be true:

- [ ] Full test suite passes locally with `pytest -n auto -p randomly tests/` across at least 3 different random seeds.
- [ ] CI runtime measured and recorded; target ≤ 8 min (stretch: ≤ 5 min).
- [ ] No `test_NN_` numeric prefixes remain in any migrated file.
- [ ] `tests/README.md` documents the new structure and fixture catalog.
- [ ] No test file exceeds 1,500 lines.
- [ ] `pytest --collect-only` lists the expected ~2,441 tests (no test lost during reshuffling).
- [ ] At least one clean CI run with `-n auto` and `pytest-randomly` enabled.
