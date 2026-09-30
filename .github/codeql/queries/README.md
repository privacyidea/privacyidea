# privacyIDEA custom CodeQL queries

These run in addition to the default CodeQL suite (see `.github/workflows/codeql.yml`, Python leg) and encode recurring
defect shapes so a new change that reintroduces one is flagged on the pull request.

| Query | Flags |
|---|---|
| `B1-tls-verify-off` | An SMTP/`requests` client created without certificate verification (`SMTP_SSL`/`starttls()` with no `context=`, or `verify=False`) on a path that carries credentials/OTPs. |
| `B2-structured-template-injection` | A value substituted with `str.replace()` and then parsed with `json.loads()` — a substituted value can inject structure. |
| `B3-subprocess-argv-concat` | A subprocess argv element built by string concatenation (no path containment / `--` separator). |
| `B4-write-then-chmod` | A secret file opened for writing and only `chmod`'d to an owner-only mode afterwards (world-readable window). |
| `B5-config-exec-sink` | `Config.from_pyfile` / `exec` running a file as Python — unsafe if the bytes can come from an archive/untrusted source. |

These five are the high-precision queries. Broader "review-list" queries (route-missing-authz, global-write-only) and
the design notes live in the security-review corpus and are intentionally not wired to fail CI; the missing-gate case
is covered by `tests/test_route_authorization_registry.py` instead.

Run locally with the CodeQL CLI:
```
codeql database create db --language=python --source-root=. --codescanning-config=.github/codeql/codeql-config.yml
codeql database analyze db .github/codeql/queries --format=csv --output=out.csv
```
