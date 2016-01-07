"""
This test file tests the lib/passwordreset.py
"""
from .base import MyTestCase
from privacyidea.lib.error import ConfigAdminError
from privacyidea.lib.smtpserver import (get_smtpservers, add_smtpserver,
                                        delete_smtpserver, get_smtpserver)
import smtpmock
from privacyidea.lib.error import privacyIDEAError
from privacyidea.lib.passwordreset import (create_recoverycode,
                                           check_recoverycode)
from privacyidea.lib.config import set_privacyidea_config
from privacyidea.lib.user import User, UserError


class RecoveryTestCase(MyTestCase):
    serial1 = "ser1"


    # set_user, get_user, reset, set_user_identifiers

    def test_00_init_users(self):
        self.setUp_user_realms()

    @smtpmock.activate
    def test_01_create_recovery(self):
        smtpmock.setdata(response={"user@localhost.localdomain": (200, "OK")})

        # missing configuration
        self.assertRaises(privacyIDEAError, create_recoverycode,
                          user=User("cornelius", self.realm1))

        # recover password with "recovery.identifier"
        r = add_smtpserver(identifier="myserver", server="1.2.3.4")
        self.assertTrue(r > 0)
        set_privacyidea_config("recovery.identifier", "myserver")
        r = create_recoverycode(User("cornelius", self.realm1))
        self.assertEqual(r, True)

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
