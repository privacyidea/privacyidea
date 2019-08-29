# coding: utf-8
"""
This test file tests privacyidea/api/lib/ui.py.
"""

from mock import Mock

from privacyidea.lib.auth import ROLE
from privacyidea.lib.realm import delete_realm, set_realm
from privacyidea.lib.resolver import save_resolver, delete_resolver
from privacyidea.lib.policy import delete_all_policies, MAIN_MENU, SCOPE, set_policy, ACTION, delete_policy, PolicyClass
from privacyidea.api.lib import ui
from .base import MyTestCase, FakeFlaskG
from .base import PWFILE as FILE_PASSWORDS
from .base import PWFILE2 as FILE_PASSWD


class ApiLibUiTestCase(MyTestCase):
    def test_01_ui_get_menus(self):
        delete_all_policies()
        g = FakeFlaskG()
        g.audit_object = Mock()
        g.logged_in_user = {"username": "admin", "role": "admin", "realm": ""}
        g.policy_object = PolicyClass()

        # Without policies, the admin gets all
        menus = ui.get_main_menus(g)
        self.assertTrue(MAIN_MENU.USERS in menus)
        self.assertTrue(MAIN_MENU.TOKENS in menus)
        self.assertTrue(MAIN_MENU.COMPONENTS in menus)
        self.assertTrue(MAIN_MENU.CONFIG in menus)
        self.assertTrue(MAIN_MENU.MACHINES in menus)

        # Admin has only right to enroll HOTP! :-)
        set_policy("pol1", scope=SCOPE.ADMIN, user="admin",
                   action="enrollHOTP")
        menus = ui.get_main_menus(g)
        # Thus he can only see the token menu
        self.assertTrue(MAIN_MENU.USERS not in menus)
        self.assertTrue(MAIN_MENU.TOKENS in menus)
        self.assertTrue(MAIN_MENU.COMPONENTS not in menus)
        self.assertTrue(MAIN_MENU.CONFIG not in menus)
        self.assertTrue(MAIN_MENU.MACHINES not in menus)

        set_policy("pol2", scope=SCOPE.ADMIN, user="admin",
                   action=ACTION.USERLIST)
        menus = ui.get_main_menus(g)
        # Thus he can only see the token menu
        self.assertTrue(MAIN_MENU.USERS in menus)
        self.assertTrue(MAIN_MENU.TOKENS in menus)
        self.assertTrue(MAIN_MENU.COMPONENTS not in menus)
        self.assertTrue(MAIN_MENU.CONFIG not in menus)
        self.assertTrue(MAIN_MENU.MACHINES not in menus)

        set_policy("pol3", scope=SCOPE.ADMIN, user="admin",
                   action=ACTION.MACHINELIST)
        menus = ui.get_main_menus(g)
        # Thus he can only see the token menu
        self.assertTrue(MAIN_MENU.USERS in menus)
        self.assertTrue(MAIN_MENU.TOKENS in menus)
        self.assertTrue(MAIN_MENU.COMPONENTS not in menus)
        self.assertTrue(MAIN_MENU.CONFIG not in menus)
        self.assertTrue(MAIN_MENU.MACHINES in menus)

        set_policy("pol4", scope=SCOPE.ADMIN, user="admin",
                   action=ACTION.SYSTEMDELETE)
        menus = ui.get_main_menus(g)
        # Thus he can only see the token menu
        self.assertTrue(MAIN_MENU.USERS in menus)
        self.assertTrue(MAIN_MENU.TOKENS in menus)
        self.assertTrue(MAIN_MENU.COMPONENTS not in menus)
        self.assertTrue(MAIN_MENU.CONFIG in menus)
        self.assertTrue(MAIN_MENU.MACHINES in menus)

        delete_all_policies()

    def test_02_ui_tokentypes(self):
        g = FakeFlaskG()
        g.audit_object = Mock()
        g.logged_in_user = {"username": "admin", "role": "admin", "realm": "realm1"}
        g.policy_object = PolicyClass()
        g.client_ip = "127.0.0.1"
        # Without policies, the admin gets all
        tt = ui.get_enroll_tokentypes(g)
        self.assertTrue("hotp" in tt)
        self.assertTrue("totp" in tt)
        self.assertTrue("motp" in tt)
        self.assertTrue("sms" in tt)
        self.assertTrue("spass" in tt)
        self.assertTrue("sshkey" in tt)
        self.assertTrue("email" in tt)
        self.assertTrue("certificate" in tt)
        self.assertTrue("yubico" in tt)
        self.assertTrue("yubikey" in tt)
        self.assertTrue("radius" in tt)

        # An admin may only enroll Yubikeys
        set_policy(name="tokenEnroll", scope=SCOPE.ADMIN,
                   action="enrollYUBIKEY")

        tt = ui.get_enroll_tokentypes(g)
        self.assertFalse("hotp" in tt)
        self.assertFalse("totp" in tt)
        self.assertFalse("motp" in tt)
        self.assertFalse("sms" in tt)
        self.assertFalse("spass" in tt)
        self.assertFalse("sshkey" in tt)
        self.assertFalse("email" in tt)
        self.assertFalse("certificate" in tt)
        self.assertFalse("yubico" in tt)
        self.assertTrue("yubikey" in tt)
        self.assertFalse("radius" in tt)

        # A user may enroll nothing
        set_policy(name="someUserAction", scope=SCOPE.USER,
                   action="disable")
        g.logged_in_user = {"username": "kurt",
                            "realm": "realm",
                            "role": "user"}
        tt = ui.get_enroll_tokentypes(g)
        self.assertEqual(len(tt), 0)
        delete_policy("tokenEnroll")

        # Two admins:
        # adminA is allowed to enroll tokens in all realms
        # adminB is allowed to enroll tokens only in realmB

        set_policy(name="polAdminA", scope=SCOPE.ADMIN, user="adminA",
                   action="enrollHOTP, enrollTOTP")
        set_policy(name="polAdminB", scope=SCOPE.ADMIN, user="adminB",
                   realm="realmB",
                   action="enrollHOTP")
        # realm is empty, since in case of an admin, this is the admin realm
        g.logged_in_user = {"role": SCOPE.ADMIN,
                            "realm": "",
                            "username": "adminA"}
        rights = ui.get_enroll_tokentypes(g)
        self.assertTrue("hotp" in rights)
        self.assertTrue("totp" in rights)
        g.logged_in_user = {"role": SCOPE.ADMIN,
                            "realm": "",
                            "username": "adminB"}
        rights = ui.get_enroll_tokentypes(g)
        self.assertTrue("totp" not in rights)
        self.assertTrue("hotp" in rights)
        g.logged_in_user = {"role": SCOPE.ADMIN,
                            "realm": "",
                            "username": "adminC"}
        rights = ui.get_enroll_tokentypes(g)
        self.assertEqual(rights, {})
        delete_policy("polAdminA")
        delete_policy("polAdminB")

    def test_03_admin_realm(self):
        g = FakeFlaskG()
        g.audit_object = Mock()
        g.policy_object = PolicyClass()
        g.client_ip = "127.0.0.1"
        g.logged_in_user = {"username": "admin",
                            "role": "admin",
                            "realm": "realm1"}
        # Without policies, the admin gets all
        tt = ui.get_enroll_tokentypes(g)
        self.assertTrue("hotp" in tt)
        self.assertTrue("totp" in tt)
        self.assertTrue("motp" in tt)
        self.assertTrue("sms" in tt)
        self.assertTrue("spass" in tt)
        self.assertTrue("sshkey" in tt)
        self.assertTrue("email" in tt)
        self.assertTrue("certificate" in tt)
        self.assertTrue("yubico" in tt)
        self.assertTrue("yubikey" in tt)
        self.assertTrue("radius" in tt)

        # An admin in realm1 may only enroll Yubikeys
        set_policy(name="tokenEnroll", scope=SCOPE.ADMIN,
                   adminrealm="realm1",
                   action="enrollYUBIKEY")

        tt = ui.get_enroll_tokentypes(g)
        self.assertFalse("hotp" in tt)
        self.assertFalse("totp" in tt)
        self.assertFalse("motp" in tt)
        self.assertFalse("sms" in tt)
        self.assertFalse("spass" in tt)
        self.assertFalse("sshkey" in tt)
        self.assertFalse("email" in tt)
        self.assertFalse("certificate" in tt)
        self.assertFalse("yubico" in tt)
        self.assertTrue("yubikey" in tt)
        self.assertFalse("radius" in tt)

        # An admin in another admin realm may enroll nothing.
        g.logged_in_user = {"username": "admin",
                            "role": "admin",
                            "realm": "OtherRealm"}
        tt = ui.get_enroll_tokentypes(g)
        self.assertFalse("hotp" in tt)
        self.assertFalse("totp" in tt)
        self.assertFalse("motp" in tt)
        self.assertFalse("sms" in tt)
        self.assertFalse("spass" in tt)
        self.assertFalse("sshkey" in tt)
        self.assertFalse("email" in tt)
        self.assertFalse("certificate" in tt)
        self.assertFalse("yubico" in tt)
        self.assertFalse("yubikey" in tt)
        self.assertFalse("radius" in tt)
        delete_policy("tokenEnroll")

    def test_04_ui_get_rights(self):
        g = FakeFlaskG()
        g.audit_object = Mock()
        g.policy_object = PolicyClass()
        g.client_ip = "127.0.0.1"
        g.logged_in_user = {"role": ROLE.ADMIN,
                            "realm": "realm1",
                            "username": "admin"}
        set_policy(name="someUserAction", scope=SCOPE.USER,
                   action="disable")

        # Without policies, the admin gets all
        rights = ui.get_rights(g)
        self.assertTrue(len(rights) >= 60)

        # An admin may only enroll Yubikeys
        set_policy(name="tokenEnroll", scope=SCOPE.ADMIN,
                   action="enrollYUBIKEY")
        rights = ui.get_rights(g)
        self.assertEqual(rights, ["enrollYUBIKEY"])

        # A user may do something else...
        g.logged_in_user = {"role": ROLE.USER,
                            "realm": "realm2",
                            "username": "user"}
        set_policy(name="userpol", scope=SCOPE.USER, action="enable")
        rights = ui.get_rights(g)
        # there was still another policy...
        self.assertEqual(set(rights), {"enable", "disable"})

        delete_policy("tokenEnroll")
        delete_policy("userpol")
        # Two admins:
        # adminA is allowed to enroll tokens in all realms
        # adminB is allowed to enroll tokens only in realmB
        set_policy(name="polAdminA", scope=SCOPE.ADMIN, user="adminA",
                   action="enrollHOTP, enrollTOTP")
        set_policy(name="polAdminB", scope=SCOPE.ADMIN, user="adminB",
                   realm="realmB",
                   action="enrollHOTP")
        # realm is empty, since in case of an admin, this is the admin realm
        g.logged_in_user = {"role": SCOPE.ADMIN,
                            "realm": "",
                            "username": "adminA"}
        rights = ui.get_rights(g)
        self.assertTrue("enrollTOTP" in rights)
        self.assertTrue("enrollHOTP" in rights)
        g.logged_in_user = {"role": SCOPE.ADMIN,
                            "realm": "",
                            "username": "adminB"}
        rights = ui.get_rights(g)
        self.assertTrue("enrollTOTP" not in rights)
        self.assertTrue("enrollHOTP" in rights)
        g.logged_in_user = {"role": SCOPE.ADMIN,
                            "realm": "",
                            "username": "adminC"}
        rights = ui.get_rights(g)
        self.assertEqual(rights, [])
        delete_policy("polAdminA")
        delete_policy("polAdminB")

    def test_05_ui_rights_users_in_different_resolvers(self):
        g = FakeFlaskG()
        g.audit_object = Mock()
        g.policy_object = PolicyClass()
        g.client_ip = "127.0.0.1"
        # Create a realm with two resolvers
        rid = save_resolver({"resolver": "passwd",
                             "type": "passwdresolver",
                             "fileName": FILE_PASSWD})
        self.assertTrue(rid > 0, rid)

        rid = save_resolver({"resolver": "passwords",
                             "type": "passwdresolver",
                             "fileName": FILE_PASSWORDS})
        self.assertTrue(rid > 0, rid)

        # create user realm
        (added, failed) = set_realm("realm4",
                                    ["passwd", "passwords"])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 2)

        # A user may do something else...
        set_policy(name="userpol41", scope=SCOPE.USER, action="enable",
                   realm="realm4", resolver="passwd")
        set_policy(name="userpol42", scope=SCOPE.USER, action="remove",
                   realm="realm4", resolver="passwords")

        # The two users are in different resolvers and get different rights
        g.logged_in_user = {"role": ROLE.USER,
                            "realm": "realm4",
                            "username": "postfix"}
        rights = ui.get_rights(g)
        self.assertEqual(set(rights), {"enable", "disable"})

        g.logged_in_user = {"role": ROLE.USER,
                            "realm": "realm4",
                            "username": "usernotoken"}
        rights = ui.get_rights(g)
        self.assertEqual(set(rights), {"disable", "remove"})

        delete_policy("userpol41")
        delete_policy("userpol42")
        delete_realm("realm4")
        delete_resolver("passwords")
        delete_resolver("passwd")
        delete_all_policies()
