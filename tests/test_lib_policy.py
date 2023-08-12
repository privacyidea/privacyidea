# coding: utf-8
"""
This test file tests the lib.policy.py

The lib.policy.py only depends on the database model.
"""
import dateutil
import mock

from .base import MyTestCase, FakeFlaskG, FakeAudit

from privacyidea.lib.auth import ROLE
from privacyidea.lib.policy import (set_policy, delete_policy,
                                    import_policies, export_policies,
                                    get_static_policy_definitions,
                                    PolicyClass, SCOPE, enable_policy,
                                    PolicyError, ACTION, MAIN_MENU,
                                    delete_all_policies,
                                    get_action_values_from_options, Match, MatchingError,
                                    get_allowed_custom_attributes)
from privacyidea.lib.realm import (set_realm, delete_realm, get_realms)
from privacyidea.lib.resolver import (save_resolver, get_resolver_list,
                                      delete_resolver)
from privacyidea.lib.error import ParameterError
from privacyidea.lib.user import User
from .base import PWFILE as FILE_PASSWORDS
from .base import PWFILE2 as FILE_PASSWD



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
        policies = P.match_policies(name="pol3")
        # only one policy found
        self.assertTrue(len(policies) == 1, len(policies))

        policies = P.match_policies(scope=SCOPE.AUTHZ)
        self.assertTrue(len(policies) == 2, len(policies))

        policies = P.match_policies(scope=SCOPE.AUTHZ,
                                    action="tokentype")
        self.assertTrue(len(policies) == 1, len(policies))

        policies = P.match_policies(scope="admin",
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
                       adminuser=["admin", "superroot"])
        self.assertTrue(p > 0)

        # enable and disable policies
        policies = PolicyClass().match_policies(active=False)
        num_old = len(policies)
        p = enable_policy("pol4", False)
        policies = PolicyClass().match_policies(active=False)
        self.assertTrue(num_old + 1 == len(policies), (num_old, len(policies)))
        p = enable_policy("pol4", True)
        policies = PolicyClass().match_policies(active=False)
        self.assertTrue(num_old == len(policies), len(policies))

        # find inactive policies
        P = PolicyClass()
        policies = P.match_policies(active=False)
        self.assertTrue(len(policies) == 1, len(policies))
        self.assertTrue(policies[0].get("name") == "pol1")

        # find policies action tokentype
        policies = P.match_policies(action="tokentype")
        self.assertTrue(len(policies) == 2, policies)
        # find policies action serial
        policies = P.match_policies(action="serial")
        self.assertTrue(len(policies) == 1, policies)
        # find policies with scope authorization
        policies = P.match_policies(scope=SCOPE.AUTHZ)
        self.assertTrue(len(policies) == 3, policies)
        # find policies authorization and realm2
        policies = P.match_policies(action="tokentype", scope=SCOPE.AUTHZ)
        self.assertTrue(len(policies) == 2, policies)
        # find policies with user admin
        policies = P.match_policies(scope="admin", adminuser="admin")
        self.assertTrue(len(policies) == 1, "{0!s}".format(len(policies)))
        # find policies with resolver2 and authorization. THe result should
        # be pol2 and pol2a
        policies = P.match_policies(resolver="resolver2", scope=SCOPE.AUTHZ)
        self.assertTrue(len(policies) == 2, policies)

        # find policies with realm1 and authorization. We also include the
        # "*" into the result list. We find pol2 and pol3
        policies = P.match_policies(realm="realm1", scope=SCOPE.AUTHZ)
        self.assertTrue(len(policies) == 2, policies)

        # find policies with resolver1 and authorization.
        # All other authorization policies will also match, since they either
        # user * or
        # have no destinct information about resolvers
        policies = P.match_policies(resolver="resolver1", scope=SCOPE.AUTHZ)
        self.assertTrue(len(policies) == 3, policies)

    def test_04_delete_policy(self):
        delete_policy(name="pol4")
        P = PolicyClass()
        pol4 = P.match_policies(name="pol4")
        self.assertTrue(pol4 == [], pol4)

    def test_05_export_policies(self):
        P = PolicyClass()
        policies = P.match_policies()
        file = export_policies(policies)
        self.assertTrue("[pol1]" in file, file)
        self.assertTrue("[pol2]" in file, file)
        self.assertTrue("[pol3]" in file, file)

    def test_06_import_policies(self):
        P = PolicyClass()
        file = export_policies(P.match_policies())
        delete_policy("pol1")
        delete_policy("pol2")
        delete_policy("pol3")
        P = PolicyClass()
        policies = P.match_policies()
        self.assertFalse(_check_policy_name("pol1", policies), policies)
        self.assertFalse(_check_policy_name("pol2", policies), policies)
        self.assertFalse(_check_policy_name("pol3", policies), policies)
        # Now import the policies again
        num = import_policies(file)
        self.assertTrue(num == 4, num)
        P = PolicyClass()
        policies = P.match_policies()
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
        p = P.match_policies(client="10.0.0.1")
        self.assertTrue(_check_policy_name("pol3", p), p)
        self.assertTrue(_check_policy_name("pol4", p), p)
        self.assertTrue(len(p) == 2, p)

        # client matches pol4 and pol2
        p = P.match_policies(client="192.168.2.3")
        self.assertTrue(_check_policy_name("pol2", p), p)
        self.assertTrue(_check_policy_name("pol4", p), p)
        self.assertTrue(len(p) == 2, p)

        # client only matches pol4, since it is excluded in pol2
        p = P.match_policies(client="192.168.1.1")
        self.assertTrue(_check_policy_name("pol4", p), p)
        self.assertTrue(len(p) == 1, p)

        # client="" throws a ParameterError
        with self.assertRaises(ParameterError):
            P.match_policies(client="")

    def test_08_user_policies(self):
        set_policy(name="pol1", scope="s", user="*")
        set_policy(name="pol2", scope="s", user="admin, root, user1")
        set_policy(name="pol3", scope="s", user="*, !user1")
        set_policy(name="pol4", scope="s", user="*, -root")

        # get policies for user1
        P = PolicyClass()
        p = P.match_policies(user="user1")
        self.assertTrue(len(p) == 3, (len(p), p))
        self.assertTrue(_check_policy_name("pol1", p), p)
        self.assertTrue(_check_policy_name("pol2", p), p)
        self.assertFalse(_check_policy_name("pol3", p), p)
        self.assertTrue(_check_policy_name("pol4", p), p)
        # get policies for root
        p = P.match_policies(user="root")
        self.assertTrue(len(p) == 3, p)
        self.assertTrue(_check_policy_name("pol1", p), p)
        self.assertTrue(_check_policy_name("pol2", p), p)
        self.assertTrue(_check_policy_name("pol3", p), p)
        self.assertFalse(_check_policy_name("pol4", p), p)
        # get policies for admin
        p = P.match_policies(user="admin")
        self.assertTrue(len(p) == 4, p)
        self.assertTrue(_check_policy_name("pol1", p), p)
        self.assertTrue(_check_policy_name("pol2", p), p)
        self.assertTrue(_check_policy_name("pol3", p), p)
        self.assertTrue(_check_policy_name("pol4", p), p)
        # get policies for empty user
        p = P.match_policies(user="")
        self.assertEqual(len(p), 3)
        self.assertTrue(_check_policy_name("pol1", p), p)
        self.assertTrue(_check_policy_name("pol3", p), p)
        self.assertTrue(_check_policy_name("pol4", p), p)

    def test_08a_adminuser_policies(self):
        set_policy(name="pol1", scope="admin", adminuser="*", user="")
        set_policy(name="pol2", scope="admin", adminuser="admin, root, user1", user="*")
        set_policy(name="pol3", scope="admin", adminuser="*, !user1", user="")
        set_policy(name="pol4", scope="admin", adminuser="*, -root", user="")

        # get policies for user1
        P = PolicyClass()
        p = P.match_policies(scope=SCOPE.ADMIN, adminuser="user1")
        self.assertTrue(len(p) == 3, (len(p), p))
        self.assertTrue(_check_policy_name("pol1", p), p)
        self.assertTrue(_check_policy_name("pol2", p), p)
        self.assertFalse(_check_policy_name("pol3", p), p)
        self.assertTrue(_check_policy_name("pol4", p), p)
        # get policies for root
        p = P.match_policies(scope=SCOPE.ADMIN, adminuser="root")
        self.assertTrue(len(p) == 3, p)
        self.assertTrue(_check_policy_name("pol1", p), p)
        self.assertTrue(_check_policy_name("pol2", p), p)
        self.assertTrue(_check_policy_name("pol3", p), p)
        self.assertFalse(_check_policy_name("pol4", p), p)
        # get policies for admin
        p = P.match_policies(scope=SCOPE.ADMIN, adminuser="admin")
        self.assertTrue(len(p) == 4, p)
        self.assertTrue(_check_policy_name("pol1", p), p)
        self.assertTrue(_check_policy_name("pol2", p), p)
        self.assertTrue(_check_policy_name("pol3", p), p)
        self.assertTrue(_check_policy_name("pol4", p), p)
        # get policies for empty user
        p = P.match_policies(scope=SCOPE.ADMIN, adminuser="")
        self.assertEqual(len(p), 3)
        self.assertTrue(_check_policy_name("pol1", p), p)
        self.assertTrue(_check_policy_name("pol3", p), p)
        self.assertTrue(_check_policy_name("pol4", p), p)

    def test_09_realm_resolver_policy(self):
        set_policy(name="pol1", scope="s", realm="r1")
        set_policy(name="pol2", scope="s", realm="r1", resolver="reso1")
        set_policy(name="pol3", scope="s", realm="", resolver="reso2")
        set_policy(name="pol4", scope="s", realm="r2", active=True)

        P = PolicyClass()
        p = P.match_policies(realm="r1")
        self.assertTrue(len(p) == 3, p)
        self.assertTrue(_check_policy_name("pol1", p), p)
        self.assertTrue(_check_policy_name("pol2", p), p)
        self.assertTrue(_check_policy_name("pol3", p), p)
        self.assertFalse(_check_policy_name("pol4", p), p)

        p = P.match_policies(realm="r2")
        self.assertTrue(len(p) == 2, p)
        self.assertFalse(_check_policy_name("pol1", p), p)
        self.assertFalse(_check_policy_name("pol2", p), p)
        self.assertTrue(_check_policy_name("pol3", p), p)
        self.assertTrue(_check_policy_name("pol4", p), p)

        # Check cases in which we pass an empty realm or realm=None
        p = P.match_policies(realm="")
        self.assertEqual(len(p), 1)
        self.assertTrue(_check_policy_name("pol3", p), p)

        p = P.match_policies(realm=None)
        self.assertEqual(len(p), 4)

        p = P.match_policies(resolver="reso1")
        self.assertEqual(len(p), 3)
        self.assertTrue(_check_policy_name("pol1", p), p)
        self.assertTrue(_check_policy_name("pol2", p), p)
        self.assertFalse(_check_policy_name("pol3", p), p)
        self.assertTrue(_check_policy_name("pol4", p), p)

        p = P.match_policies(resolver="reso2")
        self.assertTrue(len(p) == 3, p)
        self.assertTrue(_check_policy_name("pol1", p), p)
        self.assertFalse(_check_policy_name("pol2", p), p)
        self.assertTrue(_check_policy_name("pol3", p), p)
        self.assertTrue(_check_policy_name("pol4", p), p)

        # Check case in which we pass an empty resolver
        p = P.match_policies(resolver="")
        self.assertEqual(len(p), 2)
        self.assertTrue(_check_policy_name("pol1", p), p)
        self.assertTrue(_check_policy_name("pol4", p), p)

    def test_10_action_policies(self):
        set_policy(name="pol1", action="enroll, init, disable")
        set_policy(name="pol2", action="enroll, otppin=1")
        set_policy(name="pol3", action="*, -disable")
        set_policy(name="pol4", action="*, -otppin=2")

        P = PolicyClass()
        p = P.match_policies(action="enroll")
        self.assertTrue(len(p) == 4, (len(p), p))

        p = P.match_policies(action="init")
        self.assertTrue(len(p) == 3, (len(p), p))

        p = P.match_policies(action="disable")
        self.assertTrue(len(p) == 2, (len(p), p))

        p = P.match_policies(action="otppin")
        self.assertTrue(len(p) == 2, (len(p), p))

        # Check cases in which we pass an empty action or action=None
        p = P.match_policies(action="")
        # Here, we get pol3 and pol4
        self.assertEqual(len(p), 2)
        self.assertTrue(_check_policy_name("pol3", p), p)
        self.assertTrue(_check_policy_name("pol4", p), p)

        p = P.match_policies(action=None)
        self.assertEqual(len(p), 4)

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

        type_policies = P.get_action_values("tokentype", scope=SCOPE.AUTHZ)
        self.assertTrue("motp" in type_policies.keys())
        self.assertTrue("totp" in type_policies.keys())
        self.assertTrue("hotp" in type_policies.keys())
        self.assertFalse("spass" in type_policies.keys())

        # motp is defined in policy "tt2"
        self.assertEqual(type_policies.get("motp"), ["tt2"])
        # totp and hotp is defined in policy "tt1"
        self.assertEqual(type_policies.get("hotp"), ["tt1"])
        self.assertEqual(type_policies.get("totp"), ["tt1"])

    def test_13_get_allowed_serials(self):
        set_policy(name="st1", scope=SCOPE.AUTHZ, action="serial=OATH")
        set_policy(name="st2", scope=SCOPE.AUTHZ, action="serial=mOTP ")

        P = PolicyClass()
        ttypes = P.get_action_values("serial", scope=SCOPE.AUTHZ)
        self.assertTrue("OATH" in ttypes)
        self.assertTrue("mOTP" in ttypes)
        self.assertFalse("TOTP" in ttypes)

        serial_policies = P.get_action_values("serial", scope=SCOPE.AUTHZ)
        self.assertEqual(serial_policies.get("OATH"), ["st1"])
        self.assertEqual(serial_policies.get("mOTP"), ["st2"])

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

        set_policy(name="polAdminA", scope=SCOPE.ADMIN, adminuser="adminA",
                   action="enrollHOTP, enrollTOTP")
        set_policy(name="polAdminB", scope=SCOPE.ADMIN, adminuser="adminB",
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

        set_policy(name="tokenEnroll", scope=SCOPE.ADMIN,
                   adminrealm=["realm2"],
                   action="enrollYUBIKEY")
        # Update policy: An admin in realm1 may only enroll Yubikeys
        set_policy(name="tokenEnroll", scope=SCOPE.ADMIN,
                   adminrealm=["realm1"],
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
        # Check invalid scope
        with self.assertRaises(PolicyError):
            P.ui_get_rights(SCOPE.ENROLL, "realm1", "admin")

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
        self.assertEqual(set(rights), {"enable", "disable"})

        delete_policy("tokenEnroll")
        delete_policy("userpol")
        # Two admins:
        # adminA is allowed to enroll tokens in all realms
        # adminB is allowed to enroll tokens only in realmB
        set_policy(name="polAdminA", scope=SCOPE.ADMIN, adminuser="adminA",
                   action="enrollHOTP, enrollTOTP")
        set_policy(name="polAdminB", scope=SCOPE.ADMIN, adminuser="adminB",
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

    def test_17b_ui_rights_users_in_different_resolvers(self):
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
        P = PolicyClass()

        # The two users are in different resolvers and get different rights
        rights = P.ui_get_rights(SCOPE.USER, "realm4", "postfix")
        self.assertEqual(set(rights), {"enable", "disable"})

        rights = P.ui_get_rights(SCOPE.USER, "realm4", "usernotoken")
        self.assertEqual(set(rights), {"disable", "remove"})

        delete_policy("userpol41")
        delete_policy("userpol42")
        delete_realm("realm4")
        delete_resolver("passwords")
        delete_resolver("passwd")

    def test_18_policy_match_policies_with_time(self):
        set_policy(name="time1", scope=SCOPE.AUTHZ,
                   action="tokentype=hotp totp, enroll",
                   time="Mon-Wed: 0-23:59")

        wednesday = dateutil.parser.parse("Jul 03 2019 13:00")
        thursday = dateutil.parser.parse("Jul 04 2019 14:34")

        # Simulate a Wednesday
        with mock.patch('privacyidea.lib.utils.datetime') as mock_dt:
            mock_dt.now.return_value = wednesday

            P = PolicyClass()
            # Regardless of the weekday, ``list_policies`` returns the policy
            policies = P.list_policies(name="time1", scope=SCOPE.AUTHZ)
            self.assertEqual(len(policies), 1)
            self.assertEqual(policies[0]["name"], "time1")
            # And ``match_policies`` returns it on Wednesdays
            policies = P.match_policies(name="time1", scope=SCOPE.AUTHZ)
            self.assertEqual(len(policies), 1)
            self.assertEqual(policies[0]["name"], "time1")

        # Simulate a Thursday
        with mock.patch('privacyidea.lib.utils.datetime') as mock_dt:
            mock_dt.now.return_value = thursday

            P = PolicyClass()
            # Regardless of the weekday, ``list_policies`` returns the policy
            policies = P.list_policies(name="time1", scope=SCOPE.AUTHZ)
            self.assertEqual(len(policies), 1)
            self.assertEqual(policies[0]["name"], "time1")
            # But ``match_policies`` does not return it on Thursdays!
            policies = P.match_policies(name="time1", scope=SCOPE.AUTHZ)
            self.assertEqual(len(policies), 0)

        # Directly specify a time
        # Match on Wednesday
        policies = P.match_policies(name="time1", scope=SCOPE.AUTHZ, time=wednesday)
        self.assertEqual(len(policies), 1)
        self.assertEqual(policies[0]["name"], "time1")

        # No match on Thursday
        policies = P.match_policies(name="time1", scope=SCOPE.AUTHZ, time=thursday)
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
        set_policy("pol1", scope=SCOPE.ADMIN, adminuser="admin",
                   action="enrollHOTP")
        P = PolicyClass()
        menus = P.ui_get_main_menus(luser)
        # Thus he can only see the token menu
        self.assertTrue(MAIN_MENU.USERS not in menus)
        self.assertTrue(MAIN_MENU.TOKENS in menus)
        self.assertTrue(MAIN_MENU.COMPONENTS not in menus)
        self.assertTrue(MAIN_MENU.CONFIG not in menus)
        self.assertTrue(MAIN_MENU.MACHINES not in menus)

        set_policy("pol2", scope=SCOPE.ADMIN, adminuser="admin",
                   action=ACTION.USERLIST)
        P = PolicyClass()
        menus = P.ui_get_main_menus(luser)
        # Thus he can only see the token menu
        self.assertTrue(MAIN_MENU.USERS in menus)
        self.assertTrue(MAIN_MENU.TOKENS in menus)
        self.assertTrue(MAIN_MENU.COMPONENTS not in menus)
        self.assertTrue(MAIN_MENU.CONFIG not in menus)
        self.assertTrue(MAIN_MENU.MACHINES not in menus)

        set_policy("pol3", scope=SCOPE.ADMIN, adminuser="admin",
                   action=ACTION.MACHINELIST)
        P = PolicyClass()
        menus = P.ui_get_main_menus(luser)
        # Thus he can only see the token menu
        self.assertTrue(MAIN_MENU.USERS in menus)
        self.assertTrue(MAIN_MENU.TOKENS in menus)
        self.assertTrue(MAIN_MENU.COMPONENTS not in menus)
        self.assertTrue(MAIN_MENU.CONFIG not in menus)
        self.assertTrue(MAIN_MENU.MACHINES in menus)

        set_policy("pol4", scope=SCOPE.ADMIN, adminuser="admin",
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
                                 "fileName": FILE_PASSWORDS})
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
        pols = P.match_policies(scope=SCOPE.AUTHZ, realm=user.realm,
                                resolver=user.resolver, user=user.login)
        self.assertEqual(len(pols), 1)

        # Now we change the policy, so that it uses check_all_resolver, i.e.
        p = set_policy(name="checkAll", scope=SCOPE.AUTHZ, realm="realm1",
                       resolver="resoX", check_all_resolvers=True,
                       action="{0}=totp".format(ACTION.TOKENTYPE))
        self.assertTrue(p > 0)
        P = PolicyClass()
        pols = P.match_policies(scope=SCOPE.AUTHZ, realm=user.realm,
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
                   user='nönäscii',
                   scope='s')

        P = PolicyClass()
        p = P.match_policies(action="enroll", user='somebodyelse')
        self.assertEqual(len(p), 0)

        p = P.match_policies(action="enroll", user='nönäscii')
        self.assertEqual(len(p), 1)

        delete_policy(name="polnonascii")

    def test_23_priorities(self):
        # create three policies with three different texts and different priorities
        set_policy(name="email1", scope=SCOPE.AUTH, action="emailtext=text 1", priority=4)
        set_policy(name="email2", scope=SCOPE.AUTH, action="emailtext=text 2", priority=1)
        set_policy(name="email3", scope=SCOPE.AUTH, action="emailtext=text 3", priority=77)

        # this chooses email2, because it has the highest priority
        P = PolicyClass()
        self.assertEqual(list(P.get_action_values(action="emailtext", scope=SCOPE.AUTH,
                                                  unique=True, allow_white_space_in_action=True).keys()),
                         ["text 2"])

        delete_policy("email2")

        # with email2 gone, this chooses email1
        self.assertEqual(list(P.get_action_values(action="emailtext", scope=SCOPE.AUTH,
                                                  unique=True, allow_white_space_in_action=True).keys()),
                         ["text 1"])

        # if we now add another policy with priority 77, we get no conflict
        # because email1 is chosen
        set_policy(name="email4", scope=SCOPE.AUTH, action="emailtext=text 4", priority=77)

        self.assertEqual(list(P.get_action_values(action="emailtext", scope=SCOPE.AUTH,
                                                  unique=True, allow_white_space_in_action=True).keys()),
                         ["text 1"])

        # but we get a conflict if we change the priority of email4 to 4
        set_policy(name="email4", scope=SCOPE.AUTH, action="emailtext=text 4", priority=4)

        with self.assertRaises(PolicyError) as cm:
            P.get_action_values(
                action="emailtext", scope=SCOPE.AUTH,
                unique=True, allow_white_space_in_action=True)
        self.assertIn("policies with conflicting actions", str(cm.exception))

        pols = P.match_policies(action="emailtext", scope=SCOPE.AUTH)
        self.assertEqual(len(pols), 3)
        with self.assertRaises(PolicyError) as cm:
            P.check_for_conflicts(pols, "emailtext")

        P.check_for_conflicts([], "emailtext")
        P.check_for_conflicts([pols[0]], "emailtext")

        # we can also change the priority
        set_policy(name="email4", priority=3)

        self.assertEqual(list(P.get_action_values(action="emailtext", scope=SCOPE.AUTH,
                                                  unique=True, allow_white_space_in_action=True).keys()),
                         ["text 4"])

        # now we have
        # email1, priority=4
        # email3, priority=77
        # email4, priority=3

        # export, delete all, re-import
        exported = export_policies(P.match_policies())
        self.assertIn("priority = 4", exported)
        self.assertIn("priority = 77", exported)
        delete_all_policies()
        import_policies(exported)

        pols = P.match_policies(action="emailtext", scope=SCOPE.AUTH)
        self.assertEqual(len(pols), 3)
        # this sorts by priority
        self.assertEqual([p['name'] for p in pols],
                         ['email4', 'email1', 'email3'])

        # priority must be at least 1
        with self.assertRaises(ParameterError):
            set_policy(name="email4", scope=SCOPE.AUTH, priority=0)
        with self.assertRaises(ParameterError):
            set_policy(name="email4", scope=SCOPE.AUTH, priority=-5)

        delete_policy("email1")
        delete_policy("email3")
        delete_policy("email4")

    def test_23_priorities_equal_actions(self):
        # create two policies with the same action values
        set_policy(name="email1", scope=SCOPE.AUTH, action="emailtext='text 1'", priority=1)
        set_policy(name="email2", scope=SCOPE.AUTH, action="emailtext='text 1'", priority=1)

        # this reduces the action values to unique values
        P = PolicyClass()
        self.assertEqual(list(P.get_action_values(scope=SCOPE.AUTH, action="emailtext").keys()),
                         ["text 1"])
        # this is allowed if the policies agree
        self.assertEqual(list(P.get_action_values(scope=SCOPE.AUTH, action="emailtext", unique=True).keys()),
                         ["text 1"])

        set_policy(name="email2", action="emailtext='text 2'")
        with self.assertRaises(PolicyError):
            P.get_action_values(scope=SCOPE.AUTH, action="emailtext", unique=True)

        delete_policy("email1")
        delete_policy("email2")

    def test_24_challenge_text(self):
        g = FakeFlaskG()
        g.client_ip = "10.0.0.1"
        options = {"g": g,
                   "user": User("cornelius", self.realm1)}

        set_policy("chaltext", scope=SCOPE.AUTH, action="{0!s}=Wo du wolle?".format(ACTION.CHALLENGETEXT))
        g.policy_object = PolicyClass()

        val = get_action_values_from_options(SCOPE.AUTH, ACTION.CHALLENGETEXT, options)
        self.assertEqual(val, "Wo du wolle?")

        delete_policy("chaltext")

    def test_25_get_action_values(self):
        # We test action values with different priority and values!
        set_policy("act1", scope=SCOPE.AUTH, action="{0!s}=userstore".format(ACTION.OTPPIN), priority=1)
        set_policy("act2", scope=SCOPE.AUTH, action="{0!s}=userstore".format(ACTION.OTPPIN), priority=1)
        set_policy("act3", scope=SCOPE.AUTH, action="{0!s}=none".format(ACTION.OTPPIN), priority=3)

        # Now we should get the userstore action value. Both policies act1 and act2 have the unique value
        # with prioritoy 1
        P = PolicyClass()
        audit_data = {}
        r = P.get_action_values(action=ACTION.OTPPIN, scope=SCOPE.AUTH, unique=True, audit_data=audit_data)

        self.assertIn('userstore', r, r)
        self.assertEqual({'act1', 'act2'}, set(r['userstore']), r)

        # The audit_data contains act1 and act2
        self.assertTrue("act1" in audit_data.get("policies"))
        self.assertTrue("act2" in audit_data.get("policies"))
        self.assertTrue("act3" not in audit_data.get("policies"))
        delete_policy("act1")
        delete_policy("act2")
        delete_policy("act3")

    def test_26_match_policies_user_object(self):
        # We pass a user object instead of user, resolver and realm
        # Create resolver and realm
        rid = save_resolver({"resolver": "reso1",
                             "type": "passwdresolver",
                             "fileName": FILE_PASSWORDS})
        self.assertGreater(rid, 0)
        rid = save_resolver({"resolver": "reso2",
                             "type": "passwdresolver",
                             "fileName": FILE_PASSWD})
        self.assertGreater(rid, 0)

        (added, failed) = set_realm("realm1", ["reso1"])
        self.assertEqual(len(failed), 0)
        self.assertEqual(len(added), 1)

        (added, failed) = set_realm("realm2", ["reso2"])
        self.assertEqual(len(failed), 0)
        self.assertEqual(len(added), 1)

        cornelius = User(login="cornelius", realm="realm1")
        nonascii = User(login="nönäscii", realm="realm1")
        selfservice = User(login="selfservice", realm="realm1")
        whoopsie = User(login="whoopsie", realm="realm2")
        set_policy("act1", scope=SCOPE.AUTH, action="{0!s}=userstore".format(ACTION.OTPPIN),
                   user="cornelius, nönäscii")
        set_policy("act2", scope=SCOPE.AUTH, action="{0!s}=userstore".format(ACTION.OTPPIN),
                   resolver="reso1")
        set_policy("act3", scope=SCOPE.AUTH, action="{0!s}=none".format(ACTION.OTPPIN),
                   realm="realm1")
        set_policy("act4", scope=SCOPE.AUTH, action="{0!s}=none".format(ACTION.OTPPIN),
                   user="nönäscii", realm="realm1")

        P = PolicyClass()
        self.assertEqual(set(p['name'] for p in P.match_policies(user_object=cornelius)),
                         {"act1", "act2", "act3"})
        r = P.get_action_values(action=ACTION.OTPPIN, scope=SCOPE.AUTH, user_object=cornelius)
        self.assertIn('userstore', r, r)
        self.assertIn('none', r, r)
        self.assertEqual({'act1', 'act2'}, set(r['userstore']), r)
        self.assertEqual(['act3'], r['none'], r)

        self.assertEqual(set(p['name'] for p in P.match_policies(user_object=nonascii)),
                         {"act1", "act2", "act3", "act4"})
        r = P.get_action_values(action=ACTION.OTPPIN, scope=SCOPE.AUTH, user_object=nonascii)
        self.assertIn('userstore', r, r)
        self.assertIn('none', r, r)
        self.assertEqual({'act1', 'act2'}, set(r['userstore']), r)
        self.assertEqual({'act3', 'act4'}, set(r['none']), r)

        self.assertEqual(set(p['name'] for p in P.match_policies(user_object=selfservice)),
                         {"act2", "act3"})
        self.assertEqual(P.get_action_values(action=ACTION.OTPPIN, scope=SCOPE.AUTH,
                                             user_object=selfservice),
                         {"userstore": ["act2"], "none": ["act3"]})

        self.assertEqual(set(p['name'] for p in P.match_policies(user_object=whoopsie)),
                         set())
        self.assertEqual(P.get_action_values(action=ACTION.OTPPIN, scope=SCOPE.AUTH,
                                             user_object=whoopsie),
                         {})

        self.assertEqual(set(p['name'] for p in P.match_policies(user_object=None)),
                         {"act1", "act2", "act3", "act4"})
        r = P.get_action_values(action=ACTION.OTPPIN, scope=SCOPE.AUTH, user_object=None)
        self.assertIn('userstore', r, r)
        self.assertIn('none', r, r)
        self.assertEqual({'act1', 'act2'}, set(r['userstore']), r)
        self.assertEqual({'act3', 'act4'}, set(r['none']), r)

        self.assertEqual(set(p['name'] for p in P.match_policies(user_object=User())),
                         set())
        self.assertEqual(P.get_action_values(action=ACTION.OTPPIN, scope=SCOPE.AUTH,
                                             user_object=User()),
                         {})

        with self.assertRaises(ParameterError):
            P.match_policies(user_object=cornelius, realm="realm3")

        with self.assertRaises(ParameterError):
            P.get_action_values(action=ACTION.OTPPIN, scope=SCOPE.AUTH,
                                user_object=cornelius, user="selfservice")

        set_policy("act5", scope=SCOPE.AUTH, action="{0!s}=none".format(ACTION.OTPPIN))

        P = PolicyClass()
        # If we pass an empty user object, only policies without user match
        self.assertEqual(set(p['name'] for p in P.match_policies(user_object=User())),
                         {"act5"})
        self.assertEqual(P.get_action_values(action=ACTION.OTPPIN, scope=SCOPE.AUTH, user_object=User()),
                         {"none": ["act5"]})
        # If we pass None as the user object, all policies match
        self.assertEqual(set(p['name'] for p in P.match_policies(user_object=None)),
                         {"act1", "act2", "act3", "act4", "act5"})
        r = P.get_action_values(action=ACTION.OTPPIN, scope=SCOPE.AUTH, user_object=None)
        self.assertIn('userstore', r, r)
        self.assertIn('none', r, r)
        self.assertEqual({'act1', 'act2'}, set(r['userstore']), r)
        self.assertEqual({'act3', 'act4', 'act5'}, set(r['none']), r)

        # if we pass user_obj ornelius, we only get 4 policies
        self.assertEqual(set(p['name'] for p in P.match_policies(user_object=cornelius)),
                         {"act1", "act2", "act3", "act5"})
        # Provide a user object and parameters
        self.assertEqual(set(p['name'] for p in P.match_policies(user_object=cornelius,
                                                                 user="cornelius",
                                                                 realm="realm1")),
                         {"act1", "act2", "act3", "act5"})
        # For some reason pass the same user_obj and parameters, but realm in upper case
        self.assertEqual(set(p['name'] for p in P.match_policies(user_object=cornelius,
                                                                 user="cornelius",
                                                                 realm="REALM1")),
                         {"act1", "act2", "act3", "act5"})

        delete_policy("act1")
        delete_policy("act2")
        delete_policy("act3")
        delete_policy("act4")
        delete_policy("act5")
        delete_realm("realm1")
        delete_realm("realm2")

        delete_resolver("reso1")
        delete_resolver("reso2")

    def test_27_reload_policies(self):
        # First, remove all policies
        policy_object = PolicyClass()
        delete_all_policies()
        self.assertEqual(policy_object.match_policies(), [])
        # Now, add a policy and check if the policies have been reloaded
        set_policy("act1", scope=SCOPE.AUTH, action="{0!s}=userstore".format(ACTION.OTPPIN), priority=1)
        self.assertEqual([p["name"] for p in policy_object.match_policies()], ["act1"])
        self.assertEqual(policy_object.match_policies()[0]["priority"], 1)
        # Update the policy and check if the policies have been reloaded
        set_policy("act1", scope=SCOPE.AUTH, action="{0!s}=userstore".format(ACTION.OTPPIN), priority=2)
        self.assertEqual(policy_object.match_policies()[0]["priority"], 2)
        # Add a second policy, check
        set_policy("act2", scope=SCOPE.AUTH, action="{0!s}=none".format(ACTION.OTPPIN), priority=3)
        self.assertEqual([p["name"] for p in policy_object.match_policies()], ["act1", "act2"])
        # Delete a policy, check
        delete_policy("act1")
        self.assertEqual([p["name"] for p in policy_object.match_policies()], ["act2"])
        delete_policy("act2")

    def test_28_conditions(self):
        rid = save_resolver({"resolver": "reso1",
                             "type": "passwdresolver",
                             "fileName": FILE_PASSWORDS})
        self.assertGreater(rid, 0)

        (added, failed) = set_realm("realm1", ["reso1"])
        self.assertEqual(len(failed), 0)
        self.assertEqual(len(added), 1)

        # Set policy with conditions
        set_policy("act1", scope=SCOPE.AUTH, action="{0!s}=userstore".format(ACTION.OTPPIN),
                   conditions=[("userinfo", "type", "equals", "verysecure", True)])

        P = PolicyClass()
        self.assertEqual(P.list_policies()[0]["conditions"],
                         [("userinfo", "type", "equals", "verysecure", True)])

        # Update existing policy with conditions
        set_policy("act1", conditions=[
            ("userinfo", "type", "equals", "notverysecure", True),
            ("request", "user_agent", "equals", "vpn", True)
        ])
        P = PolicyClass()

        self.assertEqual(P.list_policies()[0]["conditions"],
                         [("userinfo", "type", "equals", "notverysecure", True),
                          ("request", "user_agent", "equals", "vpn", True)])

        delete_policy("act1")
        delete_realm("realm1")
        delete_resolver("reso1")

    def test_29_filter_by_conditions(self):
        def _names(policies):
            return set(p['name'] for p in policies)

        set_policy("verysecure", scope=SCOPE.AUTH, action="{0!s}=userstore".format(ACTION.OTPPIN),
                   conditions=[("userinfo", "type", "equals", "verysecure", True)])
        set_policy("notverysecure", scope=SCOPE.AUTH, action="{0!s}=userstore".format(ACTION.OTPPIN),
                   conditions=[("userinfo", "type", "equals", "notverysecure", True),
                               ("userinfo", "groups", "contains", "b", True)])
        P = PolicyClass()

        class MockUser(object):
            login = 'login'
            realm = 'realm'
            resolver = 'resolver'

        empty_user = User()

        user1 = MockUser()
        user1.info = {"type": "verysecure", "groups": ["a", "b", "c"]}

        user2 = MockUser()
        user2.info = {"type": "notverysecure", "groups": ["c"]}

        user3 = MockUser()
        user3.info = {"type": "notverysecure", "groups": ["b", "c"]}

        # no user => policy error
        with self.assertRaisesRegex(PolicyError, ".* an according object is not available.*"):
            P.match_policies(user_object=None)

        # empty user => policy error
        with self.assertRaisesRegex(PolicyError, ".*Unknown key.*"):
            P.match_policies(user_object=empty_user)

        # user1 => verysecure matches
        self.assertEqual(_names(P.match_policies(user_object=user1)),
                         {"verysecure"})
        # user2 => no policy matches
        self.assertEqual(_names(P.match_policies(user_object=user2)),
                         set())
        # user3 => notverysecure matches
        self.assertEqual(_names(P.match_policies(user_object=user3)),
                         {"notverysecure"})

        # an unforeseen error in the comparison function => policy error
        with mock.patch("privacyidea.lib.policy.compare_values") as mock_function:
            mock_function.side_effect = ValueError
            with self.assertRaisesRegex(PolicyError, r".*Invalid comparison.*"):
                P.match_policies(user_object=user1)

        for policy in ["verysecure", "notverysecure"]:
            delete_policy(policy)

        # Policy with initially inactive condition
        set_policy("extremelysecure", scope=SCOPE.AUTH, action="{0!s}=userstore".format(ACTION.OTPPIN),
                   conditions=[("userinfo", "type", "equals", "notverysecure", False)])

        # user1 matches, because the condition on type is inactive
        self.assertEqual(_names(P.match_policies(user_object=user1)),
                         {"extremelysecure"})

        # activate the condition
        set_policy("extremelysecure", conditions=[("userinfo", "type", "equals", "notverysecure", True)])

        # user1 does not match anymore, because the condition on type is active
        self.assertEqual(_names(P.match_policies(user_object=user1)),
                         set())

        delete_policy("extremelysecure")

    def test_30_filter_by_conditions_errors(self):
        P = PolicyClass()

        class MockUser(object):
            login = 'login'
            realm = 'realm'
            resolver = 'resolver'

        user1 = MockUser()
        user1.info = {"type": "verysecure", "groups": ["a", "b", "c"]}

        # Various error cases:

        # an unknown section in the condition
        set_policy("unknownsection", scope=SCOPE.AUTH, action="{0!s}=userstore".format(ACTION.OTPPIN),
                    conditions=[("somesection", "bla", "equals", "verysecure", True)])
        with self.assertRaisesRegex(PolicyError, r".*unknown section.*"):
            P.match_policies(user_object=user1)
        delete_policy("unknownsection")

        # ... but the error does not occur if the condition is inactive
        set_policy("unknownsection", scope=SCOPE.AUTH, action="{0!s}=userstore".format(ACTION.OTPPIN),
                    conditions=[("somesection", "bla", "equals", "verysecure", False)])
        all_policies = P.list_policies()
        self.assertEqual(P.match_policies(user_object=user1), all_policies)
        delete_policy("unknownsection")

        # an unknown key in the condition
        set_policy("unknownkey", scope=SCOPE.AUTH, action="{0!s}=userstore".format(ACTION.OTPPIN),
                    conditions=[("userinfo", "bla", "equals", "verysecure", True)])
        with self.assertRaisesRegex(PolicyError, r".*Unknown key.*"):
            P.match_policies(user_object=user1)
        delete_policy("unknownkey")

        # a CompareError
        user4 = MockUser()
        user4.info = {"type": "notverysecure", "number": 5}

        set_policy("error", scope=SCOPE.AUTH, action="{0!s}=userstore".format(ACTION.OTPPIN),
                   conditions=[("userinfo", "number", "contains", "b", True)])
        with self.assertRaisesRegex(PolicyError, r".*Invalid comparison.*"):
            P.match_policies(user_object=user4)
        delete_policy("error")

    def test_31_match_pinode(self):
        # import_admin is only allowed to import on node1
        set_policy("import_node1", scope=SCOPE.ADMIN, action=ACTION.IMPORT,
                   adminuser="import_admin, delete_admin", pinode="pinode1")
        # delete_admin is allowed to do everything everywhere
        set_policy("delete_node2", scope=SCOPE.ADMIN, action=ACTION.DELETE,
                   adminuser="delete_admin", pinode="pinode2, pinode1")
        # enable_admin is allowed to enable on all nodes
        set_policy("enable", scope=SCOPE.ADMIN, action=ACTION.ENABLE,
                   adminuser="enable_admin", pinode="")

        P = PolicyClass()
        # Check what the user "import_admin" is allowed to do
        # Allowed to import on pinode 1
        pols = P.match_policies(scope=SCOPE.ADMIN, adminuser="import_admin", action=ACTION.IMPORT, pinode="pinode1")
        self.assertEqual({"import_node1"}, set(p['name'] for p in pols),)
        # Not allowed to import on pinode 2
        pols = P.match_policies(scope=SCOPE.ADMIN, adminuser="import_admin", action=ACTION.IMPORT, pinode="pinode2")
        self.assertEqual(set(), set(p['name'] for p in pols))
        # not allowed to delete on any node
        pols = P.match_policies(scope=SCOPE.ADMIN, adminuser="import_admin", action=ACTION.DELETE)
        self.assertEqual(set(), set(p['name'] for p in pols))

        # Check what the user "delete_admin" is allowerd to do
        pols = P.match_policies(scope=SCOPE.ADMIN, adminuser="delete_admin", action=ACTION.IMPORT, pinode="pinode1")
        self.assertEqual({"import_node1"}, set(p['name'] for p in pols))
        # Not allowed to import on pinode 2
        pols = P.match_policies(scope=SCOPE.ADMIN, adminuser="delete_admin", action=ACTION.IMPORT, pinode="pinode2")
        self.assertEqual(set(), set(p['name'] for p in pols))
        # Allowed to delete on node 1 and node 2
        pols = P.match_policies(scope=SCOPE.ADMIN, adminuser="delete_admin", action=ACTION.DELETE, pinode="pinode1")
        self.assertEqual(set({"delete_node2"}), set(p['name'] for p in pols))
        pols = P.match_policies(scope=SCOPE.ADMIN, adminuser="delete_admin", action=ACTION.DELETE, pinode="pinode2")
        self.assertEqual(set({"delete_node2"}), set(p['name'] for p in pols))

        # Check what the user "enable_admin" is allowed to do
        pols = P.match_policies(scope=SCOPE.ADMIN, adminuser="enable_admin", action=ACTION.ENABLE, pinode="pinode1")
        self.assertEqual({"enable"}, set(p['name'] for p in pols))
        pols = P.match_policies(scope=SCOPE.ADMIN, adminuser="enable_admin", action=ACTION.ENABLE, pinode="pinode2")
        self.assertEqual({"enable"}, set(p['name'] for p in pols))

        # Now check the Match-Object, which uses the pinode from the config: In testing environment it is "Node1".
        g = FakeFlaskG()
        g.client_ip = "127.0.0.1"
        g.audit_object = mock.Mock()
        g.policy_object = PolicyClass()
        g.logged_in_user = {"username": "delete_admin", "role": ROLE.ADMIN, "realm": ""}
        pols = Match.admin(g, "delete", None).policies()
        # There is is no policy for Node1 for the "delete_admin
        self.assertEqual(set(), set(p['name'] for p in pols))

        g.logged_in_user = {"username": "enable_admin", "role": ROLE.ADMIN, "realm": ""}
        pols = Match.admin(g, "enable", None).policies()
        # The "enable_admin" is allowed to enable on all nodes, so also on "Node1"
        self.assertEqual({"enable"}, set(p['name'] for p in pols))

        delete_policy("import_node1")
        delete_policy("delete_node2")
        delete_policy("enable")

    def test_31_filter_by_conditions_tokeninfo(self):
        def _names(policies):
            return set(p['name'] for p in policies)

        from privacyidea.lib.tokenclass import TokenClass
        from privacyidea.models import Token
        serial = "filter_by_conditions_token"
        db_token = Token(serial, tokentype="spass")
        db_token.save()
        token = TokenClass(db_token)
        token.set_tokeninfo({"fixedpin": "true", "otherinfo": "true"})

        P = PolicyClass()

        class MockUser(object):
            login = 'login'
            realm = 'realm'
            resolver = 'resolver'

        user1 = MockUser()
        user1.info = {"email": "foo@bar.com"}

        # Policy with initially inactive condition, setpin is allowed for this token
        set_policy("setpin_pol", scope=SCOPE.USER, action=ACTION.SETPIN,
                   conditions=[("tokeninfo", "fixedpin", "equals", "false", False)])

        # policy matches, because the condition on tokeninfo is inactive
        self.assertEqual(_names(P.match_policies(user_object=user1, serial=serial)),
                         {"setpin_pol"})

        # activate the condition
        set_policy("setpin_pol", conditions=[("tokeninfo", "fixedpin", "equals", "false", True)])

        # policy does not match anymore, because the condition on tokeninfo is active
        # setpin action not returned for our token with tokeninfo "fixedpin" = "true"
        self.assertEqual(_names(P.match_policies(user_object=user1, serial=serial)),
                         set())

        # A request without any serial number will raise a Policy error, since condition
        # on tokeninfo is there, but no dbtoken object is available.
        self.assertRaises(PolicyError, P.match_policies, user_object=user1)

        delete_policy("setpin_pol")
        db_token.delete()

    def test_32_filter_by_conditions_token(self):
        def _names(policies):
            return set(p['name'] for p in policies)

        from privacyidea.lib.tokenclass import TokenClass
        from privacyidea.models import Token
        serial = "filter_by_conditions_token"
        db_token = Token(serial, tokentype="spass")
        db_token.save()

        P = PolicyClass()

        class MockUser(object):
            login = 'login'
            realm = 'realm'
            resolver = 'resolver'

        user1 = MockUser()
        user1.info = {"email": "foo@bar.com"}

        # Policy with initially inactive condition, setpin is allowed for this token
        set_policy("setpin_pol", scope=SCOPE.USER, action=ACTION.SETPIN,
                   conditions=[("token", "tokentype", "equals", "hotp", False)])

        # policy matches, because the condition on tokeninfo is inactive
        self.assertEqual(_names(P.match_policies(user_object=user1, serial=serial)),
                         {"setpin_pol"})

        # activate the condition
        set_policy("setpin_pol", conditions=[("token", "tokentype", "equals", "hotp", True)])

        # policy does not match anymore, because the condition on tokeninfo is active
        # setpin action not returned for our token with tokentype == spass
        self.assertEqual(_names(P.match_policies(user_object=user1, serial=serial)),
                         set())

        # Now set a policy condition with a non-case matching token type!
        set_policy("setpin_pol", conditions=[("token", "tokentype", "equals", "Spass", True)])
        self.assertEqual(_names(P.match_policies(user_object=user1, serial=serial)),
                         set())

        # Now check, if we can compare numbers.
        set_policy("setpin_pol", conditions=[("token", "count", "<", "100", True)])
        self.assertEqual(_names(P.match_policies(user_object=user1, serial=serial)),
                         {"setpin_pol"})
        # The the counter of the token is >=100, the policy will not match anymore
        db_token.count = 102
        db_token.save()
        self.assertEqual(_names(P.match_policies(user_object=user1, serial=serial)),
                         set())

        # A request without any serial number will raise a Policy error, since condition
        # on tokeninfo is there, but no dbtoken object is available.
        self.assertRaises(PolicyError, P.match_policies, user_object=user1)

        # Now check, if a wrong comparison raises an exception
        set_policy("setpin_pol", conditions=[("token", "count", "<", "not a number", True)])
        self.assertRaises(PolicyError, P.match_policies, user_object=user1, serial=serial)

        delete_policy("setpin_pol")
        db_token.delete()

    def test_33_get_allowed_attributes(self):

        class MockUser(object):
            login = 'login'
            realm = 'realm'
            resolver = 'resolver'

        user = MockUser()
        g = FakeFlaskG()
        g.policy_object = PolicyClass()
        g.audit_object = FakeAudit()
        g.logged_in_user = {"role": "admin", "username": "admin", "realm": ""}

        d = get_allowed_custom_attributes(g, user)
        self.assertEqual({"set": {}, "delete": []}, d)

        set_policy("custom_attr", scope=SCOPE.ADMIN,
                   action="{0!s}=:hello: one two".format(ACTION.SET_USER_ATTRIBUTES))
        set_policy("custom_attr2", scope=SCOPE.ADMIN,
                   action="{0!s}=:hello2: * :hello: three".format(ACTION.SET_USER_ATTRIBUTES))
        set_policy("custom_attr3", scope=SCOPE.ADMIN,
                   action="{0!s}=:*: on off".format(ACTION.SET_USER_ATTRIBUTES))
        set_policy("custom_attr4", scope=SCOPE.ADMIN,
                   action="{0!s}=*".format(ACTION.DELETE_USER_ATTRIBUTES))
        # Also check, that a double entry "one" only appears once
        set_policy("custom_attr5", scope=SCOPE.ADMIN,
                   action="{0!s}=:hello: one".format(ACTION.SET_USER_ATTRIBUTES))
        g.policy_object = PolicyClass()

        d = get_allowed_custom_attributes(g, user)
        self.assertEqual(["*"], d.get("delete"))
        self.assertEqual(sorted(d.get("set").keys()), ["*", "hello", "hello2"])
        self.assertEqual(sorted(d.get("set").get("*")), ["off", "on"])
        self.assertEqual(sorted(d.get("set").get("hello")), ["one", "three", "two"])
        self.assertEqual(sorted(d.get("set").get("hello2")), ["*"])

    def test_40_disable_policy_client_remains(self):
        pname = "client_must_not_vanish"
        test_ip = "1.2.3.4"
        set_policy(pname, scope=SCOPE.AUTH,
                   action="otppin=none", client=test_ip)
        p = PolicyClass()
        plist = p.list_policies(name=pname)
        self.assertIn(test_ip, plist[0].get("client"))
        # Now disable the policy
        enable_policy(pname, enable=False)
        # client is still there
        p = PolicyClass()
        plist = p.list_policies(name=pname)
        self.assertIn(test_ip, plist[0].get("client"))
        # enable policy again
        enable_policy(pname, enable=True)
        # client is still there
        p = PolicyClass()
        plist = p.list_policies(name=pname)
        self.assertIn(test_ip, plist[0].get("client"))
        # clean up
        delete_policy(pname)


class PolicyMatchTestCase(MyTestCase):
    @classmethod
    def setUpClass(cls):
        """ create some policies """
        MyTestCase.setUpClass()
        set_policy(name="pol1",
                   action="audit",
                   scope="user",
                   realm="realm1",
                   resolver="reso",
                   user="foobar",
                   client="0.0.0.0/0",
                   active=True)
        set_policy(name="pol2",
                   action="tokentype=HOTP",
                   scope=SCOPE.AUTHZ,
                   realm="*")
        set_policy(name="pol2a",
                   action="tokentype=TOTP",
                   scope=SCOPE.AUTHZ,
                   realm="realm2")
        set_policy(name="pol3",
                   action="serial=OATH",
                   scope=SCOPE.AUTHZ,
                   realm="realm1",
                   resolver="resolver1")
        set_policy(name="pol4",
                   action="enroll, init, disable , enable, audit",
                   scope="admin",
                   realm="realm2",
                   adminuser="admin, superroot")

    def check_names(self, policies, names):
        self.assertEqual(set(p["name"] for p in policies), set(names))

    def test_01_action_only(self):
        g = FakeFlaskG()
        g.client_ip = "127.0.0.1"
        g.audit_object = mock.Mock()
        g.policy_object = PolicyClass()

        g.audit_object.audit_data = {}
        self.check_names(Match.action_only(g, SCOPE.AUTHZ, None).policies(),
                         {"pol2", "pol2a", "pol3"})
        self.assertEqual(set(g.audit_object.audit_data["policies"]),
                         {"pol2", "pol2a", "pol3"})

        g.audit_object.audit_data = {}
        self.check_names(Match.action_only(g, SCOPE.AUTHZ, "tokentype").policies(),
                         {"pol2", "pol2a"})
        self.assertEqual(set(g.audit_object.audit_data["policies"]),
                         {"pol2", "pol2a"})
        g.audit_object.audit_data = {}
        self.assertEqual(Match.action_only(g, SCOPE.AUTHZ, "tokentype").action_values(unique=False),
                         {"HOTP": ["pol2"], "TOTP": ["pol2a"]})
        self.assertEqual(set(g.audit_object.audit_data["policies"]),
                         {"pol2", "pol2a"})

        g.audit_object.audit_data = {}
        self.check_names(Match.action_only(g, SCOPE.AUTHZ, "no_detail_on_success").policies(),
                         {})
        self.assertEqual(g.audit_object.audit_data, {})

        with self.assertRaises(MatchingError):
            Match.action_only(g, SCOPE.ADMIN, "tokenview")

    def test_02_realm(self):
        g = FakeFlaskG()
        g.client_ip = "127.0.0.1"
        g.audit_object = mock.Mock()
        g.policy_object = PolicyClass()

        g.audit_object.audit_data = {}
        self.check_names(Match.realm(g, SCOPE.AUTHZ, "tokentype", None).policies(),
                         {"pol2", "pol2a"})
        self.check_names(Match.realm(g, SCOPE.AUTHZ, "tokentype", "realm1").policies(),
                         {"pol2"})
        self.check_names(Match.realm(g, SCOPE.AUTHZ, "tokentype", "realm2").policies(),
                         {"pol2", "pol2a"})
        self.check_names(Match.realm(g, SCOPE.AUTHZ, "tokentype", "realm3").policies(),
                         {"pol2"})
        self.check_names(Match.realm(g, SCOPE.AUTHZ, "serial", "realm1").policies(),
                         {"pol3"})

        with self.assertRaises(MatchingError):
            Match.realm(g, SCOPE.ADMIN, "tokentype", "realm1")

    def test_03_user(self):
        g = FakeFlaskG()
        g.client_ip = "127.0.0.1"
        g.audit_object = mock.Mock()
        g.policy_object = PolicyClass()

        class Foobar(User):
            def __init__(self):
                self.login = "foobar"
                self.realm = "realm1"
                self.resolver = "reso"

        class Baz(User):
            def __init__(self):
                self.login = "baz"
                self.realm = "realm1"
                self.resolver = "reso"

        self.check_names(Match.user(g, SCOPE.USER, "audit", Foobar()).policies(),
                         {"pol1"})
        self.check_names(Match.user(g, SCOPE.USER, "audit", Baz()).policies(),
                         {})
        self.check_names(Match.user(g, SCOPE.USER, "audit", None).policies(),
                         {"pol1"})

        with self.assertRaises(MatchingError):
            Match.user(g, SCOPE.ADMIN, "tokentype", Foobar())
        with self.assertRaises(MatchingError):
            Match.user(g, SCOPE.ADMIN, "tokentype", {"username": "bla", "realm": "foo", "role": ROLE.USER})

    def test_04_admin(self):
        g = FakeFlaskG()
        g.client_ip = "127.0.0.1"
        g.audit_object = mock.Mock()
        g.policy_object = PolicyClass()
        g.logged_in_user = {"username": "superroot", "realm": "", "role": ROLE.ADMIN}

        self.check_names(Match.admin(g, "enable", None).policies(),
                         {"pol4"})
        self.check_names(Match.admin(g, "enable", User("cornelius", "realm2")).policies(),
                         {"pol4"})
        self.check_names(Match.admin(g, "enable", User("cornelius", "realm1")).policies(),
                         {})

        g.logged_in_user = {"username": "superroot", "realm": "", "role": ROLE.USER}
        with self.assertRaises(MatchingError):
            self.check_names(Match.admin(g, "enable", User("cornelius", "realm1")).policies(),
                             {"pol4"})

    def test_05_admin_or_user(self):
        g = FakeFlaskG()
        g.client_ip = "127.0.0.1"
        g.audit_object = mock.Mock()
        g.policy_object = PolicyClass()

        g.logged_in_user = {"username": "superroot", "realm": "", "role": ROLE.ADMIN}
        self.check_names(Match.admin_or_user(g, "audit", None).policies(),
                         {"pol4"})
        self.check_names(Match.admin_or_user(g, "audit", User("cornelius", "realm2")).policies(),
                         {"pol4"})
        self.check_names(Match.admin_or_user(g, "audit", User("cornelius", "realm1")).policies(),
                         {})

        g.logged_in_user = {"username": "foobar", "realm": "realm1", "role": ROLE.USER}
        # The user foobar@realm1 matches pol1
        self.check_names(Match.admin_or_user(g, "audit", None).policies(),
                         {"pol1"})
        # A user in a different realm does not match!
        self.check_names(Match.admin_or_user(g, "audit", User("cornelius", "realm2")).policies(),
                         {})
        # A wrong user in a realm does not match!
        self.check_names(Match.admin_or_user(g, "audit", User("cornelius", "realm1")).policies(),
                         {})

        g.logged_in_user = {"username": "baz", "realm": "asdf", "role": ROLE.USER}
        self.check_names(Match.admin_or_user(g, "audit", None).policies(),
                         {})

        g.logged_in_user = {"username": "baz", "realm": "asdf", "role": "something"}
        with self.assertRaises(MatchingError):
            self.check_names(Match.admin_or_user(g, "enable", User("cornelius", "realm1")).policies(),
                             {"pol4"})

    @classmethod
    def tearDownClass(cls):
        delete_all_policies()
