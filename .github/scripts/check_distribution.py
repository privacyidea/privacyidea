#!/usr/bin/env python3
# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: CC0-1.0
"""
Check that the built sdist and wheel carry what an installation needs, and nothing more.

Run after "python -m build", from the repository root. Expects dist/ to hold exactly one sdist
and one wheel.
"""
import glob
import pathlib
import sys
import tarfile
import zipfile

# Present in both distributions: without these an installation has no WebUI, no policy templates
# and no pages for the requests privacyIDEA renders itself.
REQUIRED = [
    "privacyidea/static/dist/privacyidea-webui/browser/en/index.html",
    "privacyidea/static/public/policy-templates/index.json",
    "privacyidea/static_old/templates/index.html",
    "privacyidea/static_old/contrib/css/bootstrap-theme.css",
    "privacyidea/migrations/env.py",
]

# Absent from both: the WebUI is distributed built, and everything below the static folder is
# reachable over HTTP.
FORBIDDEN_PREFIXES = [
    "privacyidea/static/src/",
    "privacyidea/static/node_modules/",
    "privacyidea/static/.angular/",
]
FORBIDDEN = [
    "privacyidea/static/angular.json",
    "privacyidea/static/package.json",
    "privacyidea/static/package-lock.json",
]


def members(path: pathlib.Path) -> set[str]:
    """Return the members of a distribution, with the leading <name>-<version>/ removed."""
    if path.suffix == ".whl":
        names = zipfile.ZipFile(path).namelist()
        return {name for name in names if not name.startswith("privacyidea-")}
    with tarfile.open(path) as archive:
        names = archive.getnames()
    return {name.split("/", 1)[1] for name in names if "/" in name}


def check(path: pathlib.Path) -> list[str]:
    names = members(path)
    problems = []
    for required in REQUIRED:
        if required not in names:
            problems.append(f"{path.name} is missing {required}")
    for forbidden in FORBIDDEN:
        if forbidden in names:
            problems.append(f"{path.name} contains {forbidden}, which is not distributed")
    for prefix in FORBIDDEN_PREFIXES:
        found = sorted(name for name in names if name.startswith(prefix))
        if found:
            problems.append(f"{path.name} contains {len(found)} files below {prefix}, "
                            f"for example {found[0]}")
    print(f"{path.name}: {len(names)} members")
    return problems


def main() -> int:
    distributions = [pathlib.Path(name) for name in sorted(glob.glob("dist/*.whl") + glob.glob("dist/*.tar.gz"))]
    if len(distributions) != 2:
        print(f"::error::Expected one wheel and one sdist in dist/, found {distributions}")
        return 1

    problems = [problem for distribution in distributions for problem in check(distribution)]
    for problem in problems:
        print(f"::error::{problem}")
    if problems:
        print("\nWhat a distribution contains is decided by MANIFEST.in, not by pyproject.toml.")
        return 1
    print("Both distributions carry the WebUI and the previous WebUI, without the WebUI sources.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
