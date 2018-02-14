"""
This file tests the web UI Login

implementation is contained webui/login.py
"""
from .base import MyTestCase
from privacyidea.lib.policy import set_policy, SCOPE, ACTION


class LoginUITestCase(MyTestCase):

    def test_01_normal_login(self):
        # We just test, if the login page can be called.
        with self.app.test_request_context('/',
                                           method='GET'):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue("/static/templates/baseline.html" in res.data)
            self.assertTrue("/static/templates/menu.html" in res.data)

    def test_02_custom_menu_baseline(self):
        # We provide a non-existing file, so we can not read "privacyIDEA" in the footer.
        set_policy("custom1", scope=SCOPE.WEBUI,
                   action="{0!s}=mytemplates/nonexist.html".format(ACTION.CUSTOM_BASELINE))
        set_policy("custom2", scope=SCOPE.WEBUI,
                   action="{0!s}=mytemplates/nonexist.html".format(ACTION.CUSTOM_MENU))

        with self.app.test_request_context('/',
                                           method='GET'):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue("/static/mytemplates/nonexist.html" in res.data)
            self.assertTrue("/static/mytemplates/nonexist.html" in res.data)