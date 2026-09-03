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
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import mock
from sqlalchemy import event
from sqlalchemy.exc import InvalidRequestError

from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType
from privacyidea.lib.conditional_access.authentication_log import (
    AuthenticationLogVisibilityScope,
    AuthLogUserRole,
    PendingAuthEvent,
    cleanup_authentication_log,
    delete_authentication_log_event,
    delete_authentication_logs,
    get_authentication_log_event,
    MAX_STATISTICS_BINS,
    get_authentication_log_statistics,
    get_authentication_logs,
    get_authentication_logs_paginate,
    log_authentication_event,
    update_authentication_events,
    write_authentication_events,
)
from privacyidea.lib.conditional_access.engine import count_user_attempts, count_user_events
from privacyidea.lib.conditional_access.outcome_log import get_outcomes, record_outcomes
from privacyidea.lib.conditional_access.session import get_ca_session
from privacyidea.lib.error import ParameterError
from privacyidea.models import AuthenticationLog, ConditionalAccessOutcome, db, authentication_log_column_length
from privacyidea.models.utils import utc_now

from .base import MyTestCase


@contextmanager
def statements_against(table: str):
    """Collect the SQL statements executed against *table* while the block runs."""
    seen: list[str] = []

    def listener(conn, cursor, statement, parameters, context, executemany):
        if table in statement:
            seen.append(statement)

    event.listen(db.engine, "before_cursor_execute", listener)
    try:
        yield seen
    finally:
        event.remove(db.engine, "before_cursor_execute", listener)


class AuthenticationLogTestCase(MyTestCase):

    def tearDown(self):
        from privacyidea.models import db
        from privacyidea.models.authentication_log import AuthenticationLog
        db.session.query(AuthenticationLog).delete()
        db.session.commit()

        super().tearDown()

    def test_create_required_fields_only(self):
        event_id = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="user1",
                                            realm="realm1")
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
        event_id = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="user1",
                                            realm="realm1")
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

    def test_get_authentication_logs_filter_by_event_type_list(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1")
        log_authentication_event(event_type=AuthEventType.MFA_FAIL, resolver="res1", uid="u1", realm="r1")
        log_authentication_event(event_type=AuthEventType.PIN_FAIL, resolver="res1", uid="u1", realm="r1")

        results = get_authentication_logs(event_type=[AuthEventType.MFA_FAIL, AuthEventType.PIN_FAIL])
        self.assertEqual(2, len(results))
        self.assertSetEqual({AuthEventType.MFA_FAIL, AuthEventType.PIN_FAIL},
                            {entry.event_type for entry in results})

    def test_get_authentication_logs_filter_by_serial_wildcard(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1",
                                 serial="TOTP001")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1",
                                 serial="TOTP002")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1",
                                 serial="HOTP001")

        results = get_authentication_logs(serial="TOTP*")
        self.assertSetEqual({"TOTP001", "TOTP002"}, {entry.serial for entry in results})

    def test_get_authentication_logs_wildcard_escapes_like_specials(self):
        # Only '*' is a wildcard; the SQL LIKE specials '_' and '%' must match literally.
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1",
                                 serial="A_B")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1",
                                 serial="AXB")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1",
                                 serial="50%OFF")

        # 'A_*' must match only the literal "A_..." entry, not "AXB" (which an unescaped '_' wildcard would match)
        self.assertSetEqual({"A_B"}, {entry.serial for entry in get_authentication_logs(serial="A_*")})
        # '%' is literal too
        self.assertSetEqual({"50%OFF"}, {entry.serial for entry in get_authentication_logs(serial="50%*")})

    def test_get_authentication_logs_event_type_wildcard_underscore_literal(self):
        log_authentication_event(event_type=AuthEventType.MFA_FAIL, resolver="res1", uid="u1", realm="r1")
        log_authentication_event(event_type=AuthEventType.PIN_FAIL, resolver="res1", uid="u1", realm="r1")

        # the '_' in the pattern is literal, so 'MFA_*' matches MFA_FAIL but not PIN_FAIL
        results = get_authentication_logs(event_type="MFA_*")
        self.assertListEqual([AuthEventType.MFA_FAIL], [entry.event_type for entry in results])

    def test_get_authentication_logs_filter_mixed_exact_and_wildcard(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1",
                                 serial="TOTP001")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1",
                                 serial="HOTP001")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1",
                                 serial="YUBI999")

        # one exact value (batched into IN) plus one wildcard pattern (LIKE), OR'd together
        results = get_authentication_logs(serial=["HOTP001", "TOTP*"])
        self.assertSetEqual({"TOTP001", "HOTP001"}, {entry.serial for entry in results})

    def test_get_authentication_logs_filter_by_user_role(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1",
                                 username="alice", user_role=AuthLogUserRole.USER)
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u2", realm="r1",
                                 username="iadmin", user_role=AuthLogUserRole.ADMIN_INTERNAL)
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u3", realm="r1",
                                 username="eadmin", user_role=AuthLogUserRole.ADMIN_EXTERNAL)

        self.assertEqual(1, get_authentication_logs_paginate(user_role=AuthLogUserRole.USER).count)
        self.assertEqual(1, get_authentication_logs_paginate(user_role=AuthLogUserRole.ADMIN_INTERNAL).count)
        # The shared 'admin-' prefix lets a single wildcard match either admin kind.
        self.assertEqual({AuthLogUserRole.ADMIN_INTERNAL, AuthLogUserRole.ADMIN_EXTERNAL},
                         {entry.user_role for entry in get_authentication_logs_paginate(user_role="admin*").auth_logs})

    def test_get_authentication_logs_case_insensitive_flag_enforces_insensitive_match(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1",
                                 username="Alice", serial="TOK1")

        # Every string column uses a case-sensitive collation on every backend, so matching is case-sensitive unless
        # case_insensitive is set; this holds for a non-boundary column (serial) too, confirming the behaviour is
        # uniform across columns.
        self.assertEqual(0, get_authentication_logs_paginate(username="alice").count)
        self.assertEqual(1, get_authentication_logs_paginate(username="alice", case_insensitive=True).count)
        self.assertEqual(1, get_authentication_logs_paginate(username="Alice").count)
        self.assertEqual(0, get_authentication_logs_paginate(serial="tok1").count)
        self.assertEqual(1, get_authentication_logs_paginate(serial="tok1", case_insensitive=True).count)

    def test_get_authentication_logs_wildcard_is_always_case_insensitive(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1",
                                 serial="TOTP001")

        # A wildcard match ignores case regardless of the case_insensitive flag.
        self.assertEqual(1, get_authentication_logs_paginate(serial="totp*").count)
        self.assertEqual(1, get_authentication_logs_paginate(serial="totp*", case_insensitive=True).count)

    def test_get_authentication_logs_filter_by_serial(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1",
                                 serial="TOK001")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1",
                                 serial="TOK002")

        results = get_authentication_logs(serial="TOK001")
        self.assertEqual(1, len(results))
        self.assertEqual("TOK001", results[0].serial)

    def test_get_authentication_logs_filter_by_source_ip(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1",
                                 source_ip="10.0.0.1")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1",
                                 source_ip="10.0.0.2")

        results = get_authentication_logs(source_ip="10.0.0.1")
        self.assertEqual(1, len(results))
        self.assertEqual("10.0.0.1", results[0].source_ip)

    def test_get_authentication_logs_filter_by_client_label(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1",
                                 client_label="vpn")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1",
                                 client_label="webui")

        results = get_authentication_logs(client_label="vpn")
        self.assertEqual(1, len(results))
        self.assertEqual("vpn", results[0].client_label)

    def test_get_authentication_logs_filter_by_peer_ip(self):
        # The peer is the second pivot: "what came from this machine", whatever it claimed to forward for.
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1",
                                 source_ip="203.0.113.5", peer_ip="10.0.0.17")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1",
                                 source_ip="203.0.113.6", peer_ip="10.0.0.18")
        # Outside the "10.0.0.*" wildcard, so it must not appear in that result.
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1",
                                 source_ip="203.0.113.7", peer_ip="192.168.1.1")

        results = get_authentication_logs(peer_ip="10.0.0.17")
        self.assertEqual(1, len(results))
        self.assertEqual("203.0.113.5", results[0].source_ip)
        self.assertSetEqual({"203.0.113.5", "203.0.113.6"},
                            {entry.source_ip for entry in get_authentication_logs(peer_ip="10.0.0.*")})

    def test_get_authentication_logs_filter_by_source_ip_source(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1",
                                 source_ip_source="X_FORWARDED_FOR")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1",
                                 source_ip_source="REMOTE_ADDR")

        results = get_authentication_logs(source_ip_source="X_FORWARDED_FOR")
        self.assertEqual(1, len(results))
        self.assertEqual(2, len(get_authentication_logs(
            source_ip_source=["X_FORWARDED_FOR", "REMOTE_ADDR"])))

    def test_get_authentication_logs_filter_by_client_label_source(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1",
                                 client_label="myapp", client_label_source="client_id")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="r1",
                                 client_label="Mozilla/5.0", client_label_source="user_agent")

        results = get_authentication_logs(client_label_source="client_id")
        self.assertEqual(1, len(results))
        self.assertEqual("myapp", results[0].client_label)

    def test_get_authentication_logs_filter_by_transaction_id(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, transaction_id="txn-a",
                                 resolver="res1", uid="u1", realm="r1")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, transaction_id="txn-b",
                                 resolver="res1", uid="u1", realm="r1")

        results = get_authentication_logs(transaction_id="txn-a")
        self.assertEqual(1, len(results))
        self.assertEqual("txn-a", results[0].transaction_id)

    def test_get_authentication_logs_filter_by_attempt_id(self):
        # Two requests of the same attempt share an attempt_id; a third belongs to another attempt.
        log_authentication_event(event_type=AuthEventType.CHALLENGE_TRIGGERED, attempt_id="att-a",
                                 resolver="res1", uid="u1", realm="r1")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, attempt_id="att-a",
                                 resolver="res1", uid="u1", realm="r1")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, attempt_id="att-b",
                                 resolver="res1", uid="u1", realm="r1")

        results = get_authentication_logs(attempt_id="att-a")
        self.assertEqual(2, len(results))
        self.assertSetEqual({"att-a"}, {entry.attempt_id for entry in results})

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
            id1 = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1",
                                           realm="r1")

        with patch('privacyidea.models.utils.datetime') as mock_dt:
            mock_dt.now.return_value.replace.return_value = future
            id2 = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u2",
                                           realm="r1")

        # only the past entry
        results = get_authentication_logs(end_time=now)
        self.assertEqual(1, len(results))
        self.assertEqual(id1, results[0].id)

        # only the future entry
        results = get_authentication_logs(start_time=now)
        self.assertEqual(1, len(results))
        self.assertEqual(id2, results[0].id)

        # both entries
        results = get_authentication_logs(start_time=past, end_time=future)
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
            old_id = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1",
                                              realm="r1")

        with patch('privacyidea.models.utils.datetime') as mock_dt:
            mock_dt.now.return_value.replace.return_value = recent_ts
            recent_id = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u2",
                                                 realm="r1")

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
        # The timestamp column stores naive UTC, so a timezone-aware cutoff must be normalized to UTC rather than
        # rejected or mis-compared.
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
        # event_type is NOT NULL, so passing None fails the insert at flush; the failure is swallowed (returns None, no
        # exception) and no row is written.
        from privacyidea.models import db

        event_id = log_authentication_event(event_type=None, resolver="res1", uid="u1", realm="r1")
        db.session.commit()

        self.assertIsNone(event_id)
        self.assertEqual([], get_authentication_logs())

    def test_failed_write_leaves_prior_pending_write_pending(self):
        # The insert runs on the conditional-access session, so a failing entry neither rolls back nor commits an
        # earlier, still-uncommitted write on the request session.
        from privacyidea.models import db
        from privacyidea.models.authentication_log import AuthenticationLog

        # A prior write that is pending but not yet committed.
        prior = AuthenticationLog(event_type=AuthEventType.LOGIN_SUCCESS, resolver="prior")
        db.session.add(prior)

        # A failing auth-log write (event_type is NOT NULL).
        event_id = log_authentication_event(event_type=None, resolver="failing", uid="u1", realm="r1")
        self.assertIsNone(event_id)

        # The prior write is untouched: still pending, so neither it nor the failing entry is in the log yet.
        self.assertIn(prior, db.session.new)
        self.assertListEqual([], get_authentication_logs())

        # It is still the request session's to commit, and only its own row lands.
        db.session.commit()
        results = get_authentication_logs()
        self.assertEqual(1, len(results))
        self.assertEqual("prior", results[0].resolver)

    def test_values_are_truncated_to_column_length(self):
        # A value longer than its column is truncated on insert rather than overflowing it; this covers a
        # size-constrained indexed column (resolver) and generously-sized free columns (client_label, holding a raw
        # User-Agent, and serial, holding a comma-joined list).
        def over(column):
            return "X" * (authentication_log_column_length[column] + 50)

        event_id = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver=over("resolver"),
                                            uid="u1", realm="r1", username=over("username"),
                                            client_label=over("client_label"), serial=over("serial"),
                                            transaction_id=over("transaction_id"))
        entry = get_authentication_log_event(event_id)
        assert entry is not None
        self.assertEqual("X" * authentication_log_column_length["resolver"], entry.resolver)
        self.assertEqual("X" * authentication_log_column_length["username"], entry.username)
        self.assertEqual("X" * authentication_log_column_length["client_label"], entry.client_label)
        self.assertEqual("X" * authentication_log_column_length["serial"], entry.serial)
        self.assertEqual("X" * authentication_log_column_length["transaction_id"],
                         entry.transaction_id)

    def test_overflow_is_preserved_in_other_info(self):
        # The part of a value that does not fit the column is preserved as the cut-off remainder under
        # other_info["truncated"][column] instead of being lost.
        max_resolver = authentication_log_column_length["resolver"]
        event_id = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS,
                                            resolver="R" * max_resolver + "OVERFLOW")
        entry = get_authentication_log_event(event_id)
        assert entry is not None
        self.assertEqual("R" * max_resolver, entry.resolver)
        self.assertEqual({"truncated": {"resolver": "OVERFLOW"}}, entry.other_info)

    def test_overflow_merges_with_caller_other_info(self):
        # Overflow is folded into the caller's other_info under "truncated" without clobbering the caller's own keys.
        max_resolver = authentication_log_column_length["resolver"]
        event_id = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS,
                                            resolver="R" * max_resolver + "TAIL",
                                            other_info={"reason": "policy"})
        entry = get_authentication_log_event(event_id)
        assert entry is not None
        self.assertEqual({"reason": "policy", "truncated": {"resolver": "TAIL"}}, entry.other_info)

    def test_no_overflow_leaves_other_info_untouched(self):
        # Without truncation, other_info is left exactly as the caller passed it (no empty "truncated" key added).
        event_id = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1",
                                            other_info={"reason": "policy"})
        entry = get_authentication_log_event(event_id)
        assert entry is not None
        self.assertEqual({"reason": "policy"}, entry.other_info)

    def test_serial_overflow_splits_on_separator(self):
        # A comma-joined serial list is cut on a comma boundary so whole serials remain filterable in the column, with
        # the dropped serials preserved whole in the overflow; here the last serial straddles the column limit.
        max_serial = authentication_log_column_length["serial"]
        head = "S" * (max_serial - 4)  # leaves room for ",AAA" but not the next serial
        serial = f"{head},AAA,BBBBBBBBBB"
        event_id = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, serial=serial)
        entry = get_authentication_log_event(event_id)
        assert entry is not None
        self.assertEqual(f"{head},AAA", entry.serial)
        self.assertEqual({"truncated": {"serial": "BBBBBBBBBB"}}, entry.other_info)

    def test_serial_overflow_falls_back_to_char_split_when_no_separator_fits(self):
        # A single serial longer than the column has no comma boundary to cut on, so it falls back to a character split
        # rather than dropping the value entirely.
        max_serial = authentication_log_column_length["serial"]
        serial = "S" * (max_serial + 5)
        event_id = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, serial=serial)
        entry = get_authentication_log_event(event_id)
        assert entry is not None
        self.assertEqual("S" * max_serial, entry.serial)
        self.assertEqual({"truncated": {"serial": "SSSSS"}}, entry.other_info)

    def test_amending_a_written_event_preserves_serial_overflow(self):
        # An amended row truncates the same way as an insert and folds the serial overflow into the entry's existing
        # other_info.
        event = PendingAuthEvent(event_type=AuthEventType.LOGIN_SUCCESS, serial="TOK001")
        write_authentication_events([event])
        max_serial = authentication_log_column_length["serial"]
        head = "S" * (max_serial - 4)

        event.event_type = AuthEventType.ENROLLMENT_TRIGGERED
        event.serial = f"{head},AAA,BBBBBBBBBB"
        update_authentication_events([event])

        entry = get_authentication_log_event(event.row_id)
        assert entry is not None
        self.assertEqual(f"{head},AAA", entry.serial)
        self.assertEqual({"truncated": {"serial": "BBBBBBBBBB"}}, entry.other_info)

    def test_amending_only_the_event_type_keeps_the_serial(self):
        # Amending only the classification leaves the rest of the row alone, e.g. the authorized=deny post-policy
        # corrects a successful login to NOT_AUTHORIZED without touching the serial.
        event = PendingAuthEvent(event_type=AuthEventType.LOGIN_SUCCESS, serial="TOK001")
        write_authentication_events([event])

        event.event_type = AuthEventType.NOT_AUTHORIZED
        update_authentication_events([event])

        entry = get_authentication_log_event(event.row_id)
        assert entry is not None
        self.assertEqual(AuthEventType.NOT_AUTHORIZED, entry.event_type)
        self.assertEqual("TOK001", entry.serial)

    def test_amending_a_written_event_leaves_other_info_alone(self):
        event = PendingAuthEvent(event_type=AuthEventType.LOGIN_SUCCESS, other_info={"reason": "before"})
        write_authentication_events([event])

        event.event_type = AuthEventType.NOT_AUTHORIZED
        event.other_info = {"reason": "after", "note": "updated"}
        update_authentication_events([event])

        entry = get_authentication_log_event(event.row_id)
        self.assertIsNotNone(entry)
        self.assertEqual(AuthEventType.NOT_AUTHORIZED, entry.event_type)
        self.assertEqual({"reason": "after", "note": "updated"}, entry.other_info)

    def test_outcomes_on_an_event_are_not_row_content(self):
        # An event holds its conditional-access outcomes until the row id they attach to exists; since outcomes are not
        # columns, setting them on an already-written event must not mark it changed and trigger an UPDATE.
        event = PendingAuthEvent(event_type=AuthEventType.LOGIN_SUCCESS)
        write_authentication_events([event])
        self.assertFalse(event.changed)

        event.outcomes = ["an outcome"]
        self.assertFalse(event.changed)
        event.outcomes.append("another")
        self.assertFalse(event.changed)



class AuthenticationLogDBTestCase(MyTestCase):

    def tearDown(self):
        from privacyidea.models import db
        from privacyidea.models.authentication_log import AuthenticationLog
        db.session.query(AuthenticationLog).delete()
        db.session.commit()

        super().tearDown()

    def test_get_as_dict(self):
        log_time_utc_naive = datetime(2026, 6, 1, 5, 23, 21, 1, tzinfo=None)
        with mock.patch("privacyidea.models.utils.datetime") as datetime_mock:
            datetime_mock.now.return_value = log_time_utc_naive
            event_id = log_authentication_event(
                event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="user1", realm="realm1",
                username="testuser", user_role=AuthLogUserRole.ADMIN_EXTERNAL, source_ip="192.168.1.1",
                peer_ip="10.0.0.5", source_ip_source="X_FORWARDED_FOR",
                client_label="vpn", client_label_source="client_id",
                ip_chain=[{"ip": "10.0.0.5", "source": "REMOTE_ADDR"},
                          {"ip": "192.168.1.1", "source": "X_FORWARDED_FOR", "effective": True}],
                serial="TOK001", transaction_id="txn-123",
                attempt_id="attempt-123",
                other_info={"key": "value"}
            )

        entry = get_authentication_log_event(event_id)
        auth_log_dict = entry.to_dict()

        expected_keys = {"id", "resolver", "uid", "realm", "username", "user_role", "event_type", "timestamp",
                         "source_ip", "peer_ip", "source_ip_source", "client_label", "client_label_source",
                         "ip_chain", "serial", "transaction_id",
                         "attempt_id", "other_info"}
        self.assertSetEqual(expected_keys, set(auth_log_dict.keys()))
        self.assertEqual(event_id, auth_log_dict["id"])
        self.assertEqual("res1", auth_log_dict["resolver"])
        self.assertEqual("user1", auth_log_dict["uid"])
        self.assertEqual("realm1", auth_log_dict["realm"])
        self.assertEqual("testuser", auth_log_dict["username"])
        self.assertEqual(AuthLogUserRole.ADMIN_EXTERNAL, auth_log_dict["user_role"])
        self.assertEqual(AuthEventType.LOGIN_SUCCESS, auth_log_dict["event_type"])
        log_time_tz_aware = log_time_utc_naive.replace(tzinfo=timezone.utc)
        self.assertEqual(log_time_tz_aware.isoformat(), auth_log_dict["timestamp"])
        self.assertEqual("192.168.1.1", auth_log_dict["source_ip"])
        self.assertEqual("10.0.0.5", auth_log_dict["peer_ip"])
        self.assertEqual("X_FORWARDED_FOR", auth_log_dict["source_ip_source"])
        self.assertEqual("vpn", auth_log_dict["client_label"])
        self.assertEqual("client_id", auth_log_dict["client_label_source"])
        self.assertEqual([{"ip": "10.0.0.5", "source": "REMOTE_ADDR"},
                          {"ip": "192.168.1.1", "source": "X_FORWARDED_FOR", "effective": True}],
                         auth_log_dict["ip_chain"])
        self.assertEqual("TOK001", auth_log_dict["serial"])
        self.assertEqual("txn-123", auth_log_dict["transaction_id"])
        self.assertEqual("attempt-123", auth_log_dict["attempt_id"])
        self.assertEqual({"key": "value"}, auth_log_dict["other_info"])


class AuthenticationLogPaginateTestCase(MyTestCase):

    def tearDown(self):
        from privacyidea.models import ConditionalAccessOutcome, db
        from privacyidea.models.authentication_log import AuthenticationLog
        # Children first: nothing cascades on SQLite.
        db.session.query(ConditionalAccessOutcome).delete()
        db.session.query(AuthenticationLog).delete()
        db.session.commit()
        super().tearDown()

    @staticmethod
    def _create(count, **kwargs):
        return [log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid=f"u{i}",
                                         realm="realm1", **kwargs) for i in range(count)]

    def test_pagination_metadata_across_pages(self):
        self._create(5)
        first = get_authentication_logs_paginate(page=1, page_size=2)
        self.assertEqual(5, first.count)
        self.assertEqual(2, len(first.auth_logs))
        self.assertEqual(1, first.current)
        self.assertIsNone(first.prev)
        self.assertEqual(2, first.next)

        last = get_authentication_logs_paginate(page=3, page_size=2)
        self.assertEqual(1, len(last.auth_logs))
        self.assertEqual(2, last.prev)
        self.assertIsNone(last.next)

    def test_default_sort_is_newest_first(self):
        ids = self._create(3)
        page = get_authentication_logs_paginate()
        self.assertEqual(sorted(ids, reverse=True), [entry.id for entry in page.auth_logs])

    def test_sort_ascending(self):
        ids = self._create(3)
        page = get_authentication_logs_paginate(sort_order="asc")
        self.assertEqual(sorted(ids), [entry.id for entry in page.auth_logs])

    def test_unknown_sort_falls_back_to_timestamp(self):
        self._create(2)
        page = get_authentication_logs_paginate(sort_column="not_a_column")
        self.assertEqual(2, page.count)

    def test_filters_are_applied(self):
        self._create(2, serial="TOK_A")
        self._create(3, serial="TOK_B")
        page = get_authentication_logs_paginate(serial="TOK_A")
        self.assertEqual(2, page.count)
        self.assertTrue(all(entry.serial == "TOK_A" for entry in page.auth_logs))

    def test_visibility_scope_by_realm_excludes_other_and_null_realms(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="realm1")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u2", realm="realm2")
        log_authentication_event(event_type=AuthEventType.USER_UNKNOWN)  # no realm
        # None means unrestricted
        self.assertEqual(3, get_authentication_logs_paginate().count)
        # A realm-only scope hides realm2 and the null-realm row
        scope = AuthenticationLogVisibilityScope(realms=["realm1"], resolvers=[], usernames=[])
        restricted = get_authentication_logs_paginate(visibility_scopes=[scope])
        self.assertEqual(1, restricted.count)
        self.assertEqual("realm1", restricted.auth_logs[0].realm)

    def test_visibility_scope_by_resolver(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="realm1")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res2", uid="u2", realm="realm1")
        scope = AuthenticationLogVisibilityScope(realms=[], resolvers=["res1"], usernames=[])
        restricted = get_authentication_logs_paginate(visibility_scopes=[scope])
        self.assertEqual(1, restricted.count)
        self.assertEqual("res1", restricted.auth_logs[0].resolver)

    def test_visibility_scope_dimensions_are_anded(self):
        # A single scope with realm + resolver matches only entries satisfying both.
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="realm1")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res2", uid="u2", realm="realm1")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u3", realm="realm2")
        scope = AuthenticationLogVisibilityScope(realms=["realm1"], resolvers=["res1"], usernames=[])
        restricted = get_authentication_logs_paginate(visibility_scopes=[scope])
        self.assertEqual(1, restricted.count)
        self.assertEqual(("res1", "realm1"), (restricted.auth_logs[0].resolver, restricted.auth_logs[0].realm))

    def test_visibility_scopes_are_ored_across_policies(self):
        # Two scopes (from two policies) act as a union: realm1 OR resolver res2.
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="resA", uid="u1", realm="realm1")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res2", uid="u2", realm="realm9")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="resZ", uid="u3", realm="realm9")
        scopes = [AuthenticationLogVisibilityScope(realms=["realm1"], resolvers=[], usernames=[]),
                  AuthenticationLogVisibilityScope(realms=[], resolvers=["res2"], usernames=[])]
        restricted = get_authentication_logs_paginate(visibility_scopes=scopes)
        self.assertEqual(2, restricted.count)

    def test_visibility_scope_resolver_matches_case_sensitively(self):
        # Boundary columns are pinned to a case-sensitive collation on every backend (utf8mb4_bin on MySQL/MariaDB;
        # case-sensitive by default on SQLite, Postgres and Oracle), so a resolver scope never leaks a case-variant
        # resolver -- the boundary fails closed.
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="realm1")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="RES1", uid="u2", realm="realm1")
        scope = AuthenticationLogVisibilityScope(realms=[], resolvers=["res1"], usernames=[])
        restricted = get_authentication_logs_paginate(visibility_scopes=[scope])
        self.assertEqual(1, restricted.count)
        self.assertEqual("res1", restricted.auth_logs[0].resolver)

    def test_visibility_scope_username_matches_case_sensitively_by_default(self):
        # Without the policy's user_case_insensitive option, an admin scoped to "alice" must not see "Alice", and the
        # case-sensitive collation guarantees this holds on every backend.
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", realm="realm1",
                                 username="alice")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", realm="realm1",
                                 username="Alice")
        scope = AuthenticationLogVisibilityScope(realms=[], resolvers=[], usernames=["alice"])
        restricted = get_authentication_logs_paginate(visibility_scopes=[scope])
        self.assertEqual(1, restricted.count)
        self.assertEqual("alice", restricted.auth_logs[0].username)

    def test_visibility_scope_username_case_insensitive_when_policy_set(self):
        # With user_case_insensitive set on the scope, the username dimension is forced case-insensitive via LOWER() on
        # both sides, so the admin scoped to "alice" also sees the "Alice" entry.
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", realm="realm1",
                                 username="alice")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", realm="realm1",
                                 username="Alice")
        scope = AuthenticationLogVisibilityScope(realms=[], resolvers=[], usernames=["alice"],
                                                 username_case_insensitive=True)
        restricted = get_authentication_logs_paginate(visibility_scopes=[scope])
        self.assertEqual(2, restricted.count)

    def test_visibility_scope_user_roles_dimension(self):
        # The user_roles dimension is AND-ed with the others, so a local admin's own entries are matched by username +
        # admin-internal and a same-named regular-user entry is excluded.
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, username="testadmin",
                                 user_role=AuthLogUserRole.ADMIN_INTERNAL)
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, realm="realm1", username="testadmin",
                                 user_role=AuthLogUserRole.USER)
        scope = AuthenticationLogVisibilityScope(realms=[], resolvers=[], usernames=["testadmin"],
                                                 user_roles=[str(AuthLogUserRole.ADMIN_INTERNAL)])
        restricted = get_authentication_logs_paginate(visibility_scopes=[scope])
        self.assertEqual(1, restricted.count)
        self.assertEqual(str(AuthLogUserRole.ADMIN_INTERNAL), restricted.auth_logs[0].user_role)

    def test_to_dict_shape_and_iso_timestamp(self):
        self._create(1)
        page_dict = get_authentication_logs_paginate().to_dict()
        self.assertEqual({"auth_logs", "count", "current", "prev", "next"}, set(page_dict.keys()))
        timestamp = page_dict["auth_logs"][0]["timestamp"]
        self.assertIsInstance(timestamp, str)
        datetime.fromisoformat(timestamp)  # parseable ISO 8601


class AuthenticationLogDeleteTestCase(MyTestCase):

    def tearDown(self):
        from privacyidea.models import ConditionalAccessOutcome, db
        from privacyidea.models.authentication_log import AuthenticationLog
        # Children first: nothing cascades on SQLite.
        db.session.query(ConditionalAccessOutcome).delete()
        db.session.query(AuthenticationLog).delete()
        db.session.commit()
        super().tearDown()

    def test_delete_by_filter_returns_count(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="realm1")
        log_authentication_event(event_type=AuthEventType.MFA_FAIL, resolver="res1", uid="u2", realm="realm1")
        deleted = delete_authentication_logs(event_type=AuthEventType.MFA_FAIL)
        self.assertEqual(1, deleted)
        remaining = get_authentication_logs()
        self.assertEqual(1, len(remaining))
        self.assertEqual(AuthEventType.LOGIN_SUCCESS, remaining[0].event_type)

    def test_delete_without_filter_raises(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="realm1")
        self.assertRaises(ParameterError, delete_authentication_logs)
        # nothing was deleted
        self.assertEqual(1, len(get_authentication_logs()))

    def test_delete_visibility_scope_excludes_other_and_null_realms(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="realm1")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u2", realm="realm2")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS)  # no realm
        # Deleting all LOGIN_SUCCESS while scoped to realm1 only removes the realm1 row.
        scope = AuthenticationLogVisibilityScope(realms=["realm1"], resolvers=[], usernames=[])
        deleted = delete_authentication_logs(event_type=AuthEventType.LOGIN_SUCCESS, visibility_scopes=[scope])
        self.assertEqual(1, deleted)
        remaining_realms = {entry.realm for entry in get_authentication_logs()}
        self.assertEqual({"realm2", None}, remaining_realms)


class AuthenticationLogOutcomeJoinTestCase(MyTestCase):
    """
    How the conditional-access outcomes of a request reach a reader: only through the paginated listing, in one batched
    query, and never on the authentication path (see the ``outcomes`` relationship and D11 of the design notes).
    """

    def tearDown(self):
        db.session.query(ConditionalAccessOutcome).delete()
        db.session.query(AuthenticationLog).delete()
        db.session.commit()
        super().tearDown()

    @staticmethod
    def _entry_with_outcomes(count: int = 1, **kwargs) -> int:
        """Write one authentication-log row plus *count* conditional-access outcomes, and return the row id."""
        event_id = log_authentication_event(event_type=AuthEventType.MFA_FAIL, resolver="res1", uid="u1",
                                            realm="realm1", **kwargs)
        record_outcomes([ConditionalAccessOutcome(action_type="LOCK_USER", policy_name="p",
                                                 threshold=3, event_count=3) for _ in range(count)], event_id)
        return event_id

    def test_the_page_carries_the_outcomes_of_each_entry(self):
        self._entry_with_outcomes(2)
        page = get_authentication_logs_paginate()

        entry = page.auth_logs[0]
        self.assertEqual(2, len(entry.outcomes))
        # to_dict of the *page* opts in, so a client sees them alongside the entry.
        self.assertEqual(2, len(page.to_dict()["auth_logs"][0]["conditional_access_outcomes"]))
        self.assertEqual("LOCK_USER", page.to_dict()["auth_logs"][0]["conditional_access_outcomes"][0]["action_type"])

    def test_an_entry_without_outcomes_carries_an_empty_list(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="realm1")
        page = get_authentication_logs_paginate()
        self.assertListEqual([], page.to_dict()["auth_logs"][0]["conditional_access_outcomes"])

    def test_the_outcomes_of_a_whole_page_cost_one_statement(self):
        # selectinload fetches a whole page's outcomes in one extra query regardless of page size; a lazy relationship
        # would pass every content assertion above while issuing one query per entry, so this asserts on statement count
        # rather than on the payload.
        for _ in range(5):
            self._entry_with_outcomes()

        with statements_against("conditional_access_outcome") as statements:
            page = get_authentication_logs_paginate(page_size=5)
            self.assertEqual(5, len(page.auth_logs))
        self.assertEqual(1, len(statements), statements)

    def test_the_unpaginated_query_does_not_load_the_outcomes(self):
        # get_authentication_logs is used by lib callers and tests, not the log view, so it must not pay for the join;
        # reading the relationship afterward is an error, not a silent query.
        self._entry_with_outcomes()

        with statements_against("conditional_access_outcome") as statements:
            entries = get_authentication_logs()
        self.assertListEqual([], statements)
        self.assertRaises(InvalidRequestError, lambda: entries[0].outcomes)

    def test_to_dict_of_a_single_entry_leaves_the_outcomes_out(self):
        # The default is off because the relationship raises: an entry loaded without its outcomes must not try to fetch
        # them while being serialized.
        event_id = self._entry_with_outcomes()
        entry = get_authentication_log_event(event_id)
        self.assertNotIn("conditional_access_outcomes", entry.to_dict())

    def test_counting_events_never_touches_the_outcome_table(self):
        # The engine's counting path fetches whole AuthenticationLog objects (PER_ATTEMPT), which is exactly where an
        # eagerly configured relationship would add a fan-out query per count.
        self._entry_with_outcomes()

        with statements_against("conditional_access_outcome") as statements:
            count_user_events("res1", "u1", "realm1", [str(AuthEventType.MFA_FAIL)], 3600)
            count_user_attempts("res1", "u1", "realm1", [str(AuthEventType.MFA_FAIL)], 3600)
        self.assertListEqual([], statements)

    def test_deleting_one_entry_takes_its_outcomes(self):
        kept = self._entry_with_outcomes()
        removed = self._entry_with_outcomes()

        delete_authentication_log_event(removed)

        self.assertListEqual([], list(get_outcomes(removed)))
        self.assertEqual(1, len(get_outcomes(kept)))

    def test_deleting_an_entry_as_an_object_takes_its_outcomes(self):
        # The cascade covers every caller that deletes an entry as an object, including the model's own
        # MethodsMixin.delete(), not only this module's delete function; without it, those paths would orphan the
        # outcomes on SQLite, which does not enforce foreign keys.
        kept = self._entry_with_outcomes()
        removed = self._entry_with_outcomes()

        # Loaded through db.session, because that is the session MethodsMixin.delete() commits on.
        AuthenticationLog.query.filter_by(id=removed).one().delete()

        self.assertListEqual([], list(get_outcomes(removed)))
        self.assertEqual(1, len(get_outcomes(kept)))

    def test_a_filtered_delete_takes_the_outcomes_with_it(self):
        removed = self._entry_with_outcomes(2, username="doomed")
        kept = self._entry_with_outcomes(username="spared")

        self.assertEqual(1, delete_authentication_logs(username="doomed"))

        self.assertEqual([], list(get_outcomes(removed)))
        self.assertEqual(1, len(get_outcomes(kept)))

    def test_retention_takes_the_outcomes_with_it(self):
        removed = self._entry_with_outcomes(2)
        # Age the row past the cutoff; its outcomes have no timestamp of their own, so they are matched through it.
        db.session.query(AuthenticationLog).filter_by(id=removed).update({"timestamp": utc_now() - timedelta(days=10)})
        db.session.commit()
        kept = self._entry_with_outcomes()

        self.assertEqual(1, cleanup_authentication_log(older_than=utc_now() - timedelta(days=1)))

        self.assertListEqual([], list(get_outcomes(removed)))
        self.assertEqual(1, len(get_outcomes(kept)))

    def test_retention_deletes_the_outcomes_in_chunks_too(self):
        # The chunked path is a different code path in delete_matching_rows; the children must follow it as well.
        removed = [self._entry_with_outcomes(2) for _ in range(3)]
        db.session.query(AuthenticationLog).filter(AuthenticationLog.id.in_(removed)).update(
            {"timestamp": utc_now() - timedelta(days=10)})
        db.session.commit()

        self.assertEqual(3, cleanup_authentication_log(older_than=utc_now() - timedelta(days=1), chunk_size=2))

        self.assertEqual(0, get_ca_session().query(ConditionalAccessOutcome).count())


class AuthenticationLogStatisticsTestCase(MyTestCase):
    """
    Attempt-level statistics over the authentication log: the reduction rule it shares with the conditional-access
    engine, the two places it deliberately diverges, and the bucketing.
    """

    window_start = datetime(2026, 3, 1, 0, 0, 0)
    window_end = window_start + timedelta(hours=24)

    def tearDown(self):
        db.session.query(AuthenticationLog).delete()
        db.session.commit()
        super().tearDown()

    def _log(self, event_type, at=None, attempt_id="attempt-1", **kwargs):
        """Write one entry at a fixed timestamp, since the column otherwise defaults to the real current time."""
        kwargs.setdefault("resolver", "res1")
        kwargs.setdefault("uid", "u1")
        kwargs.setdefault("realm", "r1")
        event_id = log_authentication_event(event_type=event_type, attempt_id=attempt_id, **kwargs)
        session = get_ca_session()
        session.get(AuthenticationLog, event_id).timestamp = at or (self.window_start + timedelta(hours=1))
        session.commit()
        return event_id

    def _statistics(self, **kwargs):
        kwargs.setdefault("start_time", self.window_start)
        kwargs.setdefault("end_time", self.window_end)
        kwargs.setdefault("bins", 4)
        return get_authentication_log_statistics(**kwargs)

    def _totals(self, statistics):
        return {series.event_type: series.total for series in statistics.events}

    def test_counts_attempts_not_rows(self):
        self._log(AuthEventType.CHALLENGE_TRIGGERED)
        self._log(AuthEventType.LOGIN_SUCCESS)

        self.assertDictEqual({str(AuthEventType.LOGIN_SUCCESS): 1}, self._totals(self._statistics()))

    def test_success_classifies_the_attempt_over_a_later_row(self):
        self._log(AuthEventType.LOGIN_SUCCESS)
        self._log(AuthEventType.CHALLENGE_ANSWERED_FAIL)

        self.assertDictEqual({str(AuthEventType.LOGIN_SUCCESS): 1}, self._totals(self._statistics()))

    def test_latest_row_classifies_an_unsuccessful_attempt(self):
        self._log(AuthEventType.CHALLENGE_ANSWERED_FAIL, attempt_id="in-progress")
        self._log(AuthEventType.CHALLENGE_CONTINUED, attempt_id="in-progress")
        self._log(AuthEventType.CHALLENGE_CONTINUED, attempt_id="failed")
        self._log(AuthEventType.CHALLENGE_ANSWERED_FAIL, attempt_id="failed")

        self.assertDictEqual({str(AuthEventType.CHALLENGE_CONTINUED): 1,
                              str(AuthEventType.CHALLENGE_ANSWERED_FAIL): 1},
                             self._totals(self._statistics()))

    def test_enforcement_row_classifies_the_attempt_it_ended(self):
        self._log(AuthEventType.CHALLENGE_TRIGGERED)
        self._log(AuthEventType.USER_LOCKED)

        totals = self._totals(self._statistics())

        # Dropping the enforcement row before the reduction would leave CHALLENGE_TRIGGERED as the representative and
        # report an attempt still in flight, when it was turned away.
        self.assertDictEqual({str(AuthEventType.USER_LOCKED): 1}, totals)

    def test_rows_without_attempt_id_count_individually(self):
        for _ in range(3):
            self._log(AuthEventType.PIN_FAIL, attempt_id=None)

        self.assertDictEqual({str(AuthEventType.PIN_FAIL): 3}, self._totals(self._statistics()))

    def test_agrees_with_the_engine_on_enforcement_free_attempts(self):
        self._log(AuthEventType.PIN_FAIL, attempt_id="a")
        self._log(AuthEventType.PIN_FAIL, attempt_id="a")
        self._log(AuthEventType.PIN_FAIL, attempt_id="b")
        self._log(AuthEventType.LOGIN_SUCCESS, attempt_id="b")
        self._log(AuthEventType.MFA_FAIL, attempt_id="c")

        totals = self._totals(self._statistics())
        for event_type in (AuthEventType.PIN_FAIL, AuthEventType.LOGIN_SUCCESS, AuthEventType.MFA_FAIL):
            self.assertEqual(count_user_attempts("res1", "u1", "r1", [event_type], 24 * 3600,
                                                 window_end=self.window_end),
                             totals.get(str(event_type), 0),
                             f"statistics and engine disagree on {event_type}")

    def test_buckets_by_the_representative_timestamp(self):
        self._log(AuthEventType.PIN_FAIL, at=self.window_start + timedelta(hours=1), attempt_id="a")
        self._log(AuthEventType.MFA_FAIL, at=self.window_start + timedelta(hours=13), attempt_id="b")

        statistics = self._statistics()

        self.assertListEqual([1, 0, 0, 0], next(s.counts for s in statistics.events
                                                if s.event_type == str(AuthEventType.PIN_FAIL)))
        self.assertListEqual([0, 0, 1, 0], next(s.counts for s in statistics.events
                                                if s.event_type == str(AuthEventType.MFA_FAIL)))

    def test_last_bin_includes_the_window_end(self):
        self._log(AuthEventType.PIN_FAIL, at=self.window_end)

        statistics = self._statistics()

        self.assertListEqual([0, 0, 0, 1], statistics.events[0].counts)

    def test_rows_outside_the_window_are_ignored(self):
        self._log(AuthEventType.PIN_FAIL, at=self.window_start - timedelta(minutes=1), attempt_id="before")
        self._log(AuthEventType.MFA_FAIL, at=self.window_end + timedelta(minutes=1), attempt_id="after")

        self.assertDictEqual({}, self._totals(self._statistics()))

    def test_filters_match_the_representative_not_any_row(self):
        self._log(AuthEventType.PIN_FAIL)
        self._log(AuthEventType.LOGIN_SUCCESS)

        self.assertDictEqual({str(AuthEventType.LOGIN_SUCCESS): 1},
                             self._totals(self._statistics(event_types=[str(AuthEventType.LOGIN_SUCCESS)])))
        self.assertDictEqual({}, self._totals(self._statistics(event_types=[str(AuthEventType.PIN_FAIL)])))

    def test_a_filter_narrows_the_attempts_reduced_but_not_their_rows(self):
        # The reduction only groups attempts with a matching row, or a filtered summary would make the database group
        # every row in the window first. What it must not do is reduce an attempt from its matching rows *alone*: this
        # attempt answered from a second address, so filtering by the first one has to exclude it (its representative
        # is the success from the other address) rather than report it as the failure its first row was.
        self._log(AuthEventType.MFA_FAIL, source_ip="10.0.0.1")
        self._log(AuthEventType.LOGIN_SUCCESS, source_ip="10.0.0.2")

        self.assertDictEqual({}, self._totals(self._statistics(source_ips=["10.0.0.1"])))
        self.assertDictEqual({str(AuthEventType.LOGIN_SUCCESS): 1},
                             self._totals(self._statistics(source_ips=["10.0.0.2"])))

    def test_a_visibility_scope_narrows_the_attempts_reduced_but_not_their_rows(self):
        # The same for the scope, whose dimensions exclude a NULL: the rejection that ended this attempt carries no
        # realm, so reducing the attempt from its in-scope row alone would report a challenge still in flight.
        self._log(AuthEventType.CHALLENGE_TRIGGERED, realm="visible")
        self._log(AuthEventType.USER_LOCKED, realm=None)

        scope = AuthenticationLogVisibilityScope(realms=["visible"], resolvers=[], usernames=[])

        self.assertDictEqual({}, self._totals(self._statistics(visibility_scopes=[scope])))

    def test_the_reduction_is_narrowed_by_attempt_only_when_something_filters(self):
        # A performance property no count can show: with a filter the reduction is restricted to the matching
        # attempts, and without one it is not wrapped at all, because summarising a whole deployment does have to
        # group every row of the window.
        self._log(AuthEventType.LOGIN_SUCCESS)

        with statements_against("authentication_log") as statements:
            self._statistics(usernames=["alice"])
        self.assertIn("attempt_id IN (SELECT", statements[-1])

        with statements_against("authentication_log") as statements:
            self._statistics()
        self.assertNotIn("attempt_id IN (SELECT", statements[-1])

    def test_visibility_scope_restricts_the_counts(self):
        self._log(AuthEventType.PIN_FAIL, realm="visible", attempt_id="a")
        self._log(AuthEventType.MFA_FAIL, realm="hidden", attempt_id="b")

        scope = AuthenticationLogVisibilityScope(realms=["visible"], resolvers=[], usernames=[])

        self.assertDictEqual({str(AuthEventType.PIN_FAIL): 1},
                             self._totals(self._statistics(visibility_scopes=[scope])))

    def test_series_carry_the_event_outcome(self):
        self._log(AuthEventType.LOGIN_SUCCESS, attempt_id="a")
        self._log(AuthEventType.PIN_FAIL, attempt_id="b")
        self._log(AuthEventType.CHALLENGE_TRIGGERED, attempt_id="c")

        outcomes = {series.event_type: series.outcome for series in self._statistics().events}

        self.assertDictEqual({str(AuthEventType.LOGIN_SUCCESS): "success",
                              str(AuthEventType.PIN_FAIL): "failure",
                              str(AuthEventType.CHALLENGE_TRIGGERED): "pending"}, outcomes)

    def test_series_are_ordered_by_descending_total(self):
        self._log(AuthEventType.LOGIN_SUCCESS, attempt_id="a")
        for index in range(3):
            self._log(AuthEventType.PIN_FAIL, attempt_id=f"fail-{index}")

        statistics = self._statistics()

        self.assertListEqual([str(AuthEventType.PIN_FAIL), str(AuthEventType.LOGIN_SUCCESS)],
                             [series.event_type for series in statistics.events])
        self.assertEqual(4, statistics.total)

    def test_rejects_an_empty_window(self):
        self.assertRaises(ParameterError, get_authentication_log_statistics,
                          start_time=self.window_end, end_time=self.window_start)
        self.assertRaises(ParameterError, get_authentication_log_statistics,
                          start_time=self.window_start, end_time=self.window_start)

    def test_rejects_an_out_of_range_bin_count(self):
        for bins in (0, -1, MAX_STATISTICS_BINS + 1):
            self.assertRaises(ParameterError, get_authentication_log_statistics,
                              start_time=self.window_start, end_time=self.window_end, bins=bins)

    def test_to_dict_shape(self):
        self._log(AuthEventType.PIN_FAIL)

        result = self._statistics().to_dict()

        self.assertEqual("2026-03-01T00:00:00+00:00", result["window"]["start_time"])
        self.assertEqual("2026-03-02T00:00:00+00:00", result["window"]["end_time"])
        self.assertEqual(1, result["window"]["total"])
        self.assertEqual(4, result["bins"]["count"])
        self.assertListEqual(["2026-03-01T00:00:00+00:00", "2026-03-01T06:00:00+00:00",
                              "2026-03-01T12:00:00+00:00", "2026-03-01T18:00:00+00:00"],
                             result["bins"]["starts"])
        self.assertListEqual([{"event_type": str(AuthEventType.PIN_FAIL), "outcome": "failure",
                               "counts": [1, 0, 0, 0], "total": 1}], result["events"])

    def test_rows_with_and_without_attempt_id_are_grouped_independently(self):
        self._log(AuthEventType.PIN_FAIL, attempt_id="shared")
        self._log(AuthEventType.PIN_FAIL, attempt_id="shared")
        self._log(AuthEventType.MFA_FAIL, attempt_id=None)
        self._log(AuthEventType.MFA_FAIL, attempt_id=None)

        self.assertDictEqual({str(AuthEventType.PIN_FAIL): 1, str(AuthEventType.MFA_FAIL): 2},
                             self._totals(self._statistics()))
