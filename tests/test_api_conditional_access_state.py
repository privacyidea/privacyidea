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
Tests for the ``/conditionalaccess/lock/*`` and ``/conditionalaccess/blocklist``
REST endpoints: listing and resetting the live user-lock state and blocklist,
plus the per-domain admin-policy gate (``user_lock_read`` / ``user_lock_reset``
/ ``blocklist_read`` / ``blocklist_reset``) and the admin-only access restriction.

Each endpoint x case has its own test method so a failure names exactly the
endpoint and case that broke.
"""
from datetime import timedelta

from werkzeug.test import TestResponse

from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import SCOPE, set_policy, delete_policy
from privacyidea.lib.conditional_access.authentication_event_types import RestrictionCause
from privacyidea.lib.user import User
from privacyidea.models import db
from privacyidea.models.audit import Audit
from privacyidea.models.authentication_log import AuthenticationLog
from privacyidea.models.conditional_access_policy import (
    BlockList,
    ConditionalAccessPolicy,
    ConditionalAccessPolicyCounterType,
    ConditionalAccessPolicyStage,
    ConditionalAccessStageAction,
    UserLockState,
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
        for model in (UserLockState, BlockList, ConditionalAccessStageAction, ConditionalAccessPolicyStage,
                      ConditionalAccessPolicyCounterType, ConditionalAccessPolicy, AuthenticationLog):
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
        db.session.add(UserLockState(resolver=user.resolver, uid=user.uid, realm=user.realm, username=user.login,
                                        lock_expires_at=lock_expires_at))
        db.session.commit()

    def _block(self, ip, block_expires_at) -> None:
        db.session.add(BlockList(ip=ip, block_expires_at=block_expires_at))
        db.session.commit()

    # --- GET lock/users ----------------------------------------------------

    def test_list_locked_users_empty(self):
        res = self._request("lock/users")
        self.assertEqual(200, res.status_code, res.json)
        page = res.json["result"]["value"]
        self.assertListEqual([], page["locked_users"])
        self.assertEqual(0, page["count"])

    def test_list_locked_users_returns_locked(self):
        self._lock_user(utc_now() + timedelta(seconds=600))
        page = self._request("lock/users").json["result"]["value"]
        self.assertEqual(1, page["count"])
        self.assertEqual("cornelius", page["locked_users"][0]["username"])
        self.assertEqual(self.user.realm, page["locked_users"][0]["realm"])

    def test_single_user_lookup_locked(self):
        self._lock_user(utc_now() + timedelta(seconds=600))
        res = self._request("lock/user",
                            query_string={"user": "cornelius", "realm": self.realm1})
        value = res.json["result"]["value"]
        self.assertIsNotNone(value)
        self.assertEqual("cornelius", value["username"])
        self.assertFalse(value["permanent"])

    def test_single_user_lookup_not_locked_is_null(self):
        res = self._request("lock/user",
                            query_string={"user": "cornelius", "realm": self.realm1})
        self.assertEqual(200, res.status_code, res.json)
        self.assertIsNone(res.json["result"]["value"])

    def test_single_user_lookup_by_uid_needs_a_resolver(self):
        # A uid is only unique within its resolver, so User() cannot be built from one alone. The
        # endpoint has to reject that up front instead of letting a UserError escape the lookup.
        self._lock_user(utc_now() + timedelta(seconds=600))
        res = self._request("lock/user",
                            query_string={"user_id": self.user.uid, "realm": self.realm1})
        self.assertEqual(400, res.status_code, res.json)
        self.assertIn("resolver", res.json["result"]["error"]["message"])

    def test_single_user_lookup_by_uid_needs_a_resolver_even_with_username(self):
        # A username alongside the uid does not relax the requirement: the two are not cross-checked
        # against each other, so the uid alone still needs its resolver to be unambiguous.
        self._lock_user(utc_now() + timedelta(seconds=600))
        res = self._request("lock/user",
                            query_string={"user_id": self.user.uid, "username": "cornelius",
                                          "realm": self.realm1})
        self.assertEqual(400, res.status_code, res.json)
        self.assertIn("resolver", res.json["result"]["error"]["message"])

    def test_single_user_lookup_prefers_username_over_legacy_user(self):
        # 'username' is the documented, authoritative key; the legacy 'user' must not silently win just
        # because it also happens to resolve to a real account.
        hans = User("hans", self.realm1, self.resolvername1)
        self._lock_user(utc_now() + timedelta(seconds=600), user=hans)
        res = self._request("lock/user",
                            query_string={"user": "hans", "username": "cornelius", "realm": self.realm1})
        self.assertEqual(200, res.status_code, res.json)
        # cornelius (the 'username' target) is not locked, so the answer is null - not hans's lock.
        self.assertIsNone(res.json["result"]["value"])

    def test_single_user_lookup_by_uid_with_resolver(self):
        self._lock_user(utc_now() + timedelta(seconds=600))
        res = self._request("lock/user",
                            query_string={"user_id": self.user.uid, "realm": self.realm1,
                                          "resolver": self.user.resolver})
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual("cornelius", res.json["result"]["value"]["username"])

    def test_list_locked_users_unknown_state_is_rejected(self):
        res = self._request("lock/users", query_string={"states": "bogus"})
        self.assertEqual(400, res.status_code, res.json)

    def test_list_locked_users_username_filter(self):
        self._lock_user(utc_now() + timedelta(seconds=600))
        db.session.add(UserLockState(resolver="r", uid="7", realm="realm2", username="hans",
                                        lock_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        page = self._request("lock/users",
                             query_string={"usernames": "cornelius"}).json["result"]["value"]
        self.assertEqual(1, page["count"])
        self.assertEqual("cornelius", page["locked_users"][0]["username"])

    def test_list_locked_users_paginated(self):
        for i in range(5):
            db.session.add(UserLockState(resolver="r", uid=str(100 + i), realm="realm2", username=f"u{i}",
                                            lock_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        page = self._request("lock/users",
                             query_string={"page": "1", "page_size": "2", "sort_column": "username",
                                           "sort_order": "asc"}).json["result"]["value"]
        self.assertEqual(5, page["count"])
        self.assertEqual(2, len(page["locked_users"]))
        self.assertEqual(2, page["next"])
        self.assertIsNone(page["prev"])

    def test_list_locked_users_case_insensitive(self):
        self._lock_user(utc_now() + timedelta(seconds=600))
        sensitive = self._request("lock/users",
                                  query_string={"usernames": "CORNELIUS"}).json["result"][
            "value"]
        self.assertEqual(0, sensitive["count"])
        insensitive = self._request("lock/users",
                                    query_string={"usernames": "CORNELIUS", "case_insensitive": "1"}
                                    ).json["result"]["value"]
        self.assertEqual(1, insensitive["count"])

    def test_list_locked_users_states_filter(self):
        self._lock_user(utc_now() - timedelta(seconds=60))
        # No states filter -> all states, so the expired lock is returned.
        default = self._request("lock/users").json["result"]["value"]["locked_users"]
        self.assertEqual(1, len(default))
        self.assertEqual(0, default[0]["seconds_remaining"])
        # Restricting to the currently-locked states hides it.
        hidden = self._request(
            "lock/users", query_string={"states": "permanent,temporary"}
        ).json["result"]["value"]["locked_users"]
        self.assertListEqual([], hidden)

    def test_purge_user_locks(self):
        self._lock_user(utc_now() - timedelta(seconds=60))  # expired -> purged
        db.session.add(UserLockState(resolver="r", uid="2", realm="realm2",
                                        lock_expires_at=utc_now() + timedelta(seconds=600)))  # active
        db.session.commit()
        res = self._request("lock/users/purge", method="POST")
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual(1, res.json["result"]["value"])
        self.assertIsNone(db.session.get(UserLockState, (self.user.resolver, self.user.uid, self.user.realm)))
        self.assertIsNotNone(db.session.get(UserLockState, ("r", "2", "realm2")))
        self.assertEqual(1, UserLockState.query.count())

    # --- DELETE lock/user --------------------------------------------------

    def test_reset_user_by_login(self):
        self._lock_user(utc_now() + timedelta(seconds=600))
        res = self._request("lock/user", method="DELETE",
                            json_data={"user": "cornelius", "realm": self.realm1, "resolver": self.resolvername1})
        self.assertEqual(200, res.status_code, res.json)
        self.assertTrue(res.json["result"]["value"])
        self.assertIsNone(db.session.get(
            UserLockState, (self.user.resolver, self.user.uid, self.user.realm)))
        self.assertEqual(0, UserLockState.query.count())

    def test_reset_user_by_raw_id(self):
        self._lock_user(utc_now() + timedelta(seconds=600))
        res = self._request("lock/user", method="DELETE",
                            json_data={"resolver": self.user.resolver, "user_id": self.user.uid,
                                       "realm": self.user.realm})
        self.assertEqual(200, res.status_code, res.json)
        self.assertTrue(res.json["result"]["value"])
        self.assertEqual(0, UserLockState.query.count())

    def test_reset_user_by_login_without_resolver(self):
        # resolver is an optional disambiguator: a login+realm reset must work without it.
        self._lock_user(utc_now() + timedelta(seconds=600))
        res = self._request("lock/user", method="DELETE",
                            json_data={"user": "cornelius", "realm": self.realm1})
        self.assertEqual(200, res.status_code, res.json)
        self.assertTrue(res.json["result"]["value"])
        self.assertIsNone(db.session.get(UserLockState, (self.user.resolver, self.user.uid, self.user.realm)))
        self.assertEqual(0, UserLockState.query.count())

    def test_reset_user_by_raw_id_without_resolver(self):
        # Same for the uid path: resolver is optional there too.
        self._lock_user(utc_now() + timedelta(seconds=600))
        res = self._request("lock/user", method="DELETE",
                            json_data={"user_id": self.user.uid, "realm": self.user.realm})
        self.assertEqual(200, res.status_code, res.json)
        self.assertTrue(res.json["result"]["value"])
        self.assertEqual(0, UserLockState.query.count())

    def test_reset_user_by_raw_id_zero(self):
        # user_id is checked with `is not None`, not truthiness: a resolver-local uid of 0 is a valid
        # identifier and must take the id lookup, not fall through to a username of None.
        db.session.add(UserLockState(resolver=self.resolvername1, uid="0", realm=self.realm1,
                                     username="zerouser", lock_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        res = self._request("lock/user", method="DELETE",
                            json_data={"resolver": self.resolvername1, "user_id": 0, "realm": self.realm1})
        self.assertEqual(200, res.status_code, res.json)
        self.assertTrue(res.json["result"]["value"])
        self.assertEqual(0, UserLockState.query.count())

    def test_reset_user_not_locked_returns_false(self):
        res = self._request("lock/user", method="DELETE",
                            json_data={"user": "cornelius", "realm": self.realm1, "resolver": self.resolvername1})
        self.assertEqual(200, res.status_code, res.json)
        self.assertFalse(res.json["result"]["value"])
        self.assertEqual(0, UserLockState.query.count())

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
        res = self._request("lock/users", auth_token=self.at_user)
        self.assertEqual(401, res.status_code, res.json)

    # --- POST lock/user (the manual lock) ----------------------------------

    def test_set_user_lock_locks_permanently_by_default(self):
        res = self._request("lock/user", method="POST",
                            json_data={"user": "cornelius", "realm": self.realm1})
        self.assertEqual(200, res.status_code, res.json)
        value = res.json["result"]["value"]
        self.assertTrue(value["permanent"])
        self.assertEqual(RestrictionCause.MANUAL, value["lock_cause"])
        self.assertEqual(RestrictionCause.MANUAL, UserLockState.query.one().lock_cause)

    def test_set_user_lock_records_the_username_in_the_audit_log(self):
        # A request identifying its target by 'username' must not leave the audit log's structured
        # 'user' column blank - the free-text 'info' naming the user is not a substitute for it.
        res = self._request("lock/user", method="POST",
                            json_data={"username": "cornelius", "realm": self.realm1})
        self.assertEqual(200, res.status_code, res.json)
        entry = Audit.query.order_by(Audit.id.desc()).first()
        self.assertEqual("cornelius", entry.user)
        self.assertEqual(self.realm1, entry.realm)

    def test_set_user_lock_with_a_duration(self):
        res = self._request("lock/user", method="POST",
                            json_data={"user": "cornelius", "realm": self.realm1, "duration_seconds": 600})
        self.assertEqual(200, res.status_code, res.json)
        self.assertFalse(res.json["result"]["value"]["permanent"])

    def test_set_user_lock_rejects_a_bad_duration(self):
        for duration in ("soon", 0, -5):
            res = self._request("lock/user", method="POST",
                                json_data={"user": "cornelius", "realm": self.realm1,
                                           "duration_seconds": duration})
            self.assertEqual(400, res.status_code, res.json)
        self.assertEqual(0, UserLockState.query.count())

    def test_set_user_lock_by_uid_needs_a_resolver(self):
        res = self._request("lock/user", method="POST",
                            json_data={"user_id": self.user.uid, "realm": self.realm1})
        self.assertEqual(400, res.status_code, res.json)

    def test_set_user_lock_by_uid_needs_a_resolver_even_with_username(self):
        # A uid is only unique within its resolver, so it still needs one even when a username is also given -
        # the two are not cross-checked against each other.
        res = self._request("lock/user", method="POST",
                            json_data={"user_id": self.user.uid, "username": "cornelius", "realm": self.realm1})
        self.assertEqual(400, res.status_code, res.json)

    def test_set_user_lock_for_an_unknown_user_is_400(self):
        res = self._request("lock/user", method="POST",
                            json_data={"user": "nosuchuser", "realm": self.realm1})
        self.assertEqual(400, res.status_code, res.json)
        self.assertEqual(0, UserLockState.query.count())

    def test_set_user_lock_is_visible_on_the_list(self):
        self._request("lock/user", method="POST", json_data={"user": "cornelius", "realm": self.realm1})
        page = self._request("lock/users", query_string={"causes": "MANUAL"}).json["result"]["value"]
        self.assertEqual(1, page["count"])
        self.assertEqual(RestrictionCause.MANUAL, page["locked_users"][0]["lock_cause"])
        page = self._request("lock/users", query_string={"causes": "POLICY"}).json["result"]["value"]
        self.assertEqual(0, page["count"])

    def test_list_locked_users_rejects_an_unknown_cause(self):
        res = self._request("lock/users", query_string={"causes": "ADMIN"})
        self.assertEqual(400, res.status_code, res.json)

    # --- POST blocklist (the manual block) -------------------------------------

    def test_add_blocklist_entry(self):
        res = self._request("blocklist", method="POST",
                            json_data={"ip": "203.0.113.9", "duration_seconds": 300})
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual(RestrictionCause.MANUAL, res.json["result"]["value"]["block_cause"])
        self.assertEqual("203.0.113.9", BlockList.query.one().ip)

    def test_add_blocklist_entry_refuses_a_never_block_ip(self):
        res = self._request("blocklist", method="POST", json_data={"ip": "127.0.0.1"})
        self.assertEqual(400, res.status_code, res.json)
        self.assertEqual(0, BlockList.query.count())

    def test_add_blocklist_entry_rejects_an_invalid_ip(self):
        res = self._request("blocklist", method="POST", json_data={"ip": "not-an-ip"})
        self.assertEqual(400, res.status_code, res.json)

    def test_read_and_reset_do_not_grant_set(self):
        # Clearing a restriction is recoverable, imposing one is not, so the rights are separate.
        set_policy("ca_state_no_set", scope=SCOPE.ADMIN,
                   action=f"{PolicyAction.USER_LOCK_READ},{PolicyAction.USER_LOCK_RESET},"
                          f"{PolicyAction.BLOCKLIST_READ},{PolicyAction.BLOCKLIST_RESET}")
        try:
            lock = self._request("lock/user", method="POST",
                                 json_data={"user": "cornelius", "realm": self.realm1})
            self.assertEqual(403, lock.status_code, lock.json)
            block = self._request("blocklist", method="POST", json_data={"ip": "203.0.113.9"})
            self.assertEqual(403, block.status_code, block.json)
        finally:
            delete_policy("ca_state_no_set")
        self.assertEqual(0, UserLockState.query.count())
        self.assertEqual(0, BlockList.query.count())

    def test_user_lock_set_does_not_grant_blocklist_set(self):
        set_policy("ca_state_lock_only", scope=SCOPE.ADMIN, action=str(PolicyAction.USER_LOCK_SET))
        try:
            lock = self._request("lock/user", method="POST",
                                 json_data={"user": "cornelius", "realm": self.realm1})
            self.assertEqual(200, lock.status_code, lock.json)
            block = self._request("blocklist", method="POST", json_data={"ip": "203.0.113.9"})
            self.assertEqual(403, block.status_code, block.json)
        finally:
            delete_policy("ca_state_lock_only")

    def test_set_user_lock_by_uid_zero_still_needs_a_resolver(self):
        # user_id is checked with `is not None`, not truthiness, so a JSON 0 must not be mistaken for
        # "no user_id was given" and skip the resolver requirement - not even when a username is also
        # given, which would otherwise let User() silently re-resolve by login and ignore the uid.
        res = self._request("lock/user", method="POST",
                            json_data={"user_id": 0, "username": "cornelius", "realm": self.realm1})
        self.assertEqual(400, res.status_code, res.json)
        self.assertIn("resolver", res.json["result"]["error"]["message"])
        self.assertEqual(0, UserLockState.query.count())

    def test_set_user_lock_outside_the_visibility_scope_is_refused(self):
        # A write has exactly one target, so an out-of-scope one is refused loudly rather than silently
        # doing nothing - a lock that did not happen must not look like one that did.
        set_policy("ca_state_scoped_set", scope=SCOPE.ADMIN, action=str(PolicyAction.USER_LOCK_SET),
                   user="someoneelse")
        try:
            res = self._request("lock/user", method="POST",
                                json_data={"user": "cornelius", "realm": self.realm1})
            self.assertEqual(403, res.status_code, res.json)
        finally:
            delete_policy("ca_state_scoped_set")
        self.assertEqual(0, UserLockState.query.count())

    # --- the unambiguous 'username' key (with 'user' kept for compatibility) -----

    def test_set_user_lock_accepts_the_username_param(self):
        # 'username' is the preferred, unambiguous key; 'user' stays accepted (tested elsewhere).
        res = self._request("lock/user", method="POST",
                            json_data={"username": "cornelius", "realm": self.realm1})
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual("cornelius", UserLockState.query.one().username)

    def test_get_user_lock_accepts_the_username_param(self):
        self._lock_user(utc_now() + timedelta(seconds=600))
        res = self._request("lock/user",
                            query_string={"username": "cornelius", "realm": self.realm1})
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual("cornelius", res.json["result"]["value"]["username"])

    def test_reset_user_lock_accepts_the_username_param(self):
        self._lock_user(utc_now() + timedelta(seconds=600))
        res = self._request("lock/user", method="DELETE",
                            json_data={"username": "cornelius", "realm": self.realm1})
        self.assertEqual(200, res.status_code, res.json)
        self.assertTrue(res.json["result"]["value"])
        self.assertEqual(0, UserLockState.query.count())

    def test_set_user_lock_by_uid_locks_the_resolved_user(self):
        # The uid path resolves to the same user as the login path (username vs uid input).
        res = self._request("lock/user", method="POST",
                            json_data={"user_id": self.user.uid, "realm": self.realm1,
                                       "resolver": self.user.resolver})
        self.assertEqual(200, res.status_code, res.json)
        self.assertEqual("cornelius", UserLockState.query.one().username)

    # --- the scope check precedes (and shields) the existence check --------------

    def test_set_user_lock_out_of_scope_error_does_not_disclose_the_user(self):
        # The refusal echoes only what the caller sent (username, realm), never a resolved identifier
        # (resolver/uid) nor whether the user exists - an out-of-scope admin must learn neither.
        set_policy("ca_state_scoped_set", scope=SCOPE.ADMIN, action=str(PolicyAction.USER_LOCK_SET),
                   user="someoneelse")
        try:
            res = self._request("lock/user", method="POST",
                                json_data={"username": "cornelius", "realm": self.realm1})
            self.assertEqual(403, res.status_code, res.json)
            message = res.json["result"]["error"]["message"]
            self.assertNotIn(self.resolvername1, message)
            self.assertNotIn("does not exist", message)
        finally:
            delete_policy("ca_state_scoped_set")
        self.assertEqual(0, UserLockState.query.count())

    def test_set_user_lock_out_of_scope_hides_a_nonexistent_user(self):
        # An out-of-scope user and a user that does not exist must be indistinguishable: both 403, so the
        # scope check runs before the existence check rather than leaking existence through a 400/403 split.
        set_policy("ca_state_scoped_set", scope=SCOPE.ADMIN, action=str(PolicyAction.USER_LOCK_SET),
                   user="someoneelse")
        try:
            existing = self._request("lock/user", method="POST",
                                     json_data={"username": "cornelius", "realm": self.realm1})
            missing = self._request("lock/user", method="POST",
                                    json_data={"username": "nosuchuser", "realm": self.realm1})
            self.assertEqual(403, existing.status_code, existing.json)
            self.assertEqual(403, missing.status_code, missing.json)
        finally:
            delete_policy("ca_state_scoped_set")
        self.assertEqual(0, UserLockState.query.count())

    def test_set_user_lock_allowed_within_the_resolver_scope(self):
        # Locking by login+realm without a resolver still passes a resolver-scoped check: the user is
        # resolved (which fills in the resolver) before the scope is evaluated.
        set_policy("ca_state_resolver_ok", scope=SCOPE.ADMIN, action=str(PolicyAction.USER_LOCK_SET),
                   resolver=self.resolvername1)
        try:
            res = self._request("lock/user", method="POST",
                                json_data={"username": "cornelius", "realm": self.realm1})
            self.assertEqual(200, res.status_code, res.json)
        finally:
            delete_policy("ca_state_resolver_ok")
        self.assertEqual(1, UserLockState.query.count())

    def test_set_user_lock_refused_outside_the_resolver_scope(self):
        # An admin scoped to another resolver cannot lock a user resolved from resolvername1.
        self.setUp_user_realm3()
        set_policy("ca_state_resolver_no", scope=SCOPE.ADMIN, action=str(PolicyAction.USER_LOCK_SET),
                   resolver=self.resolvername3)
        try:
            res = self._request("lock/user", method="POST",
                                json_data={"username": "cornelius", "realm": self.realm1})
            self.assertEqual(403, res.status_code, res.json)
        finally:
            delete_policy("ca_state_resolver_no")
        self.assertEqual(0, UserLockState.query.count())

    def test_set_user_lock_refused_outside_the_realm_scope(self):
        # An admin scoped to another realm cannot lock a user in realm1, and the attempt writes nothing.
        self.setUp_user_realm2()
        set_policy("ca_state_realm_no", scope=SCOPE.ADMIN, action=str(PolicyAction.USER_LOCK_SET),
                   realm=self.realm2)
        try:
            res = self._request("lock/user", method="POST",
                                json_data={"username": "cornelius", "realm": self.realm1})
            self.assertEqual(403, res.status_code, res.json)
        finally:
            delete_policy("ca_state_realm_no")
        self.assertEqual(0, UserLockState.query.count())

    def test_read_action_does_not_grant_reset(self):
        # An admin policy that grants only the read actions must block the resets.
        self._lock_user(utc_now() + timedelta(seconds=600))
        self._block("203.0.113.7", utc_now() + timedelta(seconds=600))
        set_policy("ca_state_read", scope=SCOPE.ADMIN,
                   action=f"{PolicyAction.USER_LOCK_READ},{PolicyAction.BLOCKLIST_READ}")
        try:
            self.assertEqual(200, self._request("lock/users").status_code)
            self.assertEqual(200, self._request("blocklist").status_code)
            reset = self._request("lock/user", method="DELETE",
                                  json_data={"user": "cornelius", "realm": self.realm1})
            self.assertEqual(403, reset.status_code, reset.json)
            unblock = self._request("blocklist/203.0.113.7", method="DELETE")
            self.assertEqual(403, unblock.status_code, unblock.json)
            self.assertEqual(403, self._request("lock/users/purge", method="POST").status_code)
            self.assertEqual(403, self._request("blocklist/purge", method="POST").status_code)
        finally:
            delete_policy("ca_state_read")
        # Every rejected call must have left the state untouched.
        self.assertEqual(1, UserLockState.query.count())
        self.assertEqual(1, BlockList.query.count())

    def test_list_is_constrained_to_policy_visibility_scope(self):
        # Lock a user in realm1 and a raw row in another realm.
        self._lock_user(utc_now() + timedelta(seconds=600))
        db.session.add(UserLockState(resolver="other", uid="7", realm="otherrealm",
                                        lock_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        # An admin whose read action is scoped to realm1 only sees the realm1 lock.
        set_policy("ca_state_realm1", scope=SCOPE.ADMIN,
                   action=str(PolicyAction.USER_LOCK_READ), realm=self.realm1)
        try:
            users = self._request("lock/users").json["result"]["value"]["locked_users"]
            self.assertEqual(1, len(users))
            self.assertEqual(self.realm1, users[0]["realm"])
        finally:
            delete_policy("ca_state_realm1")
        # The scope narrows the view, not the data: both rows are still there.
        self.assertEqual(2, UserLockState.query.count())

    def test_reset_only_clears_rows_inside_the_resolver_scope(self):
        # The boundary must be part of the delete criterion, not a pre-flight check on one identity: resetting by
        # login+realm with no resolver matches rows in every resolver of the realm, so only the admin's own may clear.
        self._lock_user(utc_now() + timedelta(seconds=600))
        db.session.add(UserLockState(resolver="otherresolver", uid="99", realm=self.realm1,
                                        username="cornelius",
                                        lock_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        set_policy("ca_reset_resolver1", scope=SCOPE.ADMIN,
                   action=str(PolicyAction.USER_LOCK_RESET), resolver=self.resolvername1)
        try:
            res = self._request("lock/user", method="DELETE",
                                json_data={"user": "cornelius", "realm": self.realm1})
            self.assertEqual(200, res.status_code, res.json)
            self.assertTrue(res.json["result"]["value"])
        finally:
            delete_policy("ca_reset_resolver1")
        # The in-scope row is gone, the out-of-scope one survives, and nothing else was touched.
        self.assertIsNone(db.session.get(UserLockState, (self.user.resolver, self.user.uid, self.user.realm)))
        self.assertIsNotNone(db.session.get(UserLockState, ("otherresolver", "99", self.realm1)))
        self.assertEqual(1, UserLockState.query.count())

    def test_reset_outside_the_scope_reports_no_lock_removed(self):
        # An out-of-scope target is indistinguishable from an absent lock: false, and the row stays.
        # The only matching lock lives in a resolver outside the admin's scope.
        db.session.add(UserLockState(resolver="otherresolver", uid="99", realm=self.realm1, username="cornelius",
                                        lock_expires_at=utc_now() + timedelta(seconds=600)))
        db.session.commit()
        set_policy("ca_reset_resolver1", scope=SCOPE.ADMIN, action=str(PolicyAction.USER_LOCK_RESET),
                   resolver=self.resolvername1)
        try:
            # No resolver in the request, so only the visibility scope keeps this row out of reach.
            res = self._request("lock/user", method="DELETE",
                                json_data={"user": "cornelius", "realm": self.realm1})
            self.assertEqual(200, res.status_code, res.json)
            self.assertFalse(res.json["result"]["value"])
        finally:
            delete_policy("ca_reset_resolver1")
        # Deliberately the only row in play: adding an in-scope one would make the reset succeed and
        # turn this into test_reset_only_clears_rows_inside_the_resolver_scope. Here nothing may go.
        self.assertIsNotNone(db.session.get(UserLockState, ("otherresolver", "99", self.realm1)))
        self.assertEqual(1, UserLockState.query.count())

    def test_purge_is_constrained_to_policy_visibility_scope(self):
        # A scoped admin only purges the stale rows inside their boundary.
        self._lock_user(utc_now() - timedelta(seconds=60))  # expired, in scope
        db.session.add(UserLockState(resolver="otherresolver", uid="99", realm=self.realm1, username="hans",
                                        lock_expires_at=utc_now() - timedelta(seconds=60)))  # expired, out of scope
        db.session.commit()
        set_policy("ca_reset_resolver1", scope=SCOPE.ADMIN,
                   action=str(PolicyAction.USER_LOCK_RESET), resolver=self.resolvername1)
        try:
            res = self._request("lock/users/purge", method="POST")
            self.assertEqual(200, res.status_code, res.json)
            self.assertEqual(1, res.json["result"]["value"])
        finally:
            delete_policy("ca_reset_resolver1")
        # The in-scope stale row is gone, the out-of-scope one survives, and nothing else was touched.
        self.assertIsNone(db.session.get(UserLockState, (self.user.resolver, self.user.uid, self.user.realm)))
        self.assertIsNotNone(db.session.get(UserLockState, ("otherresolver", "99", self.realm1)))
        self.assertEqual(1, UserLockState.query.count())

    def test_user_lock_action_does_not_grant_blocklist(self):
        # Per-domain gating: the user-lock read action must not open the blocklist.
        set_policy("ca_user_only", scope=SCOPE.ADMIN,
                   action=str(PolicyAction.USER_LOCK_READ))
        try:
            self.assertEqual(200, self._request("lock/users").status_code)
            self.assertEqual(403, self._request("blocklist").status_code)
        finally:
            delete_policy("ca_user_only")
