"""
This tests the files
  lib/audit.py and
  lib/auditmodules/sqlaudit.py
"""

from .base import MyTestCase
from privacyidea.lib.audit import getAudit

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
        # Patch ldap.initialize
        config = {"PI_AUDIT_MODULE":
                      "privacyidea.lib.auditmodules.sqlaudit",
                  "PI_AUDIT_KEY_PRIVATE": "tests/testdata/private.pem",
                  "PI_AUDIT_KEY_PUBLIC": "tests/testdata/public.pem",
                  "PI_AUDIT_SQL_URI": "sqlite://"}
        self.Audit = getAudit(config)

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
        audit_log = self.Audit.search({}, {})
        self.assertTrue(len(audit_log) == 3, audit_log)

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
        audit_log = self.Audit.search({}, {"sortorder": "desc"})

        print "The Log:"
        print audit_log

        # with search filter
        tot = self.Audit.get_total({"action": "action2",
                                    "bullshit": "value"})
        self.assertTrue(tot == 2, "Total numbers: %s" % tot)

    def test_02_empty_search(self):
        audit_log = self.Audit.search({"action": "XXXX"}, {})
        self.assertTrue(len(audit_log) == 0, audit_log)
