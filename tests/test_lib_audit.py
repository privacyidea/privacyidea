# -*- coding: utf-8 -*-
"""
This tests the files
  lib/audit.py and
  lib/auditmodules/sqlaudit.py
"""
import datetime
import os

from mock import mock

from privacyidea.config import TestingConfig
from privacyidea.lib.audit import getAudit, search
from privacyidea.lib.auditmodules.containeraudit import Audit as ContainerAudit
from privacyidea.lib.auditmodules.loggeraudit import Audit as LoggerAudit
from privacyidea.lib.auditmodules.sqlaudit import column_length
from .base import MyTestCase, OverrideConfigTestCase
from testfixtures import log_capture

PUBLIC = "tests/testdata/public.pem"
PRIVATE = "tests/testdata/private.pem"
AUDIT_DB = 'sqlite:///tests/testdata//audit.sqlite'


class AuditTestCase(MyTestCase):
    """
    Test the Audit module
    """

    def setUp(self):
        self.Audit = getAudit(self.app.config)
        self.assertEqual(self.Audit.name, 'sqlaudit')
        self.Audit.clear()

    def tearDown(self):
        pass

    def test_00_write_audit(self):
        self.assertFalse(self.Audit.has_data)
        self.Audit.log({"action": "action1"})
        self.assertTrue(self.Audit.has_data)
        self.Audit.finalize_log()
        self.assertFalse(self.Audit.has_data)

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

        # remember the current time for later
        current_timestamp = datetime.datetime.now()

        # create a new audit log entry 2 seconds after the previous ones
        with mock.patch('privacyidea.models.datetime') as mock_dt:
            mock_dt.now.return_value = current_timestamp + datetime.timedelta(seconds=2)
            self.Audit.log({"action": "/validate/check",
                            "success": True})
            self.Audit.finalize_log()

        # freeze time at ``current_timestamp`` + 2.5s.
        # This is necessary because when doing unit tests on a CI server,
        # things will sometimes go slower than expected, which will
        # cause the very last assertion to fail.
        with mock.patch('datetime.datetime') as mock_dt:
            mock_dt.now.return_value = current_timestamp + datetime.timedelta(seconds=2.5)

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
        res = search(self.app.config, {"page": 1, "page_size": 10,
                                       "sortorder": "asc"})
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
        self.assertEqual(audit_log.total, 1)
        self.assertEqual(audit_log.auditdata[0].get("sig_check"), "FAIL")

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
        self.assertEqual(total, 5)
        # check that we have old style signatures in the DB
        db_entries = audit.search_query({"user": "testuser"})
        db_entry = next(db_entries)
        self.assertTrue(db_entry.signature.startswith('213842441384'), db_entry)
        # by default, PI_CHECK_OLD_SIGNATURES is false and thus the signature check fails
        audit_log = audit.search({"user": "testuser"})
        self.assertEqual(audit_log.total, 1)
        self.assertEqual(audit_log.auditdata[0].get("sig_check"), "FAIL")

        # they validate correctly when PI_CHECK_OLD_SIGNATURES is true
        # we need to create a new audit object to enable the new config
        self.app.config['PI_CHECK_OLD_SIGNATURES'] = True
        audit = getAudit(self.app.config)
        total = audit.get_count({})
        self.assertEqual(total, 5)
        audit_log = audit.search({"user": "testuser"})
        self.assertEqual(audit_log.total, 1)
        self.assertEqual(audit_log.auditdata[0].get("sig_check"), "OK")
        # except for entry number 4 where the 'realm' was added afterwards
        audit_log = audit.search({"realm": "realm1"})
        self.assertEqual(audit_log.total, 1)
        self.assertEqual(audit_log.auditdata[0].get("sig_check"), "FAIL")
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


class AuditFileTestCase(OverrideConfigTestCase):
    class Config(TestingConfig):
        # this needs to exist on app creation
        PI_LOGCONFIG = "tests/testdata/logging.cfg"

    def test_10_external_file_audit(self):
        a = LoggerAudit(config={})
        self.assertFalse(a.is_readable)
        self.assertFalse(a.has_data)
        a.log({"action": "action1"})
        self.assertTrue(a.has_data)
        a.finalize_log()
        self.assertFalse(a.has_data)
        with open("audit.log") as file:
            c = file.readlines()
            self.assertIn("action1", c[-1])
        os.unlink('audit.log')

    def test_20_logger_audit(self):
        a = LoggerAudit()
        a.log({"action": "something"})
        a.finalize_log()
        r = a.search({"action": "something"})
        # This is a non readable audit, so we got nothing
        self.assertEqual(r.auditdata, [])
        self.assertEqual(r.total, 0)

    @log_capture()
    def test_30_logger_audit_qualname(self, capture):
        # Check that the default qualname is 'privacyidea.lib.auditmodules.loggeraudit'
        current_utc_time = datetime.datetime(2018, 3, 4, 5, 6, 8)
        with mock.patch('privacyidea.lib.auditmodules.loggeraudit.datetime') as mock_dt:
            mock_dt.utcnow.return_value = current_utc_time
            a = LoggerAudit(config={})
            a.log({"action": "No PI_AUDIT_LOGGER_QUALNAME given"})
            a.finalize_log()
            capture.check_present(
                ('privacyidea.lib.auditmodules.loggeraudit', 'INFO',
                 '{{"action": "No PI_AUDIT_LOGGER_QUALNAME given", "policies": "", '
                 '"timestamp": "{timestamp}"}}'.format(timestamp=current_utc_time.isoformat())))

        # Now change the qualname to 'pi-audit'
        current_utc_time = datetime.datetime(2020, 3, 4, 5, 6, 8)
        with mock.patch('privacyidea.lib.auditmodules.loggeraudit.datetime') as mock_dt:
            mock_dt.utcnow.return_value = current_utc_time
            a = LoggerAudit(config={"PI_AUDIT_LOGGER_QUALNAME": "pi-audit"})
            a.log({"action": "PI_AUDIT_LOGGER_QUALNAME given"})
            a.finalize_log()
            capture.check_present(
                ('pi-audit', 'INFO',
                 '{{"action": "PI_AUDIT_LOGGER_QUALNAME given", "policies": "", '
                 '"timestamp": "{timestamp}"}}'.format(timestamp=current_utc_time.isoformat())))


class ContainerAuditTestCase(OverrideConfigTestCase):
    class Config(TestingConfig):
        # this needs to available on app creation
        PI_LOGCONFIG = "tests/testdata/logging.cfg"

    def test_10_container_audit(self):
        import os
        basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
        a = ContainerAudit({"PI_AUDIT_CONTAINER_WRITE": ["privacyidea.lib.auditmodules.loggeraudit",
                                                         "privacyidea.lib.auditmodules.sqlaudit"],
                            "PI_AUDIT_CONTAINER_READ": "privacyidea.lib.auditmodules.sqlaudit",
                            "PI_AUDIT_NO_SIGN": True,
                            "PI_AUDIT_SQL_URI": 'sqlite:///' + os.path.join(basedir, 'data-test.sqlite')})
        self.assertFalse(a.has_data)
        a.log({"action": "something_test_30"})
        self.assertTrue(a.has_data)
        a.finalize_log()
        self.assertFalse(a.has_data)
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

    def test_15_container_audit_check_audit(self):
        import os
        basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
        a = ContainerAudit({"PI_AUDIT_CONTAINER_WRITE": ["privacyidea.lib.auditmodules.loggeraudit",
                                                         "privacyidea.lib.auditmodules.sqlaudit"],
                            "PI_AUDIT_CONTAINER_READ": "privacyidea.lib.auditmodules.sqlaudit",
                            "PI_AUDIT_NO_SIGN": True,
                            "PI_AUDIT_SQL_URI": 'sqlite:///' + os.path.join(basedir, 'data-test.sqlite')})
        a.log({"action": "something_test_35"})
        a.finalize_log()
        r = a.search({"action": "*something_test_35*"})
        # The search should go to the sql audit
        self.assertEqual(r.total, 1)
        self.assertEqual(r.auditdata[0].get("action"), u"something_test_35")
        # now check the log file
        with open("audit.log") as file:
            c = file.readlines()
            self.assertIn("something_test_35", c[-1])
        os.unlink('audit.log')

    def test_20_container_audit_wrong_module(self):
        # Test what happens with a non-existing module
        import os
        basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
        module_config = {
            "PI_AUDIT_CONTAINER_WRITE": ["privacyidea.lib.auditmodules.doesnotexist",
                                         "privacyidea.lib.auditmodules.sqlaudit"],
            "PI_AUDIT_CONTAINER_READ": "privacyidea.lib.auditmodules.sqlaudit",
            "PI_AUDIT_NO_SIGN": True,
            "PI_AUDIT_SQL_URI": 'sqlite:///' + os.path.join(basedir, 'data-test.sqlite')}
        self.assertRaises(ImportError, ContainerAudit, module_config)
