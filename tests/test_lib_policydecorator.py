"""
This test file tests the lib.policy.py

The lib.policy.py only depends on the database model.
"""
PWFILE2 = "tests/testdata/passwords"
DICT_FILE = "tests/testdata/dictionary"


from .base import MyTestCase, FakeFlaskG

from privacyidea.lib.policy import (set_policy, delete_policy,
                                    PolicyClass, SCOPE,
                                    ACTION, ACTIONVALUE, LOGINMODE)
from privacyidea.lib.policydecorators import (auth_otppin,
                                              auth_user_does_not_exist,
                                              auth_user_passthru,
                                              auth_user_has_no_token,
                                              login_mode, config_lost_token,
                                              challenge_response_allowed,
                                              auth_user_timelimit,
                                              auth_lastauth)
from privacyidea.lib.user import User
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.realm import set_realm
from privacyidea.lib.token import (init_token, remove_token, check_user_pass,
                                   get_tokens)
from privacyidea.lib.error import UserError, PolicyError
from privacyidea.lib.radiusserver import add_radius
import datetime
import radiusmock


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


class LibPolicyTestCase(MyTestCase):
    """
    Test all the internal libpolicy decorators
    """
    @staticmethod
    def fake_check_otp(dummy, pin, user=None, options=None):
        return pin == "FAKE"

    def test_01_otppin(self):
        my_user = User("cornelius", realm="r1")
        set_policy(name="pol1",
                   scope=SCOPE.AUTH,
                   action="{0!s}={1!s}".format(ACTION.OTPPIN, ACTIONVALUE.NONE))
        g = FakeFlaskG()
        P = PolicyClass()
        g.policy_object = P
        options = {"g": g}

        # NONE with empty PIN -> success
        r = auth_otppin(self.fake_check_otp, None,
                        "", options=options, user=my_user)
        self.assertTrue(r)
        # NONE with empty PIN -> success, even if the authentication is done
        # for a serial and not a user, since the policy holds for all realms
        token = init_token({"type": "HOTP", "otpkey": "1234"})
        r = auth_otppin(self.fake_check_otp, token,
                        "", options=options, user=None)
        self.assertTrue(r)

        # NONE with some pin -> fail
        r = auth_otppin(self.fake_check_otp, None,
                        "some pin", options=options, user=my_user)
        self.assertFalse(r)

        delete_policy("pol1")
        set_policy(name="pol1",
                   scope=SCOPE.AUTH,
                   action="{0!s}={1!s}".format(ACTION.OTPPIN, ACTIONVALUE.TOKENPIN))
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
                   action="{0!s}={1!s}".format(ACTION.OTPPIN, ACTIONVALUE.USERSTORE))
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
                   action="{0!s}={1!s}".format(ACTION.OTPPIN, ACTIONVALUE.USERSTORE))
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
                         u"The user has no token, but is accepted due to "
                         u"policy 'pol1'.")
        delete_policy("pol1")

    @radiusmock.activate
    def test_06_passthru(self):
        user = User("cornelius", realm="r1")
        passw = "test"
        options = {}
        # A user with no tokens will fail to authenticate
        self.assertEqual(get_tokens(user=user, count=True), 0)
        rv = auth_user_passthru(check_user_pass, user, passw, options)
        self.assertFalse(rv[0])
        self.assertEqual(rv[1].get("message"),
                         "The user has no tokens assigned")

        # Now we set a PASSTHRU policy, so that the user may authenticate
        # against his userstore (old style)
        set_policy(name="pol1",
                   scope=SCOPE.AUTH,
                   action=ACTION.PASSTHRU)
        g = FakeFlaskG()
        g.policy_object = PolicyClass()
        options = {"g": g}
        rv = auth_user_passthru(check_user_pass, user, passw,
                                options=options)
        self.assertTrue(rv[0])
        self.assertEqual(rv[1].get("message"),
                         u"The user authenticated against his userstore "
                         u"according to policy 'pol1'.")

        # Now set a PASSTHRU policy to the userstore (new style)
        set_policy(name="pol1",
                   scope=SCOPE.AUTH,
                   action="{0!s}=userstore".format(ACTION.PASSTHRU))
        g = FakeFlaskG()
        g.policy_object = PolicyClass()
        options = {"g": g}
        rv = auth_user_passthru(check_user_pass, user, passw,
                                options=options)
        self.assertTrue(rv[0])
        self.assertEqual(rv[1].get("message"),
                         u"The user authenticated against his userstore "
                         u"according to policy 'pol1'.")

        # Now set a PASSTHRU policy to a RADIUS config (new style)
        radiusmock.setdata(success=True)
        set_policy(name="pol1",
                   scope=SCOPE.AUTH,
                   action="{0!s}=radiusconfig1".format(ACTION.PASSTHRU))
        r = add_radius("radiusconfig1", "1.2.3.4", "testing123",
                       dictionary=DICT_FILE)
        self.assertTrue(r > 0)
        g = FakeFlaskG()
        g.policy_object = PolicyClass()
        options = {"g": g}
        rv = auth_user_passthru(check_user_pass, user, passw,
                                options=options)
        self.assertTrue(rv[0])
        self.assertEqual(rv[1].get("message"),
                         u"The user authenticated against the RADIUS server "
                         u"radiusconfig1 according to policy 'pol1'.")

        # Now assign a token to the user. If the user has a token and the
        # passthru policy is set, the user must not be able to authenticate
        # with his userstore password.
        init_token({"serial": "PTHRU",
                    "type": "spass", "pin": "Hallo"},
                   user=user)
        rv = auth_user_passthru(check_user_pass, user, passw,
                                options=options)
        self.assertFalse(rv[0])
        self.assertEqual(rv[1].get("message"), "wrong otp pin")

        remove_token("PTHRU")
        delete_policy("pol1")

    def test_07_login_mode(self):
        # a realm: cornelius@r1: PW: test

        def check_webui_user_userstore(user_obj, password,
                                       options=None, superuser_realms=None,
                                       check_otp=False):
            self.assertEqual(check_otp, False)

        def check_webui_user_privacyidea(user_obj, password,
                                         options=None, superuser_realms=None,
                                         check_otp=False):
            self.assertEqual(check_otp, True)

        user_obj = User("cornelius", "r1")

        g = FakeFlaskG()
        P = PolicyClass()
        g.policy_object = P
        options = {"g": g}

        # No policy, the function is called with check_otp=False
        login_mode(check_webui_user_userstore, user_obj, "",
                   options=options, superuser_realms="", check_otp=False)

        set_policy(name="pol2",
                   scope=SCOPE.WEBUI,
                   action="{0!s}={1!s}".format(ACTION.LOGINMODE, LOGINMODE.PRIVACYIDEA))
        g = FakeFlaskG()
        P = PolicyClass()
        g.policy_object = P
        options = {"g": g}

        # Policy is set, the function is called with check_otp=True
        login_mode(check_webui_user_privacyidea, user_obj, "",
                   options=options, superuser_realms="", check_otp=False)

        # Set policy, so that the user is not allowed to login at all
        set_policy(name="pol2",
                   scope=SCOPE.WEBUI,
                   action="{0!s}={1!s}".format(ACTION.LOGINMODE, LOGINMODE.DISABLE))
        g = FakeFlaskG()
        P = PolicyClass()
        g.policy_object = P
        options = {"g": g}

        # Policy is set. Trying to login raises a policy error
        self.assertRaises(PolicyError, login_mode,
                          check_webui_user_privacyidea, user_obj, "",
                          options=options, superuser_realms="",
                          check_otp=False)
        delete_policy("pol2")

    def test_08_config_lost_token_policy(self):

        def func1(serial, validity=10, contents="Ccns", pw_len=16,
                  options=None):
            self.assertEqual(validity, 10)
            self.assertEqual(contents, "Ccns")
            self.assertEqual(pw_len, 16)

        def func2(serial, validity=10, contents="Ccns", pw_len=16,
                  options=None):
            self.assertEqual(validity, 5)
            self.assertEqual(contents, "C")
            self.assertEqual(pw_len, 3)

        init_token({"serial": "LOST001", "type": "hotp", "genkey": 1},
                   user=User("cornelius", realm="r1"))

        g = FakeFlaskG()
        P = PolicyClass()
        g.policy_object = P
        options = {"g": g}

        # No policy, the function is called with default values
        config_lost_token(func1, "LOST001", options=options)

        set_policy(name="lost_pol2",
                   scope=SCOPE.ENROLL,
                   action="%s=%s, %s=%s,"
                          "%s=%s" % (ACTION.LOSTTOKENPWCONTENTS, "C",
                                     ACTION.LOSTTOKENVALID, 5,
                                     ACTION.LOSTTOKENPWLEN, 3))
        g = FakeFlaskG()
        P = PolicyClass()
        g.policy_object = P
        options = {"g": g}

        # Policy is set, the function is called with check_otp=True
        config_lost_token(func2, "LOST001", options=options)

    def test_09_challenge_response_allowed(self):
        user = User("cornelius", realm="r1")
        pin = "test"

        g = FakeFlaskG()
        g.policy_object = PolicyClass()
        options = {"g": g}
        token = init_token({"type": "hotp",
                            "otpkey": "1234",
                            "pin": pin}, user=user)
        # With no policy, it will be no chal resp
        rv = token.is_challenge_request(pin, user=user, options=options)
        self.assertEqual(rv, False)

        # Now we set a policy with several tokentypes
        set_policy(name="pol_chal_resp_1",
                   scope=SCOPE.AUTH,
                   action="{0!s}=hotp tiqr totp".format(ACTION.CHALLENGERESPONSE))
        set_policy(name="pol_chal_resp_2",
                   scope=SCOPE.AUTH,
                   action="{0!s}=hotp motp".format(ACTION.CHALLENGERESPONSE))
        g = FakeFlaskG()
        g.policy_object = PolicyClass()
        options = {"g": g}
        rv = token.is_challenge_request(pin, user=user, options=options)
        self.assertEqual(rv, True)
        delete_policy("pol_chal_resp_1")

    def test_10_auth_lastauth(self):
        serial = "SPASSLASTAUTH"
        pin = "secretpin"

        def fake_auth_missing_serial(user, pin, options=None):
            return True, {}

        def fake_auth(user, pin, options):
            return True, {"serial": serial}

        user = User("cornelius", realm="r1")
        init_token({"type": "spass",
                    "pin": pin,
                    "serial": serial}, user=user)

        # set time limit policy
        set_policy(name="pol_lastauth",
                   scope=SCOPE.AUTHZ,
                   action="{0!s}=1d".format(ACTION.LASTAUTH))
        g = FakeFlaskG()
        g.policy_object = PolicyClass()
        options = {"g": g}

        rv = auth_lastauth(fake_auth, user, pin, options)
        self.assertEqual(rv[0], True)

        token = get_tokens(serial=serial)[0]
        # Set a very old last_auth
        token.add_tokeninfo(ACTION.LASTAUTH,
                            datetime.datetime.utcnow()-datetime.timedelta(days=2))
        rv = auth_lastauth(fake_auth, user, pin, options)
        self.assertEqual(rv[0], False)
        self.assertTrue("The last successful authentication was" in
                        rv[1].get("message"), rv[1])

        remove_token(serial)
        delete_policy("pol_lastauth")
