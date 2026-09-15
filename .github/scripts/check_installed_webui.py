#!/usr/bin/env python3
# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: CC0-1.0
"""
Check that an installed privacyIDEA serves the WebUI.

Run with the interpreter of the environment the wheel was installed into, from a directory that
is not the repository, so that nothing can be answered out of the source tree.
"""
import json
import os
import sys
import tempfile

TEMP_DIR = tempfile.mkdtemp()
# An empty configuration file, so that neither the configuration of the machine this runs on nor
# a warning about a missing one gets into the way.
EMPTY_CONFIG = os.path.join(TEMP_DIR, "empty.cfg")
open(EMPTY_CONFIG, "w").close()
os.environ["PRIVACYIDEA_CONFIGFILE"] = EMPTY_CONFIG
os.environ["PRIVACYIDEA_SQLALCHEMY_DATABASE_URI"] = json.dumps(f"sqlite:///{TEMP_DIR}/privacyidea.sqlite")

from privacyidea.app import create_app  # noqa: E402
from privacyidea.models import db  # noqa: E402


def main() -> int:
    package_dir = os.path.dirname(sys.modules["privacyidea"].__file__)
    print(f"privacyIDEA is installed in {package_dir}")
    if os.path.realpath(package_dir).startswith(os.path.realpath(os.getcwd())):
        print("::error::Running from the source tree, which is what this check has to avoid")
        return 1

    app = create_app("production", "", silent=True)
    with app.app_context():
        db.create_all()
    client = app.test_client()
    problems = []

    root = client.get("/")
    if root.status_code != 302 or not root.headers.get("Location", "").endswith("/app/v2/"):
        problems.append(f"GET / answered {root.status_code} {root.headers.get('Location')}, "
                        f"expected a redirect to /app/v2/")

    # curl and every browser send an Accept header; the SPA routes are served through the
    # not-found handler, which negotiates on it.
    spa = client.get("/app/v2/", headers={"Accept": "text/html"})
    if spa.status_code != 200:
        problems.append(f"GET /app/v2/ answered {spa.status_code}, expected the WebUI")

    assets = client.get("/static/public/policy-templates/index.json")
    if assets.status_code != 200:
        problems.append(f"GET /static/public/policy-templates/index.json answered "
                        f"{assets.status_code}, expected the policy template index")

    # The WebUI is installed built, so its sources are not there to be served.
    for path in ["/static/src/main.ts", "/static/angular.json", "/static/package-lock.json"]:
        response = client.get(path)
        if response.status_code != 404:
            problems.append(f"GET {path} answered {response.status_code}, expected 404: "
                            f"the WebUI sources are not distributed")

    for problem in problems:
        print(f"::error::{problem}")
    if problems:
        return 1
    print("The installed privacyIDEA serves the WebUI and none of its sources.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
