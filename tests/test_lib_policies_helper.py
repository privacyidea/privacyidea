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
Unit tests for the policy helpers in :mod:`privacyidea.lib.policies.helper`. The visibility boundary they build is
enforced end-to-end in test_api_authentication_log.py; what is tested here is the identity resolution behind it,
including the failure paths a request cannot produce on demand.
"""
import mock
from flask import g

from privacyidea.lib.auth import ROLE
from privacyidea.lib.error import ResolverError
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policies.helper import (admin_granted_realms, get_policy_visibility_scopes, own_entries_scope,
                                             policy_realm_names)
from privacyidea.lib.policy import PolicyClass, SCOPE, delete_policy, set_policy
from privacyidea.lib.user import User
from .base import FakeAudit, MyTestCase


class OwnEntriesScopeTestCase(MyTestCase):
    """The scope matching one principal's own records, bound to their resolver-stable identity."""

    def setUp(self):
        self.setUp_user_realms()
        self.user = User("cornelius", self.realm1)

    def test_scope_binds_to_the_resolved_identity(self):
        with self.app.test_request_context():
            scope = own_entries_scope("cornelius", self.realm1)
        self.assertListEqual([self.realm1], scope.realms)
        self.assertListEqual([self.resolvername1], scope.resolvers)
        self.assertListEqual([str(self.user.uid)], scope.uids)
        # The login name is deliberately not part of the match: it is what the identity replaces.
        self.assertListEqual([], scope.usernames)

    def test_no_scope_without_a_login_or_a_realm(self):
        # Both are needed to name an account. Neither caller can currently omit one, but falling through to a
        # login-name match on a partial principal is what this boundary must never do.
        with self.app.test_request_context():
            self.assertIsNone(own_entries_scope("", self.realm1))
            self.assertIsNone(own_entries_scope("cornelius", ""))
            self.assertIsNone(own_entries_scope(None, None))

    def test_no_scope_for_a_login_that_resolves_to_no_account(self):
        with self.app.test_request_context():
            self.assertIsNone(own_entries_scope("nosuchuser", self.realm1))

    def test_no_scope_when_the_resolver_fails(self):
        # A directory outage leaves the identity unknown, which must fail closed rather than fall back to the login
        # name or propagate and turn a read into a server error.
        with mock.patch("privacyidea.lib.policies.helper.User",
                        side_effect=ResolverError("The resolver is not reachable")):
            with self.app.test_request_context():
                self.assertIsNone(own_entries_scope("cornelius", self.realm1))


class AdminGrantedRealmsTestCase(MyTestCase):
    """The realms an admin's policies grant, read the way the policy engine matches the realm field."""

    def setUp(self) -> None:
        self.setUp_user_realms()
        self.setUp_user_realm2()
        self.setUp_user_realm3()
        g.audit_object = FakeAudit()
        g.logged_in_user = {"username": "admin1", "realm": "", "role": ROLE.ADMIN}
        g.client_ip = None
        g.serial = None

    def _granted(self, **policy_scope: str) -> list[str] | None:
        set_policy("granted", scope=SCOPE.ADMIN, action=PolicyAction.DELETEUSER, **policy_scope)
        g.policy_object = PolicyClass()
        try:
            return admin_granted_realms(PolicyAction.DELETEUSER)
        finally:
            delete_policy("granted")

    def test_named_realms_are_granted(self):
        self.assertEqual([self.realm1, self.realm3], self._granted(realm=f"{self.realm1},{self.realm3}"))

    def test_a_realm_field_that_restricts_nothing_grants_every_realm(self):
        self.assertIsNone(self._granted())
        self.assertIsNone(self._granted(realm="*"))

    def test_every_realm_but_an_excluded_one(self):
        granted = self._granted(realm=f"*,!{self.realm3}")
        self.assertIn(self.realm1, granted)
        self.assertIn(self.realm2, granted)
        self.assertNotIn(self.realm3, granted)
        self.assertEqual(granted, self._granted(realm=f"*,-{self.realm3}"))

    def test_an_excluded_realm_is_not_granted_by_name_either(self):
        self.assertEqual([self.realm1], self._granted(realm=f"{self.realm1},{self.realm3},!{self.realm3}"))
        # Nothing but an exclusion matches no realm at all.
        self.assertEqual([], self._granted(realm=f"!{self.realm3}"))

    def test_a_policy_scoped_by_user_or_resolver_names_a_realm_only_if_its_realm_field_does(self):
        for target_scope in ({"user": "cornelius"}, {"resolver": self.resolvername1}):
            self.assertEqual([], self._granted(**target_scope), target_scope)
            self.assertEqual([], self._granted(realm="*", **target_scope), target_scope)
            self.assertEqual([self.realm1], self._granted(realm=self.realm1, **target_scope), target_scope)
            # Every realm but one is named as well, realm by realm.
            granted = self._granted(realm=f"*,!{self.realm3}", **target_scope)
            self.assertIn(self.realm1, granted, target_scope)
            self.assertNotIn(self.realm3, granted, target_scope)


class VisibilityScopeTargetsTestCase(MyTestCase):
    """An admin's visibility boundary, with every target field read the way the policy engine matches it."""

    def setUp(self) -> None:
        self.setUp_user_realms()
        self.setUp_user_realm3()
        g.audit_object = FakeAudit()
        g.logged_in_user = {"username": "admin1", "realm": "", "role": ROLE.ADMIN}
        g.client_ip = None
        g.serial = None

    def _scopes(self, **policy_scope: str | bool) -> list | None:
        set_policy("visible", scope=SCOPE.ADMIN, action=PolicyAction.AUTHENTICATION_LOG_READ, **policy_scope)
        g.policy_object = PolicyClass()
        try:
            return get_policy_visibility_scopes(PolicyAction.AUTHENTICATION_LOG_READ)
        finally:
            delete_policy("visible")

    def test_realms_of_the_boundary(self):
        self.assertIsNone(self._scopes(realm="*"))
        self.assertEqual([self.realm1], self._scopes(realm=self.realm1)[0].realms)
        scopes = self._scopes(realm=f"*,!{self.realm3}")
        self.assertEqual(1, len(scopes))
        self.assertIn(self.realm1, scopes[0].realms)
        self.assertNotIn(self.realm3, scopes[0].realms)
        # A realm field that matches no realm admits no record. None would admit every record.
        self.assertEqual([], self._scopes(realm=f"!{self.realm3}"))

    def test_resolvers_of_the_boundary(self):
        self.assertIsNone(self._scopes(resolver="*"))
        scopes = self._scopes(resolver=f"*,!{self.resolvername3}")
        self.assertEqual(1, len(scopes))
        self.assertIn(self.resolvername1, scopes[0].resolvers)
        self.assertNotIn(self.resolvername3, scopes[0].resolvers)
        self.assertEqual([], self._scopes(resolver=f"!{self.resolvername3}"))

    def test_users_of_the_boundary(self):
        self.assertIsNone(self._scopes(user="*"))
        scope = self._scopes(user="alice")[0]
        self.assertEqual((["alice"], []), (scope.usernames, scope.excluded_usernames))
        # Every user but some can not be listed, so it is carried as the excluded users.
        scope = self._scopes(user="*,!alice,-bob")[0]
        self.assertEqual(([], ["alice", "bob"]), (scope.usernames, scope.excluded_usernames))
        # A user field that matches no user admits no record.
        self.assertEqual([], self._scopes(user="!alice"))
        self.assertEqual([], self._scopes(user="alice,!alice"))
        # With user_case_insensitive an exclusion also takes away a name that differs only in case.
        self.assertEqual(["Alice"], self._scopes(user="Alice,!alice")[0].usernames)
        self.assertEqual([], self._scopes(user="Alice,!alice", user_case_insensitive=True))
        self.assertTrue(self._scopes(user="*,!alice", user_case_insensitive=True)[0].username_case_insensitive)

    def test_excluded_users_carry_their_accounts(self):
        cornelius = User("cornelius", self.realm1)
        scope = self._scopes(user="*,!cornelius,!nobody-by-this-name")[0]
        self.assertIn((cornelius.resolver, cornelius.uid), scope.excluded_accounts)
        # Only in the realms of the policy.
        scope = self._scopes(user="*,!cornelius", realm=self.realm3)[0]
        self.assertNotIn((cornelius.resolver, cornelius.uid), scope.excluded_accounts)
        # Excluding the logins without their accounts would admit too much, so a policy whose excluded users can not
        # be resolved grants nothing.
        with mock.patch("privacyidea.lib.policies.helper.User", side_effect=ResolverError("unreachable")):
            self.assertEqual([], self._scopes(user="*,!cornelius"))


class PolicyRealmNamesTestCase(MyTestCase):
    """A policy's realm field, read the way the policy engine matches it."""

    def setUp(self) -> None:
        self.setUp_user_realms()
        self.setUp_user_realm3()

    def test_policy_realm_names(self):
        for restricts_nothing in (None, [], ["*"]):
            self.assertIsNone(policy_realm_names(restricts_nothing), restricts_nothing)
        self.assertEqual([self.realm1], policy_realm_names([self.realm1, self.realm1]))
        every_other = policy_realm_names(["*", f"!{self.realm3}"])
        self.assertIn(self.realm1, every_other)
        self.assertNotIn(self.realm3, every_other)
        self.assertEqual(every_other, policy_realm_names(["*", f"-{self.realm3}"]))
        self.assertEqual([self.realm1], policy_realm_names([self.realm1, self.realm3, f"!{self.realm3}"]))
        # A field that matches no realm names none - which is not the same as restricting nothing.
        self.assertEqual([], policy_realm_names([f"!{self.realm3}"]))
