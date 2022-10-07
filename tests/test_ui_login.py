# -*- coding: utf-8 -*-

"""
This file tests the web UI Login

implementation is contained webui/login.py
"""
from .base import MyTestCase, MyApiTestCase
from privacyidea.lib.policy import set_policy, SCOPE, ACTION, PolicyClass, delete_all_policies
from privacyidea.lib.utils import to_unicode
import re
from privacyidea.app import create_app
from privacyidea.models import db, save_config_timestamp


class AlternativeWebUI(MyTestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app('altUI', "")
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
                   action="{0!s}=allowed".format(ACTION.REMOTE_USER))
        with self.app.test_request_context('/',
                                           method='GET',
                                           environ_base={'REMOTE_USER': 'foo'}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(b"<input type=hidden id=REMOTE_USER value=\"foo\">" in res.data)

    def test_07_privacy_statement_link(self):
        set_policy("gdpr_link", scope=SCOPE.WEBUI,
                   action="{0!s}=https://privacyidea.org/".format(ACTION.GDPR_LINK))
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
        with self.app.test_request_context('/auth/rights',
                                           method='GET',
                                           headers={
                                               'Authorization': self.at,
                                               'Accept-Language': 'de'}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.json['result']['value']['totp'], 'TOTP: Zeitbasiertes Einmalpasswort.')
