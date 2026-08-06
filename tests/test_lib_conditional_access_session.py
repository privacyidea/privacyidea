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
"""
Unit tests for the dedicated conditional-access database session
(:mod:`privacyidea.lib.conditional_access.session`).
"""
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType
from privacyidea.lib.conditional_access.session import close_ca_session, get_ca_session, guarded_write
from privacyidea.lib.lifecycle import call_finalizers
from privacyidea.models import db
from privacyidea.models.authentication_log import AuthenticationLog
from .base import MyTestCase


class ConditionalAccessSessionTestCase(MyTestCase):

    def tearDown(self):
        close_ca_session()
        db.session.execute(AuthenticationLog.__table__.delete())
        db.session.commit()
        super().tearDown()

    def test_01_session_is_cached_per_app_context(self):
        session = get_ca_session()
        self.assertIs(session, get_ca_session())
        # A fresh app context has its own ``g``, and therefore its own session.
        with self.app.app_context():
            self.assertIsNot(session, get_ca_session())
            close_ca_session()

    def test_02_session_is_not_the_request_session(self):
        # ``db.session`` is a scoped_session proxy, so compare against the session it proxies to.
        self.assertIsNot(db.session(), get_ca_session())

    def test_03_bound_to_the_same_engine(self):
        self.assertIs(db.engine, get_ca_session().get_bind())

    def test_04_write_is_visible_to_the_request_session(self):
        ca_session = get_ca_session()
        ca_session.add(AuthenticationLog(event_type=AuthEventType.LOGIN_SUCCESS, username="alice"))
        ca_session.commit()

        entries = db.session.scalars(select(AuthenticationLog)).all()
        self.assertEqual(1, len(entries))
        self.assertEqual("alice", entries[0].username)

    def test_05_close_is_idempotent_and_reopens(self):
        session = get_ca_session()
        close_ca_session()
        # Closing again must not raise, even though there is nothing left to close.
        close_ca_session()
        self.assertIsNot(session, get_ca_session())

    def test_06_request_finalizer_closes_the_session(self):
        session = get_ca_session()
        entry = AuthenticationLog(event_type=AuthEventType.LOGIN_SUCCESS, username="bob")
        session.add(entry)
        self.assertIn(entry, session)

        call_finalizers()
        # close() expunges the identity map, and the session is dropped so the next call opens a new one.
        self.assertNotIn(entry, session)
        self.assertIsNot(session, get_ca_session())

    def test_07_closer_registered_as_appcontext_teardown(self):
        # Covers the callers that never run a request (pi-manage, scripts, periodic tasks), for which
        # call_finalizers() is never invoked.
        self.assertIn(close_ca_session, self.app.teardown_appcontext_funcs)


class GuardedWriteTestCase(MyTestCase):

    def setUp(self):
        self._clear()

    def tearDown(self):
        close_ca_session()
        self._clear()
        super().tearDown()

    @staticmethod
    def _clear():
        db.session.rollback()
        db.session.execute(AuthenticationLog.__table__.delete())
        db.session.commit()

    @staticmethod
    def _entry(username):
        return AuthenticationLog(event_type=AuthEventType.LOGIN_SUCCESS, username=username)

    def _stored_usernames(self):
        return db.session.scalars(select(AuthenticationLog.username).order_by(AuthenticationLog.username)).all()

    def test_01_commits_on_success(self):
        with guarded_write("an authentication log entry") as outcome:
            get_ca_session().add(self._entry("alice"))

        self.assertTrue(outcome.succeeded)
        self.assertIsNone(outcome.error)
        self.assertListEqual(["alice"], self._stored_usernames())

    def test_02_rolls_back_and_swallows_on_failure(self):
        error = RuntimeError("write failed")
        with guarded_write("an authentication log entry") as outcome:
            get_ca_session().add(self._entry("alice"))
            raise error

        # error should be caught by the guarded write, hence we should reach here otherwise the test fail
        self.assertFalse(outcome.succeeded)
        self.assertIs(error, outcome.error)
        self.assertListEqual([], self._stored_usernames())

    def test_03_reraise_propagates_and_still_rolls_back(self):
        with self.assertRaises(RuntimeError):
            with guarded_write("an authentication log entry", reraise=True):
                get_ca_session().add(self._entry("alice"))
                raise RuntimeError("write failed")

        self.assertListEqual([], self._stored_usernames())

    def test_04_session_is_usable_after_a_failure(self):
        with guarded_write("an authentication log entry"):
            get_ca_session().add(self._entry("alice"))
            raise RuntimeError("write failed")

        # error should be caught by the guarded write, hence we should reach here otherwise the test fail
        with guarded_write("an authentication log entry") as outcome:
            get_ca_session().add(self._entry("bob"))

        self.assertTrue(outcome.succeeded)
        self.assertListEqual(["bob"], self._stored_usernames())

    def test_05_commit_does_not_commit_pending_request_work(self):
        # The whole point of the dedicated session: a conditional-access commit must not persist whatever else
        # the request happens to have pending on db.session.
        db.session.add(self._entry("pending-on-request-session"))

        with guarded_write("an authentication log entry") as outcome:
            get_ca_session().add(self._entry("alice"))

        self.assertTrue(outcome.succeeded)
        db.session.rollback()
        self.assertListEqual(["alice"], self._stored_usernames())

    def test_06_rollback_does_not_discard_pending_request_work(self):
        # The mirror image: a failed conditional-access write must not roll back the request's own changes.
        pending = self._entry("pending-on-request-session")
        db.session.add(pending)

        with guarded_write("an authentication log entry") as outcome:
            get_ca_session().add(self._entry("alice"))
            raise RuntimeError("write failed")

        # error should be caught by the guarded write, hence we should reach here otherwise the test fail
        self.assertFalse(outcome.succeeded)
        self.assertIn(pending, db.session.new)
        db.session.commit()
        self.assertListEqual(["pending-on-request-session"], self._stored_usernames())

    def test_07_write_lock_on_the_request_session_is_a_contained_failure(self):
        # Database write locking behavior is SQLite-specific. On MariaDB and PostgreSQL, row-level locking
        # allows concurrent writes and this test does not apply.
        if db.engine.dialect.name != "sqlite":
            self.skipTest("Database write locking behavior is SQLite-specific. On MariaDB and PostgreSQL, "
                          "row-level locking allows concurrent writes and this test does not apply.")

        # Two sessions means two connections. On SQLite, which locks the whole database for writing, a request
        # session that has flushed without committing blocks the conditional-access write: it waits out the
        # driver's lock timeout (5s by default) and then fails. The entry is lost, but the failure stays
        # contained - it is swallowed, the request's own work survives, and the session remains usable.
        # Callers must therefore release the request session before writing; see the next test.
        pending = self._entry("flushed-on-request-session")
        db.session.add(pending)
        db.session.flush()

        with guarded_write("an authentication log entry") as outcome:
            get_ca_session().add(self._entry("alice"))

        self.assertFalse(outcome.succeeded)
        self.assertIsInstance(outcome.error, OperationalError)
        db.session.commit()
        self.assertListEqual(["flushed-on-request-session"], self._stored_usernames())

    def test_07b_flushed_lock_succeeds_on_non_sqlite(self):
        # On MariaDB and PostgreSQL with row-level locking, a conditional-access write succeeds even when the
        # request session has a flushed-but-uncommitted transaction (the opposite of SQLite behavior in test_07).
        # This documents the production database behavior.
        if db.engine.dialect.name == "sqlite":
            self.skipTest("This test documents non-SQLite (row-level locking) behavior. "
                          "See test_07 for SQLite's database-level locking behavior.")

        # Add and flush work on the request session without committing
        pending = self._entry("flushed-on-request-session")
        db.session.add(pending)
        db.session.flush()

        # The conditional-access write succeeds despite the lock, because MariaDB/PostgreSQL use row-level locking
        with guarded_write("an authentication log entry") as outcome:
            get_ca_session().add(self._entry("alice"))

        # On production databases, the write succeeds and both entries are stored
        self.assertTrue(outcome.succeeded)
        db.session.commit()
        self.assertListEqual(["alice", "flushed-on-request-session"], self._stored_usernames())

    def test_08_commits_once_the_request_session_released_its_lock(self):
        # The mitigation for the above: with the request session committed (or rolled back) first, there is no
        # competing write lock and the conditional-access write goes through. This is why request teardown has to
        # release db.session before flushing the conditional-access writes.
        db.session.add(self._entry("flushed-on-request-session"))
        db.session.flush()
        db.session.commit()

        with guarded_write("an authentication log entry") as outcome:
            get_ca_session().add(self._entry("alice"))

        self.assertTrue(outcome.succeeded)
        self.assertListEqual(["alice", "flushed-on-request-session"], self._stored_usernames())
