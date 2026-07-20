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
Shared test fixtures for the conditional-access lockout tests.

:class:`LockoutTestCase` is the common base for the engine, template and
snapshot suites: it resolves a real test user, wipes every lockout table before
and after each test, and offers helpers to seed ``authentication_log`` events
and read back the resulting lock / block state.

This module is deliberately **not** named ``test_*`` so pytest does not collect
it; the concrete suites import :class:`LockoutTestCase` and add their own tests.
"""
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


class LockoutTestCase(MyTestCase):
    """
    Base for conditional-access lockout tests: a resolved test user plus a clean
    slate of all lockout tables around every test.
    """

    def setUp(self):
        self.setUp_user_realms()
        # "cornelius" resolves to a non-empty uid in the test resolver ("root" has an
        # empty uid there), so it is a fully resolved (resolver, uid, realm) identity
        # the engine acts on; it also carries an email address the EMAIL_* actions target.
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

    def _seed_events(self, event_type, count, timestamp=None, user=None):
        """Insert *count* authentication-log rows for *user* (default: the test user)."""
        user = user or self.user
        timestamp = timestamp if timestamp is not None else utc_now()
        for _ in range(count):
            db.session.add(AuthenticationLog(
                event_type=str(event_type), resolver=user.resolver, uid=user.uid,
                realm=user.realm, timestamp=timestamp))
        db.session.commit()

    def _seed_ip_events(self, source_ip, event_type, n_users, per_user=1, timestamp=None, start=0):
        """Seed *n_users* distinct users (``spray<start>``..), each with *per_user* rows, all from
        *source_ip* (the password-spraying shape: one IP hitting many users). *start* offsets the
        user index so several calls can seed non-overlapping users."""
        timestamp = timestamp if timestamp is not None else utc_now()
        for i in range(start, start + n_users):
            for _ in range(per_user):
                db.session.add(AuthenticationLog(
                    event_type=str(event_type), resolver=self.user.resolver, uid=f"spray{i}",
                    realm=self.user.realm, source_ip=source_ip, timestamp=timestamp))
        db.session.commit()

    def _state(self, user=None):
        user = user or self.user
        return db.session.get(UserLockoutState, (user.resolver, user.uid, user.realm))

    def _block(self, ip):
        return db.session.get(BlockList, ip)
