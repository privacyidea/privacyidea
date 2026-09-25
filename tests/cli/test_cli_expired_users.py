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
import datetime
from unittest import mock

from click.testing import Result

from privacyidea.lib.error import ResolverError
from privacyidea.lib.realm import set_realm, delete_realm
from privacyidea.lib.resolver import save_resolver, delete_resolver
from privacyidea.lib.token import get_tokens, init_token
from privacyidea.lib.user import User
from .base import CliTestCase
from ..test_lib_user import patch_resolver_to_raise
from privacyidea.cli.tools.expired_users import expire

PWFILE = "tests/testdata/passwd"
RESOLVER = "cli_expired_users_resolver"
REALM = "cli_expired_users_realm"
# An Active Directory account that never expires is read from LDAP as the largest possible datetime
NEVER_EXPIRES = datetime.datetime(9999, 12, 31, 23, 59, 59, 999999, tzinfo=datetime.timezone.utc)


def days_from_now(days: int) -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(days=days)


def user_entry(login: str, account_expires: datetime.datetime | None,
               attribute_name: str = "accountExpires") -> dict:
    """A user as get_user_list returns it, with the expiration date read from the user store."""
    return {"username": login, "resolver": RESOLVER, "realm": REALM, attribute_name: account_expires}


def assign_token(serial: str, login: str) -> None:
    init_token({"serial": serial, "type": "spass"}, user=User(login, realm=REALM))


def assigned_serials(login: str) -> list[str]:
    return sorted(token.token.serial for token in get_tokens(user=User(login, realm=REALM)))


def existing_serials() -> list[str]:
    return sorted(token.token.serial for token in get_tokens())


def remove_all_tokens() -> None:
    for token in get_tokens():
        token.delete_token()


class PIExpiredUsersTestCase(CliTestCase):
    def create_realm(self) -> None:
        save_resolver({"resolver": RESOLVER,
                       "type": "passwdresolver",
                       "fileName": PWFILE})
        self.addCleanup(delete_resolver, RESOLVER)
        self.addCleanup(delete_realm, REALM)
        (added, failed) = set_realm(REALM, [{"name": RESOLVER}])
        self.assertEqual(0, len(failed))
        self.assertEqual(1, len(added))
        # The realm can only be deleted once no token is assigned to one of its users any more
        self.addCleanup(remove_all_tokens)

    def run_expire(self, users: list[dict], arguments: list[str]) -> tuple[Result, mock.Mock]:
        """
        Run the command with get_user_list returning ``users``. The users are real users of the realm, only the
        expiration date comes from the given entries instead of an Active Directory.
        """
        runner = self.app.test_cli_runner()
        with mock.patch("privacyidea.cli.tools.expired_users.get_user_list", return_value=users) as get_user_list:
            result = runner.invoke(expire, arguments)
        return result, get_user_list

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

    def test_03_tokens_of_expired_user_are_unassigned(self):
        # By default all tokens of an expired user are unassigned and none is deleted. A user whose account
        # expires in the future keeps the tokens.
        self.create_realm()
        assign_token("EXP0001", "daemon")
        assign_token("EXP0002", "daemon")
        assign_token("FUT0001", "bin")

        result, get_user_list = self.run_expire([user_entry("daemon", days_from_now(-1)),
                                                 user_entry("bin", days_from_now(1))],
                                                ["--realm", REALM])
        self.assertEqual(0, result.exit_code, result.output)
        get_user_list.assert_called_once_with({"accountExpires": "1", "realm": REALM}, failures=[])
        self.assertIn("=== Account daemon has expired.", result.output, result)
        self.assertIn("=== Unassigning token EXP0001", result.output, result)
        self.assertIn("=== Unassigning token EXP0002", result.output, result)
        self.assertIn("= User bin has an expiration date.", result.output, result)
        self.assertNotIn("Account bin has expired", result.output, result)
        self.assertNotIn("FUT0001", result.output, result)
        self.assertEqual([], assigned_serials("daemon"))
        self.assertEqual(["FUT0001"], assigned_serials("bin"))
        self.assertEqual(["EXP0001", "EXP0002", "FUT0001"], existing_serials())

    def test_04_delete_serial_deletes_matching_tokens(self):
        # Tokens matching --delete_serial are deleted, the others are only unassigned.
        self.create_realm()
        assign_token("DEL0001", "daemon")
        assign_token("KEEP0001", "daemon")

        result, _ = self.run_expire([user_entry("daemon", days_from_now(-1))],
                                    ["--realm", REALM, "-d", "^DEL"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("=== Deleting token DEL0001", result.output, result)
        self.assertNotIn("Deleting token KEEP0001", result.output, result)
        self.assertEqual(["KEEP0001"], existing_serials())
        self.assertEqual([], assigned_serials("daemon"))

    def test_05_unassign_serial_limits_unassigned_tokens(self):
        self.create_realm()
        assign_token("UNA0001", "daemon")
        assign_token("KEEP0001", "daemon")

        result, _ = self.run_expire([user_entry("daemon", days_from_now(-1))],
                                    ["--realm", REALM, "-u", "^UNA"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("=== Unassigning token UNA0001", result.output, result)
        self.assertNotIn("KEEP0001", result.output, result)
        self.assertEqual(["KEEP0001"], assigned_serials("daemon"))

    def test_06_noaction_only_reports(self):
        # With --noaction the tokens that would be unassigned and deleted are listed, but stay as they are.
        self.create_realm()
        assign_token("EXP0001", "daemon")

        result, _ = self.run_expire([user_entry("daemon", days_from_now(-1))],
                                    ["--realm", REALM, "-d", ".*", "-n"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("=== Account daemon has expired.", result.output, result)
        self.assertIn("=== I WOULD unassign token EXP0001", result.output, result)
        self.assertIn("=== I WOULD delete token EXP0001", result.output, result)
        self.assertNotIn("Unassigning token", result.output, result)
        self.assertNotIn("Deleting token", result.output, result)
        self.assertEqual(["EXP0001"], existing_serials())
        self.assertEqual(["EXP0001"], assigned_serials("daemon"))

    def test_07_account_without_expiration_is_skipped(self):
        # An account that never expires is reported as such, a user without an expiration date is passed over.
        # Both keep their tokens.
        self.create_realm()
        assign_token("NEVER0001", "sys")
        assign_token("NODATE0001", "bin")

        result, _ = self.run_expire([user_entry("sys", NEVER_EXPIRES), user_entry("bin", None)],
                                    ["--realm", REALM])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Account 'sys' does not expire", result.output, result)
        self.assertNotIn("User sys has an expiration date", result.output, result)
        self.assertNotIn("bin", result.output, result)
        self.assertEqual(["NEVER0001"], assigned_serials("sys"))
        self.assertEqual(["NODATE0001"], assigned_serials("bin"))

    def test_08_expired_user_without_tokens_is_reported(self):
        self.create_realm()

        result, _ = self.run_expire([user_entry("games", days_from_now(-1))], ["--realm", REALM])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("=== Account games has expired.", result.output, result)
        self.assertIn("=== The account has no tokens assigned.", result.output, result)

    def test_09_attribute_name_is_used_without_realm(self):
        # Without --realm the users of all realms are searched, and the expiration date is read from the
        # attribute given with --attribute_name.
        self.create_realm()
        assign_token("EXP0001", "daemon")

        result, get_user_list = self.run_expire([user_entry("daemon", days_from_now(-1), "expiryDate")],
                                                ["-a", "expiryDate"])
        self.assertEqual(0, result.exit_code, result.output)
        get_user_list.assert_called_once_with({"expiryDate": "1"}, failures=[])
        self.assertIn("=== Unassigning token EXP0001", result.output, result)
        self.assertEqual([], assigned_serials("daemon"))

    def test_10_attribute_missing_from_mapping_is_reported(self):
        # A resolver without the attribute in its mapping raises a KeyError while searching, which is reported
        # with a hint instead of failing the command.
        runner = self.app.test_cli_runner()
        with mock.patch("privacyidea.cli.tools.expired_users.get_user_list",
                        side_effect=KeyError("accountExpires")):
            result = runner.invoke(expire, [])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Failed to get users: KeyError('accountExpires')", result.output, result)
        self.assertIn("Does the attribute 'accountExpires' exist in the attribute mapping of the resolver?",
                      result.output, result)
