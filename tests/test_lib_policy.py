"""
This test file tests the lib.policy.py

The lib.policy.py only depends on the database model.
"""
import dateutil
import mock
from werkzeug.datastructures.headers import Headers, EnvironHeaders

from privacyidea.lib.container import init_container, find_container_by_serial
from privacyidea.lib.containers.container_info import RegistrationState
from privacyidea.lib.policies.policy_conditions import (PolicyConditionClass, ConditionSection,
                                                        ConditionHandleMissingData)
from privacyidea.lib.token import init_token
from privacyidea.lib.tokens.emailtoken import EMAILACTION
from privacyidea.lib.utils.compare import PrimaryComparators
from privacyidea.models import PolicyDescription, Policy, PolicyCondition, db, NodeName
from .base import MyTestCase, FakeFlaskG, FakeAudit

from privacyidea.lib.auth import ROLE
from privacyidea.lib.policy import (set_policy, delete_policy, delete_policies,
                                    import_policies, export_policies,
                                    get_static_policy_definitions,
                                    PolicyClass, SCOPE, enable_policy,
                                    PolicyError, ACTION, MAIN_MENU,
                                    delete_all_policies,
                                    get_action_values_from_options, Match, MatchingError,
                                    get_allowed_custom_attributes, convert_action_dict_to_python_dict,
                                    set_policy_conditions, validate_actions)
from privacyidea.lib.realm import (set_realm, delete_realm, get_realms)
from privacyidea.lib.resolver import (save_resolver, get_resolver_list,
                                      delete_resolver)
from privacyidea.lib.error import ParameterError, privacyIDEAError
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

    def setUp(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        self.setUp_user_realm3()

    def test_01_create_simple_policy(self):
        # Success
        p = set_policy(name="pol1",
                       action=ACTION.CONTAINER_CLIENT_ROLLOVER,
                       scope=SCOPE.CONTAINER)
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
                       action=f"enrollHOTP, {ACTION.DISABLE} , {ACTION.ENABLE}",
                       scope=SCOPE.ADMIN,
                       description="test")
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

        policies = P.match_policies(scope=SCOPE.ADMIN,
                                    action=ACTION.DISABLE)
        self.assertTrue(len(policies) == 1, len(policies))
        self.assertTrue(policies[0].get("name") == "pol4")

        policies = P.match_policies(name="pol4")
        self.assertEqual(policies[0].get('description'), 'test')

    def test_02_update_policies(self):
        p = set_policy(name="pol1",
                       action=ACTION.CONTAINER_CLIENT_ROLLOVER,
                       scope=SCOPE.CONTAINER,
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
                       realm=self.realm2)
        self.assertTrue(p > 0)

        p = set_policy(name="pol3",
                       action="serial=OATH",
                       scope=SCOPE.AUTHZ,
                       realm=self.realm1,
                       resolver=self.resolvername1)
        self.assertTrue(p > 0)

        p = set_policy(name="pol4",
                       action=f"enrollHOTP, {ACTION.DISABLE}, {ACTION.ENABLE}",
                       scope=SCOPE.ADMIN,
                       realm=self.realm2,
                       adminuser=["admin", "superroot"],
                       description="test3")
        self.assertTrue(p > 0)

        p = set_policy(name="pol5",
                       action=f"enrollHOTP, {ACTION.DISABLE} , {ACTION.ENABLE}",
                       scope=SCOPE.ADMIN,
                       realm=self.realm2,
                       user_case_insensitive=True,
                       adminuser=["Admin", "superroot"])
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
        # find policies with user admin and just as case-insensitive police with Admin
        policies = P.match_policies(scope="admin", adminuser="admin")
        self.assertTrue(len(policies) == 2, "{0!s}".format(len(policies)))
        # find policies with user Admin and no case-sensitive police with admin
        policies = P.match_policies(scope="admin", adminuser="Admin")
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

        policies = P.match_policies(name="pol4")
        self.assertEqual(policies[0].get('description'), 'test3')

        # Find policy with user agent
        policies = P.match_policies(user_agent="privacyidea-cp")
        self.assertEqual("pol1", policies[0]["name"])

        delete_policy(name="pol5")

    def test_03_set_policy_fails(self):
        # invalid scope
        with self.assertRaises(ParameterError):
            set_policy(name="invalid", scope="invalid_scope")

        # Scope is None, but actions are defined
        with self.assertRaises(ParameterError) as exception:
            set_policy(name="invalid", action=ACTION.ENABLE)
            self.assertEqual("Scope is required to set action values!", exception.exception.message)

        # Invalid actions
        with self.assertRaises(ParameterError) as exception:
            set_policy(name="invalid", scope=SCOPE.ADMIN, action="invalid_action")
            self.assertEqual(f"The following actions are not valid for scope '{SCOPE.ADMIN}': ['invalid_action']",
                             exception.exception.message)

        # Priority
        with self.assertRaises(ParameterError) as exception:
            set_policy(name="invalid", action=ACTION.ENABLE, priority=0)
            self.assertEqual("Priority must be at least 1", exception.exception.message)

        # Invalid client ip
        with self.assertRaises(privacyIDEAError) as exception:
            set_policy(name="invalid", action=ACTION.ENABLE, client="10.1.2.3.4")
            self.assertEqual("Invalid client definition!", exception.exception.message)

        # Invalid realm
        with self.assertRaises(ParameterError) as exception:
            set_policy(name="invalid", action=ACTION.ENABLE, realm="invalid_realm")
            self.assertEqual("Invalid Realms ['invalid_realm']!", exception.exception.message)

        # Invalid adminrealm
        with self.assertRaises(ParameterError) as exception:
            set_policy(name="invalid", action=ACTION.ENABLE, adminrealm="invalid_realm")
            self.assertEqual("Invalid Adminrealms ['invalid_realm']!", exception.exception.message)

        # Invalid resolver
        with self.assertRaises(ParameterError) as exception:
            set_policy(name="invalid", action=ACTION.ENABLE, resolver="invalid_resolver")
            self.assertEqual("Undefined resolvers ['invalid_resolver']!", exception.exception.message)

        # Invalid node
        with self.assertRaises(ParameterError) as exception:
            set_policy(name="invalid", action=ACTION.ENABLE, pinode="invalid_node")
            self.assertEqual("Undefined nodes ['invalid_node']!", exception.exception.message)

        # Invalid time
        with self.assertRaises(ParameterError) as exception:
            set_policy(name="invalid", action=ACTION.ENABLE, time="Monday: 12-18")
            self.assertEqual("Invalid time format!", exception.exception.message)

    def test_04_delete_policy(self):
        d1 = PolicyDescription.query.filter_by().all()
        self.assertEqual(len(d1), 1)
        delete_policy(name="pol4")
        P = PolicyClass()
        pol4 = P.match_policies(name="pol4")
        self.assertTrue(pol4 == [], pol4)
        d1 = PolicyDescription.query.filter_by().all()
        self.assertEqual(len(d1), 0)

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
        set_policy(name="pol1", scope=SCOPE.CONTAINER, client="172.16.0.3, 172.16.0.4/24")
        set_policy(name="pol2", scope=SCOPE.AUTHZ, client="192.168.0.0/16, -192.168.1.1")
        set_policy(name="pol3", scope=SCOPE.AUTH, client="10.0.0.1, 10.0.0.2, 10.0.0.3")
        set_policy(name="pol4", scope=SCOPE.ADMIN)

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

        # Check client parameter is set correctly
        policy = Policy.query.filter_by(name="pol1").first()
        self.assertEqual("172.16.0.3, 172.16.0.4/24", policy.client)
        # Update policy without client keeps old parameter
        set_policy(name="pol1", scope=SCOPE.CONTAINER)
        self.assertEqual("172.16.0.3, 172.16.0.4/24", policy.client)
        # Set empty string removes client
        set_policy(name="pol1", scope=SCOPE.CONTAINER, client="")
        self.assertEqual("", policy.client)

    def test_08_user_policies(self):
        set_policy(name="pol1", scope=SCOPE.CONTAINER, user="*")
        set_policy(name="pol2", scope=SCOPE.AUTHZ, user="admin, root, user1")
        set_policy(name="pol3", scope=SCOPE.AUTH, user="*, !user1")
        set_policy(name="pol4", scope=SCOPE.ADMIN, user="*, -root")

        policy = Policy.query.filter_by(name="pol2").first()
        self.assertEqual("admin, root, user1", policy.user)

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

        # Update policy without user keeps old user parameter
        set_policy(name="pol2", scope=SCOPE.AUTHZ)
        self.assertEqual("admin, root, user1", policy.user)
        # Set empty string removes adminuser
        set_policy(name="pol2", scope=SCOPE.AUTHZ, user="")
        self.assertEqual("", policy.user)

    def test_08a_adminuser_policies(self):
        set_policy(name="pol1", scope=SCOPE.ADMIN, adminuser="*", user="")
        set_policy(name="pol2", scope=SCOPE.ADMIN, adminuser="admin, root, user1", user="*")
        set_policy(name="pol3", scope=SCOPE.ADMIN, adminuser="*, !user1", user="")
        set_policy(name="pol4", scope=SCOPE.ADMIN, adminuser="*, -root", user="")

        policy = Policy.query.filter_by(name="pol2").first()
        self.assertEqual("admin, root, user1", policy.adminuser)

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

        # Update policy without admin keeps old admin parameter
        set_policy(name="pol2", scope=SCOPE.ADMIN, user="*")
        self.assertEqual("admin, root, user1", policy.adminuser)
        # Set empty string removes adminuser
        set_policy(name="pol2", scope=SCOPE.ADMIN, adminuser="", user="*")
        self.assertEqual("", policy.adminuser)

    def test_09_realm_resolver_policy(self):
        set_policy(name="pol1", scope=SCOPE.CONTAINER, realm=self.realm1)
        set_policy(name="pol2", scope=SCOPE.AUTHZ, realm=self.realm1, resolver=self.resolvername1)
        set_policy(name="pol3", scope=SCOPE.AUTH, realm="", resolver=self.resolvername3)
        set_policy(name="pol4", scope=SCOPE.ENROLL, realm=self.realm3, active=True)

        P = PolicyClass()
        p = P.match_policies(realm=self.realm1)
        self.assertTrue(len(p) == 3, p)
        self.assertTrue(_check_policy_name("pol1", p), p)
        self.assertTrue(_check_policy_name("pol2", p), p)
        self.assertTrue(_check_policy_name("pol3", p), p)
        self.assertFalse(_check_policy_name("pol4", p), p)

        p = P.match_policies(realm=self.realm3)
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

        p = P.match_policies(resolver=self.resolvername1)
        self.assertEqual(len(p), 3)
        self.assertTrue(_check_policy_name("pol1", p), p)
        self.assertTrue(_check_policy_name("pol2", p), p)
        self.assertFalse(_check_policy_name("pol3", p), p)
        self.assertTrue(_check_policy_name("pol4", p), p)

        p = P.match_policies(resolver=self.resolvername3)
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

        # Check realm and resolver are set correctly
        policy = Policy.query.filter_by(name="pol2").first()
        self.assertEqual(self.resolvername1, policy.resolver)
        self.assertEqual(self.realm1, policy.realm)

        # Update policy without realm and resolver keeps old parameters
        set_policy(name="pol2", scope=SCOPE.AUTHZ)
        self.assertEqual(self.resolvername1, policy.resolver)
        self.assertEqual(self.realm1, policy.realm)
        # Set empty string removes realm and resolver
        set_policy(name="pol2", scope=SCOPE.AUTHZ, realm="", resolver="")
        self.assertEqual("", policy.resolver)
        self.assertEqual("", policy.realm)

    def test_10_action_policies(self):
        set_policy(name="pol1", scope=SCOPE.ADMIN, action=f"enrollHOTP, {ACTION.ENABLE}, {ACTION.DISABLE}")
        set_policy(name="pol2", scope=SCOPE.AUTH, action=f"{ACTION.RESETALLTOKENS}, {ACTION.OTPPIN}=1")
        set_policy(name="pol3", scope=SCOPE.ADMIN, action=f"*, -{ACTION.DISABLE}")
        set_policy(name="pol4", scope=SCOPE.AUTH, action=f"*, -{ACTION.OTPPIN}=2")

        P = PolicyClass()
        p = P.match_policies(scope=SCOPE.ADMIN, action="enrollHOTP")
        self.assertEqual(2, len(p), (len(p), p))

        p = P.match_policies(scope=SCOPE.ADMIN, action=ACTION.ENABLE)
        self.assertEqual(2, len(p), (len(p), p))

        p = P.match_policies(scope=SCOPE.ADMIN, action=ACTION.DISABLE)
        self.assertEqual(1, len(p), (len(p), p))

        p = P.match_policies(scope=SCOPE.AUTH, action=ACTION.OTPPIN)
        self.assertEqual(1, len(p), (len(p), p))

        # Check cases in which we pass an empty action or action=None
        p = P.match_policies(action="")
        # Here, we get pol3 and pol4
        self.assertEqual(len(p), 2)
        self.assertTrue(_check_policy_name("pol3", p), p)
        self.assertTrue(_check_policy_name("pol4", p), p)

        p = P.match_policies(action=None)
        self.assertEqual(len(p), 4)

        for i in range(1, 5):
            delete_policy(f"pol{i}")

    def test_11_get_policy_definitions(self):
        p = get_static_policy_definitions()
        self.assertTrue("admin" in p, p)

        p = get_static_policy_definitions(scope="admin")
        self.assertTrue("enable" in p, p)

    def test_12_get_allowed_tokentypes(self):
        set_policy(name="tt1", scope=SCOPE.AUTHZ, action=f"{ACTION.TOKENTYPE}=hotp totp, {ACTION.APIKEY}")
        set_policy(name="tt2", scope=SCOPE.AUTHZ, action=f"{ACTION.TOKENTYPE}=motp")

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

        delete_policy("tt1")
        delete_policy("tt2")

    def test_13_get_allowed_serials(self):
        set_policy(name="st1", scope=SCOPE.AUTHZ, action=f"{ACTION.SERIAL}=OATH")
        set_policy(name="st2", scope=SCOPE.AUTHZ, action=f"{ACTION.SERIAL}=mOTP ")

        P = PolicyClass()
        ttypes = P.get_action_values("serial", scope=SCOPE.AUTHZ)
        self.assertTrue("OATH" in ttypes)
        self.assertTrue("mOTP" in ttypes)
        self.assertFalse("TOTP" in ttypes)

        serial_policies = P.get_action_values("serial", scope=SCOPE.AUTHZ)
        self.assertEqual(serial_policies.get("OATH"), ["st1"])
        self.assertEqual(serial_policies.get("mOTP"), ["st2"])

        delete_policy("st1")
        delete_policy("st2")

    def test_14_fail_unique_policies(self):
        # create policies with two different texts
        set_policy(name="email1", scope=SCOPE.AUTH, action=f"{EMAILACTION.EMAILTEXT}=text 1")
        set_policy(name="email2", scope=SCOPE.AUTH, action=f"{EMAILACTION.EMAILTEXT}=text 2")

        # As there are two policies with different action values,
        # a PolicyError is raised.
        P = PolicyClass()
        self.assertRaises(PolicyError, P.get_action_values,
                          action=EMAILACTION.EMAILTEXT, scope=SCOPE.AUTH,
                          unique=True,
                          allow_white_space_in_action=True)
        delete_policy("email1")
        delete_policy("email2")

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
        set_policy(name="someUserAction", scope=SCOPE.USER, action=ACTION.DISABLE)
        P = PolicyClass()
        tt = P.ui_get_enroll_tokentypes("127.0.0.1", {"username": "kurt",
                                                      "realm": "realm",
                                                      "role": "user"})
        self.assertEqual(len(tt), 0)
        delete_policy("tokenEnroll")

        # Two admins:
        # adminA is allowed to enroll tokens in all realms
        # adminB is allowed to enroll tokens only in realmB

        set_policy(name="polAdminA", scope=SCOPE.ADMIN, adminuser="adminA", action="enrollHOTP, enrollTOTP")
        set_policy(name="polAdminB", scope=SCOPE.ADMIN, adminuser="adminB", realm=self.realm1, action="enrollHOTP")
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
        set_policy(name="tokenEnroll", scope=SCOPE.ADMIN, adminrealm=[self.realm1], action="enrollYUBIKEY")
        policy = Policy.query.filter_by(name="tokenEnroll").first()
        self.assertEqual(self.realm1, policy.adminrealm)
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

        # Update without passing adminrealm keeps old admin realm
        set_policy(name="tokenEnroll", scope=SCOPE.ADMIN, adminrealm=None, action="enrollYUBIKEY")
        policy = Policy.query.filter_by(name="tokenEnroll").first()
        self.assertEqual(self.realm1, policy.adminrealm)

        # Update with empty list removes adminrealm
        set_policy(name="tokenEnroll", scope=SCOPE.ADMIN, adminrealm="", action="enrollYUBIKEY")
        policy = Policy.query.filter_by(name="tokenEnroll").first()
        self.assertEqual("", policy.adminrealm)

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
        set_policy(name="polAdminA", scope=SCOPE.ADMIN, adminuser="adminA", action="enrollHOTP, enrollTOTP")
        set_policy(name="polAdminB", scope=SCOPE.ADMIN, adminuser="adminB", realm=self.realm2, action="enrollHOTP")
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
                                    [
                                        {'name': "passwd"},
                                        {'name': "passwords"}])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 2)

        # A user may do something else...
        set_policy(name="userpol41", scope=SCOPE.USER, action=ACTION.ENABLE, realm="realm4", resolver="passwd")
        set_policy(name="userpol42", scope=SCOPE.USER, action=ACTION.DELETE, realm="realm4", resolver="passwords")
        P = PolicyClass()

        # The two users are in different resolvers and get different rights
        rights = P.ui_get_rights(SCOPE.USER, "realm4", "postfix")
        self.assertEqual({ACTION.ENABLE, ACTION.DISABLE}, set(rights))

        rights = P.ui_get_rights(SCOPE.USER, "realm4", "usernotoken")
        self.assertEqual({ACTION.DISABLE, ACTION.DELETE}, set(rights))

        delete_policy("userpol41")
        delete_policy("userpol42")
        delete_realm("realm4")
        delete_resolver("passwords")
        delete_resolver("passwd")

    def test_18_policy_match_policies_with_time(self):
        # Set valid times
        set_policy(name="test", scope=SCOPE.AUTHZ, action=f"{ACTION.TOKENTYPE}=hotp totp", time="Mon-Fri: 08:00-16:30")
        set_policy(name="test", scope=SCOPE.AUTHZ, action=f"{ACTION.TOKENTYPE}=hotp totp", time="Tue-Thu:6-22")
        set_policy(name="test", scope=SCOPE.AUTHZ, action=f"{ACTION.TOKENTYPE}=hotp totp", time="Wed: 13:30-18")
        set_policy(name="test", scope=SCOPE.AUTHZ, action=f"{ACTION.TOKENTYPE}=hotp totp", time="Sat-Sun: 20-23:59")
        policy = Policy.query.filter_by(name="test").first()
        self.assertEqual("Sat-Sun: 20-23:59", policy.time)
        # set empty string removes time
        set_policy(name="test", scope=SCOPE.AUTHZ, action=f"{ACTION.TOKENTYPE}=hotp totp", time="")
        policy = Policy.query.filter_by(name="test").first()
        self.assertEqual("", policy.time)

        # Set invalid times raises Error
        self.assertRaises(ParameterError, set_policy, name="test", scope=SCOPE.AUTHZ,
                          action=f"{ACTION.TOKENTYPE}=hotp totp", time="Montag: 8-12")
        self.assertRaises(ParameterError, set_policy, name="test", scope=SCOPE.AUTHZ,
                          action=f"{ACTION.TOKENTYPE}=hotp totp", time=":8-12")
        self.assertRaises(ParameterError, set_policy, name="test", scope=SCOPE.AUTHZ,
                          action=f"{ACTION.TOKENTYPE}=hotp totp", time="Mon-Fri: 12:26")
        self.assertRaises(ParameterError, set_policy, name="test", scope=SCOPE.AUTHZ,
                          action=f"{ACTION.TOKENTYPE}=hotp totp", time="Mon:")
        self.assertRaises(ParameterError, set_policy, name="test", scope=SCOPE.AUTHZ,
                          action=f"{ACTION.TOKENTYPE}=hotp totp", time="Mon-Fri: 12-08")

        delete_policy("test")

        # Test policy matching
        set_policy(name="time1", scope=SCOPE.AUTHZ,
                   action=f"{ACTION.TOKENTYPE}=hotp totp, {ACTION.APIKEY}",
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
        # We create one realm "test_realm" with the resolvers
        # reso1 (prio 1)
        # reso2 (prio 2)
        # reso3 (prio 3)
        # A user user@test_realm will be identified as user.reso1@test_realm.
        # But we will also match policies for reso2.

        # no realm and resolver with the names that should be used in this test
        r = get_realms("test_realm")
        self.assertEqual(r, {})
        for name in ["reso1", "resoX", "resoA"]:
            r = get_resolver_list(name)
            self.assertEqual(r, {})

        # create user realm
        for reso in ["reso1", "resoX", "resoA"]:
            rid = save_resolver({"resolver": reso,
                                 "type": "passwdresolver",
                                 "fileName": FILE_PASSWORDS})
            self.assertTrue(rid > 0, rid)

        # create a realm with reso1 being the resolver with the highest priority
        (added, failed) = set_realm("test_realm",
                                    [{'name': "reso1", 'priority': 1},
                                     {'name': "resoX", 'priority': 2},
                                     {'name': "resoA", 'priority': 3}])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 3)

        user = User(login="cornelius",
                    realm="test_realm")
        # The user, that is created, is cornelius.reso1@realm1
        user_str = "{0!s}".format(user)
        self.assertEqual("<cornelius.reso1@test_realm>", user_str)
        # But the user "cornelius" is also contained in other resolves in
        # this realm
        r = user.get_ordered_resolvers()
        self.assertEqual(r, ["reso1", "resoX", "resoA"])
        self.assertFalse(user.is_empty())
        self.assertTrue(User().is_empty())

        # define a policy with the wrong resolver
        p = set_policy(name="checkAll", scope=SCOPE.AUTHZ, realm="test_realm",
                       resolver="resoX",
                       action=f"{ACTION.TOKENTYPE}=totp")
        self.assertTrue(p > 0)
        p = set_policy(name="catchAll", scope=SCOPE.AUTHZ, realm="test_realm",
                       action=f"{ACTION.TOKENTYPE}=totp")
        self.assertTrue(p > 0)
        P = PolicyClass()
        pols = P.match_policies(scope=SCOPE.AUTHZ, realm=user.realm,
                                resolver=user.resolver, user=user.login)
        self.assertEqual(len(pols), 1)

        # Now we change the policy, so that it uses check_all_resolver, i.e.
        p = set_policy(name="checkAll", scope=SCOPE.AUTHZ, realm="test_realm",
                       resolver="resoX", check_all_resolvers=True,
                       action=f"{ACTION.TOKENTYPE}=totp")
        self.assertTrue(p > 0)
        P = PolicyClass()
        pols = P.match_policies(scope=SCOPE.AUTHZ, realm=user.realm,
                                resolver=user.resolver, user=user.login)
        self.assertEqual(len(pols), 2)

        # delete policy
        delete_policy("checkAll")
        delete_policy("catchAll")
        # delete resolvers and realm
        delete_realm("test_realm")
        for reso in ["reso1", "resoX", "resoA"]:
            rid = delete_resolver(reso)
            self.assertTrue(rid > 0, rid)

    def test_22_non_ascii_user(self):
        set_policy(name="polnonascii",
                   action=f"enrollHOTP, {ACTION.OTPPINMINLEN}=4",
                   user='nönäscii',
                   scope=SCOPE.USER)

        P = PolicyClass()
        p = P.match_policies(action="enrollHOTP", user='somebodyelse')
        self.assertEqual(len(p), 0)

        p = P.match_policies(action="enrollHOTP", user='nönäscii')
        self.assertEqual(len(p), 1)

        delete_policy(name="polnonascii")

    def test_23_priorities(self):
        # create three policies with three different texts and different priorities
        set_policy(name="email1", scope=SCOPE.AUTH, action=f"{EMAILACTION.EMAILTEXT}=text 1", priority=4)
        set_policy(name="email2", scope=SCOPE.AUTH, action=f"{EMAILACTION.EMAILTEXT}=text 2", priority=1)
        set_policy(name="email3", scope=SCOPE.AUTH, action=f"{EMAILACTION.EMAILTEXT}=text 3", priority=77)

        # this chooses email2, because it has the highest priority
        P = PolicyClass()
        self.assertEqual(["text 2"], list(P.get_action_values(action=EMAILACTION.EMAILTEXT, scope=SCOPE.AUTH,
                                                              unique=True, allow_white_space_in_action=True).keys()))
        delete_policy("email2")

        # with email2 gone, this chooses email1
        self.assertEqual(["text 1"], list(P.get_action_values(action=EMAILACTION.EMAILTEXT, scope=SCOPE.AUTH,
                                                              unique=True, allow_white_space_in_action=True).keys()), )

        # if we now add another policy with priority 77, we get no conflict
        # because email1 is chosen
        set_policy(name="email4", scope=SCOPE.AUTH, action=f"{EMAILACTION.EMAILTEXT}=text 4", priority=77)

        self.assertEqual(["text 1"], list(P.get_action_values(action=EMAILACTION.EMAILTEXT, scope=SCOPE.AUTH,
                                                              unique=True, allow_white_space_in_action=True).keys()))

        # but we get a conflict if we change the priority of email4 to 4
        set_policy(name="email4", scope=SCOPE.AUTH, action=f"{EMAILACTION.EMAILTEXT}=text 4", priority=4)

        with self.assertRaises(PolicyError) as cm:
            P.get_action_values(action=EMAILACTION.EMAILTEXT, scope=SCOPE.AUTH, unique=True,
                                allow_white_space_in_action=True)
        self.assertIn("policies with conflicting actions", str(cm.exception))

        pols = P.match_policies(action=EMAILACTION.EMAILTEXT, scope=SCOPE.AUTH)
        self.assertEqual(len(pols), 3)
        with self.assertRaises(PolicyError):
            P.check_for_conflicts(pols, EMAILACTION.EMAILTEXT)

        P.check_for_conflicts([], EMAILACTION.EMAILTEXT)
        P.check_for_conflicts([pols[0]], EMAILACTION.EMAILTEXT)

        # we can also change the priority
        set_policy(name="email4", priority=3)

        self.assertEqual(["text 4"], list(P.get_action_values(action=EMAILACTION.EMAILTEXT, scope=SCOPE.AUTH,
                                                              unique=True, allow_white_space_in_action=True).keys()))

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

        pols = P.match_policies(action=EMAILACTION.EMAILTEXT, scope=SCOPE.AUTH)
        self.assertEqual(len(pols), 3)
        # this sorts by priority
        self.assertEqual(['email4', 'email1', 'email3'], [p['name'] for p in pols])

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
        set_policy(name="email1", scope=SCOPE.AUTH, action=f"{EMAILACTION.EMAILTEXT}='text 1'", priority=1)
        set_policy(name="email2", scope=SCOPE.AUTH, action=f"{EMAILACTION.EMAILTEXT}='text 1'", priority=1)

        # this reduces the action values to unique values
        P = PolicyClass()
        self.assertEqual(["text 1"],
                         list(P.get_action_values(scope=SCOPE.AUTH, action=EMAILACTION.EMAILTEXT).keys()))
        # this is allowed if the policies agree
        self.assertEqual(["text 1"],
                         list(P.get_action_values(scope=SCOPE.AUTH, action=EMAILACTION.EMAILTEXT, unique=True).keys()))

        set_policy(name="email2", action=f"{EMAILACTION.EMAILTEXT}='text 2'")
        with self.assertRaises(PolicyError):
            P.get_action_values(scope=SCOPE.AUTH, action=EMAILACTION.EMAILTEXT, unique=True)

        delete_policy("email1")
        delete_policy("email2")

    def test_24_challenge_text(self):
        g = FakeFlaskG()
        g.client_ip = "10.0.0.1"
        options = {"g": g,
                   "user": User("cornelius", self.realm1)}

        set_policy("chaltext", scope=SCOPE.AUTH,
                   action=f"{ACTION.CHALLENGETEXT}=Insert your yubikey and press the button")
        g.policy_object = PolicyClass()

        val = get_action_values_from_options(SCOPE.AUTH, ACTION.CHALLENGETEXT, options)
        self.assertEqual(val, "Insert your yubikey and press the button")

        delete_policy("chaltext")

    def test_25_get_action_values(self):
        # We test action values with different priority and values!
        set_policy("act1", scope=SCOPE.AUTH, action=f"{ACTION.OTPPIN}=userstore", priority=1)
        set_policy("act2", scope=SCOPE.AUTH, action=f"{ACTION.OTPPIN}=userstore", priority=1)
        set_policy("act3", scope=SCOPE.AUTH, action=f"{ACTION.OTPPIN}=userstore", priority=3)

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

        (added, failed) = set_realm("realm1", [{'name': "reso1"}])
        self.assertEqual(len(failed), 0)
        self.assertEqual(len(added), 1)

        (added, failed) = set_realm("realm2", [{'name': "reso2"}])
        self.assertEqual(len(failed), 0)
        self.assertEqual(len(added), 1)

        cornelius = User(login="cornelius", realm="realm1")
        nonascii = User(login="nönäscii", realm="realm1")
        selfservice = User(login="selfservice", realm="realm1")
        whoopsie = User(login="whoopsie", realm="realm2")
        set_policy("act1", scope=SCOPE.AUTH, action=f"{ACTION.OTPPIN}=userstore",
                   user="cornelius, nönäscii")
        set_policy("act2", scope=SCOPE.AUTH, action=f"{ACTION.OTPPIN}=userstore",
                   resolver="reso1")
        set_policy("act3", scope=SCOPE.AUTH, action=f"{ACTION.OTPPIN}=none",
                   realm="realm1")
        set_policy("act4", scope=SCOPE.AUTH, action=f"{ACTION.OTPPIN}=none",
                   user="nönäscii", realm="realm1")

        P = PolicyClass()
        self.assertSetEqual({"act1", "act2", "act3"}, set(p['name'] for p in P.match_policies(user_object=cornelius)))
        r = P.get_action_values(action=ACTION.OTPPIN, scope=SCOPE.AUTH, user_object=cornelius)
        self.assertIn('userstore', r, r)
        self.assertIn('none', r, r)
        self.assertSetEqual({'act1', 'act2'}, set(r['userstore']), r)
        self.assertEqual(['act3'], r['none'], r)

        self.assertSetEqual({"act1", "act2", "act3", "act4"},
                            set(p['name'] for p in P.match_policies(user_object=nonascii)))
        r = P.get_action_values(action=ACTION.OTPPIN, scope=SCOPE.AUTH, user_object=nonascii)
        self.assertIn('userstore', r, r)
        self.assertIn('none', r, r)
        self.assertSetEqual({'act1', 'act2'}, set(r['userstore']), r)
        self.assertSetEqual({'act3', 'act4'}, set(r['none']), r)

        self.assertSetEqual({"act2", "act3"}, set(p['name'] for p in P.match_policies(user_object=selfservice)))
        self.assertEqual({"userstore": ["act2"], "none": ["act3"]},
                         P.get_action_values(action=ACTION.OTPPIN, scope=SCOPE.AUTH, user_object=selfservice))

        self.assertSetEqual(set(), set(p['name'] for p in P.match_policies(user_object=whoopsie)))
        self.assertEqual(P.get_action_values(action=ACTION.OTPPIN, scope=SCOPE.AUTH,
                                             user_object=whoopsie),
                         {})

        self.assertSetEqual({"act1", "act2", "act3", "act4"},
                            set(p['name'] for p in P.match_policies(user_object=None)))
        r = P.get_action_values(action=ACTION.OTPPIN, scope=SCOPE.AUTH, user_object=None)
        self.assertIn('userstore', r, r)
        self.assertIn('none', r, r)
        self.assertSetEqual({'act1', 'act2'}, set(r['userstore']), r)
        self.assertSetEqual({'act3', 'act4'}, set(r['none']), r)

        self.assertSetEqual(set(), set(p['name'] for p in P.match_policies(user_object=User())))
        self.assertEqual({}, P.get_action_values(action=ACTION.OTPPIN, scope=SCOPE.AUTH,
                                                 user_object=User()))

        with self.assertRaises(ParameterError):
            P.match_policies(user_object=cornelius, realm="realm3")

        with self.assertRaises(ParameterError):
            P.get_action_values(action=ACTION.OTPPIN, scope=SCOPE.AUTH,
                                user_object=cornelius, user="selfservice")

        set_policy("act5", scope=SCOPE.AUTH, action=f"{ACTION.OTPPIN}=none")

        P = PolicyClass()
        # If we pass an empty user object, only policies without user match
        self.assertSetEqual({"act5"}, set(p['name'] for p in P.match_policies(user_object=User())))
        self.assertEqual({"none": ["act5"]},
                         P.get_action_values(action=ACTION.OTPPIN, scope=SCOPE.AUTH, user_object=User()))
        # If we pass None as the user object, all policies match
        self.assertSetEqual({"act1", "act2", "act3", "act4", "act5"},
                            set(p['name'] for p in P.match_policies(user_object=None)))
        r = P.get_action_values(action=ACTION.OTPPIN, scope=SCOPE.AUTH, user_object=None)
        self.assertIn('userstore', r, r)
        self.assertIn('none', r, r)
        self.assertSetEqual({'act1', 'act2'}, set(r['userstore']), r)
        self.assertSetEqual({'act3', 'act4', 'act5'}, set(r['none']), r)

        # if we pass user_obj ornelius, we only get 4 policies
        self.assertSetEqual({"act1", "act2", "act3", "act5"},
                            set(p['name'] for p in P.match_policies(user_object=cornelius)))
        # Provide a user object and parameters
        self.assertSetEqual({"act1", "act2", "act3", "act5"},
                            set(p['name'] for p in
                                P.match_policies(user_object=cornelius, user="cornelius", realm="realm1")))
        # For some reason pass the same user_obj and parameters, but realm in upper case
        self.assertSetEqual({"act1", "act2", "act3", "act5"},
                            set(p['name'] for p in
                                P.match_policies(user_object=cornelius, user="cornelius", realm="REALM1")))

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
        set_policy("act1", scope=SCOPE.AUTH, action=f"{ACTION.OTPPIN}=userstore", priority=1)
        self.assertEqual(["act1"], [p["name"] for p in policy_object.match_policies()])
        self.assertEqual(1, policy_object.match_policies()[0]["priority"])
        # Update the policy and check if the policies have been reloaded
        set_policy("act1", scope=SCOPE.AUTH, action=f"{ACTION.OTPPIN}=userstore", priority=2)
        self.assertEqual(2, policy_object.match_policies()[0]["priority"])
        # Add a second policy, check
        set_policy("act2", scope=SCOPE.AUTH, action=f"{ACTION.OTPPIN}=none", priority=3)
        self.assertSetEqual({"act1", "act2"}, {p["name"] for p in policy_object.match_policies()})
        # Delete a policy, check
        delete_policy("act1")
        self.assertSetEqual({"act2"}, {p["name"] for p in policy_object.match_policies()})
        delete_policy("act2")

    def test_28_conditions(self):
        rid = save_resolver({"resolver": "reso1",
                             "type": "passwdresolver",
                             "fileName": FILE_PASSWORDS})
        self.assertGreater(rid, 0)

        (added, failed) = set_realm("realm1", [{'name': "reso1"}])
        self.assertEqual(len(failed), 0)
        self.assertEqual(len(added), 1)

        # Set policy with conditions
        set_policy("act1", scope=SCOPE.AUTH, action=f"{ACTION.OTPPIN}=userstore",
                   conditions=[(ConditionSection.USERINFO, "type", PrimaryComparators.EQUALS, "verysecure", True)])

        P = PolicyClass()
        self.assertEqual([(ConditionSection.USERINFO, "type", PrimaryComparators.EQUALS, "verysecure", True,
                           ConditionHandleMissingData.RAISE_ERROR.value)], P.list_policies()[0]["conditions"])

        # Update existing policy with conditions
        set_policy("act1", conditions=[
            (ConditionSection.USERINFO, "type", PrimaryComparators.EQUALS, "notverysecure", True),
            (ConditionSection.HTTP_REQUEST_HEADER, "user_agent", PrimaryComparators.EQUALS, "vpn", True,
             ConditionHandleMissingData.RAISE_ERROR.value)
        ])

        self.assertEqual([(ConditionSection.USERINFO, "type", PrimaryComparators.EQUALS, "notverysecure", True,
                           ConditionHandleMissingData.RAISE_ERROR.value),
                          (ConditionSection.HTTP_REQUEST_HEADER, "user_agent", PrimaryComparators.EQUALS, "vpn", True,
                           ConditionHandleMissingData.RAISE_ERROR.value)], P.list_policies()[0]["conditions"])
        # check that old condition is not contained in the database anymore
        self.assertIsNone(PolicyCondition.query.filter_by(section=ConditionSection.USERINFO, Key="type",
                                                          comparator=PrimaryComparators.EQUALS,
                                                          Value="verysecure", active=True).first())

        # Set None for handle missing data is allowed, but is replaced with the default
        set_policy("act1",
                   conditions=[(ConditionSection.USERINFO, "type", PrimaryComparators.EQUALS, "notverysecure", True),
                               (ConditionSection.HTTP_REQUEST_HEADER, "user_agent", PrimaryComparators.EQUALS, "vpn",
                                True,
                                None)])
        self.assertSetEqual({(ConditionSection.USERINFO, "type", PrimaryComparators.EQUALS, "notverysecure", True,
                              ConditionHandleMissingData.RAISE_ERROR.value),
                             (ConditionSection.HTTP_REQUEST_HEADER, "user_agent", PrimaryComparators.EQUALS, "vpn",
                              True, ConditionHandleMissingData.RAISE_ERROR.value)},
                            set(P.list_policies()[0]["conditions"]))

        # Set policy with invalid condition tuple
        # Missing active value
        self.assertRaises(ParameterError, set_policy, "invalid_policy",
                          conditions=[(ConditionSection.USERINFO, "type", PrimaryComparators.EQUALS, "verysecure")])
        # check that policy is not set in the db
        self.assertIsNone(Policy.query.filter_by(name="invalid_policy").first())

        # invalid data type
        self.assertRaises(ParameterError, set_policy, "invalid_policy",
                          conditions=[(ConditionSection.USERINFO, ["type", "password"], PrimaryComparators.EQUALS,
                                       "verysecure", True)])
        # check that policy is not set in the db
        self.assertIsNone(Policy.query.filter_by(name="invalid_policy").first())

        # invalid data type of handle missing data
        self.assertRaises(ParameterError, set_policy, "invalid_policy",
                          conditions=[(ConditionSection.USERINFO, "type", PrimaryComparators.EQUALS, "verysecure", True,
                                       False)])
        # check that policy is not set in the db
        self.assertIsNone(Policy.query.filter_by(name="invalid_policy").first())

        # also raises an error if the condition is not active
        self.assertRaises(ParameterError, set_policy, "invalid_policy",
                          conditions=[("invalid", "type", PrimaryComparators.EQUALS, "verysecure", False)])
        # check that policy is not set in the db
        self.assertIsNone(Policy.query.filter_by(name="invalid_policy").first())

        delete_policy("act1")
        delete_realm("realm1")
        delete_resolver("reso1")

    def test_29_filter_by_conditions(self):
        def _names(policies):
            return set(p['name'] for p in policies)

        set_policy("verysecure", scope=SCOPE.AUTH, action=f"{ACTION.OTPPIN}=userstore",
                   conditions=[(ConditionSection.USERINFO, "type", PrimaryComparators.EQUALS, "verysecure", True)])
        set_policy("notverysecure", scope=SCOPE.AUTH, action=f"{ACTION.OTPPIN}=userstore",
                   conditions=[(ConditionSection.USERINFO, "type", PrimaryComparators.EQUALS, "notverysecure", True),
                               (ConditionSection.USERINFO, "groups", PrimaryComparators.CONTAINS, "b", True)])
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
        with self.assertRaisesRegex(PolicyError,
                                    "ERR303: Policy 'verysecure' has a condition on the section "
                                    "'userinfo' with key 'type', but a user is unavailable!"):
            P.match_policies(user_object=None)

        # empty user => policy error
        with self.assertRaisesRegex(PolicyError, ".*Unknown userinfo key.*"):
            P.match_policies(user_object=empty_user)

        # user1 => verysecure matches
        self.assertSetEqual({"verysecure"}, _names(P.match_policies(user_object=user1)))
        # user2 => no policy matches
        self.assertSetEqual(set(), _names(P.match_policies(user_object=user2)))
        # user3 => notverysecure matches
        self.assertSetEqual({"notverysecure"}, _names(P.match_policies(user_object=user3)))

        # an unforeseen error in the comparison function => policy error
        with mock.patch("privacyidea.lib.policies.policy_conditions.compare_values") as mock_function:
            mock_function.side_effect = ValueError
            with self.assertRaisesRegex(PolicyError, r".*Invalid comparison.*"):
                P.match_policies(user_object=user1)

        for policy in ["verysecure", "notverysecure"]:
            delete_policy(policy)

        # Policy with initially inactive condition
        set_policy("extremelysecure", scope=SCOPE.AUTH, action=f"{ACTION.OTPPIN}=userstore",
                   conditions=[(ConditionSection.USERINFO, "type", PrimaryComparators.EQUALS, "notverysecure", False)])

        # user1 matches, because the condition on type is inactive
        self.assertSetEqual({"extremelysecure"}, _names(P.match_policies(user_object=user1)))

        # activate the condition
        set_policy("extremelysecure",
                   conditions=[(ConditionSection.USERINFO, "type", PrimaryComparators.EQUALS, "notverysecure", True)])

        # user1 does not match anymore, because the condition on type is active
        self.assertSetEqual(set(), _names(P.match_policies(user_object=user1)))

        delete_policy("extremelysecure")

    def test_30_filter_by_conditions_errors(self):
        P = PolicyClass()

        class MockUser(object):
            login = 'login'
            realm = 'realm'
            resolver = 'resolver'

        user1 = MockUser()
        user1.info = {"type": "verysecure", "groups": ["a", "b", "c"]}

        def set_invalid_policy(name, scope, action, conditions):
            policy = Policy(name, scope=scope, action=action)
            policy.conditions = []
            for condition in conditions:
                policy.conditions.append(PolicyCondition(**condition))
            policy.save()

        # Various error cases:

        # an unknown section in the condition
        set_invalid_policy("unknownsection", scope=SCOPE.AUTH, action=f"{ACTION.OTPPIN}=userstore",
                           conditions=[{"section": "somesection", "Key": "bla", "comparator": PrimaryComparators.EQUALS,
                                        "Value": "verysecure", "active": True}])
        with self.assertRaisesRegex(PolicyError, r".*Unknown section.*"):
            P.match_policies(user_object=user1)
        delete_policy("unknownsection")

        # ... but the error does not occur if the condition is inactive
        set_invalid_policy("unknownsection", scope=SCOPE.AUTH, action=f"{ACTION.OTPPIN}=userstore",
                           conditions=[{"section": "somesection", "Key": "bla", "comparator": PrimaryComparators.EQUALS,
                                        "Value": "verysecure", "active": False}])
        all_policies = P.list_policies()
        self.assertEqual(all_policies, P.match_policies(user_object=user1))
        delete_policy("unknownsection")

        # an unknown key in the condition
        set_policy("unknownkey", scope=SCOPE.AUTH, action=f"{ACTION.OTPPIN}=userstore",
                   conditions=[(ConditionSection.USERINFO, "bla", PrimaryComparators.EQUALS, "verysecure", True)])
        with self.assertRaisesRegex(PolicyError, r".*Unknown .*key.*"):
            P.match_policies(user_object=user1)
        delete_policy("unknownkey")

        # a CompareError
        user4 = MockUser()
        user4.info = {"type": "notverysecure", "number": 5}

        set_policy("error", scope=SCOPE.AUTH, action=f"{ACTION.OTPPIN}=userstore",
                   conditions=[(ConditionSection.USERINFO, "number", PrimaryComparators.CONTAINS, "b", True)])
        with self.assertRaisesRegex(PolicyError, r".*Invalid comparison.*"):
            P.match_policies(user_object=user4)
        delete_policy("error")

    def test_31_match_pinode(self):
        db.session.add(NodeName(id="8e4272a9-9037-40df-8aa3-976e4a04b5a8", name="pinode1"))
        db.session.add(NodeName(id="d1d7fde6-330f-4c12-88f3-58a1752594bf", name="pinode2"))
        db.session.commit()

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
        self.assertSetEqual({"import_node1"}, set(p['name'] for p in pols), )
        # Not allowed to import on pinode 2
        pols = P.match_policies(scope=SCOPE.ADMIN, adminuser="import_admin", action=ACTION.IMPORT, pinode="pinode2")
        self.assertSetEqual(set(), set(p['name'] for p in pols))
        # not allowed to delete on any node
        pols = P.match_policies(scope=SCOPE.ADMIN, adminuser="import_admin", action=ACTION.DELETE)
        self.assertSetEqual(set(), set(p['name'] for p in pols))

        # Check what the user "delete_admin" is allowerd to do
        pols = P.match_policies(scope=SCOPE.ADMIN, adminuser="delete_admin", action=ACTION.IMPORT, pinode="pinode1")
        self.assertSetEqual({"import_node1"}, set(p['name'] for p in pols))
        # Not allowed to import on pinode 2
        pols = P.match_policies(scope=SCOPE.ADMIN, adminuser="delete_admin", action=ACTION.IMPORT, pinode="pinode2")
        self.assertSetEqual(set(), set(p['name'] for p in pols))
        # Allowed to delete on node 1 and node 2
        pols = P.match_policies(scope=SCOPE.ADMIN, adminuser="delete_admin", action=ACTION.DELETE, pinode="pinode1")
        self.assertSetEqual({"delete_node2"}, set(p['name'] for p in pols))
        pols = P.match_policies(scope=SCOPE.ADMIN, adminuser="delete_admin", action=ACTION.DELETE, pinode="pinode2")
        self.assertSetEqual({"delete_node2"}, set(p['name'] for p in pols))

        # Check what the user "enable_admin" is allowed to do
        pols = P.match_policies(scope=SCOPE.ADMIN, adminuser="enable_admin", action=ACTION.ENABLE, pinode="pinode1")
        self.assertSetEqual({"enable"}, set(p['name'] for p in pols))
        pols = P.match_policies(scope=SCOPE.ADMIN, adminuser="enable_admin", action=ACTION.ENABLE, pinode="pinode2")
        self.assertSetEqual({"enable"}, set(p['name'] for p in pols))

        # Now check the Match-Object, which uses the pinode from the config: In testing environment it is "Node1".
        g = FakeFlaskG()
        g.client_ip = "127.0.0.1"
        g.audit_object = mock.Mock()
        g.policy_object = PolicyClass()
        g.logged_in_user = {"username": "delete_admin", "role": ROLE.ADMIN, "realm": ""}
        pols = Match.admin(g, "delete", None).policies()
        # There is is no policy for Node1 for the "delete_admin
        self.assertSetEqual(set(), set(p['name'] for p in pols))

        g.logged_in_user = {"username": "enable_admin", "role": ROLE.ADMIN, "realm": ""}
        pols = Match.admin(g, "enable", None).policies()
        # The "enable_admin" is allowed to enable on all nodes, so also on "Node1"
        self.assertSetEqual({"enable"}, set(p['name'] for p in pols))

        # Check node parameter is set correctly
        policy = Policy.query.filter_by(name="import_node1").first()
        self.assertEqual("pinode1", policy.pinode)
        # Update policy without pinode parameter keeps old parameter
        set_policy("import_node1", scope=SCOPE.ADMIN, action=ACTION.IMPORT,
                   adminuser="import_admin, delete_admin")
        self.assertEqual("pinode1", policy.pinode)
        # Pass empty string to remove pinode parameter
        set_policy("import_node1", scope=SCOPE.ADMIN, action=ACTION.IMPORT,
                   adminuser="import_admin, delete_admin", pinode="")
        self.assertEqual("", policy.pinode)

        delete_policy("import_node1")
        delete_policy("delete_node2")
        delete_policy("enable")
        NodeName.query.filter_by(name="pinode1").first().delete()
        NodeName.query.filter_by(name="pinode2").first().delete()

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
                   conditions=[(ConditionSection.TOKENINFO, "fixedpin", PrimaryComparators.EQUALS, "false", False)])

        # policy matches, because the condition on tokeninfo is inactive
        self.assertSetEqual({"setpin_pol"}, _names(P.match_policies(user_object=user1, serial=serial)))

        # activate the condition
        set_policy("setpin_pol",
                   conditions=[(ConditionSection.TOKENINFO, "fixedpin", PrimaryComparators.EQUALS, "false", True,
                                ConditionHandleMissingData.RAISE_ERROR.value)])

        # policy does not match anymore, because the condition on tokeninfo is active
        # setpin action not returned for our token with tokeninfo "fixedpin" = "true"
        self.assertSetEqual(set(), _names(P.match_policies(user_object=user1, serial=serial)))

        # A request without any serial number will raise a Policy error, since condition
        # on tokeninfo is there, but no dbtoken object is available.
        self.assertRaises(PolicyError, P.match_policies, user_object=user1)

        # policy matches, because the condition shall be true if no token is available
        set_policy("setpin_pol",
                   conditions=[(ConditionSection.TOKENINFO, "fixedpin", PrimaryComparators.EQUALS, "false", True,
                                ConditionHandleMissingData.IS_TRUE.value)])
        self.assertSetEqual({"setpin_pol"}, _names(P.match_policies(user_object=user1)))

        # policy not matches, because the condition shall be false if no token is available, but not raise an error
        set_policy("setpin_pol", conditions=[(ConditionSection.TOKENINFO, "fixedpin", PrimaryComparators.EQUALS,
                                              "false", True, ConditionHandleMissingData.IS_FALSE.value)])
        self.assertSetEqual(set(), _names(P.match_policies(user_object=user1)))

        delete_policy("setpin_pol")
        db_token.delete()

    def test_32_filter_by_conditions_token(self):
        def _names(policies):
            return set(p['name'] for p in policies)

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
                   conditions=[(ConditionSection.TOKEN, "tokentype", PrimaryComparators.EQUALS, "hotp", False)])

        # policy matches, because the condition on tokeninfo is inactive
        self.assertSetEqual({"setpin_pol"}, _names(P.match_policies(user_object=user1, serial=serial)))

        # activate the condition
        set_policy("setpin_pol",
                   conditions=[(ConditionSection.TOKEN, "tokentype", PrimaryComparators.EQUALS, "hotp", True)])

        # policy does not match anymore, because the condition on tokeninfo is active
        # setpin action not returned for our token with tokentype == spass
        self.assertSetEqual(set(), _names(P.match_policies(user_object=user1, serial=serial)))

        # Now set a policy condition with a non-case matching token type!
        set_policy("setpin_pol",
                   conditions=[(ConditionSection.TOKEN, "tokentype", PrimaryComparators.EQUALS, "Spass", True)])
        self.assertSetEqual(set(), _names(P.match_policies(user_object=user1, serial=serial)))

        # Now check, if we can compare numbers.
        set_policy("setpin_pol", conditions=[(ConditionSection.TOKEN, "count", PrimaryComparators.SMALLER, "100", True,
                                              ConditionHandleMissingData.RAISE_ERROR.value)])
        self.assertSetEqual({"setpin_pol"}, _names(P.match_policies(user_object=user1, serial=serial)))
        # The the counter of the token is >=100, the policy will not match anymore
        db_token.count = 102
        db_token.save()
        self.assertSetEqual(set(), _names(P.match_policies(user_object=user1, serial=serial)))

        # A request without any serial number will raise a Policy error, since condition
        # on the token is there, but no dbtoken object is available.
        self.assertRaises(PolicyError, P.match_policies, user_object=user1)
        # raise error if key is not available
        set_policy("setpin_pol",
                   conditions=[(ConditionSection.TOKEN, "random", PrimaryComparators.SMALLER, "100", True)])
        self.assertRaises(PolicyError, P.match_policies, user_object=user1, serial=serial)

        # policy matches, because the condition shall be true if no token is available
        set_policy("setpin_pol", conditions=[(ConditionSection.TOKEN, "count", PrimaryComparators.SMALLER, "100", True,
                                              ConditionHandleMissingData.IS_TRUE.value)])
        self.assertSetEqual({"setpin_pol"}, _names(P.match_policies(user_object=user1)))

        # policy not matches, because the condition shall be false if no token is available
        set_policy("setpin_pol", conditions=[(ConditionSection.TOKEN, "count", PrimaryComparators.SMALLER, "100", True,
                                              ConditionHandleMissingData.IS_FALSE.value)])
        self.assertSetEqual(set(), _names(P.match_policies(user_object=user1)))

        # Now check, if a wrong comparison raises an exception
        set_policy("setpin_pol",
                   conditions=[(ConditionSection.TOKEN, "count", PrimaryComparators.SMALLER, "not a number", True)])
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

        set_policy("custom_attr", scope=SCOPE.ADMIN, action=f"{ACTION.SET_USER_ATTRIBUTES}=:hello: one two")
        set_policy("custom_attr2", scope=SCOPE.ADMIN, action=f"{ACTION.SET_USER_ATTRIBUTES}=:hello2: * :hello: three")
        set_policy("custom_attr3", scope=SCOPE.ADMIN, action=f"{ACTION.SET_USER_ATTRIBUTES}=:*: on off")
        set_policy("custom_attr4", scope=SCOPE.ADMIN, action=f"{ACTION.DELETE_USER_ATTRIBUTES}=*")
        # Also check, that a double entry "one" only appears once
        set_policy("custom_attr5", scope=SCOPE.ADMIN, action=f"{ACTION.SET_USER_ATTRIBUTES}=:hello: one")
        g.policy_object = PolicyClass()

        d = get_allowed_custom_attributes(g, user)
        self.assertEqual(["*"], d.get("delete"))
        self.assertEqual(["*", "hello", "hello2"], sorted(d.get("set").keys()))
        self.assertEqual(["off", "on"], sorted(d.get("set").get("*")))
        self.assertEqual(["one", "three", "two"], sorted(d.get("set").get("hello")))
        self.assertEqual(["*"], sorted(d.get("set").get("hello2")))

        delete_policy("custom_attr")
        delete_policy("custom_attr2")
        delete_policy("custom_attr3")
        delete_policy("custom_attr4")
        delete_policy("custom_attr5")

    def test_40_disable_policy_client_remains(self):
        pname = "client_must_not_vanish"
        test_ip = "1.2.3.4"
        set_policy(pname, scope=SCOPE.AUTH, action=f"{ACTION.OTPPIN}=none", client=test_ip)
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

    def test_41_list_policies_user_realm_resolver(self):
        set_policy(name="enable", scope=SCOPE.ADMIN, action=ACTION.ENABLE)
        set_policy(name="disable", scope=SCOPE.ADMIN, action=ACTION.DISABLE)
        set_policy(name="disable_realm1", scope=SCOPE.ADMIN, action=ACTION.DISABLE, realm=self.realm1)
        set_policy(name="disable_realm2", scope=SCOPE.ADMIN, action=ACTION.DISABLE, realm=self.realm2)
        set_policy(name="disable_realm3", scope=SCOPE.ADMIN, action=ACTION.DISABLE, realm=self.realm3)
        set_policy(name="disable_realm1_userA", scope=SCOPE.ADMIN, action=ACTION.DISABLE, realm=self.realm1,
                   user="userA")
        set_policy(name="disable_realm2_userA", scope=SCOPE.ADMIN, action=ACTION.DISABLE, realm=self.realm2,
                   user="userA")
        set_policy(name="disable_resolver1", scope=SCOPE.ADMIN, action=ACTION.DISABLE, resolver=self.resolvername1)
        set_policy(name="disable_resolver3", scope=SCOPE.ADMIN, action=ACTION.DISABLE, resolver=self.resolvername3)
        set_policy(name="disable_realm1_userA_resolver1", scope=SCOPE.ADMIN, action=ACTION.DISABLE, realm=self.realm1,
                   user="userA", resolver=self.resolvername1)
        set_policy(name="disable_realm1_userA_resolver3", scope=SCOPE.ADMIN, action=ACTION.DISABLE, realm=self.realm1,
                   user="userA", resolver=self.resolvername3)
        P = PolicyClass()

        # get policies for action read
        policies = P.list_policies(action=ACTION.DISABLE)
        self.assertEqual(10, len(policies))

        # get policies applicable for realm A
        policies = P.list_policies(action=ACTION.DISABLE, realm=self.realm1)
        policy_names = {p["name"] for p in policies}
        self.assertEqual(7, len(policies))
        correct_policies = {"disable", "disable_realm1", "disable_realm1_userA", "disable_resolver1",
                            "disable_resolver3", "disable_realm1_userA_resolver1",
                            "disable_realm1_userA_resolver3"}
        self.assertSetEqual(correct_policies, policy_names)

        # get policies applicable for any user and resolver of realm A
        policies = P.list_policies(action=ACTION.DISABLE, realm=self.realm1, user="", resolver="")
        policy_names = {p["name"] for p in policies}
        self.assertEqual(2, len(policies))
        correct_policies = {"disable", "disable_realm1"}
        self.assertSetEqual(correct_policies, policy_names)

        # get policies applicable of userA in realmA of resolver1
        policies = P.list_policies(action=ACTION.DISABLE, realm=self.realm1, user="userA", resolver=self.resolvername1)
        policy_names = {p["name"] for p in policies}
        self.assertEqual(5, len(policies))
        correct_policies = {"disable", "disable_realm1", "disable_realm1_userA", "disable_resolver1",
                            "disable_realm1_userA_resolver1"}
        self.assertSetEqual(correct_policies, policy_names)

        # get policies applicable to userA in realm1 of resolver1 or realm2+resolver1
        policies = P.list_policies(action=ACTION.DISABLE, realm=self.realm1, user="userA", resolver=self.resolvername1,
                                   additional_realms=[self.realm2])
        policy_names = {p["name"] for p in policies}
        self.assertEqual(6, len(policies))
        correct_policies = {"disable", "disable_realm1", "disable_realm2", "disable_realm1_userA",
                            "disable_resolver1", "disable_realm1_userA_resolver1"}
        self.assertSetEqual(correct_policies, policy_names)

        delete_policy("enable")
        delete_policy("disable")
        delete_policy("disable_realm1")
        delete_policy("disable_realm2")
        delete_policy("disable_realm3")
        delete_policy("disable_realm1_userA")
        delete_policy("disable_realm2_userA")
        delete_policy("disable_resolver1")
        delete_policy("disable_resolver3")
        delete_policy("disable_realm1_userA_resolver1")
        delete_policy("disable_realm1_userA_resolver3")

    def test_42_convert_action_dict_to_python_dict_success(self):
        action_dict = "'Key1':'Value1'-'Community News':'https://community.privacyidea.org/c/news.rss'-'Key2':'Value2'"
        python_dict = convert_action_dict_to_python_dict(action_dict)
        correct_dict = {"Key1": "Value1", "Community News": "https://community.privacyidea.org/c/news.rss",
                        "Key2": "Value2"}
        self.assertDictEqual(correct_dict, python_dict)

        # single entry
        action_dict = "'Key1':'Value1'"
        python_dict = convert_action_dict_to_python_dict(action_dict)
        self.assertDictEqual({"Key1": "Value1"}, python_dict)

        # empty string
        python_dict = convert_action_dict_to_python_dict("")
        self.assertEqual({}, python_dict)

    def test_43_convert_action_dict_to_python_dict_fail(self):
        # invalid separator between key-value pairs
        action_dict = "'Key1':'Value1'- 'Community News':'https://community.privacyidea.org/c/news.rss','Key2':'Value2'"
        python_dict = convert_action_dict_to_python_dict(action_dict)
        self.assertEqual({}, python_dict)

        # keys and values not set in single quotes
        action_dict = "Key1:Value1-Community News:https://community.privacyidea.org/c/news.rss-Key2:Value2"
        python_dict = convert_action_dict_to_python_dict(action_dict)
        self.assertEqual({}, python_dict)

        # invalid separator between key and value
        action_dict = "'Key1' 'Value1'-'Community News': 'https://community.privacyidea.org/c/news.rss'-'Key2'-'Value2'"
        python_dict = convert_action_dict_to_python_dict(action_dict)
        self.assertEqual({}, python_dict)

    def test_44_delete_policies_list(self):
        # Clean up policies from previous tests...
        delete_all_policies()
        # No policies exist
        policies = Policy.query.filter_by().all()
        self.assertFalse(policies, policies)
        # Create some policies
        set_policy("wan1", scope=SCOPE.ENROLL, action="webauthn_relying_party_id=fritz.box")
        set_policy("wan2", scope=SCOPE.ENROLL, action="webauthn_relying_party_name=fritz box")
        policies = Policy.query.filter_by().all()
        self.assertEqual(2, len(policies), policies)
        # Delete those and one that does not exist in between, which will NOT raise an error and still remove the
        # other 2, indicated by the returned ids
        deleted_ids = delete_policies(["wan1", "wan3", "wan2"])
        self.assertEqual(2, len(deleted_ids), deleted_ids)
        policies = Policy.query.filter_by().all()
        self.assertFalse(policies, policies)

    def test_45_filter_by_condition_missing_data_error(self):
        """
        This test checks the behaviour to raise an error if any data is missing to check the condition.
        """
        policy_class = PolicyClass()
        # Define condition
        set_policy("policy", scope=SCOPE.USER, action=ACTION.SETPIN,
                   conditions=[(ConditionSection.TOKENINFO, "fixedpin", PrimaryComparators.EQUALS, "false", True,
                                ConditionHandleMissingData.RAISE_ERROR.value)])

        # Create token for a user
        user = User(login="hans", realm=self.realm2)
        token = init_token({"type": "hotp", "genkey": True}, user=user)

        # Token object not available
        error_message = (r"Policy 'policy' has a condition on the section 'tokeninfo' with key 'fixedpin', but a token "
                         r"is unavailable!")
        with self.assertRaisesRegex(PolicyError, error_message):
            policy_class.match_policies(user_object=user)

        # Key not available
        error_message = r"Unknown tokeninfo key 'fixedpin' referenced in condition of policy 'policy'"
        with self.assertRaisesRegex(PolicyError, error_message):
            policy_class.match_policies(user_object=user, serial=token.get_serial())

        # Compare Error
        token.set_tokeninfo({"count_auth": "invalid_count"})
        set_policy("policy", scope=SCOPE.USER, action=ACTION.SETPIN,
                   conditions=[(ConditionSection.TOKENINFO, "count_auth", PrimaryComparators.BIGGER, "3", True,
                                ConditionHandleMissingData.RAISE_ERROR.value)])
        self.assertRaises(PolicyError, policy_class.match_policies, user_object=user, serial=token.get_serial())

        delete_policy("policy")

    def test_46_filter_by_condition_missing_data_true(self):
        """
        This test checks the behaviour to evaluate the condition to true if any data is missing.
        """
        policy_class = PolicyClass()
        # Define condition
        set_policy("policy", scope=SCOPE.USER, action=ACTION.SETPIN,
                   conditions=[(ConditionSection.TOKENINFO, "fixedpin", PrimaryComparators.EQUALS, "false", True,
                                ConditionHandleMissingData.IS_TRUE.value)])

        # Create token for a user
        user = User(login="hans", realm=self.realm2)
        token = init_token({"type": "hotp", "genkey": True}, user=user)

        # Token object not available
        policies = policy_class.match_policies(user_object=user)
        self.assertEqual("policy", policies[0]['name'])

        # Key not available
        policy_class.match_policies(user_object=user, serial=token.get_serial())
        self.assertEqual("policy", policies[0]['name'])

        # Compare Error still raises error
        token.set_tokeninfo({"count_auth": "3"})
        set_policy("policy", scope=SCOPE.USER, action=ACTION.SETPIN,
                   conditions=[(ConditionSection.TOKENINFO, "count_auth", PrimaryComparators.BIGGER, "3.5", True,
                                ConditionHandleMissingData.IS_TRUE.value)])
        self.assertRaises(PolicyError, policy_class.match_policies, user_object=user, serial=token.get_serial())

        delete_policy("policy")

    def test_47_filter_by_condition_missing_data_false(self):
        """
        This test checks the behaviour to evaluate the condition to false if any data is missing.
        """
        policy_class = PolicyClass()
        # Define condition
        set_policy("policy", scope=SCOPE.USER, action=ACTION.SETPIN,
                   conditions=[(ConditionSection.TOKENINFO, "fixedpin", PrimaryComparators.EQUALS, "false", True,
                                ConditionHandleMissingData.IS_FALSE.value)])

        # Create token for a user
        user = User(login="hans", realm=self.realm2)
        token = init_token({"type": "hotp", "genkey": True}, user=user)

        # Token object not available
        policies = policy_class.match_policies(user_object=user)
        self.assertEqual(0, len(policies))

        # Key not available
        policy_class.match_policies(user_object=user, serial=token.get_serial())
        self.assertEqual(0, len(policies))

        # Compare Error still raises error
        token.set_tokeninfo({"count_auth": "three"})
        set_policy("policy", scope=SCOPE.USER, action=ACTION.SETPIN,
                   conditions=[(ConditionSection.TOKENINFO, "count_auth", PrimaryComparators.SMALLER, "3", True,
                                ConditionHandleMissingData.IS_FALSE.value)])
        self.assertRaises(PolicyError, policy_class.match_policies, user_object=user, serial=token.get_serial())

        delete_policy("policy")

    def test_48_filter_by_condition_user_info(self):
        cornelius = User(login="cornelius", realm=self.realm1)
        selfservice = User(login="selfservice", realm=self.realm1)
        policy_class = PolicyClass()

        set_policy("policy", scope=SCOPE.USER, action=ACTION.SETPIN,
                   conditions=[(ConditionSection.USERINFO, "phone", PrimaryComparators.MATCHES, "\+49.*", True,
                                ConditionHandleMissingData.RAISE_ERROR.value)])

        # Policy matches
        policies = policy_class.match_policies(user_object=cornelius)
        self.assertEqual(1, len(policies))
        self.assertSetEqual({"policy"}, {p["name"] for p in policies})

        # Policy does not match
        policies = policy_class.match_policies(user_object=selfservice)
        self.assertEqual(0, len(policies))

        # ---- Raise error on missing data ----
        # missing user object
        self.assertRaises(PolicyError, policy_class.match_policies, user_object=None)

        # Empty user / missing key
        self.assertRaises(PolicyError, policy_class.match_policies, user_object=User())

        # ---- Condition is true on missing data ----
        set_policy("policy", scope=SCOPE.USER, action=ACTION.SETPIN,
                   conditions=[(ConditionSection.USERINFO, "phone", PrimaryComparators.MATCHES, "\+49.*", True,
                                ConditionHandleMissingData.IS_TRUE.value)])
        # missing user object
        policies = policy_class.match_policies(user_object=None)
        self.assertEqual(1, len(policies))
        self.assertSetEqual({"policy"}, {p["name"] for p in policies})

        # empty user / missing key
        policies = policy_class.match_policies(user_object=User())
        self.assertEqual(1, len(policies))
        self.assertSetEqual({"policy"}, {p["name"] for p in policies})

        # ---- Condition is false on missing data ----
        set_policy("policy", scope=SCOPE.USER, action=ACTION.SETPIN,
                   conditions=[(ConditionSection.USERINFO, "phone", PrimaryComparators.MATCHES, "\+49.*", True,
                                ConditionHandleMissingData.IS_FALSE.value)])
        # missing user object
        policies = policy_class.match_policies(user_object=None)
        self.assertEqual(0, len(policies))

        # empty user / missing key
        policies = policy_class.match_policies(user_object=User())
        self.assertEqual(0, len(policies))

        delete_policy("policy")

    def test_49_condition_handle_missing_data_get_selection_dict(self):
        # check that all enums are included in get_selection_dict (dict for the UI)
        enum_members = {member.value for member in ConditionHandleMissingData.__members__.values()}
        dict_members = set(ConditionHandleMissingData.get_selection_dict().keys())
        self.assertSetEqual(enum_members, dict_members)

    def test_50_get_policy_condition_from_tuple(self):
        # No handle missing data
        condition_tuple = (ConditionSection.USERINFO, "email", PrimaryComparators.MATCHES, ".*@example.com", True)
        condition = PolicyClass.get_policy_condition_from_tuple(condition_tuple, "policy")
        self.assertEqual(ConditionSection.USERINFO, condition.section)
        self.assertEqual("email", condition.key)
        self.assertEqual(PrimaryComparators.MATCHES, condition.comparator)
        self.assertEqual(".*@example.com", condition.value)
        self.assertTrue(condition.active)
        self.assertEqual(ConditionHandleMissingData.RAISE_ERROR, condition.handle_missing_data)

        # Pass None for handle_missing_data
        condition_tuple = (ConditionSection.USERINFO, "email", PrimaryComparators.MATCHES, ".*@example.com", True, None)
        condition = PolicyClass.get_policy_condition_from_tuple(condition_tuple, "policy")
        self.assertEqual(ConditionSection.USERINFO, condition.section)
        self.assertEqual("email", condition.key)
        self.assertEqual(PrimaryComparators.MATCHES, condition.comparator)
        self.assertEqual(".*@example.com", condition.value)
        self.assertTrue(condition.active)
        self.assertEqual(ConditionHandleMissingData.RAISE_ERROR, condition.handle_missing_data)

        # With handle missing data
        condition_tuple = (ConditionSection.USERINFO, "email", PrimaryComparators.MATCHES, ".*@example.com", True,
                           ConditionHandleMissingData.IS_TRUE.value)
        condition = PolicyClass.get_policy_condition_from_tuple(condition_tuple, "policy")
        self.assertEqual(ConditionSection.USERINFO, condition.section)
        self.assertEqual("email", condition.key)
        self.assertEqual(PrimaryComparators.MATCHES, condition.comparator)
        self.assertEqual(".*@example.com", condition.value)
        self.assertTrue(condition.active)
        self.assertEqual(ConditionHandleMissingData.IS_TRUE, condition.handle_missing_data)

    def test_51_set_policy_conditions(self):
        # Success
        policy = Policy(name="policy", scope=SCOPE.USER, action=ACTION.ENABLE)
        policy.save()
        conditions = [
            PolicyConditionClass(ConditionSection.USERINFO, "email", PrimaryComparators.MATCHES, ".*@example.com",
                                 True),
            PolicyConditionClass(ConditionSection.TOKEN, "tokentype", PrimaryComparators.EQUALS, "hotp", True,
                                 ConditionHandleMissingData.IS_FALSE.value)]
        set_policy_conditions(conditions, policy)
        db.session.commit()

        policy = Policy.query.filter_by(name="policy").first()
        conditions = policy.conditions
        self.assertEqual(2, len(conditions))
        for condition in conditions:
            if condition.section == ConditionSection.USERINFO:
                self.assertEqual("email", condition.Key)
                self.assertEqual(PrimaryComparators.MATCHES, condition.comparator)
                self.assertEqual(".*@example.com", condition.Value)
                self.assertTrue(condition.active)
                self.assertEqual(ConditionHandleMissingData.RAISE_ERROR.value, condition.handle_missing_data)
            else:
                self.assertEqual(ConditionSection.TOKEN, condition.section)
                self.assertEqual("tokentype", condition.Key)
                self.assertEqual(PrimaryComparators.EQUALS, condition.comparator)
                self.assertEqual("hotp", condition.Value)
                self.assertTrue(condition.active)
                self.assertEqual(ConditionHandleMissingData.IS_FALSE.value, condition.handle_missing_data)

        conditions = PolicyCondition.query.filter_by(active=True).all()
        self.assertEqual(2, len(conditions))

        # set empty list removes conditions
        set_policy_conditions([], policy)
        db.session.commit()

        policy = Policy.query.filter_by(name="policy").first()
        conditions = policy.conditions
        self.assertEqual(0, len(conditions))

        conditions = PolicyCondition.query.filter_by(active=True).all()
        self.assertEqual(0, len(conditions))

        delete_policy("policy")

    def test_52_validate_actions(self):
        action_dict = {ACTION.ENABLE: True, ACTION.HIDE_TOKENINFO: "hashlib private_server_key", ACTION.DISABLE: True}
        action_str = f"{ACTION.ENABLE}, {ACTION.HIDE_TOKENINFO}=hashlib private_server_key ,{ACTION.DISABLE}"
        action_list = [ACTION.ENABLE, ACTION.TOKENINFO, ACTION.DISABLE]

        # Valid actions for admin scope
        self.assertTrue(validate_actions(SCOPE.ADMIN, action_dict))
        self.assertTrue(validate_actions(SCOPE.ADMIN, action_str))

        # Valid actions for user scope
        self.assertTrue(validate_actions(SCOPE.USER, action_dict))
        self.assertTrue(validate_actions(SCOPE.USER, action_str))

        # Invalid actions for enroll scope
        with self.assertRaises(ParameterError) as exception:
            validate_actions(SCOPE.ENROLL, action_dict)
            self.assertEqual(f"Invalid actions [{ACTION.ENABLE}, {ACTION.HIDE_TOKENINFO}, {ACTION.DISABLE}]",
                             exception.exception.message)
        with self.assertRaises(ParameterError) as exception:
            validate_actions(SCOPE.ENROLL, action_str)
            self.assertEqual(f"Invalid actions [{ACTION.ENABLE}, {ACTION.HIDE_TOKENINFO}, {ACTION.DISABLE}]",
                             exception.exception.message)

        # Invalid for non-existing scope
        with self.assertRaises(ParameterError) as exception:
            validate_actions("non-exisiting-scope", action_dict)
            self.assertEqual(f"Invalid actions [{ACTION.ENABLE}, {ACTION.HIDE_TOKENINFO}, {ACTION.DISABLE}]",
                             exception.exception.message)
        with self.assertRaises(ParameterError) as exception:
            validate_actions("non-exisiting-scope", action_str)
            self.assertEqual(f"Invalid actions [{ACTION.ENABLE}, {ACTION.HIDE_TOKENINFO}, {ACTION.DISABLE}]",
                             exception.exception.message)

        # Invalid action type
        with self.assertRaises(ParameterError) as exception:
            validate_actions(SCOPE.ADMIN, action_list)
            self.assertEqual("Invalid actions type 'list'. Must be a string or a dictionary.",
                             exception.exception.message)

        # Use wildcard
        self.assertTrue(validate_actions(SCOPE.ADMIN, "*"))

        # Exclude actions from wildcard
        self.assertTrue(validate_actions(SCOPE.ADMIN, f"*, -{ACTION.ENABLE}, {ACTION.DISABLE}, !{ACTION.DELETE}"))

        # Exclude invalid actions passes (excluded actions are not checked anyway)
        with self.assertRaises(ParameterError) as exception:
            validate_actions(SCOPE.ADMIN, f"*, -i_am_invalid, {ACTION.DISABLE}, !not-existing")
            self.assertEqual("Invalid actions: ['i_am_invalid', 'not-existing']", exception.exception.message)

        # Invalid action set to false are also not accepted
        with self.assertRaises(ParameterError) as exception:
            validate_actions(SCOPE.ADMIN, {"i_am_invalid": False})
            self.assertEqual("Invalid actions: ['i_am_invalid']", exception.exception.message)

        # Invalid action string (actions can not be extracted correctly)
        action_str = (f"{ACTION.ENABLE}, {ACTION.HIDE_TOKENINFO}:hashlib private_server_key ,"
                      f"{ACTION.DISABLE}; {ACTION.DELETE}")
        with self.assertRaises(ParameterError) as exception:
            validate_actions(SCOPE.ADMIN, action_str)
            self.assertEqual(f"Invalid actions: ['{ACTION.HIDE_TOKENINFO}:hashlib private_server_key', "
                             f"'{ACTION.DISABLE}; {ACTION.DELETE}']", exception.exception.message)

    def test_53_set_policy_validate_realms(self):
        """
        This test checks that the realm parameter is evaluated correctly in the set_policy function
        """
        # Valid single realm
        set_policy(name="test", scope=SCOPE.ADMIN, realm=self.realm1)

        # Valid list
        set_policy(name="test", scope=SCOPE.ADMIN, realm=[self.realm1, self.realm2])
        set_policy(name="test", scope=SCOPE.ADMIN, realm=f"{self.realm1}, {self.realm2}")

        # realm is None
        set_policy(name="test", scope=SCOPE.ADMIN, realm=None)

        # Use wildcard and negations
        set_policy(name="test", scope=SCOPE.ADMIN, realm=f"*, -{self.realm1}, {self.realm2}, !{self.realm1}")

        # Invalid data type
        self.assertRaises(ParameterError, set_policy, name="test", scope=SCOPE.ADMIN, realm={self.realm1, self.realm2})

        # Undefined Realm
        with self.assertRaises(ParameterError) as exception:
            set_policy(name="test", scope=SCOPE.ADMIN, realm=[self.realm2, "undefined_realm", self.realm1, "invalid"])
            self.assertEqual("Undefined Realms: ['undefined_realm', 'invalid']!", exception.exception.message)
        with self.assertRaises(ParameterError) as exception:
            set_policy(name="test", scope=SCOPE.ADMIN, realm=f"{self.realm2}, undefined_realm,{self.realm1} ,invalid")
            self.assertEqual("Undefined Realms: ['undefined_realm', 'invalid']!", exception.exception.message)
        with self.assertRaises(ParameterError) as exception:
            set_policy(name="test", scope=SCOPE.ADMIN, realm=f"{self.realm2}, -undefined_realm,{self.realm1} ,!invalid")
            self.assertEqual("Undefined Realms: ['undefined_realm', 'invalid']!", exception.exception.message)

        delete_policy("test")

    def test_54_set_policy_validate_resolvers(self):
        # Valid single resolver
        set_policy(name="test", scope=SCOPE.ADMIN, resolver=self.resolvername1)

        # Valid list
        set_policy(name="test", scope=SCOPE.ADMIN, resolver=[self.resolvername1, self.resolvername3, ""])
        set_policy(name="test", scope=SCOPE.ADMIN, resolver=f"{self.resolvername1}, {self.resolvername3}")

        # resolver is None
        set_policy(name="test", scope=SCOPE.ADMIN, resolver=None)

        # Use wildcard and negations
        set_policy(name="test", scope=SCOPE.ADMIN, resolver=f"*, -{self.resolvername1}, !{self.resolvername3}, ")

        # Invalid data type
        self.assertRaises(ParameterError, set_policy, name="test", scope=SCOPE.ADMIN,
                          resolver={self.resolvername1, self.resolvername3})

        # Undefined Resolver
        with self.assertRaises(ParameterError) as exception:
            set_policy(name="test", scope=SCOPE.ADMIN,
                       resolver=[self.resolvername1, "undefined_resolver", self.resolvername3, "invalid"])
            self.assertEqual("Undefined Resolvers: ['undefined_resolver', 'invalid']!", exception.exception.message)
        with self.assertRaises(ParameterError) as exception:
            set_policy(name="test", scope=SCOPE.ADMIN, resolver=f"undefined_resolver,{self.resolvername1}, invalid")
            self.assertEqual("Undefined Resolvers: ['undefined_resolver', 'invalid']!", exception.exception.message)
        with self.assertRaises(ParameterError) as exception:
            set_policy(name="test", scope=SCOPE.ADMIN,
                       resolver=f"*, -undefined_resolver,{self.resolvername1}, !invalid")
            self.assertEqual("Undefined Resolvers: ['undefined_resolver', 'invalid']!", exception.exception.message)

        delete_policy("test")

    def test_55_set_policy_validate_nodes(self):
        node1 = "pinode1"
        node2 = "pinode2"
        db.session.add(NodeName(id="8e4272a9-9037-40df-8aa3-976e4a04b5a8", name=node1))
        db.session.add(NodeName(id="d1d7fde6-330f-4c12-88f3-58a1752594bf", name=node2))
        db.session.commit()

        # Valid single node
        set_policy(name="test", scope=SCOPE.ADMIN, pinode=node1)

        # Valid list
        set_policy(name="test", scope=SCOPE.ADMIN, pinode=[node1, "", "*", node2])
        set_policy(name="test", scope=SCOPE.ADMIN, pinode=f"{node1}, {node2}")

        # node is None
        set_policy(name="test", scope=SCOPE.ADMIN, pinode=None)

        # Use wildcard and negations
        set_policy(name="test", scope=SCOPE.ADMIN, pinode=f"*, -{node1}, !{node2}")

        # Invalid data type
        self.assertRaises(ParameterError, set_policy, name="test", scope=SCOPE.ADMIN, realm={node1, node2})

        # Undefined Node
        with self.assertRaises(ParameterError) as exception:
            set_policy(name="test", scope=SCOPE.ADMIN, pinode=[node1, "undefined_node", node2, "invalid"])
            self.assertEqual("Undefined Nodes: ['undefined_node', 'invalid']!", exception.exception.message)
        with self.assertRaises(ParameterError) as exception:
            set_policy(name="test", scope=SCOPE.ADMIN, pinode=f"undefined_node,{node1}, invalid")
            self.assertEqual("Undefined Nodes: ['undefined_node', 'invalid']!", exception.exception.message)
        with self.assertRaises(ParameterError) as exception:
            set_policy(name="test", scope=SCOPE.ADMIN, pinode=f"*, -undefined_node,{node1}, !invalid")
            self.assertEqual("Undefined Nodes: ['undefined_node', 'invalid']!", exception.exception.message)

        NodeName.query.filter_by(name=node1).first().delete()
        NodeName.query.filter_by(name=node2).first().delete()
        delete_policy("test")

    def test_56_list_policies_user_agent(self):
        set_policy(name="policy-cp", scope=SCOPE.AUTH, action={ACTION.CHALLENGERESPONSE: ["hotp"]},
                   user_agents=["privacyidea-cp", "PAM"])
        set_policy(name="policy-keycloak", scope=SCOPE.AUTH, action={ACTION.CHALLENGERESPONSE: ["totp", "push"]},
                   user_agents=["privacyIDEA-Keycloak", "Mozilla"])
        set_policy(name="policy-no-agent", scope=SCOPE.AUTH, action={ACTION.CHALLENGERESPONSE: ["daypassword"]})
        P = PolicyClass()

        # get policies for CP
        policies = P.list_policies(scope=SCOPE.AUTH, user_agent="privacyidea-cp")
        self.assertEqual(2, len(policies), policies)
        self.assertSetEqual({"policy-cp", "policy-no-agent"}, {policy["name"] for policy in policies})

        # check that search is case-insensitive
        policies = P.list_policies(scope=SCOPE.AUTH, user_agent="privacyIDEA-CP")
        self.assertEqual(2, len(policies), policies)
        self.assertSetEqual({"policy-cp", "policy-no-agent"}, {policy["name"] for policy in policies})

        # get policies for PAM
        policies = P.list_policies(scope=SCOPE.AUTH, user_agent="PAM")
        self.assertEqual(2, len(policies), policies)
        self.assertSetEqual({"policy-cp", "policy-no-agent"}, {policy["name"] for policy in policies})

        # get policies for Keycloak
        policies = P.list_policies(scope=SCOPE.AUTH, user_agent="privacyidea-keycloak")
        self.assertEqual(2, len(policies), policies)
        self.assertSetEqual({"policy-keycloak", "policy-no-agent"}, {policy["name"] for policy in policies})

        # no user agent filter: only get policies without user agent
        policies = P.list_policies(scope=SCOPE.AUTH)
        self.assertEqual(1, len(policies), policies)
        self.assertSetEqual({"policy-no-agent"}, {policy["name"] for policy in policies})


class PolicyConditionClassTestCase(MyTestCase):

    def test_01_init_success(self):
        # All parameters are valid and default is set
        condition = PolicyConditionClass(ConditionSection.USERINFO, "email", PrimaryComparators.MATCHES,
                                         ".*@example.com",
                                         True)
        self.assertTrue(isinstance(condition, PolicyConditionClass))
        self.assertEqual(ConditionHandleMissingData.RAISE_ERROR, condition.handle_missing_data)

        # All parameters are valid with handle_missing_data
        condition = PolicyConditionClass(ConditionSection.USERINFO, "email", PrimaryComparators.MATCHES,
                                         ".*@example.com",
                                         True,
                                         ConditionHandleMissingData.IS_TRUE.value)
        self.assertTrue(isinstance(condition, PolicyConditionClass))
        self.assertEqual(ConditionHandleMissingData.IS_TRUE, condition.handle_missing_data)

        # Pass None for handle_missing_data
        condition = PolicyConditionClass(ConditionSection.USERINFO, "email", PrimaryComparators.MATCHES,
                                         ".*@example.com",
                                         True, None)
        self.assertTrue(isinstance(condition, PolicyConditionClass))
        self.assertEqual(ConditionHandleMissingData.RAISE_ERROR, condition.handle_missing_data)

    def test_02_init_invalid_parameters(self):
        # Invalid section
        with self.assertRaises(ParameterError) as exception:
            PolicyConditionClass("invalid", "email", PrimaryComparators.MATCHES, ".*@example.com", True)
            self.assertIn("Unknown section", exception.exception.message)

        # Invalid key
        with self.assertRaises(ParameterError) as exception:
            PolicyConditionClass(ConditionSection.USERINFO, ["email"], PrimaryComparators.MATCHES, ".*@example.com",
                                 True)
            self.assertEqual("Key must be a non-empty string. Got '[\"email\"]' of type 'list' instead.",
                             exception.exception.message)

        # Invalid comparator
        with self.assertRaises(ParameterError) as exception:
            PolicyConditionClass(ConditionSection.USERINFO, "email", "random", ".*@example.com", True)
            self.assertEqual("Unknown comparator 'random'.", exception.exception.message)

        # Invalid value
        with self.assertRaises(ParameterError) as exception:
            PolicyConditionClass(ConditionSection.USERINFO, "email", PrimaryComparators.MATCHES, False, True)
            self.assertIn("Value must be a non-empty string.", exception.exception.message)

        # Invalid active
        with self.assertRaises(ParameterError) as exception:
            PolicyConditionClass(ConditionSection.USERINFO, "email", PrimaryComparators.MATCHES, ".*@example.com",
                                 "True")
            self.assertIn("Active must be a boolean.", exception.exception.message)

        # Invalid handle_missing_data
        with self.assertRaises(ParameterError) as exception:
            PolicyConditionClass(ConditionSection.USERINFO, "email", PrimaryComparators.MATCHES, ".*@example.com", True,
                                 "random")
            self.assertIn("Unknown handle missing data value", exception.exception.message)

    def test_03_allow_invalid_parameters(self):
        """
        We can allow invalid parameters if the condition is inactive. This is used when an invalid inactive condition
        is already contained in the db to not raise an error during the policy matching as the condition is not applied
        anyway.
        """
        # --- Invalid section ---
        # inactive condition
        condition = PolicyConditionClass("invalid", "email", PrimaryComparators.MATCHES, ".*@example.com", False,
                                         pass_if_inactive=True)
        self.assertTrue(isinstance(condition, PolicyConditionClass))
        self.assertEqual("invalid", condition.section)

        # activate the condition will raise an error
        with self.assertRaises(ParameterError) as exception:
            condition.active = True
            self.assertIn("Invalid condition can not be activated", exception.exception.message)
            self.assertIn("Unknown section", exception.exception.message)

        # active condition will still raise error
        with self.assertRaises(ParameterError) as exception:
            PolicyConditionClass("invalid", "email", PrimaryComparators.MATCHES, ".*@example.com", True,
                                 pass_if_inactive=True)
            self.assertIn("Unknown section", exception.exception.message)

        # --- Invalid key ---
        # inactive condition
        condition = PolicyConditionClass(ConditionSection.USERINFO, ["email"], PrimaryComparators.MATCHES,
                                         ".*@example.com",
                                         False,
                                         pass_if_inactive=True)
        self.assertTrue(isinstance(condition, PolicyConditionClass))
        self.assertEqual(["email"], condition.key)

        # activate the condition will raise an error
        with self.assertRaises(ParameterError) as exception:
            condition.active = True
            self.assertIn("Invalid condition can not be activated", exception.exception.message)
            self.assertIn("Key must be a non-empty string", exception.exception.message)

        # active condition will still raise error
        with self.assertRaises(ParameterError) as exception:
            PolicyConditionClass(ConditionSection.USERINFO, ["email"], PrimaryComparators.MATCHES, ".*@example.com",
                                 True,
                                 pass_if_inactive=True)
            self.assertEqual("Key must be a non-empty string. Got '[\"email\"]' of type 'list' instead.",
                             exception.exception.message)

        # --- Invalid comparator ---
        # inactive condition
        condition = PolicyConditionClass(ConditionSection.USERINFO, "email", "random", ".*@example.com", False,
                                         pass_if_inactive=True)
        self.assertTrue(isinstance(condition, PolicyConditionClass))
        self.assertEqual("random", condition.comparator)

        # activate the condition will raise an error
        with self.assertRaises(ParameterError) as exception:
            condition.active = True
            self.assertIn("Invalid condition can not be activated", exception.exception.message)
            self.assertIn("Unknown comparator", exception.exception.message)

        # active condition will still raise error
        with self.assertRaises(ParameterError) as exception:
            PolicyConditionClass(ConditionSection.USERINFO, "email", "random", ".*@example.com", True,
                                 pass_if_inactive=True)
            self.assertEqual("Unknown comparator 'random'.", exception.exception.message)

        # --- Invalid value ---
        # inactive condition
        condition = PolicyConditionClass(ConditionSection.USERINFO, "email", PrimaryComparators.MATCHES, False, False,
                                         pass_if_inactive=True)
        self.assertTrue(isinstance(condition, PolicyConditionClass))
        self.assertEqual(False, condition.value)

        # --- Invalid active ---
        # active condition will still raise error
        with self.assertRaises(ParameterError) as exception:
            PolicyConditionClass(ConditionSection.USERINFO, "email", PrimaryComparators.MATCHES, False, True,
                                 pass_if_inactive=True)
            self.assertIn("Value must be a non-empty string.", exception.exception.message)

        # Invalid active always raises error
        with self.assertRaises(ParameterError) as exception:
            PolicyConditionClass(ConditionSection.USERINFO, "email", PrimaryComparators.MATCHES, ".*@example.com",
                                 "True",
                                 pass_if_inactive=True)
            self.assertIn("Active must be a boolean.", exception.exception.message)
        with self.assertRaises(ParameterError) as exception:
            PolicyConditionClass(ConditionSection.USERINFO, "email", PrimaryComparators.MATCHES, ".*@example.com",
                                 "False",
                                 pass_if_inactive=True)
            self.assertIn("Active must be a boolean.", exception.exception.message)

        # --- Invalid handle_missing_data ---
        # inactive condition
        condition = PolicyConditionClass(ConditionSection.USERINFO, "email", PrimaryComparators.MATCHES,
                                         ".*@example.com",
                                         False, "random", True)
        self.assertTrue(isinstance(condition, PolicyConditionClass))
        self.assertEqual("random", condition.handle_missing_data)

        # activate the condition will raise an error
        with self.assertRaises(ParameterError) as exception:
            condition.active = True
            self.assertIn("Invalid condition can not be activated", exception.exception.message)
            self.assertIn("Unknown handle missing data", exception.exception.message)

        # active condition will still raise error
        with self.assertRaises(ParameterError) as exception:
            PolicyConditionClass(ConditionSection.USERINFO, "email", PrimaryComparators.MATCHES, ".*@example.com", True,
                                 "random", True)
            self.assertIn("Unknown handle missing data value", exception.exception.message)

    def test_04_get_user_data(self):
        self.setUp_user_realms()
        cornelius = User(login="cornelius", realm=self.realm1)
        selfservice = User(login="selfservice", realm=self.realm1)
        condition = PolicyConditionClass(section=ConditionSection.USERINFO, key="birthday",
                                         comparator=PrimaryComparators.MATCHES, value=".*May.*", active=True)

        # user object not available
        data = condition.get_user_data(user=None)
        self.assertEqual("user", data.object_name)
        self.assertFalse(data.object_available)
        self.assertIsNone(data.value)
        self.assertIsNone(data.available_keys)

        # user available, but key is not available
        data = condition.get_user_data(selfservice)
        self.assertEqual("user", data.object_name)
        self.assertTrue(data.object_available)
        self.assertIsNone(data.value)
        self.assertTrue(isinstance(data.available_keys, list))

        # user and key available, but key is empty
        condition = PolicyConditionClass(section=ConditionSection.USERINFO, key="email",
                                         comparator=PrimaryComparators.MATCHES, value=".*@example.com", active=True)
        data = condition.get_user_data(selfservice)
        self.assertEqual("user", data.object_name)
        self.assertTrue(data.object_available)
        self.assertEqual("", data.value)
        self.assertIsNone(data.available_keys)

        # user and key available
        condition = PolicyConditionClass(section=ConditionSection.USERINFO, key="email",
                                         comparator=PrimaryComparators.MATCHES, value=".*@example.com", active=True)
        data = condition.get_user_data(cornelius)
        self.assertEqual("user", data.object_name)
        self.assertTrue(data.object_available)
        self.assertEqual("user@localhost.localdomain", data.value)
        self.assertIsNone(data.available_keys)

    def test_05_get_token_data_object_not_available(self):
        condition = PolicyConditionClass(section=ConditionSection.TOKEN, key="tokentype",
                                         comparator=PrimaryComparators.EQUALS, value="hotp", active=True)

        # Pass invalid serial
        data = condition.get_token_data("1234")
        self.assertEqual("token", data.object_name)
        self.assertFalse(data.object_available)
        self.assertIsNone(data.value)
        self.assertIsNone(data.available_keys)

    def test_06_get_token_data_token(self):
        condition = PolicyConditionClass(section=ConditionSection.TOKEN, key="tokentype",
                                         comparator=PrimaryComparators.EQUALS, value="hotp", active=True)
        token = init_token({"type": "hotp", "genkey": True})

        # Everything available
        data = condition.get_token_data(token.get_serial())
        self.assertEqual("token", data.object_name)
        self.assertTrue(data.object_available)
        self.assertEqual("hotp", data.value)
        self.assertIsNone(data.available_keys)

        # Key not available
        condition = PolicyConditionClass(section=ConditionSection.TOKEN, key="hashlib",
                                         comparator=PrimaryComparators.EQUALS,
                                         value="sha256", active=True)
        data = condition.get_token_data(token.get_serial())
        self.assertEqual("token", data.object_name)
        self.assertTrue(data.object_available)
        self.assertIsNone(data.value)
        self.assertTrue(isinstance(data.available_keys, list))

    def test_07_get_token_data_token_info(self):
        condition = PolicyConditionClass(section=ConditionSection.TOKENINFO, key="hashlib",
                                         comparator=PrimaryComparators.EQUALS, value="sha256", active=True)
        token = init_token({"type": "hotp", "genkey": True, "hashlib": "sha1"})

        # Everything available
        data = condition.get_token_data(token.get_serial())
        self.assertEqual("token", data.object_name)
        self.assertTrue(data.object_available)
        self.assertEqual("sha1", data.value)
        self.assertIsNone(data.available_keys)

        # Key not available
        condition = PolicyConditionClass(section=ConditionSection.TOKENINFO, key="tokentype",
                                         comparator=PrimaryComparators.EQUALS, value="hotp", active=True)
        data = condition.get_token_data(token.get_serial())
        self.assertEqual("token", data.object_name)
        self.assertTrue(data.object_available)
        self.assertIsNone(data.value)
        self.assertTrue(isinstance(data.available_keys, list))

    def test_08_get_request_header_data(self):
        condition = PolicyConditionClass(section=ConditionSection.HTTP_REQUEST_HEADER, key="User-Agent",
                                         comparator=PrimaryComparators.EQUALS, value="SpecialApp", active=True)
        request_headers = Headers({})

        # Request header not available
        data = condition.get_request_header_data(None)
        self.assertEqual(ConditionSection.HTTP_REQUEST_HEADER, data.object_name)
        self.assertFalse(data.object_available)
        self.assertIsNone(data.value)
        self.assertIsNone(data.available_keys)

        # Key not available
        data = condition.get_request_header_data(request_headers)
        self.assertEqual(ConditionSection.HTTP_REQUEST_HEADER, data.object_name)
        self.assertTrue(data.object_available)
        self.assertIsNone(data.value)
        self.assertTrue(isinstance(data.available_keys, list))

        # Everything available
        request_headers["User-Agent"] = "SpecialApp"
        data = condition.get_request_header_data(request_headers)
        self.assertEqual(ConditionSection.HTTP_REQUEST_HEADER, data.object_name)
        self.assertTrue(data.object_available)
        self.assertEqual("SpecialApp", data.value)
        self.assertIsNone(data.available_keys)

    def test_09_get_request_environment_data(self):
        condition = PolicyConditionClass(section=ConditionSection.HTTP_ENVIRONMENT, key="REQUEST_METHOD",
                                         comparator=PrimaryComparators.EQUALS, value="POST", active=True)
        request_headers = EnvironHeaders({})

        # Request header not available
        data = condition.get_request_header_data(None)
        self.assertEqual(ConditionSection.HTTP_ENVIRONMENT, data.object_name)
        self.assertFalse(data.object_available)
        self.assertIsNone(data.value)
        self.assertIsNone(data.available_keys)

        # Key not available
        data = condition.get_request_header_data(request_headers)
        self.assertEqual(ConditionSection.HTTP_ENVIRONMENT, data.object_name)
        self.assertTrue(data.object_available)
        self.assertIsNone(data.value)
        self.assertTrue(isinstance(data.available_keys, list))

        # Everything available
        request_headers = EnvironHeaders({"REQUEST_METHOD": "POST"})
        data = condition.get_request_header_data(request_headers)
        self.assertEqual(ConditionSection.HTTP_ENVIRONMENT, data.object_name)
        self.assertTrue(data.object_available)
        self.assertEqual("POST", data.value)
        self.assertIsNone(data.available_keys)

    def test_10_do_handle_missing_data_raise_error(self):
        # ---- Test for ConditionHandleMissingData.RAISE_ERROR ----
        condition = PolicyConditionClass(section=ConditionSection.TOKENINFO, key="hashlib",
                                         comparator=PrimaryComparators.EQUALS, value="sha256", active=True,
                                         handle_missing_data=ConditionHandleMissingData.RAISE_ERROR.value)
        # Token object not available
        error_message = (r"Policy 'test' has a condition on the section 'tokeninfo' with key 'hashlib', but a token is "
                         r"unavailable!")
        with self.assertRaisesRegex(PolicyError, error_message):
            condition._do_handle_missing_data(policy_name="test", missing="token", object_name="token")

        # Key not available
        error_message = r"Unknown tokeninfo key 'hashlib' referenced in condition of policy 'test'"
        with self.assertRaisesRegex(PolicyError, error_message):
            condition._do_handle_missing_data(policy_name="test", missing="hashlib", object_name="token",
                                              available_keys=["serial"])

        # missing parameter does not match object_name or key
        error_message = (r"Policy 'test' has a condition on the section 'tokeninfo' with key 'hashlib', but some "
                         r"required data is unavailable!")
        with self.assertRaisesRegex(PolicyError, error_message):
            condition._do_handle_missing_data(policy_name="test", missing="user", object_name="token")

    def test_11_do_handle_missing_data_is_true(self):
        # ---- Test for ConditionHandleMissingData.IS_TRUE ----
        condition = PolicyConditionClass(section=ConditionSection.TOKENINFO, key="hashlib",
                                         comparator=PrimaryComparators.EQUALS, value="sha256", active=True,
                                         handle_missing_data=ConditionHandleMissingData.IS_TRUE.value)
        # Token object not available
        self.assertTrue(condition._do_handle_missing_data(policy_name="test", missing="token", object_name="token"))

        # Key not available
        self.assertTrue(condition._do_handle_missing_data(policy_name="test", missing="hashlib", object_name="token",
                                                          available_keys=["serial"]))

        # missing parameter does not match object_name or key
        self.assertTrue(condition._do_handle_missing_data(policy_name="test", missing="user", object_name="token"))

    def test_12_do_handle_missing_data_is_false(self):
        # ---- Test for ConditionHandleMissingData.IS_FALSE ----
        condition = PolicyConditionClass(section=ConditionSection.TOKENINFO, key="hashlib",
                                         comparator=PrimaryComparators.EQUALS, value="sha256", active=True,
                                         handle_missing_data=ConditionHandleMissingData.IS_FALSE.value)
        # Token object not available
        self.assertFalse(condition._do_handle_missing_data(policy_name="test", missing="token", object_name="token"))

        # Key not available
        self.assertFalse(condition._do_handle_missing_data(policy_name="test", missing="hashlib", object_name="token",
                                                           available_keys=["serial"]))

        # missing parameter does not match object_name or key
        self.assertFalse(condition._do_handle_missing_data(policy_name="test", missing="user", object_name="token"))

        # Test that we did not miss to test an enum member
        tested_enums = {ConditionHandleMissingData.RAISE_ERROR, ConditionHandleMissingData.IS_FALSE,
                        ConditionHandleMissingData.IS_TRUE}
        self.assertSetEqual(set(ConditionHandleMissingData), tested_enums)

    def test_13_do_handle_missing_data_invalid(self):
        # ---- ConditionHandleMissingData is not defined ----
        # It should not be possible to reach this as the handle missing data is already checked in the
        # PolicyConditionClass. We can only get an invalid condition if it is inactive. The active flag is not
        # checked in the _do_handle_missing data function as it is already done in the filter_policies_by_conditions
        # function.
        ConditionHandleMissingData.RANDOM = "random"
        self.assertFalse(ConditionHandleMissingData.RANDOM in ConditionHandleMissingData.__members__)
        error_message = r"Unknown handle missing data random defined in condition of policy test."
        condition = PolicyConditionClass(section=ConditionSection.TOKENINFO, key="hashlib",
                                         comparator=PrimaryComparators.EQUALS, value="sha256", active=False,
                                         handle_missing_data=ConditionHandleMissingData.RANDOM, pass_if_inactive=True)
        with self.assertRaisesRegex(PolicyError, error_message):
            condition._do_handle_missing_data(policy_name="test", missing="token", object_name="token")

    def test_14_match_success(self):
        condition = PolicyConditionClass(section=ConditionSection.TOKEN, key="tokentype",
                                         comparator=PrimaryComparators.EQUALS, value="hotp", active=True,
                                         handle_missing_data=ConditionHandleMissingData.RAISE_ERROR.value)
        hotp = init_token({"type": "hotp", "genkey": True})
        totp = init_token({"type": "totp", "genkey": True})

        # condition is True
        self.assertTrue(condition.match("policy", None, hotp.get_serial(), None))

        # condition is False
        self.assertFalse(condition.match("policy", None, totp.get_serial(), None))

        # Inactive condition is always true
        condition.active = False
        self.assertTrue(condition.match("policy", None, hotp.get_serial(), None))
        self.assertTrue(condition.match("policy", None, totp.get_serial(), None))

        hotp.delete_token()
        totp.delete_token()

    def test_15_match_fails(self):
        condition = PolicyConditionClass(section=ConditionSection.TOKENINFO, key="count_auth",
                                         comparator=PrimaryComparators.BIGGER, value="3", active=True)

        token = init_token({"type": "hotp", "genkey": True})

        # object is missing
        with self.assertRaises(PolicyError):
            condition.match("policy", None, None, None)

        # Key not available
        with self.assertRaises(PolicyError):
            condition.match("policy", None, token.get_serial(), None)

        token.set_tokeninfo({"count_auth": "2"})

        # Comparison error
        condition.value = "3.5"
        with self.assertRaises(PolicyError):
            condition.match("policy", None, token.get_serial(), None)

        # Inactive condition is always true
        condition.active = False
        self.assertTrue(condition.match("policy", None, token.get_serial(), None))

        token.delete_token()

    def test_16_get_container_data_container(self):
        condition = PolicyConditionClass(section=ConditionSection.CONTAINER, key="type",
                                         comparator=PrimaryComparators.EQUALS, value="smartphone", active=True)
        container_serial = init_container({"type": "smartphone"})["container_serial"]

        # Everything available
        data = condition.get_container_data(container_serial)
        self.assertEqual("container", data.object_name)
        self.assertTrue(data.object_available)
        self.assertEqual("smartphone", data.value)
        self.assertIsNone(data.available_keys)

        # Key not available
        condition = PolicyConditionClass(section=ConditionSection.CONTAINER, key="hashlib",
                                         comparator=PrimaryComparators.EQUALS, value="sha256", active=True)
        data = condition.get_container_data(container_serial)
        self.assertEqual("container", data.object_name)
        self.assertTrue(data.object_available)
        self.assertIsNone(data.value)
        self.assertTrue(isinstance(data.available_keys, list))

        # container not available
        # no serial provided
        data = condition.get_container_data(None)
        self.assertEqual("container", data.object_name)
        self.assertFalse(data.object_available)
        self.assertIsNone(data.value)
        self.assertIsNone(data.available_keys)

        # invalid serial provided
        data = condition.get_container_data("invalid")
        self.assertEqual("container", data.object_name)
        self.assertFalse(data.object_available)
        self.assertIsNone(data.value)
        self.assertIsNone(data.available_keys)

    def test_17_get_container_data_container_info(self):
        condition = PolicyConditionClass(section=ConditionSection.CONTAINER_INFO, key="registration_state",
                                         comparator=PrimaryComparators.EQUALS,
                                         value=RegistrationState.CLIENT_WAIT.value,
                                         active=True)
        container_serial = init_container({"type": "smartphone"})["container_serial"]
        container = find_container_by_serial(container_serial)

        # Key not available
        data = condition.get_container_data(container_serial)
        self.assertEqual("container", data.object_name)
        self.assertTrue(data.object_available)
        self.assertIsNone(data.value)
        self.assertTrue(isinstance(data.available_keys, list))

        # Everything available
        container.set_container_info({"registration_state": RegistrationState.CLIENT_WAIT.value})
        data = condition.get_container_data(container_serial)
        self.assertEqual("container", data.object_name)
        self.assertTrue(data.object_available)
        self.assertEqual(RegistrationState.CLIENT_WAIT.value, data.value)
        self.assertIsNone(data.available_keys)

        # container not available
        # no serial provided
        data = condition.get_container_data(None)
        self.assertEqual("container", data.object_name)
        self.assertFalse(data.object_available)
        self.assertIsNone(data.value)
        self.assertIsNone(data.available_keys)

        # invalid serial provided
        data = condition.get_container_data("invalid")
        self.assertEqual("container", data.object_name)
        self.assertFalse(data.object_available)
        self.assertIsNone(data.value)
        self.assertIsNone(data.available_keys)

    def test_18_get_data_from_dict(self):
        condition = PolicyConditionClass(section=ConditionSection.REQUEST_DATA, key="type",
                                         comparator=PrimaryComparators.EQUALS, value="hotp", active=True)

        # Request data not available
        data = condition.get_data_from_dict(None)
        self.assertEqual(ConditionSection.REQUEST_DATA, data.object_name)
        self.assertFalse(data.object_available)
        self.assertIsNone(data.value)
        self.assertIsNone(data.available_keys)

        # Invalid data type for request data
        data = condition.get_data_from_dict("type: hotp")
        self.assertEqual(ConditionSection.REQUEST_DATA, data.object_name)
        self.assertFalse(data.object_available)
        self.assertIsNone(data.value)
        self.assertIsNone(data.available_keys)

        # Key not available
        request_data = {"user": "hans", "serial": "1234567890"}
        data = condition.get_data_from_dict(request_data)
        self.assertEqual(ConditionSection.REQUEST_DATA, data.object_name)
        self.assertTrue(data.object_available)
        self.assertIsNone(data.value)
        self.assertTrue(isinstance(data.available_keys, list))

        # Everything available
        request_data = {"user": "hans", "type": "hotp", "serial": "1234567890"}
        data = condition.get_data_from_dict(request_data)
        self.assertEqual(ConditionSection.REQUEST_DATA, data.object_name)
        self.assertTrue(data.object_available)
        self.assertEqual("hotp", data.value)
        self.assertIsNone(data.available_keys)


class ConditionHandleMissingDataTestCase(MyTestCase):

    def test_01_get_valid_values(self):
        # Check that all enum values are valid
        for enum in ConditionHandleMissingData:
            self.assertIn(enum.value, ConditionHandleMissingData.get_valid_values())

    def test_02_get_from_value(self):
        # valid value
        enum = ConditionHandleMissingData.get_from_value(ConditionHandleMissingData.IS_TRUE.value)
        self.assertEqual(ConditionHandleMissingData.IS_TRUE, enum)

        # invalid value
        with self.assertRaises(ParameterError) as exception:
            ConditionHandleMissingData.get_from_value("invalid_value")
            self.assertIn("Unknown handle missing data value", exception.exception.message)

    def test_03_get_selection_dict(self):
        # Check that all enum values are included in the selection dict
        enum_values = {member.value for member in ConditionHandleMissingData.__members__.values()}
        selection_dict = ConditionHandleMissingData.get_selection_dict()
        self.assertEqual(len(enum_values), len(selection_dict))
        for enum in enum_values:
            self.assertIn(enum, selection_dict)


class PolicyMatchTestCase(MyTestCase):
    def setUp(self):
        """ create some policies """
        MyTestCase.setUpClass()
        self.setUp_user_realms()
        self.setUp_user_realm2()
        set_policy(name="pol1",
                   action=ACTION.AUDIT,
                   scope=SCOPE.USER,
                   realm=self.realm1,
                   resolver=self.resolvername1,
                   user="foobar",
                   client="0.0.0.0/0",
                   active=True)
        set_policy(name="pol2",
                   action=f"{ACTION.TOKENTYPE}=HOTP",
                   scope=SCOPE.AUTHZ,
                   realm="*")
        set_policy(name="pol2a",
                   action=f"{ACTION.TOKENTYPE}=TOTP",
                   scope=SCOPE.AUTHZ,
                   realm=self.realm2)
        set_policy(name="pol3",
                   action=f"{ACTION.SERIAL}=OATH",
                   scope=SCOPE.AUTHZ,
                   realm=self.realm1,
                   resolver=self.resolvername1)
        set_policy(name="pol4",
                   action=f"enrollHOTP, {ACTION.DISABLE} , {ACTION.ENABLE}, {ACTION.AUDIT}",
                   scope=SCOPE.ADMIN,
                   realm=self.realm2,
                   adminuser="admin, superroot")

    def check_names(self, policies, names):
        self.assertSetEqual(set(names), set(p["name"] for p in policies))

    def test_01_action_only(self):
        g = FakeFlaskG()
        g.client_ip = "127.0.0.1"
        g.audit_object = mock.Mock()
        g.policy_object = PolicyClass()

        g.audit_object.audit_data = {}
        self.check_names(Match.action_only(g, SCOPE.AUTHZ, None).policies(),
                         {"pol2", "pol2a", "pol3"})
        self.assertSetEqual({"pol2", "pol2a", "pol3"}, set(g.audit_object.audit_data["policies"]))

        g.audit_object.audit_data = {}
        self.check_names(Match.action_only(g, SCOPE.AUTHZ, ACTION.TOKENTYPE).policies(),
                         {"pol2", "pol2a"})
        self.assertSetEqual({"pol2", "pol2a"}, set(g.audit_object.audit_data["policies"]))
        g.audit_object.audit_data = {}
        self.assertEqual(Match.action_only(g, SCOPE.AUTHZ, ACTION.TOKENTYPE).action_values(unique=False),
                         {"HOTP": ["pol2"], "TOTP": ["pol2a"]})
        self.assertSetEqual({"pol2", "pol2a"}, set(g.audit_object.audit_data["policies"]))

        g.audit_object.audit_data = {}
        self.check_names(Match.action_only(g, SCOPE.AUTHZ, ACTION.NODETAILSUCCESS).policies(),
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
        self.check_names(Match.realm(g, SCOPE.AUTHZ, ACTION.TOKENTYPE, None).policies(),
                         {"pol2", "pol2a"})
        self.check_names(Match.realm(g, SCOPE.AUTHZ, ACTION.TOKENTYPE, "realm1").policies(),
                         {"pol2"})
        self.check_names(Match.realm(g, SCOPE.AUTHZ, ACTION.TOKENTYPE, "realm2").policies(),
                         {"pol2", "pol2a"})
        self.check_names(Match.realm(g, SCOPE.AUTHZ, ACTION.TOKENTYPE, "realm3").policies(),
                         {"pol2"})
        self.check_names(Match.realm(g, SCOPE.AUTHZ, ACTION.SERIAL, "realm1").policies(),
                         {"pol3"})

        with self.assertRaises(MatchingError):
            Match.realm(g, SCOPE.ADMIN, ACTION.TOKENTYPE, "realm1")

    def test_03_user(self):
        g = FakeFlaskG()
        g.client_ip = "127.0.0.1"
        g.audit_object = mock.Mock()
        g.policy_object = PolicyClass()

        class Foobar(User):
            def __init__(self):
                self.login = "foobar"
                self.realm = "realm1"
                self.resolver = "resolver1"

        class Baz(User):
            def __init__(self):
                self.login = "baz"
                self.realm = "realm1"
                self.resolver = "resolver1"

        self.check_names(Match.user(g, SCOPE.USER, ACTION.AUDIT, Foobar()).policies(),
                         {"pol1"})
        self.check_names(Match.user(g, SCOPE.USER, ACTION.AUDIT, Baz()).policies(),
                         {})
        self.check_names(Match.user(g, SCOPE.USER, ACTION.AUDIT, None).policies(),
                         {"pol1"})

        with self.assertRaises(MatchingError):
            Match.user(g, SCOPE.ADMIN, ACTION.TOKENTYPE, Foobar())
        with self.assertRaises(MatchingError):
            Match.user(g, SCOPE.ADMIN, ACTION.TOKENTYPE, {"username": "bla", "realm": "foo", "role": ROLE.USER})

    def test_04_admin(self):
        g = FakeFlaskG()
        g.client_ip = "127.0.0.1"
        g.audit_object = mock.Mock()
        g.policy_object = PolicyClass()
        g.logged_in_user = {"username": "superroot", "realm": "", "role": ROLE.ADMIN}

        self.check_names(Match.admin(g, ACTION.ENABLE, None).policies(),
                         {"pol4"})
        self.check_names(Match.admin(g, ACTION.ENABLE, User("cornelius", "realm2")).policies(),
                         {"pol4"})
        self.check_names(Match.admin(g, ACTION.ENABLE, User("cornelius", "realm1")).policies(),
                         {})

        g.logged_in_user = {"username": "superroot", "realm": "", "role": ROLE.USER}
        with self.assertRaises(MatchingError):
            self.check_names(Match.admin(g, ACTION.ENABLE, User("cornelius", "realm1")).policies(),
                             {"pol4"})

    def test_05_admin_or_user(self):
        g = FakeFlaskG()
        g.client_ip = "127.0.0.1"
        g.audit_object = mock.Mock()
        g.policy_object = PolicyClass()

        g.logged_in_user = {"username": "superroot", "realm": "", "role": ROLE.ADMIN}
        self.check_names(Match.admin_or_user(g, ACTION.AUDIT, None).policies(),
                         {"pol4"})
        self.check_names(Match.admin_or_user(g, ACTION.AUDIT, User("cornelius", "realm2")).policies(),
                         {"pol4"})
        self.check_names(Match.admin_or_user(g, ACTION.AUDIT, User("cornelius", "realm1")).policies(),
                         {})

        g.logged_in_user = {"username": "foobar", "realm": "realm1", "role": ROLE.USER}
        # The user foobar@realm1 matches pol1
        self.check_names(Match.admin_or_user(g, ACTION.AUDIT, None).policies(),
                         {"pol1"})
        # A user in a different realm does not match!
        self.check_names(Match.admin_or_user(g, ACTION.AUDIT, User("cornelius", "realm2")).policies(),
                         {})
        # A wrong user in a realm does not match!
        self.check_names(Match.admin_or_user(g, ACTION.AUDIT, User("cornelius", "realm1")).policies(),
                         {})

        g.logged_in_user = {"username": "baz", "realm": "asdf", "role": ROLE.USER}
        self.check_names(Match.admin_or_user(g, ACTION.AUDIT, None).policies(),
                         {})

        g.logged_in_user = {"username": "baz", "realm": "asdf", "role": "something"}
        with self.assertRaises(MatchingError):
            self.check_names(Match.admin_or_user(g, ACTION.ENABLE, User("cornelius", "realm1")).policies(),
                             {"pol4"})

    @classmethod
    def tearDownClass(cls):
        delete_all_policies()
