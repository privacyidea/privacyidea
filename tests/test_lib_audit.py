"""
This tests the files
  lib/audit.py and
  lib/auditmodules/sqlaudit.py
"""

from .base import MyTestCase
from privacyidea.lib.audit import getAudit, search
from privacyidea.lib.auditmodules.sqlaudit import column_length
import datetime
import time
from privacyidea.models import db
from privacyidea.app import create_app


PUBLIC = "tests/testdata/public.pem"
PRIVATE = "tests/testdata/private.pem"

class AuditTestCase(MyTestCase):
    """
    Test the Audit module
    """

    def setUp(self):
        self.Audit = getAudit(self.app.config)
        self.Audit.clear()

    def tearDown(self):
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
        self.assertTrue(tot == 2, "Total numbers: {0!s}".format(tot))

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

        # Search audit entries one minute in the future
        audit_log = self.Audit.search({}, timelimit=datetime.timedelta(
            minutes=-1))
        self.assertEqual(len(audit_log.auditdata), 0)

    def test_02_get_count(self):
        # Prepare some audit entries:
        self.Audit.log({"action": "/validate/check",
                        "success": True})
        self.Audit.finalize_log()

        self.Audit.log({"action": "/validate/check",
                        "success": True})
        self.Audit.finalize_log()

        self.Audit.log({"action": "/validate/check",
                        "success": False})
        self.Audit.finalize_log()
        time.sleep(2)

        self.Audit.log({"action": "/validate/check",
                        "success": True})
        self.Audit.finalize_log()

        # get 4 authentications
        r = self.Audit.get_count({"action": "/validate/check"})
        self.assertEqual(r, 4)

        # get one failed authentication
        r = self.Audit.get_count({"action": "/validate/check"}, success=False)
        self.assertEqual(r, 1)

        # get one authentication during the last second
        r = self.Audit.get_count({"action": "/validate/check"}, success=True,
                                 timedelta=datetime.timedelta(seconds=1))
        self.assertEqual(r, 1)

    def test_03_lib_search(self):
        res = search(self.app.config, {"page": 1, "page_size": 10, "sortorder":
            "asc"})
        self.assertTrue(res.get("count") == 0, res)

        res = search(self.app.config, {"timelimit": "-1d"})
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
            self.assertTrue(type(audit_entry).__name__ in ["unicode", "str"],
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

    def test_06_truncate_data(self):
        long_serial = "This serial is much to long, you know it!"
        token_type = "12345678901234567890"
        self.Audit.log({"serial": long_serial,
                        "token_type": token_type})
        self.Audit._truncate_data()
        self.assertEqual(len(self.Audit.audit_data.get("serial")),
                         column_length.get("serial"))
        self.assertEqual(len(self.Audit.audit_data.get("token_type")),
                         column_length.get("token_type"))
