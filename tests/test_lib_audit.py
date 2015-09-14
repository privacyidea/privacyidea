"""
This tests the files
  lib/audit.py and
  lib/auditmodules/sqlaudit.py
"""

from .base import MyTestCase
from privacyidea.lib.audit import getAudit, search
import datetime

PUBLIC = "tests/testdata/public.pem"
PRIVATE = "tests/testdata/private.pem"

class AuditTestCase(MyTestCase):
    """
    Test the Audit module
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

    def test_00_write_audit(self):
        self.Audit.log({"action": "action1"})
        self.Audit.finalize_log()

        # next audit entry
        self.Audit.log({"action": "action2"})
        self.Audit.finalize_log()

        # 3rd audit entry
        self.Audit.log({"action": "action2"})
        self.Audit.finalize_log()

        # read audit entry
        audit_log = self.Audit.search({})
        self.assertTrue(audit_log.total == 3, audit_log.total)

    def test_01_get_total(self):
        self.Audit.log({"action": "action1"})
        self.Audit.finalize_log()

        # next audit entry
        self.Audit.log({"action": "action2"})
        self.Audit.finalize_log()

        # 3rd audit entry
        self.Audit.log({"action": "action2"})
        self.Audit.finalize_log()

        tot = self.Audit.get_total({})
        self.assertTrue(tot == 3, tot)
        audit_log = self.Audit.search({}, sortorder="desc")

        print("The Log:")
        print(audit_log)

        # with search filter
        tot = self.Audit.get_total({"action": "action2",
                                    "bullshit": "value"})
        self.assertTrue(tot == 2, "Total numbers: %s" % tot)

    def test_02_filter_search(self):
        # Prepare some audit entries:
        self.Audit.log({"serial": "serial1"})
        self.Audit.finalize_log()

        self.Audit.log({"serial": "serial1"})
        self.Audit.finalize_log()

        self.Audit.log({"serial": "serial2"})
        self.Audit.finalize_log()

        self.Audit.log({"serial": "oath"})
        self.Audit.finalize_log()

        audit_log = self.Audit.search({"serial": "serial1"})
        self.assertTrue(audit_log.total == 2, audit_log.total)

        audit_log = self.Audit.search({"serial": "serial2"})
        self.assertTrue(audit_log.total == 1, audit_log.total)

        audit_log = self.Audit.search({"serial": "*serial*"})
        self.assertTrue(audit_log.total == 3, audit_log.total)

        audit_log = self.Audit.search({"serial": "oath*"})
        self.assertTrue(audit_log.total == 1, audit_log.total)

    def test_03_lib_search(self):
        res = search(self.config, {"page": 1, "page_size": 10, "sortorder":
            "asc"})
        self.assertTrue(res.get("count") == 0, res)

    def test_04_lib_download(self):
        # Prepare some audit entries:
        self.Audit.log({"serial": "serial1"})
        self.Audit.finalize_log()

        self.Audit.log({"serial": "serial1"})
        self.Audit.finalize_log()

        self.Audit.log({"serial": "serial2"})
        self.Audit.finalize_log()

        self.Audit.log({"serial": "oath"})
        self.Audit.finalize_log()

        audit_log = self.Audit.csv_generator()
        self.assertTrue(type(audit_log).__name__ == "generator",
                        type(audit_log).__name__)

        for audit_entry in audit_log:
            self.assertTrue(type(audit_entry).__name__ == "unicode",
                            type(audit_entry).__name__)

    def test_05_dataframe(self):
        self.Audit.log({"action": "action1",
                        "serial": "s2"})
        self.Audit.finalize_log()

        # next audit entry
        self.Audit.log({"action": "action2",
                        "serial": "s1"})
        self.Audit.finalize_log()

        # 3rd audit entry
        self.Audit.log({"action": "action2",
                        "serial": "s1"})
        self.Audit.finalize_log()
        df = self.Audit.get_dataframe(start_time=datetime.datetime.now()
                                      -datetime.timedelta(days=7),
                                      end_time=datetime.datetime.now()
                                      +datetime.timedelta(days=1))
        series = df['serial'].value_counts()
        self.assertEqual(series.values[0], 2)
        self.assertEqual(series.values[1], 1)

