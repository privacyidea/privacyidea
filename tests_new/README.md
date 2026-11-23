# New test suite

This folder holds the rewritten test suite (#6368). It replaces `tests/` area by area. New tests go here, not into
`tests/`. When the old suite is gone, this folder is renamed to `tests/`.

Every test here runs on its own, in any order and in parallel.

## Running the tests

```bash
python -m pytest tests_new                                 # all
python -m pytest tests_new/api/validate/                   # one folder
python -m pytest tests_new/<path>/test_<name>.py           # one file
python -m pytest "tests_new/<path>/test_<name>.py::<test>" # one test
python -m pytest -n auto tests_new                         # parallel
```

## Layout

The tests mirror the code: `privacyidea/lib/...` becomes `tests_new/lib/...`, `privacyidea/api/...` becomes
`tests_new/api/...`.

```
tests_new/
  conftest.py                  # app, app_context, clean_db, no_error_logs, markers
  helpers/                     # code only, no tests
    asserts.py                 # assert_auth, assert_error(code), ...
    otp.py                     # RFC test vectors, TOTP helpers on a fixed clock
    keys/                      # fixed key pairs for push and certificates
    directories.py             # LDAP directories
    smartphone.py              # push and passkey client
  doubles/                     # fixtures for external systems, loaded as a pytest plugin
    redis.py  smtp.py  ldap.py  radius.py  hsm.py  msca.py  http.py

  lib/                         # mirrors privacyidea/lib
    conftest.py                # factories: make_token, make_policy, make_realm, ...
    token/                     # test_auth_decision.py  test_query.py  test_failcounter.py ...
    tokens/                    # test_hotp.py  test_totp.py  push/test_enroll.py  push/test_challenge.py ...
    resolvers/                 # test_ldap_search.py  test_ldap_edit.py  test_sql.py ...
    policies/  conditional_access/  containers/  eventhandler/  auditmodules/  ...

  api/                         # one folder per module in privacyidea/api
    conftest.py                # api, admin_api, user_api, realm and user fixtures
    validate/                  # test_check_user.py  test_check_serial.py  test_failcounter.py ...
    token/  policy/  auth/  container/  user/  realm/  system/  ...
    lib/                       # privacyidea/api/lib: test_prepolicy_enroll.py  test_postpolicy_*.py ...

  integration/                 # real servers: OpenLDAP, FreeRADIUS, Redis, PostgreSQL, SoftHSM2
  migrations/
  cli/                         # mirrors privacyidea/cli: pimanage/  pitokenjanitor/  tools/
```

Every folder has an `__init__.py`, so files with the same name in different folders do not collide.

- **Test path matches code path.** The tests for `privacyidea/lib/token/query.py` live in `tests_new/lib/token/`.
- **One file per group of behaviour**, at most about 500 lines. The name says what it covers: `test_failcounter.py`,
  not `test_validate_3.py`. A file that grows too large becomes a folder.
- **Fixtures as low as possible.** A fixture only `api/validate/` needs lives in its `conftest.py`. It moves up when
  a second folder needs it.
- **`lib/` tests the logic, `api/` what the request adds:** parameters, rights, policies, response format, audit.
- **Pure logic needs no app.** A test without the `app` fixture runs without database.
- **Real servers only in `integration/`.** These tests are marked and run in their own CI job.
- **Nothing is imported from `tests/`.** Shared code lives in `helpers/` or in fixtures.

## What a good test looks like

Every test follows **F.I.R.S.T.**:

- **Fast:** only the setup it needs.
- **Independent:** builds its own state through fixtures. Runs alone and in any order. Leaves nothing behind.
- **Repeatable:** controlled clock, no network, no `sleep`. Same result on every machine, serial or parallel.
- **Self-validating:** passes or fails on its own, nobody has to read logs. Turns red when the behaviour breaks, and
  only then.
- **Timely:** written together with the code change.

In addition:

- **One behaviour:** one test checks one behaviour, and its name says which. Arrange, act, assert, with one act.
- **Readable on its own:** the values an assertion depends on are visible in the test. No loops or `if`s.
- **Through the public interface:** tests what the API or function does, not how.
- **Real before fake before mock:** real database and real code. Fakes or mocks only at system boundaries.
- **Negative and unusual cases too:** failures, refusals and unusual data are tested as carefully as the success path.
- **Side effects too:** a test that triggers an action also checks what it records: audit entry, authentication log,
  token counters, sent messages.

## Conventions

- **Names describe the behaviour**, no numbers: `test_matching_pin_increases_failcounter_of_that_token_only`.
- **Variations with `@pytest.mark.parametrize`**, no copied blocks.
- **Plain `assert`**, so pytest shows both values on failure.
- **Assert the whole result:** status code, `result.value` and the relevant `detail` fields.
- **Assert error codes and exception types**, not message texts. `pytest.raises(SpecificError)`, never `Exception`.
- **No assumptions on order or ids** unless the code sorts. Compare sets or sort explicitly.
- **Files:** `tmp_path` for temporary files, a fixture for test data paths. Never relative to the working directory,
  never written into the test data.
- **pytest only:** no `TestCase`, no `self.assert*`, no `unittest.mock`.
- **Tools:** `monkeypatch` and `mocker` (`pytest-mock`) for code, `responses` or `pytest-httpserver` for HTTP,
  `time-machine` for the clock.
- **Empty the tables per test, do not roll back.** Audit, authentication log, metrics and resolver cache use their own
  database connections, which a SAVEPOINT rollback does not cover.

## Common mistakes

The old suite shows these again and again. Avoid them.

- Assertions that cannot fail: `assert response`, `assertTrue(x, expected)`, a truth check on a return value like
  `-1`.
- Statements after the raising call inside a `pytest.raises` block. They never run.
- Checks in a loop over a result that may be empty.
- `try`/`except` around the code under test, or errors that are only logged.
- Setup helpers that assert, so a broken setup looks like a failing test.
- A behaviour that only a test about something else catches.
- Mocks that replace our own logic instead of a fake at the system boundary.

## Test doubles

| System              | Test double                                             |
|---------------------|---------------------------------------------------------|
| Redis               | `fakeredis`                                             |
| SMTP                | `aiosmtpd` `Controller` on localhost                    |
| LDAP                | ldap3 `MOCK_SYNC`; OpenLDAP in `integration/`           |
| HSM (PKCS#11)       | SoftHSM2                                                |
| RADIUS              | `pyrad.server.Server` in a thread                       |
| Microsoft CA (gRPC) | fake servicer behind a real `grpc.server` on localhost  |
| SMPP                | `mocker.create_autospec(smpplib.client.Client)`         |
| HTTP                | `responses` in strict mode, `pytest-httpserver`         |
| Clock               | `time-machine`                                          |

The fixtures live in `doubles/`. Our own mocks in `tests/` (`ldap3mock`, `smtpmock`, ...) are not used here.

## Fixtures

Each fixture is listed here with what it provides, once it exists.

| Fixture       | Scope    | Defined in    | Provides                                                                   |
|---------------|----------|---------------|----------------------------------------------------------------------------|
| `app`         | session  | `conftest.py` | The Flask app with a freshly built schema, one per process                 |
| `app_context` | function | `conftest.py` | A fresh app context with an empty `g` and an empty app-local store         |
| `clean_db`    | function | `conftest.py` | Empty tables and sequences from 1, apart from the config timestamp         |

A test that needs the database requests `clean_db`, directly or through another fixture. A test of pure logic requests
none of them and runs without an app. The tables are emptied before each test, so a test without `clean_db` cannot
disturb the tests that use it.

Without `TEST_DATABASE_URL`, every process gets its own temporary SQLite file. With it, every xdist worker appends its
name, as CI expects.

## Moving tests from `tests/`

The old tests are frozen: no new tests in old files. A bug fix in an area that is not migrated yet gets its test here.

Each work area of #6368 is one sub-issue and follows these steps:

1. **Decide:** list the old files of the work area, each marked rewrite or revise. Revise only files that already
   run alone and in any order.
2. **Inventory:** list the behaviours the old tests check. Each item is covered by a new test, dropped with a reason,
   or marked as doubtful and clarified.
3. **Write or revise** the tests here. Do not copy old test code.
4. **Compare:** branch coverage of the affected modules must not drop. Lines only the old tests covered are listed
   and explained.
5. **Delete** the old tests in the same PR.

## Checklist for a PR

- [ ] Every test runs on its own and in random order
- [ ] Every new test was seen failing once
- [ ] Pure pytest, no `pytest.raises(Exception)`
- [ ] No `sleep`, no real clock, no network, no writes outside `tmp_path`
- [ ] Negative and unusual cases are tested
- [ ] Side effects are checked
- [ ] No unexpected `ERROR` logs
- [ ] Branch coverage of the module did not drop
