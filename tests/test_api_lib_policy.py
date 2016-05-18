"""
This test file tests the api.lib.policy.py

The api.lib.policy.py depends on lib.policy and on flask!
"""
import json
from .base import (MyTestCase, PWFILE)

from privacyidea.lib.policy import (set_policy, delete_policy,
                                    PolicyClass, SCOPE, ACTION, REMOTE_USER,
                                    AUTOASSIGNVALUE)
from privacyidea.api.lib.prepolicy import (check_token_upload,
                                           check_base_action, check_token_init,
                                           check_max_token_user,
                                           check_anonymous_user,
                                           check_max_token_realm, set_realm,
                                           init_tokenlabel, init_random_pin,
                                           init_token_defaults,
                                           encrypt_pin, check_otp_pin,
                                           check_external, api_key_required,
                                           mangle, is_remote_user_allowed,
                                           required_email)
from privacyidea.api.lib.postpolicy import (check_serial, check_tokentype,
                                            no_detail_on_success,
                                            no_detail_on_fail, autoassign,
                                            offline_info, sign_response,
                                            get_webui_settings)
from privacyidea.lib.token import (init_token, get_tokens, remove_token,
                                   set_realms, check_user_pass, unassign_token)
from privacyidea.lib.user import User

from flask import Response, Request, g, current_app
from werkzeug.test import EnvironBuilder
from privacyidea.lib.error import PolicyError, RegistrationError
from privacyidea.lib.machineresolver import save_resolver
from privacyidea.lib.machine import attach_token
from privacyidea.lib.auth import ROLE
import jwt
from datetime import datetime, timedelta


HOSTSFILE = "tests/testdata/hosts"
SSHKEY = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDO1rx366cmSSs/89j" \
         "/0u5aEiXa7bYArHn7zFNCBaVnDUiK9JDNkpWBj2ucbmOpDKWzH0Vl3in21E" \
         "8BaRlq9AobASG0qlEqlnwrYwlH+vcYp6td4QBoh3sOelzhyrJFug9dnfe8o7" \
         "0r3IL4HIbdQOdh1b8Ogi7aL01V/eVE9RgGfTNHUzuYRMUL3si4dtqbCsSjFZ" \
         "6dN1nnVhos9cSphPr7pQEbq8xW0uxzOGrFDY9g1NSOleA8bOjsCT9k+3X4R7" \
         "00iVGvpzWkKopcWrzXJDIa3yxylAMOM0c3uO9U3NLfRsucvcQ5Cs8S6ctM30" \
         "8cua3t5WaBOsr3RyoXs+cHIPIkXnJHg03HsnWONaGxl8VPymC9s3P0zVwm2jMFx" \
         "JD9WbBqep7Dwc5unxLOSKidKrnNflQiMyiIv+5dY5lhc0YTJdktC2Scse64ac2E" \
         "7ldjG3bJuKSIWAz8Sd1km4ZJWWIx8NlpC9AfbHcgMyFUDniV1EtFIaSQLPspIk" \
         "thzIMqPTpKblzdRZP37mPu/FpwfYG4S+F34dCmJ4BipslsVcqgCFJQHoAYAJc4N" \
         "Dq5IRDQqXH2KybHpSLATnbSY7zjVD+evJeU994yTaXTFi5hBmd0aWTC+ph79mmE" \
         "tu3dokA2YbLa7uWkAIXvX/HHauGLMTyCOpYi1BxN47c/kccxyNg" \
         "jPw== corny@schnuck"


class PrePolicyDecoratorTestCase(MyTestCase):

    def test_01_check_token_action(self):
        g.logged_in_user = {"username": "admin1",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"serial": "SomeSerial"}

        # Set a policy, that does allow the action
        set_policy(name="pol1",
                   scope=SCOPE.ADMIN,
                   action="enable", client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        # Action enable is cool
        r = check_base_action(request=req, action="enable")
        self.assertTrue(r)

        # Another action - like "disable" - is not allowed
        # An exception is
        self.assertRaises(PolicyError,
                          check_base_action, req, "disable")

        # Action delete is not allowed
        self.assertRaises(PolicyError,
                          check_base_action, req, "delete")

        # check action with a token realm
        set_policy(name="pol1",
                   scope=SCOPE.ADMIN,
                   action="enable", client="10.0.0.0/8",
                   realm="realm1")
        set_policy(name="pol2",
                   scope=SCOPE.ADMIN,
                   action="*", client="10.0.0.0/8",
                   realm="realm2")
        g.policy_object = PolicyClass()
        # set a polrealm1 and a polrealm2
        # setup realm1
        self.setUp_user_realms()
        # setup realm2
        self.setUp_user_realm2()
        tokenobject = init_token({"serial": "POL001", "type": "hotp",
                                  "otpkey": "1234567890123456"})
        r = set_realms("POL001", [self.realm1])

        tokenobject = init_token({"serial": "POL002", "type": "hotp",
                                  "otpkey": "1234567890123456"})
        r = set_realms("POL002", [self.realm2])

        # Token in realm1 can not be deleted
        req.all_data = {"serial": "POL001"}
        self.assertRaises(PolicyError,
                          check_base_action, req, "delete")
        # while token in realm2 can be deleted
        req.all_data = {"serial": "POL002"}
        r = check_base_action(req, action="delete")
        self.assertTrue(r)

        # A normal user can "disable", since no user policies are defined.
        g.logged_in_user = {"username": "user1",
                            "role": "user"}
        r = check_base_action(req, "disable")
        self.assertTrue(r)
        delete_policy("pol1")
        delete_policy("pol2")
        remove_token("POL001")
        remove_token("POL002")

    def test_01a_admin_realms(self):
        admin1 = {"username": "admin1",
                  "role": "admin",
                  "realm": "realm1"}

        admin2 = {"username": "admin1",
                  "role": "admin",
                  "realm": "realm2"}

        set_policy(name="pol",
                   scope=SCOPE.ADMIN,
                   action="*", adminrealm="realm1")
        g.policy_object = PolicyClass()
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {}

        # admin1 is allowed to do everything
        g.logged_in_user = admin1
        r = check_base_action(req, action="delete")
        self.assertTrue(r)

        # admin2 is not allowed.
        g.logged_in_user = admin2
        self.assertRaises(PolicyError, check_base_action, req, action="delete")
        delete_policy("pol")

    def test_02_check_token_init(self):
        g.logged_in_user = {"username": "admin1",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"type": "totp"}

        # Set a policy, that does allow the action
        set_policy(name="pol1",
                   scope=SCOPE.ADMIN,
                   action="enrollTOTP, enrollHOTP",
                   client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        # Enrolling TOTP is cool
        r = check_token_init(req)
        self.assertTrue(r)

        # Another Token type can not be enrolled:
        # An exception is raised
        req.all_data = {"type": "motp"}
        self.assertRaises(PolicyError,
                          check_token_init, req)

        # A normal user can "enroll", since no user policies are defined.
        g.logged_in_user = {"username": "user1",
                            "role": "user"}
        r = check_token_init(req)
        self.assertTrue(r)
        # finally delete policy
        delete_policy("pol1")


    def test_03_check_token_upload(self):
        g.logged_in_user = {"username": "admin1",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"filename": "token.xml"}

        # Set a policy, that does allow the action
        set_policy(name="pol1",
                   scope=SCOPE.ADMIN,
                   action="enrollTOTP, enrollHOTP, {0!s}".format(ACTION.IMPORT),
                   client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        # Try to import tokens
        r = check_token_upload(req)
        self.assertTrue(r)

        # The admin can not upload from another IP address
        # An exception is raised
        env["REMOTE_ADDR"] = "192.168.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"filename": "token.xml"}
        self.assertRaises(PolicyError,
                          check_token_upload, req)
        # finally delete policy
        delete_policy("pol1")

    def test_04_check_max_token_user(self):
        g.logged_in_user = {"username": "admin1",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"user": "cornelius",
                        "realm": self.realm1}

        # Set a policy, that allows two tokens per user
        set_policy(name="pol1",
                   scope=SCOPE.ENROLL,
                   action="{0!s}={1!s}".format(ACTION.MAXTOKENUSER, 2))
        g.policy_object = PolicyClass()
        # The user has one token, everything is fine.
        self.setUp_user_realms()
        tokenobject = init_token({"serial": "NEW001", "type": "hotp",
                                  "otpkey": "1234567890123456"},
                                  user=User(login="cornelius",
                                            realm=self.realm1))
        tokenobject_list = get_tokens(user=User(login="cornelius",
                                           realm=self.realm1))
        self.assertTrue(len(tokenobject_list) == 1)
        self.assertTrue(check_max_token_user(req))

        # Now the user gets his second token
        tokenobject = init_token({"serial": "NEW002", "type": "hotp",
                                  "otpkey": "1234567890123456"},
                                  user=User(login="cornelius",
                                            realm=self.realm1))
        tokenobject_list = get_tokens(user=User(login="cornelius",
                                           realm=self.realm1))
        self.assertTrue(len(tokenobject_list) == 2)

        # The user has two tokens. The check that will run in this case,
        # before the user would be assigned the 3rd token, will raise a
        # PolicyError
        self.assertRaises(PolicyError,
                          check_max_token_user, req)


        # The check for a token, that has no username in it, must not
        # succeed. I.e. in the realm new tokens must be enrollable.
        req.all_data = {}
        self.assertTrue(check_max_token_user(req))

        req.all_data = {"realm": self.realm1}
        self.assertTrue(check_max_token_user(req))

        # finally delete policy
        delete_policy("pol1")
        remove_token("NEW001")
        remove_token("NEW002")

    def test_05_check_max_token_realm(self):
        g.logged_in_user = {"username": "admin1",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"realm": self.realm1}

        # Set a policy, that allows two tokens per realm
        set_policy(name="pol1",
                   scope=SCOPE.ENROLL,
                   action="max_token_per_realm=2",
                   realm=self.realm1)
        g.policy_object = PolicyClass()
        self.setUp_user_realms()
        # Add the first token into the realm
        tokenobject = init_token({"serial": "NEW001", "type": "hotp",
                                  "otpkey": "1234567890123456"})
        set_realms("NEW001", [self.realm1])
        # check the realm, only one token is in it the policy condition will
        # pass
        tokenobject_list = get_tokens(realm=self.realm1)
        self.assertTrue(len(tokenobject_list) == 1)
        self.assertTrue(check_max_token_realm(req))

        # add a second token to the realm
        tokenobject = init_token({"serial": "NEW002", "type": "hotp",
                                  "otpkey": "1234567890123456"})
        set_realms("NEW002", [self.realm1])
        tokenobject_list = get_tokens(realm=self.realm1)
        self.assertTrue(len(tokenobject_list) == 2)

        # request with a user object, not with a realm
        req.all_data = {"user": "cornelius@{0!s}".format(self.realm1)}

        # Now a new policy check will fail, since there are already two
        # tokens in the realm
        self.assertRaises(PolicyError,
                          check_max_token_realm, req)

        # finally delete policy
        delete_policy("pol1")
        remove_token("NEW001")
        remove_token("NEW002")

    def test_06_set_realm(self):
        g.logged_in_user = {"username": "admin1",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)

        # Set a policy, that allows two tokens per realm
        set_policy(name="pol1",
                   scope=SCOPE.AUTHZ,
                   action="{0!s}={1!s}".format(ACTION.SETREALM, self.realm1),
                   realm="somerealm")
        g.policy_object = PolicyClass()

        # request, that matches the policy
        req.all_data = {"realm": "somerealm"}
        set_realm(req)
        # Check, if the realm was modified to the realm specified in the policy
        self.assertTrue(req.all_data.get("realm") == self.realm1)

        # A request, that does not match the policy:
        req.all_data = {"realm": "otherrealm"}
        set_realm(req)
        # Check, if the realm is still the same
        self.assertEqual(req.all_data.get("realm"), "otherrealm")

        # If there are several policies, which will produce different realms,
        #  we get an exception
        set_policy(name="pol2",
                   scope=SCOPE.AUTHZ,
                   action="{0!s}={1!s}".format(ACTION.SETREALM, "ConflictRealm"),
                   realm="somerealm")
        g.policy_object = PolicyClass()
        # This request will trigger two policies with different realms to set
        req.all_data = {"realm": "somerealm"}
        self.assertRaises(PolicyError, set_realm, req)

        # finally delete policy
        delete_policy("pol1")
        delete_policy("pol2")

    def test_06_set_tokenlabel(self):
        g.logged_in_user = {"username": "admin1",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)

        # Set a policy that defines the tokenlabel
        set_policy(name="pol1",
                   scope=SCOPE.ENROLL,
                   action="{0!s}={1!s}".format(ACTION.TOKENLABEL, "<u>@<r>"))
        set_policy(name="pol2",
                   scope=SCOPE.ENROLL,
                   action="{0!s}={1!s}".format(ACTION.TOKENISSUER, "myPI"))
        g.policy_object = PolicyClass()

        # request, that matches the policy
        req.all_data = {
                        "user": "cornelius",
                        "realm": "home"}
        init_tokenlabel(req)

        # Check, if the tokenlabel was added
        self.assertEqual(req.all_data.get("tokenlabel"), "<u>@<r>")
        # Check, if the tokenissuer was added
        self.assertEqual(req.all_data.get("tokenissuer"), "myPI")
        # finally delete policy
        delete_policy("pol1")
        delete_policy("pol2")

    def test_07_set_random_pin(self):
        g.logged_in_user = {"username": "admin1",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)

        # Set a policy that defines the tokenlabel
        set_policy(name="pol1",
                   scope=SCOPE.ENROLL,
                   action="{0!s}={1!s}".format(ACTION.OTPPINRANDOM, "12"))
        set_policy(name="pinhandling",
                   scope=SCOPE.ENROLL,
                   action="{0!s}=privacyidea.lib.pinhandling.base.PinHandler".format(
                          ACTION.PINHANDLING))
        g.policy_object = PolicyClass()

        # request, that matches the policy
        req.all_data = {
                        "user": "cornelius",
                        "realm": "home"}
        init_random_pin(req)

        # Check, if the tokenlabel was added
        self.assertEqual(len(req.all_data.get("pin")), 12)
        # finally delete policy
        delete_policy("pol1")
        delete_policy("pinhandling")

    def test_08_encrypt_pin(self):
        g.logged_in_user = {"username": "admin1",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)

        # Set a policy that defines the PIN to be encrypted
        set_policy(name="pol1",
                   scope=SCOPE.ENROLL,
                   action=ACTION.ENCRYPTPIN)
        g.policy_object = PolicyClass()

        # request, that matches the policy
        req.all_data = {
                        "user": "cornelius",
                        "realm": "home"}
        encrypt_pin(req)

        # Check, if the tokenlabel was added
        self.assertEqual(req.all_data.get("encryptpin"), "True")
        # finally delete policy
        delete_policy("pol1")

    def test_09_pin_policies(self):
        g.logged_in_user = {"username": "user1",
                            "role": "user"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)

        # Set a policy that defines PIN policy
        set_policy(name="pol1",
                   scope=SCOPE.USER,
                   action="{0!s}={1!s},{2!s}={3!s},{4!s}={5!s}".format(ACTION.OTPPINMAXLEN, "10",
                                                 ACTION.OTPPINMINLEN, "4",
                                                 ACTION.OTPPINCONTENTS, "cn"))
        g.policy_object = PolicyClass()

        req.all_data = {
                        "user": "cornelius",
                        "realm": "home"}
        # The minimum OTP length is 4
        self.assertRaises(PolicyError, check_otp_pin, req)

        req.all_data = {
                        "user": "cornelius",
                        "realm": "home",
                        "pin": "12345566890012"}
        # Fail maximum OTP length
        self.assertRaises(PolicyError, check_otp_pin, req)

        req.all_data = {
                        "user": "cornelius",
                        "realm": "home",
                        "pin": "123456"}
        # Good OTP length, but missing character A-Z
        self.assertRaises(PolicyError, check_otp_pin, req)

        req.all_data = {
                        "user": "cornelius",
                        "realm": "home",
                        "pin": "abc123"}
        # Good length and good contents
        self.assertTrue(check_otp_pin(req))

        # A token that does not use pins is ignored.
        init_token({"type": "certificate",
                    "serial": "certificate"})
        req.all_data = {"serial": "certificate",
                        "realm": "somerealm",
                        "user": "cornelius",
                        "pin": ""}
        self.assertTrue(check_otp_pin(req))

        init_token({"type": "sshkey",
                    "serial": "sshkey",
                    "sshkey": SSHKEY})
        req.all_data = {"serial": "sshkey",
                        "realm": "somerealm",
                        "user": "cornelius",
                        "pin": ""}
        self.assertTrue(check_otp_pin(req))

        # finally delete policy
        delete_policy("pol1")

    def test_10_check_external(self):
        g.logged_in_user = {"username": "user1",
                            "role": "user"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        req = Request(env)
        g.policy_object = PolicyClass()
        req.all_data = {
                        "user": "cornelius",
                        "realm": "home"}

        # Check success on no definition
        r = check_external(req)
        self.assertTrue(r)

        # Check success with external function
        current_app.config["PI_INIT_CHECK_HOOK"] = \
            "privacyidea.api.lib.prepolicy.mock_success"
        r = check_external(req)
        self.assertTrue(r)

        # Check exception with external function
        current_app.config["PI_INIT_CHECK_HOOK"] = \
            "privacyidea.api.lib.prepolicy.mock_fail"
        self.assertRaises(Exception, check_external, req)

    def test_11_api_key_required(self):
        g.logged_in_user = {}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        g.policy_object = PolicyClass()

        # No policy and no Auth token
        req.all_data = {}
        r = api_key_required(req)
        # The request was not modified
        self.assertTrue(r)

        # Set a policy, that allows two tokens per realm
        set_policy(name="pol_api",
                   scope=SCOPE.AUTHZ,
                   action=ACTION.APIKEY)
        g.policy_object = PolicyClass()

        # A request with no API Key fails
        self.assertRaises(PolicyError, api_key_required, req)

        # A request with an API key succeeds
        secret = current_app.config.get("SECRET_KEY")
        token = jwt.encode({"role": ROLE.VALIDATE,
                            "exp": datetime.utcnow() + timedelta(hours=1)},
                            secret)
        req.headers = {"Authorization": token}
        r = api_key_required(req)
        self.assertTrue(r)

        # A request with a valid Admin Token does not succeed
        token = jwt.encode({"role": ROLE.ADMIN,
                            "username": "admin",
                            "exp": datetime.utcnow() + timedelta(hours=1)},
                            secret)
        req.headers = {"Authorization": token}
        self.assertRaises(PolicyError, api_key_required, req)

        delete_policy("pol_api")

    def test_12_mangle(self):
        g.logged_in_user = {"username": "admin1",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)

        # Set a mangle policy to change the username
        # and only use the last 4 characters of the username
        set_policy(name="mangle1",
                   scope=SCOPE.AUTH,
                   action="{0!s}=user/.*(.{{4}}$)/\\1/".format(ACTION.MANGLE))
        g.policy_object = PolicyClass()

        # request, that matches the policy
        req.all_data = {"user": "Thiswillbesplit_user"}
        mangle(req)
        # Check if the user was modified
        self.assertEqual(req.all_data.get("user"), "user")

        # Set a mangle policy to remove blanks from realm name
        set_policy(name="mangle2",
                   scope=SCOPE.AUTH,
                   action="{0!s}=realm/\\s//".format(ACTION.MANGLE))
        g.policy_object = PolicyClass()

        # request, that matches the policy
        req.all_data = {"realm": "lower Realm"}
        mangle(req)
        # Check if the realm was modified
        self.assertEqual(req.all_data.get("realm"), "lowerRealm")

        # finally delete policy
        delete_policy("mangle1")
        delete_policy("mangle2")

    def test_13_remote_user(self):
        g.logged_in_user = {"username": "admin1",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        env["REMOTE_USER"] = "admin"
        req = Request(env)

        # A user, for whom the login via REMOTE_USER is allowed.
        set_policy(name="ruser",
                   scope=SCOPE.WEBUI,
                   action="{0!s}={1!s}".format(ACTION.REMOTE_USER, REMOTE_USER.ACTIVE))
        g.policy_object = PolicyClass()

        r = is_remote_user_allowed(req)
        self.assertEqual(r, [REMOTE_USER.ACTIVE])

        # Login for the REMOTE_USER is not allowed.
        # Only allowed for user "super", but REMOTE_USER=admin
        set_policy(name="ruser",
                   scope=SCOPE.WEBUI,
                   action="{0!s}={1!s}".format(ACTION.REMOTE_USER, REMOTE_USER.ACTIVE),
                   user="super")
        g.policy_object = PolicyClass()

        r = is_remote_user_allowed(req)
        self.assertEqual(r, [])

        delete_policy("ruser")

    def test_14_required_email(self):
        g.logged_in_user = {"username": "admin1",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        # Set a mangle policy to change the username
        # and only use the last 4 characters of the username
        set_policy(name="email1",
                   scope=SCOPE.REGISTER,
                   action="{0!s}=/.*@mydomain\..*".format(ACTION.REQUIREDEMAIL))
        g.policy_object = PolicyClass()
        # request, that matches the policy
        req.all_data = {"email": "user@mydomain.net"}
        # This emails is allowed
        r = required_email(req)
        self.assertTrue(r)

        # This email is not allowed
        req.all_data = {"email": "user@otherdomain.net"}
        # This emails is allowed
        self.assertRaises(RegistrationError, required_email, req)

        delete_policy("email1")
        g.policy_object = PolicyClass()
        # Without a policy, this email can register
        req.all_data = {"email": "user@otherdomain.net"}
        # This emails is allowed
        r = required_email(req)
        self.assertTrue(r)

    def test_15_reset_password(self):
        builder = EnvironBuilder(method='POST',
                                 data={'user': "cornelius",
                                       "realm": self.realm1},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        # Set a mangle policy to change the username
        # and only use the last 4 characters of the username
        set_policy(name="recover",
                   scope=SCOPE.USER,
                   action="{0!s}".format(ACTION.RESYNC))
        g.policy_object = PolicyClass()
        req.all_data = {"user": "cornelius", "realm": self.realm1}
        # There is a user policy without password reset, so an exception is
        # raised
        self.assertRaises(PolicyError, check_anonymous_user, req,
                          ACTION.PASSWORDRESET)

        # The password reset is allowed
        set_policy(name="recover",
                   scope=SCOPE.USER,
                   action="{0!s}".format(ACTION.PASSWORDRESET))
        g.policy_object = PolicyClass()
        r = check_anonymous_user(req, ACTION.PASSWORDRESET)
        self.assertEqual(r, True)

    def test_16_check_two_admins(self):
        # We are checking two administrators
        # adminA: all rights on all realms
        # adminB: restricted rights on realmB
        builder = EnvironBuilder(method='POST')
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        req = Request(env)
        req.all_data = {"name": "newpol",
                        "scope": SCOPE.WEBUI,
                        "action": ["loginmode=privacyIDEA"],
                        "active": True,
                        "client": [],
                        "realm": ["realmB"],
                        "resolver": ["resolverB"],
                        "time": "",
                        "user": []
        }
        set_policy("polAdminA", scope=SCOPE.ADMIN,
                   action="set, revoke, adduser, enrollSMS, policydelete, "
                          "policywrite, enrollTIQR, configdelete, machinelist, "
                          "enrollREMOTE, setpin, resync, unassign, tokenrealms,"
                          " enrollSPASS, auditlog, enrollPAPER, deleteuser, "
                          "enrollEMAIL, resolverdelete, enrollMOTP, enrollPW, "
                          "enrollHOTP, enrollQUESTION, enrollCERTIFICATE, "
                          "copytokenuser, configwrite, enrollTOTP, "
                          "enrollREGISTRATION, enrollYUBICO, resolverwrite, "
                          "updateuser, enable, enrollU2F, "
                          "manage_machine_tokens, getrandom, userlist, "
                          "getserial, radiusserver_write, system_documentation,"
                          " caconnectordelete, caconnectorwrite, disable, "
                          "mresolverdelete, copytokenpin, enrollRADIUS, "
                          "smtpserver_write, set_hsm_password, reset, "
                          "getchallenges, enroll4EYES, enrollYUBIKEY, "
                          "fetch_authentication_items, enrollDAPLUG, "
                          "mresolverwrite, losttoken, enrollSSHKEY, "
                          "importtokens, assign, delete",
                   user="adminA",
                   realm="realmA, realmB",
                   resolver="resolverA, resolverB",
                   )
        set_policy("polAdminB", scope=SCOPE.ADMIN,
                   action="set, revoke, adduser, resync, unassign, "
                          "tokenrealms, deleteuser, enrollTOTP, "
                          "enrollREGISTRATION, updateuser, enable, userlist, "
                          "getserial, disable, reset, getchallenges, losttoken,"
                          " assign, delete ",
                   realm="realmB",
                   resolver="resolverB",
                   user="adminB")
        g.policy_object = PolicyClass()
        # Test AdminA
        g.logged_in_user = {"username": "adminA",
                            "role": "admin",
                            "realm": ""}
        r = check_base_action(req, action=ACTION.POLICYWRITE)
        self.assertEqual(r, True)
        # Test AdminB
        g.logged_in_user = {"username": "adminB",
                            "role": "admin",
                            "realm": ""}
        # AdminB is allowed to add user
        r = check_base_action(req, action=ACTION.ADDUSER)
        self.assertEqual(r, True)
        # But admin b is not allowed to policywrite
        self.assertRaises(PolicyError, check_base_action, req,
                          action=ACTION.POLICYWRITE)
        # Test AdminC: is not allowed to do anything
        g.logged_in_user = {"username": "adminC",
                            "role": "admin",
                            "realm": ""}
        self.assertRaises(PolicyError, check_base_action, req,
                          action=ACTION.POLICYWRITE)
        delete_policy("polAdminA")
        delete_policy("polAdminB")

    def test_17_add_user(self):
        # Check if adding a user is restricted to the resolver
        # adminA is allowed to add users to resolverA but not to resolverB
        set_policy("userAdd", scope=SCOPE.ADMIN,
                   action="adduser",
                   user="adminA",
                   realm="realmA",
                   resolver="resolverA",
                   )
        builder = EnvironBuilder(method='POST')
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        req = Request(env)
        req.all_data = {"user": "new_user",
                        "resolver": "resolverA"}
        g.policy_object = PolicyClass()
        g.logged_in_user = {"username": "adminA",
                            "role": "admin",
                            "realm": ""}
        # User can be added
        r = check_base_action(req, action=ACTION.ADDUSER)
        self.assertEqual(r, True)

        req.all_data = {"user": "new_user",
                        "resolver": "resolverB"}

        # User can not be added in a different resolver
        self.assertRaises(PolicyError, check_base_action, req,
                          action=ACTION.ADDUSER)
        delete_policy("userAdd")


class PostPolicyDecoratorTestCase(MyTestCase):

    def test_01_check_tokentype(self):
        # http://werkzeug.pocoo.org/docs/0.10/test/#environment-building
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        # The response contains the token type SPASS
        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": True},
               "version": "privacyIDEA test",
               "id": 1,
               "detail": {"message": "matching 1 tokens",
                          "serial": "PISP0000AB00",
                          "type": "spass"}}
        resp = Response(json.dumps(res))

        # Set a policy, that does not allow the tokentype
        set_policy(name="pol1",
                   scope=SCOPE.AUTHZ,
                   action="tokentype=hotp", client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        # The token type SPASS is not allowed on this client, so an exception
        #  is raised.
        self.assertRaises(PolicyError,
                          check_tokentype,
                          req, resp)

        # A policy, that allows the token spass
        # Set a policy, that does not allow the tokentype
        set_policy(name="pol1",
                   scope=SCOPE.AUTHZ,
                   action="tokentype=spass", client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        # The token type SPASS is not allowed on this client, so an exception
        #  is raised.
        r = check_tokentype(req, resp)
        jresult = json.loads(r.data)
        self.assertTrue(jresult.get("result").get("value"))

    def test_02_check_serial(self):
        # http://werkzeug.pocoo.org/docs/0.10/test/#environment-building
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "HOTP123435"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        # The response contains the token type SPASS
        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": True},
               "version": "privacyIDEA test",
               "id": 1,
               "detail": {"message": "matching 1 tokens",
                          "serial": "HOTP123456",
                          "type": "hotp"}}
        resp = Response(json.dumps(res))

        # Set a policy, that does not allow the tokentype
        set_policy(name="pol1",
                   scope=SCOPE.AUTHZ,
                   action="serial=TOTP", client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        # The token serial HOTP is not allowed on this client, so an exception
        #  is raised.
        self.assertRaises(PolicyError,
                          check_serial,
                          req, resp)

        # A policy, that allows the token spass
        # Set a policy, that does not allow the tokentype
        set_policy(name="pol1",
                   scope=SCOPE.AUTHZ,
                   action="serial=HOTP", client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        # The token type SPASS is not allowed on this client, so an exception
        # is raised.
        r = check_serial(req, resp)
        jresult = json.loads(r.data)
        self.assertTrue(jresult.get("result").get("value"))

    def test_03_no_detail_on_success(self):
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "HOTP123435"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        # The response contains the token type SPASS
        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": True},
               "version": "privacyIDEA test",
               "id": 1,
               "detail": {"message": "matching 1 tokens",
                          "serial": "HOTP123456",
                          "type": "hotp"}}
        resp = Response(json.dumps(res))

        # Set a policy, that does not allow the detail on success
        set_policy(name="pol2",
                   scope=SCOPE.AUTHZ,
                   action="no_detail_on_success", client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        new_response = no_detail_on_success(req, resp)
        jresult = json.loads(new_response.data)
        self.assertTrue("detail" not in jresult, jresult)
        delete_policy("pol2")

    def test_04_no_detail_on_fail(self):
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "HOTP123435"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        # The response contains the token type SPASS
        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": False},
               "version": "privacyIDEA test",
               "id": 1,
               "detail": {"message": "matching 1 tokens",
                          "serial": "HOTP123456",
                          "type": "hotp"}}
        resp = Response(json.dumps(res))

        # Set a policy, that does not allow the detail on success
        set_policy(name="pol2",
                   scope=SCOPE.AUTHZ,
                   action="no_detail_on_fail", client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        new_response = no_detail_on_fail(req, resp)
        jresult = json.loads(new_response.data)
        self.assertTrue("detail" not in jresult, jresult)

        # A successful call has a detail in the response!
        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": True},
               "version": "privacyIDEA test",
               "id": 1,
               "detail": {"message": "matching 1 tokens",
                          "serial": "HOTP123456",
                          "type": "hotp"}}
        resp = Response(json.dumps(res))

        new_response = no_detail_on_fail(req, resp)
        jresult = json.loads(new_response.data)
        self.assertTrue("detail" in jresult, jresult)

        delete_policy("pol2")

    def test_05_autoassign_any_pin(self):
        # init a token, that does has no uwser
        self.setUp_user_realms()
        tokenobject = init_token({"serial": "UASSIGN1", "type": "hotp",
                                  "otpkey": "3132333435363738393031"
                                            "323334353637383930"},
                                 tokenrealms=[self.realm1])

        user_obj = User("autoassignuser", self.realm1)
        # unassign all tokens from the user autoassignuser
        try:
            unassign_token(None, user=user_obj)
        except Exception:
            print("no need to unassign token")

        # The request with an OTP value and a PIN of a user, who has not
        # token assigned
        builder = EnvironBuilder(method='POST',
                                 data={},
                                 headers={})
        env = builder.get_environ()
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"user": "autoassignuser", "realm": self.realm1,
                        "pass": "test287082"}
        # The response with a failed request
        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": False},
               "version": "privacyIDEA test",
               "id": 1}
        resp = Response(json.dumps(res))

        # Set the autoassign policy
        # to "any_pin"
        set_policy(name="pol2",
                   scope=SCOPE.ENROLL,
                   action="{0!s}={1!s}".format(ACTION.AUTOASSIGN, AUTOASSIGNVALUE.NONE),
                                     client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        new_response = autoassign(req, resp)
        jresult = json.loads(new_response.data)
        self.assertTrue(jresult.get("result").get("value"), jresult)
        self.assertEqual(jresult.get("detail").get("serial"), "UASSIGN1")

        # test the token with test287082 will fail
        res, dict = check_user_pass(User("autoassignuser", self.realm1),
                                    "test287082")
        self.assertFalse(res)

        # test the token with test359152 will succeed
        res, dict = check_user_pass(User("autoassignuser", self.realm1),
                                    "test359152")
        self.assertTrue(res)

        delete_policy("pol2")

    def test_05_autoassign_userstore(self):
        # init a token, that does has no user
        self.setUp_user_realms()
        tokenobject = init_token({"serial": "UASSIGN2", "type": "hotp",
                                  "otpkey": "3132333435363738393031"
                                            "323334353637383930"},
                                 tokenrealms=[self.realm1])
        user_obj = User("autoassignuser", self.realm1)
        # unassign all tokens from the user autoassignuser
        try:
            unassign_token(None, user=user_obj)
        except Exception:
            print("no need to unassign token")

        # The request with an OTP value and a PIN of a user, who has not
        # token assigned
        builder = EnvironBuilder(method='POST',
                                 data={},
                                 headers={})
        env = builder.get_environ()
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"user": "autoassignuser", "realm": self.realm1,
                        "pass": "password287082"}
        # The response with a failed request
        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": False},
               "version": "privacyIDEA test",
               "id": 1}
        resp = Response(json.dumps(res))

        # Set the autoassign policy
        # to "userstore"
        set_policy(name="pol2",
                   scope=SCOPE.ENROLL,
                   action="{0!s}={1!s}".format(ACTION.AUTOASSIGN,
                                     AUTOASSIGNVALUE.USERSTORE),
                                     client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        new_response = autoassign(req, resp)
        jresult = json.loads(new_response.data)
        self.assertEqual(jresult.get("result").get("value"), True)
        self.assertEqual(jresult.get("detail").get("serial"), "UASSIGN2")

        # authenticate with 287082 a second time will fail
        res, dict = check_user_pass(User("autoassignuser", self.realm1),
                                    "password287082")
        self.assertFalse(res)

        # authenticate with the next OTP 359152 will succeed
        res, dict = check_user_pass(User("autoassignuser", self.realm1),
                                    "password359152")
        self.assertTrue(res)

        delete_policy("pol2")

    def test_06_offline_auth(self):
        # Test that a machine definition will return offline hashes
        self.setUp_user_realms()
        serial = "offline01"
        tokenobject = init_token({"serial": serial, "type": "hotp",
                                  "otpkey": "3132333435363738393031"
                                            "323334353637383930",
                                  "pin": "offline",
                                  "user": "cornelius"})

        # Set the Machine and MachineToken
        resolver1 = save_resolver({"name": "reso1",
                                   "type": "hosts",
                                   "filename": HOSTSFILE})

        mt = attach_token(serial, "offline", hostname="gandalf")
        self.assertEqual(mt.token.serial, serial)
        self.assertEqual(mt.token.machine_list[0].machine_id, "192.168.0.1")

        # The request with an OTP value and a PIN of a user, who has not
        # token assigned
        builder = EnvironBuilder(method='POST',
                                 data={},
                                 headers={})
        env = builder.get_environ()
        env["REMOTE_ADDR"] = "192.168.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"user": "cornelius",
                        "pass": "offline287082"}

        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": True},
               "version": "privacyIDEA test",
               "detail": {"serial": serial},
               "id": 1}
        resp = Response(json.dumps(res))

        new_response = offline_info(req, resp)
        jresult = json.loads(new_response.data)
        self.assertTrue(jresult.get("result").get("value"), jresult)
        self.assertEqual(jresult.get("detail").get("serial"), serial)

        # Check the hashvalues in the offline tree
        auth_items = jresult.get("auth_items")
        self.assertEqual(len(auth_items), 1)
        response = auth_items.get("offline")[0].get("response")
        self.assertEqual(len(response), 100)
        # check if the counter of the token was increased to 100
        tokenobject = get_tokens(serial=serial)[0]
        self.assertEqual(tokenobject.token.count, 101)
        delete_policy("pol2")

    def test_07_sign_response(self):
        builder = EnvironBuilder(method='POST',
                                 data={},
                                 headers={})
        env = builder.get_environ()
        env["REMOTE_ADDR"] = "192.168.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.values = {"user": "cornelius",
                      "pass": "offline287082",
                      "nonce": "12345678"}

        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": True},
               "version": "privacyIDEA test",
               "id": 1}
        resp = Response(json.dumps(res))
        from privacyidea.lib.crypto import Sign
        g.sign_object = Sign("tests/testdata/private.pem",
                             "tests/testdata/public.pem")

        new_response = sign_response(req, resp)
        jresult = json.loads(new_response.data)
        self.assertEqual(jresult.get("nonce"), "12345678")
        self.assertEqual(jresult.get("signature"), "7220461805369685253863294214862525311437731987121534735993146952136348520396812489782945679627890785973634896605293523175424850299832912878523161817380029213546063467888018205435416020286712762804412024065559270543774578319469096483246637875013247101135063221604113204491121777932147776087110152414627230087278622508771143940031542890514380486863296102037208395371717795767683973979032142677315402422403254992482761563612174177151960004042109847122772813717599078313600692433727690239340230353616318691769042290314664126975201679642739717702497638318611217001361093950139025744740660953017413716736691777322916588328")

    def test_08_get_webui_settings(self):
        # Test that a machine definition will return offline hashes
        self.setUp_user_realms()
        serial = "offline01"
        tokenobject = init_token({"serial": serial, "type": "hotp",
                                  "otpkey": "3132333435363738393031"
                                            "323334353637383930",
                                  "pin": "offline",
                                  "user": "cornelius"})

        # Set the Machine and MachineToken
        resolver1 = save_resolver({"name": "reso1",
                                   "type": "hosts",
                                   "filename": HOSTSFILE})

        mt = attach_token(serial, "offline", hostname="gandalf")
        self.assertEqual(mt.token.serial, serial)
        self.assertEqual(mt.token.machine_list[0].machine_id, "192.168.0.1")

        # The request with an OTP value and a PIN of a user, who has not
        # token assigned
        builder = EnvironBuilder(method='POST',
                                 data={},
                                 headers={})
        env = builder.get_environ()
        env["REMOTE_ADDR"] = "192.168.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"user": "cornelius",
                        "pass": "offline287082"}

        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": {"role": "user",
                                    "username": "cornelius"}},
               "version": "privacyIDEA test",
               "detail": {"serial": serial},
               "id": 1}
        resp = Response(json.dumps(res))

        new_response = get_webui_settings(req, resp)
        jresult = json.loads(new_response.data)
        self.assertEqual(jresult.get("result").get("value").get(
            "token_wizard"), False)

        # Set a policy. User has not token, so "token_wizard" will be True
        set_policy(name="pol_wizard",
                   scope=SCOPE.WEBUI,
                   action=ACTION.TOKENWIZARD)
        g.policy_object = PolicyClass()
        new_response = get_webui_settings(req, resp)
        jresult = json.loads(new_response.data)
        self.assertEqual(jresult.get("result").get("value").get(
            "token_wizard"), True)

        delete_policy("pol_wizard")

    def test_16_init_token_defaults(self):
        g.logged_in_user = {"username": "cornelius",
                            "role": "user"}
        builder = EnvironBuilder(method='POST',
                                 data={'type': "totp",
                                       "genkey": "1"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)

        # Set a policy that defines the default totp settings
        set_policy(name="pol1",
                   scope=SCOPE.USER,
                   action="totp_otplen=8,totp_hashlib=sha256,totp_timestep=60")
        g.policy_object = PolicyClass()

        # request, that matches the policy
        req.all_data = {
            "type": "totp",
            "genkey": "1"}
        init_token_defaults(req)

        # Check, if the token defaults were added
        self.assertEqual(req.all_data.get("totp.hashlib"), "sha256")
        self.assertEqual(req.all_data.get("otplen"), "8")
        self.assertEqual(req.all_data.get("timeStep"), "60")
        # finally delete policy
        delete_policy("pol1")

