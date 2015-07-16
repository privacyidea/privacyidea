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

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        pass
        self.config = {"PI_AUDIT_MODULE":
                       "privacyidea.lib.auditmodules.sqlaudit",
                       "PI_AUDIT_KEY_PRIVATE": "tests/testdata/private.pem",
                       "PI_AUDIT_KEY_PUBLIC": "tests/testdata/public.pem",
                       "PI_AUDIT_SQL_URI": "sqlite://"}
        self.Audit = getAudit(self.config)
        self.Audit.clear()

    def tearDown(self):
        # Stop patching ldap.initialize and reset state.
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
