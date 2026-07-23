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
Unit tests for the conditional-access state management layer
(:mod:`privacyidea.lib.conditional_access.lockout_state`): listing and clearing
the live user-lockout state and blocklist entries.
"""
from datetime import timedelta

from privacyidea.lib.conditional_access.authentication_log import AuthenticationLogVisibilityScope
from privacyidea.lib.conditional_access.lockout_state import (
    get_user_lockout_dict,
    list_blocklist,
    list_locked_users,
    list_locked_users_paginate,
    purge_expired_blocklist,
    purge_expired_user_lockouts,
    remove_blocklist_entry,
    unlock_user_by_id,
    user_matches_scopes, unlock_user_by_username,
)
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
from .base import MyTestCase


class LockoutStateTestCase(MyTestCase):

    def setUp(self):
        self.setUp_user_realms()
        # "cornelius" resolves to a non-empty uid in the test resolver, so it is a
        # fully resolved (resolver, uid, realm) identity.
        self.user = User("cornelius", self.realm1, self.resolvername1)
        self._clear()

    def tearDown(self):
        self._clear()
        super().tearDown()

    @staticmethod
    def _clear():
        for model in (UserLockoutState, BlockList, LockoutStageAction, LockoutPolicyStage,
                      LockoutPolicyCounterType, LockoutPolicy, AuthenticationLog):
            db.session.query(model).delete()
        db.session.commit()

    def _lock(self, lock_expires_at, user=None, resolver=None, uid=None, realm=None, username=None):
        user = user or self.user
        db.session.add(UserLockoutState(
            resolver=resolver if resolver is not None else user.resolver,
            uid=uid if uid is not None else user.uid,
            realm=realm if realm is not None else user.realm,
            username=username if username is not None else user.login,
            is_locked=True, lock_expires_at=lock_expires_at))
        db.session.commit()

    def _block(self, ip, block_expires_at, reason=None):
        db.session.add(BlockList(ip=ip, is_blocked=True,
                                 block_expires_at=block_expires_at, reason=reason))
        db.session.commit()

    # --- list_locked_users ----------------------------------------------------

    def test_list_locked_users_empty(self):
        self.assertListEqual([], list_locked_users())

    def test_list_locked_users_returns_active_lock(self):
        self._lock(utc_now() + timedelta(seconds=600))
        users = list_locked_users()
        self.assertEqual(1, len(users))
        entry = users[0]
        self.assertEqual(self.user.resolver, entry["resolver"])
        self.assertEqual(self.user.uid, entry["uid"])
        self.assertEqual(self.user.realm, entry["realm"])
        self.assertEqual("cornelius", entry["username"])
        self.assertFalse(entry["permanent"])
        self.assertGreater(entry["seconds_remaining"], 0)

    def test_list_locked_users_default_returns_all_states(self):
        # No states filter -> everything, including expired records.
        self._lock(utc_now() - timedelta(seconds=60))
        self.assertEqual(1, len(list_locked_users()))
        # Restricting to the currently-locked states hides the expired one.
        self.assertListEqual([], list_locked_users(states=["permanent", "temporary"]))

    def test_list_locked_users_active_row(self):
        self._lock(utc_now() + timedelta(seconds=600))
        row = list_locked_users()[0]
        self.assertTrue(row["is_locked"])
        self.assertGreater(row["seconds_remaining"], 0)

    def test_list_locked_users_states_filter(self):
        self._lock(utc_now() + timedelta(seconds=600))                                  # temporary
        self._lock(None, resolver=self.resolvername1, uid="2", realm=self.realm1, username="perm")  # permanent
        self._lock(utc_now() - timedelta(seconds=60),
                   resolver=self.resolvername1, uid="3", realm=self.realm1, username="old")  # expired
        # No states filter -> all three states.
        self.assertEqual(3, len(list_locked_users()))
        # Restricting to the currently-locked states hides the expired one.
        self.assertEqual(2, len(list_locked_users(states=["permanent", "temporary"])))
        # Explicitly request only expired.
        expired = list_locked_users(states=["expired"])
        self.assertEqual(1, len(expired))
        self.assertFalse(expired[0]["permanent"])
        self.assertEqual(0, expired[0]["seconds_remaining"])
        # Only permanent.
        permanent = list_locked_users(states=["permanent"])
        self.assertEqual(1, len(permanent))
        self.assertTrue(permanent[0]["permanent"])
        # All three.
        self.assertEqual(3, len(list_locked_users(states=["permanent", "temporary", "expired"])))

    def test_list_locked_users_includes_permanent(self):
        self._lock(None)
        users = list_locked_users()
        self.assertEqual(1, len(users))
        self.assertTrue(users[0]["permanent"])
        self.assertIsNone(users[0]["seconds_remaining"])

    def test_list_locked_users_uses_stored_username(self):
        # The username is captured at lock time; it is returned as-is even if user does not exist anymore.
        self._lock(utc_now() + timedelta(seconds=600),
                   resolver=self.resolvername1, uid="999999", realm=self.realm1, username="ghost")
        self.assertEqual("ghost", list_locked_users()[0]["username"])

    def test_list_locked_users_username_filter(self):
        self._lock(utc_now() + timedelta(seconds=600))
        self._lock(utc_now() + timedelta(seconds=600),
                   resolver=self.resolvername1, uid="7", realm=self.realm1, username="hans")
        filtered = list_locked_users(usernames=["cornelius"])
        self.assertEqual(1, len(filtered))
        self.assertEqual("cornelius", filtered[0]["username"])

    def test_list_locked_users_wildcard_filter(self):
        self._lock(utc_now() + timedelta(seconds=600))                                 # cornelius
        self._lock(utc_now() + timedelta(seconds=600),
                   resolver=self.resolvername1, uid="7", realm=self.realm1, username="hans")
        matched = list_locked_users(usernames=["corn*"])
        self.assertEqual(1, len(matched))
        self.assertEqual("cornelius", matched[0]["username"])

    def test_list_locked_users_case_insensitive_filter(self):
        self._lock(utc_now() + timedelta(seconds=600))
        # Case-sensitive by default: an upper-case query does not match.
        self.assertListEqual([], list_locked_users(usernames=["CORNELIUS"]))
        # ...but does with case_insensitive.
        self.assertEqual(1, len(list_locked_users(usernames=["CORNELIUS"], case_insensitive=True)))

    def test_list_locked_users_paginate(self):
        for i in range(5):
            self._lock(utc_now() + timedelta(seconds=600),
                       resolver=self.resolvername1, uid=str(100 + i), realm=self.realm1,
                       username=f"u{i}")
        first = list_locked_users_paginate(page=1, page_size=2, sort_column="username", sort_order="asc")
        self.assertEqual(5, first["count"])
        self.assertEqual(2, len(first["locked_users"]))
        self.assertEqual("u0", first["locked_users"][0]["username"])
        self.assertIsNone(first["prev"])
        self.assertEqual(2, first["next"])
        last = list_locked_users_paginate(page=3, page_size=2, sort_column="username", sort_order="asc")
        self.assertEqual(1, len(last["locked_users"]))
        self.assertEqual("u4", last["locked_users"][0]["username"])
        self.assertIsNone(last["next"])

    def test_list_locked_users_realm_filter(self):
        self._lock(utc_now() + timedelta(seconds=600))
        self._lock(utc_now() + timedelta(seconds=600),
                   resolver="other", uid="7", realm="otherrealm")
        filtered = list_locked_users(realms=[self.user.realm])
        self.assertEqual(1, len(filtered))
        self.assertEqual(self.user.realm, filtered[0]["realm"])

    def test_list_locked_users_multi_realm_and_resolver_filter(self):
        self._lock(utc_now() + timedelta(seconds=600))
        self._lock(utc_now() + timedelta(seconds=600),
                   resolver="other", uid="7", realm="otherrealm")
        self.assertEqual(2, len(list_locked_users(realms=[self.user.realm, "otherrealm"])))
        self.assertEqual(1, len(list_locked_users(resolvers=["other"])))

    # --- visibility scoping ---------------------------------------------------

    def test_visibility_scope_realm_limits_results(self):
        self._lock(utc_now() + timedelta(seconds=600))
        self._lock(utc_now() + timedelta(seconds=600),
                   resolver="other", uid="7", realm="otherrealm")
        scopes = [AuthenticationLogVisibilityScope(realms=[self.user.realm], resolvers=[], usernames=[])]
        result = list_locked_users(visibility_scopes=scopes)
        self.assertEqual(1, len(result))
        self.assertEqual(self.user.realm, result[0]["realm"])

    def test_visibility_scope_none_is_unrestricted(self):
        self._lock(utc_now() + timedelta(seconds=600))
        self.assertEqual(1, len(list_locked_users(visibility_scopes=None)))

    def test_visibility_scope_username_enforced(self):
        # The denormalized username column lets a user-scoped policy be enforced in SQL.
        self._lock(utc_now() + timedelta(seconds=600))
        match = [AuthenticationLogVisibilityScope(realms=[], resolvers=[], usernames=["cornelius"])]
        self.assertEqual(1, len(list_locked_users(visibility_scopes=match)))
        miss = [AuthenticationLogVisibilityScope(realms=[], resolvers=[], usernames=["nobody"])]
        self.assertListEqual([], list_locked_users(visibility_scopes=miss))

    def test_user_matches_scopes(self):
        self.assertTrue(user_matches_scopes(self.user, None))
        self.assertTrue(user_matches_scopes(
            self.user, [AuthenticationLogVisibilityScope(realms=[self.user.realm], resolvers=[], usernames=[])]))
        self.assertFalse(user_matches_scopes(
            self.user, [AuthenticationLogVisibilityScope(realms=["nope"], resolvers=[], usernames=[])]))
        # The single-user path *can* enforce username (login is supplied).
        self.assertTrue(user_matches_scopes(
            self.user, [AuthenticationLogVisibilityScope(realms=[], resolvers=[], usernames=["cornelius"])]))
        self.assertFalse(user_matches_scopes(
            self.user, [AuthenticationLogVisibilityScope(realms=[], resolvers=[], usernames=["someone"])]))
        self.assertTrue(user_matches_scopes(
            self.user, [AuthenticationLogVisibilityScope(realms=[], resolvers=[], usernames=["CORNELIUS"],
                                                         username_case_insensitive=True)]))

    # --- get_user_lockout_dict ------------------------------------------------

    def test_get_user_lockout_dict_none_when_not_locked(self):
        self.assertIsNone(get_user_lockout_dict(self.user))

    def test_get_user_lockout_dict_returns_status(self):
        self._lock(utc_now() + timedelta(seconds=600))
        entry = get_user_lockout_dict(self.user)
        self.assertIsNotNone(entry)
        self.assertEqual("cornelius", entry["username"])
        self.assertFalse(entry["permanent"])
        self.assertGreater(entry["seconds_remaining"], 0)

    def test_get_user_lockout_dict_none_when_expired(self):
        self._lock(utc_now() - timedelta(seconds=60))
        self.assertIsNone(get_user_lockout_dict(self.user))

    # --- unlock ---------------------------------------------------------------

    def test_unlock_user_by_id(self):
        self._lock(utc_now() + timedelta(seconds=600))
        self.assertTrue(unlock_user_by_id(self.user.resolver, self.user.uid, self.user.realm))
        self.assertIsNone(db.session.get(
            UserLockoutState, (self.user.resolver, self.user.uid, self.user.realm)))
        # A second reset finds nothing to remove.
        self.assertFalse(unlock_user_by_id(self.user.resolver, self.user.uid, self.user.realm))

    def test_unlock_user_by_username(self):
        self._lock(utc_now() + timedelta(seconds=600))
        self.assertTrue(unlock_user_by_username(self.user.login, self.user.realm, self.user.resolver))
        self.assertListEqual([], list_locked_users())

    # --- blocklist ------------------------------------------------------------

    def test_list_blocklist_empty(self):
        self.assertListEqual([], list_blocklist())

    def test_list_blocklist_active_and_excludes_expired(self):
        self._block("203.0.113.7", utc_now() + timedelta(seconds=600), reason="brute force")
        self._block("203.0.113.8", utc_now() - timedelta(seconds=60))
        entries = list_blocklist()
        self.assertEqual(1, len(entries))
        self.assertEqual("203.0.113.7", entries[0]["identifier"])
        self.assertEqual("brute force", entries[0]["reason"])
        self.assertFalse(entries[0]["permanent"])

    def test_list_blocklist_includes_permanent(self):
        self._block("203.0.113.9", None)
        entries = list_blocklist()
        self.assertEqual(1, len(entries))
        self.assertTrue(entries[0]["permanent"])
        self.assertIsNone(entries[0]["seconds_remaining"])

    def test_remove_blocklist_entry(self):
        self._block("203.0.113.7", utc_now() + timedelta(seconds=600))
        self.assertTrue(remove_blocklist_entry("203.0.113.7"))
        self.assertIsNone(db.session.get(BlockList, "203.0.113.7"))
        # A second removal finds nothing.
        self.assertFalse(remove_blocklist_entry("203.0.113.7"))

    def test_list_blocklist_include_expired_marks_stale(self):
        self._block("203.0.113.8", utc_now() - timedelta(seconds=60))
        entries = list_blocklist(include_expired=True)
        self.assertEqual(1, len(entries))
        self.assertEqual(0, entries[0]["seconds_remaining"])

    # --- purge expired --------------------------------------------------------

    def test_purge_expired_user_lockouts(self):
        self._lock(utc_now() - timedelta(seconds=60))                       # expired -> purged
        self._lock(utc_now() + timedelta(seconds=600),
                   resolver="r", uid="2", realm="realm2")                   # active -> kept
        self._lock(None, resolver="r", uid="3", realm="realm3")            # permanent -> kept
        self.assertEqual(1, purge_expired_user_lockouts())
        self.assertEqual(2, UserLockoutState.query.count())

    def test_purge_expired_blocklist(self):
        self._block("203.0.113.1", utc_now() - timedelta(seconds=60))       # expired -> purged
        self._block("203.0.113.2", utc_now() + timedelta(seconds=600))      # active -> kept
        self._block("203.0.113.3", None)                                    # permanent -> kept
        self.assertEqual(1, purge_expired_blocklist())
        self.assertEqual(2, BlockList.query.count())
