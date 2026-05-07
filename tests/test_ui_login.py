"""
This file tests the web UI Login

implementation is contained webui/login.py
"""
import pathlib
import re
import unittest.mock as mock

from flask import Response
from flask_babel import refresh

from privacyidea.app import create_app
from privacyidea.lib.policies.actions import PolicyAction, PasskeyLoginButtonOptions
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
                                "otp_pin_set_random_user", "privacyideaVersionNumber", "passkey_login"}
            self.assertSetEqual(expected_entries, set(config.keys()))

            self.assertEqual("static/customize", config["customization"])
            self.assertEqual("", config["custom_css"])
            self.assertEqual("", config["logo"])
            self.assertEqual("privacyIDEA Authentication System", config["page_title"])
            self.assertEqual("", config["realms"])
            self.assertEqual("", config["show_node"])
            self.assertEqual("templates/menu.html", config["customization_menu_file"])
            self.assertEqual("templates/baseline.html", config["customization_baseline_file"])
            self.assertEqual("", config["login_text"])
            self.assertEqual(get_version_number(), config["privacyideaVersionNumber"])
            self.assertEqual(PasskeyLoginButtonOptions.SHOW, config["passkey_login"])

    def test_02_get_ui_config_custom_values(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        self.app.config['PI_CUSTOMIZATION'] = '/my/custom/path'
        self.app.config["PI_LOGO"] = 'mylogo.png'
        self.app.config["PI_PAGE_TITLE"] = 'My Custom Title'

        set_policy("ui", scope=SCOPE.WEBUI,
                   action=f"{PolicyAction.REALMDROPDOWN}={self.realm1} {self.realm2},{PolicyAction.SHOW_NODE},"
                          f"{PolicyAction.CUSTOM_MENU}=myMenu.html,{PolicyAction.LOGIN_TEXT}=Please log in,"
                          f"{PolicyAction.PASSKEY_LOGIN}=hide")

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
            self.assertEqual("hide", config["passkey_login"])


class NewUIRoutingTestCase(MyTestCase):
    """Tests for the new Angular i18n routing logic."""

    _mock_response = Response(b"<html>index</html>", mimetype="text/html")

    def test_root_redirects_to_locale_when_build_exists(self):
        """GET / with German Accept-Language redirects to /app/v2/de/ when build exists."""
        with mock.patch("privacyidea.webui.login.os.path.isdir", return_value=True):
            with self.app.test_request_context("/", method="GET", headers={"Accept-Language": "de"}):
                res = self.app.full_dispatch_request()
        self.assertEqual(res.status_code, 302)
        self.assertIn("/app/v2/de/", res.location)

    def test_root_does_not_redirect_when_build_missing(self):
        """GET / with German Accept-Language falls back to old UI when no build."""
        with mock.patch("privacyidea.webui.login.os.path.isdir", return_value=False), \
             mock.patch("privacyidea.webui.login._serve_locale", return_value=None):
            with self.app.test_request_context("/", method="GET", headers={"Accept-Language": "de"}):
                res = self.app.full_dispatch_request()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, "text/html")

    def test_root_redirects_to_app_v2_for_english(self):
        """GET / with English redirects to /app/v2/ when build exists."""
        with mock.patch("privacyidea.webui.login._serve_locale", return_value=self._mock_response):
            with self.app.test_request_context("/", method="GET", headers={"Accept-Language": "en"}):
                res = self.app.full_dispatch_request()
        self.assertEqual(res.status_code, 302)
        self.assertIn("/app/v2/", res.location)

    def test_root_falls_back_to_old_ui_when_no_build(self):
        """GET / falls back to old Jinja2 UI when no Angular build exists."""
        with mock.patch("privacyidea.webui.login._serve_locale", return_value=None):
            with self.app.test_request_context("/", method="GET"):
                res = self.app.full_dispatch_request()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, "text/html")

    def test_locale_route_serves_index(self):
        """GET /app/v2/de/ serves the German index.html."""
        with mock.patch("privacyidea.webui.login._serve_locale", return_value=self._mock_response):
            with self.app.test_request_context("/app/v2/de/", method="GET"):
                res = self.app.full_dispatch_request()
        self.assertEqual(res.status_code, 200)

    def test_locale_route_with_subpath_serves_index(self):
        """GET /app/v2/de/tokens serves the German index.html (SPA fallback)."""
        with mock.patch("privacyidea.webui.login._serve_locale", return_value=self._mock_response):
            with self.app.test_request_context("/app/v2/de/tokens", method="GET"):
                res = self.app.full_dispatch_request()
        self.assertEqual(res.status_code, 200)

    def test_english_spa_fallback_serves_index(self):
        """GET /app/v2/some-route/ serves English index.html via 404 fallback."""
        with mock.patch("privacyidea.webui.login._serve_locale", return_value=self._mock_response):
            with self.app.test_request_context("/app/v2/tokens/", method="GET"):
                res = self.app.full_dispatch_request()
        self.assertEqual(res.status_code, 200)

    def test_locale_route_without_trailing_slash_redirects(self):
        """GET /app/v2/de (no trailing slash) redirects to /app/v2/de/."""
        with self.app.test_request_context("/app/v2/de", method="GET"):
            res = self.app.full_dispatch_request()
        self.assertIn(res.status_code, [301, 302, 308])
        self.assertIn("/app/v2/de/", res.location)

    def test_unknown_locale_falls_back_to_english(self):
        """GET /app/v2/invalid/ falls back to English when locale not in list."""
        def serve_side_effect(locale):
            return self._mock_response if locale == "en" else None

        with mock.patch("privacyidea.webui.login._serve_locale", side_effect=serve_side_effect):
            with self.app.test_request_context("/app/v2/invalid/", method="GET"):
                res = self.app.full_dispatch_request()
        self.assertIn(res.status_code, [200, 302])

    def test_zh_hant_underscore_mapper_uses_hyphen_directory(self):
        """_serve_locale maps zh_Hant (ICU) to zh-Hant (BCP 47) build directory."""
        with mock.patch("privacyidea.webui.login.os.path.isfile") as mock_isfile:
            mock_isfile.return_value = False
            with self.app.test_request_context("/"):
                from privacyidea.webui.login import _serve_locale
                _serve_locale("zh_Hant")
                checked_path = mock_isfile.call_args[0][0]
                self.assertIn("zh-Hant", checked_path)
                self.assertNotIn("zh_Hant", checked_path)

    def test_zh_hant_hyphen_accepted_by_serve_locale(self):
        """_serve_locale also accepts zh-Hant (BCP 47 URL form) and serves zh-Hant build."""
        with mock.patch("privacyidea.webui.login.os.path.isfile") as mock_isfile:
            mock_isfile.return_value = False
            with self.app.test_request_context("/"):
                from privacyidea.webui.login import _serve_locale
                _serve_locale("zh-Hant")
                # returns None (no build found) but did NOT reject due to whitelist
                checked_path = mock_isfile.call_args[0][0]
                self.assertIn("zh-Hant", checked_path)
