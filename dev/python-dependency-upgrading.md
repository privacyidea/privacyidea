# Python Dependency Updates

## Background

Python dependencies are managed as **pip-compile generated lock files with hashes**:

- `requirements.txt` — main application (generated from `pyproject.toml`)
- `tests/requirements.txt` — main app + test extras (superset of `requirements.txt`)
- `doc/requirements.txt` — main app + doc extras (superset of `requirements.txt`)

### Why pip-compile with hashes?

`pyproject.toml` declares *abstract* dependencies (name + version constraints).
pip-compile resolves the full transitive dependency graph and writes a *concrete* lockfile
with exact versions pinned. This separation means:

- **Reproducibility** — every developer and CI run installs the exact same package
  versions, including transitive dependencies. No surprise breakage from an upstream
  release.
- **Supply chain security** — `--generate-hashes` adds a SHA-256 hash for every
  downloaded artifact. pip will refuse to install a package if the hash doesn't match,
  protecting against tampered packages on PyPI (e.g. a compromised release or a
  typosquatting attack). For a security product like privacyidea this is particularly
  important.
- **Explicit upgrades** — nothing changes unless you explicitly run pip-compile. There
  are no silent upgrades.

Alternatives like `poetry` or `pipenv` offer similar lockfile guarantees but add tooling
overhead. Plain pinned `requirements.txt` files without hashes provide reproducibility but
not supply chain protection. pip-compile is the lightest-weight option that gives both.

Because the files are fully pinned and hash-verified, dependabot cannot update them
correctly — it edits individual version pins without re-solving the dependency graph,
leaving the lockfile internally inconsistent. Dependabot is therefore **not used** for
Python dependencies.

## Vulnerability Detection

Security vulnerabilities are detected by `pip-audit` running in CI against `requirements.txt`
and results are uploaded to the GitHub Code Scanning tab (Security → Code scanning alerts).
Findings are informational and do not block merging — a CVE being present does not mean
the vulnerable code path is reachable in privacyidea.

You can also run it locally:
```bash
pip install pip-audit
pip-audit -r requirements.txt
```

## Updating a Vulnerable Package

When a CVE is identified for a package, regenerate all three lockfiles:

```bash
pip-compile --upgrade-package <package-name> \
    --allow-unsafe --generate-hashes \
    --output-file=requirements.txt \
    pyproject.toml
```
```bash
pip-compile --upgrade-package <package-name> \
    --allow-unsafe --generate-hashes --extra=test \
    --output-file=tests/requirements.txt \
    pyproject.toml
```
```bash
pip-compile --upgrade-package <package-name> \
    --allow-unsafe --generate-hashes --extra=doc \
    --output-file=doc/requirements.txt \
    pyproject.toml
```

Replace `<package-name>` with the vulnerable package (e.g. `cryptography`).

Commit all three files together in a single PR so the lockfiles stay in sync.

## Updating All Dependencies (routine maintenance, e.g. on start of new development cycle)

To upgrade everything to the latest compatible versions:

```bash
pip-compile --upgrade --allow-unsafe --generate-hashes --output-file=requirements.txt pyproject.toml
```
```bash
pip-compile --upgrade --allow-unsafe --generate-hashes --extra=test --output-file=tests/requirements.txt pyproject.toml
```
```bash
pip-compile --upgrade --allow-unsafe --generate-hashes --extra=doc --output-file=doc/requirements.txt pyproject.toml
```

## Python Version Compatibility

The pip-compile headers record which Python version was used.
Always run pip-compile with the lowest supported python version to avoid pinning packages
incompatible with older supported releases.