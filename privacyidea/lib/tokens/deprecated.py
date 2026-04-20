# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Generic stub for token types that have been removed from privacyIDEA.

When a token type is dropped, an alembic migration flips the affected
rows (tokens) to ``tokentype='deprecated'`` and stashes the original type in
``tokeninfo['original_tokentype']``. This class lets those tokens still
be listed and deleted via the normal UI and pitokenjanitor, while
refusing any authentication or enrollment operation.

See ``dev/token-deprecation-strategy.md`` for the full design.
"""
import logging

from privacyidea.lib import _
from privacyidea.lib.error import NoLongerSupportedError
from privacyidea.lib.tokenclass import TokenClass

log = logging.getLogger(__name__)


class DeprecatedTokenClass(TokenClass):
    """
    Stand-in for tokens whose original type has been removed.

    Instances are safe to construct, list, and delete — but any
    attempt to use them for enrollment or state change (enable, reset)
    raises :class:`NoLongerSupportedError`.
    Read-only operations like ``get_tokeninfo``, ``get_as_dict``, and
    deletion fall through to :class:`TokenClass` unchanged.

    Authentication-path methods return silent failure values instead of
    raising, because callers iterate over multiple tokens and an
    exception would abort the loop for sibling tokens.  The ``mode``
    class attribute is empty so the token is filtered out before
    challenge creation, but the safe return values are a second line
    of defence.
    See ``dev/token-deprecation-strategy.md``.
    """

    mode = []

    @staticmethod
    def get_class_type():
        return "deprecated"

    @staticmethod
    def get_class_prefix():
        return "DEPR"

    def _refuse(self):
        original = self.get_tokeninfo("original_tokentype") or "unknown"
        raise NoLongerSupportedError(
            _("This is a deprecated {0} token and is no longer supported.").format(original)
        )

    # --- enrollment ---
    def update(self, param, reset_failcount=True):
        self._refuse()

    def get_init_detail(self, params=None, user=None):
        self._refuse()

    # --- authentication (silent failure — see class docstring) ---
    def is_challenge_request(self, passw, user=None, options=None):
        return False

    def create_challenge(self, transactionid=None, options=None):
        return False, "", None, {}

    def check_challenge_response(self, user=None, passw=None, options=None):
        return -1

    def check_otp(self, otpval, counter=None, window=None, options=None):
        return -1

    def authenticate(self, passw, user=None, options=None):
        return False, -1, {}

    # --- state changes that would make the token look usable again ---
    def enable(self, enable=True):
        # Prevent an admin from accidentally flipping active=True on a
        # deprecated token — the token still wouldn't authenticate, and
        # the mismatch between UI "active" and actual behaviour is worse
        # than a clear refusal. Allow explicit disable so admins can
        # still audit-log a disable if they want.
        if enable:
            self._refuse()
        TokenClass.enable(self, enable=False)

    def reset(self):
        # Resetting the failcounter on a token that will never pass its
        # next check is meaningless.
        self._refuse()

    # --- token-specific REST endpoint ---
    @classmethod
    def api_endpoint(cls, request, g):
        raise NoLongerSupportedError(
            _("This token type has been removed and has no active API endpoint.")
        )
