# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
This test file tests the api.lib.policy.py

The api.lib.policy.py depends on lib.policy and on flask!
"""
import json
import logging
from datetime import datetime, timedelta

import jwt
from dateutil.tz import tzlocal
from flask import Request, g, current_app, jsonify
from passlib.hash import pbkdf2_sha512
from testfixtures import log_capture, LogCapture
from werkzeug.datastructures.headers import Headers
from werkzeug.test import EnvironBuilder

from privacyidea.api.lib.policyhelper import get_realm_for_authentication
from privacyidea.api.lib.postpolicy import (check_serial, check_tokentype,
                                            check_tokeninfo,
                                            no_detail_on_success,
                                            no_detail_on_fail, autoassign,
                                            offline_info, sign_response,
                                            get_webui_settings,
                                            save_pin_change,
                                            add_user_detail_to_response,
                                            mangle_challenge_response, is_authorized,
                                            check_verify_enrollment, preferred_client_mode,
                                            multichallenge_enroll_via_validate)
from privacyidea.api.lib.prepolicy import (check_token_upload,
                                           check_base_action, check_token_init,
                                           check_max_token_user,
                                           check_anonymous_user,
                                           check_max_token_realm, set_realm,
                                           init_tokenlabel, init_random_pin, set_random_pin,
                                           init_token_defaults, _generate_pin_from_policy,
                                           encrypt_pin, check_otp_pin,
                                           enroll_pin,
                                           init_token_length_contents,
                                           check_external, api_key_required,
                                           mangle, is_remote_user_allowed,
                                           required_email, auditlog_age, hide_audit_columns,
                                           papertoken_count,
                                           tantoken_count, sms_identifiers,
                                           pushtoken_add_config, pushtoken_validate,
                                           indexedsecret_force_attribute,
                                           check_admin_tokenlist, pushtoken_disable_wait,
                                           fido2_auth, webauthntoken_authz,
                                           fido2_enroll, webauthntoken_request,
                                           check_application_tokentype,
                                           required_piv_attestation, check_custom_user_attributes,
                                           hide_tokeninfo, init_ca_template, init_ca_connector,
                                           init_subject_components, increase_failcounter_on_challenge,
                                           require_description, check_container_action,
                                           check_token_action, check_user_params,
                                           check_client_container_action, container_registration_config,
                                           smartphone_config, check_client_container_disabled_action, rss_age,
                                           hide_container_info, force_server_generate_key, verify_enrollment)
from privacyidea.lib.auth import ROLE
from privacyidea.lib.config import set_privacyidea_config, SYSCONF
from privacyidea.lib.container import (init_container, find_container_by_serial, create_container_template,
                                       get_all_containers, delete_container_template)
from privacyidea.lib.containers.container_info import RegistrationState, TokenContainerInfoData
from privacyidea.lib.error import PolicyError, RegistrationError, ValidateError
from privacyidea.lib.fido2.policy_action import FIDO2PolicyAction
from privacyidea.lib.machine import attach_token
from privacyidea.lib.machineresolver import save_resolver
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policies.helper import get_jwt_validity
from privacyidea.lib.policy import (set_policy, delete_policy, enable_policy,
                                    PolicyClass, SCOPE, REMOTE_USER,
                                    AUTOASSIGNVALUE, AUTHORIZED,
                                    DEFAULT_ANDROID_APP_URL, DEFAULT_IOS_APP_URL)
from privacyidea.lib.realm import delete_realm
from privacyidea.lib.realm import set_realm as create_realm
from privacyidea.lib.subscriptions import EXPIRE_MESSAGE
from privacyidea.lib.token import (init_token, get_tokens, remove_token,
                                   set_realms, check_user_pass, unassign_token,
                                   enable_token)
from privacyidea.lib.tokenclass import DATE_FORMAT
from privacyidea.lib.tokens.certificatetoken import ACTION as CERTIFICATE_ACTION
from privacyidea.lib.tokens.indexedsecrettoken import PIIXACTION
from privacyidea.lib.tokens.papertoken import PAPERACTION
from privacyidea.lib.tokens.pushtoken import PushAction
from privacyidea.lib.tokens.registrationtoken import DEFAULT_LENGTH, DEFAULT_CONTENTS
from privacyidea.lib.tokens.smstoken import SMSAction
from privacyidea.lib.tokens.tantoken import TANAction
from privacyidea.lib.tokens.webauthn import (webauthn_b64_decode, AuthenticatorAttachmentType,
                                             AttestationLevel, AttestationForm,
                                             UserVerificationLevel)
from privacyidea.lib.tokens.webauthntoken import (DEFAULT_ALLOWED_TRANSPORTS,
                                                  WebAuthnTokenClass, DEFAULT_CHALLENGE_TEXT_AUTH,
                                                  PUBLIC_KEY_CREDENTIAL_ALGORITHMS,
                                                  DEFAULT_PUBLIC_KEY_CREDENTIAL_ALGORITHM_PREFERENCE,
                                                  DEFAULT_AUTHENTICATOR_ATTESTATION_LEVEL,
                                                  DEFAULT_AUTHENTICATOR_ATTESTATION_FORM,
                                                  DEFAULT_CHALLENGE_TEXT_ENROLL, DEFAULT_TIMEOUT,
                                                  DEFAULT_USER_VERIFICATION_REQUIREMENT,
                                                  PUBKEY_CRED_ALGORITHMS_ORDER)
from privacyidea.lib.user import User
from privacyidea.lib.users.custom_user_attributes import InternalCustomUserAttributes, INTERNAL_USAGE
from privacyidea.lib.utils import (create_img, generate_charlists_from_pin_policy,
                                   CHARLIST_CONTENTPOLICY, check_pin_contents)
from privacyidea.lib.utils import hexlify_and_unicode, AUTH_RESPONSE
from .base import (MyApiTestCase)
from .test_lib_tokens_webauthn import (ALLOWED_TRANSPORTS, CRED_ID, ASSERTION_RESPONSE_TMPL,
                                       ASSERTION_CHALLENGE, RP_ID, RP_NAME, ORIGIN)

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

YUBIKEY_CSR = """-----BEGIN CERTIFICATE REQUEST-----
MIICbTCCAVUCAQAwFzEVMBMGA1UEAwwMY249Y29ybmVsaXVzMIIBIjANBgkqhkiG
9w0BAQEFAAOCAQ8AMIIBCgKCAQEAzqQ5MCVz5J3mNzuFWYPvo275g7n3SLAL1egF
QGHNxVq8ES9bTtBPuNDofwWrrSQLkNQ/YOwVtk6+jtkmq/IvfzXCpqG8UjrZiPuz
+nEguVEO+K8NFr69XbmrMNWsazy87ihKT2/UCRX3mK932zYVLh7uD9DZYK3bucQ/
xiUy+ePpULjshKDE0pz9ziWAhX46rUynQBsKWBifwl424dFE6Ua23LQoouztAvcl
eeGGjmlnUu6CIbeELcznqDlXfaMe6VBjdymr5KX/3O5MS14IK2IILXW4JmyT6/VF
6s2DWFMVRuZrQ8Ev2YhLPdX9DP9RUu1U+yctWe9MUM5xzetamQIDAQABoBEwDwYJ
KoZIhvcNAQkOMQIwADANBgkqhkiG9w0BAQsFAAOCAQEArLWY74prQRtKojwMEOsw
4efmzCwOvLoO/WXDwzrr7kgSOawQanhFzD+Z4kCwapf1ZMmobBnyWREpL4EC9PzC
YH+mgSDCI0jDj/4OSfklb31IzRhuWcCVOpV9xuiDW875WM792t09ILCpx4rayw2a
8t92zv49IcWHtJNqpo2Q8064p2fzYf1J1r4OEBKUUxEIcw2/nifIiHHTb7DqDF4+
XjcD3ygUfTVbCzPYBmLPwvt+80AxgT2Nd6E612L/fbI9clv5DsvMwnVeSvlP1wXo
5BampVY4p5CQRFLlCQa9fGWZrT+ArC9Djo0mHf32x6pEsSz0zMOlmjHrh+ChVkAs
tA==
-----END CERTIFICATE REQUEST-----"""

class PostPolicyDecoratorTestCase(MyApiTestCase):

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
        req.User = User()
        # The response contains the token type SPASS
        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": True},
               "version": "privacyIDEA test",
               "id": 1,
               "detail": {"message": "matching 1 tokens",
                          "serial": "PISP0000AB00",
                          "type": "spass"}}
        resp = jsonify(res)

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
        jresult = r.json
        self.assertTrue(jresult.get("result").get("value"))

    def test_01_check_undetermined_tokentype(self):
        # If there is a tokentype policy but the type can not be
        # determined, authentication fails.
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.User = User()
        # The response contains the token type SPASS
        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": True},
               "version": "privacyIDEA test",
               "id": 1,
               "detail": {"message": "matching 2 tokens",
                          "type": "undetermined"}}
        resp = jsonify(res)

        # Set a policy, that does not allow the tokentype
        set_policy(name="pol1",
                   scope=SCOPE.AUTHZ,
                   action="tokentype=hotp", client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        # The token type can not be determined, so an exception
        #  is raised.
        self.assertRaises(PolicyError,
                          check_tokentype,
                          req, resp)

    def test_03_check_tokeninfo(self):
        token_obj = init_token({"type": "SPASS", "serial": "PISP0001"})
        token_obj.set_tokeninfo({"testkey": "testvalue"})

        # http://werkzeug.pocoo.org/docs/0.10/test/#environment-building
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "PISP0001"},
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
                          "serial": "PISP0001",
                          "type": "spass"}}
        resp = jsonify(res)

        # Set a policy, that does match
        set_policy(name="pol1",
                   scope=SCOPE.AUTHZ,
                   action="tokeninfo=testkey/test.*/", client="10.0.0.0/8")
        g.policy_object = PolicyClass()
        r = check_tokeninfo(req, resp)
        jresult = r.json
        self.assertTrue(jresult.get("result").get("value"))

        # Set a policy that does NOT match
        set_policy(name="pol1",
                   scope=SCOPE.AUTHZ,
                   action="tokeninfo=testkey/NO.*/", client="10.0.0.0/8")
        g.policy_object = PolicyClass()
        self.assertRaises(PolicyError,
                          check_tokeninfo,
                          req, resp)

        # Set a policy, but the token has no tokeninfo!
        # Thus the authorization will fail
        token_obj.delete_tokeninfo("testkey")
        self.assertRaises(PolicyError,
                          check_tokeninfo,
                          req, resp)

        # If we set an invalid policy, authorization will succeed
        set_policy(name="pol1",
                   scope=SCOPE.AUTHZ,
                   action="tokeninfo=testkey/missingslash", client="10.0.0.0/8")
        g.policy_object = PolicyClass()
        r = check_tokeninfo(req, resp)
        jresult = r.json
        self.assertTrue(jresult.get("result").get("value"))

        delete_policy("pol1")
        remove_token("PISP0001")

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
        resp = jsonify(res)

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
        jresult = r.json
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
        resp = jsonify(res)

        # Set a policy, that does not allow the detail on success
        set_policy(name="pol2",
                   scope=SCOPE.AUTHZ,
                   action="no_detail_on_success", client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        new_response = no_detail_on_success(req, resp)
        jresult = new_response.json
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
        resp = jsonify(res)

        # Set a policy, that does not allow the detail on success
        set_policy(name="pol2",
                   scope=SCOPE.AUTHZ,
                   action="no_detail_on_fail", client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        new_response = no_detail_on_fail(req, resp)
        jresult = new_response.json
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
        resp = jsonify(res)

        new_response = no_detail_on_fail(req, resp)
        jresult = new_response.json
        self.assertTrue("detail" in jresult, jresult)

        delete_policy("pol2")

    def test_04_add_user_in_response(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        builder = EnvironBuilder(method='POST',
                                 data={'user': "cornelius",
                                       "pass": "test"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.User = User("autoassignuser", self.realm1)
        # The response contains the token type SPASS and result->authentication set to ACCEPT
        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": True,
                          "authentication": AUTH_RESPONSE.ACCEPT},
               "version": "privacyIDEA test",
               "id": 1,
               "detail": {"message": "matching 1 tokens",
                          "serial": "HOTP123456",
                          "type": "hotp"}}
        resp = jsonify(res)

        g.policy_object = PolicyClass()

        new_response = add_user_detail_to_response(req, resp)
        jresult = new_response.json
        self.assertTrue("user" not in jresult.get("detail"), jresult)

        # A successful get a user added
        # Set a policy, that adds user info to detail
        set_policy(name="pol_add_user",
                   scope=SCOPE.AUTHZ,
                   action=PolicyAction.ADDUSERINRESPONSE, client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        new_response = add_user_detail_to_response(req, resp)
        jresult = new_response.json
        self.assertTrue("user" in jresult.get("detail"), jresult)
        self.assertFalse("user-resolver" in jresult.get("detail"), jresult)
        self.assertFalse("user-realm" in jresult.get("detail"), jresult)

        # check with different realm in policy conditions
        # if the user-name is evaluated
        # in add_user_in_response policy
        res = {"result": {"status": True,
                          "value": True},
               "detail": {"message": "matching 1 tokens",
                          "serial": "HOTP123456",
                          "type": "hotp"}}
        resp = jsonify(res)
        set_policy(name="pol_add_user",
                   scope=SCOPE.AUTHZ,
                   action=PolicyAction.ADDUSERINRESPONSE, client="10.0.0.0/8", realm=self.realm2)
        g.policy_object = PolicyClass()

        new_response = add_user_detail_to_response(req, resp)
        jresult = new_response.json
        self.assertNotIn("user", jresult.get("detail"), jresult)

        # set a policy that adds user resolver to detail
        set_policy(name="pol_add_resolver",
                   scope=SCOPE.AUTHZ,
                   action=PolicyAction.ADDRESOLVERINRESPONSE, client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        new_response = add_user_detail_to_response(req, resp)
        jresult = new_response.json
        self.assertTrue("user-resolver" in jresult.get("detail"), jresult)
        self.assertEqual(jresult.get("detail").get("user-resolver"), self.resolvername1)
        self.assertTrue("user-realm" in jresult.get("detail"), jresult)
        self.assertEqual(jresult.get("detail").get("user-realm"), self.realm1)

        delete_policy("pol_add_user")
        delete_policy("pol_add_resolver")

        # check with different realm in policy conditions
        # if the user-realm is evaluated
        # in add_resolver_in_response policy
        res = {
            "result": {
                "status": True,
                "value": True},
            "detail": {
                "message": "matching 1 tokens",
                "serial": "HOTP123456",
                "type": "hotp"}}
        resp = jsonify(res)
        set_policy(name="pol_add_resolver",
                   scope=SCOPE.AUTHZ,
                   action=PolicyAction.ADDRESOLVERINRESPONSE, client="10.0.0.0/8", realm=self.realm2)
        g.policy_object = PolicyClass()

        new_response = add_user_detail_to_response(req, resp)
        jresult = new_response.json
        self.assertNotIn("user-realm", jresult.get("detail"), jresult)
        self.assertNotIn("user-resolver", jresult.get("detail"), jresult)

    def test_05_autoassign_any_pin(self):
        # init a token, that does has no uwser
        self.setUp_user_realms()
        init_token({"serial": "UASSIGN1", "type": "hotp",
                    "otpkey": "3132333435363738393031"
                              "323334353637383930"},
                   tokenrealms=[self.realm1])

        user_obj = User("autoassignuser", self.realm1)
        # unassign all tokens from the user autoassignuser
        unassign_token(None, user=user_obj)

        # The request with an OTP value and a PIN of a user, who has no token assigned
        builder = EnvironBuilder(method='POST',
                                 data={},
                                 headers={})
        env = builder.get_environ()
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"user": "autoassignuser", "realm": self.realm1,
                        "pass": "test287082"}
        req.User = User("autoassignuser", self.realm1)
        # The response with a failed request
        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": False},
               "version": "privacyIDEA test",
               "id": 1}
        resp = jsonify(res)

        # Set the autoassign policy
        # to "any_pin"
        set_policy(name="pol2",
                   scope=SCOPE.ENROLL,
                   action="{0!s}={1!s}".format(PolicyAction.AUTOASSIGN, AUTOASSIGNVALUE.NONE),
                   client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        new_response = autoassign(req, resp)
        jresult = new_response.json
        self.assertTrue(jresult.get("result").get("value"), jresult)
        self.assertEqual(jresult.get("detail").get("serial"), "UASSIGN1")
        self.assertEqual(jresult.get("detail").get("otplen"), 6)

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
        init_token({"serial": "UASSIGN2", "type": "hotp",
                    "otpkey": "3132333435363738393031"
                              "323334353637383930"},
                   tokenrealms=[self.realm1])
        user_obj = User("autoassignuser", self.realm1)
        # unassign all tokens from the user autoassignuser
        unassign_token(None, user=user_obj)

        # The request with an OTP value and a PIN of a user, who has no token assigned
        builder = EnvironBuilder(method='POST',
                                 data={},
                                 headers={})
        env = builder.get_environ()
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"user": "autoassignuser", "realm": self.realm1,
                        "pass": "password287082"}
        req.User = User("autoassignuser", self.realm1)
        # The response with a failed request
        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": False},
               "version": "privacyIDEA test",
               "id": 1}
        resp = jsonify(res)

        # Set the autoassign policy
        # to "userstore"
        set_policy(name="pol2",
                   scope=SCOPE.ENROLL,
                   action="{0!s}={1!s}".format(PolicyAction.AUTOASSIGN, AUTOASSIGNVALUE.USERSTORE),
                   client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        new_response = autoassign(req, resp)
        jresult = new_response.json
        self.assertEqual(jresult.get("result").get("value"), True)
        self.assertEqual(jresult.get("detail").get("serial"), "UASSIGN2")
        self.assertEqual(jresult.get("detail").get("otplen"), 6)

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
        init_token({"serial": serial, "type": "hotp",
                    "otpkey": "3132333435363738393031323334353637383930",
                    "pin": "offline",
                    "user": "cornelius"})

        # Set the Machine and MachineToken
        save_resolver({"name": "reso1",
                       "type": "hosts",
                       "filename": HOSTSFILE})

        mt = attach_token(serial, "offline", hostname="gandalf")
        self.assertEqual(mt.token.serial, serial)
        self.assertEqual(mt.token.machine_list[0].machine_id, "192.168.0.1")

        # The request with an OTP value and a PIN of a user, who has no token assigned
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
        resp = jsonify(res)

        new_response = offline_info(req, resp)
        jresult = new_response.json
        self.assertTrue(jresult.get("result").get("value"), jresult)
        self.assertEqual(jresult.get("detail").get("serial"), serial)

        # Check the hashvalues in the offline tree
        auth_items = jresult.get("auth_items")
        self.assertEqual(len(auth_items), 1)
        response = auth_items.get("offline")[0].get("response")
        self.assertEqual(len(response), 100)
        # check if the counter of the token was increased to 100
        # it is only 100, not 102, because the OTP value with counter=1
        # (287082) has not actually been consumed (because this
        # test only invoked the policy function)
        tokenobject = get_tokens(serial=serial)[0]
        self.assertEqual(tokenobject.token.count, 100)
        # check that we cannot authenticate with an offline value
        self.assertTrue(pbkdf2_sha512.verify("offline287082", response.get('1')))
        self.assertTrue(pbkdf2_sha512.verify("offline516516", response.get('99')))
        res = tokenobject.check_otp("516516")  # count = 99
        self.assertEqual(res, -1)
        # check that we can authenticate online with the correct value
        res = tokenobject.check_otp("295165")  # count = 100
        self.assertEqual(res, 100)

    def test_06a_offline_auth_postpend_pin(self):
        serial = "offline01"
        # Do prepend_pin == False
        set_privacyidea_config(SYSCONF.PREPENDPIN, False)
        # The request with an OTP value and a PIN of a user, who has no token assigned
        builder = EnvironBuilder(method='POST',
                                 data={},
                                 headers={})
        env = builder.get_environ()
        env["REMOTE_ADDR"] = "192.168.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        # Use: % oathtool -c 101 3132333435363738393031323334353637383930
        # 329376
        # Send the PIN behind the OTP value
        req.all_data = {"user": "cornelius",
                        "pass": "329376offline"}

        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": True},
               "version": "privacyIDEA test",
               "detail": {"serial": serial},
               "id": 1}
        resp = jsonify(res)
        new_response = offline_info(req, resp)
        jresult = new_response.json
        self.assertTrue(jresult.get("result").get("value"), jresult)
        self.assertEqual(jresult.get("detail").get("serial"), serial)

        # Check the hashvalues in the offline tree
        auth_items = jresult.get("auth_items")
        self.assertEqual(len(auth_items), 1)
        response = auth_items.get("offline")[0].get("response")
        self.assertEqual(len(response), 100)
        # Check that the token counter has now increased to 201
        tokenobject = get_tokens(serial=serial)[0]
        self.assertEqual(tokenobject.token.count, 201)
        # check that we cannot authenticate with an offline value
        self.assertTrue(pbkdf2_sha512.verify("629694offline", response.get('102')))
        self.assertTrue(pbkdf2_sha512.verify("492354offline", response.get('199')))
        res = tokenobject.check_otp("492354")  # count = 199
        self.assertEqual(res, -1)
        # check that we can authenticate online with the correct value
        res = tokenobject.check_otp("462985")  # count = 201
        self.assertEqual(res, 201)
        # Revert
        set_privacyidea_config(SYSCONF.PREPENDPIN, True)

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
        resp = jsonify(res)
        from privacyidea.lib.crypto import Sign
        with open("tests/testdata/public.pem", 'rb') as f:
            public_key = f.read()
        sign_object = Sign(private_key=None, public_key=public_key)

        # check that we don't sign if 'PI_NO_RESPONSE_SIGN' is set
        current_app.config['PI_NO_RESPONSE_SIGN'] = True
        new_response = sign_response(req, resp)
        self.assertEqual(new_response, resp, new_response)
        current_app.config['PI_NO_RESPONSE_SIGN'] = False

        # set a broken signing key path. The function should return without
        # changing the response
        orig_key_path = current_app.config['PI_AUDIT_KEY_PRIVATE']
        current_app.config['PI_AUDIT_KEY_PRIVATE'] = '/path/does/not/exist'
        new_response = sign_response(req, resp)
        self.assertEqual(new_response, resp, new_response)
        current_app.config['PI_AUDIT_KEY_PRIVATE'] = orig_key_path

        # signing of API responses is the default
        new_response = sign_response(req, resp)
        jresult = new_response.json
        self.assertEqual(jresult.get("nonce"), "12345678")
        # After switching to the PSS signature scheme, each signature will be
        # different. So we have to verify the signature through the sign object
        sig = jresult.pop('signature')
        self.assertTrue(sign_object.verify(json.dumps(jresult, sort_keys=True), sig))

    def test_08_get_webui_settings(self):
        self.setUp_user_realms()
        # The request with an OTP value and a PIN of a user, who has no token assigned
        builder = EnvironBuilder(method='POST',
                                 data={},
                                 headers={})
        env = builder.get_environ()
        env["REMOTE_ADDR"] = "192.168.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.User = User("cornelius", self.realm1)
        req.all_data = {"user": "cornelius",
                        "pass": "offline287082"}

        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": {"role": "user",
                                    "username": "cornelius",
                                    "realm": self.realm1}},
               "version": "privacyIDEA test",
               "detail": {"serial": None},
               "id": 1}
        resp = jsonify(res)

        new_response = get_webui_settings(req, resp)
        jresult = new_response.json
        self.assertEqual(jresult.get("result").get("value").get(
            "token_wizard"), False)
        self.assertEqual(jresult.get("result").get("value").get("logout_redirect_url"),
                         "", jresult)

        # Set a policy. User has not token, so "token_wizard" will be True
        set_policy(name="pol_wizard",
                   scope=SCOPE.WEBUI,
                   action=PolicyAction.TOKENWIZARD)
        g.policy_object = PolicyClass()
        new_response = get_webui_settings(req, resp)
        jresult = new_response.json
        self.assertEqual(jresult.get("result").get("value").get(
            "token_wizard"), True)

        # Assert the policy is not honored if inactive
        set_policy(name="pol_wizard",
                   active=False)
        g.policy_object = PolicyClass()
        new_response = get_webui_settings(req, resp)
        jresult = new_response.json
        self.assertEqual(jresult.get("result").get("value").get(
            "token_wizard"), False)

        delete_policy("pol_wizard")

        # check if the dialog_no_token will not be displayed
        self.assertEqual(jresult.get("result").get("value").get(
            "dialog_no_token"), False)

        # Now set a policy and check again
        set_policy(name="pol_dialog", scope=SCOPE.WEBUI, action=PolicyAction.DIALOG_NO_TOKEN)
        g.policy_object = PolicyClass()
        new_response = get_webui_settings(req, resp)
        jresult = new_response.json
        self.assertEqual(jresult.get("result").get("value").get(
            PolicyAction.DIALOG_NO_TOKEN), True)
        delete_policy("pol_dialog")

        # Set a policy for the QR codes
        set_policy(name="pol_qr1", scope=SCOPE.WEBUI, action=PolicyAction.SHOW_ANDROID_AUTHENTICATOR)
        set_policy(name="pol_qr2", scope=SCOPE.WEBUI, action=PolicyAction.SHOW_IOS_AUTHENTICATOR)
        set_policy(name="pol_qr3", scope=SCOPE.WEBUI,
                   action="{0!s}=http://privacyidea.org".format(PolicyAction.SHOW_CUSTOM_AUTHENTICATOR))

        android_url_image = create_img(DEFAULT_ANDROID_APP_URL)
        ios_url_image = create_img(DEFAULT_IOS_APP_URL)
        custom_url = create_img("http://privacyidea.org")
        g.policy_object = PolicyClass()
        new_response = get_webui_settings(req, resp)
        jresult = new_response.json
        self.assertEqual(android_url_image,
                         jresult.get("result").get("value").get("qr_image_android"))
        self.assertEqual(ios_url_image,
                         jresult.get("result").get("value").get("qr_image_ios"))
        qr_image_custom = jresult.get("result").get("value").get("qr_image_custom")
        self.assertEqual(len(custom_url), len(qr_image_custom))
        self.assertEqual(custom_url, qr_image_custom)

        delete_policy("pol_qr1")
        delete_policy("pol_qr2")
        delete_policy("pol_qr3")

        # Test if the webui gets the information about the preset attribute for indexedsecret token
        set_policy(name="pol_indexed1", scope=SCOPE.WEBUI,
                   action="indexedsecret_{0!s}=preattr".format(PIIXACTION.PRESET_ATTRIBUTE))

        g.policy_object = PolicyClass()
        new_response = get_webui_settings(req, resp)
        jresult = new_response.json
        self.assertEqual("preattr",
                         jresult.get("result").get("value").get("indexedsecret_preset_attribute"))

        delete_policy("pol_indexed1")

        # Test if the webui gets the information, that a normal user has force_attribute
        set_policy(name="pol_indexed_force", scope=SCOPE.USER,
                   action="indexedsecret_{0!s}=force".format(PIIXACTION.FORCE_ATTRIBUTE))
        g.policy_object = PolicyClass()
        new_response = get_webui_settings(req, resp)
        jresult = new_response.json
        # Check that the force_attribute indicator is set to "1"
        self.assertEqual(1, jresult.get("result").get("value").get("indexedsecret_force_attribute"))
        delete_policy("pol_indexed_force")

        # Test if the logout_redirect URL is set
        redir_uri = 'https://redirect.to'
        set_policy(name="pol_logout_redirect", scope=SCOPE.WEBUI,
                   action="{0!s}={1!s}".format(PolicyAction.LOGOUT_REDIRECT, redir_uri))
        g.policy_object = PolicyClass()
        new_response = get_webui_settings(req, resp)
        jresult = new_response.json
        self.assertEqual(redir_uri,
                         jresult.get("result").get("value").get("logout_redirect_url"),
                         jresult)
        delete_policy("pol_logout_redirect")

        # Test default container type
        # policy not set: default is generic
        self.assertEqual("generic", new_response.json["result"]["value"]["default_container_type"])
        # Set smartphone as default
        set_policy(name="default_container", scope=SCOPE.WEBUI,
                   action={PolicyAction.DEFAULT_CONTAINER_TYPE: "smartphone"})
        g.policy_object = PolicyClass()
        new_response = get_webui_settings(req, resp)
        self.assertEqual("smartphone", new_response.json["result"]["value"]["default_container_type"])
        delete_policy("default_container")

    def test_09_get_webui_settings_token_pagesize(self):
        # Test that policies like tokenpagesize are also user dependent
        self.setUp_user_realms()

        # The request with an OTP value and a PIN of a user, who has no token assigned
        builder = EnvironBuilder(method='POST',
                                 data={},
                                 headers={})
        env = builder.get_environ()
        env["REMOTE_ADDR"] = "192.168.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.User = User("cornelius", self.realm1)
        req.all_data = {"user": "cornelius",
                        "pass": "offline287082"}

        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": {"role": "user",
                                    "username": "cornelius",
                                    "realm": self.realm1}},
               "version": "privacyIDEA test",
               "id": 1}
        resp = jsonify(res)

        new_response = get_webui_settings(req, resp)
        jresult = new_response.json
        self.assertEqual(jresult.get("result").get("value").get(
            PolicyAction.TOKENPAGESIZE), 15)

        # Set a policy. User has not token, so "token_wizard" will be True
        set_policy(name="pol_pagesize",
                   scope=SCOPE.WEBUI,
                   realm=self.realm1,
                   action="{0!s}=177".format(PolicyAction.TOKENPAGESIZE))
        g.policy_object = PolicyClass()
        new_response = get_webui_settings(req, resp)
        jresult = new_response.json
        self.assertEqual(jresult.get("result").get("value").get(
            PolicyAction.TOKENPAGESIZE), 177)

        # Now we change the policy pol_pagesize this way, that it is only valid for the user "root"
        set_policy(name="pol_pagesize",
                   scope=SCOPE.WEBUI,
                   realm=self.realm1,
                   user="root",
                   action="{0!s}=177".format(PolicyAction.TOKENPAGESIZE))
        # This way the user "cornelius" gets the default pagesize again
        g.policy_object = PolicyClass()
        new_response = get_webui_settings(req, resp)
        jresult = new_response.json
        self.assertEqual(jresult.get("result").get("value").get(
            PolicyAction.TOKENPAGESIZE), 15)

        delete_policy("pol_pagesize")

    def test_10_get_webui_settings_admin_dashboard(self):
        # Test admin_dashboard
        self.setUp_user_realms()

        # The request with an OTP value and a PIN of a user, who has no token assigned
        builder = EnvironBuilder(method='POST',
                                 data={},
                                 headers={})
        env = builder.get_environ()
        env["REMOTE_ADDR"] = "192.168.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.User = User()
        req.all_data = {}

        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": {"role": "admin",
                                    "username": "cornelius",
                                    "realm": ""}},
               "version": "privacyIDEA test",
               "id": 1}
        resp = jsonify(res)

        new_response = get_webui_settings(req, resp)
        jresult = new_response.json
        self.assertEqual(jresult.get("result").get("value").get(
            "admin_dashboard"), False)

        # Set a policy. Admin can see the dashboard
        set_policy(name="pol_dashboard",
                   scope=SCOPE.WEBUI,
                   action=PolicyAction.ADMIN_DASHBOARD)
        g.policy_object = PolicyClass()
        new_response = get_webui_settings(req, resp)
        jresult = new_response.json
        self.assertTrue(jresult.get("result").get("value").get(PolicyAction.ADMIN_DASHBOARD))

        delete_policy("pol_dashboard")

    def test_11_get_webui_settings_support_link(self):
        # Test the link to the support
        self.setUp_user_realms()

        # The request with an OTP value and a PIN of a user, who has no token assigned
        builder = EnvironBuilder(method='POST',
                                 data={},
                                 headers={})
        env = builder.get_environ()
        env["REMOTE_ADDR"] = "192.168.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.User = User()
        req.all_data = {}

        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": {"role": "admin",
                                    "username": "cornelius",
                                    "realm": ""}},
               "version": "privacyIDEA test",
               "id": 1}
        resp = jsonify(res)

        new_response = get_webui_settings(req, resp)
        jresult = new_response.json
        self.assertNotIn("supportmail", jresult.get("result").get("value"))

        # Add a subscription
        from privacyidea.models import Subscription
        Subscription(application="privacyidea",
                     for_name="testuser",
                     for_email="admin@example.com",
                     for_phone="0",
                     by_name="privacyIDEA project",
                     by_email="privacyidea@example.com",
                     date_from=datetime.utcnow(),
                     date_till=datetime.utcnow() + timedelta(days=365),
                     num_users=100,
                     num_tokens=100,
                     num_clients=100
                     ).save()
        new_response = get_webui_settings(req, resp)
        jresult = new_response.json
        self.assertIn("privacyidea@example.com", jresult.get("result").get("value").get("supportmail"))
        self.assertIn(str(EXPIRE_MESSAGE), jresult.get("result").get("value").get("supportmail"))

    def test_12_get_webui_settings_container_wizard(self):
        self.setUp_user_realms()

        # Mock request
        builder = EnvironBuilder(method="POST", data={}, headers={})
        env = builder.get_environ()
        req = Request(env)
        req.User = User("cornelius", self.realm1)
        req.all_data = {}

        user_response = {"jsonrpc": "2.0",
                         "result": {"status": True,
                                    "value": {"role": "user",
                                              "username": "cornelius",
                                              "realm": self.realm1}},
                         "version": "privacyIDEA test",
                         "id": 1}
        admin_response = {"jsonrpc": "2.0",
                          "result": {"status": True,
                                     "value": {"role": "admin",
                                               "username": "cornelius",
                                               "realm": ""}},
                          "version": "privacyIDEA test",
                          "id": 1}

        # User without container, but no container wizard defined
        resp = jsonify(user_response)
        new_response = get_webui_settings(req, resp)
        self.assertFalse(new_response.json["result"]["value"]["container_wizard"]["enabled"])

        # Set container wizard policy only for template, but not type
        set_policy(name="container_wizard", scope=SCOPE.WEBUI,
                   action={PolicyAction.CONTAINER_WIZARD_TEMPLATE: "test(generic)"})
        # User without container, but container wizard type is missing
        resp = jsonify(user_response)
        new_response = get_webui_settings(req, resp)
        self.assertFalse(new_response.json["result"]["value"]["container_wizard"]["enabled"])
        self.assertEqual(1, len(new_response.json["result"]["value"]["container_wizard"].keys()))
        delete_policy("container_wizard")

        # define correct policy
        set_policy(name="container_wizard", scope=SCOPE.WEBUI,
                   action={PolicyAction.CONTAINER_WIZARD_TYPE: "generic",
                           PolicyAction.CONTAINER_WIZARD_TEMPLATE: "test(generic)"})
        # User without container
        resp = jsonify(user_response)
        new_response = get_webui_settings(req, resp)
        container_wizard = new_response.json["result"]["value"]["container_wizard"]
        self.assertTrue(container_wizard["enabled"])
        self.assertEqual("generic", container_wizard["type"])
        self.assertEqual("test", container_wizard["template"])
        self.assertFalse(container_wizard["registration"])

        # Admin without container: container wizard disabled
        resp = jsonify(admin_response)
        req.User = User()
        new_response = get_webui_settings(req, resp)
        container_wizard = new_response.json["result"]["value"]["container_wizard"]
        self.assertFalse(container_wizard["enabled"])
        self.assertEqual(1, len(container_wizard.keys()))

        # User with container: container wizard disabled
        container_serial = init_container({"type": "generic", "user": "cornelius", "realm": self.realm1})[
            "container_serial"]
        resp = jsonify(user_response)
        req.User = User("cornelius", self.realm1)
        new_response = get_webui_settings(req, resp)
        container_wizard = new_response.json["result"]["value"]["container_wizard"]
        self.assertFalse(container_wizard["enabled"])
        self.assertEqual(1, len(container_wizard.keys()))
        find_container_by_serial(container_serial).delete()
        delete_policy("container_wizard")

        # container wizard with registration
        set_policy(name="container_wizard", scope=SCOPE.WEBUI,
                   action=f"{PolicyAction.CONTAINER_WIZARD_TYPE}=smartphone,{PolicyAction.CONTAINER_WIZARD_REGISTRATION}")
        # User without container
        resp = jsonify(user_response)
        new_response = get_webui_settings(req, resp)
        container_wizard = new_response.json["result"]["value"]["container_wizard"]
        self.assertTrue(container_wizard["enabled"])
        self.assertEqual("smartphone", container_wizard["type"])
        self.assertIsNone(container_wizard["template"])
        self.assertTrue(container_wizard["registration"])
        delete_policy("container_wizard")

    def test_16_init_token_defaults(self):
        g.logged_in_user = {"username": "cornelius",
                            "realm": "",
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
        self.assertEqual(req.all_data.get("hashlib"), "sha256")
        self.assertEqual(req.all_data.get("otplen"), "8")
        self.assertEqual(req.all_data.get("timeStep"), "60")
        # finally delete policy
        delete_policy("pol1")

        # check that it works in admin scope as well
        set_policy(name="pol1",
                   scope=SCOPE.ADMIN,
                   action="hotp_otplen=8,hotp_hashlib=sha512")
        g.policy_object = PolicyClass()
        g.logged_in_user = {"username": "admin",
                            "realm": "super",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 data={'type': "hotp",
                                       "genkey": "1"},
                                 headers={})
        env = builder.get_environ()
        req = Request(env)
        # request, that matches the policy
        req.all_data = {
            "type": "hotp",
            "genkey": "1"}
        init_token_defaults(req)

        # Check, if the token defaults were added
        self.assertEqual(req.all_data.get("hashlib"), "sha512")
        self.assertEqual(req.all_data.get("otplen"), "8")
        # finally delete policy
        delete_policy("pol1")

    def test_17_pin_change(self):
        g.logged_in_user = {"username": "admin",
                            "realm": "",
                            "role": "admin"}
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
                   scope=SCOPE.ENROLL,
                   action=PolicyAction.CHANGE_PIN_FIRST_USE)
        g.policy_object = PolicyClass()

        # request, that matches the policy
        #
        # Take the serialnumber from the request data
        req.all_data = {
            "type": "spass",
            "serial": "changePIN1"}

        # The response contains the token serial
        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": True},
               "version": "privacyIDEA test",
               "id": 1,
               "detail": {"message": "matching 1 tokens",
                          "serial": "changePIN1",
                          "type": "spass"}}
        resp = jsonify(res)

        # the token itself
        token = init_token({"serial": "changePIN1",
                            "type": "spass"}, tokenrealms=[self.realm1])
        save_pin_change(req, resp)
        ti = token.get_tokeninfo("next_pin_change")
        ndate = datetime.now(tzlocal()).strftime(DATE_FORMAT)
        self.assertEqual(ti, ndate)

        #
        # check a token without a given serial
        #
        # take the serial number from the response data
        req.all_data = {
            "type": "spass",
            "pin": "123456"}

        # The response contains the token serial
        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": True},
               "version": "privacyIDEA test",
               "id": 1,
               "detail": {"message": "matching 1 tokens",
                          "serial": "changePIN2",
                          "type": "spass"}}
        resp = jsonify(res)

        token = init_token({"type": "spass",
                            "serial": "changePIN2"}, tokenrealms=[self.realm1])

        save_pin_change(req, resp)
        ti = token.get_tokeninfo("next_pin_change")
        ndate = datetime.now(tzlocal()).strftime(DATE_FORMAT)
        self.assertTrue(ti, ndate)

        # Now the user changes the PIN. Afterwards the next_pin_change is empty
        g.logged_in_user = {"username": "hans",
                            "realm": "",
                            "role": "user"}

        save_pin_change(req, resp, serial="changePIN2")
        ti = token.get_tokeninfo("next_pin_change")
        self.assertEqual(ti, None)

        # change PIN every day. The next_pin_change will be
        set_policy(name="pol2", scope=SCOPE.ENROLL,
                   action="{0!s}=1d".format(PolicyAction.CHANGE_PIN_EVERY))
        g.policy_object = PolicyClass()
        save_pin_change(req, resp)
        ti = token.get_tokeninfo("next_pin_change")
        ndate = (datetime.now(tzlocal()) + timedelta(1)).strftime(DATE_FORMAT)
        self.assertTrue(ti, ndate)

        # finally delete policy
        delete_policy("pol1")
        delete_policy("pol2")

    def test_18_challenge_text_header(self):
        # This looks like a validate/check request, that triggers a challenge
        builder = EnvironBuilder(method='POST',
                                 data={'user': "hans",
                                       "pass": "pin"},
                                 headers={})

        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)

        # Set a policy for the header
        set_policy(name="pol_header",
                   scope=SCOPE.AUTH,
                   action="{0!s}=These are your options:<ul>".format(PolicyAction.CHALLENGETEXT_HEADER))
        # Set a policy for the footer
        set_policy(name="pol_footer",
                   scope=SCOPE.AUTH,
                   action="{0!s}=Happy authenticating!".format(PolicyAction.CHALLENGETEXT_FOOTER))
        g.policy_object = PolicyClass()

        req.all_data = {
            "user": "hans",
            "pass": "pin"}
        req.User = User()

        # We do an html list
        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": False},
               "version": "privacyIDEA test",
               "id": 1,
               "detail": {"message": "enter the HOTP from your email, "
                                     "enter the HOTP from your email, "
                                     "enter the TOTP from your SMS",
                          "messages": ["enter the HOTP from your email",
                                       "enter the HOTP from your email",
                                       "enter the TOTP from your SMS"],
                          "multi_challenge": ["chal1", "chal2", "chal3"]}}
        resp = jsonify(res)

        r = mangle_challenge_response(req, resp)
        message = r.json.get("detail", {}).get("message")
        self.assertEqual(message,
                         "These are your options:<ul><li>enter the HOTP from your email</li>\n"
                         "<li>enter the TOTP from your SMS</li>\nHappy authenticating!")

        # We do no html list
        set_policy(name="pol_header",
                   scope=SCOPE.AUTH,
                   action="{0!s}=These are your options:".format(PolicyAction.CHALLENGETEXT_HEADER))
        g.policy_object = PolicyClass()
        resp = jsonify(res)

        r = mangle_challenge_response(req, resp)
        message = r.json.get("detail", {}).get("message")
        self.assertTrue("<ul><li>" not in message, message)
        self.assertEqual(message,
                         "These are your options:\n"
                         "enter the HOTP from your email, enter the TOTP from your SMS\nHappy authenticating!")

        delete_policy("pol_header")
        delete_policy("pol_footer")

    def test_19_is_authorized(self):
        # Test authz authorized policy
        builder = EnvironBuilder(method='POST',
                                 data={'user': "cornelius",
                                       "pass": "test123123"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        self.setUp_user_realms()
        req.User = User("autoassignuser", self.realm1)
        # The response contains the token type HOTP, successful authentication
        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": True},
               "version": "privacyIDEA test",
               "id": 1,
               "detail": {"message": "matching 1 tokens",
                          "serial": "HOTP123456",
                          "type": "hotp"}}
        resp = jsonify(res)
        g.policy_object = PolicyClass()

        # The response is unchanged
        new_resp = is_authorized(req, resp)
        self.assertEqual(resp, new_resp)

        # Define a generic policy, that denies the request
        set_policy("auth01", scope=SCOPE.AUTHZ, action="{0!s}={1!s}".format(PolicyAction.AUTHORIZED, AUTHORIZED.DENY),
                   priority=2)
        g.policy_object = PolicyClass()

        # The request will fail.
        self.assertRaises(ValidateError, is_authorized, req, resp)

        # Now we set a 2nd policy with a higher priority
        set_policy("auth02", scope=SCOPE.AUTHZ, action="{0!s}={1!s}".format(PolicyAction.AUTHORIZED, AUTHORIZED.ALLOW),
                   priority=1, client="10.0.0.0/8")
        g.policy_object = PolicyClass()

        # The response is unchanged, authentication successful
        new_resp = is_authorized(req, resp)
        self.assertEqual(resp, new_resp)

        delete_policy("auth01")
        delete_policy("auth02")

    def test_20_verify_enrollment(self):
        # Test verify enrollment policy
        serial = "HOTP123456"
        tok = init_token({"serial": serial,
                          "type": "hotp",
                          "otpkey": "31323334353637383040"})
        builder = EnvironBuilder(method='POST',
                                 data={'user': "cornelius",
                                       'genkey': 1,
                                       'type': 'hotp'},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {}
        self.setUp_user_realms()
        req.User = User("autoassignuser", self.realm1)
        # The response contains the token type HOTP, enrollment
        from privacyidea.lib.tokens.hotptoken import VERIFY_ENROLLMENT_MESSAGE
        from privacyidea.lib.tokenclass import RolloutState
        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": True},
               "version": "privacyIDEA test",
               "id": 1,
               "detail": {"serial": serial}}
        resp = jsonify(res)
        g.policy_object = PolicyClass()

        # The response is unchanged
        new_resp = check_verify_enrollment(req, resp)
        self.assertEqual(resp, new_resp)

        # Define a verify enrollment policy
        set_policy("verify_toks", scope=SCOPE.ENROLL, action="{0!s}=hotp".format(PolicyAction.VERIFY_ENROLLMENT))
        g.policy_object = PolicyClass()

        new_resp = check_verify_enrollment(req, resp)
        detail = new_resp.json.get("detail")
        self.assertEqual(detail.get("verify").get("message"), VERIFY_ENROLLMENT_MESSAGE)
        self.assertEqual(detail.get("rollout_state"), RolloutState.VERIFY_PENDING)
        # Also check the token object.
        self.assertEqual(tok.token.rollout_state, RolloutState.VERIFY_PENDING)
        delete_policy("verify_toks")

    def test_20a_verify_enrollment_no_serial(self):
        """Test verify_enrollment prepolicy with no serial - should return early"""
        builder = EnvironBuilder(method='POST', data={}, headers={})
        env = builder.get_environ()
        req = Request(env)
        req.all_data = {"verify": "123456"}  # verify present but no serial

        # Should return None without error (early exit)
        result = verify_enrollment(req, None)
        self.assertIsNone(result)

    def test_20b_verify_enrollment_token_not_found(self):
        """Test verify_enrollment prepolicy with non-existent serial - should return early

        This tests the early exit when len(token_list) != 1 (specifically when len == 0).
        The case where len > 1 cannot occur because serial is a unique database constraint.
        """
        builder = EnvironBuilder(method='POST', data={}, headers={})
        env = builder.get_environ()
        req = Request(env)
        req.all_data = {"serial": "NONEXISTENT", "verify": "123456"}

        # Should return None without error (early exit - token not found, len(token_list) == 0)
        result = verify_enrollment(req, None)
        self.assertIsNone(result)

    def test_20c_verify_enrollment_missing_verify_param(self):
        """Test verify_enrollment prepolicy with token in verify_pending but no verify param - should raise an error"""
        from privacyidea.lib.tokenclass import RolloutState
        from privacyidea.lib.error import ParameterError

        serial = "HOTP_VERIFY_PENDING"
        tok = init_token({"serial": serial,
                          "type": "hotp",
                          "otpkey": "31323334353637383940"})
        # Set token to VERIFY_PENDING state
        tok.token.rollout_state = RolloutState.VERIFY_PENDING
        tok.save()

        builder = EnvironBuilder(method='POST', data={}, headers={})
        env = builder.get_environ()
        req = Request(env)
        req.all_data = {"serial": serial}  # No verify parameter

        # Should raise ParameterError
        with self.assertRaises(ParameterError) as cm:
            verify_enrollment(req, None)

        self.assertIn("verify_pending", str(cm.exception))
        self.assertIn("verify", str(cm.exception).lower())

        # Token should still be in verify_pending state
        tok = get_tokens(serial=serial)[0]
        self.assertEqual(tok.token.rollout_state, RolloutState.VERIFY_PENDING)
        remove_token(serial)

    def test_20d_verify_enrollment_wrong_verify_value(self):
        """Test verify_enrollment prepolicy with wrong verify value - should raise error"""
        from privacyidea.lib.tokenclass import RolloutState
        from privacyidea.lib.error import ParameterError

        serial = "HOTP_VERIFY_WRONG"
        tok = init_token({"serial": serial,
                          "type": "hotp",
                          "otpkey": "31323334353637383940"})
        # Set token to VERIFY_PENDING state
        tok.token.rollout_state = RolloutState.VERIFY_PENDING
        tok.save()

        builder = EnvironBuilder(method='POST', data={}, headers={})
        env = builder.get_environ()
        req = Request(env)
        req.all_data = {"serial": serial, "verify": "wrong_value"}

        # Should raise ParameterError for wrong verification
        with self.assertRaises(ParameterError) as cm:
            verify_enrollment(req, None)

        self.assertIn("Verification of the new token failed", str(cm.exception))

        # Token should still be in verify_pending state
        tok = get_tokens(serial=serial)[0]
        self.assertEqual(tok.token.rollout_state, RolloutState.VERIFY_PENDING)
        remove_token(serial)

    def test_20e_verify_enrollment_not_in_verify_pending_state(self):
        """Test verify_enrollment prepolicy with token not in verify_pending state - should exit early"""
        from privacyidea.lib.tokenclass import RolloutState

        serial = "HOTP_NOT_VERIFY_PENDING"
        tok = init_token({"serial": serial,
                          "type": "hotp",
                          "otpkey": "31323334353637383940"})
        # Token that are enrolled directly without verify or 2step have the empty enrollment state
        # TODO should be unified
        self.assertEqual(tok.token.rollout_state, "")

        builder = EnvironBuilder(method='POST', data={}, headers={})
        env = builder.get_environ()
        req = Request(env)
        req.all_data = {"serial": serial, "verify": "123456"}

        # Should return None without error (early exit - not in verify_pending state)
        result = verify_enrollment(req, None)
        self.assertIsNone(result)

        # Token should still be empty (unchanged)
        tok = get_tokens(serial=serial)[0]
        self.assertEqual(tok.token.rollout_state, "")
        remove_token(serial)

    def test_20f_verify_enrollment_success(self):
        """Test verify_enrollment prepolicy happy path - successful verification"""
        from privacyidea.lib.tokenclass import RolloutState

        otpkey_hex = ("5287c8247735148e48cc66412e8510de0414eb996da86edf18d944dd9844d13f9b804fce48a4c6d3f43f27788f70122b"
                      "457dffc12563e8d319c23c8b6fac5395")
        first_otp = "148752"

        serial = "HOTP_VERIFY_SUCCESS"
        tok = init_token({"serial": serial,
                          "type": "hotp",
                          "otpkey": otpkey_hex})
        # Set token to VERIFY_PENDING state
        tok.token.rollout_state = RolloutState.VERIFY_PENDING
        tok.save()

        builder = EnvironBuilder(method='POST', data={}, headers={})
        env = builder.get_environ()
        req = Request(env)
        req.all_data = {"serial": serial, "verify": first_otp, "type": "hotp"}

        # Should succeed without raising an error
        result = verify_enrollment(req, None)
        self.assertIsNone(result)  # prepolicy returns None on success

        # Token should now be in ENROLLED state
        tok = get_tokens(serial=serial)[0]
        self.assertEqual(tok.token.rollout_state, RolloutState.ENROLLED)

        # Verify that the OTP counter was incremented (token consumed the OTP)
        # The same OTP should not work again
        r = tok.check_otp(first_otp)
        self.assertEqual(r, -1)  # -1 means OTP already used

        remove_token(serial)

    def test_21_preferred_client_mode_for_user_allowed(self):
        """
        Tests the preferred_client_mode function when the policy client_mode_per_user is activated.
        """
        # Mock request
        builder = EnvironBuilder(method="POST", data={}, headers=Headers({"user_agent": "privacyidea-cp"}))
        env = builder.get_environ()
        request = Request(env)
        request.all_data = {}
        self.setUp_user_realms()
        user = User("hans", self.realm1)
        request.User = user

        response_data = {"jsonrpc": "2.0",
                         "result": {"status": True, "value": True},
                         "version": "privacyIDEA test",
                         "detail": {"multi_challenge": []}
                         }
        g.policy_object = PolicyClass()

        # Allow to use preferred client mode per user
        set_policy("user_client_mode", scope=SCOPE.AUTH, action=PolicyAction.CLIENT_MODE_PER_USER)

        # No custom user attribute available for the user and no policy: use default
        multi_challenge = [
            {"client_mode": "interactive", "type": "hotp", "transaction_id": "", "serial": "", "message": ""},
            {"client_mode": "poll", "type": "push", "transaction_id": "", "serial": "", "message": ""},
            {"client_mode": "webauthn", "type": "webauthn", "transaction_id": "", "serial": "", "message": ""}
        ]
        response_data["detail"]["multi_challenge"] = multi_challenge
        response = jsonify(response_data)

        preferred_client_mode(request, response)

        response_details = response.json["detail"]
        self.assertEqual("interactive", response_details.get("preferred_client_mode"))

        # No preferred client mode policy set only custom user attribute: use user+application preference
        response = jsonify(response_data)
        user.set_attribute(f"{InternalCustomUserAttributes.LAST_USED_TOKEN}_privacyidea-cp", "push", INTERNAL_USAGE)
        user.set_attribute(f"{InternalCustomUserAttributes.LAST_USED_TOKEN}_privacyidea-Shibbole", "u2f",
                           INTERNAL_USAGE)

        preferred_client_mode(request, response)

        response_details = response.json["detail"]
        self.assertEqual("poll", response_details.get("preferred_client_mode"))

        # preferred client mode policy with webauthn first, but user prefers push
        set_policy("preferred_client_mode", scope=SCOPE.AUTH,
                   action={PolicyAction.PREFERREDCLIENTMODE: "webauthn interactive poll"})
        response = jsonify(response_data)

        preferred_client_mode(request, response)
        response_details = response.json["detail"]
        self.assertEqual("poll", response_details.get("preferred_client_mode"))

        # preferred user token not in multi-challenge: use preferred client mode policy
        multi_challenge = [
            {"client_mode": "interactive", "type": "hotp", "transaction_id": "", "serial": "", "message": ""},
            {"client_mode": "webauthn", "type": "webauthn", "transaction_id": "", "serial": "", "message": ""}
        ]
        response_data["detail"]["multi_challenge"] = multi_challenge
        response = jsonify(response_data)

        preferred_client_mode(request, response)
        response_details = response.json["detail"]
        self.assertEqual("webauthn", response_details.get("preferred_client_mode"))

        # preferred user token not in multi-challenge and no preferred_client_mode policy: use default
        delete_policy("preferred_client_mode")
        response = jsonify(response_data)
        preferred_client_mode(request, response)
        response_details = response.json["detail"]
        self.assertEqual("interactive", response_details.get("preferred_client_mode"))

        delete_policy("user_client_mode")

    def test_22_preferred_client_mode_for_user_denied(self):
        """
        Tests the preferred_client_mode function when the policy client_mode_per_user is not activated.
        """
        # Mock request
        builder = EnvironBuilder(method='POST', data={}, headers=Headers({"user_agent": "privacyidea-cp"}))
        env = builder.get_environ()
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        request = Request(env)
        request.all_data = {}
        self.setUp_user_realms()
        user = User("hans", self.realm1)
        request.User = user

        response_data = {"jsonrpc": "2.0",
                         "result": {"status": True, "value": True},
                         "version": "privacyIDEA test",
                         "detail": {"multi_challenge": []}
                         }
        g.policy_object = PolicyClass()

        multi_challenge = [
            {"client_mode": "interactive", "type": "hotp", "transaction_id": "", "serial": "", "message": ""},
            {"client_mode": "poll", "type": "push", "transaction_id": "", "serial": "", "message": ""},
            {"client_mode": "webauthn", "type": "webauthn", "transaction_id": "", "serial": "", "message": ""}
        ]
        response_data["detail"]["multi_challenge"] = multi_challenge
        response = jsonify(response_data)
        user.set_attribute(f"{InternalCustomUserAttributes.LAST_USED_TOKEN}_privacyidea-cp", "push", INTERNAL_USAGE)

        # set any policy in scope AUTH
        set_policy("challenge", scope=SCOPE.AUTH, action={PolicyAction.CHALLENGERESPONSE: "hotp"})

        # user_client_mode not allowed and also no preferred_client_mode policy: use default
        preferred_client_mode(request, response)
        response_details = response.json["detail"]
        self.assertEqual("interactive", response_details.get("preferred_client_mode"))

        # user_client_mode not allowed: use preferred_client_mode policy: webauthn
        set_policy("preferred_client_mode", scope=SCOPE.AUTH,
                   action={PolicyAction.PREFERREDCLIENTMODE: "webauthn interactive poll"})
        response = jsonify(response_data)

        preferred_client_mode(request, response)
        response_details = response.json["detail"]
        self.assertEqual("webauthn", response_details.get("preferred_client_mode"))

        delete_policy("preferred_client_mode")
        delete_policy("challenge")

    def test_23_enroll_via_multichallenge_smartphone_is_triggered(self):
        """
        Here we only test that the enroll_via_multichallenge is triggered correctly for different scenarios
        """
        template_options = {"tokens": [{"type": "hotp", "genkey": True}, {"type": "totp", "genkey": True}]}
        create_container_template(container_type="smartphone", template_name="test", options=template_options)
        set_policy("enroll_via_multichallenge", scope=SCOPE.AUTH,
                   action={PolicyAction.ENROLL_VIA_MULTICHALLENGE: "smartphone", PolicyAction.PASSTHRU: True})
        set_policy("registration", scope=SCOPE.CONTAINER, action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.net/"})

        self.setUp_user_realms()
        hans = User("hans", self.realm1)

        # Mock request
        builder = EnvironBuilder(method='POST', data={}, headers=Headers({"user_agent": "privacyidea-cp"}))
        env = builder.get_environ()
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        request = Request(env)
        request.all_data = {}
        request.User = hans
        g.policy_object = PolicyClass()
        g.policies = {}

        response_data = {"jsonrpc": "2.0",
                         "result": {"status": True, "value": True, "authentication": AUTH_RESPONSE.ACCEPT},
                         "version": "privacyIDEA test"}
        response = jsonify(response_data)

        def check_response(response, message=None):
            result = response.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertFalse(result.get("value"))
            self.assertEqual(AUTH_RESPONSE.CHALLENGE, result.get("authentication"))
            details = response.json.get("detail", {})
            self.assertIn("multi_challenge", details)
            self.assertEqual(1, len(details.get("multi_challenge", [])))
            challenge_data = details.get("multi_challenge")[0]
            # Data in the challenge is equal to the data in the details
            self.assertEqual(details.get("serial"), challenge_data.get("serial"))
            self.assertEqual(details.get("type"), challenge_data.get("type"))
            self.assertEqual(details.get("transaction_id"), challenge_data.get("transaction_id"))
            self.assertEqual(details.get("client_mode"), challenge_data.get("client_mode"))
            self.assertEqual(details.get("message"), challenge_data.get("message"))
            self.assertEqual(details.get("image"), challenge_data.get("image"))
            self.assertEqual(details.get("link"), challenge_data.get("link"))
            # As it is equal we only need to check for valid values once
            self.assertEqual("smartphone", challenge_data.get("type"))
            self.assertEqual("poll", challenge_data.get("client_mode"))
            self.assertTrue(challenge_data.get("link").startswith("pia://container"))
            # Default message
            message = message or "Please scan the QR code to register the container."
            self.assertEqual(message, challenge_data.get("message"))

        # User has no container
        response = multichallenge_enroll_via_validate(request, response)
        check_response(response)
        container = find_container_by_serial(response.json.get("detail").get("serial"))
        # container is created without template hence there are no tokens
        self.assertEqual(0, len(container.tokens))
        # clean up
        container.delete()
        response = jsonify(response_data)

        # User has token, but no container
        g.policies = {}
        token = init_token({"type": "hotp", "genkey": True}, user=hans)
        response = multichallenge_enroll_via_validate(request, response)
        check_response(response)
        # clean up
        token.delete_token()
        [container.delete() for container in get_all_containers(user=hans)["containers"]]
        response = jsonify(response_data)

        # User has generic container, but not smartphone container
        g.policies = {}
        init_container({"type": "generic", "user": "hans", "realm": self.realm1})["container_serial"]
        response = multichallenge_enroll_via_validate(request, response)
        check_response(response)
        # clean up
        [container.delete() for container in get_all_containers(user=hans)["containers"]]
        response = jsonify(response_data)

        # User has smartphone container, but it is not registered
        g.policies = {}
        container_serial = init_container({"type": "smartphone", "user": "hans", "realm": self.realm1})[
            "container_serial"]
        response = multichallenge_enroll_via_validate(request, response)
        check_response(response)
        self.assertEqual(container_serial, response.json.get("detail").get("serial"))
        # clean up
        [container.delete() for container in get_all_containers(user=hans)["containers"]]
        response = jsonify(response_data)

        # use template policy
        g.policies = {}
        set_policy("enroll_via_multichallenge_template", scope=SCOPE.AUTH,
                   action={PolicyAction.ENROLL_VIA_MULTICHALLENGE_TEMPLATE: "test"})
        response = multichallenge_enroll_via_validate(request, response)
        check_response(response)
        container = find_container_by_serial(response.json.get("detail").get("serial"))
        self.assertEqual("test", container.template.name)
        tokens = container.tokens
        self.assertSetEqual({"hotp", "totp"}, {token.type for token in tokens})
        # clean up
        [token.delete_token() for token in tokens]
        [container.delete() for container in get_all_containers(user=hans)["containers"]]
        response = jsonify(response_data)

        # User max token reached, but container is created anyway
        g.policies = {}
        set_policy("max_token_user", scope=SCOPE.ENROLL, action={PolicyAction.MAXTOKENUSER: 1})
        token = init_token({"type": "hotp", "genkey": True}, user=hans)
        with LogCapture() as capture:
            logging.getLogger('privacyidea.lib.container').setLevel(logging.WARNING)
            response = multichallenge_enroll_via_validate(request, response)
            token_info = {"type": "hotp", "genkey": True, "user": hans.login, "realm": hans.realm,
                          "resolver": hans.resolver}
            log_message = (f"Error checking pre-policies for token {token_info} created from template: ERR303: The "
                           "number of tokens for this user is limited!")
            capture.check_present(("privacyidea.lib.container", "WARNING", log_message))
            token_info["type"] = "totp"
            log_message = (f"Error checking pre-policies for token {token_info} created from template: ERR303: The "
                           "number of tokens for this user is limited!")
            capture.check_present(("privacyidea.lib.container", "WARNING", log_message))
        check_response(response)
        container = find_container_by_serial(response.json.get("detail").get("serial"))
        self.assertEqual("test", container.template.name)
        # token is not created as the user already had one token
        tokens = container.tokens
        self.assertEqual(0, len(tokens))

        # clean up
        [container.delete() for container in get_all_containers(user=hans)["containers"]]
        token.delete_token()
        delete_policy("max_token_user")
        delete_policy("enroll_via_multichallenge_template")
        response = jsonify(response_data)

        # use custom text
        g.policies = {}
        set_policy("enroll_via_multichallenge_text", scope=SCOPE.AUTH,
                   action={PolicyAction.ENROLL_VIA_MULTICHALLENGE_TEXT: "Test custom text!"})
        response = multichallenge_enroll_via_validate(request, response)
        check_response(response, message="Test custom text!")
        # clean up
        [container.delete() for container in get_all_containers(user=hans)["containers"]]
        delete_policy("enroll_via_multichallenge_text")
        response = jsonify(response_data)

        # Invalid template name: container is created anyway
        g.policies = {}
        set_policy("enroll_via_multichallenge_template", scope=SCOPE.AUTH,
                   action={PolicyAction.ENROLL_VIA_MULTICHALLENGE_TEMPLATE: "invalid"})
        response = multichallenge_enroll_via_validate(request, response)
        check_response(response)
        container = find_container_by_serial(response.json.get("detail").get("serial"))
        self.assertEqual(0, len(container.tokens))
        self.assertIsNone(container.template)
        # clean up
        [container.delete() for container in get_all_containers(user=hans)["containers"]]
        delete_policy("enroll_via_multichallenge_template")
        response = jsonify(response_data)

        delete_policy("enroll_via_multichallenge")
        delete_policy("registration")

    @log_capture(level=logging.DEBUG)
    def test_24_enroll_smartphone_is_not_triggered(self, capture):
        """
        Here we only test that the enroll_via_multichallenge is not triggered correctly for different scenarios
        """
        logging.getLogger('privacyidea.api.lib.postpolicy').setLevel(logging.DEBUG)
        set_policy("enroll_via_multichallenge", scope=SCOPE.AUTH,
                   action={PolicyAction.ENROLL_VIA_MULTICHALLENGE: "smartphone", PolicyAction.PASSTHRU: True})
        set_policy("registration", scope=SCOPE.CONTAINER, action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.net/"})
        set_policy("enroll_via_multichallenge_template", scope=SCOPE.AUTH,
                   action={PolicyAction.ENROLL_VIA_MULTICHALLENGE_TEMPLATE: "test"})

        self.setUp_user_realms()
        hans = User("hans", self.realm1)

        # Mock request
        builder = EnvironBuilder(method='POST', data={}, headers=Headers({"user_agent": "privacyidea-cp"}))
        env = builder.get_environ()
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        request = Request(env)
        request.all_data = {}
        request.User = hans
        g.policy_object = PolicyClass()
        g.policies = {}

        response_data = {"jsonrpc": "2.0",
                         "result": {"status": True, "value": True, "authentication": AUTH_RESPONSE.ACCEPT},
                         "version": "privacyIDEA test"}
        response = jsonify(response_data)

        def check_response(response):
            result = response.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))
            self.assertEqual(AUTH_RESPONSE.ACCEPT, result.get("authentication"))

        # User has registered smartphone container
        container_serial = init_container({"type": "smartphone", "user": "hans", "realm": self.realm1})[
            "container_serial"]
        container = find_container_by_serial(container_serial)
        container.set_container_info(
            [TokenContainerInfoData(RegistrationState.get_key(), RegistrationState.REGISTERED.value)])
        response = multichallenge_enroll_via_validate(request, response)
        check_response(response)
        container_of_hans = get_all_containers(user=hans)["containers"]
        self.assertEqual(1, len(container_of_hans))
        self.assertEqual(container_serial, container_of_hans[0].serial)
        [container.delete() for container in get_all_containers(user=hans)["containers"]]
        response = jsonify(response_data)

        # Missing registration policies
        delete_policy("registration")
        g.policies = {}
        delete_container_template("test")
        # create with template to check that also no tokens are created
        template_options = {"tokens": [{"type": "hotp", "genkey": True}, {"type": "totp", "genkey": True}]}
        create_container_template(container_type="smartphone", template_name="test", options=template_options)
        response = multichallenge_enroll_via_validate(request, response)
        check_response(response)
        container_of_hans = get_all_containers(user=hans)["containers"]
        self.assertEqual(0, len(container_of_hans))
        tokens_of_hans = get_tokens(user=hans)
        self.assertEqual(0, len(tokens_of_hans))
        capture.check_present(("privacyidea.api.lib.postpolicy", "WARNING",
                               "Missing container registration policy. Can not enroll container via multichallenge."))

        delete_policy("enroll_via_multichallenge")
        delete_policy("enroll_via_multichallenge_template")
        delete_container_template("test")


class PolicyHelperTestCase(MyApiTestCase):

    def test_01_set_realm_for_authentication(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()

        # policy not set
        realm = get_realm_for_authentication(g, "hans", "realm1")
        self.assertEqual("realm1", realm)
        self.assertNotIn("policies", g)

        realm = get_realm_for_authentication(g, "hans", "")
        self.assertEqual("", realm)
        self.assertNotIn("policies", g)

        # policy with non-existing realm
        set_policy("auth_realm", scope=SCOPE.AUTH, action=f"{PolicyAction.SET_REALM}=random")
        realm = get_realm_for_authentication(g, "hans", "realm1")
        self.assertEqual("realm1", realm)
        self.assertNotIn("policies", g)

        realm = get_realm_for_authentication(g, "hans", "")
        self.assertEqual("", realm)
        self.assertNotIn("policies", g)

        # set policy
        set_policy("auth_realm", scope=SCOPE.AUTH, action=f"{PolicyAction.SET_REALM}=realm2")
        realm = get_realm_for_authentication(g, "hans", "realm1")
        self.assertEqual("realm2", realm)
        self.assertEqual("realm2", g.policies.get(PolicyAction.SET_REALM))

        realm = get_realm_for_authentication(g, "hans", "")
        self.assertEqual("realm2", realm)

        delete_policy("auth_realm")
