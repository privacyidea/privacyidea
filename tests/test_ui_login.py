"""
This file tests the web UI Login

implementation is contained webui/login.py
"""
import pathlib
import re

from flask_babel import refresh

from privacyidea.app import create_app
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import set_policy, SCOPE, PolicyClass, delete_all_policies
from privacyidea.lib.utils import to_unicode, get_version_number
from privacyidea.models import db, save_config_timestamp
from .base import MyTestCase, MyApiTestCase


class AlternativeWebUI(MyTestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app('altUI', pathlib.Path.cwd() / "tests/testdata/test_pi.cfg", "")
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        db.create_all()
        # save the current timestamp to the database to avoid hanging cached
        # data
        save_config_timestamp()
        db.session.commit()

    def test_01_normal_login(self):
        # We just test, if the alterrnative page is called
        with self.app.test_request_context('/',
                                           method='GET'):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertEqual(res.mimetype, 'text/html', res)
            self.assertIn(b"This is an alternative UI", res.data)


class LoginUITestCase(MyTestCase):

    def test_01_normal_login(self):
        # We just test, if the login page can be called.
        with self.app.test_request_context('/',
                                           method='GET'):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertEqual(res.mimetype, 'text/html', res)
            self.assertTrue(b"/static/templates/baseline.html" in res.data)
            self.assertTrue(b"/static/templates/menu.html" in res.data)

    def test_02_deactivated(self):
        self.app.config['PI_UI_DEACTIVATED'] = True
        with self.app.test_request_context('/', method='GET'):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertEqual(res.mimetype, 'text/html', res)
            self.assertTrue(b"The privacyIDEA WebUI is deactivated." in res.data)
        self.app.config['PI_UI_DEACTIVATED'] = False

    def test_03_realm_dropdown(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        set_policy("realmdrop", scope=SCOPE.WEBUI,
                   action=f"{PolicyAction.REALMDROPDOWN}={self.realm1} {self.realm2}")
        with self.app.test_request_context('/', method='GET'):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertIsNotNone(re.search(r'id="REALMS" value=".*realm1.*realm2.*"',
                                           to_unicode(res.data)), res)

    def test_04_custom_menu_baseline(self):
        # We provide a non-existing file, so we can not read "privacyIDEA" in the footer.
        set_policy("custom1", scope=SCOPE.WEBUI,
                   action="{0!s}=mytemplates/nonexist_base.html".format(PolicyAction.CUSTOM_BASELINE))
        set_policy("custom2", scope=SCOPE.WEBUI,
                   action="{0!s}=mytemplates/nonexist_menu.html".format(PolicyAction.CUSTOM_MENU))

        with self.app.test_request_context('/',
                                           method='GET'):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(b"/static/mytemplates/nonexist_base.html" in res.data)
            self.assertTrue(b"/static/mytemplates/nonexist_menu.html" in res.data)

    def test_05_custom_login_text(self):
        set_policy("logtext", scope=SCOPE.WEBUI,
                   action="{0!s}=Go for it!".format(PolicyAction.LOGIN_TEXT))
        with self.app.test_request_context('/',
                                           method='GET'):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(b"Go for it!" in res.data)

    def test_06_remote_user(self):
        delete_all_policies()
        # test login when no policies are set
        self.assertEqual(len(PolicyClass().policies), 0, PolicyClass().policies)
        with self.app.test_request_context('/',
                                           method='GET',
                                           environ_base={'REMOTE_USER': 'foo'}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(b"<input type=hidden id=REMOTE_USER value=\"\">" in res.data)

        # test login with remote_user policy set
        set_policy("remote_user", scope=SCOPE.WEBUI,
                   action="{0!s}=allowed".format(PolicyAction.REMOTE_USER))
        with self.app.test_request_context('/',
                                           method='GET',
                                           environ_base={'REMOTE_USER': 'foo'}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(b"<input type=hidden id=REMOTE_USER value=\"foo\">" in res.data)

    def test_07_privacy_statement_link(self):
        set_policy("gdpr_link", scope=SCOPE.WEBUI,
                   action="{0!s}=https://privacyidea.org/".format(PolicyAction.GDPR_LINK))
        with self.app.test_request_context('/',
                                           method='GET'):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(b"https://privacyidea.org/" in res.data)


class LanguageTestCase(MyApiTestCase):

    def test_01_check_for_english_translation(self):
        with self.app.test_request_context('/auth/rights',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at,
                                               'Accept-Language': 'en'}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.json['result']['value']['totp'], 'TOTP: Time based One Time Passwords.')

    def test_02_check_for_german_translation(self):
        # It seems flask_babel caches the language between test requests, so we
        # have to refresh it
        refresh()

        with self.app.test_request_context('/auth/rights',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at,
                                               'Accept-Language': 'de'}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.json['result']['value']['totp'], 'TOTP: Zeitbasiertes Einmalpasswort.')


class ConfigTestCase(MyApiTestCase):
    """
    Tests the endpoint to receive the UI configuration as JSON.
    """

    def test_01_get_ui_config_defaults(self):
        """Test fetching the UI configuration"""
        with self.app.test_request_context("/config",
                                           method="GET"):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            config = result.get("value")
            expected_entries = {"instance", "backendUrl", "browser_lang", "remote_user", "force_remote_user", "theme",
                                "translation_warning", "password_reset", "hsm_ready", "has_job_queue", "customization",
                                "custom_css", "customization_menu_file", "customization_baseline_file", "realms",
                                "show_node", "external_links", "login_text", "gdpr_link", "logo", "page_title",
                                "otp_pin_set_random_user", "privacyideaVersionNumber"}
            self.assertSetEqual(expected_entries, set(config.keys()))

            self.assertEqual("static/customize", config["customization"])
            self.assertEqual("", config["custom_css"])
            self.assertEqual("privacyIDEA1.png", config["logo"])
            self.assertEqual("privacyIDEA Authentication System", config["page_title"])
            self.assertEqual("", config["realms"])
            self.assertEqual("", config["show_node"])
            self.assertEqual("templates/menu.html", config["customization_menu_file"])
            self.assertEqual("templates/baseline.html", config["customization_baseline_file"])
            self.assertEqual("", config["login_text"])
            self.assertEqual(get_version_number(), config["privacyideaVersionNumber"])

    def test_02_get_ui_config_custom_values(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        self.app.config['PI_CUSTOMIZATION'] = '/my/custom/path'
        self.app.config["PI_LOGO"] = 'mylogo.png'
        self.app.config["PI_PAGE_TITLE"] = 'My Custom Title'

        set_policy("ui", scope=SCOPE.WEBUI,
                   action=f"{PolicyAction.REALMDROPDOWN}={self.realm1} {self.realm2},{PolicyAction.SHOW_NODE},"
                          f"{PolicyAction.CUSTOM_MENU}=myMenu.html,{PolicyAction.LOGIN_TEXT}=Please log in")

        with self.app.test_request_context("/config",
                                           method="GET"):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            config = result.get("value")

            self.assertEqual("my/custom/path", config["customization"])
            self.assertEqual("", config["custom_css"])
            self.assertEqual("mylogo.png", config["logo"])
            self.assertEqual("My Custom Title", config["page_title"])
            self.assertEqual("realm1,realm2", config["realms"])
            self.assertEqual("Node1", config["show_node"])
            self.assertEqual("myMenu.html", config["customization_menu_file"])
            self.assertEqual("templates/baseline.html", config["customization_baseline_file"])
            self.assertEqual("Please log in", config["login_text"])
