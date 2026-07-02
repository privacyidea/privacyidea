# SPDX-FileCopyrightText: (C) 2025 Paul Lettich <paul.lettich@netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Info: https://privacyidea.org
#
# This code is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License
# as published by the Free Software Foundation, either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program. If not, see <http://www.gnu.org/licenses/>.

import os
import shutil
import socket

# Per-worker DB isolation for pytest-xdist. Must run before any `privacyidea`
# import, because TestingConfig.SQLALCHEMY_DATABASE_URI is evaluated at class
# definition (i.e. import) time.
_worker = os.environ.get("PYTEST_XDIST_WORKER")
if _worker:
    _base = os.environ.get("TEST_DATABASE_URL", "")
    if not _base:
        os.environ["TEST_DATABASE_URL"] = f"sqlite:////tmp/pi-test-{_worker}.sqlite"
    elif _base.startswith("sqlite"):
        os.environ["TEST_DATABASE_URL"] = _base.replace(".sqlite", f"-{_worker}.sqlite")
    else:  # mysql / postgres - suffix the DB name
        os.environ["TEST_DATABASE_URL"] = f"{_base}_{_worker}"


def _redis_reachable(host="127.0.0.1", port=6379, timeout=0.2):
    """Best-effort probe so the cache tests opt in automatically when a
    local Redis is already running (e.g. via compose-dev.yml)."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


# Auto-enable real-Redis cache tests when compose-dev's Redis is up. CI
# already exports TEST_REDIS_URL explicitly, so the probe is a no-op there.
if "TEST_REDIS_URL" not in os.environ and _redis_reachable():
    os.environ["TEST_REDIS_URL"] = "redis://127.0.0.1:6379/0"


# Redis ships 16 logical DBs (0-15) by default, and we give each xdist worker
# its own DB so the parallel suite can't collide on the shared
# pi:challenge:* keyspace. That caps the Redis test run at 16 workers; the
# dedicated CI job pins -n to this (and CI runners are far smaller anyway).
_REDIS_TEST_MAX_WORKERS = 16


def _redis_url_for_worker(url, worker):
    """Point each xdist worker at its own Redis logical DB so the parallel
    suite doesn't collide on the shared ``pi:challenge:*`` keyspace - the
    Redis analogue of the per-worker DB-name suffix above. Worker names are
    ``gw0``, ``gw1``, ...

    Fails fast rather than wrapping the DB index with modulo: silently
    collapsing two workers onto one logical DB would let one worker's FLUSHDB
    wipe the other's challenges mid-test - the hardest kind of flake to trace.
    A loud error pointing at ``-n`` is far better than that."""
    import re
    match = re.match(r"gw(\d+)$", worker)
    if not match:
        return url
    db_index = int(match.group(1))
    if db_index >= _REDIS_TEST_MAX_WORKERS:
        raise RuntimeError(
            f"xdist worker {worker} would need Redis logical DB {db_index}, but "
            f"Redis has only {_REDIS_TEST_MAX_WORKERS} (0-{_REDIS_TEST_MAX_WORKERS - 1}). "
            f"Run the Redis test suite with at most {_REDIS_TEST_MAX_WORKERS} workers "
            f"(e.g. -n {_REDIS_TEST_MAX_WORKERS}) so workers don't share a DB.")
    url, _, query = url.partition("?")
    head = re.sub(r"/\d+$", "", url.rstrip("/"))
    rewritten = f"{head}/{db_index}"
    return f"{rewritten}?{query}" if query else rewritten


# Each worker gets its own Redis logical DB, mirroring the per-worker DB above.
# Done before any privacyidea import so TestingConfig.PI_REDIS_URL (read at
# import time) and the cache tests' TEST_REDIS_URL both pick up the worker DB.
if _worker:
    for _redis_var in ("PI_REDIS_URL", "TEST_REDIS_URL"):
        _redis_url = os.environ.get(_redis_var)
        if _redis_url:
            os.environ[_redis_var] = _redis_url_for_worker(_redis_url, _worker)

import pytest

# Enable rich assert diffs for the plain asserts in the auth-log helper module.
pytest.register_assert_rewrite("tests.authlog_utils")

from privacyidea.lib.caconnector import save_caconnector

_redis_flush_client = None


def _flush_worker_redis():
    """FLUSHDB this worker's Redis logical DB. No-op for the default DB-only
    runs (PI_REDIS_URL unset).

    Reliability matters here: a *skipped* flush leaves a stale challenge that
    pollutes the next test on this worker (an unfiltered get_challenges() sees
    an extra entry, or a presence/poll flow matches the wrong challenge). Under
    heavy parallel load the single shared Redis can stall past a tight timeout,
    so use a generous timeout and retry rather than silently giving up after
    one short attempt."""
    url = os.environ.get("PI_REDIS_URL")
    if not url:
        return
    global _redis_flush_client
    import redis as _redis
    last_error = None
    for _attempt in range(3):
        try:
            if _redis_flush_client is None:
                _redis_flush_client = _redis.Redis.from_url(
                    url, socket_connect_timeout=5, socket_timeout=5)
            _redis_flush_client.flushdb()
            return
        except Exception as exc:
            # Drop the (maybe broken) client so the next attempt reconnects.
            last_error = exc
            _redis_flush_client = None
    # All attempts failed. Don't raise (that would mask the test's own result),
    # but make it loud: a skipped flush leaks challenge state into the next test
    # on this worker, which is the hardest CI flake to trace. See
    # notes/flaky-push-test.md.
    import sys
    print(f"WARNING: _flush_worker_redis could not flush {url} after 3 attempts "
          f"({last_error!r}); the next test on this worker may see stale "
          f"challenge state.", file=sys.stderr)


@pytest.fixture(autouse=True)
def _flush_redis_between_tests():
    """When the suite runs against a real Redis challenge backend (the
    dedicated CI job sets PI_REDIS_URL + PI_REDIS_CACHE_CHALLENGES), wipe
    this worker's logical DB after every test. Tests reuse fixed serials and
    transaction ids, so without this their challenge state would leak across
    tests via Redis (which the DB teardown doesn't touch). Each worker owns
    its own DB index, so FLUSHDB is isolated. No-op for the default DB-only
    runs, where PI_REDIS_URL is unset."""
    yield
    _flush_worker_redis()


CAKEY = "cakey.pem"
CACERT = "cacert.pem"
OPENSSLCNF = "openssl.cnf"
WORKINGDIR = "tests/testdata/ca"


@pytest.fixture(scope="function")
def setup_local_ca(tmp_path):
    # TODO: we should probably yield the directory to properly clean it up
    shutil.copytree(WORKINGDIR, tmp_path, dirs_exist_ok=True)
    save_caconnector(
        {
            "cakey": CAKEY,
            "cacert": CACERT,
            "type": "local",
            "caconnector": "localCA",
            "openssl.cnf": OPENSSLCNF,
            "CSRDir": "",
            "CertificateDir": "",
            "WorkingDir": str(tmp_path),
        }
    )
