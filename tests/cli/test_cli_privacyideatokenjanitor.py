# SPDX-FileCopyrightText: (C) 2023 Jona-Samuel Höhmann <jona-samuel.hoehmann@netknights.it>
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

import os
import tempfile
from unittest import mock

import yaml
from click.testing import Result

from .base import CliTestCase
from privacyidea.cli.privacyideatokenjanitor import cli as pi_token_janitor
from privacyidea.lib.error import ResolverError
from privacyidea.lib.realm import set_realm
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.token import enable_token, get_one_token, init_token
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.user import User
from privacyidea.models.token import TokenOwner

OTP_KEY = "3132333435363738393031323334353637383930"


class PITokenJanitorLoadTestCase(CliTestCase):
    def test_01_pitokenjanitor_help(self):
        runner = self.app.test_cli_runner()
        result = runner.invoke(pi_token_janitor, ["-h"])
        self.assertIn("Loads token data from the PSKC file.",
                      result.output, result)
        self.assertIn("Update existing tokens in the privacyIDEA system.",
                      result.output, result)
        self.assertIn("Finds all tokens which match the conditions.",
                      result.output, result)


class TokenJanitorFindTestCase(CliTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        save_resolver({"resolver": "janitorresolver", "type": "passwdresolver",
                       "fileName": "tests/testdata/passwords"})
        set_realm(realm="janitorrealm", resolvers=[{"name": "janitorresolver"}])

    def invoke_find(self, *arguments: str) -> Result:
        runner = self.app.test_cli_runner()
        return runner.invoke(pi_token_janitor, ["find", *arguments])

    def test_01_banner_goes_to_stderr(self) -> None:
        result = self.invoke_find("--serial", "^NOSUCHTOKEN$")
        self.assertEqual(0, result.exit_code, result.output)
        self.assertNotIn("/___/", result.stdout)
        self.assertIn("/___/", result.stderr)
        self.assertEqual(f"Token serial\tTokeninfo\n{'=' * 42}\n", result.stdout)

    def test_02_boolean_filters(self) -> None:
        init_token({"serial": "BOOLACTIVE", "type": "hotp", "otpkey": OTP_KEY})
        init_token({"serial": "BOOLDISABLED", "type": "hotp", "otpkey": OTP_KEY})
        enable_token("BOOLDISABLED", enable=False)
        init_token({"serial": "BOOLASSIGNED", "type": "hotp", "otpkey": OTP_KEY},
                   user=User("cornelius", "janitorrealm"))

        result = self.invoke_find("--serial", "^BOOL")
        self.assertEqual(0, result.exit_code, result.output)
        for serial in ["BOOLACTIVE", "BOOLDISABLED", "BOOLASSIGNED"]:
            self.assertIn(serial, result.stdout)

        for value in ["false", "False", "0", "no", "off", "f", "n"]:
            result = self.invoke_find("--serial", "^BOOL", "--active", value)
            self.assertEqual(0, result.exit_code, result.output)
            self.assertIn("BOOLDISABLED", result.stdout)
            self.assertNotIn("BOOLACTIVE", result.stdout)

        for value in ["true", "TRUE", "1", "yes", "on", "t", "y"]:
            result = self.invoke_find("--serial", "^BOOL", "--active", value)
            self.assertEqual(0, result.exit_code, result.output)
            self.assertIn("BOOLACTIVE", result.stdout)
            self.assertNotIn("BOOLDISABLED", result.stdout)

        result = self.invoke_find("--serial", "^BOOL", "--assigned", "yes")
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("BOOLASSIGNED", result.stdout)
        self.assertNotIn("BOOLACTIVE", result.stdout)

        result = self.invoke_find("--serial", "^BOOL", "--assigned", "no")
        self.assertEqual(0, result.exit_code, result.output)
        self.assertNotIn("BOOLASSIGNED", result.stdout)
        self.assertIn("BOOLACTIVE", result.stdout)

        # A value that is not a boolean is a usage error, the command does not run
        for option in ["--active", "--assigned", "--orphaned"]:
            result = self.invoke_find("--serial", "^BOOL", option, "None")
            self.assertEqual(2, result.exit_code, result.output)
            self.assertIn(f"Invalid value for '{option}'", result.output)
            self.assertNotIn("BOOLACTIVE", result.stdout)

    def test_03_orphaned_on_error(self) -> None:
        init_token({"serial": "ORPHANERROR", "type": "hotp", "otpkey": OTP_KEY},
                   user=User("cornelius", "janitorrealm"))
        # The user store fails while the owner of the token is looked up
        with mock.patch.object(TokenClass, "user", new_callable=mock.PropertyMock,
                               side_effect=ResolverError("user store not reachable")):
            result = self.invoke_find("--serial", "^ORPHANERROR$", "--orphaned", "true")
            self.assertEqual(0, result.exit_code, result.output)
            self.assertNotIn("ORPHANERROR", result.stdout)

            result = self.invoke_find("--serial", "^ORPHANERROR$", "--orphaned", "false")
            self.assertEqual(0, result.exit_code, result.output)
            self.assertIn("ORPHANERROR", result.stdout)

            result = self.invoke_find("--serial", "^ORPHANERROR$", "--orphaned", "true",
                                      "--orphaned-on-error", "True")
            self.assertEqual(0, result.exit_code, result.output)
            self.assertIn("ORPHANERROR", result.stdout)

        # Without an error the owner exists and the token is not orphaned
        result = self.invoke_find("--serial", "^ORPHANERROR$", "--orphaned", "true", "--orphaned-on-error", "True")
        self.assertEqual(0, result.exit_code, result.output)
        self.assertNotIn("ORPHANERROR", result.stdout)

    def test_03b_owner_of_a_deleted_resolver_is_orphaned(self) -> None:
        # A deleted resolver is certain, unlike an error of the user store, so --orphaned-on-error is not needed
        token = init_token({"serial": "ORPHANRESOLVER", "type": "hotp", "otpkey": OTP_KEY})
        TokenOwner(token_id=token.token.id, user_id="1000", resolver="deletedresolver",
                   realmname="janitorrealm").save()

        result = self.invoke_find("--serial", "^ORPHANRESOLVER$", "--orphaned", "true")
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("ORPHANRESOLVER", result.stdout)

    def test_04_csv_export_contains_totp_time_step(self) -> None:
        init_token({"serial": "TOTPCSV", "type": "totp", "otpkey": OTP_KEY, "timeStep": "60"})
        init_token({"serial": "HOTPCSV", "type": "hotp", "otpkey": OTP_KEY})

        result = self.invoke_find("--serial", "^(TOTPCSV|HOTPCSV)$", "--action", "export", "--csv")
        self.assertEqual(0, result.exit_code, result.output)
        lines = sorted(result.stdout.splitlines())
        self.assertEqual([f"n/a, HOTPCSV, {OTP_KEY}, hotp, 6", f"n/a, TOTPCSV, {OTP_KEY}, totp, 6, 60"], lines)


class TokenJanitorUpdateTestCase(CliTestCase):

    def export_yaml(self, serial: str) -> list:
        runner = self.app.test_cli_runner()
        result = runner.invoke(pi_token_janitor, ["find", "--serial", f"^{serial}$", "--action", "export", "--yaml"])
        self.assertEqual(0, result.exit_code, result.output)
        # stdout only carries the export, so it can be read as YAML
        return yaml.safe_load(result.stdout)

    def run_update(self, token_list: list) -> None:
        runner = self.app.test_cli_runner()
        with tempfile.TemporaryDirectory() as directory:
            file_name = os.path.join(directory, "tokens.yaml")
            with open(file_name, "w") as yaml_file:
                yaml_file.write(yaml.safe_dump(token_list))
            result = runner.invoke(pi_token_janitor, ["update", file_name])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertNotIn("Failed to update token", result.output)

    def create_used_token(self, serial: str, count: int, failcount: int) -> None:
        token = init_token({"serial": serial, "type": "hotp", "otpkey": OTP_KEY})
        token.token.count = count
        token.token.failcount = failcount
        token.token.save()

    def test_01_update_keeps_counters(self) -> None:
        self.create_used_token("UPDATEKEEP", count=42, failcount=3)
        token_list = self.export_yaml("UPDATEKEEP")
        self.assertEqual(1, len(token_list))
        self.assertEqual(42, token_list[0]["counter"])
        self.assertEqual(3, token_list[0]["failcount"])

        self.run_update(token_list)

        token = get_one_token(serial="UPDATEKEEP")
        self.assertEqual(OTP_KEY, token.token.get_otpkey().getKey().decode())
        self.assertEqual(42, token.token.count)
        self.assertEqual(3, token.token.failcount)

    def test_02_update_without_counters_in_export(self) -> None:
        self.create_used_token("UPDATENOCOUNT", count=17, failcount=2)
        token_list = self.export_yaml("UPDATENOCOUNT")
        del token_list[0]["counter"]
        del token_list[0]["failcount"]

        self.run_update(token_list)

        token = get_one_token(serial="UPDATENOCOUNT")
        self.assertEqual(17, token.token.count)
        self.assertEqual(2, token.token.failcount)

    def test_03_update_takes_a_higher_otp_counter_and_keeps_the_fail_counter(self) -> None:
        self.create_used_token("UPDATEHIGHER", count=10, failcount=5)
        token_list = self.export_yaml("UPDATEHIGHER")
        # The export has a higher OTP counter, which the token takes, and a higher fail counter, which it does not
        token_list[0]["counter"] = 100
        token_list[0]["failcount"] = 9

        self.run_update(token_list)

        token = get_one_token(serial="UPDATEHIGHER")
        self.assertEqual(100, token.token.count)
        self.assertEqual(5, token.token.failcount)

    def test_05_update_skips_an_entry_without_serial_and_takes_one_without_owner(self) -> None:
        self.create_used_token("UPDATEGUARD", count=7, failcount=0)
        token_list = self.export_yaml("UPDATEGUARD")
        entry_without_serial = {key: value for key, value in token_list[0].items() if key != "serial"}
        entry_without_serial["otpkey"] = "00" * 20
        entry_without_owner = {key: value for key, value in token_list[0].items() if key != "owner"}

        runner = self.app.test_cli_runner()
        with tempfile.TemporaryDirectory() as directory:
            file_name = os.path.join(directory, "tokens.yaml")
            with open(file_name, "w") as yaml_file:
                yaml_file.write(yaml.safe_dump([entry_without_serial, entry_without_owner]))
            result = runner.invoke(pi_token_janitor, ["update", file_name])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Skipping an entry without a serial.", result.output)
        self.assertIn("Updated token UPDATEGUARD.", result.output)
        token = get_one_token(serial="UPDATEGUARD")
        self.assertEqual(OTP_KEY, token.token.get_otpkey().getKey().decode())
        self.assertEqual(7, token.token.count)

    def test_04_update_keeps_the_token_kind(self) -> None:
        self.create_used_token("UPDATEKIND", count=1, failcount=0)
        get_one_token(serial="UPDATEKIND").write_tokeninfo("tokenkind", "hardware")
        token_list = self.export_yaml("UPDATEKIND")

        self.run_update(token_list)

        self.assertEqual("hardware", get_one_token(serial="UPDATEKIND").get_tokeninfo("tokenkind"))
