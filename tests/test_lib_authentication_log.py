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
from datetime import datetime, timezone, timedelta

from .base import MyTestCase
from privacyidea.lib.conditional_access.authentication_error_codes import AuthEventType
from privacyidea.lib.conditional_access.authentication_log import (
    log_authentication_event,
    delete_authentication_log_event,
    get_authentication_log_event,
    get_authentication_logs,
    cleanup_authentication_log,
)


class AuthenticationLogTestCase(MyTestCase):

    def tearDown(self):
        from privacyidea.models.authentication_log import AuthenticationLog
        from privacyidea.models import db
        db.session.query(AuthenticationLog).delete()
        db.session.commit()

        super().tearDown()

    def test_create_required_fields_only(self):
        event_id = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="user1", realm="realm1")
        self.assertIsNotNone(event_id)
        self.assertGreater(event_id, 0)

        entry = get_authentication_log_event(event_id)
        assert entry is not None
        self.assertEqual("res1", entry.resolver)
        self.assertEqual("user1", entry.uid)
        self.assertEqual("realm1", entry.realm)
        self.assertIsNone(entry.username)
        self.assertEqual(AuthEventType.LOGIN_SUCCESS, entry.event_type)
        self.assertIsNone(entry.source_ip)
        self.assertIsNone(entry.client_label)
        self.assertIsNone(entry.serial)
        self.assertIsNone(entry.transaction_id)
        self.assertIsNone(entry.other_info)

    def test_create_all_fields(self):
        event_id = log_authentication_event(
            event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="user1", realm="realm1",
            username="testuser", source_ip="192.168.1.1", client_label="vpn", serial="TOK001",
            transaction_id="txn-123", other_info={"key": "value"}
        )

        entry = get_authentication_log_event(event_id)
        assert entry is not None
        self.assertEqual("testuser", entry.username)
        self.assertEqual("192.168.1.1", entry.source_ip)
        self.assertEqual("vpn", entry.client_label)
        self.assertEqual("TOK001", entry.serial)
        self.assertEqual("txn-123", entry.transaction_id)
        self.assertEqual({"key": "value"}, entry.other_info)

    def test_create_returns_unique_ids(self):
        id1 = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1")
        id2 = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1")
        self.assertNotEqual(id1, id2)

    def test_delete_existing_entry(self):
        event_id = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="user1", realm="realm1")
        self.assertIsNotNone(get_authentication_log_event(event_id))

        delete_authentication_log_event(event_id)

        self.assertIsNone(get_authentication_log_event(event_id))

    def test_delete_nonexistent_is_noop(self):
        delete_authentication_log_event(999999)

    def test_get_nonexistent_returns_none(self):
        self.assertIsNone(get_authentication_log_event(999999))

    def test_get_authentication_logs_no_filter(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res2", uid="u2", realm="r2")

        results = get_authentication_logs()
        self.assertEqual(2, len(results))

    def test_get_authentication_logs_filter_by_resolver(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res2", uid="u2", realm="r1")

        results = get_authentication_logs(resolver="res1")
        self.assertEqual(1, len(results))
        self.assertEqual("res1", results[0].resolver)

    def test_get_authentication_logs_filter_by_uid(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u2", realm="r1")

        results = get_authentication_logs(uid="u1")
        self.assertEqual(1, len(results))
        self.assertEqual("u1", results[0].uid)

    def test_get_authentication_logs_filter_by_realm(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r2")

        results = get_authentication_logs(realm="r2")
        self.assertEqual(1, len(results))
        self.assertEqual("r2", results[0].realm)

    def test_get_authentication_logs_filter_by_event_type(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1")
        log_authentication_event(event_type=AuthEventType.MFA_FAIL, resolver="res1", uid="u1", realm="r1")

        results = get_authentication_logs(event_type=AuthEventType.MFA_FAIL)
        self.assertEqual(1, len(results))
        self.assertEqual(AuthEventType.MFA_FAIL, results[0].event_type)

    def test_get_authentication_logs_filter_by_serial(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1", serial="TOK001")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1", serial="TOK002")

        results = get_authentication_logs(serial="TOK001")
        self.assertEqual(1, len(results))
        self.assertEqual("TOK001", results[0].serial)

    def test_get_authentication_logs_filter_by_source_ip(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1", source_ip="10.0.0.1")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1", source_ip="10.0.0.2")

        results = get_authentication_logs(source_ip="10.0.0.1")
        self.assertEqual(1, len(results))
        self.assertEqual("10.0.0.1", results[0].source_ip)

    def test_get_authentication_logs_filter_by_transaction_id(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, transaction_id="txn-a",
                                  resolver="res1", uid="u1", realm="r1")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, transaction_id="txn-b",
                                  resolver="res1", uid="u1", realm="r1")

        results = get_authentication_logs(transaction_id="txn-a")
        self.assertEqual(1, len(results))
        self.assertEqual("txn-a", results[0].transaction_id)

    def test_get_authentication_logs_combined_filters(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u2", realm="r1")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res2", uid="u1", realm="r1")

        results = get_authentication_logs(resolver="res1", uid="u1")
        self.assertEqual(1, len(results))
        self.assertEqual("res1", results[0].resolver)
        self.assertEqual("u1", results[0].uid)

    def test_get_authentication_logs_no_match_returns_empty(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1")

        results = get_authentication_logs(resolver="nonexistent")
        self.assertEqual([], results)

    def test_get_authentication_logs_timestamp_filters(self):
        from unittest.mock import patch

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        past = now - timedelta(hours=2)
        future = now + timedelta(hours=2)

        with patch('privacyidea.models.utils.datetime') as mock_dt:
            mock_dt.now.return_value.replace.return_value = past
            id1 = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1")

        with patch('privacyidea.models.utils.datetime') as mock_dt:
            mock_dt.now.return_value.replace.return_value = future
            id2 = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u2", realm="r1")

        # only the past entry
        results = get_authentication_logs(end_timestamp=now)
        self.assertEqual(1, len(results))
        self.assertEqual(id1, results[0].id)

        # only the future entry
        results = get_authentication_logs(start_timestamp=now)
        self.assertEqual(1, len(results))
        self.assertEqual(id2, results[0].id)

        # both entries
        results = get_authentication_logs(start_timestamp=past, end_timestamp=future)
        self.assertEqual(2, len(results))

    def test_create_user_unknown_event(self):
        event_id = log_authentication_event(event_type=AuthEventType.USER_UNKNOWN, source_ip="10.0.0.1")

        entry = get_authentication_log_event(event_id)
        assert entry is not None
        self.assertEqual(AuthEventType.USER_UNKNOWN, entry.event_type)
        self.assertIsNone(entry.resolver)
        self.assertIsNone(entry.uid)
        self.assertIsNone(entry.realm)
        self.assertIsNone(entry.username)
        self.assertEqual("10.0.0.1", entry.source_ip)

    def test_cleanup_removes_old_entries(self):
        from unittest.mock import patch

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        old_ts = now - timedelta(days=30)
        recent_ts = now - timedelta(hours=1)

        with patch('privacyidea.models.utils.datetime') as mock_dt:
            mock_dt.now.return_value.replace.return_value = old_ts
            old_id = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1")

        with patch('privacyidea.models.utils.datetime') as mock_dt:
            mock_dt.now.return_value.replace.return_value = recent_ts
            recent_id = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u2", realm="r1")

        cutoff = now - timedelta(days=7)
        deleted = cleanup_authentication_log(older_than=cutoff)

        self.assertEqual(1, deleted)
        self.assertIsNone(get_authentication_log_event(old_id))
        self.assertIsNotNone(get_authentication_log_event(recent_id))

    def test_cleanup_returns_zero_when_nothing_to_delete(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1")

        future_cutoff = datetime(2000, 1, 1)
        deleted = cleanup_authentication_log(older_than=future_cutoff)

        self.assertEqual(0, deleted)

    def test_cleanup_accepts_timezone_aware_cutoff(self):
        # The timestamp column is naive UTC; a timezone-aware cutoff must be normalized to UTC, not rejected or
        # mis-compared. An entry now (naive UTC) must survive a cutoff of "one hour ago" expressed in a +02:00 zone.
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1")
        tz = timezone(timedelta(hours=2))
        cutoff_aware = datetime.now(tz) - timedelta(hours=1)
        self.assertEqual(0, cleanup_authentication_log(older_than=cutoff_aware))
        # And a far-future aware cutoff deletes the entry.
        self.assertEqual(1, cleanup_authentication_log(older_than=datetime.now(tz) + timedelta(days=1)))

    def test_aware_timestamp_is_utc(self):
        # The column is stored naive (UTC); aware_timestamp re-attaches the UTC tzinfo on read.
        event_id = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1",
                                            realm="r1")
        entry = get_authentication_log_event(event_id)
        assert entry is not None
        self.assertIsNone(entry.timestamp.tzinfo)
        self.assertEqual(timezone.utc, entry.aware_timestamp.tzinfo)
        self.assertEqual(entry.timestamp, entry.aware_timestamp.replace(tzinfo=None))

    def test_failed_write_is_swallowed_and_not_persisted(self):
        # event_type is NOT NULL, so passing None makes the insert fail at flush. The failure must be swallowed
        # (return None, no exception) and no row must be written.
        from privacyidea.models import db

        event_id = log_authentication_event(event_type=None, resolver="res1", uid="u1", realm="r1")
        db.session.commit()

        self.assertIsNone(event_id)
        self.assertEqual([], get_authentication_logs())

    def test_failed_write_preserves_prior_pending_write(self):
        # The insert runs inside a SAVEPOINT, so a failing entry must roll back only itself and leave an earlier,
        # still-uncommitted write of the same session intact.
        from privacyidea.models import db
        from privacyidea.models.authentication_log import AuthenticationLog

        # A prior write that is pending but not yet committed.
        db.session.add(AuthenticationLog(event_type=AuthEventType.LOGIN_SUCCESS, resolver="prior"))

        # A failing auth-log write (event_type is NOT NULL).
        event_id = log_authentication_event(event_type=None, resolver="failing", uid="u1", realm="r1")
        self.assertIsNone(event_id)

        # The prior pending write survived the savepoint rollback and was committed; the failing one was not written.
        results = get_authentication_logs()
        self.assertEqual(1, len(results))
        self.assertEqual("prior", results[0].resolver)

    def test_values_are_truncated_to_column_length(self):
        from privacyidea.models import authentication_log_column_length

        # A value longer than its column is truncated instead of overflowing the column on insert. Cover a
        # size-constrained indexed column (resolver) and the generously-sized free columns (client_label, serial,
        # which hold a raw User-Agent and a comma-joined serial list).
        def over(column):
            return "X" * (authentication_log_column_length[column] + 50)

        event_id = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver=over("resolver"),
                                            uid="u1", realm="r1", username=over("username"),
                                            client_label=over("client_label"), serial=over("serial"))
        entry = get_authentication_log_event(event_id)
        assert entry is not None
        self.assertEqual("X" * authentication_log_column_length["resolver"], entry.resolver)
        self.assertEqual("X" * authentication_log_column_length["username"], entry.username)
        self.assertEqual("X" * authentication_log_column_length["client_label"], entry.client_label)
        self.assertEqual("X" * authentication_log_column_length["serial"], entry.serial)
