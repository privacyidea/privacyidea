"""
This test file tests the lib/passwordreset.py
"""
from .base import MyTestCase, FakeFlaskG
from privacyidea.lib.smtpserver import add_smtpserver
from . import smtpmock
from sqlalchemy import select

from privacyidea.lib.error import PrivacyIDEAError, ConfigAdminError, UserError
from privacyidea.lib.framework import get_base_url
from privacyidea.models import PasswordReset, db
from privacyidea.lib.passwordreset import (create_recoverycode,
                                           check_recoverycode,
                                           is_password_reset)
from privacyidea.lib.config import set_privacyidea_config
from privacyidea.lib.user import User
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.realm import set_realm
from privacyidea.lib.policy import SCOPE, set_policy, PolicyClass
from privacyidea.lib.policies.actions import PolicyAction


class RecoveryTestCase(MyTestCase):
    serial1 = "ser1"

    parameters = {'Driver': 'sqlite',
                  'Server': '/tests/testdata/',
                  'Database': "testuser.sqlite",
                  'Table': 'users',
                  'Encoding': 'utf8',
                  'Editable': True,
                  'Map': '{ "username": "username", \
                    "userid" : "id", \
                    "email" : "email", \
                    "surname" : "name", \
                    "givenname" : "givenname", \
                    "password" : "password", \
                    "phone": "phone", \
                    "mobile": "mobile"}'
    }

    # add_user, get_user, reset, set_user_identifiers

    def test_00_init_users(self):
        self.setUp_user_realms()

    @smtpmock.activate
    def test_01_create_recovery(self):
        smtpmock.setdata(response={"user@localhost.localdomain": (200, "OK")})

        # missing configuration
        self.assertRaises(PrivacyIDEAError, create_recoverycode,
                          user=User("cornelius", self.realm1))

        # recover password with "recovery.identifier"
        r = add_smtpserver(identifier="myserver", server="1.2.3.4")
        self.assertTrue(r > 0)
        set_privacyidea_config("recovery.identifier", "myserver")
        r = create_recoverycode(User("cornelius", self.realm1))
        self.assertEqual(r, True)

        # A user without an email address on file does not crash, but raises a
        # clean UserError instead of an AttributeError on None. The rejected
        # request must not leave a PasswordReset row behind (validation happens
        # before the code is persisted).
        self.assertRaises(UserError, create_recoverycode,
                          user=User("selfservice", self.realm1))
        stmt = select(PasswordReset).where(PasswordReset.username == "selfservice")
        self.assertEqual(len(db.session.scalars(stmt).all()), 0)

    @smtpmock.activate
    def test_02_check_recoverycode(self):
        smtpmock.setdata(response={"user@localhost.localdomain": (200, "OK")})
        recoverycode = "reccode"
        user = User("cornelius", self.realm1)
        r = create_recoverycode(user, recoverycode=recoverycode)
        self.assertEqual(r, True)

        r = check_recoverycode(user, recoverycode)
        self.assertEqual(r, True)

        # The recovery code is not valid a second time
        r = check_recoverycode(user, recoverycode)
        self.assertEqual(r, False)

    def test_03_is_password_reset(self):
        # create resolver and realm
        param = self.parameters
        param["resolver"] = "register"
        param["type"] = "sqlresolver"
        r = save_resolver(param)
        self. assertTrue(r > 0)

        added, failed = set_realm("register", resolvers=[{'name': "register"}])
        self.assertGreater(len(added), 0, added)
        self.assertEqual(len(failed), 0, failed)

        g = FakeFlaskG()
        g.client_ip = "127.0.0.1"
        g.policy_object = PolicyClass()

        # No user policy at all
        r = is_password_reset(g)
        self.assertEqual(r, True)

        # create policy
        set_policy(name="pwrest", scope=SCOPE.USER, action=PolicyAction.PASSWORDRESET)
        r = is_password_reset(g)
        self.assertEqual(r, True)

        # create policy that does not allow password_reset
        set_policy(name="pwrest", scope=SCOPE.USER, action=PolicyAction.DELETE)
        r = is_password_reset(g)
        self.assertEqual(r, False)

    @smtpmock.activate
    def test_04_create_recovery_nonascii(self):
        smtpmock.setdata(response={"user@localhost.localdomain": (200, "OK")})
        recoverycode = "reccode"
        # create resolver and realm
        param = self.parameters
        param["resolver"] = "register"
        param["type"] = "sqlresolver"
        r = save_resolver(param)
        self. assertTrue(r > 0)
        # recover password with "recovery.identifier"
        r = add_smtpserver(identifier="myserver", server="1.2.3.4")
        self.assertTrue(r > 0)
        set_privacyidea_config("recovery.identifier", "myserver")
        r = create_recoverycode(User("nönäscii", "register"), recoverycode=recoverycode)
        self.assertEqual(r, True)

        user = User("nönäscii", "register")

        r = check_recoverycode(user, recoverycode)
        self.assertEqual(r, True)

        # The recovery code is not valid a second time
        r = check_recoverycode(user, recoverycode)
        self.assertEqual(r, False)

    def test_05_get_base_url(self):
        # Not configured + required -> refuse, so that a recovery link can
        # never be built from the untrusted HTTP Host header.
        self.app.config.pop("PI_BASE_URL", None)
        self.assertRaises(ConfigAdminError, get_base_url, required=True)
        # Not configured + not required -> empty string (link left blank, never
        # built from the request Host header)
        self.assertEqual(get_base_url(), "")
        # Configured -> value is returned, trailing slash stripped
        self.app.config["PI_BASE_URL"] = "https://pi.example.com/"
        try:
            self.assertEqual(get_base_url(), "https://pi.example.com")
            self.assertEqual(get_base_url(required=True), "https://pi.example.com")
        finally:
            self.app.config.pop("PI_BASE_URL", None)
