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
(:mod:`privacyidea.lib.conditional_access.state`): listing and clearing
the live user-lock state and blocklist entries.
"""
from datetime import timedelta

from privacyidea.lib.conditional_access.authentication_log import AuthenticationLogVisibilityScope
from privacyidea.lib.conditional_access.authentication_event_types import RestrictionCause
from privacyidea.lib.error import ParameterError
from privacyidea.lib.conditional_access.state import (
    block_ip,
    get_user_lock_dict,
    lock_user,
    list_blocklist,
    list_locked_users,
    list_locked_users_paginate,
    purge_expired_blocklist,
    purge_expired_user_locks,
    remove_blocklist_entry,
    unlock_user_by_id,
    user_matches_scopes, unlock_user_by_username,
)
from privacyidea.lib.user import User
from privacyidea.models import db
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
from .base import MyTestCase


class UserLockStateTestCase(MyTestCase):

    def setUp(self):
        self.setUp_user_realms()
        # "cornelius" resolves to a non-empty uid, so it is a fully resolved (resolver, uid, realm) identity.
        self.user = User("cornelius", self.realm1, self.resolvername1)
        self._clear()

    def tearDown(self):
        self._clear()
        super().tearDown()

    @staticmethod
    def _clear():
        for model in (UserLockState, BlockList, ConditionalAccessStageAction, ConditionalAccessPolicyStage,
                      ConditionalAccessPolicyCounterType, ConditionalAccessPolicy, AuthenticationLog):
            db.session.query(model).delete()
        db.session.commit()

    def _lock(self, lock_expires_at, user=None, resolver=None, uid=None, realm=None, username=None,
              error_message=None):
        user = user or self.user
        db.session.add(UserLockState(
            resolver=resolver if resolver is not None else user.resolver,
            uid=uid if uid is not None else user.uid,
            realm=realm if realm is not None else user.realm,
            username=username if username is not None else user.login,
            lock_expires_at=lock_expires_at,
            error_message=error_message))
        db.session.commit()

    def _block(self, ip, block_expires_at, error_message=None):
        db.session.add(BlockList(ip=ip, block_expires_at=block_expires_at, error_message=error_message))
        db.session.commit()

    # --- lock_user / block_ip (the manual write path) -------------------------

    def test_lock_user_writes_a_permanent_manual_lock(self):
        # Permanent is the default: an admin locking by hand is reacting to an incident, and a lock that
        # quietly expires on its own would be the surprising outcome.
        lock = lock_user(self.user)
        self.assertTrue(lock["permanent"])
        self.assertEqual(RestrictionCause.MANUAL, lock["lock_cause"])
        row = db.session.query(UserLockState).one()
        self.assertIsNone(row.lock_expires_at)
        self.assertEqual(RestrictionCause.MANUAL, row.lock_cause)
        self.assertEqual(self.user.login, row.username)

    def test_lock_user_with_a_duration_sets_the_expiry(self):
        lock = lock_user(self.user, duration_seconds=600)
        self.assertFalse(lock["permanent"])
        self.assertAlmostEqual(600, lock["seconds_remaining"], delta=5)

    def test_lock_user_rejects_a_non_positive_duration(self):
        for duration in (0, -1, True, "600"):
            self.assertRaises(ParameterError, lock_user, self.user, duration)
        self.assertEqual(0, db.session.query(UserLockState).count())

    def test_lock_user_rejects_an_unresolved_user(self):
        # The row is keyed on (resolver, uid, realm), so a user that does not resolve has no key.
        self.assertRaises(ParameterError, lock_user, User())

    def test_manual_lock_is_authoritative_in_both_directions(self):
        # The engine refuses to downgrade a permanent lock so that the order two policies happen to fire in
        # cannot decide the outcome. An admin stating the outcome is not a race, so the write stands.
        lock_user(self.user)
        self.assertTrue(get_user_lock_dict(self.user)["permanent"])
        # A permanent lock is replaced by a timed one, which the engine's upsert would decline as a weakening.
        lock_user(self.user, duration_seconds=60)
        self.assertFalse(get_user_lock_dict(self.user)["permanent"])
        lock_user(self.user)
        self.assertTrue(get_user_lock_dict(self.user)["permanent"])

    def test_lock_user_replaces_a_policy_lock_and_its_cause(self):
        self._lock(utc_now() + timedelta(seconds=3600))
        self.assertEqual(RestrictionCause.POLICY, db.session.query(UserLockState).one().lock_cause)
        lock_user(self.user, duration_seconds=60)
        self.assertEqual(RestrictionCause.MANUAL, db.session.query(UserLockState).one().lock_cause)

    def test_block_ip_writes_a_manual_block(self):
        entry = block_ip("203.0.113.9", duration_seconds=300)
        self.assertEqual("203.0.113.9", entry["identifier"])
        self.assertEqual(RestrictionCause.MANUAL, entry["block_cause"])
        self.assertFalse(entry["permanent"])
        self.assertEqual(RestrictionCause.MANUAL, db.session.query(BlockList).one().block_cause)

    def test_block_ip_refuses_a_never_block_address_loudly(self):
        # The engine skips one silently so an automatic action cannot lock out everyone behind a shared
        # proxy; an admin asking for a block has to be told it did not happen.
        self.assertRaisesRegex(ParameterError, "never-block", block_ip, "127.0.0.1")
        self.assertEqual(0, db.session.query(BlockList).count())

    def test_block_ip_rejects_an_invalid_address(self):
        self.assertRaisesRegex(ParameterError, "not a valid IP address", block_ip, "not-an-ip")

    def test_block_ip_stores_an_ipv6_address_canonically(self):
        # The pre-check looks a block up by exact string against the request's client IP, which is
        # canonical, so a block filed under one of IPv6's other spellings would never match.
        entry = block_ip("2001:0DB8::0:1", duration_seconds=300)
        self.assertEqual("2001:db8::1", entry["identifier"])
        self.assertEqual("2001:db8::1", db.session.query(BlockList).one().ip)

    def test_block_ip_does_not_duplicate_a_differently_spelled_ipv6_address(self):
        # Two spellings of one address are one block, not two rows racing each other.
        block_ip("2001:0DB8::0:1", duration_seconds=300)
        block_ip("2001:db8::1", duration_seconds=600)
        self.assertEqual(1, db.session.query(BlockList).count())

    # --- the lock cause --------------------------------------------------------

    def test_locked_user_dict_reports_the_cause(self):
        self._lock(None)
        self.assertEqual(RestrictionCause.POLICY, list_locked_users()[0]["lock_cause"])

    def test_list_locked_users_filters_by_cause(self):
        self._lock(None)
        lock_user(User("selfservice", self.realm1, self.resolvername1))
        self.assertEqual(2, len(list_locked_users()))
        self.assertEqual([RestrictionCause.MANUAL], [row["lock_cause"] for row in list_locked_users(causes=["MANUAL"])])
        self.assertEqual([RestrictionCause.POLICY], [row["lock_cause"] for row in list_locked_users(causes=["POLICY"])])

    def test_list_locked_users_rejects_an_unknown_cause(self):
        # Ignoring it would widen the result to every cause, so a typo would return more than was asked for.
        self._lock(None)
        self.assertRaisesRegex(ParameterError, "Unknown lock cause", list_locked_users, causes=["ADMIN"])

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

    def test_list_locked_users_reports_the_stored_wording(self):
        # The wording this user is actually being shown, so an admin can see it without reading the policy -
        # and can tell a stale snapshot from what the stage carries now.
        self._lock(utc_now() + timedelta(seconds=600), error_message="Locked. Try again in about {duration}.")
        self.assertEqual("Locked. Try again in about {duration}.", list_locked_users()[0]["error_message"])

    def test_list_locked_users_reports_no_wording_when_the_stage_configured_none(self):
        # Silent is the default, and the table has to show that as plainly as it shows a message.
        self._lock(utc_now() + timedelta(seconds=600))
        self.assertIsNone(list_locked_users()[0]["error_message"])

    def test_list_locked_users_filters_on_the_stored_wording(self):
        # So an admin can find every lock still quoting wording they have since changed - the row keeps a
        # snapshot, so those users go on reading it until the lock is rewritten.
        self._lock(utc_now() + timedelta(seconds=600), error_message="Locked. Contact your administrator.")
        self._lock(utc_now() + timedelta(seconds=600), username="bob", uid="uid002",
                   error_message="Blocked for a while.")
        self._lock(utc_now() + timedelta(seconds=600), username="carol", uid="uid003")
        matched = list_locked_users(error_messages=["*administrator*"])
        self.assertEqual(1, len(matched))
        self.assertEqual("cornelius", matched[0]["username"])

    def test_list_locked_users_default_returns_all_states(self):
        # No states filter -> everything, including expired records.
        self._lock(utc_now() - timedelta(seconds=60))
        self.assertEqual(1, len(list_locked_users()))
        # Restricting to the currently-locked states hides the expired one.
        self.assertListEqual([], list_locked_users(states=["permanent", "temporary"]))

    def test_list_locked_users_active_row(self):
        self._lock(utc_now() + timedelta(seconds=600))
        row = list_locked_users()[0]
        self.assertFalse(row["permanent"])
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

    def test_list_locked_users_unknown_state_raises(self):
        self._lock(utc_now() + timedelta(seconds=600))
        # An unknown state must not be ignored: dropping it would widen the result to every state,
        # so a typo would silently return more than was asked for.
        self.assertRaises(ParameterError, list_locked_users, states=["bogus"])
        # ... also when mixed with a valid one.
        self.assertRaises(ParameterError, list_locked_users, states=["permanent", "bogus"])
        self.assertRaises(ParameterError, list_locked_users_paginate, states=["bogus"])

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

    # --- get_user_lock_dict ------------------------------------------------

    def test_get_user_lock_dict_none_when_not_locked(self):
        self.assertIsNone(get_user_lock_dict(self.user))

    def test_get_user_lock_dict_returns_status(self):
        self._lock(utc_now() + timedelta(seconds=600))
        entry = get_user_lock_dict(self.user)
        self.assertIsNotNone(entry)
        self.assertEqual("cornelius", entry["username"])
        self.assertFalse(entry["permanent"])
        self.assertGreater(entry["seconds_remaining"], 0)

    def test_get_user_lock_dict_none_when_expired(self):
        self._lock(utc_now() - timedelta(seconds=60))
        self.assertIsNone(get_user_lock_dict(self.user))

    # --- unlock ---------------------------------------------------------------

    def test_unlock_user_by_id(self):
        self._lock(utc_now() + timedelta(seconds=600))
        self.assertTrue(unlock_user_by_id(self.user.uid, self.user.realm, self.user.resolver))
        self.assertIsNone(db.session.get(
            UserLockState, (self.user.resolver, self.user.uid, self.user.realm)))
        # A second reset finds nothing to remove.
        self.assertFalse(unlock_user_by_id(self.user.uid, self.user.realm, self.user.resolver))

    def test_unlock_user_by_id_without_resolver(self):
        # Resolver is an optional disambiguator (mirrors unlock_user_by_username): omitting it
        # must still unlock, matching on (uid, realm).
        self._lock(utc_now() + timedelta(seconds=600))
        self.assertTrue(unlock_user_by_id(self.user.uid, self.user.realm))
        self.assertListEqual([], list_locked_users())

    def test_unlock_user_by_id_uid_collision_across_resolvers(self):
        # uid is resolver-local and opaque: the same uid can name unrelated users in two resolvers of a realm.
        # Omitting resolver clears both matching locks; passing one removes only that resolver's lock.
        self._lock(utc_now() + timedelta(seconds=600), resolver="resoA", uid="1001",
                   realm="collide", username="alice")
        self._lock(utc_now() + timedelta(seconds=600), resolver="resoB", uid="1001",
                   realm="collide", username="bob")
        # Targeted: only resoA's lock goes.
        self.assertTrue(unlock_user_by_id("1001", "collide", "resoA"))
        self.assertIsNotNone(db.session.get(UserLockState, ("resoB", "1001", "collide")))
        # Untargeted: the remaining collision (resoB) is cleared too.
        self.assertTrue(unlock_user_by_id("1001", "collide"))
        self.assertIsNone(db.session.get(UserLockState, ("resoB", "1001", "collide")))

    def test_unlock_user_by_username(self):
        self._lock(utc_now() + timedelta(seconds=600))
        self.assertTrue(unlock_user_by_username(self.user.login, self.user.realm, self.user.resolver))
        self.assertListEqual([], list_locked_users())

    def test_unlock_user_by_username_without_resolver(self):
        self._lock(utc_now() + timedelta(seconds=600))
        self.assertTrue(unlock_user_by_username(self.user.login, self.user.realm))
        self.assertListEqual([], list_locked_users())

    # --- blocklist ------------------------------------------------------------

    def test_list_blocklist_empty(self):
        self.assertListEqual([], list_blocklist())

    def test_list_blocklist_default_returns_all_states(self):
        self._block("203.0.113.7", utc_now() + timedelta(seconds=600))
        self._block("203.0.113.8", utc_now() - timedelta(seconds=60))
        entries = list_blocklist()
        self.assertSetEqual({"203.0.113.7", "203.0.113.8"}, {entry["identifier"] for entry in entries})

    def test_list_blocklist_reports_the_stored_wording(self):
        self._block("203.0.113.7", utc_now() + timedelta(seconds=600), error_message="Blocked for {duration}.")
        self._block("203.0.113.8", utc_now() + timedelta(seconds=600))
        by_ip = {entry["identifier"]: entry["error_message"] for entry in list_blocklist()}
        self.assertEqual("Blocked for {duration}.", by_ip["203.0.113.7"])
        self.assertIsNone(by_ip["203.0.113.8"])

    def test_list_blocklist_excludes_expired_on_request(self):
        self._block("203.0.113.7", utc_now() + timedelta(seconds=600))
        self._block("203.0.113.8", utc_now() - timedelta(seconds=60))
        entries = list_blocklist(include_expired=False)
        self.assertEqual(1, len(entries))
        self.assertEqual("203.0.113.7", entries[0]["identifier"])
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

    def test_purge_expired_user_locks(self):
        self._lock(utc_now() - timedelta(seconds=60))                       # expired -> purged
        self._lock(utc_now() + timedelta(seconds=600),
                   resolver="r", uid="2", realm="realm2")                   # active -> kept
        self._lock(None, resolver="r", uid="3", realm="realm3")            # permanent -> kept
        self.assertEqual(1, purge_expired_user_locks())
        self.assertEqual(2, UserLockState.query.count())

    def test_purge_expired_blocklist(self):
        self._block("203.0.113.1", utc_now() - timedelta(seconds=60))       # expired -> purged
        self._block("203.0.113.2", utc_now() + timedelta(seconds=600))      # active -> kept
        self._block("203.0.113.3", None)                                    # permanent -> kept
        self.assertEqual(1, purge_expired_blocklist())
        self.assertEqual(2, BlockList.query.count())
