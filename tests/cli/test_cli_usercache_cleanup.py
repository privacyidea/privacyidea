from .base import CliTestCase
from privacyidea.cli.tools.usercache_cleanup import cli as privacyidea_usercache_cleanup


class PIUsercacheCleanupTestCase(CliTestCase):
    def test_01_piusercachecleanup_help(self):
        runner = self.app.test_cli_runner()
        result = runner.invoke(privacyidea_usercache_cleanup, ["-h"])
        self.assertIn("Delete all cache entries that are considered expired according to...",
                      result.output, result)
