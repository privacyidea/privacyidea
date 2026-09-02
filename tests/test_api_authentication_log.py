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
Tests for the /authenticationlog/ management API: admin GET (pagination, filtering, realm/resolver-scoped visibility,
the policy gate) and user-scope GET. Rows are seeded directly; the recording of events during authentication is
covered in test_api_authentication_event_logging.py.
"""
import datetime

import mock

from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType
from privacyidea.lib.conditional_access.authentication_log import (log_authentication_event, AuthLogUserRole,
                                                                  MAX_STATISTICS_BINS)
from privacyidea.lib.conditional_access.outcome_log import record_outcomes
from privacyidea.lib.policy import set_policy, delete_policy, SCOPE, PolicyAction
from privacyidea.lib.realm import set_realm, delete_realm
from privacyidea.lib.resolver import save_resolver, delete_resolver
from privacyidea.models import ConditionalAccessOutcome, db
from .authlog_utils import AuthLogTestCase


class AuthenticationLogApiTestCase(AuthLogTestCase):
    """The /authenticationlog/ API: admin GET (pagination, filtering, realm/resolver visibility, the policy gate)
    and user-scope GET. All share the same blueprint and seed fixtures."""

    OTHER_REALM = "otherrealm"
    # A window around "now", since seeded rows take the current time and the statistics endpoint requires an explicit
    # one at both ends.
    STATS_START = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)).isoformat()
    STATS_END = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)).isoformat()

    def _seed(self, include_no_realm=False):
        # Seeds LOGIN_SUCCESS + MFA_FAIL in realm1 and a LOGIN_SUCCESS in another realm, plus an optional null-realm row
        # (e.g. USER_UNKNOWN); returns the created ids by key.
        ids = {
            "realm1_login": log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res", uid="1",
                                                     realm=self.realm1),
            "realm1_fail": log_authentication_event(event_type=AuthEventType.MFA_FAIL, resolver="res", uid="2",
                                                    realm=self.realm1),
            "other_login": log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res", uid="3",
                                                    realm=self.OTHER_REALM),
        }
        if include_no_realm:
            ids["no_realm"] = log_authentication_event(event_type=AuthEventType.USER_UNKNOWN)
        db.session.commit()
        return ids

    def _get(self, query_string=None, status=200):
        with self.app.test_request_context('/authenticationlog/', method='GET', query_string=query_string or {},
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(status, res.status_code, res.json)
            return res.json

    def _user_get(self, query_string=None, status=200):
        with self.app.test_request_context("/authenticationlog/", method="GET", query_string=query_string or {},
                                           headers={"Authorization": self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertEqual(status, res.status_code, res.json)
            return res.json

    @staticmethod
    def _returned_ids(value):
        return {entry["id"] for entry in value["auth_logs"]}

    def _login_helpdesk(self):
        # Logs in a helpdesk admin from the superuser realm "adminrealm" (so they have a real realm + username) and
        # clears the auth event their login produced, so tests run on controlled entries only; returns the JWT.
        set_realm("adminrealm", [{"name": self.resolvername1}])
        with self.app.test_request_context("/auth", method="POST",
                                           data={"username": "selfservice@adminrealm", "password": "test"}):
            token = self.app.full_dispatch_request().json["result"]["value"]["token"]
        self._clear_log()
        return token

    def _helpdesk_ids(self, token, query_string):
        with self.app.test_request_context("/authenticationlog/", method="GET", query_string=query_string,
                                           headers={"Authorization": token}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res.json)
            return {entry["id"] for entry in res.json["result"]["value"]["auth_logs"]}

    # --- admin GET ---

    def test_requires_admin(self):
        with self.app.test_request_context('/authenticationlog/', method='GET'):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res.json)

    def test_returns_paginated_page(self):
        self._seed(include_no_realm=True)
        value = self._get({"page": 1, "page_size": 2})["result"]["value"]
        self.assertEqual(4, value["count"])
        self.assertEqual(2, len(value["auth_logs"]))
        self.assertEqual(1, value["current"])
        self.assertIsNone(value["prev"])
        self.assertEqual(2, value["next"])

        last = self._get({"page": 2, "page_size": 2})["result"]["value"]
        self.assertEqual(1, last["prev"])
        self.assertIsNone(last["next"])

    def test_invalid_paging_params_fall_back_to_defaults(self):
        # A bad page / page_size must not reach the query as a negative offset or empty limit, so non-positive and
        # non-numeric values fall back to the defaults (page 1, default page_size).
        self._seed(include_no_realm=True)
        for bad in ({"page": 0}, {"page": -3}, {"page": "abc"}):
            value = self._get(bad)["result"]["value"]
            self.assertEqual(1, value["current"], bad)
            self.assertEqual(4, value["count"], bad)
            self.assertEqual(4, len(value["auth_logs"]), bad)
            self.assertIsNone(value["prev"], bad)
        for bad in ({"page_size": 0}, {"page_size": -10}, {"page_size": "abc"}):
            value = self._get(bad)["result"]["value"]
            self.assertEqual(4, len(value["auth_logs"]), bad)

    def test_serialized_entry_shape(self):
        self._seed(include_no_realm=True)
        value = self._get({"page_size": 50})["result"]["value"]
        entry = value["auth_logs"][0]
        self.assertIn("event_type", entry)
        self.assertIn("realm", entry)
        # timestamp is serialized as an ISO 8601 string, not a datetime
        self.assertIsInstance(entry["timestamp"], str)
        datetime.datetime.fromisoformat(entry["timestamp"])
        # Every entry carries its conditional-access history, empty when the request tripped no policy.
        self.assertEqual([], entry["conditional_access_outcomes"])

    def test_entry_carries_its_conditional_access_outcomes(self):
        event_id = log_authentication_event(event_type=AuthEventType.MFA_FAIL, resolver="res1", uid="u1",
                                            realm=self.realm1)
        record_outcomes([ConditionalAccessOutcome(action_type="LOCK_USER", policy_name="Brute force",
                                                 threshold=3, event_count=3, stage_name="Second strike",
                                                 info={"expires_at": "2026-08-07T12:00:00+00:00"})], event_id)
        try:
            entry = next(e for e in self._get({"page_size": 50})["result"]["value"]["auth_logs"]
                         if e["id"] == event_id)
            outcome = entry["conditional_access_outcomes"][0]
            self.assertEqual("LOCK_USER", outcome["action_type"])
            self.assertEqual("Brute force", outcome["policy_name"])
            self.assertEqual("Second strike", outcome["stage_name"])
            self.assertEqual(3, outcome["threshold"])
            self.assertEqual(3, outcome["event_count"])
            self.assertFalse(outcome["dry_run"])
            # Action-specific detail rides along as the dict it was stored as.
            self.assertDictEqual({"expires_at": "2026-08-07T12:00:00+00:00"}, outcome["info"])
            # No timestamp of its own: the entry it hangs off carries it.
            self.assertNotIn("timestamp", outcome)
        finally:
            db.session.query(ConditionalAccessOutcome).delete()
            db.session.commit()

    # --- filtering on what conditional access did ---

    def _seed_outcomes(self):
        """
        Three entries: one locked by "Brute force", one only notified by "Notify", one a dry run of "Notify", plus a
        fourth entry conditional access never touched. Returns the ids by key.
        """
        ids = {
            "locked": log_authentication_event(event_type=AuthEventType.MFA_FAIL, resolver="res", uid="1",
                                               realm=self.realm1),
            "notified": log_authentication_event(event_type=AuthEventType.MFA_FAIL, resolver="res", uid="2",
                                                 realm=self.realm1),
            "simulated": log_authentication_event(event_type=AuthEventType.MFA_FAIL, resolver="res", uid="3",
                                                 realm=self.realm1),
            "untouched": log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res", uid="4",
                                                  realm=self.realm1),
        }
        db.session.commit()
        record_outcomes([self._make_outcome("LOCK_USER", "Brute force")], ids["locked"])
        record_outcomes([self._make_outcome("EMAIL_ADMIN", "Notify")], ids["notified"])
        record_outcomes([self._make_outcome("LOCK_USER", "Notify", dry_run=True)], ids["simulated"])
        return ids

    @staticmethod
    def _make_outcome(action_type, policy_name, dry_run=False):
        return ConditionalAccessOutcome(action_type=action_type, policy_name=policy_name, threshold=3,
                                        event_count=3, dry_run=dry_run)

    def _clear_outcomes(self):
        db.session.query(ConditionalAccessOutcome).delete()
        db.session.commit()

    def test_filter_by_outcome_action_type(self):
        ids = self._seed_outcomes()
        try:
            value = self._get({"ca_action_type": "LOCK_USER"})["result"]["value"]
            self.assertEqual(2, value["count"])
            self.assertSetEqual({ids["locked"], ids["simulated"]}, self._returned_ids(value))
            # A list and a wildcard work as for every other filter, and "*" means "acted on at all".
            self.assertSetEqual({ids["locked"], ids["notified"], ids["simulated"]},
                                self._returned_ids(self._get({"ca_action_type": "LOCK_USER,EMAIL_ADMIN"})
                                                   ["result"]["value"]))
            self.assertSetEqual({ids["notified"]},
                                self._returned_ids(self._get({"ca_action_type": "EMAIL*"})["result"]["value"]))
            self.assertSetEqual({ids["locked"], ids["notified"], ids["simulated"]},
                                self._returned_ids(self._get({"ca_action_type": "*"})["result"]["value"]))
        finally:
            self._clear_outcomes()

    def test_filter_by_outcome_policy_name(self):
        ids = self._seed_outcomes()
        try:
            value = self._get({"ca_policy_name": "Notify"})["result"]["value"]
            self.assertSetEqual({ids["notified"], ids["simulated"]}, self._returned_ids(value))
            # The outcome columns use the same case-sensitive collation as the log, so the flag is needed here too.
            self.assertEqual(0, self._get({"ca_policy_name": "notify"})["result"]["value"]["count"])
            self.assertEqual(2, self._get({"ca_policy_name": "notify", "case_insensitive": "1"})
                             ["result"]["value"]["count"])
        finally:
            self._clear_outcomes()

    def test_filter_by_outcome_dry_run_is_a_tri_state(self):
        ids = self._seed_outcomes()
        try:
            self.assertSetEqual({ids["simulated"]},
                                self._returned_ids(self._get({"ca_dry_run": "true"})["result"]["value"]))
            self.assertSetEqual({ids["locked"], ids["notified"]},
                                self._returned_ids(self._get({"ca_dry_run": "false"})["result"]["value"]))
            # Omitted or empty does not filter at all - which is how "both" is expressed.
            self.assertEqual(4, self._get({"page_size": 50})["result"]["value"]["count"])
            self.assertEqual(4, self._get({"ca_dry_run": "", "page_size": 50})["result"]["value"]["count"])
        finally:
            self._clear_outcomes()

    def test_outcome_filters_apply_to_one_and_the_same_outcome(self):
        # The entry has two outcomes, LOCK_USER by "Brute force" and EMAIL_ADMIN by "Notify"; asking for LOCK_USER *by
        # Notify* must not match it, even though each half is true of a different outcome on the same entry.
        event_id = log_authentication_event(event_type=AuthEventType.MFA_FAIL, resolver="res", uid="9",
                                            realm=self.realm1)
        db.session.commit()
        record_outcomes([self._make_outcome("LOCK_USER", "Brute force"),
                         self._make_outcome("EMAIL_ADMIN", "Notify")], event_id)
        try:
            self.assertEqual(0, self._get({"ca_action_type": "LOCK_USER", "ca_policy_name": "Notify"})
                             ["result"]["value"]["count"])
            self.assertEqual(1, self._get({"ca_action_type": "LOCK_USER", "ca_policy_name": "Brute force"})
                             ["result"]["value"]["count"])
        finally:
            self._clear_outcomes()

    def test_outcome_filter_returns_an_entry_once_however_many_outcomes_match(self):
        # The EXISTS must not multiply the entry the way a join would - in the page or in the count.
        event_id = log_authentication_event(event_type=AuthEventType.MFA_FAIL, resolver="res", uid="8",
                                            realm=self.realm1)
        db.session.commit()
        record_outcomes([self._make_outcome("LOCK_USER", "P1"), self._make_outcome("LOCK_USER", "P2"),
                         self._make_outcome("LOCK_USER", "P3")], event_id)
        try:
            value = self._get({"ca_action_type": "LOCK_USER"})["result"]["value"]
            self.assertEqual(1, value["count"])
            self.assertListEqual([event_id], [entry["id"] for entry in value["auth_logs"]])
        finally:
            self._clear_outcomes()

    def test_outcome_filter_combines_with_a_filter_on_the_entry(self):
        ids = self._seed_outcomes()
        try:
            self.assertSetEqual({ids["locked"]},
                                self._returned_ids(self._get({"ca_action_type": "LOCK_USER", "uid": "1"})
                                                   ["result"]["value"]))
            self.assertEqual(0, self._get({"ca_action_type": "LOCK_USER",
                                           "event_type": AuthEventType.LOGIN_SUCCESS})["result"]["value"]["count"])
        finally:
            self._clear_outcomes()

    def test_filter_by_event_type(self):
        self._seed(include_no_realm=True)
        value = self._get({"event_type": AuthEventType.MFA_FAIL})["result"]["value"]
        self.assertEqual(1, value["count"])
        self.assertEqual(AuthEventType.MFA_FAIL, value["auth_logs"][0]["event_type"])

    def test_filter_by_event_type_csv_list(self):
        self._seed(include_no_realm=True)
        value = self._get({"event_type": f"{AuthEventType.MFA_FAIL},{AuthEventType.USER_UNKNOWN}"})["result"]["value"]
        self.assertEqual(2, value["count"])
        self.assertSetEqual({AuthEventType.MFA_FAIL, AuthEventType.USER_UNKNOWN},
                            {entry["event_type"] for entry in value["auth_logs"]})

    def test_filter_by_event_type_wildcard(self):
        self._seed(include_no_realm=True)
        # the two LOGIN_SUCCESS rows match the LOGIN* prefix; MFA_FAIL and USER_UNKNOWN do not
        value = self._get({"event_type": "LOGIN*"})["result"]["value"]
        self.assertEqual(2, value["count"])
        self.assertSetEqual({AuthEventType.LOGIN_SUCCESS}, {entry["event_type"] for entry in value["auth_logs"]})

    def test_filter_by_user_role(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res", uid="1", realm=self.realm1,
                             user_role=AuthLogUserRole.USER)
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res", uid="2", realm=self.realm1,
                                 user_role=AuthLogUserRole.ADMIN_INTERNAL)
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res", uid="3", realm=self.realm1,
                                 user_role=AuthLogUserRole.ADMIN_EXTERNAL)
        db.session.commit()

        self.assertEqual(1, self._get({"user_role": AuthLogUserRole.USER})["result"]["value"]["count"])
        # The shared 'admin-' prefix lets one wildcard filter match either admin kind.
        value = self._get({"user_role": "admin*"})["result"]["value"]
        self.assertEqual(2, value["count"])
        self.assertSetEqual({AuthLogUserRole.ADMIN_INTERNAL, AuthLogUserRole.ADMIN_EXTERNAL},
                            {entry["user_role"] for entry in value["auth_logs"]})

    def test_filter_case_insensitive(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res", uid="1", realm=self.realm1,
                                 username="Alice")
        db.session.commit()

        # The log's string columns use a case-sensitive collation on every backend, so "alice" does not match the stored
        # "Alice" without the case_insensitive flag, and does with it.
        self.assertEqual(0, self._get({"username": "alice"})["result"]["value"]["count"])
        self.assertEqual(1, self._get({"username": "alice", "case_insensitive": "1"})["result"]["value"]["count"])
        self.assertEqual(1, self._get({"username": "Alice"})["result"]["value"]["count"])

    def test_filter_by_client_label(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res", uid="1", realm=self.realm1,
                                 client_label="vpn")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res", uid="2", realm=self.realm1,
                                 client_label="webui")
        db.session.commit()

        value = self._get({"client_label": "vpn"})["result"]["value"]
        self.assertEqual(1, value["count"])
        self.assertEqual("vpn", value["auth_logs"][0]["client_label"])

    def test_filter_by_attempt_id(self):
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res", uid="1", realm=self.realm1,
                                 attempt_id="att-x")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res", uid="2", realm=self.realm1,
                                 attempt_id="att-y")
        db.session.commit()

        value = self._get({"attempt_id": "att-x"})["result"]["value"]
        self.assertEqual(1, value["count"])
        self.assertEqual("att-x", value["auth_logs"][0]["attempt_id"])

    def test_rejects_a_malformed_timestamp(self):
        # The filters are optional, but a present value that cannot be parsed must not escape as the ValueError
        # isoparse raises, nor be dropped so the page answers an unfiltered question.
        for key in ("start_time", "end_time"):
            with self.app.test_request_context("/authenticationlog/", method="GET", query_string={key: "not-a-time"},
                                               headers={"Authorization": self.at}):
                res = self.app.full_dispatch_request()
                self.assertEqual(400, res.status_code, res.json)
                self.assertEqual(905, res.json["result"]["error"]["code"], res.json)
                self.assertIn(f"Invalid ISO 8601 timestamp for {key}", res.json["result"]["error"]["message"])

    def test_blank_timestamp_does_not_filter(self):
        ids = self._seed()
        self.assertEqual(len(ids), self._get({"start_time": "", "end_time": ""})["result"]["value"]["count"])

    def test_policy_gate_denies_without_action(self):
        # Admin policies exist but none grant authentication_log_read -> the admin is denied.
        set_policy("authlog_other", scope=SCOPE.ADMIN, action=PolicyAction.ENABLE)
        try:
            body = self._get(status=403)
            self.assertFalse(body["result"]["status"], body)
        finally:
            delete_policy("authlog_other")

    # --- event types ---

    def _get_event_types(self, token, status=200):
        with self.app.test_request_context("/authenticationlog/eventtypes", method="GET",
                                           headers={"Authorization": token}):
            res = self.app.full_dispatch_request()
            self.assertEqual(status, res.status_code, res.json)
            return res.json

    def test_event_types_lists_all_defined_types_for_admin(self):
        value = self._get_event_types(self.at)["result"]["value"]
        # The endpoint is the authoritative AuthEventType list (name + outcome), in definition order.
        self.assertListEqual([str(event_type) for event_type in AuthEventType], [entry["name"] for entry in value])
        by_name = {entry["name"]: entry["outcome"] for entry in value}
        self.assertEqual("success", by_name["LOGIN_SUCCESS"])
        self.assertEqual("failure", by_name["USER_UNKNOWN"])
        self.assertEqual("pending", by_name["CHALLENGE_TRIGGERED"])
        # This includes the types conditional access writes for its own rejections: a policy may not count them, but an
        # admin must still be able to filter the log for them.
        self.assertEqual("failure", by_name["USER_LOCKED"])
        self.assertEqual("failure", by_name["IP_BLOCKED"])
        self.assertEqual("failure", by_name["ACCESS_DENIED"])

    def test_event_types_accessible_to_user(self):
        self.authenticate_selfservice_user()
        set_policy("authlog_user", scope=SCOPE.USER, action=PolicyAction.AUTHENTICATION_LOG_READ)
        try:
            value = self._get_event_types(self.at_user)["result"]["value"]
            self.assertListEqual([str(event_type) for event_type in AuthEventType], [entry["name"] for entry in value])
        finally:
            delete_policy("authlog_user")

    def test_event_types_denied_without_action(self):
        # The same policy gate as the log read endpoint: admin policies exist but none grant the action -> denied.
        set_policy("authlog_other", scope=SCOPE.ADMIN, action=PolicyAction.ENABLE)
        try:
            body = self._get_event_types(self.at, status=403)
            self.assertFalse(body["result"]["status"], body)
        finally:
            delete_policy("authlog_other")

    def test_realm_scoped_policy_restricts_visible_entries(self):
        ids = self._seed(include_no_realm=True)
        # case-sensitive matching: same name capitalized should not match
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver=self.resolvername1,
                                 uid="2", realm=self.realm1.capitalize())
        # Policy scoped to realm1: the admin sees exactly the realm1 rows, not the other realm or the null-realm row.
        set_policy("authlog_realm", scope=SCOPE.ADMIN, action=PolicyAction.AUTHENTICATION_LOG_READ,
                   realm=self.realm1)
        try:
            value = self._get({"page_size": 50})["result"]["value"]
            self.assertEqual({ids["realm1_login"], ids["realm1_fail"]}, self._returned_ids(value))
        finally:
            delete_policy("authlog_realm")

    def test_resolver_scoped_policy_restricts_visible_entries(self):
        in_scope = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver=self.resolvername1,
                                            uid="1", realm=self.realm1)
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="otherresolver", uid="2",
                                 realm=self.realm1)
        # case-sensitive matching: same name capitalized should not match
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver=self.resolvername1.capitalize(), uid="2",
                                 realm=self.realm1)
        db.session.commit()
        set_policy("authlog_resolver", scope=SCOPE.ADMIN, action=PolicyAction.AUTHENTICATION_LOG_READ,
                   resolver=self.resolvername1)
        try:
            value = self._get({"page_size": 50})["result"]["value"]
            self.assertEqual({in_scope}, self._returned_ids(value))
        finally:
            delete_policy("authlog_resolver")

    def test_user_scoped_policy_matches_username_case_sensitively_by_default(self):
        # A user-scoped policy is an authorization boundary: without user_case_insensitive it matches the username
        # case-sensitively, so a differently-cased entry ("Alice") is hidden from an admin scoped to "alice" -- and the
        # case-sensitive column collation guarantees this on every backend.
        in_scope = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver=self.resolvername1,
                                            uid="1", realm=self.realm1, username="alice")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver=self.resolvername1, uid="2",
                                 realm=self.realm1, username="Alice")
        db.session.commit()
        set_policy("authlog_user", scope=SCOPE.ADMIN, action=PolicyAction.AUTHENTICATION_LOG_READ, user="alice")
        try:
            value = self._get({"page_size": 50})["result"]["value"]
            self.assertSetEqual({in_scope}, self._returned_ids(value))
        finally:
            delete_policy("authlog_user")

    def test_user_scoped_policy_case_insensitive_when_policy_set(self):
        # With user_case_insensitive on the policy, the username dimension is forced case-insensitive (LOWER on both
        # sides), so the admin scoped to "alice" also sees the "Alice" entry, exercising the policy -> scope -> query
        # wiring.
        alice = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver=self.resolvername1,
                                         uid="1", realm=self.realm1, username="alice")
        alice_upper = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver=self.resolvername1,
                                               uid="2", realm=self.realm1, username="Alice")
        db.session.commit()
        set_policy("authlog_user", scope=SCOPE.ADMIN, action=PolicyAction.AUTHENTICATION_LOG_READ, user="alice",
                   user_case_insensitive=True)
        try:
            value = self._get({"page_size": 50})["result"]["value"]
            self.assertSetEqual({alice, alice_upper}, self._returned_ids(value))
        finally:
            delete_policy("authlog_user")

    def test_multiple_policies_union_scopes(self):
        # P1 scopes realm1, P2 scopes resolver1 -> the admin sees (realm1) OR (resolver1).
        matches_p1 = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="otherresolver",
                                              uid="1", realm=self.realm1)
        matches_p2 = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver=self.resolvername1,
                                              uid="2", realm=self.OTHER_REALM)
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="otherresolver", uid="3",
                                 realm=self.OTHER_REALM)  # matches neither
        db.session.commit()
        set_policy("authlog_p1", scope=SCOPE.ADMIN, action=PolicyAction.AUTHENTICATION_LOG_READ, realm=self.realm1)
        set_policy("authlog_p2", scope=SCOPE.ADMIN, action=PolicyAction.AUTHENTICATION_LOG_READ,
                   resolver=self.resolvername1)
        try:
            value = self._get({"page_size": 50})["result"]["value"]
            self.assertEqual({matches_p1, matches_p2}, self._returned_ids(value))
        finally:
            delete_policy("authlog_p1")
            delete_policy("authlog_p2")

    def test_unscoped_policy_grants_all_even_alongside_a_scoped_one(self):
        # If any applicable policy has no target scope, the admin is unrestricted, even alongside another policy that is
        # scoped (which alone would have limited the result to realm1's 2 rows).
        ids = self._seed(include_no_realm=True)  # realm1 x2, OTHER_REALM x1, null-realm x1
        set_policy("authlog_scoped", scope=SCOPE.ADMIN, action=PolicyAction.AUTHENTICATION_LOG_READ, realm=self.realm1)
        set_policy("authlog_all", scope=SCOPE.ADMIN, action=PolicyAction.AUTHENTICATION_LOG_READ)
        try:
            value = self._get({"page_size": 50})["result"]["value"]
            self.assertEqual(set(ids.values()), self._returned_ids(value))
        finally:
            delete_policy("authlog_scoped")
            delete_policy("authlog_all")

    def test_unscoped_policy_builds_no_visibility_filter(self):
        # An unscoped policy grants everything, so no realm/resolver/user filter is built at all -- the lib is called
        # with visibility_scopes=None rather than scopes that merely happen to match every row.
        with mock.patch("privacyidea.api.authentication_log.get_authentication_logs_paginate") as paginate_mock:
            paginate_mock.return_value.to_dict.return_value = {}
            # Only a scoped policy -> the lib receives concrete scopes.
            set_policy("authlog_scoped", scope=SCOPE.ADMIN, action=PolicyAction.AUTHENTICATION_LOG_READ,
                       realm=self.realm1)
            self._get()
            self.assertIsNotNone(paginate_mock.call_args.kwargs["visibility_scopes"])
            # Adding an unscoped policy of the same action -> no filter is built at all.
            set_policy("authlog_all", scope=SCOPE.ADMIN, action=PolicyAction.AUTHENTICATION_LOG_READ)
            try:
                self._get()
                self.assertIsNone(paginate_mock.call_args.kwargs["visibility_scopes"])
            finally:
                delete_policy("authlog_scoped")
                delete_policy("authlog_all")

    def test_realm_scoped_admin_always_sees_own_entries(self):
        # A realm-scoped helpdesk admin sees their own entry even though it is in a different realm (adminrealm),
        # because the own-scope matches by realm + username -- resolver is intentionally not part of the match.
        helpdesk_token = self._login_helpdesk()
        in_scope = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver=self.resolvername1,
                                            uid="1", realm=self.realm1)
        own = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver=self.resolvername1, uid="2",
                                       realm="adminrealm", username="selfservice")
        db.session.commit()
        set_policy("authlog_realm", scope=SCOPE.ADMIN, action=PolicyAction.AUTHENTICATION_LOG_READ, realm=self.realm1)
        try:
            self.assertEqual({in_scope, own}, self._helpdesk_ids(helpdesk_token, {"page_size": 50}))
        finally:
            delete_policy("authlog_realm")
            delete_realm("adminrealm")

    def test_resolver_scoped_admin_always_sees_own_entries(self):
        # The helpdesk admin resolves via resolvername1 (adminrealm uses it); granted read access scoped to a
        # *different* resolver, their own entries fall outside that scope and are only included via the own-entries
        # scope.
        save_resolver({"resolver": "otherresolver", "type": "passwdresolver", "fileName": "tests/testdata/passwords"})
        helpdesk_token = self._login_helpdesk()
        in_scope = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="otherresolver",
                                            uid="1", realm=self.realm1)
        own = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver=self.resolvername1, uid="2",
                                       realm="adminrealm", username="selfservice")
        db.session.commit()
        set_policy("authlog_resolver", scope=SCOPE.ADMIN, action=PolicyAction.AUTHENTICATION_LOG_READ,
                   resolver="otherresolver")
        try:
            self.assertSetEqual({in_scope, own}, self._helpdesk_ids(helpdesk_token, {"page_size": 50}))
        finally:
            delete_policy("authlog_resolver")
            delete_realm("adminrealm")
            delete_resolver("otherresolver")

    def test_user_scoped_admin_always_sees_own_entries(self):
        # A user-scoped helpdesk admin sees their own entry even though its username differs from the scoped user, so it
        # is only included via the own-entries scope.
        helpdesk_token = self._login_helpdesk()
        in_scope = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver=self.resolvername1,
                                            uid="1", realm=self.realm1, username="someuser")
        own = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver=self.resolvername1, uid="2",
                                       realm="adminrealm", username="selfservice")
        db.session.commit()
        set_policy("authlog_user", scope=SCOPE.ADMIN, action=PolicyAction.AUTHENTICATION_LOG_READ, user="someuser")
        try:
            self.assertSetEqual({in_scope, own}, self._helpdesk_ids(helpdesk_token, {"page_size": 50}))
        finally:
            delete_policy("authlog_user")
            delete_realm("adminrealm")

    def test_local_admin_always_sees_own_entries(self):
        # A restricted local (DB) admin has no realm; their own /auth events are recorded with realm/resolver NULL and
        # user_role=admin-internal, so they are matched by username + role, not by realm.
        in_scope = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver=self.resolvername1,
                                            uid="1", realm=self.realm1)
        own = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, username=self.testadmin,
                                       user_role=AuthLogUserRole.ADMIN_INTERNAL)
        # A same-named regular user's entry must NOT leak in via the own-scope (matched by role, not username alone).
        other = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver=self.resolvername1, uid="3",
                                         realm=self.OTHER_REALM, username=self.testadmin,
                                         user_role=AuthLogUserRole.USER)
        db.session.commit()
        set_policy("authlog_realm", scope=SCOPE.ADMIN, action=PolicyAction.AUTHENTICATION_LOG_READ, realm=self.realm1)
        try:
            ids = self._returned_ids(self._get({"page_size": 50})["result"]["value"])
            self.assertSetEqual({in_scope, own}, ids)
            self.assertNotIn(other, ids)
        finally:
            delete_policy("authlog_realm")

    def test_user_sees_only_own_entries(self):
        # Logs in the self-service user "selfservice" in realm1 (-> self.at_user); that login writes its own auth-log
        # entry, so the log is cleared to test on controlled entries only.
        self.authenticate_selfservice_user()
        self._clear_log()
        own = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver=self.resolvername1, uid="1",
                                       realm=self.realm1, username="selfservice")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver=self.resolvername1, uid="2",
                                 realm=self.realm1, username="hans")  # another user, same realm
        log_authentication_event(event_type=AuthEventType.USER_UNKNOWN)  # no identity
        db.session.commit()
        set_policy("authlog_user", scope=SCOPE.USER, action=PolicyAction.AUTHENTICATION_LOG_READ)
        try:
            value = self._user_get({"page_size": 50})["result"]["value"]
            self.assertEqual({own}, {entry["id"] for entry in value["auth_logs"]})
        finally:
            delete_policy("authlog_user")

    def test_user_denied_without_action(self):
        # A user-scope policy exists but does not grant authentication_log_read -> the user is denied.
        self.authenticate_selfservice_user()  # -> self.at_user
        set_policy("user_other", scope=SCOPE.USER, action=PolicyAction.DISABLE)
        try:
            body = self._user_get(status=403)
            self.assertFalse(body["result"]["status"], body)
        finally:
            delete_policy("user_other")

    # --- statistics ---

    def _statistics(self, query_string=None, token=None, status=200):
        query = {"start_time": self.STATS_START, "end_time": self.STATS_END}
        query.update(query_string or {})
        with self.app.test_request_context("/authenticationlog/statistics", method="GET", query_string=query,
                                           headers={"Authorization": token or self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(status, res.status_code, res.json)
            return res.json

    @staticmethod
    def _statistics_totals(body):
        return {series["event_type"]: series["total"] for series in body["result"]["value"]["events"]}

    def _assert_error(self, body, code, message):
        # A status code alone does not say which check rejected the request - several distinct failures share a 400 -
        # so the error code and message are what pin a test to the reason it is meant to cover.
        result = body["result"]
        self.assertFalse(result["status"], body)
        self.assertEqual(code, result["error"]["code"], body)
        self.assertIn(message, result["error"]["message"], body)

    def test_statistics_is_authenticated(self):
        with self.app.test_request_context("/authenticationlog/statistics", method="GET",
                                           query_string={"start_time": self.STATS_START,
                                                         "end_time": self.STATS_END}):
            res = self.app.full_dispatch_request()
            self.assertEqual(401, res.status_code, res.json)
            self._assert_error(res.json, 4033, "Missing Authorization header")

    def test_statistics_policy_gate_denies_without_action(self):
        set_policy("authlog_other", scope=SCOPE.ADMIN, action=PolicyAction.ENABLE)
        try:
            self._assert_error(self._statistics(status=403), 303,
                               f"the action {PolicyAction.AUTHENTICATION_LOG_READ} is not allowed")
        finally:
            delete_policy("authlog_other")

    def test_statistics_counts_attempts_not_rows(self):
        log_authentication_event(event_type=AuthEventType.CHALLENGE_TRIGGERED, resolver="res", uid="1",
                                 realm=self.realm1, attempt_id="att-1")
        log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver="res", uid="1", realm=self.realm1,
                                 attempt_id="att-1")
        db.session.commit()

        body = self._statistics()

        self.assertDictEqual({str(AuthEventType.LOGIN_SUCCESS): 1}, self._statistics_totals(body))
        self.assertEqual(1, body["result"]["value"]["window"]["total"])

    def test_statistics_response_shape(self):
        log_authentication_event(event_type=AuthEventType.MFA_FAIL, resolver="res", uid="1", realm=self.realm1)
        db.session.commit()

        value = self._statistics({"bins": 6})["result"]["value"]

        self.assertEqual(6, value["bins"]["count"])
        self.assertEqual(6, len(value["bins"]["starts"]))
        self.assertListEqual([str(AuthEventType.MFA_FAIL)], [s["event_type"] for s in value["events"]])
        series = value["events"][0]
        self.assertEqual("failure", series["outcome"])
        self.assertEqual(6, len(series["counts"]))
        self.assertEqual(1, sum(series["counts"]))

    def test_statistics_requires_a_window(self):
        # Each end names itself in its own error, so a caller that omitted one is not sent looking at the other.
        for missing, query in (("start_time", {"end_time": self.STATS_END}),
                               ("end_time", {"start_time": self.STATS_START}),
                               ("start_time", {"start_time": "", "end_time": self.STATS_END})):
            with self.app.test_request_context("/authenticationlog/statistics", method="GET", query_string=query,
                                               headers={"Authorization": self.at}):
                res = self.app.full_dispatch_request()
                self.assertEqual(400, res.status_code, res.json)
                self._assert_error(res.json, 905, f"Missing parameter: {missing}")

    def test_statistics_rejects_a_malformed_timestamp(self):
        # isoparse raises ValueError, which is not a PrivacyIDEAError: unguarded it escapes the request unhandled
        # instead of becoming a 400 naming the parameter at fault.
        self._assert_error(self._statistics({"start_time": "not-a-time"}, status=400), 905,
                           "Invalid ISO 8601 timestamp for start_time")
        self._assert_error(self._statistics({"end_time": "31-12-2026"}, status=400), 905,
                           "Invalid ISO 8601 timestamp for end_time")

    def test_statistics_rejects_an_inverted_window(self):
        self._assert_error(self._statistics({"start_time": self.STATS_END, "end_time": self.STATS_START},
                                            status=400), 905, "window must end after it starts")
        self._assert_error(self._statistics({"end_time": self.STATS_START}, status=400), 905,
                           "window must end after it starts")

    def test_statistics_rejects_an_out_of_range_bin_count(self):
        # The documented maximum itself is accepted, and only the value past it is refused: a caller asking for a
        # resolution the endpoint will not serve is told the limit rather than handed a coarser answer silently.
        self.assertEqual(MAX_STATISTICS_BINS,
                         self._statistics({"bins": MAX_STATISTICS_BINS})["result"]["value"]["bins"]["count"])
        for bins in (MAX_STATISTICS_BINS + 1, 1000):
            self._assert_error(self._statistics({"bins": bins}, status=400), 905,
                               f"The number of bins must be between 1 and {MAX_STATISTICS_BINS}.")

    def test_statistics_clamps_a_non_positive_bin_count(self):
        # A non-positive or unparsable bins falls back to the default, as page_size does on the listing, rather than
        # reaching the lib's lower-bound guard.
        for bins in (0, -5, "abc"):
            self.assertEqual(48, self._statistics({"bins": bins})["result"]["value"]["bins"]["count"])

    def test_statistics_filters_take_a_list_under_a_plural_name(self):
        log_authentication_event(event_type=AuthEventType.MFA_FAIL, resolver="res", uid="1", realm=self.realm1,
                                 source_ip="10.0.0.1")
        log_authentication_event(event_type=AuthEventType.MFA_FAIL, resolver="res", uid="2", realm=self.realm1,
                                 source_ip="10.0.0.2")
        db.session.commit()

        self.assertDictEqual({str(AuthEventType.MFA_FAIL): 1},
                             self._statistics_totals(self._statistics({"source_ips": "10.0.0.1"})))
        self.assertDictEqual({str(AuthEventType.MFA_FAIL): 2},
                             self._statistics_totals(self._statistics({"source_ips": "10.0.0.1,10.0.0.2"})))
        # The singular name the listing uses is not a filter here, so it must not silently narrow the result.
        self.assertDictEqual({str(AuthEventType.MFA_FAIL): 2},
                             self._statistics_totals(self._statistics({"source_ip": "10.0.0.1"})))

    def test_statistics_respects_the_visibility_scope(self):
        self._seed()
        set_policy("authlog_realm", scope=SCOPE.ADMIN, action=PolicyAction.AUTHENTICATION_LOG_READ,
                   realm=self.realm1)
        try:
            # The other realm's LOGIN_SUCCESS must not reach the aggregate, so only realm1's two attempts are counted.
            self.assertDictEqual({str(AuthEventType.LOGIN_SUCCESS): 1, str(AuthEventType.MFA_FAIL): 1},
                                 self._statistics_totals(self._statistics()))
        finally:
            delete_policy("authlog_realm")

    def test_statistics_ignores_the_outcome_filters(self):
        # The ca_* filters match a request's conditional-access outcomes, which an attempt-level aggregate has no
        # notion of, so the endpoint does not offer them and passing one neither filters nor fails.
        log_authentication_event(event_type=AuthEventType.MFA_FAIL, resolver="res", uid="1", realm=self.realm1)
        db.session.commit()

        self.assertDictEqual({str(AuthEventType.MFA_FAIL): 1},
                             self._statistics_totals(self._statistics({"ca_action_type": "LOCK_USER"})))
