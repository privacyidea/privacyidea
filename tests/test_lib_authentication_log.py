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

import mock

from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType
from privacyidea.lib.conditional_access.authentication_log import (
    log_authentication_event,
    delete_authentication_log_event,
    reclassify_authentication_log_event,
    get_authentication_log_event,
    get_authentication_logs,
    get_authentication_logs_paginate,
    delete_authentication_logs,
    cleanup_authentication_log,
    AuthenticationLogVisibilityScope,
    AuthLogUserRole,
)
from privacyidea.lib.error import ParameterError
from privacyidea.models import authentication_log_column_length
from .base import MyTestCase


class AuthenticationLogTestCase(MyTestCase):

    def tearDown(self):
        from privacyidea.models.authentication_log import AuthenticationLog
        from privacyidea.models import db
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
        self.assertIsNone(entry.previous_transaction_id)
        self.assertIsNone(entry.other_info)

    def test_create_all_fields(self):
        event_id = log_authentication_event(
            event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="user1", realm="realm1",
            username="testuser", source_ip="192.168.1.1", client_label="vpn", serial="TOK001",
            transaction_id="txn-123", previous_transaction_id="txn-prev", other_info={"key": "value"}
        )

        entry = get_authentication_log_event(event_id)
        assert entry is not None
        self.assertEqual("testuser", entry.username)
        self.assertEqual("192.168.1.1", entry.source_ip)
        self.assertEqual("vpn", entry.client_label)
        self.assertEqual("TOK001", entry.serial)
        self.assertEqual("txn-123", entry.transaction_id)
        self.assertEqual("txn-prev", entry.previous_transaction_id)
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

        # All string columns use a case-sensitive collation, so the unflagged default is case-sensitive on every
        # backend: a differently-cased value does not match without the flag, and matches with it. This holds for a
        # non-boundary column (serial) too, confirming the behaviour is uniform across columns.
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
            id1 = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1",
                                           realm="r1")

        with patch('privacyidea.models.utils.datetime') as mock_dt:
            mock_dt.now.return_value.replace.return_value = future
            id2 = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u2",
                                           realm="r1")

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
        self.assertIsNone(entry.previous_transaction_id)
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
        # A value longer than its column is truncated instead of overflowing the column on insert. Cover a
        # size-constrained indexed column (resolver) and the generously-sized free columns (client_label, serial,
        # which hold a raw User-Agent and a comma-joined serial list).
        def over(column):
            return "X" * (authentication_log_column_length[column] + 50)

        event_id = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver=over("resolver"),
                                            uid="u1", realm="r1", username=over("username"),
                                            client_label=over("client_label"), serial=over("serial"),
                                            previous_transaction_id=over("previous_transaction_id"))
        entry = get_authentication_log_event(event_id)
        assert entry is not None
        self.assertEqual("X" * authentication_log_column_length["resolver"], entry.resolver)
        self.assertEqual("X" * authentication_log_column_length["username"], entry.username)
        self.assertEqual("X" * authentication_log_column_length["client_label"], entry.client_label)
        self.assertEqual("X" * authentication_log_column_length["serial"], entry.serial)
        self.assertEqual("X" * authentication_log_column_length["previous_transaction_id"],
                         entry.previous_transaction_id)

    def test_overflow_is_preserved_in_other_info(self):
        # The part of a value that does not fit the column is preserved under other_info["truncated"][column] (as the
        # cut-off remainder, not the full value) instead of being lost.
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
        # A comma-joined serial list is cut on a comma boundary so whole serials stay in the column (filterable via a
        # wildcard) and the dropped serials land in the overflow whole. Build a list whose last serial straddles the
        # column limit.
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
        # rather than dropping everything.
        max_serial = authentication_log_column_length["serial"]
        serial = "S" * (max_serial + 5)
        event_id = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, serial=serial)
        entry = get_authentication_log_event(event_id)
        assert entry is not None
        self.assertEqual("S" * max_serial, entry.serial)
        self.assertEqual({"truncated": {"serial": "SSSSS"}}, entry.other_info)

    def test_reclassify_preserves_serial_overflow(self):
        # Reclassification truncates the same way as the insert and preserves the serial overflow into the entry's
        # existing other_info.
        event_id = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, serial="TOK001")
        max_serial = authentication_log_column_length["serial"]
        head = "S" * (max_serial - 4)
        reclassify_authentication_log_event(event_id, AuthEventType.ENROLLMENT_TRIGGERED,
                                            serial=f"{head},AAA,BBBBBBBBBB")
        entry = get_authentication_log_event(event_id)
        assert entry is not None
        self.assertEqual(f"{head},AAA", entry.serial)
        self.assertEqual({"truncated": {"serial": "BBBBBBBBBB"}}, entry.other_info)

    def test_reclassify_without_serial_keeps_existing_serial(self):
        # Reclassifying with the default serial=None means "do not modify": an existing serial must survive, e.g. the
        # authorized=deny post-policy reclassifies a successful login to NOT_AUTHORIZED without passing a serial.
        event_id = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, serial="TOK001")
        reclassify_authentication_log_event(event_id, AuthEventType.NOT_AUTHORIZED)
        entry = get_authentication_log_event(event_id)
        assert entry is not None
        self.assertEqual(AuthEventType.NOT_AUTHORIZED, entry.event_type)
        self.assertEqual("TOK001", entry.serial)


class AuthenticationLogDBTestCase(MyTestCase):

    def tearDown(self):
        from privacyidea.models.authentication_log import AuthenticationLog
        from privacyidea.models import db
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
                client_label="vpn",
                serial="TOK001", transaction_id="txn-123", previous_transaction_id="txn-prev",
                other_info={"key": "value"}
            )

        entry = get_authentication_log_event(event_id)
        auth_log_dict = entry.to_dict()

        expected_keys = {"id", "resolver", "uid", "realm", "username", "user_role", "event_type", "timestamp",
                         "source_ip", "client_label", "serial", "transaction_id", "previous_transaction_id",
                         "other_info"}
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
        self.assertEqual("vpn", auth_log_dict["client_label"])
        self.assertEqual("TOK001", auth_log_dict["serial"])
        self.assertEqual("txn-123", auth_log_dict["transaction_id"])
        self.assertEqual("txn-prev", auth_log_dict["previous_transaction_id"])
        self.assertEqual({"key": "value"}, auth_log_dict["other_info"])


class AuthenticationLogPaginateTestCase(MyTestCase):

    def tearDown(self):
        from privacyidea.models.authentication_log import AuthenticationLog
        from privacyidea.models import db
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
        # The boundary columns are pinned to a case-sensitive collation (utf8mb4_bin on MySQL/MariaDB; SQLite, Postgres
        # and Oracle are case-sensitive by default), so a resolver scope never leaks a case-variant resolver on any
        # backend -- the boundary fails closed.
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", uid="u1", realm="realm1")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="RES1", uid="u2", realm="realm1")
        scope = AuthenticationLogVisibilityScope(realms=[], resolvers=["res1"], usernames=[])
        restricted = get_authentication_logs_paginate(visibility_scopes=[scope])
        self.assertEqual(1, restricted.count)
        self.assertEqual("res1", restricted.auth_logs[0].resolver)

    def test_visibility_scope_username_matches_case_sensitively_by_default(self):
        # Without the policy's user_case_insensitive option, an admin scoped to "alice" must not see "Alice" -- and the
        # case-sensitive collation makes this hold on every backend, not just on a case-sensitive DB collation.
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", realm="realm1",
                                 username="alice")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", realm="realm1",
                                 username="Alice")
        scope = AuthenticationLogVisibilityScope(realms=[], resolvers=[], usernames=["alice"])
        restricted = get_authentication_logs_paginate(visibility_scopes=[scope])
        self.assertEqual(1, restricted.count)
        self.assertEqual("alice", restricted.auth_logs[0].username)

    def test_visibility_scope_username_case_insensitive_when_policy_set(self):
        # With user_case_insensitive carried on the scope, the username dimension is forced case-insensitive via
        # LOWER() on both sides, so the admin scoped to "alice" also sees the "Alice" entry.
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", realm="realm1",
                                 username="alice")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res1", realm="realm1",
                                 username="Alice")
        scope = AuthenticationLogVisibilityScope(realms=[], resolvers=[], usernames=["alice"],
                                                 username_case_insensitive=True)
        restricted = get_authentication_logs_paginate(visibility_scopes=[scope])
        self.assertEqual(2, restricted.count)

    def test_to_dict_shape_and_iso_timestamp(self):
        self._create(1)
        page_dict = get_authentication_logs_paginate().to_dict()
        self.assertEqual({"auth_logs", "count", "current", "prev", "next"}, set(page_dict.keys()))
        timestamp = page_dict["auth_logs"][0]["timestamp"]
        self.assertIsInstance(timestamp, str)
        datetime.fromisoformat(timestamp)  # parseable ISO 8601


class AuthenticationLogDeleteTestCase(MyTestCase):

    def tearDown(self):
        from privacyidea.models.authentication_log import AuthenticationLog
        from privacyidea.models import db
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
