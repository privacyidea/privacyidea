from .base import CliTestCase
from privacyidea.cli.tools.cron import cli as privacyidea_cron


class PICronTestCase(CliTestCase):
    def test_01_picron_help(self):
        runner = self.app.test_cli_runner()
        result = runner.invoke(privacyidea_cron, ["-h"])
        self.assertIn("Execute all periodic tasks that are scheduled to run.",
                      result.output, result)
        self.assertIn("Show a list of available tasks that could be run.",
                      result.output, result)
        self.assertIn("Manually run a periodic task",
                      result.output, result)
