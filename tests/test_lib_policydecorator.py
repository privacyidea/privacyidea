"""
This test file tests the lib.policy.py

The lib.policy.py only depends on the database model.
"""
PWFILE2 = "tests/testdata/passwords"

from .base import MyTestCase

from privacyidea.lib.policy import (set_policy, delete_policy,
                                    PolicyClass, SCOPE,
                                    ACTION, ACTIONVALUE)
from privacyidea.lib.policydecorators import policy_otppin
from privacyidea.lib.user import User
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.realm import set_realm
from privacyidea.lib.token import init_token, remove_token


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


class FakeFlaskG():
    policy_object = None


class LibPolicyTestCase(MyTestCase):
    """
    Test all the internal libpolicy decorators
    """
    def fake_check_otp(self, dummy, pin, user=None, options=None):
        return pin == "FAKE"

    def test_01_otppin(self):
        my_user = User("cornelius", realm="r1")
        set_policy(name="pol1",
                   scope=SCOPE.AUTH,
                   action="%s=%s" % (ACTION.OTPPIN, ACTIONVALUE.NONE))
        g = FakeFlaskG()
        P = PolicyClass()
        g.policy_object = P
        options = {"g": g}

        # NONE with empty PIN -> success
        r = policy_otppin(self.fake_check_otp, None,
                          "", options=options, user=my_user)
        self.assertTrue(r)
        # NONE with some pin -> fail
        r = policy_otppin(self.fake_check_otp, None,
                          "some pin", options=options, user=my_user)
        self.assertFalse(r)

        delete_policy("pol1")
        set_policy(name="pol1",
                   scope=SCOPE.AUTH,
                   action="%s=%s" % (ACTION.OTPPIN, ACTIONVALUE.TOKENPIN))
        g = FakeFlaskG()
        P = PolicyClass()
        g.policy_object = P
        options = {"g": g}

        r = policy_otppin(self.fake_check_otp, None,
                          "FAKE", options=options,
                          user=my_user)
        self.assertTrue(r)
        r = policy_otppin(self.fake_check_otp, None,
                          "Wrong Pin", options=options,
                          user=my_user)
        self.assertFalse(r)
        delete_policy("pol1")

    def test_02_userstore_password(self):
        # create a realm, where cornelius has a password test
        rid = save_resolver({"resolver": "myreso",
                             "type": "passwdresolver",
                             "fileName": PWFILE2})
        self.assertTrue(rid > 0, rid)

        (added, failed) = set_realm("r1", ["myreso"])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 1)

        # now create a policy with userstore PW
        set_policy(name="pol1",
                   scope=SCOPE.AUTH,
                   action="%s=%s" % (ACTION.OTPPIN, ACTIONVALUE.USERSTORE))
        g = FakeFlaskG()
        P = PolicyClass()
        g.policy_object = P
        options = {"g": g}

        # Wrong password
        r = policy_otppin(self.fake_check_otp, None,
                          "WrongPW", options=options,
                          user=User("cornelius", realm="r1"))
        self.assertFalse(r)

        # Correct password from userstore: "test"
        r = policy_otppin(self.fake_check_otp, None,
                          "test", options=options,
                          user=User("cornelius", realm="r1"))
        self.assertTrue(r)
        delete_policy("pol1")

    def test_03_otppin_for_serial(self):
        # now create a policy with userstore PW
        set_policy(name="pol1",
                   scope=SCOPE.AUTH,
                   action="%s=%s" % (ACTION.OTPPIN, ACTIONVALUE.USERSTORE))
        g = FakeFlaskG()
        P = PolicyClass()
        g.policy_object = P
        options = {"g": g,
                   "serial": "T001"}

        # create a token and assign to user cornelius
        token = init_token({"serial": "T001", "type": "hotp", "genkey": 1},
                           user=User("cornelius", realm="r1"))
        self.assertTrue(token)

        # Wrong password
        # Not identified by the user but by the token owner
        r = policy_otppin(self.fake_check_otp, token,
                          "WrongPW", options=options,
                          user=None)
        self.assertFalse(r)

        # Correct password from userstore: "test"
        # Not identified by the user but by the token owner
        r = policy_otppin(self.fake_check_otp, token,
                          "test", options=options,
                          user=None)
        self.assertTrue(r)
        delete_policy("pol1")
