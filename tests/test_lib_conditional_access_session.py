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
from unittest import mock

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
        # Covers callers with no request (pi-manage, scripts, periodic tasks), where call_finalizers() never runs.
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

        # Reaching this line means guarded_write caught the exception; otherwise it would have propagated.
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

        # Reaching this line means guarded_write caught the exception; otherwise it would have propagated.
        with guarded_write("an authentication log entry") as outcome:
            get_ca_session().add(self._entry("bob"))

        self.assertTrue(outcome.succeeded)
        self.assertListEqual(["bob"], self._stored_usernames())

    def test_05_commit_does_not_commit_pending_request_work(self):
        # This is the point of the dedicated session: a conditional-access commit must never persist whatever
        # else the request has pending on db.session.
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

        # Reaching this line means guarded_write caught the exception; otherwise it would have propagated.
        self.assertFalse(outcome.succeeded)
        self.assertIn(pending, db.session.new)
        db.session.commit()
        self.assertListEqual(["pending-on-request-session"], self._stored_usernames())

    def test_07_write_lock_on_the_request_session_is_a_contained_failure(self):
        # This test is SQLite-specific: MariaDB and PostgreSQL use row-level locking, so it does not apply there.
        if db.engine.dialect.name != "sqlite":
            self.skipTest("Database write locking behavior is SQLite-specific. On MariaDB and PostgreSQL, "
                          "row-level locking allows concurrent writes and this test does not apply.")

        # SQLite locks the whole database for writing, so a request session that has flushed without committing
        # blocks the conditional-access write until the driver's lock timeout (5s by default) expires and it fails.
        # The failure is swallowed and stays contained, leaving the request's own session usable; callers must
        # therefore release the request session before writing (see the next test).
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
        # MariaDB and PostgreSQL use row-level locking, so this write succeeds even with a flushed-but-uncommitted
        # request-session transaction, unlike SQLite in test_07; this documents production database behavior.
        if db.engine.dialect.name == "sqlite":
            self.skipTest("This test documents non-SQLite (row-level locking) behavior. "
                          "See test_07 for SQLite's database-level locking behavior.")

        # Add work to the request session and flush it, without committing.
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
        # Once the request session is committed (or rolled back) first, there is no competing write lock, so the
        # conditional-access write goes through - which is why teardown releases db.session before flushing
        # conditional-access writes.
        db.session.add(self._entry("flushed-on-request-session"))
        db.session.flush()
        db.session.commit()

        with guarded_write("an authentication log entry") as outcome:
            get_ca_session().add(self._entry("alice"))

        self.assertTrue(outcome.succeeded)
        self.assertListEqual(["alice", "flushed-on-request-session"], self._stored_usernames())

    def test_09_rollback_failure_is_swallowed_and_logged(self):
        # Cover the contained-failure path where the original write fails and rollback fails as well.
        session = get_ca_session()
        with mock.patch.object(session, "rollback", side_effect=RuntimeError("rollback failed")) as rollback_mock:
            with mock.patch("privacyidea.lib.conditional_access.session.log.warning") as warning_mock:
                with guarded_write("an authentication log entry") as outcome:
                    session.add(self._entry("alice"))
                    raise RuntimeError("write failed")

        self.assertFalse(outcome.succeeded)
        self.assertIsInstance(outcome.error, RuntimeError)
        self.assertEqual("write failed", str(outcome.error))
        rollback_mock.assert_called_once()
        self.assertTrue(any("Rolling back the failed write of an authentication log entry failed as well"
                            in call.args[0] for call in warning_mock.call_args_list))

