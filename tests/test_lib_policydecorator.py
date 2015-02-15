"""
This test file tests the lib.policy.py

The lib.policy.py only depends on the database model.
"""
PWFILE2 = "tests/testdata/passwords"

from .base import MyTestCase

from privacyidea.lib.policy import (set_policy, delete_policy,
                                    PolicyClass, SCOPE,
                                    ACTION, ACTIONVALUE)
from privacyidea.lib.policydecorators import (auth_otppin,
                                              auth_user_does_not_exist,
                                              auth_user_passthru,
                                              auth_user_has_no_token)
from privacyidea.lib.user import User
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.realm import set_realm
from privacyidea.lib.token import init_token, remove_token, check_user_pass
from privacyidea.lib.error import UserError


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
        r = auth_otppin(self.fake_check_otp, None,
                          "", options=options, user=my_user)
        self.assertTrue(r)
        # NONE with some pin -> fail
        r = auth_otppin(self.fake_check_otp, None,
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

        r = auth_otppin(self.fake_check_otp, None,
                          "FAKE", options=options,
                          user=my_user)
        self.assertTrue(r)
        r = auth_otppin(self.fake_check_otp, None,
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
        r = auth_otppin(self.fake_check_otp, None,
                          "WrongPW", options=options,
                          user=User("cornelius", realm="r1"))
        self.assertFalse(r)

        # Correct password from userstore: "test"
        r = auth_otppin(self.fake_check_otp, None,
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
        r = auth_otppin(self.fake_check_otp, token,
                          "WrongPW", options=options,
                          user=None)
        self.assertFalse(r)

        # Correct password from userstore: "test"
        # Not identified by the user but by the token owner
        r = auth_otppin(self.fake_check_otp, token,
                          "test", options=options,
                          user=None)
        self.assertTrue(r)
        delete_policy("pol1")
        remove_token("T001")

    def test_04_user_does_not_exist(self):
        user = User("MisterX", realm="NoRealm")
        passw = "wrongPW"
        options = {}
        # A non-existing user will fail to authenticate without a policy
        self.assertRaises(UserError, auth_user_does_not_exist,
                          check_user_pass, user, passw, options)

        # Now we set a policy, that a non existing user will authenticate
        set_policy(name="pol1",
                   scope=SCOPE.AUTH,
                   action=ACTION.PASSNOUSER)
        g = FakeFlaskG()
        g.policy_object = PolicyClass()
        options = {"g": g}
        rv = auth_user_does_not_exist(check_user_pass, user, passw,
                                        options=options)
        self.assertTrue(rv[0])
        self.assertEqual(rv[1].get("message"),
                         u"The user does not exist, but is accepted due "
                         u"to policy 'pol1'.")
        delete_policy("pol1")

    def test_05_user_has_no_tokens(self):
        user = User("cornelius", realm="r1")
        passw = "test"
        options = {}
        # A user with no tokens will fail to authenticate
        rv = auth_user_has_no_token(check_user_pass, user, passw, options)
        self.assertFalse(rv[0])
        self.assertEqual(rv[1].get("message"),
                         "The user has no tokens assigned")

        # Now we set a policy, that a non existing user will authenticate
        set_policy(name="pol1",
                   scope=SCOPE.AUTH,
                   action=ACTION.PASSNOTOKEN)
        g = FakeFlaskG()
        g.policy_object = PolicyClass()
        options = {"g": g}
        rv = auth_user_has_no_token(check_user_pass, user, passw,
                                      options=options)
        self.assertTrue(rv[0])
        self.assertEqual(rv[1].get("message"),
                         u"The user has not token, but is accepted due to "
                         u"policy 'pol1'.")
        delete_policy("pol1")

    def test_06_passthru(self):
        user = User("cornelius", realm="r1")
        passw = "test"
        options = {}
        # A user with no tokens will fail to authenticate
        rv = auth_user_passthru(check_user_pass, user, passw, options)
        self.assertFalse(rv[0])
        self.assertEqual(rv[1].get("message"),
                         "The user has no tokens assigned")

        # Now we set a PASSTHRU policy, so that the user may authenticate
        # against his userstore
        set_policy(name="pol1",
                   scope=SCOPE.AUTH,
                   action=ACTION.PASSTHRU)
        g = FakeFlaskG()
        g.policy_object = PolicyClass()
        options = {"g": g}
        rv = auth_user_has_no_token(check_user_pass, user, passw,
                                      options=options)
        self.assertTrue(rv[0])
        self.assertEqual(rv[1].get("message"),
                         u"The user authenticated against his userstore "
                         u"according to policy 'pol1'.")
        delete_policy("pol1")
