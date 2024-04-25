from .base import CliTestCase
from privacyidea.cli.tools.expired_users import expire


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
