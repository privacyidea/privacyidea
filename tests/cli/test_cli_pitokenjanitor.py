from .base import CliTestCase
from privacyidea.cli.privacyideatokenjanitor import cli as pi_token_janitor


class PITokenJanitorLoadTestCase(CliTestCase):
    def test_01_pitokenjanitor_help(self):
        runner = self.app.test_cli_runner()
        result = runner.invoke(pi_token_janitor, ["-h"])
        self.assertIn("Loads token data from a PSKC file.",
                      result.output, result)
        self.assertIn("This can update existing tokens in the privacyIDEA system.",
                      result.output, result)
        self.assertIn("Finds all tokens which match the conditions.",
                      result.output, result)
