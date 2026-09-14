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

from privacyidea.lib.error import ResolverError
from privacyidea.lib.policies.helper import own_entries_scope
from privacyidea.lib.user import User
from .base import MyTestCase


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
