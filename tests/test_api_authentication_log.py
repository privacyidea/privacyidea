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
the policy gate), admin DELETE (filtered bulk delete), and user-scope GET. Rows are seeded directly; the recording of
events during authentication is covered in test_api_authentication_event_logging.py.
"""
import datetime

import mock

from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.conditional_access.authentication_event_types import AuthEventType, AUTH_EVENT_TYPE_KEY
from privacyidea.lib.conditional_access.authentication_log import (get_authentication_logs, log_authentication_event,
                                                                   AuthLogUserRole)
from privacyidea.lib.policy import set_policy, delete_policy, SCOPE, PolicyAction, AUTHORIZED
from privacyidea.lib.realm import set_realm, delete_realm
from privacyidea.models import db
from .authlog_utils import AuthLogTestCase


class AuthenticationLogApiTestCase(AuthLogTestCase):
    """The /authenticationlog/ API: admin GET (pagination, filtering, realm/resolver visibility, the policy gate),
    admin DELETE (filtered bulk delete), and user-scope GET. All share the same blueprint and seed fixtures."""

    OTHER_REALM = "otherrealm"

    def _seed(self, include_no_realm=False):
        # LOGIN_SUCCESS + MFA_FAIL in realm1 and a LOGIN_SUCCESS in another realm; optionally a null-realm row
        # (e.g. USER_UNKNOWN). Returns the created ids by key.
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

    def _delete(self, query_string=None, status=200):
        with self.app.test_request_context("/authenticationlog/", method="DELETE", query_string=query_string or {},
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

    @staticmethod
    def _remaining_ids():
        return {entry.id for entry in get_authentication_logs()}

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
        # A bad page / page_size must not reach the query as a negative offset or empty limit: non-positive and
        # non-numeric values fall back to the defaults (page 1, default page_size) instead.
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

        # The flag enforces a case-insensitive match regardless of the DB collation. The unflagged default follows
        # the collation (case-sensitive on SQLite, case-insensitive on a MySQL/MariaDB *_ci collation), so it is not
        # asserted here.
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

    def test_policy_gate_denies_without_action(self):
        # Admin policies exist but none grant authentication_log_read -> the admin is denied.
        set_policy("authlog_other", scope=SCOPE.ADMIN, action=PolicyAction.ENABLE)
        try:
            body = self._get(status=403)
            self.assertFalse(body["result"]["status"], body)
        finally:
            delete_policy("authlog_other")

    def test_realm_scoped_policy_restricts_visible_entries(self):
        ids = self._seed(include_no_realm=True)
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
        db.session.commit()
        set_policy("authlog_resolver", scope=SCOPE.ADMIN, action=PolicyAction.AUTHENTICATION_LOG_READ,
                   resolver=self.resolvername1)
        try:
            value = self._get({"page_size": 50})["result"]["value"]
            self.assertEqual({in_scope}, self._returned_ids(value))
        finally:
            delete_policy("authlog_resolver")

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
        # If any applicable policy has no target scope, the admin is unrestricted -- even when another policy is
        # scoped. (The scoped policy alone would have limited the result to realm1's 2 rows.)
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
        # Efficiency: an unscoped policy grants everything, so no realm/resolver/user filter is built at all -- the
        # lib is called with visibility_scopes=None, not scopes that merely happen to match every row.
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

    def test_admins_own_entries_always_included(self):
        # A helpdesk admin in the superuser realm "adminrealm" has a real (username, realm), so their own entries
        # are always added to the policy scope.
        set_realm("adminrealm", [{"name": self.resolvername1}])
        with self.app.test_request_context("/auth", method="POST",
                                           data={"username": "selfservice@adminrealm", "password": "test"}):
            helpdesk_token = self.app.full_dispatch_request().json["result"]["value"]["token"]
        # The login above logged its own auth event; clear so the test works on controlled entries only.
        self._clear_log()
        # One in-scope (realm1) entry and the admin's own entry (username=selfservice, realm=adminrealm).
        in_scope = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver=self.resolvername1,
                                            uid="1", realm=self.realm1)
        own = log_authentication_event(event_type=AuthEventType.LOGIN_SUCCESS, resolver=self.resolvername1, uid="2",
                                       realm="adminrealm", username="selfservice")
        db.session.commit()
        set_policy("authlog_realm", scope=SCOPE.ADMIN, action=PolicyAction.AUTHENTICATION_LOG_READ, realm=self.realm1)

        def helpdesk_get(query_string):
            with self.app.test_request_context("/authenticationlog/", method="GET", query_string=query_string,
                                               headers={"Authorization": helpdesk_token}):
                res = self.app.full_dispatch_request()
                self.assertEqual(200, res.status_code, res.json)
                return {entry["id"] for entry in res.json["result"]["value"]["auth_logs"]}

        try:
            # The realm1 entry (policy scope) plus the admin's own adminrealm entry are both returned.
            self.assertEqual({in_scope, own}, helpdesk_get({"page_size": 50}))
        finally:
            delete_policy("authlog_realm")
            delete_realm("adminrealm")


    def test_user_sees_only_own_entries(self):
        # Log in the self-service user "selfservice" in realm1 (-> self.at_user); that login writes its own auth-log
        # entry, so clear the log to test on controlled entries only.
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
