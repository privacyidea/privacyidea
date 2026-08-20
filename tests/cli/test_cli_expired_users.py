# SPDX-FileCopyrightText: (C) 2024 Paul Lettich <paul.lettich@netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Info: https://privacyidea.org
#
# This code is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License
# as published by the Free Software Foundation, either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program. If not, see <http://www.gnu.org/licenses/>.

from privacyidea.lib.error import ResolverError
from privacyidea.lib.realm import set_realm, delete_realm
from privacyidea.lib.resolver import save_resolver, delete_resolver
from .base import CliTestCase
from ..test_lib_user import patch_resolver_to_raise
from privacyidea.cli.tools.expired_users import expire

PWFILE = "tests/testdata/passwd"


class PIExpiredUsersTestCase(CliTestCase):
    def test_01_piexpiredusers_help(self):
        runner = self.app.test_cli_runner()
        result = runner.invoke(expire, ["-h"])
        self.assertIn("Search for expired Users in the specified realm.",
                      result.output, result)
        self.assertIn("--attribute_name", result.output, result)
        self.assertIn("--delete_serial", result.output, result)
        self.assertIn("--unassign_serial", result.output, result)
        self.assertIn("--noaction", result.output, result)

    def test_02_piexpiredusers_warns_on_skipped_resolver(self):
        # A resolver that raises while listing users must not fail the whole
        # command; it is skipped and the report is flagged as incomplete.
        resolvername = "cli_expired_resolver"
        realm = "cli_expired_realm"
        save_resolver({"resolver": resolvername,
                       "type": "passwdresolver",
                       "fileName": PWFILE})
        self.addCleanup(delete_resolver, resolvername)
        self.addCleanup(delete_realm, realm)
        (added, failed) = set_realm(realm, [{"name": resolvername}])
        self.assertEqual(0, len(failed))
        self.assertEqual(1, len(added))

        runner = self.app.test_cli_runner()
        with patch_resolver_to_raise(resolvername, ResolverError("simulated outage")):
            result = runner.invoke(expire, ["--realm", realm])
        self.assertIn("Warning: the following resolvers raised errors and were skipped",
                      result.output, result)
        self.assertIn(resolvername, result.output, result)
