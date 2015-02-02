"""
This test file tests the lib.policy.py

The lib.poliy.py only depends on the database model.
"""
import json
from .base import MyTestCase

from privacyidea.lib.policy import (set_policy, get_policies, delete_policy,
                                    import_policies, export_policies,
                                    get_static_policy_definitions)


class PolicyTestCase(MyTestCase):
    """
    Test the policies on a database level
    """

    def test_01_create_policy(self):
        p = set_policy(name="pol1", action="read", scope="system")
        self.assertTrue(p > 0)

        p = set_policy(name="pol2", action="read", scope="system")
        self.assertTrue(p > 0)

        p = set_policy(name="pol3", action="read", scope="system")
        self.assertTrue(p > 0)

        p = set_policy(name="pol4", action="read", scope="system")
        self.assertTrue(p > 0)

    def test_02_update_policy(self):
        p = set_policy(name="pol4", action="write", scope="admin")
        self.assertTrue(p > 0)

    def test_03_get_policy(self):
        pols = get_policies()
        self.assertTrue("pol1" in pols, pols)
        self.assertTrue("pol2" in pols, pols)
        self.assertTrue("pol3" in pols, pols)
        self.assertTrue("pol4" in pols, pols)

        self.assertTrue(pols.get("pol4").get("scope") == "admin", pols.get(
            "pol4"))

        pol4 = get_policies(name="pol4", realm="", scope="admin", active=True)
        self.assertTrue("pol4" in pol4, pol4)
        self.assertTrue("pol1" not in pol4, pol4)

        # A resolver is not specified in any policy, so the given resolver
        # matches all policies
        p = get_policies(resolver="reso")
        self.assertTrue(len(p) == 4, p)
        # A user is not specified in any policy, so the given user matches
        # all policies
        p = get_policies(user="user")
        self.assertTrue(len(p) == 4, p)

    def test_04_delete_policy(self):
        delete_policy(name="pol4")
        pol4 = get_policies(name="pol4")
        self.assertTrue(pol4 == {}, pol4)

    def test_05_export_policies(self):
        file = export_policies(get_policies())
        self.assertTrue("[pol1]" in file, file)
        self.assertTrue("[pol2]" in file, file)
        self.assertTrue("[pol3]" in file, file)

    def test_06_import_policies(self):
        file = export_policies(get_policies())
        delete_policy("pol1")
        delete_policy("pol2")
        delete_policy("pol3")
        policies = get_policies()
        self.assertTrue("pol1" not in policies, policies)
        self.assertTrue("pol2" not in policies, policies)
        self.assertTrue("pol3" not in policies, policies)
        # Now import the policies again
        num = import_policies(file)
        self.assertTrue(num == 3, num)
        policies = get_policies()
        self.assertTrue("pol1" in policies, policies)
        self.assertTrue("pol2" in policies, policies)
        self.assertTrue("pol3" in policies, policies)

    def test_07_client_policies(self):
        set_policy(name="pol1", scope="s", client="172.16.0.3, 172.16.0.4/24")
        set_policy(name="pol2", scope="s", client="192.168.0.0/16, "
                                                  "-192.168.1.1")
        set_policy(name="pol3", scope="s", client="10.0.0.1, 10.0.0.2, "
                                                  "10.0.0.3")
        set_policy(name="pol4", scope="s")

        # One policy with matching client, one without any clients
        p = get_policies(client="10.0.0.1")
        self.assertTrue("pol3" in p, p)
        self.assertTrue("pol4" in p, p)
        self.assertTrue(len(p) == 2, p)

        # client matches pol4 and pol2
        p = get_policies(client="192.168.2.3")
        self.assertTrue("pol2" in p, p)
        self.assertTrue("pol4" in p, p)
        self.assertTrue(len(p) == 2, p)

        # client only matches pol4, since it is excluded in pol2
        p = get_policies(client="192.168.1.1")
        self.assertTrue("pol4" in p, p)
        self.assertTrue(len(p) == 1, p)

    def test_08_user_policies(self):
        set_policy(name="pol1", scope="s", user="*")
        set_policy(name="pol2", scope="s", user="admin, root, user1")
        set_policy(name="pol3", scope="s", user="*, !user1")
        set_policy(name="pol4", scope="s", user="*, -root")

        # get policies for user1
        p = get_policies(user="user1")
        self.assertTrue(len(p) == 3, (len(p), p))
        self.assertTrue("pol1" in p, p)
        self.assertTrue("pol2" in p, p)
        self.assertFalse("pol3" in p, p)
        self.assertTrue("pol4" in p, p)
        # get policies for root
        p = get_policies(user="root")
        self.assertTrue(len(p) == 3, p)
        self.assertTrue("pol1" in p, p)
        self.assertTrue("pol2" in p, p)
        self.assertTrue("pol3" in p, p)
        self.assertFalse("pol4" in p, p)
        # get policies for admin
        p = get_policies(user="admin")
        self.assertTrue(len(p) == 4, p)
        self.assertTrue("pol1" in p, p)
        self.assertTrue("pol2" in p, p)
        self.assertTrue("pol3" in p, p)
        self.assertTrue("pol4" in p, p)

    def test_09_realm_resolver_policy(self):
        set_policy(name="pol1", scope="s", realm="r1")
        set_policy(name="pol2", scope="s", realm="r1", resolver="reso1")
        set_policy(name="pol3", scope="s", resolver="reso2")
        set_policy(name="pol4", scope="s", realm="r2")

        p = get_policies(realm="r1")
        self.assertTrue(len(p) == 3, p)
        self.assertTrue("pol1" in p, p)
        self.assertTrue("pol2" in p, p)
        self.assertTrue("pol3" in p, p)
        self.assertFalse("pol4" in p, p)

        p = get_policies(realm="r2")
        self.assertTrue(len(p) == 2, p)
        self.assertFalse("pol1" in p, p)
        self.assertFalse("pol2" in p, p)
        self.assertTrue("pol3" in p, p)
        self.assertTrue("pol4" in p, p)

        p = get_policies(resolver="reso1")
        self.assertTrue(len(p) == 3, p)
        self.assertTrue("pol1" in p, p)
        self.assertTrue("pol2" in p, p)
        self.assertFalse("pol3" in p, p)
        self.assertTrue("pol4" in p, p)

        p = get_policies(resolver="reso2")
        self.assertTrue(len(p) == 3, p)
        self.assertTrue("pol1" in p, p)
        self.assertFalse("pol2" in p, p)
        self.assertTrue("pol3" in p, p)
        self.assertTrue("pol4" in p, p)

    def test_10_action_policies(self):
        set_policy(name="pol1", action="enroll, init, disable")
        set_policy(name="pol2", action="enroll, otppin=1")
        set_policy(name="pol3", action="*, -disable")
        set_policy(name="pol4", action="*, -otppin=2")

        p = get_policies(action="enroll")
        self.assertTrue(len(p) == 4, (len(p), p))

        p = get_policies(action="init")
        self.assertTrue(len(p) == 3, (len(p), p))

        p = get_policies(action="disable")
        self.assertTrue(len(p) == 2, (len(p), p))

        p = get_policies(action="otppin")
        self.assertTrue(len(p) == 2, (len(p), p))

    def test_11_get_policy_definitions(self):
        p = get_static_policy_definitions()
        self.assertTrue("admin" in p, p)

        p = get_static_policy_definitions(scope="admin")
        self.assertTrue("enable" in p, p)
