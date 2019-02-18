"""
This file tests the web UI Login

implementation is contained webui/login.py
"""
from .base import MyTestCase
from privacyidea.lib.policy import set_policy, SCOPE, ACTION
from privacyidea.lib.utils import to_unicode
import re


class LoginUITestCase(MyTestCase):

    def test_01_normal_login(self):
        # We just test, if the login page can be called.
        with self.app.test_request_context('/',
                                           method='GET'):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(b"/static/templates/baseline.html" in res.data)
            self.assertTrue(b"/static/templates/menu.html" in res.data)

    def test_02_deactivated(self):
        self.app.config['PI_UI_DEACTIVATED'] = True
        with self.app.test_request_context('/', method='GET'):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(b"The privacyIDEA WebUI is deactivated." in res.data)
        self.app.config['PI_UI_DEACTIVATED'] = False

    def test_03_realm_dropdown(self):
        set_policy("realmdrop", scope=SCOPE.WEBUI,
                   action="{0!s}=Hello World".format(ACTION.REALMDROPDOWN))
        with self.app.test_request_context('/', method='GET'):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertIsNotNone(re.search(r'id="REALMS" value=".*World.*"',
                                           to_unicode(res.data)), res)

    def test_04_custom_menu_baseline(self):
        # We provide a non-existing file, so we can not read "privacyIDEA" in the footer.
        set_policy("custom1", scope=SCOPE.WEBUI,
                   action="{0!s}=mytemplates/nonexist_base.html".format(ACTION.CUSTOM_BASELINE))
        set_policy("custom2", scope=SCOPE.WEBUI,
                   action="{0!s}=mytemplates/nonexist_menu.html".format(ACTION.CUSTOM_MENU))

        with self.app.test_request_context('/',
                                           method='GET'):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(b"/static/mytemplates/nonexist_base.html" in res.data)
            self.assertTrue(b"/static/mytemplates/nonexist_menu.html" in res.data)

    def test_05_custom_login_text(self):
        set_policy("logtext", scope=SCOPE.WEBUI,
                   action="{0!s}=Go for it!".format(ACTION.LOGIN_TEXT))
        with self.app.test_request_context('/',
                                           method='GET'):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(b"Go for it!" in res.data)

