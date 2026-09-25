# SPDX-FileCopyrightText: (C) 2023 Paul Lettich <paul.lettich@netknights.it>
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

from dateutil.tz import tzlocal

from privacyidea.cli.tools.get_unused_tokens import cli
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.token import get_one_token, get_tokens, init_token
from privacyidea.lib.tokenclass import AUTH_DATE_FORMAT, TokenClass
from .base import CliTestCase

OTPKEY = "3132333435363738393031323334353637383930"


def create_token(serial: str, last_auth_age: datetime.timedelta | None, token_type: str = "hotp",
                 parameters: dict | None = None) -> TokenClass:
    """
    Create a token whose last successful authentication was ``last_auth_age`` ago, written the way a successful
    authentication records it. With ``last_auth_age`` None the token has never been used.
    """
    token = init_token({"serial": serial, "type": token_type, "otpkey": OTPKEY, **(parameters or {})})
    if last_auth_age is not None:
        last_auth = datetime.datetime.now(tzlocal()) - last_auth_age
        token.write_tokeninfo(PolicyAction.LASTAUTH, last_auth.strftime(AUTH_DATE_FORMAT))
    return token


def remove_all_tokens() -> None:
    for token in get_tokens():
        token.delete_token()


def existing_serials() -> list[str]:
    return sorted(token.token.serial for token in get_tokens())


class PIGetUnusedTokensTestCase(CliTestCase):
    def setUp(self) -> None:
        self.addCleanup(remove_all_tokens)

    def create_old_new_and_unused_token(self) -> None:
        """
        Create a token last used ten days ago, one last used an hour ago and one that was never used. Only the
        first one is older than an AGE of 5d.
        """
        create_token("OLD0001", datetime.timedelta(days=10))
        create_token("NEW0001", datetime.timedelta(hours=1))
        create_token("UNUSED0001", None)

    def test_01_pi_get_unused_tokens_help(self):
        runner = self.app.test_cli_runner()
        result = runner.invoke(cli, ["-h"])
        self.assertIn("Search for tokens that have not been used for a while",
                      result.output, result)
        self.assertIn("delete", result.output, result)
        self.assertIn("disable", result.output, result)
        self.assertIn("list", result.output, result)
        self.assertIn("mark", result.output, result)

    def test_02_pi_get_unused_tokens_find_help(self):
        runner = self.app.test_cli_runner()
        result = runner.invoke(cli, ["list"])
        self.assertIn("Error: Missing argument 'AGE'.",
                      result.output, result)
        self.assertNotIn("Find all tokens where the last_auth is greater than AGE.",
                         result.output, result)
        result = runner.invoke(cli, ["list", "-h"])
        self.assertNotIn("Error: Missing argument 'AGE'.",
                         result.output, result)
        self.assertIn("Find all tokens where the last_auth is greater than AGE.",
                      result.output, result)

    def test_03_list_shows_tokens_last_used_before_age(self):
        # A token that was never used has no last_auth and is not listed, it is not considered unused.
        self.create_old_new_and_unused_token()
        old_last_auth = get_one_token(serial="OLD0001").get_tokeninfo(PolicyAction.LASTAUTH)

        runner = self.app.test_cli_runner()
        result = runner.invoke(cli, ["list", "5d"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Token serial\tLast authentication", result.output, result)
        self.assertIn(f"OLD0001\t{old_last_auth}", result.output, result)
        self.assertNotIn("NEW0001", result.output, result)
        self.assertNotIn("UNUSED0001", result.output, result)

        # With a shorter AGE the token used an hour ago is listed as well
        result = runner.invoke(cli, ["list", "30m"])
        self.assertIn("OLD0001", result.output, result)
        self.assertIn("NEW0001", result.output, result)
        self.assertNotIn("UNUSED0001", result.output, result)

    def test_04_list_without_unused_tokens_prints_no_table(self):
        create_token("NEW0001", datetime.timedelta(hours=1))

        runner = self.app.test_cli_runner()
        result = runner.invoke(cli, ["list", "5d"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertNotIn("Token serial", result.output, result)
        self.assertNotIn("NEW0001", result.output, result)

    def test_05_disable_disables_tokens_last_used_before_age(self):
        self.create_old_new_and_unused_token()

        runner = self.app.test_cli_runner()
        result = runner.invoke(cli, ["disable", "5d"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Token OLD0001 disabled.", result.output, result)
        self.assertNotIn("NEW0001", result.output, result)
        self.assertNotIn("UNUSED0001", result.output, result)
        self.assertFalse(get_one_token(serial="OLD0001").is_active())
        self.assertTrue(get_one_token(serial="NEW0001").is_active())
        self.assertTrue(get_one_token(serial="UNUSED0001").is_active())

    def test_06_delete_deletes_tokens_last_used_before_age(self):
        self.create_old_new_and_unused_token()

        runner = self.app.test_cli_runner()
        result = runner.invoke(cli, ["delete", "5d"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Token OLD0001 deleted.", result.output, result)
        self.assertNotIn("NEW0001", result.output, result)
        self.assertNotIn("UNUSED0001", result.output, result)
        self.assertEqual(["NEW0001", "UNUSED0001"], existing_serials())

    def test_07_mark_sets_description_on_tokens_last_used_before_age(self):
        self.create_old_new_and_unused_token()

        runner = self.app.test_cli_runner()
        result = runner.invoke(cli, ["mark", "5d", "-d", "unused for a while"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Setting description for token OLD0001: unused for a while", result.output, result)
        self.assertEqual("unused for a while", get_one_token(serial="OLD0001").token.description)
        self.assertEqual("", get_one_token(serial="NEW0001").token.description)
        self.assertEqual("", get_one_token(serial="UNUSED0001").token.description)

    def test_08_mark_sets_tokeninfo_on_tokens_last_used_before_age(self):
        self.create_old_new_and_unused_token()

        runner = self.app.test_cli_runner()
        result = runner.invoke(cli, ["mark", "5d", "--tokeninfo", "cleanup=candidate"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Setting tokeninfo for token OLD0001: cleanup=candidate", result.output, result)
        self.assertEqual("candidate", get_one_token(serial="OLD0001").get_tokeninfo("cleanup"))
        self.assertIsNone(get_one_token(serial="NEW0001").get_tokeninfo("cleanup"))
        self.assertIsNone(get_one_token(serial="UNUSED0001").get_tokeninfo("cleanup"))

    def test_08b_mark_tokeninfo_value_with_equal_sign_and_without_key_value(self):
        # The value is everything after the first "=". Without "=" nothing is marked, not even the description.
        self.create_old_new_and_unused_token()

        runner = self.app.test_cli_runner()
        result = runner.invoke(cli, ["mark", "5d", "-t", "note=a=b"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertEqual("a=b", get_one_token(serial="OLD0001").get_tokeninfo("note"))

        result = runner.invoke(cli, ["mark", "5d", "-d", "not set", "-t", "note"])
        self.assertEqual(2, result.exit_code, result.output)
        self.assertIn("expected key=value", result.output, result)
        self.assertNotEqual("not set", get_one_token(serial="OLD0001").token.description)

    def test_09_mark_skips_tokeninfo_key_the_token_maintains_itself(self):
        # "phone" is maintained by the SMS token itself, but is a free-form entry for a HOTP token. The SMS
        # token is reported and left unchanged, and marking goes on with the HOTP token created after it.
        create_token("SMS0001", datetime.timedelta(days=10), token_type="sms", parameters={"phone": "+491111"})
        create_token("OLD0001", datetime.timedelta(days=10))

        runner = self.app.test_cli_runner()
        result = runner.invoke(cli, ["mark", "5d", "-t", "phone=+492222"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Skipped token SMS0001: ", result.output, result)
        self.assertNotIn("Skipped token OLD0001", result.output, result)
        self.assertEqual("+491111", get_one_token(serial="SMS0001").get_tokeninfo("phone"))
        self.assertEqual("+492222", get_one_token(serial="OLD0001").get_tokeninfo("phone"))

    def test_10_unsupported_age_is_reported_and_changes_nothing(self):
        create_token("OLD0001", datetime.timedelta(days=10))

        runner = self.app.test_cli_runner()
        result = runner.invoke(cli, ["delete", "5 weeks"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Unsupported timedelta '5 weeks'", result.output, result)
        self.assertNotIn("deleted", result.output, result)
        self.assertEqual(["OLD0001"], existing_serials())
