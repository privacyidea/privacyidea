# (c) NetKnights GmbH 2026,  https://netknights.it
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
__doc__ = """The database session the conditional-access subsystem writes on.

The authentication log and the lock/blocklist state are written while an authentication response is still in
flight, and they must never interfere with the request's own work. On the shared ``db.session`` they do: committing
a log entry commits whatever else the request has pending at that moment, and rolling back a failed write discards
it. Both effects are invisible at the call site, which is why these writes get a session of their own.

The session is bound to the very same engine as ``db.session`` -- same database, same connection pool. Only the
transaction is separate; nothing here implies (or supports) storing the conditional-access tables elsewhere.
"""
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy.orm import Session

from privacyidea.lib.framework import get_request_local_store
from privacyidea.lib.lifecycle import register_finalizer
from privacyidea.models import db

log = logging.getLogger(__name__)

# Key the session is cached under in the app-context-local store.
_SESSION_KEY = "conditional_access_session"


def get_ca_session() -> Session:
    """
    Return the conditional-access session of the current app context, creating it on first use.

    All conditional-access reads and writes share this one session, so a count query always sees the rows this
    request itself wrote: under MySQL/MariaDB's REPEATABLE READ, a row committed by another session after the
    reading transaction began would be invisible to it.

    A plain :class:`~sqlalchemy.orm.Session` is enough -- the store it is cached in is already local to the app
    context (and thus to the thread), so wrapping it in a ``scoped_session`` as the SQL audit module does would
    add a thread-local registry that nothing here can reach.
    """
    store = get_request_local_store()
    session = store.get(_SESSION_KEY)
    if session is None:
        session = Session(bind=db.engine)
        store[_SESSION_KEY] = session
        register_finalizer(close_ca_session)
    return session


def close_ca_session(*_args) -> None:
    """
    Close the conditional-access session of the current app context and drop it from the store, returning its
    connection to the pool.

    Idempotent, and safe to call when no session was ever created: the next :func:`get_ca_session` simply opens a
    fresh one. Registered both as a request finalizer and as an app-context teardown handler (see
    :func:`init_ca_session`), so it does run twice per request -- hence taking, and ignoring, the teardown
    handler's exception argument.
    """
    session = get_request_local_store().pop(_SESSION_KEY, None)
    if session is not None:
        session.close()


@dataclass
class WriteOutcome:
    """
    Result of a :func:`guarded_write` block: whether the writes were committed, and the exception that prevented it
    otherwise. A caller that only needs "best effort" can ignore it entirely.
    """
    succeeded: bool = False
    error: Exception | None = None


@contextmanager
def guarded_write(description: str, session: Session | None = None,
                  reraise: bool = False) -> Iterator[WriteOutcome]:
    """
    Run a block of conditional-access writes as one transaction: commit it on success, roll it back on failure.

    Failures are swallowed by default, because these writes happen while an authentication response is in flight and
    must never break it -- a lost log entry or lock row is bad, a failed authentication is worse. The session is
    left usable either way, so the rest of the request (and the audit entry it still has to write) is unaffected.

    Wrap **one** write per block, not a whole group of them: committing each separately means only one row lock is
    ever held at a time. A block that locked a ``UserLockState`` row and a ``BlockList`` row together (as one
    triggered stage can) would let two concurrent requests acquire them in opposite order and deadlock on InnoDB.

    Note the caller must not hold a flushed-but-uncommitted write on ``db.session`` when this runs: on SQLite, which
    locks the whole database for writing, the commit then waits out the driver's lock timeout and fails (see
    ``GuardedWriteTestCase.test_07``). Reads on ``db.session`` are harmless.

    :param description: what is being written, as a noun phrase for the log message, e.g.
        ``f"the user lock state for {user!r}"``
    :param session: the session to write on; defaults to the conditional-access session
    :param reraise: propagate the failure after rolling back. For management and CLI paths, where an admin is
        waiting for the outcome and a silent failure would be indistinguishable from "nothing matched".
    """
    session = session or get_ca_session()
    outcome = WriteOutcome()
    try:
        yield outcome
        session.commit()
        outcome.succeeded = True
    except Exception as ex:
        outcome.error = ex
        log.warning(f"Failed to write {description}: {ex!r}")
        try:
            session.rollback()
        except Exception as rollback_error:
            log.warning(f"Rolling back the failed write of {description} failed as well: {rollback_error!r}")
        if reraise:
            raise


def init_ca_session(app) -> None:
    """
    Register :func:`close_ca_session` as an app-context teardown handler on *app*.

    ``call_finalizers`` only runs from ``teardown_request``, so a session opened outside a request -- ``pi-manage``,
    a script, a periodic task -- would hold its connection until the app context is garbage collected. Closing on
    app-context teardown covers those callers too.
    """
    app.teardown_appcontext(close_ca_session)
