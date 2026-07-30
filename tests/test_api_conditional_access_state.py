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
Tests for the ``/conditionalaccess/lockout/*`` and ``/conditionalaccess/blocklist``
REST endpoints: listing and resetting the live user-lockout state and blocklist,
plus the per-domain admin-policy gate (``user_lockout_read`` / ``user_lockout_reset``
/ ``blocklist_read`` / ``blocklist_reset``) and the admin-only access restriction.

Each endpoint x case has its own test method so a failure names exactly the
endpoint and case that broke.
"""
from datetime import timedelta

from werkzeug.test import TestResponse

from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import SCOPE, set_policy, delete_policy
from privacyidea.lib.user import User
from privacyidea.models import db
from privacyidea.models.authentication_log import AuthenticationLog
from privacyidea.models.lockout_policy import (
    BlockList,
    LockoutPolicy,
    LockoutPolicyCounterType,
    LockoutPolicyStage,
    LockoutStageAction,
    UserLockoutState,
)
from privacyidea.models.utils import utc_now
from .base import MyApiTestCase


class ConditionalAccessStateApiTestCase(MyApiTestCase):

    def setUp(self):
        super().setUp()
        self.setUp_user_realms()
        self.authenticate()
        self.user = User("cornelius", self.realm1, self.resolvername1)
        self._clear()

    def tearDown(self):
        self._clear()
        super().tearDown()

    @staticmethod
    def _clear() -> None:
        for model in (UserLockoutState, BlockList, LockoutStageAction, LockoutPolicyStage,
                      LockoutPolicyCounterType, LockoutPolicy, AuthenticationLog):
            db.session.query(model).delete()
        db.session.commit()

    def _request(self, path: str, method: str = "GET", json_data: dict | None = None,
                 query_string: dict | None = None, auth_token: str | None = None) -> TestResponse:
        kwargs: dict = {"method": method, "headers": {"Authorization": auth_token or self.at}}
        if json_data is not None:
            kwargs["json"] = json_data
        if query_string is not None:
            kwargs["query_string"] = query_string
        with self.app.test_request_context(f"/conditionalaccess/{path}", **kwargs):
            return self.app.full_dispatch_request()

    def _lock_user(self, lock_expires_at, user=None) -> None:
        user = user or self.user
        db.session.add(UserLockoutState(resolver=user.resolver, uid=user.uid, realm=user.realm, username=user.login,
                                        lock_expires_at=lock_expires_at))
        db.session.commit()

    def _block(self, ip, block_expires_at) -> None:
        db.session.add(BlockList(ip=ip, block_expires_at=block_expires_at))
        db.session.commit()

    # --- GET lockout/users ----------------------------------------------------

    def test_list_locked_users_empty(self):
        res = self._request("lockout/users")
        self.assertEqual(200, res.status_code, res.json)
        page = res.json["result"]["value"]
        self.assertListEqual([], page["locked_users"])
        self.assertEqual(0, page["count"])

    def test_list_locked_users_returns_locked(self):
        self._lock_user(utc_now() + timedelta(seconds=600))
        page = self._request("lockout/users").json["result"]["value"]
        self.assertEqual(1, page["count"])
        self.assertEqual("cornelius", page["locked_users"][0]["username"])
        self.assertEqual(self.user.realm, page["locked_users"][0]["realm"])

    def test_single_user_lookup_locked(self):
        self._lock_user(utc_now() + timedelta(seconds=600))
        res = self._request("lockout/user",
                            query_string={"user": "cornelius", "realm": self.realm1})
        value = res.json["result"]["value"]
        self.assertIsNotNone(value)
        self.assertEqual("cornelius", value["username"])
        self.assertFalse(value["permanent"])

    def test_single_user_lookup_not_locked_is_null(self):
        res = self._request("lockout/user",
                            query_string={"user": "cornelius", "realm": self.realm1})
        self.assertEqual(200, res.status_code, res.json)
        self.assertIsNone(res.json["result"]["value"])

    def test_list_locked_users_username_filter(self):
        self._lock_user(utc_now() + timedelta(seconds=600))
        db.session.add(UserLockoutState(resolver="r", uid="7", realm="realm2", username="hans",
                                        lock_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        page = self._request("lockout/users",
                             query_string={"usernames": "cornelius"}).json["result"]["value"]
        self.assertEqual(1, page["count"])
        self.assertEqual("cornelius", page["locked_users"][0]["username"])

    def test_list_locked_users_paginated(self):
        for i in range(5):
            db.session.add(UserLockoutState(resolver="r", uid=str(100 + i), realm="realm2", username=f"u{i}",
                                            lock_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        page = self._request("lockout/users",
                             query_string={"page": "1", "page_size": "2", "sort_column": "username",
                                           "sort_order": "asc"}).json["result"]["value"]
        self.assertEqual(5, page["count"])
        self.assertEqual(2, len(page["locked_users"]))
        self.assertEqual(2, page["next"])
        self.assertIsNone(page["prev"])

    def test_list_locked_users_case_insensitive(self):
        self._lock_user(utc_now() + timedelta(seconds=600))
        sensitive = self._request("lockout/users",
                                  query_string={"usernames": "CORNELIUS"}).json["result"][
            "value"]
        self.assertEqual(0, sensitive["count"])
        insensitive = self._request("lockout/users",
                                    query_string={"usernames": "CORNELIUS", "case_insensitive": "1"}
                                    ).json["result"]["value"]
        self.assertEqual(1, insensitive["count"])

    def test_list_locked_users_states_filter(self):
        self._lock_user(utc_now() - timedelta(seconds=60))
        # No states filter -> all states, so the expired lock is returned.
        default = self._request("lockout/users").json["result"]["value"]["locked_users"]
        self.assertEqual(1, len(default))
        self.assertEqual(0, default[0]["seconds_remaining"])
        # Restricting to the currently-locked states hides it.
        hidden = self._request(
            "lockout/users", query_string={"states": "permanent,temporary"}
        ).json["result"]["value"]["locked_users"]
        self.assertListEqual([], hidden)

    def test_purge_user_lockouts(self):
        self._lock_user(utc_now() - timedelta(seconds=60))  # expired -> purged
        db.session.add(UserLockoutState(resolver="r", uid="2", realm="realm2",
                                        lock_expires_at=utc_now() + timedelta(seconds=600)))  # active
        db.session.commit()
        res = self._request("lockout/users/purge", method="POST")
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual(1, res.json["result"]["value"])
        self.assertIsNone(db.session.get(UserLockoutState, (self.user.resolver, self.user.uid, self.user.realm)))
        self.assertIsNotNone(db.session.get(UserLockoutState, ("r", "2", "realm2")))
        self.assertEqual(1, UserLockoutState.query.count())

    # --- DELETE lockout/user --------------------------------------------------

    def test_reset_user_by_login(self):
        self._lock_user(utc_now() + timedelta(seconds=600))
        res = self._request("lockout/user", method="DELETE",
                            json_data={"user": "cornelius", "realm": self.realm1, "resolver": self.resolvername1})
        self.assertEqual(200, res.status_code, res.json)
        self.assertTrue(res.json["result"]["value"])
        self.assertIsNone(db.session.get(
            UserLockoutState, (self.user.resolver, self.user.uid, self.user.realm)))
        self.assertEqual(0, UserLockoutState.query.count())

    def test_reset_user_by_raw_id(self):
        self._lock_user(utc_now() + timedelta(seconds=600))
        res = self._request("lockout/user", method="DELETE",
                            json_data={"resolver": self.user.resolver, "user_id": self.user.uid,
                                       "realm": self.user.realm})
        self.assertEqual(200, res.status_code, res.json)
        self.assertTrue(res.json["result"]["value"])
        self.assertEqual(0, UserLockoutState.query.count())

    def test_reset_user_by_login_without_resolver(self):
        # resolver is an optional disambiguator: a login+realm reset must work without it.
        self._lock_user(utc_now() + timedelta(seconds=600))
        res = self._request("lockout/user", method="DELETE",
                            json_data={"user": "cornelius", "realm": self.realm1})
        self.assertEqual(200, res.status_code, res.json)
        self.assertTrue(res.json["result"]["value"])
        self.assertIsNone(db.session.get(UserLockoutState, (self.user.resolver, self.user.uid, self.user.realm)))
        self.assertEqual(0, UserLockoutState.query.count())

    def test_reset_user_by_raw_id_without_resolver(self):
        # Same for the uid path: resolver is optional there too.
        self._lock_user(utc_now() + timedelta(seconds=600))
        res = self._request("lockout/user", method="DELETE",
                            json_data={"user_id": self.user.uid, "realm": self.user.realm})
        self.assertEqual(200, res.status_code, res.json)
        self.assertTrue(res.json["result"]["value"])
        self.assertEqual(0, UserLockoutState.query.count())

    def test_reset_user_not_locked_returns_false(self):
        res = self._request("lockout/user", method="DELETE",
                            json_data={"user": "cornelius", "realm": self.realm1, "resolver": self.resolvername1})
        self.assertEqual(200, res.status_code, res.json)
        self.assertFalse(res.json["result"]["value"])
        self.assertEqual(0, UserLockoutState.query.count())

    # --- GET blocklist --------------------------------------------------------

    def test_list_blocklist(self):
        self._block("203.0.113.7", utc_now() + timedelta(seconds=600))
        res = self._request("blocklist")
        value = res.json["result"]["value"]
        self.assertEqual(1, len(value))
        self.assertEqual("203.0.113.7", value[0]["identifier"])

    # --- DELETE blocklist/<entry> ---------------------------------------------

    def test_remove_blocklist_entry(self):
        self._block("203.0.113.7", utc_now() + timedelta(seconds=600))
        res = self._request("blocklist/203.0.113.7", method="DELETE")
        self.assertEqual(200, res.status_code, res.json)
        self.assertTrue(res.json["result"]["value"])
        self.assertIsNone(db.session.get(BlockList, "203.0.113.7"))
        self.assertEqual(0, BlockList.query.count())

    def test_remove_missing_blocklist_entry_returns_false(self):
        self._block("203.0.113.7", utc_now() + timedelta(seconds=600))
        res = self._request("blocklist/203.0.113.9", method="DELETE")
        self.assertEqual(200, res.status_code, res.json)
        self.assertFalse(res.json["result"]["value"])
        # The unrelated entry must not be touched.
        self.assertIsNotNone(db.session.get(BlockList, "203.0.113.7"))
        self.assertEqual(1, BlockList.query.count())

    def test_purge_blocklist(self):
        self._block("203.0.113.1", utc_now() - timedelta(seconds=60))  # expired -> purged
        self._block("203.0.113.2", utc_now() + timedelta(seconds=600))  # active -> kept
        res = self._request("blocklist/purge", method="POST")
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual(1, res.json["result"]["value"])
        self.assertIsNone(db.session.get(BlockList, "203.0.113.1"))
        self.assertIsNotNone(db.session.get(BlockList, "203.0.113.2"))
        self.assertEqual(1, BlockList.query.count())

    # --- admin-only + per-domain policy gate ----------------------------------

    def test_requires_admin(self):
        self.authenticate_selfservice_user()
        res = self._request("lockout/users", auth_token=self.at_user)
        self.assertEqual(401, res.status_code, res.json)

    def test_read_action_does_not_grant_reset(self):
        # An admin policy that grants only the read actions must block the resets.
        self._lock_user(utc_now() + timedelta(seconds=600))
        self._block("203.0.113.7", utc_now() + timedelta(seconds=600))
        set_policy("ca_state_read", scope=SCOPE.ADMIN,
                   action=f"{PolicyAction.USER_LOCKOUT_READ},{PolicyAction.BLOCKLIST_READ}")
        try:
            self.assertEqual(200, self._request("lockout/users").status_code)
            self.assertEqual(200, self._request("blocklist").status_code)
            reset = self._request("lockout/user", method="DELETE",
                                  json_data={"user": "cornelius", "realm": self.realm1})
            self.assertEqual(403, reset.status_code, reset.json)
            unblock = self._request("blocklist/203.0.113.7", method="DELETE")
            self.assertEqual(403, unblock.status_code, unblock.json)
            self.assertEqual(403, self._request("lockout/users/purge", method="POST").status_code)
            self.assertEqual(403, self._request("blocklist/purge", method="POST").status_code)
        finally:
            delete_policy("ca_state_read")
        # Every rejected call must have left the state untouched.
        self.assertEqual(1, UserLockoutState.query.count())
        self.assertEqual(1, BlockList.query.count())

    def test_list_is_constrained_to_policy_visibility_scope(self):
        # Lock a user in realm1 and a raw row in another realm.
        self._lock_user(utc_now() + timedelta(seconds=600))
        db.session.add(UserLockoutState(resolver="other", uid="7", realm="otherrealm",
                                        lock_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        # An admin whose read action is scoped to realm1 only sees the realm1 lock.
        set_policy("ca_state_realm1", scope=SCOPE.ADMIN,
                   action=str(PolicyAction.USER_LOCKOUT_READ), realm=self.realm1)
        try:
            users = self._request("lockout/users").json["result"]["value"]["locked_users"]
            self.assertEqual(1, len(users))
            self.assertEqual(self.realm1, users[0]["realm"])
        finally:
            delete_policy("ca_state_realm1")
        # The scope narrows the view, not the data: both rows are still there.
        self.assertEqual(2, UserLockoutState.query.count())

    def test_reset_only_clears_rows_inside_the_resolver_scope(self):
        # The boundary must be part of the delete criterion, not a pre-flight check on one identity:
        # a resolver-scoped admin resetting by login+realm (no resolver) matches rows in every
        # resolver of the realm, and must only clear their own.
        self._lock_user(utc_now() + timedelta(seconds=600))
        db.session.add(UserLockoutState(resolver="otherresolver", uid="99", realm=self.realm1,
                                        username="cornelius",
                                        lock_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        set_policy("ca_reset_resolver1", scope=SCOPE.ADMIN,
                   action=str(PolicyAction.USER_LOCKOUT_RESET), resolver=self.resolvername1)
        try:
            res = self._request("lockout/user", method="DELETE",
                                json_data={"user": "cornelius", "realm": self.realm1})
            self.assertEqual(200, res.status_code, res.json)
            self.assertTrue(res.json["result"]["value"])
        finally:
            delete_policy("ca_reset_resolver1")
        # The in-scope row is gone, the out-of-scope one survives, and nothing else was touched.
        self.assertIsNone(db.session.get(UserLockoutState, (self.user.resolver, self.user.uid, self.user.realm)))
        self.assertIsNotNone(db.session.get(UserLockoutState, ("otherresolver", "99", self.realm1)))
        self.assertEqual(1, UserLockoutState.query.count())

    def test_reset_outside_the_scope_reports_no_lock_removed(self):
        # An out-of-scope target is indistinguishable from an absent lock: false, and the row stays.
        # The only matching lock lives in a resolver outside the admin's scope.
        db.session.add(UserLockoutState(resolver="otherresolver", uid="99", realm=self.realm1, username="cornelius",
                                        lock_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        set_policy("ca_reset_resolver1", scope=SCOPE.ADMIN, action=str(PolicyAction.USER_LOCKOUT_RESET),
                   resolver=self.resolvername1)
        try:
            # No resolver in the request, so only the visibility scope keeps this row out of reach.
            res = self._request("lockout/user", method="DELETE",
                                json_data={"user": "cornelius", "realm": self.realm1})
            self.assertEqual(200, res.status_code, res.json)
            self.assertFalse(res.json["result"]["value"])
        finally:
            delete_policy("ca_reset_resolver1")
        # Deliberately the only row in play: adding an in-scope one would make the reset succeed and
        # turn this into test_reset_only_clears_rows_inside_the_resolver_scope. Here nothing may go.
        self.assertIsNotNone(db.session.get(UserLockoutState, ("otherresolver", "99", self.realm1)))
        self.assertEqual(1, UserLockoutState.query.count())

    def test_purge_is_constrained_to_policy_visibility_scope(self):
        # A scoped admin only purges the stale rows inside their boundary.
        self._lock_user(utc_now() - timedelta(seconds=60))  # expired, in scope
        db.session.add(UserLockoutState(resolver="otherresolver", uid="99", realm=self.realm1, username="hans",
                                        lock_expires_at=utc_now() - timedelta(seconds=60)))  # expired, out of scope
        db.session.commit()
        set_policy("ca_reset_resolver1", scope=SCOPE.ADMIN,
                   action=str(PolicyAction.USER_LOCKOUT_RESET), resolver=self.resolvername1)
        try:
            res = self._request("lockout/users/purge", method="POST")
            self.assertEqual(200, res.status_code, res.json)
            self.assertEqual(1, res.json["result"]["value"])
        finally:
            delete_policy("ca_reset_resolver1")
        # The in-scope stale row is gone, the out-of-scope one survives, and nothing else was touched.
        self.assertIsNone(db.session.get(UserLockoutState, (self.user.resolver, self.user.uid, self.user.realm)))
        self.assertIsNotNone(db.session.get(UserLockoutState, ("otherresolver", "99", self.realm1)))
        self.assertEqual(1, UserLockoutState.query.count())

    def test_user_lockout_action_does_not_grant_blocklist(self):
        # Per-domain gating: the user-lockout read action must not open the blocklist.
        set_policy("ca_user_only", scope=SCOPE.ADMIN,
                   action=str(PolicyAction.USER_LOCKOUT_READ))
        try:
            self.assertEqual(200, self._request("lockout/users").status_code)
            self.assertEqual(403, self._request("blocklist").status_code)
        finally:
            delete_policy("ca_user_only")
