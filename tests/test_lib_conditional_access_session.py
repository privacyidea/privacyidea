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

from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType
from privacyidea.lib.conditional_access.session import close_ca_session, get_ca_session
from privacyidea.lib.lifecycle import call_finalizers
from privacyidea.models import db
from privacyidea.models.authentication_log import AuthenticationLog
from .base import MyTestCase


class ConditionalAccessSessionTestCase(MyTestCase):

    def tearDown(self):
        close_ca_session()
        db.session.execute(AuthenticationLog.__table__.delete())
        db.session.commit()

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
