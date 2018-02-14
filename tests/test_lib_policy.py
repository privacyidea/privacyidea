# coding: utf-8
"""
This test file tests the lib.policy.py

The lib.policy.py only depends on the database model.
"""
from .base import MyTestCase

from privacyidea.lib.policy import (set_policy, delete_policy,
                                    import_policies, export_policies,
                                    get_static_policy_definitions,
                                    PolicyClass, SCOPE, enable_policy,
                                    PolicyError, ACTION, MAIN_MENU,
                                    delete_all_policies)
from privacyidea.lib.realm import (set_realm, delete_realm, get_realms)
from privacyidea.lib.resolver import (save_resolver, get_resolver_list,
                                      delete_resolver)
from privacyidea.lib.user import User
import datetime
PWFILE = "tests/testdata/passwords"


def _check_policy_name(polname, policies):
    """
    Checks if the polname is contained in the policies list.
    """
    contained = False
    for pol in policies:
        if pol.get("name") == polname:
            contained = True
            break
    return contained


class PolicyTestCase(MyTestCase):
    """
    Test the policies on a database level
    """

    def test_01_create_simple_policy(self):
        p = set_policy(name="pol1",
                       action="read",
                       scope="system")
        self.assertTrue(p > 0)

        p = set_policy(name="pol2",
                       action="tokentype=HOTP",
                       scope=SCOPE.AUTHZ)
        self.assertTrue(p > 0)

        p = set_policy(name="pol3",
                       action="serial=OATH",
                       scope=SCOPE.AUTHZ)
        self.assertTrue(p > 0)

        p = set_policy(name="pol4",
                       action="enroll, init, disable , enable",
                       scope="admin")
        self.assertTrue(p > 0)

        P = PolicyClass()
        policies = P.get_policies(name="pol3")
        # only one policy found
        self.assertTrue(len(policies) == 1, len(policies))

        policies = P.get_policies(scope=SCOPE.AUTHZ)
        self.assertTrue(len(policies) == 2, len(policies))

        policies = P.get_policies(scope=SCOPE.AUTHZ,
                                  action="tokentype")
        self.assertTrue(len(policies) == 1, len(policies))

        policies = P.get_policies(scope="admin",
                                  action="disable")
        self.assertTrue(len(policies) == 1, len(policies))
        self.assertTrue(policies[0].get("name") == "pol4")

    def test_02_update_policies(self):
        p = set_policy(name="pol1",
                       action="read",
                       scope="system",
                       realm="*",
                       resolver="*",
                       user="*",
                       client="0.0.0.0/0",
                       active=False)
        self.assertTrue(p > 0)

        p = set_policy(name="pol2",
                       action="tokentype=HOTP",
                       scope=SCOPE.AUTHZ,
                       realm="*")
        self.assertTrue(p > 0)

        p = set_policy(name="pol2a",
                       action="tokentype=TOTP",
                       scope=SCOPE.AUTHZ,
                       realm="realm2")
        self.assertTrue(p > 0)

        p = set_policy(name="pol3",
                       action="serial=OATH",
                       scope=SCOPE.AUTHZ,
                       realm="realm1",
                       resolver="resolver1")
        self.assertTrue(p > 0)

        p = set_policy(name="pol4",
                       action="enroll, init, disable , enable",
                       scope="admin",
                       realm="realm2",
                       user="admin, superroot")
        self.assertTrue(p > 0)

        # enable and disable policies
        policies = PolicyClass().get_policies(active=False)
        num_old = len(policies)
        p = enable_policy("pol4", False)
        policies = PolicyClass().get_policies(active=False)
        self.assertTrue(num_old + 1 == len(policies), (num_old, len(policies)))
        p = enable_policy("pol4", True)
        policies = PolicyClass().get_policies(active=False)
        self.assertTrue(num_old == len(policies), len(policies))

        # find inactive policies
        P = PolicyClass()
        policies = P.get_policies(active=False)
        self.assertTrue(len(policies) == 1, len(policies))
        self.assertTrue(policies[0].get("name") == "pol1")

        # find policies action tokentype
        policies = P.get_policies(action="tokentype")
        self.assertTrue(len(policies) == 2, policies)
        # find policies action serial
        policies = P.get_policies(action="serial")
        self.assertTrue(len(policies) == 1, policies)
        # find policies with scope authorization
        policies = P.get_policies(scope=SCOPE.AUTHZ)
        self.assertTrue(len(policies) == 3, policies)
        # find policies authorization and realm2
        policies = P.get_policies(action="tokentype", scope=SCOPE.AUTHZ)
        self.assertTrue(len(policies) == 2, policies)
        # find policies with user admin
        policies = P.get_policies(scope="admin", user="admin")
        self.assertTrue(len(policies) == 1, "{0!s}".format(len(policies)))
        # find policies with resolver2 and authorization. THe result should
        # be pol2 and pol2a
        policies = P.get_policies(resolver="resolver2", scope=SCOPE.AUTHZ)
        self.assertTrue(len(policies) == 2, policies)

        # find policies with realm1 and authorization. We also include the
        # "*" into the result list. We find pol2 and pol3
        policies = P.get_policies(realm="realm1", scope=SCOPE.AUTHZ)
        self.assertTrue(len(policies) == 2, policies)

        # find policies with resolver1 and authorization.
        # All other authorization policies will also match, since they either
        # user * or
        # have no destinct information about resolvers
        policies = P.get_policies(resolver="resolver1", scope=SCOPE.AUTHZ)
        self.assertTrue(len(policies) == 3, policies)

    def test_04_delete_policy(self):
        delete_policy(name="pol4")
        P = PolicyClass()
        pol4 = P.get_policies(name="pol4")
        self.assertTrue(pol4 == [], pol4)

    def test_05_export_policies(self):
        P = PolicyClass()
        policies = P.get_policies()
        file = export_policies(policies)
        self.assertTrue("[pol1]" in file, file)
        self.assertTrue("[pol2]" in file, file)
        self.assertTrue("[pol3]" in file, file)

    def test_06_import_policies(self):
        P = PolicyClass()
        file = export_policies(P.get_policies())
        delete_policy("pol1")
        delete_policy("pol2")
        delete_policy("pol3")
        P = PolicyClass()
        policies = P.get_policies()
        self.assertFalse(_check_policy_name("pol1", policies), policies)
        self.assertFalse(_check_policy_name("pol2", policies), policies)
        self.assertFalse(_check_policy_name("pol3", policies), policies)
        # Now import the policies again
        num = import_policies(file)
        self.assertTrue(num == 4, num)
        P = PolicyClass()
        policies = P.get_policies()
        self.assertTrue(_check_policy_name("pol1", policies), policies)
        self.assertTrue(_check_policy_name("pol2", policies), policies)
        self.assertTrue(_check_policy_name("pol3", policies), policies)

    def test_07_client_policies(self):
        delete_policy(name="pol2a")
        set_policy(name="pol1", scope="s", client="172.16.0.3, 172.16.0.4/24")
        set_policy(name="pol2", scope="s", client="192.168.0.0/16, "
                                                  "-192.168.1.1")
        set_policy(name="pol3", scope="s", client="10.0.0.1, 10.0.0.2, "
                                                  "10.0.0.3")
        set_policy(name="pol4", scope="s")

        # One policy with matching client, one without any clients
        P = PolicyClass()
        p = P.get_policies(client="10.0.0.1")
        self.assertTrue(_check_policy_name("pol3", p), p)
        self.assertTrue(_check_policy_name("pol4", p), p)
        self.assertTrue(len(p) == 2, p)

        # client matches pol4 and pol2
        p = P.get_policies(client="192.168.2.3")
        self.assertTrue(_check_policy_name("pol2", p), p)
        self.assertTrue(_check_policy_name("pol4", p), p)
        self.assertTrue(len(p) == 2, p)

        # client only matches pol4, since it is excluded in pol2
        p = P.get_policies(client="192.168.1.1")
        self.assertTrue(_check_policy_name("pol4", p), p)
        self.assertTrue(len(p) == 1, p)

    def test_08_user_policies(self):
        set_policy(name="pol1", scope="s", user="*")
        set_policy(name="pol2", scope="s", user="admin, root, user1")
        set_policy(name="pol3", scope="s", user="*, !user1")
        set_policy(name="pol4", scope="s", user="*, -root")

        # get policies for user1
        P = PolicyClass()
        p = P.get_policies(user="user1")
        self.assertTrue(len(p) == 3, (len(p), p))
        self.assertTrue(_check_policy_name("pol1", p), p)
        self.assertTrue(_check_policy_name("pol2", p), p)
        self.assertFalse(_check_policy_name("pol3", p), p)
        self.assertTrue(_check_policy_name("pol4", p), p)
        # get policies for root
        p = P.get_policies(user="root")
        self.assertTrue(len(p) == 3, p)
        self.assertTrue(_check_policy_name("pol1", p), p)
        self.assertTrue(_check_policy_name("pol2", p), p)
        self.assertTrue(_check_policy_name("pol3", p), p)
        self.assertFalse(_check_policy_name("pol4", p), p)
        # get policies for admin
        p = P.get_policies(user="admin")
        self.assertTrue(len(p) == 4, p)
        self.assertTrue(_check_policy_name("pol1", p), p)
        self.assertTrue(_check_policy_name("pol2", p), p)
        self.assertTrue(_check_policy_name("pol3", p), p)
        self.assertTrue(_check_policy_name("pol4", p), p)

    def test_09_realm_resolver_policy(self):
        set_policy(name="pol1", scope="s", realm="r1")
        set_policy(name="pol2", scope="s", realm="r1", resolver="reso1")
        set_policy(name="pol3", scope="s", realm="", resolver="reso2")
        set_policy(name="pol4", scope="s", realm="r2", active=True)

        P = PolicyClass()
        p = P.get_policies(realm="r1")
        self.assertTrue(len(p) == 3, p)
        self.assertTrue(_check_policy_name("pol1", p), p)
        self.assertTrue(_check_policy_name("pol2", p), p)
        self.assertTrue(_check_policy_name("pol3", p), p)
        self.assertFalse(_check_policy_name("pol4", p), p)

        p = P.get_policies(realm="r2")
        self.assertTrue(len(p) == 2, p)
        self.assertFalse(_check_policy_name("pol1", p), p)
        self.assertFalse(_check_policy_name("pol2", p), p)
        self.assertTrue(_check_policy_name("pol3", p), p)
        self.assertTrue(_check_policy_name("pol4", p), p)

        p = P.get_policies(resolver="reso1")
        self.assertEqual(len(p), 3)
        self.assertTrue(_check_policy_name("pol1", p), p)
        self.assertTrue(_check_policy_name("pol2", p), p)
        self.assertFalse(_check_policy_name("pol3", p), p)
        self.assertTrue(_check_policy_name("pol4", p), p)

        p = P.get_policies(resolver="reso2")
        self.assertTrue(len(p) == 3, p)
        self.assertTrue(_check_policy_name("pol1", p), p)
        self.assertFalse(_check_policy_name("pol2", p), p)
        self.assertTrue(_check_policy_name("pol3", p), p)
        self.assertTrue(_check_policy_name("pol4", p), p)

    def test_10_action_policies(self):
        set_policy(name="pol1", action="enroll, init, disable")
        set_policy(name="pol2", action="enroll, otppin=1")
        set_policy(name="pol3", action="*, -disable")
        set_policy(name="pol4", action="*, -otppin=2")

        P = PolicyClass()
        p = P.get_policies(action="enroll")
        self.assertTrue(len(p) == 4, (len(p), p))

        p = P.get_policies(action="init")
        self.assertTrue(len(p) == 3, (len(p), p))

        p = P.get_policies(action="disable")
        self.assertTrue(len(p) == 2, (len(p), p))

        p = P.get_policies(action="otppin")
        self.assertTrue(len(p) == 2, (len(p), p))

    def test_11_get_policy_definitions(self):
        p = get_static_policy_definitions()
        self.assertTrue("admin" in p, p)

        p = get_static_policy_definitions(scope="admin")
        self.assertTrue("enable" in p, p)

    def test_12_get_allowed_tokentypes(self):
        set_policy(name="tt1", scope=SCOPE.AUTHZ, action="tokentype=hotp "
                                                         "totp, enroll")
        set_policy(name="tt2", scope=SCOPE.AUTHZ, action="tokentype=motp")

        P = PolicyClass()
        ttypes = P.get_action_values("tokentype", scope=SCOPE.AUTHZ)
        self.assertTrue("motp" in ttypes)
        self.assertTrue("totp" in ttypes)
        self.assertTrue("hotp" in ttypes)
        self.assertFalse("spass" in ttypes)

    def test_13_get_allowed_serials(self):
        set_policy(name="st1", scope=SCOPE.AUTHZ, action="serial=OATH")
        set_policy(name="st2", scope=SCOPE.AUTHZ, action="serial=mOTP ")

        P = PolicyClass()
        ttypes = P.get_action_values("serial", scope=SCOPE.AUTHZ)
        self.assertTrue("OATH" in ttypes)
        self.assertTrue("mOTP" in ttypes)
        self.assertFalse("TOTP" in ttypes)

    def test_14_fail_unique_policies(self):
        # create policies with two different texts
        set_policy(name="email1", scope=SCOPE.AUTH, action="emailtext=text 1")
        set_policy(name="email2", scope=SCOPE.AUTH, action="emailtext=text 2")

        # As there are two policies with different action values,
        # a PolicyError is raised.
        P = PolicyClass()
        self.assertRaises(PolicyError, P.get_action_values,
                          action="emailtext", scope=SCOPE.AUTH,
                          unique=True,
                          allow_white_space_in_action=True)

    def test_15_ui_tokentypes(self):
        P = PolicyClass()
        logged_in_user = {"username": "admin",
                          "role": "admin",
                          "realm": "realm1"}
        # Without policies, the admin gets all
        tt = P.ui_get_enroll_tokentypes("127.0.0.1", logged_in_user)
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
        P = PolicyClass()

        tt = P.ui_get_enroll_tokentypes("127.0.0.1", logged_in_user)
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
        P = PolicyClass()
        tt = P.ui_get_enroll_tokentypes("127.0.0.1", {"username": "kurt",
                                                      "realm": "realm",
                                                      "role": "user"})
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
        P = PolicyClass()
        # realm is empty, since in case of an admin, this is the admin realm
        rights = P.ui_get_enroll_tokentypes(None, {"role": SCOPE.ADMIN,
                                                   "realm": None,
                                                   "username": "adminA"})
        self.assertTrue("hotp" in rights)
        self.assertTrue("totp" in rights)
        rights = P.ui_get_enroll_tokentypes(None, {"role": SCOPE.ADMIN,
                                                   "realm": "",
                                                   "username": "adminB"})
        self.assertTrue("totp" not in rights)
        self.assertTrue("hotp" in rights)
        rights = P.ui_get_enroll_tokentypes(None, {"role": SCOPE.ADMIN,
                                                   "realm": "",
                                                   "username": "adminC"})
        self.assertEqual(rights, {})
        delete_policy("polAdminA")
        delete_policy("polAdminB")

    def test_16_admin_realm(self):
        P = PolicyClass()
        logged_in_user = {"username": "admin",
                          "role": "admin",
                          "realm": "realm1"}
        # Without policies, the admin gets all
        tt = P.ui_get_enroll_tokentypes("127.0.0.1", logged_in_user)
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
        P = PolicyClass()

        tt = P.ui_get_enroll_tokentypes("127.0.0.1", logged_in_user)
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
        logged_in_user = {"username": "admin",
                          "role": "admin",
                          "realm": "OtherRealm"}
        tt = P.ui_get_enroll_tokentypes("127.0.0.1", logged_in_user)
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

    def test_17_ui_get_rights(self):
        P = PolicyClass()
        # Without policies, the admin gets all
        rights = P.ui_get_rights(SCOPE.ADMIN, "realm1", "admin")
        self.assertTrue(len(rights) >= 60)

        # An admin may only enroll Yubikeys
        set_policy(name="tokenEnroll", scope=SCOPE.ADMIN,
                   action="enrollYUBIKEY")
        P = PolicyClass()
        rights = P.ui_get_rights(SCOPE.ADMIN, "realm1", "admin")
        self.assertEqual(rights, ["enrollYUBIKEY"])

        # A user may do something else...
        set_policy(name="userpol", scope=SCOPE.USER, action="enable")
        P = PolicyClass()
        rights = P.ui_get_rights(SCOPE.USER, "realm2", "user")
        # there was still another policy...
        self.assertEqual(rights, ["enable", "disable"])

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
        P = PolicyClass()
        # realm is empty, since in case of an admin, this is the admin realm
        rights = P.ui_get_rights(SCOPE.ADMIN, realm=None, username="adminA")
        self.assertTrue("enrollTOTP" in rights)
        self.assertTrue("enrollHOTP" in rights)
        rights = P.ui_get_rights(SCOPE.ADMIN, realm=None, username="adminB")
        self.assertTrue("enrollTOTP" not in rights)
        self.assertTrue("enrollHOTP" in rights)
        rights = P.ui_get_rights(SCOPE.ADMIN, realm=None, username="adminC")
        self.assertEqual(rights, [])
        delete_policy("polAdminA")
        delete_policy("polAdminB")

    def test_18_policy_with_time(self):
        set_policy(name="time1", scope=SCOPE.AUTHZ,
                   action="tokentype=hotp totp, enroll",
                   time="Mon-Wed: 0-23:59")
        tn = datetime.datetime.now()
        dow = tn.isoweekday()
        P = PolicyClass()
        policies = P.get_policies(name="time1",
                                  scope=SCOPE.AUTHZ,
                                  all_times=True)
        self.assertEqual(len(policies), 1)

        policies = P.get_policies(name="time1",
                                  scope=SCOPE.AUTHZ)
        if dow in [1, 2, 3]:
            self.assertEqual(len(policies), 1)
        else:
            self.assertEqual(len(policies), 0)
        delete_policy("time1")

    def test_19_ui_get_menus(self):
        delete_all_policies()
        luser = {"username": "admin", "role": "admin"}

        # Without policies, the admin gets all
        P = PolicyClass()
        menus = P.ui_get_main_menus(luser)
        self.assertTrue(MAIN_MENU.USERS in menus)
        self.assertTrue(MAIN_MENU.TOKENS in menus)
        self.assertTrue(MAIN_MENU.COMPONENTS in menus)
        self.assertTrue(MAIN_MENU.CONFIG in menus)
        self.assertTrue(MAIN_MENU.MACHINES in menus)

        # Admin has only right to enroll HOTP! :-)
        set_policy("pol1", scope=SCOPE.ADMIN, user="admin",
                   action="enrollHOTP")
        P = PolicyClass()
        menus = P.ui_get_main_menus(luser)
        # Thus he can only see the token menu
        self.assertTrue(MAIN_MENU.USERS not in menus)
        self.assertTrue(MAIN_MENU.TOKENS in menus)
        self.assertTrue(MAIN_MENU.COMPONENTS not in menus)
        self.assertTrue(MAIN_MENU.CONFIG not in menus)
        self.assertTrue(MAIN_MENU.MACHINES not in menus)

        set_policy("pol2", scope=SCOPE.ADMIN, user="admin",
                   action=ACTION.USERLIST)
        P = PolicyClass()
        menus = P.ui_get_main_menus(luser)
        # Thus he can only see the token menu
        self.assertTrue(MAIN_MENU.USERS in menus)
        self.assertTrue(MAIN_MENU.TOKENS in menus)
        self.assertTrue(MAIN_MENU.COMPONENTS not in menus)
        self.assertTrue(MAIN_MENU.CONFIG not in menus)
        self.assertTrue(MAIN_MENU.MACHINES not in menus)

        set_policy("pol3", scope=SCOPE.ADMIN, user="admin",
                   action=ACTION.MACHINELIST)
        P = PolicyClass()
        menus = P.ui_get_main_menus(luser)
        # Thus he can only see the token menu
        self.assertTrue(MAIN_MENU.USERS in menus)
        self.assertTrue(MAIN_MENU.TOKENS in menus)
        self.assertTrue(MAIN_MENU.COMPONENTS not in menus)
        self.assertTrue(MAIN_MENU.CONFIG not in menus)
        self.assertTrue(MAIN_MENU.MACHINES in menus)

        set_policy("pol4", scope=SCOPE.ADMIN, user="admin",
                   action=ACTION.SYSTEMDELETE)
        P = PolicyClass()
        menus = P.ui_get_main_menus(luser)
        # Thus he can only see the token menu
        self.assertTrue(MAIN_MENU.USERS in menus)
        self.assertTrue(MAIN_MENU.TOKENS in menus)
        self.assertTrue(MAIN_MENU.COMPONENTS not in menus)
        self.assertTrue(MAIN_MENU.CONFIG in menus)
        self.assertTrue(MAIN_MENU.MACHINES in menus)

        delete_all_policies()

    def test_20_search_values(self):
        P = PolicyClass()
        found, excluded = P._search_value(["v1", "v2"], "v1")
        self.assertTrue(found)

        found, excluded = P._search_value(["v1", "v2"], "v3")
        self.assertFalse(found)

        found, excluded = P._search_value(["v1", "*"], "v3")
        self.assertTrue(found)

        found, excluded = P._search_value(["v1", "-v2"], "v2")
        self.assertTrue(excluded)

        found, excluded = P._search_value(["v1", "v.*"], "v3")
        self.assertTrue(found)
        self.assertFalse(excluded)

        found, excluded = P._search_value(["v1", "r.*"], "v13")
        self.assertFalse(found)
        self.assertFalse(excluded)

    def test_21_check_all_resolver(self):
        # check_all_resolver allows to find a policy for a secondary user
        # resolver.
        # We create one realm "realm1" with the resolvers
        # reso1 (prio 1)
        # reso2 (prio 2)
        # reso3 (prio 3)
        # A user user@realm1 will be identified as user.reso1@realm1.
        # But we will also match policies for reso2.

        # no realm and resolver
        r = get_realms()
        self.assertEqual(r, {})

        r = get_resolver_list()
        self.assertEqual(r, {})

        # create user realm
        for reso in ["reso1", "resoX", "resoA"]:
            rid = save_resolver({"resolver": reso,
                                 "type": "passwdresolver",
                                 "fileName": PWFILE})
            self.assertTrue(rid > 0, rid)

        # create a realm with reso1 being the resolver with the highest priority
        (added, failed) = set_realm("realm1",
                                    ["reso1", "resoX", "resoA"],
                                    priority={"reso1": 1,
                                              "resoX": 2,
                                              "resoA": 3})
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 3)

        user = User(login="cornelius",
                    realm="realm1")
        # The user, that is created, is cornelius.reso1@realm1
        user_str = "{0!s}".format(user)
        self.assertEqual(user_str, "<cornelius.reso1@realm1>")
        # But the user "cornelius" is also contained in other resolves in
        # this realm
        r = user.get_ordererd_resolvers()
        self.assertEqual(r, ["reso1", "resoX", "resoA"])
        self.assertFalse(user.is_empty())
        self.assertTrue(User().is_empty())

        # define a policy with the wrong resolver
        p = set_policy(name="checkAll", scope=SCOPE.AUTHZ, realm="realm1",
                       resolver="resoX",
                       action="{0}=totp".format(ACTION.TOKENTYPE))
        self.assertTrue(p > 0)
        p = set_policy(name="catchAll", scope=SCOPE.AUTHZ, realm="realm1",
                       action="{0}=totp".format(ACTION.TOKENTYPE))
        self.assertTrue(p > 0)
        P = PolicyClass()
        pols = P.get_policies(scope=SCOPE.AUTHZ, realm=user.realm,
                              resolver=user.resolver, user=user.login)
        self.assertEqual(len(pols), 1)

        # Now we change the policy, so that it uses check_all_resolver, i.e.
        p = set_policy(name="checkAll", scope=SCOPE.AUTHZ, realm="realm1",
                       resolver="resoX", check_all_resolvers=True,
                       action="{0}=totp".format(ACTION.TOKENTYPE))
        self.assertTrue(p > 0)
        P = PolicyClass()
        pols = P.get_policies(scope=SCOPE.AUTHZ, realm=user.realm,
                              resolver=user.resolver, user=user.login)
        self.assertEqual(len(pols), 2)

        # delete policy
        delete_policy("checkAll")
        delete_policy("catchAll")
        # delete resolvers and realm
        delete_realm("realm1")
        for reso in ["reso1", "resoX", "resoA"]:
            rid = delete_resolver(reso)
            self.assertTrue(rid > 0, rid)

    def test_22_non_ascii_user(self):
        set_policy(name="polnonascii",
                   action="enroll, otppin=1",
                   user=u'nönäscii',
                   scope='s')

        P = PolicyClass()
        p = P.get_policies(action="enroll", user='somebodyelse')
        self.assertEqual(len(p), 0)

        p = P.get_policies(action="enroll", user=u'nönäscii')
        self.assertEqual(len(p), 1)
