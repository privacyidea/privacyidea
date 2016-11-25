"""
This tests the files
  lib/stats.py and
"""

from .base import MyTestCase
from privacyidea.lib.audit import getAudit
from privacyidea.lib.stats import get_statistics

PUBLIC = "tests/testdata/public.pem"
PRIVATE = "tests/testdata/private.pem"


class StatsTestCase(MyTestCase):
    """
    Test the statistics module
    """

    def setUp(self):
        self.Audit = getAudit(self.app.config)
        self.Audit.clear()

    def tearDown(self):
        pass

    def test_00_statistics(self):
        self.Audit.log({"serial": "serial1"})
        self.Audit.finalize_log()

        # next audit entry
        self.Audit.log({"serial": "serial2"})
        self.Audit.finalize_log()

        # 3rd audit entry
        self.Audit.log({"serial": "serial3"})
        self.Audit.finalize_log()

        stat_json = get_statistics(self.Audit)
        self.assertTrue("serial_plot" in stat_json)
