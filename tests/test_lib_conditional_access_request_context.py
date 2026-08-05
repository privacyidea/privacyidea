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
Unit tests for the per-request conditional-access buffer
(:mod:`privacyidea.lib.conditional_access.request_context`).
"""
from sqlalchemy import select

from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType
from privacyidea.lib.conditional_access.authentication_log import (PendingAuthEvent, get_authentication_logs,
                                                                  write_authentication_events)
from privacyidea.lib.conditional_access.request_context import ConditionalAccessContext, get_ca_context
from privacyidea.lib.conditional_access.session import close_ca_session
from privacyidea.models import db
from privacyidea.models.authentication_log import AuthenticationLog, authentication_log_column_length
from .base import MyTestCase


class ConditionalAccessContextTestCase(MyTestCase):

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
    def _event(username, event_type=AuthEventType.LOGIN_SUCCESS):
        return PendingAuthEvent(event_type=event_type, username=username)

    def test_01_context_is_cached_per_app_context(self):
        context = get_ca_context()
        self.assertIs(context, get_ca_context())
        with self.app.app_context():
            self.assertIsNot(context, get_ca_context())

    def test_02_staging_does_not_write(self):
        context = ConditionalAccessContext()
        event = context.stage(self._event("alice"))

        self.assertTrue(context.has_data)
        self.assertIsNone(event.row_id)
        self.assertListEqual([], list(get_authentication_logs()))

    def test_03_stage_returns_the_event_handle(self):
        context = ConditionalAccessContext()
        event = self._event("alice")
        self.assertIs(event, context.stage(event))

    def test_04_flush_writes_and_records_row_ids(self):
        context = ConditionalAccessContext()
        first = context.stage(self._event("alice"))
        second = context.stage(self._event("bob"))

        self.assertTrue(context.flush())

        self.assertIsNotNone(first.row_id)
        self.assertIsNotNone(second.row_id)
        # Written in staging order, so the row ids reconstruct the sequence.
        self.assertLess(first.row_id, second.row_id)
        self.assertListEqual(["alice", "bob"], [entry.username for entry in get_authentication_logs()])

    def test_05_flush_is_idempotent(self):
        context = ConditionalAccessContext()
        event = context.stage(self._event("alice"))
        context.flush()
        row_id = event.row_id

        self.assertTrue(context.flush())

        self.assertEqual(row_id, event.row_id)
        self.assertEqual(1, len(get_authentication_logs()))

    def test_06_flush_only_writes_the_unwritten_events(self):
        context = ConditionalAccessContext()
        first = context.stage(self._event("alice"))
        context.flush()
        second = context.stage(self._event("bob"))

        self.assertListEqual([second], context.unwritten)
        context.flush()

        self.assertListEqual([], context.unwritten)
        self.assertListEqual(["alice", "bob"], [entry.username for entry in get_authentication_logs()])
        self.assertLess(first.row_id, second.row_id)

    def test_07_flush_with_nothing_staged_is_a_noop(self):
        context = ConditionalAccessContext()
        self.assertTrue(context.flush())
        self.assertFalse(context.has_data)
        self.assertListEqual([], list(get_authentication_logs()))

    def test_08_failed_flush_leaves_the_events_unwritten(self):
        # event_type is NOT NULL, so this entry cannot be inserted.
        context = ConditionalAccessContext()
        event = context.stage(PendingAuthEvent(event_type=None, username="alice"))

        self.assertFalse(context.flush())

        self.assertIsNone(event.row_id)
        self.assertListEqual([event], context.unwritten)
        self.assertListEqual([], list(get_authentication_logs()))

    def test_09_all_events_of_one_flush_share_a_transaction(self):
        # A failing event must take its whole flush with it, rather than leaving a partial sequence behind.
        context = ConditionalAccessContext()
        good = context.stage(self._event("alice"))
        bad = context.stage(PendingAuthEvent(event_type=None, username="broken"))

        self.assertFalse(context.flush())

        self.assertIsNone(good.row_id)
        self.assertIsNone(bad.row_id)
        self.assertListEqual([], list(get_authentication_logs()))

    def test_10_amending_a_staged_event_before_the_flush_writes_the_new_value(self):
        # What lets a post-policy correct a classification without a second UPDATE.
        context = ConditionalAccessContext()
        event = context.stage(self._event("alice", AuthEventType.LOGIN_SUCCESS))
        event.event_type = AuthEventType.NOT_AUTHORIZED

        context.flush()

        entries = get_authentication_logs()
        self.assertEqual(1, len(entries))
        self.assertEqual(str(AuthEventType.NOT_AUTHORIZED), entries[0].event_type)

    def test_11_truncation_is_applied_at_flush_time(self):
        # Values are held raw and cut when the row is built, so a value lengthened after staging is still truncated.
        context = ConditionalAccessContext()
        event = context.stage(self._event("alice"))
        oversized = "X" * (authentication_log_column_length["resolver"] + 50)
        event.resolver = oversized

        context.flush()

        entry = db.session.scalars(select(AuthenticationLog)).one()
        self.assertEqual(authentication_log_column_length["resolver"], len(entry.resolver))
        self.assertEqual(oversized[authentication_log_column_length["resolver"]:],
                         entry.other_info["truncated"]["resolver"])

    def test_12_write_authentication_events_with_no_events_succeeds(self):
        self.assertTrue(write_authentication_events([]))
