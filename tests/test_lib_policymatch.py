# coding: utf-8
"""
This test file tests the lib/policymatch.py
"""
from mock import Mock

from privacyidea.lib.auth import ROLE
from privacyidea.lib.user import User
from privacyidea.lib.policy import MatchingError, Match
from privacyidea.lib.policy import set_policy, SCOPE, delete_all_policies, PolicyClass
from .base import MyTestCase, FakeFlaskG


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
                   user="admin, superroot")

    def check_names(self, policies, names):
        self.assertEqual(set(p["name"] for p in policies), set(names))

    def test_01_action_only(self):
        g = FakeFlaskG()
        g.client_ip = "127.0.0.1"
        g.audit_object = Mock()
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
        g.audit_object = Mock()
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
        g.audit_object = Mock()
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
        g.audit_object = Mock()
        g.policy_object = PolicyClass()
        g.logged_in_user = {"username": "superroot", "realm": "", "role": ROLE.ADMIN}

        self.check_names(Match.admin(g, "enable", None).policies(),
                         {"pol4"})
        self.check_names(Match.admin(g, "enable", "realm2").policies(),
                         {"pol4"})
        self.check_names(Match.admin(g, "enable", "realm1").policies(),
                         {})

        g.logged_in_user = {"username": "superroot", "realm": "", "role": ROLE.USER}
        with self.assertRaises(MatchingError):
            self.check_names(Match.admin(g, "enable", "realm1").policies(),
                             {"pol4"})

    def test_05_admin_or_user(self):
        g = FakeFlaskG()
        g.client_ip = "127.0.0.1"
        g.audit_object = Mock()
        g.policy_object = PolicyClass()

        g.logged_in_user = {"username": "superroot", "realm": "", "role": ROLE.ADMIN}
        self.check_names(Match.admin_or_user(g, "audit", None).policies(),
                         {"pol4"})
        self.check_names(Match.admin_or_user(g, "audit", "realm2").policies(),
                         {"pol4"})
        self.check_names(Match.admin_or_user(g, "audit", "realm1").policies(),
                         {})

        g.logged_in_user = {"username": "foobar", "realm": "asdf", "role": ROLE.USER}
        self.check_names(Match.admin_or_user(g, "audit", None).policies(),
                         {"pol1"})
        self.check_names(Match.admin_or_user(g, "audit", "realm2").policies(),
                         {})
        self.check_names(Match.admin_or_user(g, "audit", "realm1").policies(),
                         {"pol1"})

        g.logged_in_user = {"username": "baz", "realm": "asdf", "role": ROLE.USER}
        self.check_names(Match.admin_or_user(g, "audit", None).policies(),
                         {})

        g.logged_in_user = {"username": "baz", "realm": "asdf", "role": "something"}
        with self.assertRaises(MatchingError):
            self.check_names(Match.admin_or_user(g, "enable", "realm1").policies(),
                             {"pol4"})

    @classmethod
    def tearDownClass(cls):
        delete_all_policies()
