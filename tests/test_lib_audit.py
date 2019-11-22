# -*- coding: utf-8 -*-
"""
This tests the files
  lib/audit.py and
  lib/auditmodules/sqlaudit.py
"""
import os

from .base import MyTestCase, OverrideConfigTestCase
from mock import mock
from privacyidea.config import TestingConfig
from privacyidea.lib.audit import getAudit, search
from privacyidea.lib.auditmodules.sqlaudit import column_length
import datetime
import time
from privacyidea.lib.auditmodules.loggeraudit import Audit as LoggerAudit
from privacyidea.lib.auditmodules.containeraudit import Audit as ContainerAudit


PUBLIC = "tests/testdata/public.pem"
PRIVATE = "tests/testdata/private.pem"
AUDIT_DB = 'sqlite:///tests/testdata//audit.sqlite'


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
        # remember the current time for later
        current_timestamp = datetime.datetime.now()

        self.Audit.log({"action": "/validate/check",
                        "success": True})
        self.Audit.finalize_log()

        # freeze time at ``current_timestamp`` + 0.5s.
        # This is necessary because when doing unit tests on a CI server,
        # things will sometimes go slower than expected, which will
        # cause the very last assertion to fail.
        with mock.patch('datetime.datetime') as mock_dt:
            mock_dt.now.return_value = current_timestamp + datetime.timedelta(seconds=0.5)

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

        self.Audit.log({"serial": "oath", "user": u"nöäscii"})
        self.Audit.finalize_log()

        audit_log = self.Audit.csv_generator()
        self.assertTrue(type(audit_log).__name__ == "generator",
                        type(audit_log).__name__)

        count = 0
        for audit_entry in audit_log:
            self.assertTrue(type(audit_entry).__name__ in ["unicode", "str"],
                            type(audit_entry).__name__)
            count += 1
        self.assertEqual(count, 5)

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

        # check treatment of None and boolean values
        self.Audit.log({"token_type": None, "info": True})
        self.Audit._truncate_data()
        self.assertEqual(self.Audit.audit_data.get("token_type"), None)
        self.assertEqual(self.Audit.audit_data.get("info"), True)

        # check treatment of policy entries:
        self.Audit.log({"serial": long_serial,
                        "token_type": token_type,
                        "policies": u"Berlin,Hamburg,München,Köln,Frankfurt am Main,"
                                    u"Stuttgart,Düsseldorf,Dortmund,Essen,Leipzig,"
                                    u"Bremen,Dresden,Hannover,Nürnberg,Duisburg,Bochum,"
                                    u"Wuppertal,Bielefeld,Bonn,Münster,Karlsruhe,"
                                    u"Mannheim,Augsburg,Wiesbaden,Gelsenkirchen,Mönchengladbach,"
                                    u"Braunschweig,Kiel,Chemnitz,Aachen,Magdeburg"})
        self.Audit._truncate_data()
        self.assertTrue(len(self.Audit.audit_data.get("policies")) <= 255)
        # Some cities like Stuttgart and Düsseldorf already get truncated :-)
        self.assertEqual(u"Berlin,Hamburg,München,Köln,Frankfu+,Stuttga+,Düsseld+,Dortmund,Essen,Leipzig,Bremen,"
                         u"Dresden,Hannover,Nürnberg,Duisburg,Bochum,Wuppert+,Bielefe+,Bonn,Münster,Karlsru+,"
                         u"Mannheim,Augsburg,Wiesbaden,Gelsenki+,Möncheng+,Braunsch+,Kiel,Chemnitz,Aachen,Magdeburg",
                         self.Audit.audit_data.get("policies"))

    def test_07_sign_and_verify(self):
        # Test with broken key file paths
        self.app.config["PI_AUDIT_KEY_PUBLIC"] = PUBLIC
        self.app.config["PI_AUDIT_KEY_PRIVATE"] = '/path/not/valid'
        with self.assertRaises(Exception):
            getAudit(self.app.config)
        self.app.config["PI_AUDIT_KEY_PRIVATE"] = PRIVATE
        # Log a username as unicode with a non-ascii character
        self.Audit.log({"serial": "1234",
                        "action": "token/assign",
                        "success": True,
                        "user": u"kölbel"})
        self.Audit.finalize_log()
        audit_log = self.Audit.search({"user": u"kölbel"})
        self.assertEqual(audit_log.total, 1)
        self.assertEqual(audit_log.auditdata[0].get("user"), u"kölbel")
        self.assertEqual(audit_log.auditdata[0].get("sig_check"), "OK")
        # check the raw data from DB
        db_entries = self.Audit.search_query({'user': u'kölbel'})
        db_entry = next(db_entries)
        self.assertTrue(db_entry.signature.startswith('rsa_sha256_pss'), db_entry)
        # modify the table data
        db_entry.realm = 'realm1'
        self.Audit.session.merge(db_entry)
        self.Audit.session.commit()
        # and check if we get a failed signature check
        audit_log = self.Audit.search({"user": u"kölbel"})
        self.assertEquals(audit_log.total, 1)
        self.assertEquals(audit_log.auditdata[0].get("sig_check"), "FAIL")

    def test_08_policies(self):
        self.Audit.log({"action": "validate/check"})
        self.Audit.add_policy(["rule1", "rule2"])
        self.Audit.add_policy("rule3")
        self.Audit.finalize_log()
        audit_log = self.Audit.search({"policies": "*rule1*"})
        self.assertEqual(audit_log.total, 1)
        self.assertEqual(audit_log.auditdata[0].get("policies"), "rule1,rule2,rule3")

        self.Audit.add_policy(["rule4", "rule5"])
        self.Audit.finalize_log()
        audit_log = self.Audit.search({"policies": "*rule4*"})
        self.assertEqual(audit_log.total, 1)
        self.assertEqual(audit_log.auditdata[0].get("policies"), "rule4,rule5")

    def test_09_check_external_audit_db(self):
        self.app.config["PI_AUDIT_SQL_URI"] = AUDIT_DB
        audit = getAudit(self.app.config)
        total = audit.get_count({})
        self.assertEquals(total, 5)
        # check that we have old style signatures in the DB
        db_entries = audit.search_query({"user": "testuser"})
        db_entry = next(db_entries)
        self.assertTrue(db_entry.signature.startswith('213842441384'), db_entry)
        # by default, PI_CHECK_OLD_SIGNATURES is false and thus the signature check fails
        audit_log = audit.search({"user": "testuser"})
        self.assertEquals(audit_log.total, 1)
        self.assertEquals(audit_log.auditdata[0].get("sig_check"), "FAIL")

        # they validate correctly when PI_CHECK_OLD_SIGNATURES is true
        # we need to create a new audit object to enable the new config
        self.app.config['PI_CHECK_OLD_SIGNATURES'] = True
        audit = getAudit(self.app.config)
        total = audit.get_count({})
        self.assertEquals(total, 5)
        audit_log = audit.search({"user": "testuser"})
        self.assertEquals(audit_log.total, 1)
        self.assertEquals(audit_log.auditdata[0].get("sig_check"), "OK")
        # except for entry number 4 where the 'realm' was added afterwards
        audit_log = audit.search({"realm": "realm1"})
        self.assertEquals(audit_log.total, 1)
        self.assertEquals(audit_log.auditdata[0].get("sig_check"), "FAIL")
        # TODO: add new audit entry and check for new style signature
        # remove the audit SQL URI from app config
        self.app.config.pop("PI_AUDIT_SQL_URI", None)

    def test_10_check_tokentype(self):
        # Add a tokentype
        self.Audit.log({"action": "test10", "tokentype": "spass"})
        self.Audit.finalize_log()
        audit_log = self.Audit.search({"action": "test10"})
        self.assertEqual(audit_log.total, 1)
        # The tokentype was actually written as token_type
        self.assertEqual(audit_log.auditdata[0].get("token_type"), "spass")

    def test_20_logger_audit(self):
        a = LoggerAudit()
        a.log({"action": "something"})
        a.finalize_log()
        r = a.search({"action": "something"})
        # This is a non readable audit, so we got nothing
        self.assertEqual(r.auditdata, [])
        self.assertEqual(r.total, 0)

    def test_30_container_audit(self):
        import os
        basedir = os.path.abspath(os.path.dirname(__file__))
        basedir = "/".join(basedir.split("/")[:-1]) + "/"
        a = ContainerAudit({"PI_AUDIT_CONTAINER_WRITE": ["privacyidea.lib.auditmodules.loggeraudit",
                                                         "privacyidea.lib.auditmodules.sqlaudit"],
                            "PI_AUDIT_CONTAINER_READ": "privacyidea.lib.auditmodules.sqlaudit",
                            "PI_AUDIT_NO_SIGN": True,
                            "PI_AUDIT_SQL_URI": 'sqlite:///' + os.path.join(basedir, 'data-test.sqlite')})
        a.log({"action": "something_test_30"})
        a.finalize_log()
        c = a.get_count({})
        self.assertEqual(c, 1)
        t = a.get_total({})
        self.assertEqual(t, 1)
        r = a.search({"action": "*something*"})
        # The search should go to the sql audit
        self.assertEqual(r.total, 1)
        self.assertEqual(r.auditdata[0].get("action"), u"something_test_30")

        # Non readable read module!
        a = ContainerAudit({"PI_AUDIT_CONTAINER_WRITE": ["privacyidea.lib.auditmodules.loggeraudit"],
                            "PI_AUDIT_CONTAINER_READ": "privacyidea.lib.auditmodules.loggeraudit"})
        a.log({"action": "logger_30"})
        a.finalize_log()
        r = a.search({"action": "*logger*"})
        # The search should go to the sql audit
        self.assertEqual(r.total, 0)
        self.assertEqual(r.auditdata, [])

    def test_31_container_audit_wrong_module(self):
        # Test what happens with a non-existing module
        import os
        basedir = os.path.abspath(os.path.dirname(__file__))
        basedir = "/".join(basedir.split("/")[:-1]) + "/"
        module_config = {"PI_AUDIT_CONTAINER_WRITE": ["privacyidea.lib.auditmodules.doesnotexist",
                                                         "privacyidea.lib.auditmodules.sqlaudit"],
                         "PI_AUDIT_CONTAINER_READ": "privacyidea.lib.auditmodules.sqlaudit",
                         "PI_AUDIT_NO_SIGN": True,
                         "PI_AUDIT_SQL_URI": 'sqlite:///' + os.path.join(basedir, 'data-test.sqlite')}
        self.assertRaises(ImportError, ContainerAudit, module_config)


class AuditFileTestCase(OverrideConfigTestCase):
    class Config(TestingConfig):
        PI_LOGCONFIG = "tests/testdata/logging.cfg"
        PI_AUDIT_MODULE = "privacyidea.lib.auditmodules.loggeraudit"

    def test_01_external_file_audit(self):
        self.authenticate()
        c = []
        # do a simple GET /token/
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
        with open("audit.log") as file:
            c = file.readlines()

        self.assertIn("GET /token/", c[-1])
        os.unlink('audit.log')
