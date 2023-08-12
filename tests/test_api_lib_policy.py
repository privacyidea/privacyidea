# -*- coding: utf-8 -*-
"""
This test file tests the api.lib.policy.py

The api.lib.policy.py depends on lib.policy and on flask!
"""
import json
import logging
from testfixtures import log_capture
from privacyidea.lib.tokens.webauthn import (webauthn_b64_decode, AUTHENTICATOR_ATTACHMENT_TYPE,
                                             ATTESTATION_LEVEL, ATTESTATION_FORM,
                                             USER_VERIFICATION_LEVEL)
from privacyidea.lib.tokens.webauthntoken import (WEBAUTHNACTION, DEFAULT_ALLOWED_TRANSPORTS,
                                                  WebAuthnTokenClass, DEFAULT_CHALLENGE_TEXT_AUTH,
                                                  PUBLIC_KEY_CREDENTIAL_ALGORITHMS,
                                                  DEFAULT_PUBLIC_KEY_CREDENTIAL_ALGORITHM_PREFERENCE,
                                                  DEFAULT_AUTHENTICATOR_ATTESTATION_LEVEL,
                                                  DEFAULT_AUTHENTICATOR_ATTESTATION_FORM,
                                                  DEFAULT_CHALLENGE_TEXT_ENROLL, DEFAULT_TIMEOUT,
                                                  DEFAULT_USER_VERIFICATION_REQUIREMENT,
                                                  PUBKEY_CRED_ALGORITHMS_ORDER)
from privacyidea.lib.utils import hexlify_and_unicode
from privacyidea.lib.config import set_privacyidea_config, SYSCONF
from .base import (MyApiTestCase)

from privacyidea.lib.policy import (set_policy, delete_policy, enable_policy,
                                    PolicyClass, SCOPE, ACTION, REMOTE_USER,
                                    AUTOASSIGNVALUE, AUTHORIZED)
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
                                           papertoken_count, allowed_audit_realm,
                                           u2ftoken_verify_cert,
                                           tantoken_count, sms_identifiers,
                                           pushtoken_add_config, pushtoken_wait,
                                           indexedsecret_force_attribute,
                                           check_admin_tokenlist, pushtoken_disable_wait,
                                           webauthntoken_auth, webauthntoken_authz,
                                           webauthntoken_enroll, webauthntoken_request,
                                           webauthntoken_allowed, check_application_tokentype,
                                           required_piv_attestation, check_custom_user_attributes,
                                           hide_tokeninfo, init_ca_template, init_ca_connector,
                                           init_subject_components, increase_failcounter_on_challenge,
                                           require_description)
from privacyidea.lib.realm import set_realm as create_realm
from privacyidea.lib.realm import delete_realm
from privacyidea.api.lib.postpolicy import (check_serial, check_tokentype,
                                            check_tokeninfo,
                                            no_detail_on_success,
                                            no_detail_on_fail, autoassign,
                                            offline_info, sign_response,
                                            get_webui_settings,
                                            save_pin_change,
                                            add_user_detail_to_response,
                                            mangle_challenge_response, is_authorized,
                                            check_verify_enrollment)
from privacyidea.lib.token import (init_token, get_tokens, remove_token,
                                   set_realms, check_user_pass, unassign_token,
                                   enable_token)
from privacyidea.lib.user import User
from privacyidea.lib.tokens.papertoken import PAPERACTION
from privacyidea.lib.tokens.tantoken import TANACTION
from privacyidea.lib.tokens.smstoken import SMSACTION
from privacyidea.lib.tokens.pushtoken import PUSH_ACTION
from privacyidea.lib.tokens.indexedsecrettoken import PIIXACTION
from privacyidea.lib.tokens.registrationtoken import DEFAULT_LENGTH, DEFAULT_CONTENTS
from privacyidea.lib.tokens.certificatetoken import ACTION as CERTIFICATE_ACTION

from flask import Request, g, current_app, jsonify
from werkzeug.test import EnvironBuilder
from privacyidea.lib.error import PolicyError, RegistrationError, ValidateError
from privacyidea.lib.machineresolver import save_resolver
from privacyidea.lib.machine import attach_token
from privacyidea.lib.auth import ROLE
import jwt
from passlib.hash import pbkdf2_sha512
from datetime import datetime, timedelta
from dateutil.tz import tzlocal
from privacyidea.lib.tokenclass import DATE_FORMAT
from .test_lib_tokens_webauthn import (ALLOWED_TRANSPORTS, CRED_ID, ASSERTION_RESPONSE_TMPL,
                                       ASSERTION_CHALLENGE, RP_ID, RP_NAME, ORIGIN,
                                       REGISTRATION_RESPONSE_TMPL)
from privacyidea.lib.utils import (create_img, generate_charlists_from_pin_policy,
                                   CHARLIST_CONTENTPOLICY, check_pin_contents)


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


class PrePolicyDecoratorTestCase(MyApiTestCase):

    def test_01_check_token_action(self):
        g.logged_in_user = {"username": "admin1",
                            "realm": "",
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
        req.User = User()

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
        req.User = User()
        self.assertRaises(PolicyError,
                          check_base_action, req, "delete")
        # while token in realm2 can be deleted
        req.all_data = {"serial": "POL002"}
        r = check_base_action(req, action="delete")
        self.assertTrue(r)

        # A normal user can "disable", since no user policies are defined.
        g.logged_in_user = {"username": "user1",
                            "realm": "",
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
        req.User = User()
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
                            "realm": "",
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
        req.User = None

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
                            "realm": "",
                            "role": "user"}
        r = check_token_init(req)
        self.assertTrue(r)

        # An exception is raised for an invalid role
        g.logged_in_user = {"username": "user1",
                            "role": "invalid"}
        with self.assertRaises(PolicyError):
            check_token_init(req)

        # finally delete policy
        delete_policy("pol1")

    def test_03_check_token_upload(self):
        g.logged_in_user = {"username": "admin1",
                            "realm": "",
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
        req.User = User()
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
        req.User = User()
        self.assertRaises(PolicyError,
                          check_token_upload, req)
        # finally delete policy
        delete_policy("pol1")

    def test_04a_check_max_active_token_user(self):
        g.logged_in_user = {"username": "admin1",
                            "realm": "",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)

        # Set a policy, that allows one active token per user
        set_policy(name="pol1",
                   scope=SCOPE.ENROLL,
                   action="{0!s}={1!s}".format(ACTION.MAXACTIVETOKENUSER, 1))
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
        # First we can create the same active token again
        req.all_data = {"user": "cornelius",
                        "realm": self.realm1,
                        "serial": "NEW001"}
        self.assertTrue(check_max_token_user(req))

        # The user has one token. The check that will run in this case,
        # before the user would be assigned the NEW 2nd token, will raise a
        # PolicyError
        req.all_data = {"user": "cornelius",
                        "realm": self.realm1,
                        "serial": "NEW0002"}
        self.assertRaises(PolicyError,
                          check_max_token_user, req)

        # Now, we disable the token NEW001, so the user has NO active token
        enable_token("NEW001", False)
        self.assertTrue(check_max_token_user(req))
        # finally delete policy
        delete_policy("pol1")

        # now we enable the hotp token again.
        enable_token("NEW001")

        # Set a policy to limit active HOTP tokens to 1
        set_policy(name="pol1",
                   scope=SCOPE.ENROLL,
                   action="hotp_{0!s}={1!s}".format(ACTION.MAXACTIVETOKENUSER, 1))
        # we try to enroll a new HOTP token, this would fail.
        req.all_data = {"user": "cornelius",
                        "realm": self.realm1,
                        "type": "hotp"}
        self.assertRaises(PolicyError,
                          check_max_token_user, req)

        # enrolling the same HOTP token would succeed
        req.all_data = {"user": "cornelius",
                        "realm": self.realm1,
                        "serial": "NEW001"}
        self.assertTrue(check_max_token_user(req))

        # We could also enroll a new TOTP token
        req.all_data = {"user": "cornelius",
                        "realm": self.realm1,
                        "type": "totp"}
        self.assertTrue(check_max_token_user(req))

        # Now, we disable the token NEW001, so the user again has NO active token
        enable_token("NEW001", enable=False)
        # we enroll a new HOTP token, this would now succeed
        init_token({"serial": "NEW002", "type": "hotp",
                    "otpkey": "1234567890123456"},
                   user=User(login="cornelius",
                             realm=self.realm1))
        tokenobject_list = get_tokens(user=User(login="cornelius",
                                                realm=self.realm1))
        self.assertTrue(len(tokenobject_list) == 2)
        # now we enable the first hotp token again, which fails due to the policy
        req.all_data = {"serial": "NEW001"}
        self.assertRaises(PolicyError,
                          check_max_token_user, req)

        # not we unassign the token and try to enable it which succeeds, since
        # there is no tokenowner anymore
        unassign_token("NEW001")
        req.all_data = {"serial": "NEW001"}
        self.assertTrue(check_max_token_user(req))

        # clean up
        delete_policy("pol1")
        remove_token("NEW001")
        remove_token("NEW002")

    def test_04_check_max_token_user(self):
        g.logged_in_user = {"username": "admin1",
                            "realm": "",
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

        # Now, the token that already exists and is reenrolled must not trigger an exception
        req.all_data = {"user": "cornelius",
                        "realm": self.realm1,
                        "serial": "NEW002"}
        self.assertTrue(check_max_token_user(req))

        # Now we set another policy for the user max_token = 12.
        # This way, the user should be allowed to enroll tokens again, since there
        # are two policies matching for the user and the maximum is 12.
        set_policy(name="pol_max_12",
                   scope=SCOPE.ENROLL,
                   action="{0!s}={1!s}".format(ACTION.MAXTOKENUSER, 12))
        g.policy_object = PolicyClass()
        # new check_max_token_user should not raise an error!
        self.assertTrue(check_max_token_user(req))
        delete_policy("pol_max_12")
        g.policy_object = PolicyClass()

        # The check for a token, that has no username in it, must not
        # succeed. I.e. in the realm new tokens must be enrollable.
        req.all_data = {}
        self.assertTrue(check_max_token_user(req))

        req.all_data = {"realm": self.realm1}
        self.assertTrue(check_max_token_user(req))

        # delete generic policy
        delete_policy("pol1")
        delete_policy("pol2")

        # Now we set a policy specifically for HOTP tokens:
        set_policy(name="pol2",
                   scope=SCOPE.ENROLL,
                   action="hotp_{0!s}={1!s}".format(ACTION.MAXTOKENUSER, 2))
        g.policy_object = PolicyClass()
        # and fail to enroll a new token
        req.all_data = {"user": "cornelius",
                        "realm": self.realm1,
                        "serial": "NEW003",
                        "type": "hotp"}
        self.assertRaises(PolicyError,
                          check_max_token_user, req)

        # and we fail to create a token with default type "hotp"
        req.all_data = {"user": "cornelius",
                        "realm": self.realm1,
                        "serial": "NEW003"}
        self.assertRaises(PolicyError,
                          check_max_token_user, req)

        # but we can reenroll an existing HOTP token
        req.all_data = {"user": "cornelius",
                        "realm": self.realm1,
                        "serial": "NEW002"}
        self.assertTrue(check_max_token_user(req))

        # and we succeed in issueing a new totp token
        req.all_data = {"user": "cornelius",
                        "realm": self.realm1,
                        "serial": "NEW004",
                        "type": "totp"}
        self.assertTrue(check_max_token_user(req))

        # finally delete policy
        delete_policy("pol2")
        remove_token("NEW001")
        remove_token("NEW002")

    def test_05_check_max_token_realm(self):
        g.logged_in_user = {"username": "admin1",
                            "realm": "",
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
                            "realm": "",
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
        req.all_data = {}
        req.User = User()
        set_realm(req)
        # Check, that the realm was not set, since there was no user in the request
        self.assertEqual(req.all_data.get("realm"), None)

        req.all_data = {}
        req.User = User(login="cornelius", realm="somerealm")
        set_realm(req)
        # Check, if the realm was modified to the realm specified in the policy
        self.assertEqual(req.all_data.get("realm"), self.realm1)

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
        req.User = User(login="cornelius", realm="somerealm")
        self.assertRaises(PolicyError, set_realm, req)

        # finally delete policy
        delete_policy("pol1")
        delete_policy("pol2")

    def test_06_set_tokenlabel(self):
        g.logged_in_user = {"username": "admin1",
                            "realm": "",
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
        req.all_data = {"user": "cornelius",
                        "realm": "home"}
        init_tokenlabel(req)

        # Check, if the tokenlabel was added
        self.assertEqual(req.all_data.get(ACTION.TOKENLABEL), "<u>@<r>")
        # Check, if the tokenissuer was added
        self.assertEqual(req.all_data.get(ACTION.TOKENISSUER), "myPI")
        # Check, if force_app_pin wasn't added (since there is no policy)
        self.assertNotIn(ACTION.FORCE_APP_PIN, req.all_data, req.all_data)

        # reset the request data and start again with force_app_pin policy
        set_policy(name="pol3",
                   scope=SCOPE.ENROLL,
                   action="hotp_{0!s}=True".format(ACTION.FORCE_APP_PIN))
        req.all_data = {"user": "cornelius",
                        "realm": "home"}
        init_tokenlabel(req)
        # Check, if force_app_pin was added and is True
        self.assertTrue(req.all_data.get('force_app_pin'))

        # Check that the force_app_pin policy isn't set for totp token
        req.all_data = {"user": "cornelius",
                        "realm": "home",
                        "type": "TOTP"}
        init_tokenlabel(req)
        # Check, that force_app_pin wasn't added
        self.assertNotIn(ACTION.FORCE_APP_PIN, req.all_data, req.all_data)

        # finally delete policy
        delete_policy("pol1")
        delete_policy("pol2")
        delete_policy("pol3")

    def test_07a_init_random_pin(self):
        g.logged_in_user = {"username": "admin1",
                            "realm": "",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.User = User("cornelius", self.realm1)

        # Set policies which define the pin generation behavior
        contents_policy = "+cns"
        size_policy = 12
        set_policy(name="pinsize",
                   scope=SCOPE.ENROLL,
                   action="{0!s}={1!s}".format(ACTION.OTPPINRANDOM, size_policy))
        set_policy(name="pincontent",
                   scope=SCOPE.ADMIN,
                   action="{0!s}={1!s}".format(ACTION.OTPPINCONTENTS, contents_policy))
        set_policy(name="pinhandling",
                   scope=SCOPE.ENROLL,
                   action="{0!s}=privacyidea.lib.pinhandling.base.PinHandler".format(
                          ACTION.PINHANDLING))
        g.policy_object = PolicyClass()

        # request, that matches the policy
        req.all_data = {
                        "user": "cornelius",
                        "realm": "realm1"}

        init_random_pin(req)
        pin = req.all_data.get("pin")

        # check if the pin honors the contents policy
        pin_valid, comment = check_pin_contents(pin, contents_policy)
        self.assertTrue(pin_valid)

        # Check, if the pin has the correct length
        self.assertEqual(len(req.all_data.get("pin")), size_policy)

        # finally delete policy
        delete_policy("pinsize")
        delete_policy("pincontent")
        delete_policy("pinhandling")

    def test_07b_set_random_pin(self):
        g.logged_in_user = {"username": "admin1",
                            "realm": "",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.User = User("cornelius", self.realm1)

        # Set policies which define the pin generation behavior
        contents_policy = "+cns"
        size_policy = 12
        set_policy(name="pinsize",
                   scope=SCOPE.ADMIN,
                   action="{0!s}={1!s}".format(ACTION.OTPPINSETRANDOM, size_policy))
        set_policy(name="pincontent",
                   scope=SCOPE.ADMIN,
                   action="{0!s}={1!s}".format(ACTION.OTPPINCONTENTS, contents_policy))
        g.policy_object = PolicyClass()

        # request, that matches the policy
        req.all_data = {
                        "user": "cornelius",
                        "realm": "realm1"}

        set_random_pin(req)
        pin = req.all_data.get("pin")

        # check if the pin honors the contents policy
        pin_valid, comment = check_pin_contents(pin, contents_policy)
        self.assertTrue(pin_valid)

        # Check, if the pin has the correct length
        self.assertEqual(len(req.all_data.get("pin")), size_policy)

        # finally delete policy
        delete_policy("pinsize")
        delete_policy("pincontent")

    def test_07c_generate_pin_from_policy(self):
        content_policies_valid = ['+cn', '-s', 'cns', '+ns', '[1234567890]', '[[]€@/(]']
        content_policies_invalid = ['+c-ns', 'cn-s', '+ns-[1234567890]', '-[1234567890]']
        pin_size = 10
        for i in range(100):
            for content_policy in content_policies_valid:
                pin = _generate_pin_from_policy(content_policy, size=pin_size)
                # check if the pin honors the contents policy
                pin_valid, comment = check_pin_contents(pin, content_policy)
                self.assertTrue(pin_valid)
                # Check, if the pin has the correct length
                self.assertEqual(len(pin), pin_size)

            for content_policy in content_policies_invalid:
                # an invalid policy string should throw a PolicyError exception
                self.assertRaises(PolicyError, _generate_pin_from_policy, content_policy, size=pin_size)

    def test_07d_generate_charlists_from_pin_policy(self):
        default_chars = "".join(CHARLIST_CONTENTPOLICY.values())

        policies = ["+cn", "+c", "+cs"]
        for policy in policies:
            required = ["".join([CHARLIST_CONTENTPOLICY[str] for str in policy[1:]])]
            charlists_dict = generate_charlists_from_pin_policy(policy)
            self.assertEqual(charlists_dict,
                             {"base": default_chars,
                              "requirements": required})

        policies = ["-cn", "-c", "-sc"]
        for policy in policies:
            base_charlist = []
            for key in CHARLIST_CONTENTPOLICY.keys():
                if key not in policy[1:]:
                    base_charlist.append(CHARLIST_CONTENTPOLICY[key])
            base_chars = "".join(base_charlist)
            charlists_dict = generate_charlists_from_pin_policy(policy)
            self.assertEqual(charlists_dict,
                             {"base": base_chars,
                              "requirements": []})

        policies = ["cn", "c", "sc"]
        for policy in policies:
            required = [CHARLIST_CONTENTPOLICY[str] for str in policy[:]]
            charlists_dict = generate_charlists_from_pin_policy(policy)
            self.assertEqual(charlists_dict,
                             {"base": default_chars,
                              "requirements": required})

        policies = ["[cn]", "[1234567890]", "[[]]", "[ÄÖüß§$@³¬&()|<>€%/\\]"]
        for policy in policies:
            charlists_dict = generate_charlists_from_pin_policy(policy)
            self.assertEqual(charlists_dict,
                             {"base": policy[1:-1],
                              "requirements": []})

        policies = ["+c-n", ".c", ""]
        for policy in policies:
            self.assertRaises(PolicyError, generate_charlists_from_pin_policy, policy)

    def test_08_encrypt_pin(self):
        g.logged_in_user = {"username": "admin1",
                            "realm": "",
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

    def test_08a_enroll_pin_admin(self):
        g.logged_in_user = {"username": "admin1",
                            "realm": "",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.User = User("cornelius", self.realm1)

        # Set a policy that defines the PIN to be encrypted
        set_policy(name="pol1",
                   scope=SCOPE.ADMIN,
                   action="enrollHOTP")
        g.policy_object = PolicyClass()

        # request, that matches the policy
        req.all_data = {"pin": "test",
                        "user": "cornelius",
                        "realm": self.realm1}
        enroll_pin(req)

        # Check, if the PIN was removed
        self.assertTrue("pin" not in req.all_data)
        # finally delete policy
        delete_policy("pol1")

    def test_08b_enroll_pin_user(self):
        g.logged_in_user = {"username": "cornelius",
                            "realm": self.realm1,
                            "role": "user"}
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
                   scope=SCOPE.USER,
                   action="enrollHOTP, enrollpin")
        g.policy_object = PolicyClass()

        # request, that matches the policy
        req.all_data = {"pin": "test",
                        "user": "cornelius",
                        "realm": self.realm1}
        req.User = User("cornelius", self.realm1)
        enroll_pin(req)

        # Check, if the PIN was removed
        self.assertEqual(req.all_data.get("pin"), "test")
        # finally delete policy
        delete_policy("pol1")

    @log_capture(level=logging.DEBUG)
    def test_09_pin_policies(self, capture):
        create_realm("home", [self.resolvername1])
        g.logged_in_user = {"username": "user1",
                            "realm": "",
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
        req.User = User("cornelius", "home")
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

        # check that no pin is checked during rollover or verify
        logging.getLogger('privacyidea').setLevel(logging.DEBUG)
        req.all_data = {
            "user": "cornelius",
            "realm": "home",
            "rollover": True
        }
        self.assertTrue(check_otp_pin(req))
        capture.check_present(("privacyidea.api.lib.prepolicy", "DEBUG",
                               "Disable PIN checking due to rollover (True) or verify (None)"))
        req.all_data = {
            "user": "cornelius",
            "realm": "home",
            "verify": 123456
        }
        self.assertTrue(check_otp_pin(req))
        capture.check_present(("privacyidea.api.lib.prepolicy", "DEBUG",
                               "Disable PIN checking due to rollover (None) or verify (123456)"))
        logging.getLogger('privacyidea').setLevel(logging.INFO)

        # finally delete policy
        delete_policy("pol1")
        delete_realm("home")

    @log_capture(level=logging.DEBUG)
    def test_09_pin_policies_admin(self, capture):
        create_realm("home", [self.resolvername1])
        g.logged_in_user = {"username": "super",
                            "realm": "",
                            "role": "admin"}
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
                   scope=SCOPE.ADMIN,
                   action="{0!s}={1!s},{2!s}={3!s},{4!s}={5!s}".format(ACTION.OTPPINMAXLEN, "10",
                                                 ACTION.OTPPINMINLEN, "4",
                                                 ACTION.OTPPINCONTENTS, "cn"),
                   realm="home")
        g.policy_object = PolicyClass()

        req.all_data = {"user": "cornelius",
                        "realm": "home"}
        req.User = User("cornelius", "home")
        # The minimum OTP length is 4
        self.assertRaises(PolicyError, check_otp_pin, req)

        req.all_data = {"user": "cornelius",
                        "realm": "home",
                        "pin": "12345566890012"}
        # Fail maximum OTP length
        self.assertRaises(PolicyError, check_otp_pin, req)

        req.all_data = {"user": "cornelius",
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

        # check that no pin is checked during rollover or verify
        logging.getLogger('privacyidea').setLevel(logging.DEBUG)
        req.all_data = {
            "user": "cornelius",
            "realm": "home",
            "rollover": True
        }
        self.assertTrue(check_otp_pin(req))
        capture.check_present(("privacyidea.api.lib.prepolicy", "DEBUG",
                               "Disable PIN checking due to rollover (True) or verify (None)"))
        req.all_data = {
            "user": "cornelius",
            "realm": "home",
            "verify": 123456
        }
        self.assertTrue(check_otp_pin(req))
        capture.check_present(("privacyidea.api.lib.prepolicy", "DEBUG",
                               "Disable PIN checking due to rollover (None) or verify (123456)"))
        logging.getLogger('privacyidea').setLevel(logging.INFO)

        # finally delete policy
        delete_policy("pol1")
        delete_realm("home")

    def test_01b_token_specific_pin_policy(self):
        create_realm("home", [self.resolvername1])
        g.logged_in_user = {"username": "super",
                            "realm": "",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)

        # Set a policy that defines a default PIN policy
        set_policy(name="pol1",
                   scope=SCOPE.ADMIN,
                   action="{0!s}={1!s},{2!s}={3!s},{4!s}={5!s}".format(
                       ACTION.OTPPINMAXLEN, "10",
                       ACTION.OTPPINMINLEN, "4",
                       ACTION.OTPPINCONTENTS, "cn"),
                   realm="home")

        # Set a policy that defines a SPASS PIN policy
        set_policy(name="pol2",
                   scope=SCOPE.ADMIN,
                   action="{0!s}={1!s},{2!s}={3!s},{4!s}={5!s}".format(
                       "spass_otp_pin_maxlength", "11",
                       "spass_otp_pin_minlength", "8",
                       "spass_otp_pin_contents", "n"),
                   realm="home")
        g.policy_object = PolicyClass()

        req.all_data = {"user": "cornelius",
                        "realm": "home",
                        "pin": "123456",
                        "type": "spass"}
        req.User = User("cornelius", "home")
        # The minimum OTP length is 8
        self.assertRaises(PolicyError, check_otp_pin, req)

        req.all_data = {"user": "cornelius",
                        "realm": "home",
                        "type": "spass",
                        "pin": "12345678901"}
        # The maximum PIN length of 11 is ok.
        r = check_otp_pin(req)
        self.assertTrue(r)

        req.all_data = {"user": "cornelius",
                        "realm": "home",
                        "type": "spass",
                        "pin": "abcdefghij"}
        # Good OTP length, but missing nummbers
        self.assertRaises(PolicyError, check_otp_pin, req)

        # finally delete policy
        delete_policy("pol1")
        delete_realm("home")

    def test_10_check_external(self):
        g.logged_in_user = {"username": "user1",
                            "realm": "",
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
        req.User = User()
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
                            "realm": "",
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
        req.User = User("Thiswillbesplit_user")
        mangle(req)
        # Check if the user was modified
        self.assertEqual(req.all_data.get("user"), "user")
        self.assertEqual(req.User, User("user", "realm1"))

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
        self.assertEqual(req.User, User("", "lowerrealm"))

        # finally delete policy
        delete_policy("mangle1")
        delete_policy("mangle2")

    def test_13_remote_user(self):
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        env["REMOTE_USER"] = "admin"
        req = Request(env)

        # A user, for whom the login via REMOTE_USER is allowed.
        set_policy(name="ruser",
                   scope=SCOPE.WEBUI,
                   action="{0!s}={1!s}".format(ACTION.REMOTE_USER, REMOTE_USER.ACTIVE))

        r = is_remote_user_allowed(req)
        self.assertEqual(REMOTE_USER.ACTIVE, r)

        # Login for the REMOTE_USER is not allowed.
        # Only allowed for user "super", but REMOTE_USER=admin
        set_policy(name="ruser",
                   scope=SCOPE.WEBUI,
                   action="{0!s}={1!s}".format(ACTION.REMOTE_USER, REMOTE_USER.ACTIVE),
                   user="super")

        r = is_remote_user_allowed(req)
        self.assertEqual(REMOTE_USER.DISABLE, r)

        # The remote_user "super" is allowed to login:
        env["REMOTE_USER"] = "super"
        req = Request(env)
        r = is_remote_user_allowed(req)
        self.assertEqual(REMOTE_USER.ACTIVE, r)

        # check that Splt@Sign works correctly
        create_realm(self.realm1)
        set_privacyidea_config(SYSCONF.SPLITATSIGN, True)
        env["REMOTE_USER"] = "super@realm1"
        req = Request(env)
        self.assertEqual(REMOTE_USER.ACTIVE, is_remote_user_allowed(req))

        # Now set the remote force policy
        set_policy(name="ruser",
                   scope=SCOPE.WEBUI,
                   action="{0!s}={1!s}".format(ACTION.REMOTE_USER, REMOTE_USER.FORCE),
                   user="super")
        self.assertEqual(REMOTE_USER.FORCE, is_remote_user_allowed(req))

        set_privacyidea_config(SYSCONF.SPLITATSIGN, False)
        self.assertEqual(REMOTE_USER.DISABLE, is_remote_user_allowed(req))

        set_privacyidea_config(SYSCONF.SPLITATSIGN, True)
        delete_policy("ruser")

    def test_14_required_email(self):
        g.logged_in_user = {"username": "admin1",
                            "realm": "",
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
                   action=r"{0!s}=/.*@mydomain\..*".format(ACTION.REQUIREDEMAIL))
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
        req.User = User()
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
                   adminuser="admin[aA]",
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
                   adminuser="adminB")
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
                   adminuser="adminA",
                   realm="realmA",
                   resolver="resolverA",
                   )
        builder = EnvironBuilder(method='POST')
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        req = Request(env)
        req.User = User()
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

    def test_18_auditlog_age(self):
        g.logged_in_user = {"username": "admin1",
                            "realm": "",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)

        # Set a mangle policy to change the username
        # and only use the last 4 characters of the username
        set_policy(name="a_age",
                   scope=SCOPE.ADMIN,
                   action="{0!s}=1d".format(ACTION.AUDIT_AGE))
        g.policy_object = PolicyClass()

        # request, that matches the policy
        req.all_data = {"user": "Unknown"}
        req.User = User("Unknown")
        auditlog_age(req)
        # Check if the timelimit was added
        self.assertEqual(req.all_data.get("timelimit"), "1d")

        # finally delete policy
        delete_policy("a_age")

    def test_18b_hide_audit_columns(self):
        builder = EnvironBuilder(method='POST',
                                 headers={})
        env = builder.get_environ()
        req = Request(env)
        g.policy_object = PolicyClass()

        # set a policy to hide the "serial" and the "action" columns in the audit response
        set_policy(name="hide_audit_columns_admin",
                   scope=SCOPE.ADMIN,
                   action="{0!s}=serial action".format(ACTION.HIDE_AUDIT_COLUMNS))
        g.logged_in_user = {"username": "admin1",
                            "realm": "",
                            "role": "admin"}
        # request, that matches the policy
        req.all_data = {"user": "Unknown"}
        req.User = User("Unknown")
        hide_audit_columns(req)
        # Check if the hidden_columns was added
        for col in ["serial", "action"]:
            self.assertIn(col, req.all_data.get("hidden_columns"))
        # delete admin policy
        delete_policy("hide_audit_columns_admin")

        # set a policy to hide the "number" and the "realm" columns in the audit response
        set_policy(name="hide_audit_columns_user",
                   scope=SCOPE.USER,
                   action="{0!s}=number realm".format(ACTION.HIDE_AUDIT_COLUMNS))
        g.logged_in_user = {"username": "user1",
                            "realm": "",
                            "role": "user"}
        # request, that matches the policy
        req.all_data = {"user": "Unknown"}
        req.User = User("Unknown")
        hide_audit_columns(req)
        # Check if the hidden_columns was added
        for col in ["number", "realm"]:
            self.assertIn(col, req.all_data.get("hidden_columns"))
        # delete user policy
        delete_policy("hide_audit_columns_user")

    def test_18c_hide_tokeninfo(self):
        builder = EnvironBuilder(method='POST',
                                 headers={})
        env = builder.get_environ()
        req = Request(env)
        g.policy_object = PolicyClass()

        # set a policy to hide the "tokenkind" and the "unknown" tokeninfo values
        set_policy(name="hide_tokeninfo_admin",
                   scope=SCOPE.ADMIN,
                   action="{0!s}=tokenkind unknown".format(ACTION.HIDE_TOKENINFO))
        g.logged_in_user = {"username": "admin1",
                            "realm": "",
                            "role": "admin"}
        req.all_data = {}
        req.User = User("Unknown")
        hide_tokeninfo(req)
        # Check if the hidden_tokeninfo entry was added to the request.data
        self.assertIn('hidden_tokeninfo', req.all_data, req.all_data)
        for col in ["tokenkind", "unknown"]:
            self.assertIn(col, req.all_data.get("hidden_tokeninfo"))
        # check that it won't be added when logged in as a user
        g.logged_in_user = {"username": "user1",
                            "realm": "",
                            "role": "user"}
        req.all_data = {}
        hide_tokeninfo(req)
        self.assertEqual(0, len(req.all_data['hidden_tokeninfo']), req.all_data)

        delete_policy("hide_tokeninfo_admin")

        # set a policy to hide the "tokenkind" and the "unknown" entries from the tokeninfo
        set_policy(name="hide_tokeninfo_user",
                   scope=SCOPE.USER,
                   action="{0!s}=tokenkind unknown".format(ACTION.HIDE_TOKENINFO))
        g.logged_in_user = {"username": "user1",
                            "realm": "",
                            "role": "user"}
        req.all_data = {}
        hide_tokeninfo(req)
        # Check if the hidden_tokeninfo entry was added to the request.data
        self.assertIn('hidden_tokeninfo', req.all_data, req.all_data)
        for col in ["tokenkind", "unknown"]:
            self.assertIn(col, req.all_data.get("hidden_tokeninfo"))

        # check that it won't be added when logged in as an admin
        g.logged_in_user = {"username": "admin1",
                            "realm": "",
                            "role": "admin"}
        req.all_data = {}
        #        req.User = User("user1")
        hide_tokeninfo(req)
        self.assertEqual(0, len(req.all_data['hidden_tokeninfo']), req.all_data)

        delete_policy("hide_tokeninfo_user")

    def test_19_papertoken_count(self):
        g.logged_in_user = {"username": "admin1",
                            "realm": "",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        set_policy(name="paperpol",
                   scope=SCOPE.ENROLL,
                   action="{0!s}=10".format(PAPERACTION.PAPERTOKEN_COUNT))
        g.policy_object = PolicyClass()

        # request, that matches the policy
        req.all_data = {}
        req.User = User()
        papertoken_count(req)
        # Check if the papertoken count is set
        self.assertEqual(req.all_data.get("papertoken_count"), "10")

        # finally delete policy
        delete_policy("paperpol")

    def test_19_tantoken_count(self):
        g.logged_in_user = {"username": "admin1",
                            "realm": "",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        set_policy(name="tanpol",
                   scope=SCOPE.ENROLL,
                   action="{0!s}=10".format(TANACTION.TANTOKEN_COUNT))
        g.policy_object = PolicyClass()

        # request, that matches the policy
        req.all_data = {}
        req.User = User()
        tantoken_count(req)
        # Check if the tantoken count is set
        self.assertEqual(req.all_data.get("tantoken_count"), "10")

        # finally delete policy
        delete_policy("tanpol")

    def test_20_allowed_audit_realm(self):
        g.logged_in_user = {"username": "admin1",
                            "realm": "",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        #
        set_policy(name="auditrealm1",
                   scope=SCOPE.ADMIN,
                   action=ACTION.AUDIT,
                   user="admin1",
                   realm="realm1")
        set_policy(name="auditrealm2",
                   scope=SCOPE.ADMIN,
                   action=ACTION.AUDIT,
                   user="admin1",
                   realm=["realm2", "realm3"])
        g.policy_object = PolicyClass()

        # request, that matches the policy
        req.all_data = {}
        req.User = User()
        allowed_audit_realm(req)

        # Check if the allowed_audit_realm is set
        self.assertTrue("realm1" in req.all_data.get("allowed_audit_realm"))
        self.assertTrue("realm2" in req.all_data.get("allowed_audit_realm"))
        self.assertTrue("realm3" in req.all_data.get("allowed_audit_realm"))

        # check that the policy is not honored if inactive
        set_policy(name="auditrealm2",
                   active=False)
        g.policy_object = PolicyClass()

        # request, that matches the policy
        req.all_data = {}
        req.User = User()
        allowed_audit_realm(req)
        self.assertEqual(req.all_data.get("allowed_audit_realm"), ["realm1"])

        # finally delete policy
        delete_policy("auditrealm1")
        delete_policy("auditrealm2")

    def test_21_u2f_verify_cert(self):
        # Usually the attestation certificate gets verified during enrollment unless
        # we set the policy scope=enrollment, action=no_verifcy
        from privacyidea.lib.tokens.u2ftoken import U2FACTION
        g.logged_in_user = {"username": "user1",
                            "realm": "",
                            "role": "user"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.User = User()
        # The default behaviour is to verify the certificate
        req.all_data = {
            "type": "u2f"}
        u2ftoken_verify_cert(req, "init")
        self.assertTrue(req.all_data.get("u2f.verify_cert"))

        # Set a policy that defines to NOT verify the certificate
        set_policy(name="polu2f1",
                   scope=SCOPE.ENROLL,
                   action=U2FACTION.NO_VERIFY_CERT)
        g.policy_object = PolicyClass()
        req.all_data = {
            "type": "u2f"}
        u2ftoken_verify_cert(req, "init")
        self.assertFalse(req.all_data.get("u2f.verify_cert"))

        # finally delete policy
        delete_policy("polu2f1")

    def test_01_sms_identifier(self):
        # every admin is allowed to enroll sms token with gw1 or gw2
        set_policy("sms1", scope=SCOPE.ADMIN, action="{0!s}=gw1 gw2".format(SMSACTION.GATEWAYS))
        set_policy("sms2", scope=SCOPE.ADMIN, action="{0!s}=gw3".format(SMSACTION.GATEWAYS))

        g.logged_in_user = {"username": "admin1",
                            "realm": "",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "SMS1234"},
                                 headers={})
        env = builder.get_environ()
        req = Request(env)
        req.User = User()
        req.all_data = {"sms.identifier": "gw1"}
        g.policy_object = PolicyClass()
        r = sms_identifiers(req)
        self.assertTrue(r)

        delete_policy("sms1")
        delete_policy("sms2")
        g.policy_object = PolicyClass()
        # No policy set, the request will fail
        self.assertRaises(PolicyError, sms_identifiers, req)

        # Users are allowed to choose gw4
        set_policy("sms1", scope=SCOPE.USER, action="{0!s}=gw4".format(SMSACTION.GATEWAYS))

        g.logged_in_user = {"username": "root",
                            "realm": "",
                            "role": "user"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "SMS1234"},
                                 headers={})
        env = builder.get_environ()
        req = Request(env)
        req.User = User("root")
        req.all_data = {"sms.identifier": "gw4"}
        g.policy_object = PolicyClass()
        r = sms_identifiers(req)
        self.assertTrue(r)

        # Now the user tries gw1
        req.all_data = {"sms.identifier": "gw1"}
        self.assertRaises(PolicyError, sms_identifiers, req)

        delete_policy("sms1")

    def test_22_push_firebase_config(self):
        from privacyidea.lib.tokens.pushtoken import PUSH_ACTION
        g.logged_in_user = {"username": "user1",
                            "realm": "",
                            "role": "user"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.User = User()
        req.all_data = {
            "type": "push"}
        # In this case we have no firebase config. We will raise an exception
        self.assertRaises(PolicyError, pushtoken_add_config, req, "init")
        # if we have a non existing firebase config, we will raise an exception
        req.all_data = {
            "type": "push",
            PUSH_ACTION.FIREBASE_CONFIG: "non-existing"}
        self.assertRaises(PolicyError, pushtoken_add_config, req, "init")

        # Set a policy for the firebase config to use.
        set_policy(name="push_pol",
                   scope=SCOPE.ENROLL,
                   action="{0!s}=some-fb-config,"
                          "{1!s}=https://privacyidea.com/enroll,"
                          "{2!s}=10".format(PUSH_ACTION.FIREBASE_CONFIG,
                                            PUSH_ACTION.REGISTRATION_URL,
                                            PUSH_ACTION.TTL))
        g.policy_object = PolicyClass()
        req.all_data = {
            "type": "push"}
        pushtoken_add_config(req, "init")
        self.assertEqual(req.all_data.get(PUSH_ACTION.FIREBASE_CONFIG), "some-fb-config")
        self.assertEqual(req.all_data.get(PUSH_ACTION.REGISTRATION_URL), "https://privacyidea.com/enroll")
        self.assertEqual("10", req.all_data.get(PUSH_ACTION.TTL))
        self.assertEqual("1", req.all_data.get(PUSH_ACTION.SSL_VERIFY))

        # the request tries to inject a rogue value, but we assure sslverify=1
        g.policy_object = PolicyClass()
        req.all_data = {
            "type": "push",
            "sslverify": "rogue"}
        pushtoken_add_config(req, "init")
        self.assertEqual("1", req.all_data.get(PUSH_ACTION.SSL_VERIFY))

        # set sslverify="0"
        set_policy(name="push_pol2",
                   scope=SCOPE.ENROLL,
                   action="{0!s}=0".format(PUSH_ACTION.SSL_VERIFY))
        g.policy_object = PolicyClass()
        req.all_data = {
            "type": "push"}
        pushtoken_add_config(req, "init")
        self.assertEqual(req.all_data.get(PUSH_ACTION.FIREBASE_CONFIG), "some-fb-config")
        self.assertEqual("0", req.all_data.get(PUSH_ACTION.SSL_VERIFY))

        # finally delete policy
        delete_policy("push_pol")
        delete_policy("push_pol2")

    def test_23_enroll_different_tokentypes_in_different_resolvers(self):
        # One realm has different resolvers.
        # The different users are allowed to enroll different tokentypes.
        realm = "myrealm"
        # We need this, to create the resolver3
        self.setUp_user_realm3()
        (added, failed) = create_realm(realm,
                                       [self.resolvername1, self.resolvername3])
        self.assertEqual(0, len(failed))
        self.assertEqual(2, len(added))
        # We have cornelius@myRealm in self.resolvername1
        # We have corny@myRealm in self.resolvername3
        set_policy("reso1pol", scope=SCOPE.USER, action="enrollTOTP", realm=realm, resolver=self.resolvername1)
        set_policy("reso3pol", scope=SCOPE.USER, action="enrollHOTP", realm=realm, resolver=self.resolvername3)

        # Cornelius is allowed to enroll TOTP
        g.logged_in_user = {"username": "cornelius",
                            "realm": realm,
                            "role": "user"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"type": "totp"}
        req.User = User("cornelius", realm)
        g.policy_object = PolicyClass()
        r = check_token_init(req)
        self.assertTrue(r)

        # Cornelius is not allowed to enroll HOTP
        req.all_data = {"type": "hotp"}
        self.assertRaises(PolicyError,
                          check_token_init, req)

        # Corny is allowed to enroll HOTP
        g.logged_in_user = {"username": "corny",
                            "realm": realm,
                            "role": "user"}
        builder = EnvironBuilder(method='POST',
                                 data={'serial': "OATH123456"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"type": "hotp"}
        req.User = User("corny", realm)
        g.policy_object = PolicyClass()
        r = check_token_init(req)
        self.assertTrue(r)

        # Corny is not allowed to enroll TOTP
        req.all_data = {"type": "totp"}
        self.assertRaises(PolicyError,
                          check_token_init, req)

        delete_policy("reso3pol")
        g.policy_object = PolicyClass()
        # Now Corny is not allowed to enroll anything! Also not hotp anymore,
        # since there is no policy for his resolver.
        req.all_data = {"type": "hotp"}
        self.assertRaises(PolicyError,
                          check_token_init, req)

        delete_policy("reso1pol")
        delete_realm(realm)

    def test_24_push_wait_policy(self):

        # We send a fake push_wait, that is not in the policies
        builder = EnvironBuilder(method='POST',
                                 data={'user': "hans",
                                       'pass': "pin",
                                       'push_wait': "120"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.User = User()
        req.all_data = {"push_wait": "120"}
        g.policy_object = PolicyClass()
        pushtoken_wait(req, None)
        self.assertEqual(req.all_data.get(PUSH_ACTION.WAIT), False)

        # Now we use the policy, to set the push_wait seconds
        set_policy(name="push1", scope=SCOPE.AUTH, action="{0!s}=10".format(PUSH_ACTION.WAIT))
        req.all_data = {}
        g.policy_object = PolicyClass()
        pushtoken_wait(req, None)
        self.assertEqual(req.all_data.get(PUSH_ACTION.WAIT), 10)

        delete_policy("push1")

    def test_24b_push_disable_wait_policy(self):
        # We send a fake push_wait that is not in the policies
        class RequestMock(object):
            pass
        req = RequestMock()
        req.all_data = {"push_wait": "120"}
        pushtoken_disable_wait(req, None)
        self.assertEqual(req.all_data.get(PUSH_ACTION.WAIT), False)

        # But even with a policy, the function still sets PUSH_ACTION.WAIT to False
        set_policy(name="push1", scope=SCOPE.AUTH, action="{0!s}=10".format(PUSH_ACTION.WAIT))
        req = RequestMock()
        req.all_data = {"push_wait": "120"}
        pushtoken_disable_wait(req, None)
        self.assertEqual(req.all_data.get(PUSH_ACTION.WAIT), False)

        delete_policy("push1")

    def test_25_admin_token_list(self):
        # The tokenlist policy can result in a None filter, an empty [] filter or
        # a filter with realms ["realm1", "realm2"].
        # The None is a wildcard, [] allows no listing at all.
        admin1 = {"username": "admin1",
                  "role": "admin",
                  "realm": "realm1"}

        # admin1 is allowed to see realm1
        set_policy(name="pol-realm1",
                   scope=SCOPE.ADMIN,
                   action="tokenlist", user="admin1", realm=self.realm1)

        # Admin1 is allowed to list all realms
        set_policy(name="pol-all-realms",
                   scope=SCOPE.ADMIN,
                   action="tokenlist", user="admin1")

        # Admin1 is allowed to only init, not list
        set_policy(name="pol-only-init",
                   scope=SCOPE.ADMIN)

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
        r = check_admin_tokenlist(req)
        self.assertTrue(r)
        # The admin1 has the policy "pol-all-realms", so he is allowed to view all realms!
        self.assertEqual(req.pi_allowed_realms, None)

        enable_policy("pol-all-realms", False)
        # Now he is only allowed to view realm1
        g.policy_object = PolicyClass()
        req = Request(env)
        r = check_admin_tokenlist(req)
        self.assertTrue(r)
        # The admin1 has the policy "pol-realm1", so he is allowed to view all realms!
        self.assertEqual(req.pi_allowed_realms, [self.realm1])

        enable_policy("pol-realm1", False)
        # Now he only has the admin right to init tokens
        g.policy_object = PolicyClass()
        req = Request(env)
        r = check_admin_tokenlist(req)
        self.assertTrue(r)
        # The admin1 has the policy "pol-only-init", so he is not allowed to list tokens
        self.assertEqual(req.pi_allowed_realms, [])

        for pol in ["pol-realm1", "pol-all-realms", "pol-only-init"]:
            delete_policy(pol)

    def test_26_indexedsecret_force_set(self):
        self.setUp_user_realms()
        # We send a fake push_wait, that is not in the policies
        builder = EnvironBuilder(method='POST',
                                 data={'user': "cornelius",
                                       'realm': self.realm1,
                                       'type': "indexedsecret"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.User = User("cornelius", self.realm1)
        g.logged_in_user = {"username": "cornelius",
                            "realm": self.realm1,
                            "role": ROLE.USER}
        req.all_data = {"type": "indexedsecret"}
        g.policy_object = PolicyClass()
        indexedsecret_force_attribute(req, None)
        # request.all_data is unchanged
        self.assertNotIn("otpkey", req.all_data)

        # Now we use the policy, to set the otpkey
        set_policy(name="Indexed", scope=SCOPE.USER,
                   action="indexedsecret_{0!s}=username".format(PIIXACTION.FORCE_ATTRIBUTE))
        req.all_data = {"type": "indexedsecret"}
        g.policy_object = PolicyClass()
        indexedsecret_force_attribute(req, None)
        # Now the request.all_data contains the otpkey from the user attributes.
        self.assertIn("otpkey", req.all_data)
        self.assertEqual("cornelius", req.all_data.get("otpkey"))

        delete_policy("Indexed")

    def test_26a_webauthn_auth_validate_triggerchallenge(self):
        class RequestMock(object):
            pass

        # Normal request
        request = RequestMock()
        request.all_data = {
            'user': 'foo'
        }
        webauthntoken_auth(request, None)
        self.assertEqual(set(request.all_data.get(WEBAUTHNACTION.ALLOWED_TRANSPORTS)),
                         set(DEFAULT_ALLOWED_TRANSPORTS.split()))
        self.assertEqual(request.all_data.get(WebAuthnTokenClass.get_class_type() + '_' + ACTION.CHALLENGETEXT),
                         DEFAULT_CHALLENGE_TEXT_AUTH)

        # Request via serial
        request = RequestMock()
        request.all_data = {
            'serial': WebAuthnTokenClass.get_class_prefix() + '123'
        }
        webauthntoken_auth(request, None)
        self.assertEqual(set(request.all_data.get(WEBAUTHNACTION.ALLOWED_TRANSPORTS)),
                         set(DEFAULT_ALLOWED_TRANSPORTS.split()))
        self.assertEqual(request.all_data.get(WebAuthnTokenClass.get_class_type() + '_' + ACTION.CHALLENGETEXT),
                         DEFAULT_CHALLENGE_TEXT_AUTH)

        # Not a WebAuthn token
        request = RequestMock()
        request.all_data = {
            'serial': 'FOO123'
        }
        webauthntoken_auth(request, None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.ALLOWED_TRANSPORTS),
                         None)
        self.assertEqual(request.all_data.get(WebAuthnTokenClass.get_class_type() + '_' + ACTION.CHALLENGETEXT),
                         None)

        # With policies
        allowed_transports = ALLOWED_TRANSPORTS
        challengetext = "Lorem Ipsum"
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTH,
            action=WEBAUTHNACTION.ALLOWED_TRANSPORTS + '=' + allowed_transports + ','
                  +WebAuthnTokenClass.get_class_type() + '_' + ACTION.CHALLENGETEXT + '=' + challengetext
        )
        request = RequestMock()
        request.all_data = {
            'user': 'foo'
        }
        webauthntoken_auth(request, None)
        self.assertEqual(set(request.all_data.get(WEBAUTHNACTION.ALLOWED_TRANSPORTS)),
                         set(allowed_transports.split()))
        self.assertEqual(request.all_data.get(WebAuthnTokenClass.get_class_type() + '_' + ACTION.CHALLENGETEXT),
                         challengetext)

        # Reset policies
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTH,
            action=''
        )

    def test_26b_webauthn_auth_validate_check(self):
        class RequestMock(object):
            pass
        # Normal request
        request = RequestMock()
        request.all_data = {
            'user': 'foo',
            'pass': '1234'
        }
        webauthntoken_auth(request, None)
        self.assertEqual(set(request.all_data.get(WEBAUTHNACTION.ALLOWED_TRANSPORTS)),
                         set(DEFAULT_ALLOWED_TRANSPORTS.split()))
        self.assertEqual(request.all_data.get(WebAuthnTokenClass.get_class_type() + '_' + ACTION.CHALLENGETEXT),
                         DEFAULT_CHALLENGE_TEXT_AUTH)

        # Request via serial
        request = RequestMock()
        request.all_data = {
            'user': 'foo',
            'serial': WebAuthnTokenClass.get_class_prefix() + '123',
            'pass': '1234'
        }
        webauthntoken_auth(request, None)
        self.assertEqual(set(request.all_data.get(WEBAUTHNACTION.ALLOWED_TRANSPORTS)),
                         set(DEFAULT_ALLOWED_TRANSPORTS.split()))
        self.assertEqual(request.all_data.get(WebAuthnTokenClass.get_class_type() + '_' + ACTION.CHALLENGETEXT),
                         DEFAULT_CHALLENGE_TEXT_AUTH)

        # Not a WebAuthn token
        request = RequestMock()
        request.all_data = {
            'user': 'foo',
            'serial': 'FOO123',
            'pass': '1234'
        }
        webauthntoken_auth(request, None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.ALLOWED_TRANSPORTS),
                         None)
        self.assertEqual(request.all_data.get(WebAuthnTokenClass.get_class_type() + '_' + ACTION.CHALLENGETEXT),
                         None)

        # With policies
        allowed_transports = ALLOWED_TRANSPORTS
        challengetext = "Lorem Ipsum"
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTH,
            action=WEBAUTHNACTION.ALLOWED_TRANSPORTS + '=' + allowed_transports + ','
                  +WebAuthnTokenClass.get_class_type() + '_' + ACTION.CHALLENGETEXT + '=' + challengetext
        )
        request = RequestMock()
        request.all_data = {
            'user': 'foo',
            'pass': '1234'
        }
        webauthntoken_auth(request, None)
        self.assertEqual(set(request.all_data.get(WEBAUTHNACTION.ALLOWED_TRANSPORTS)),
                         set(allowed_transports.split()))
        self.assertEqual(request.all_data.get(WebAuthnTokenClass.get_class_type() + '_' + ACTION.CHALLENGETEXT),
                         challengetext)

        # Reset policies
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTH,
            action=''
        )

    def test_26c_webauthn_auth_auth(self):
        class RequestMock(object):
            pass

        # Normal request
        request = RequestMock()
        request.all_data = {
            'username': 'foo',
            'password': '1234'
        }
        webauthntoken_auth(request, None)
        self.assertEqual(set(request.all_data.get(WEBAUTHNACTION.ALLOWED_TRANSPORTS)),
                         set(DEFAULT_ALLOWED_TRANSPORTS.split()))
        self.assertEqual(request.all_data.get(WebAuthnTokenClass.get_class_type() + '_' + ACTION.CHALLENGETEXT),
                         DEFAULT_CHALLENGE_TEXT_AUTH)

        # With policies
        allowed_transports = ALLOWED_TRANSPORTS
        challengetext = "Lorem Ipsum"
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTH,
            action=WEBAUTHNACTION.ALLOWED_TRANSPORTS + '=' + allowed_transports + ','
                  +WebAuthnTokenClass.get_class_type() + '_' + ACTION.CHALLENGETEXT + '=' + challengetext
        )
        request = RequestMock()
        request.all_data = {
            'username': 'foo',
            'password': '1234'
        }
        webauthntoken_auth(request, None)
        self.assertEqual(set(request.all_data.get(WEBAUTHNACTION.ALLOWED_TRANSPORTS)),
                         set(allowed_transports.split()))
        self.assertEqual(request.all_data.get(WebAuthnTokenClass.get_class_type() + '_' + ACTION.CHALLENGETEXT),
                         challengetext)

        # Reset policies
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTH,
            action=''
        )

    def test_27a_webauthn_authz_validate_check(self):
        class RequestMock(object):
            pass

        # Normal request
        request = RequestMock()
        request.all_data = {
            "credentialid": CRED_ID,
            "authenticatordata": ASSERTION_RESPONSE_TMPL['authData'],
            "clientdata": ASSERTION_RESPONSE_TMPL['clientData'],
            "signaturedata": ASSERTION_RESPONSE_TMPL['signature'],
            "user": "foo",
            "pass": "",
            "challenge": hexlify_and_unicode(webauthn_b64_decode(ASSERTION_CHALLENGE))
        }
        webauthntoken_authz(request, None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.REQ),
                         list())

        # Not a WebAuthn authorization
        request = RequestMock()
        request.all_data = {
            "user": "foo",
            "pass": ""
        }
        webauthntoken_authz(request, None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.REQ),
                         None)

        # With policies
        allowed_certs = "subject/.*Yubico.*/"
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTHZ,
            action=WEBAUTHNACTION.REQ + '=' + allowed_certs
        )
        request = RequestMock()
        request.all_data = {
            "credentialid": CRED_ID,
            "authenticatordata": ASSERTION_RESPONSE_TMPL['authData'],
            "clientdata": ASSERTION_RESPONSE_TMPL['clientData'],
            "signaturedata": ASSERTION_RESPONSE_TMPL['signature'],
            "user": "foo",
            "pass": "",
            "challenge": hexlify_and_unicode(webauthn_b64_decode(ASSERTION_CHALLENGE))
        }
        webauthntoken_authz(request, None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.REQ),
                         [allowed_certs])

        # Reset policies.
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTHZ,
            action=''
        )

    def test_27b_webauthn_authz_auth(self):
        class RequestMock(object):
            pass

        # Normal request
        request = RequestMock()
        request.all_data = {
            "credentialid": CRED_ID,
            "authenticatordata": ASSERTION_RESPONSE_TMPL['authData'],
            "clientdata": ASSERTION_RESPONSE_TMPL['clientData'],
            "signaturedata": ASSERTION_RESPONSE_TMPL['signature'],
            "username": "foo",
            "password": "",
            "challenge": hexlify_and_unicode(webauthn_b64_decode(ASSERTION_CHALLENGE))
        }
        webauthntoken_authz(request, None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.REQ),
                         list())

        # Not a WebAuthn authorization
        request = RequestMock()
        request.all_data = {
            "username": "foo",
            "password": ""
        }
        webauthntoken_authz(request, None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.REQ),
                         None)

        # With policies
        allowed_certs = "subject/.*Yubico.*/"
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTHZ,
            action=WEBAUTHNACTION.REQ + '=' + allowed_certs
        )
        request = RequestMock()
        request.all_data = {
            "credentialid": CRED_ID,
            "authenticatordata": ASSERTION_RESPONSE_TMPL['authData'],
            "clientdata": ASSERTION_RESPONSE_TMPL['clientData'],
            "signaturedata": ASSERTION_RESPONSE_TMPL['signature'],
            "username": "foo",
            "password": "",
            "challenge": hexlify_and_unicode(webauthn_b64_decode(ASSERTION_CHALLENGE))
        }
        webauthntoken_authz(request, None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.REQ),
                         [allowed_certs])

        # Reset policies
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTHZ,
            action=''
        )

    def test_28_webauthn_enroll(self):
        class RequestMock(object):
            pass

        rp_id = RP_ID
        rp_name = RP_NAME

        # Missing RP_ID
        request = RequestMock()
        request.all_data = {
            "type": WebAuthnTokenClass.get_class_type()
        }
        with self.assertRaises(PolicyError):
            webauthntoken_enroll(request, None)

        # Malformed RP_ID
        set_policy(
            name="WebAuthn1",
            scope=SCOPE.ENROLL,
            action=WEBAUTHNACTION.RELYING_PARTY_ID + '=' + 'https://' + rp_id + ','
                  +WEBAUTHNACTION.RELYING_PARTY_NAME + '=' + rp_name
        )
        request = RequestMock()
        request.all_data = {
            "type": WebAuthnTokenClass.get_class_type()
        }
        with self.assertRaises(PolicyError):
            webauthntoken_enroll(request, None)

        # Missing RP_NAME
        set_policy(
            name="WebAuthn1",
            scope=SCOPE.ENROLL,
            action=WEBAUTHNACTION.RELYING_PARTY_ID + '=' + rp_id
        )
        request = RequestMock()
        request.all_data = {
            "type": WebAuthnTokenClass.get_class_type()
        }
        with self.assertRaises(PolicyError):
            webauthntoken_enroll(request, None)

        set_policy(
            name="WebAuthn1",
            scope=SCOPE.ENROLL,
            action=WEBAUTHNACTION.RELYING_PARTY_ID + '=' + rp_id + ','
                   +WEBAUTHNACTION.RELYING_PARTY_NAME + '=' + rp_name
        )

        # Normal request
        request = RequestMock()
        request.all_data = {
            "type": WebAuthnTokenClass.get_class_type()
        }
        webauthntoken_enroll(request, None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.RELYING_PARTY_ID),
                         rp_id)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.RELYING_PARTY_NAME),
                         rp_name)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.AUTHENTICATOR_ATTACHMENT),
                         None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.PUBLIC_KEY_CREDENTIAL_ALGORITHMS),
                         [PUBLIC_KEY_CREDENTIAL_ALGORITHMS[x]
                          for x in PUBKEY_CRED_ALGORITHMS_ORDER
                          if x in DEFAULT_PUBLIC_KEY_CREDENTIAL_ALGORITHM_PREFERENCE])
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_LEVEL),
                         DEFAULT_AUTHENTICATOR_ATTESTATION_LEVEL)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_FORM),
                         DEFAULT_AUTHENTICATOR_ATTESTATION_FORM)
        self.assertEqual(request.all_data.get(WebAuthnTokenClass.get_class_type() + '_' + ACTION.CHALLENGETEXT),
                         DEFAULT_CHALLENGE_TEXT_ENROLL)

        # Not a WebAuthn token
        request = RequestMock()
        request.all_data = {
            "type": "footoken"
        }
        webauthntoken_enroll(request, None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.RELYING_PARTY_ID),
                         None),
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.RELYING_PARTY_NAME),
                         None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.AUTHENTICATOR_ATTACHMENT),
                         None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.PUBLIC_KEY_CREDENTIAL_ALGORITHMS),
                         None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_LEVEL),
                         None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_FORM),
                         None)
        self.assertEqual(request.all_data.get(WebAuthnTokenClass.get_class_type() + '_' + ACTION.CHALLENGETEXT),
                         None)

        # With policies
        authenticator_attachment = AUTHENTICATOR_ATTACHMENT_TYPE.CROSS_PLATFORM
        public_key_credential_algorithm_preference = 'ecdsa'
        authenticator_attestation_level = ATTESTATION_LEVEL.TRUSTED
        authenticator_attestation_form = ATTESTATION_FORM.INDIRECT
        challengetext = "Lorem Ipsum"
        set_policy(
            name="WebAuthn2",
            scope=SCOPE.ENROLL,
            action=WEBAUTHNACTION.AUTHENTICATOR_ATTACHMENT + '=' + authenticator_attachment + ','
                   + WEBAUTHNACTION.PUBLIC_KEY_CREDENTIAL_ALGORITHMS + '='
                   + public_key_credential_algorithm_preference + ','
                   + WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_LEVEL + '=' + authenticator_attestation_level + ','
                   + WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_FORM + '=' + authenticator_attestation_form + ','
                   + WebAuthnTokenClass.get_class_type() + '_' + ACTION.CHALLENGETEXT + '=' + challengetext
        )
        request = RequestMock()
        request.all_data = {
            "type": WebAuthnTokenClass.get_class_type()
        }
        webauthntoken_enroll(request, None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.AUTHENTICATOR_ATTACHMENT),
                         authenticator_attachment)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.PUBLIC_KEY_CREDENTIAL_ALGORITHMS),
                         [PUBLIC_KEY_CREDENTIAL_ALGORITHMS[
                             public_key_credential_algorithm_preference
                         ]])
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_LEVEL),
                         authenticator_attestation_level)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_FORM),
                         authenticator_attestation_form)
        self.assertEqual(request.all_data.get(WebAuthnTokenClass.get_class_type() + '_' + ACTION.CHALLENGETEXT),
                         challengetext)

        # Malformed policies
        request = RequestMock()
        request.all_data = {
            "type": WebAuthnTokenClass.get_class_type()
        }
        set_policy(
            name="WebAuthn2",
            scope=SCOPE.ENROLL,
            action=WEBAUTHNACTION.PUBLIC_KEY_CREDENTIAL_ALGORITHMS + '=' + 'b0rked'
        )
        with self.assertRaises(PolicyError):
            webauthntoken_enroll(request, None)
        set_policy(
            name="WebAuthn2",
            scope=SCOPE.ENROLL,
            action=WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_LEVEL + '=' + 'b0rked'
        )
        with self.assertRaises(PolicyError):
            webauthntoken_enroll(request, None)
        set_policy(
            name="WebAuthn2",
            scope=SCOPE.ENROLL,
            action=WEBAUTHNACTION.AUTHENTICATOR_ATTESTATION_FORM + '=' + 'b0rked'
        )
        with self.assertRaises(PolicyError):
            webauthntoken_enroll(request, None)

        # Reset policies
        set_policy(
            name="WebAuthn1",
            scope=SCOPE.ENROLL,
            action=''
        )
        set_policy(
            name="WebAuthn2",
            scope=SCOPE.ENROLL,
            action=''
        )

    def test_29a_webauthn_request_token_init(self):
        class RequestMock(object):
            pass

        # Normal request
        request = RequestMock()
        request.all_data = {
            "type": WebAuthnTokenClass.get_class_type()
        }
        request.environ = {
            "HTTP_ORIGIN": ORIGIN
        }
        webauthntoken_request(request, None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.TIMEOUT),
                         DEFAULT_TIMEOUT * 1000)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT),
                         DEFAULT_USER_VERIFICATION_REQUIREMENT)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.AUTHENTICATOR_SELECTION_LIST),
                         None)
        self.assertEqual(request.all_data.get('HTTP_ORIGIN'),
                         ORIGIN)

        # Not a WebAuthn token
        request = RequestMock()
        request.all_data = {
            "type": "footoken"
        }
        request.environ = {
            "HTTP_ORIGIN": ORIGIN
        }
        webauthntoken_request(request, None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.TIMEOUT),
                         None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT),
                         None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.AUTHENTICATOR_SELECTION_LIST),
                         None)
        self.assertEqual(request.all_data.get('HTTP_ORIGIN'),
                         None)

        # With policies
        timeout = 30
        user_verification_requirement = USER_VERIFICATION_LEVEL.REQUIRED
        authenticator_selection_list = 'foo bar baz'
        set_policy(
            name="WebAuthn",
            scope=SCOPE.ENROLL,
            action=WEBAUTHNACTION.TIMEOUT + '=' + str(timeout) + ','
                  +WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT + '=' + user_verification_requirement + ','
                  +WEBAUTHNACTION.AUTHENTICATOR_SELECTION_LIST + '=' + authenticator_selection_list
        )
        request = RequestMock()
        request.all_data = {
            "type": WebAuthnTokenClass.get_class_type()
        }
        request.environ = {
            "HTTP_ORIGIN": ORIGIN
        }
        webauthntoken_request(request, None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.TIMEOUT),
                         timeout * 1000)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT),
                         user_verification_requirement)
        self.assertEqual(set(request.all_data.get(WEBAUTHNACTION.AUTHENTICATOR_SELECTION_LIST)),
                         set(authenticator_selection_list.split()))

        # Malformed policies
        request = RequestMock()
        request.all_data = {
            "type": WebAuthnTokenClass.get_class_type()
        }
        request.environ = {
            "HTTP_ORIGIN": ORIGIN
        }
        set_policy(
            name="WebAuthn",
            scope=SCOPE.ENROLL,
            action=WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT + '=' + 'b0rked'
        )
        with self.assertRaises(PolicyError):
            webauthntoken_request(request, None)

        # Reset policies
        set_policy(
            name="WebAuthn",
            scope=SCOPE.ENROLL,
            action=''
        )

    def test_29b_webauthn_request_validate_triggerchallenge(self):
        class RequestMock(object):
            pass

        # Normal request
        request = RequestMock()
        request.all_data = {
            'user': 'foo'
        }
        request.environ = {
            "HTTP_ORIGIN": ORIGIN
        }
        webauthntoken_request(request, None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.TIMEOUT),
                         DEFAULT_TIMEOUT * 1000)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT),
                         DEFAULT_USER_VERIFICATION_REQUIREMENT)
        self.assertEqual(request.all_data.get('HTTP_ORIGIN'),
                         ORIGIN)

        # Request via serial
        request = RequestMock()
        request.all_data = {
            'serial': WebAuthnTokenClass.get_class_prefix() + '123'
        }
        request.environ = {
            "HTTP_ORIGIN": ORIGIN
        }
        webauthntoken_request(request, None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.TIMEOUT),
                         DEFAULT_TIMEOUT * 1000)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT),
                         DEFAULT_USER_VERIFICATION_REQUIREMENT)
        self.assertEqual(request.all_data.get('HTTP_ORIGIN'),
                         ORIGIN)

        # Not a WebAuthn token
        request = RequestMock()
        request.all_data = {
            'serial': 'FOO123'
        }
        request.environ = {
            "HTTP_ORIGIN": ORIGIN
        }
        webauthntoken_request(request, None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.TIMEOUT),
                         None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT),
                         None)
        self.assertEqual(request.all_data.get('HTTP_ORIGIN'),
                         None)

        # With policies
        timeout = 30
        user_verification_requirement = USER_VERIFICATION_LEVEL.REQUIRED
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTH,
            action=WEBAUTHNACTION.TIMEOUT + '=' + str(timeout) + ','
                  +WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT + '=' + user_verification_requirement
        )
        request = RequestMock()
        request.all_data = {
            "user": "foo"
        }
        request.environ = {
            "HTTP_ORIGIN": ORIGIN
        }
        webauthntoken_request(request, None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.TIMEOUT),
                         timeout * 1000)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT),
                         user_verification_requirement)

        # Reset policies
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTH,
            action=''
        )

    def test_29c_webauthn_request_auth_authn(self):
        class RequestMock(object):
            pass

        # Normal request
        request = RequestMock()
        request.all_data = {
            'username': 'foo',
            'password': '1234'
        }
        request.environ = {
            "HTTP_ORIGIN": ORIGIN
        }
        webauthntoken_request(request, None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.TIMEOUT),
                         DEFAULT_TIMEOUT * 1000)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT),
                         DEFAULT_USER_VERIFICATION_REQUIREMENT)
        self.assertEqual(request.all_data.get('HTTP_ORIGIN'),
                         ORIGIN)

        # With policies
        timeout = 30
        user_verification_requirement = USER_VERIFICATION_LEVEL.REQUIRED
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTH,
            action=WEBAUTHNACTION.TIMEOUT + '=' + str(timeout) + ','
                  +WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT + '=' + user_verification_requirement
        )
        request = RequestMock()
        request.all_data = {
            "username": "foo",
            "password": "1234"
        }
        request.environ = {
            "HTTP_ORIGIN": ORIGIN
        }
        webauthntoken_request(request, None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.TIMEOUT),
                         timeout * 1000)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT),
                         user_verification_requirement)

        # Reset policies
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTH,
            action=''
        )

    def test_29d_webauthn_request_auth_authz(self):
        class RequestMock(object):
            pass

        # Normal request
        request = RequestMock()
        request.all_data = {
            "credentialid": CRED_ID,
            "authenticatordata": ASSERTION_RESPONSE_TMPL['authData'],
            "clientdata": ASSERTION_RESPONSE_TMPL['clientData'],
            "signaturedata": ASSERTION_RESPONSE_TMPL['signature'],
            "username": "foo",
            "password": "",
            "challenge": hexlify_and_unicode(webauthn_b64_decode(ASSERTION_CHALLENGE))
        }
        request.environ = {
            "HTTP_ORIGIN": ORIGIN
        }
        webauthntoken_request(request, None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.AUTHENTICATOR_SELECTION_LIST),
                         None)
        self.assertEqual(request.all_data.get('HTTP_ORIGIN'),
                         ORIGIN)

        # With policies
        authenticator_selection_list = 'foo bar baz'
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTHZ,
            action=WEBAUTHNACTION.AUTHENTICATOR_SELECTION_LIST + '=' + authenticator_selection_list
        )
        request = RequestMock()
        request.all_data = {
            "credentialid": CRED_ID,
            "authenticatordata": ASSERTION_RESPONSE_TMPL['authData'],
            "clientdata": ASSERTION_RESPONSE_TMPL['clientData'],
            "signaturedata": ASSERTION_RESPONSE_TMPL['signature'],
            "username": "foo",
            "password": "",
            "challenge": hexlify_and_unicode(webauthn_b64_decode(ASSERTION_CHALLENGE))
        }
        request.environ = {
            "HTTP_ORIGIN": ORIGIN
        }
        webauthntoken_request(request, None)
        self.assertEqual(set(request.all_data.get(WEBAUTHNACTION.AUTHENTICATOR_SELECTION_LIST)),
                         set(authenticator_selection_list.split()))

        # Reset policies
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTHZ,
            action=''
        )

    def test_29e_webauthn_request_validate_check_authn(self):
        class RequestMock(object):
            pass

        # Normal request
        request = RequestMock()
        request.all_data = {
            'user': 'foo',
            'pass': '1234'
        }
        request.environ = {
            "HTTP_ORIGIN": ORIGIN
        }
        webauthntoken_request(request, None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.TIMEOUT),
                         DEFAULT_TIMEOUT * 1000)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT),
                         DEFAULT_USER_VERIFICATION_REQUIREMENT)
        self.assertEqual(request.all_data.get('HTTP_ORIGIN'),
                         ORIGIN)

        # With policies
        timeout = 30
        user_verification_requirement = USER_VERIFICATION_LEVEL.REQUIRED
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTH,
            action=WEBAUTHNACTION.TIMEOUT + '=' + str(timeout) + ','
                  +WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT + '=' + user_verification_requirement
        )
        request = RequestMock()
        request.all_data = {
            "user": "foo",
            "pass": "1234"
        }
        request.environ = {
            "HTTP_ORIGIN": ORIGIN
        }
        webauthntoken_request(request, None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.TIMEOUT),
                         timeout * 1000)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT),
                         user_verification_requirement)

        # Reset policies
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTH,
            action=''
        )

    def test_29f_webauthn_request_validate_check_authz(self):
        class RequestMock(object):
            pass

        # Normal request
        request = RequestMock()
        request.all_data = {
            "credentialid": CRED_ID,
            "authenticatordata": ASSERTION_RESPONSE_TMPL['authData'],
            "clientdata": ASSERTION_RESPONSE_TMPL['clientData'],
            "signaturedata": ASSERTION_RESPONSE_TMPL['signature'],
            "user": "foo",
            "pass": "",
            "challenge": hexlify_and_unicode(webauthn_b64_decode(ASSERTION_CHALLENGE))
        }
        request.environ = {
            "HTTP_ORIGIN": ORIGIN
        }
        webauthntoken_request(request, None)
        self.assertEqual(request.all_data.get(WEBAUTHNACTION.AUTHENTICATOR_SELECTION_LIST),
                         None)
        self.assertEqual(request.all_data.get('HTTP_ORIGIN'),
                         ORIGIN)

        # With policies
        authenticator_selection_list = 'foo bar baz'
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTHZ,
            action=WEBAUTHNACTION.AUTHENTICATOR_SELECTION_LIST + '=' + authenticator_selection_list
        )
        request = RequestMock()
        request.all_data = {
            "credentialid": CRED_ID,
            "authenticatordata": ASSERTION_RESPONSE_TMPL['authData'],
            "clientdata": ASSERTION_RESPONSE_TMPL['clientData'],
            "signaturedata": ASSERTION_RESPONSE_TMPL['signature'],
            "user": "foo",
            "pass": "",
            "challenge": hexlify_and_unicode(webauthn_b64_decode(ASSERTION_CHALLENGE))
        }
        request.environ = {
            "HTTP_ORIGIN": ORIGIN
        }
        webauthntoken_request(request, None)
        self.assertEqual(set(request.all_data.get(WEBAUTHNACTION.AUTHENTICATOR_SELECTION_LIST)),
                         set(authenticator_selection_list.split()))

        # Reset policies
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTHZ,
            action=''
        )

    def test_30_webauthn_allowed_req(self):
        class RequestMock(object):
            pass

        request = RequestMock()
        request.all_data = {
            "type": WebAuthnTokenClass.get_class_type(),
            "serial": WebAuthnTokenClass.get_class_prefix() + "123",
            "regdata": REGISTRATION_RESPONSE_TMPL['attObj']
        }

        allowed_certs = "subject/.*Yubico.*/"
        set_policy(
            name="WebAuthn",
            scope=SCOPE.ENROLL,
            action=WEBAUTHNACTION.REQ + "=" + allowed_certs
        )
        self.assertTrue(webauthntoken_allowed(request, None))

        allowed_certs = "subject/.*Feitian.*/"
        set_policy(
            name="WebAuthn",
            scope=SCOPE.ENROLL,
            action=WEBAUTHNACTION.REQ + "=" + allowed_certs
        )
        self.assertRaisesRegex(PolicyError,
                               'The WebAuthn token is not allowed to be registered '
                               'due to a policy restriction.',
                               webauthntoken_allowed, request, None)

        set_policy(
            name="WebAuthn",
            scope=SCOPE.ENROLL,
            action=''
        )

    def test_31_webauthn_disallowed_req(self):
        class RequestMock(object):
            pass

        allowed_certs = "subject/.*Frobnicate.*/"

        request = RequestMock()
        request.all_data = {
            "type": WebAuthnTokenClass.get_class_type(),
            "serial": WebAuthnTokenClass.get_class_prefix() + "123",
            "regdata": REGISTRATION_RESPONSE_TMPL['attObj']
        }

        set_policy(
            name="WebAuthn",
            scope=SCOPE.ENROLL,
            action=WEBAUTHNACTION.REQ + "=" + allowed_certs
        )

        with self.assertRaises(PolicyError):
            webauthntoken_allowed(request, None)

        set_policy(
            name="WebAuthn",
            scope=SCOPE.ENROLL,
            action=''
        )

    def test_32_webauthn_allowed_aaguid(self):
        class RequestMock(object):
            pass

        request = RequestMock()
        request.all_data = {
            "type": WebAuthnTokenClass.get_class_type(),
            "serial": WebAuthnTokenClass.get_class_prefix() + "123",
            "regdata": REGISTRATION_RESPONSE_TMPL['attObj']
        }

        self.assertTrue(webauthntoken_allowed(request, None))

    def test_33_webauthn_disallowed_aaguid(self):
        class RequestMock(object):
            pass

        authenticator_selection_list = 'foo bar baz'

        request = RequestMock()
        request.all_data = {
            "type": WebAuthnTokenClass.get_class_type(),
            "serial": WebAuthnTokenClass.get_class_prefix() + "123",
            "regdata": REGISTRATION_RESPONSE_TMPL['attObj']
        }

        set_policy(
            name="WebAuthn",
            scope=SCOPE.ENROLL,
            action=WEBAUTHNACTION.AUTHENTICATOR_SELECTION_LIST + '=' + authenticator_selection_list
        )

        with self.assertRaises(PolicyError):
            webauthntoken_allowed(request, None)

        set_policy(
            name="WebAuthn",
            scope=SCOPE.ENROLL,
            action=''
        )

    def test_34_application_tokentype(self):
        builder = EnvironBuilder(method='POST',
                                 data={'user': "cornelius"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)

        # Set a policy, that the application is allowed to specify tokentype
        set_policy(name="pol1",
                   scope=SCOPE.AUTHZ,
                   action=ACTION.APPLICATION_TOKENTYPE)
        g.policy_object = PolicyClass()

        # check for
        req.all_data = {"type": "tokentype"}
        req.User = User("cornelius", self.realm1)
        check_application_tokentype(req)
        # Check for the tokentype
        self.assertEqual(req.all_data.get("type"), "tokentype")

        # delete the policy, then the application is not allowed to specify the tokentype
        delete_policy("pol1")
        g.policy_object = PolicyClass()

        check_application_tokentype(req)
        # Check that the tokentype was removed
        self.assertEqual(req.all_data.get("type"), None)

    def test_35_require_piv_attestation(self):
        from privacyidea.lib.tokens.certificatetoken import ACTION, REQUIRE_ACTIONS
        builder = EnvironBuilder(method='POST',
                                 data={'user': "cornelius"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)

        # Set a policy, that the application is allowed to specify tokentype
        set_policy(name="pol1",
                   scope=SCOPE.ENROLL,
                   action="{0!s}={1!s}".format(ACTION.REQUIRE_ATTESTATION, REQUIRE_ACTIONS.REQUIRE_AND_VERIFY))
        g.policy_object = PolicyClass()

        # provide an empty attestation
        req.all_data = {"attestation": "",
                        "type": "certificate"}
        req.User = User("cornelius", self.realm1)
        # This will fail, since the attestation is required.
        self.assertRaises(PolicyError, required_piv_attestation, req)
        delete_policy("pol1")

    def test_36_init_registrationcode_length_contents(self):
        g.logged_in_user = {"username": "admin1",
                            "realm": "",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 data={'type': "registration"},
                                 headers={})
        env = builder.get_environ()
        req = Request(env)

        # first test without any policy
        req.all_data = {"user": "cornelius", "realm": "home", "type": "registration"}
        init_token_length_contents(req)
        # Check, if the tokenlabel was added
        self.assertEqual(req.all_data.get("registration.length"), DEFAULT_LENGTH)
        self.assertEqual(req.all_data.get("registration.contents"), DEFAULT_CONTENTS)

        # now create a policy for the length of the registration code
        set_policy(name="reg_length",
                   scope=SCOPE.ENROLL,
                   action="{0!s}={1!s}".format(ACTION.REGISTRATIONCODE_LENGTH, 6))
        set_policy(name="reg_contents",
                   scope=SCOPE.ENROLL,
                   action="{0!s}={1!s}".format(ACTION.REGISTRATIONCODE_CONTENTS, "+n"))
        # request, that matches the policy
        req.all_data = {"user": "cornelius", "realm": "home", "type": "registration"}
        init_token_length_contents(req)
        # Check, if the tokenlabel was added
        self.assertEqual(req.all_data.get("registration.length"), "6")
        self.assertEqual(req.all_data.get("registration.contents"), "+n")
        # delete policy
        delete_policy("reg_length")
        delete_policy("reg_contents")

    def test_37_init_password_length_contents(self):
        g.logged_in_user = {"username": "admin1",
                            "realm": "",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 data={'type': "password", "genkey": 1},
                                 headers={})
        env = builder.get_environ()
        req = Request(env)

        # first test without any policy
        req.all_data = {"user": "cornelius", "realm": "home", "type": "pw", "genkey": 1}
        init_token_length_contents(req)
        # Check, if the tokenlabel was added
        from privacyidea.lib.tokens.passwordtoken import DEFAULT_LENGTH, DEFAULT_CONTENTS
        self.assertEqual(req.all_data.get("pw.length"), DEFAULT_LENGTH)
        self.assertEqual(req.all_data.get("pw.contents"), DEFAULT_CONTENTS)

        # now create a policy for the length of the registration code
        set_policy(name="pw_length",
                   scope=SCOPE.ENROLL,
                   action="{0!s}={1!s}".format(ACTION.PASSWORD_LENGTH, 6))
        set_policy(name="pw_contents",
                   scope=SCOPE.ENROLL,
                   action="{0!s}={1!s}".format(ACTION.PASSWORD_CONTENTS, "+n"))
        # request, that matches the policy
        req.all_data = {"user": "cornelius", "realm": "home", "type": "pw"}
        init_token_length_contents(req)
        # Check, if the tokenlabel was added
        self.assertEqual(req.all_data.get("pw.length"), "6")
        self.assertEqual(req.all_data.get("pw.contents"), "+n")
        # request, that creates a different token type
        req.all_data = {"user": "cornelius", "realm": "home", "type": "hotp", "genkey": "1"}
        init_token_length_contents(req)
        # Check, if the tokenlabel was added
        self.assertNotIn("pw.length", req.all_data)
        self.assertNotIn("pw.contents", req.all_data)
        # delete policy
        delete_policy("pw_length")
        delete_policy("pw_contents")

    def test_40_custom_user_attributes(self):
        g.logged_in_user = {"username": "admin1",
                            "realm": "",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 data={'type': "registration"},
                                 headers={})
        env = builder.get_environ()
        req = Request(env)
        req.User = User("cornelius", self.realm1)

        # first test without any policy to delete the department. This is not allowed
        req.all_data = {"user": "cornelius", "realm": self.realm1, "attrkey": "department"}
        self.assertRaisesRegex(PolicyError,
                                "ERR303: You are not allowed to delete the custom user attribute department!",
                                check_custom_user_attributes, req, "delete")

        # set to allow deleting the department
        set_policy("set_custom_attr", scope=SCOPE.ADMIN,
                   action="{0!s}=department sth".format(ACTION.DELETE_USER_ATTRIBUTES))
        req.all_data = {"user": "cornelius", "realm": self.realm1, "attrkey": "department"}
        check_custom_user_attributes(req, "delete")

        # Now try to delete a different key
        req.all_data = {"user": "cornelius", "realm": self.realm1, "attrkey": "difkey"}
        self.assertRaises(PolicyError, check_custom_user_attributes, req, "delete")

        # Allow to delete diffkey
        set_policy("set_custom_attr2", scope=SCOPE.ADMIN,
                   action="{0!s}=difkey".format(ACTION.DELETE_USER_ATTRIBUTES))
        req.all_data = {"user": "cornelius", "realm": self.realm1, "attrkey": "difkey"}
        check_custom_user_attributes(req, "delete")

        # Now we set the policy to allow to delete any attribute
        set_policy("set_custom_attr2", scope=SCOPE.ADMIN,
                   action="{0!s}=*".format(ACTION.DELETE_USER_ATTRIBUTES))
        req.all_data = {"user": "cornelius", "realm": self.realm1, "attrkey": "department"}
        check_custom_user_attributes(req, "delete")
        req.all_data = {"user": "cornelius", "realm": self.realm1, "attrkey": "anykey"}
        check_custom_user_attributes(req, "delete")

        """
        set custom attributes
        """
        # no policy set
        req.all_data = {"user": "cornelius", "realm": self.realm1,
                        "key": "department", "value": "finance"}
        self.assertRaises(PolicyError, check_custom_user_attributes, req, "set")
        set_policy("set_custom_attr", scope=SCOPE.ADMIN,
                   action="{0!s}=:department: finance devel :color: * :*: 1 2 ".format(ACTION.SET_USER_ATTRIBUTES))
        # Allow to set to finance
        check_custom_user_attributes(req, "set")
        req.all_data = {"user": "cornelius", "realm": self.realm1,
                        "key": "department", "value": "devel"}
        check_custom_user_attributes(req, "set")
        # You are not allowed to set a different department
        req.all_data = {"user": "cornelius", "realm": self.realm1,
                        "key": "department", "value": "different"}
        self.assertRaisesRegex(PolicyError,
                               "ERR303: You are not allowed to set the custom user attribute department!",
                               check_custom_user_attributes, req, "set")

        # You are allowed to set color to any value
        req.all_data = {"user": "cornelius", "realm": self.realm1,
                        "key": "color", "value": "blue"}
        check_custom_user_attributes(req, "set")

        # You are allowed to set any other value to 1 or 2
        req.all_data = {"user": "cornelius", "realm": self.realm1,
                        "key": "size", "value": "1"}
        check_custom_user_attributes(req, "set")
        req.all_data = {"user": "cornelius", "realm": self.realm1,
                        "key": "size", "value": "2"}
        check_custom_user_attributes(req, "set")
        # But not to another value
        req.all_data = {"user": "cornelius", "realm": self.realm1,
                        "key": "size", "value": "3"}
        self.assertRaises(PolicyError, check_custom_user_attributes, req, "set")

        # Now you can set any key to any value
        set_policy("set_custom_attr2", scope=SCOPE.ADMIN,
                   action="{0!s}=:*: *".format(ACTION.SET_USER_ATTRIBUTES))
        req.all_data = {"user": "cornelius", "realm": self.realm1,
                        "key": "size", "value": "3"}
        check_custom_user_attributes(req, "set")

    def test_50_enroll_ca_connector(self):
        g.logged_in_user = {"username": "admin1",
                            "realm": "",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 data={'type': "certificate", "genkey": 1},
                                 headers={})
        env = builder.get_environ()
        req = Request(env)

        # first test without any policy
        req.all_data = {"user": "cornelius", "realm": "home", "type": "certificate", "genkey": 1}
        init_ca_connector(req)
        init_ca_template(req)
        init_subject_components(req)
        # Check, if that there is no parameter set
        self.assertNotIn("ca", req.all_data)
        self.assertNotIn("template", req.all_data)
        self.assertNotIn("subject_components", req.all_data)

        # now create a policy for the CA connector and the template
        set_policy(name="ca",
                   scope=SCOPE.ENROLL,
                   action="{0!s}={1!s},{2!s}={3!s}".format(
                     CERTIFICATE_ACTION.CA_CONNECTOR, "caconnector",
                     CERTIFICATE_ACTION.CERTIFICATE_TEMPLATE, "catemplate"
                   ))
        set_policy(name="sub1",
                   scope=SCOPE.ENROLL,
                   action="{0!s}=email".format(
                       CERTIFICATE_ACTION.CERTIFICATE_REQUEST_SUBJECT_COMPONENT))
        set_policy(name="sub2",
                   scope=SCOPE.ENROLL,
                   action="{0!s}=email realm".format(
                       CERTIFICATE_ACTION.CERTIFICATE_REQUEST_SUBJECT_COMPONENT))
        # request, that matches the policy
        req.all_data = {"user": "cornelius", "realm": "home", "type": "certificate", "genkey": 1}
        # check that the parameters were added
        init_ca_connector(req)
        init_ca_template(req)
        init_subject_components(req)
        # Check, if that there is no parameter set
        self.assertIn("ca", req.all_data)
        self.assertIn("template", req.all_data)
        self.assertIn("subject_components", req.all_data)
        self.assertEqual("caconnector", req.all_data.get("ca"))
        self.assertEqual("catemplate", req.all_data.get("template"))
        self.assertIn("email", req.all_data.get("subject_components"))
        self.assertIn("realm", req.all_data.get("subject_components"))

        # request, that matches the policy
        req.all_data = {"user": "cornelius", "realm": "home", "type": "hotp", "genkey": 1}
        # check that it only works for certificate tokens
        init_ca_connector(req)
        init_ca_template(req)
        init_subject_components(req)
        # Check, if that there is no parameter set
        self.assertNotIn("ca", req.all_data)
        self.assertNotIn("template", req.all_data)
        self.assertNotIn("subject_components", req.all_data)

        # delete policy
        delete_policy("ca")
        delete_policy("sub1")
        delete_policy("sub2")

    def test_60_increase_failcounter_on_challenge(self):
        builder = EnvironBuilder(method='POST',
                                 data={'user': "hans", "pass": "123456"},
                                 headers={})
        env = builder.get_environ()
        req = Request(env)
        req.User = User()

        # Check, if that there is no parameter set
        req.all_data = {"user": "hans", "pass": "123456"}
        self.assertNotIn("increase_failcounter_on_challenge", req.all_data)

        # Check that the parameters were added
        increase_failcounter_on_challenge(req)
        self.assertIn("increase_failcounter_on_challenge", req.all_data)

        # Check that value is False with no policy
        self.assertEqual(False, req.all_data.get("increase_failcounter_on_challenge"))

        # Set policy
        set_policy(name="increase_failcounter_on_challenge",
                   scope=SCOPE.AUTH,
                   action=ACTION.INCREASE_FAILCOUNTER_ON_CHALLENGE)

        # Check that value is True with set policy
        increase_failcounter_on_challenge(req)
        self.assertEqual(True, req.all_data.get("increase_failcounter_on_challenge"))

        # delete policy
        delete_policy("increase_failcounter_on_challenge")

    def test_61_required_description_for_specified_token_types(self):
        g.logged_in_user = {"username": "cornelius",
                            "role": "user"}
        builder = EnvironBuilder(method='POST',
                                 headers={})
        env = builder.get_environ()
        # Set policy
        set_policy(name="require_description",
                   scope=SCOPE.ENROLL,
                   action=["{0!s}=hotp".format(ACTION.REQUIRE_DESCRIPTION)])
        req = Request(env)
        req.User = User("cornelius")

        # Only a description is set, no type
        # This should work without a defined type because hotp is default
        req.all_data = {"description": "test"}
        self.assertIsNone(require_description(req))

        # Totp token is not defined in pol and should be rolled oud without desc
        req.all_data = {"type": "totp"}
        self.assertIsNone(require_description(req))

        # Type and description is set, token should be rolled out
        req.all_data = {"type": "hotp",
                        "description": "test"}
        self.assertIsNone(require_description(req))

        # This should not work, a description is required for hotp
        req.all_data = {"type": "hotp"}
        self.assertRaisesRegex(PolicyError,
                               "ERR303: Description required for hotp token.",
                               require_description, req)

        delete_policy("require_description")


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
        token_obj.del_tokeninfo("testkey")
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
        builder = EnvironBuilder(method='POST',
                                 data={'user': "cornelius",
                                       "pass": "test"},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        self.setUp_user_realms()
        req.User = User("autoassignuser", self.realm1)
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

        g.policy_object = PolicyClass()

        new_response = add_user_detail_to_response(req, resp)
        jresult = new_response.json
        self.assertTrue("user" not in jresult.get("detail"), jresult)

        # A successful get a user added
        # Set a policy, that adds user info to detail
        set_policy(name="pol_add_user",
                   scope=SCOPE.AUTHZ,
                   action=ACTION.ADDUSERINRESPONSE, client="10.0.0.0/8")
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
                   action=ACTION.ADDUSERINRESPONSE, client="10.0.0.0/8", realm=self.realm2)
        g.policy_object = PolicyClass()

        new_response = add_user_detail_to_response(req, resp)
        jresult = new_response.json
        self.assertNotIn("user", jresult.get("detail"), jresult)

        # set a policy that adds user resolver to detail
        set_policy(name="pol_add_resolver",
                   scope=SCOPE.AUTHZ,
                   action=ACTION.ADDRESOLVERINRESPONSE, client="10.0.0.0/8")
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
                   action=ACTION.ADDRESOLVERINRESPONSE, client="10.0.0.0/8", realm=self.realm2)
        g.policy_object = PolicyClass()

        new_response = add_user_detail_to_response(req, resp)
        jresult = new_response.json
        self.assertNotIn("user-realm", jresult.get("detail"), jresult)
        self.assertNotIn("user-resolver", jresult.get("detail"), jresult)

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
                   action="{0!s}={1!s}".format(ACTION.AUTOASSIGN, AUTOASSIGNVALUE.NONE),
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
        tokenobject = init_token({"serial": "UASSIGN2", "type": "hotp",
                                  "otpkey": "3132333435363738393031"
                                            "323334353637383930"},
                                 tokenrealms=[self.realm1])
        user_obj = User("autoassignuser", self.realm1)
        # unassign all tokens from the user autoassignuser
        try:
            unassign_token(None, user=user_obj)
        except Exception as e:
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
                   action="{0!s}={1!s}".format(ACTION.AUTOASSIGN,
                                     AUTOASSIGNVALUE.USERSTORE),
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
        res = tokenobject.check_otp("516516") # count = 99
        self.assertEqual(res, -1)
        # check that we can authenticate online with the correct value
        res = tokenobject.check_otp("295165")  # count = 100
        self.assertEqual(res, 100)

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
        sign_object = Sign(private_key=None,
                           public_key=open("tests/testdata/public.pem", 'rb').read())

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
                   action=ACTION.TOKENWIZARD)
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
        set_policy(name="pol_dialog", scope=SCOPE.WEBUI, action=ACTION.DIALOG_NO_TOKEN)
        g.policy_object = PolicyClass()
        new_response = get_webui_settings(req, resp)
        jresult = new_response.json
        self.assertEqual(jresult.get("result").get("value").get(
            ACTION.DIALOG_NO_TOKEN), True)
        delete_policy("pol_dialog")

        # Set a policy for the QR codes
        set_policy(name="pol_qr1", scope=SCOPE.WEBUI, action=ACTION.SHOW_ANDROID_AUTHENTICATOR)
        set_policy(name="pol_qr2", scope=SCOPE.WEBUI, action=ACTION.SHOW_IOS_AUTHENTICATOR)
        set_policy(name="pol_qr3", scope=SCOPE.WEBUI,
                   action="{0!s}=http://privacyidea.org".format(ACTION.SHOW_CUSTOM_AUTHENTICATOR))

        custom_url = create_img("http://privacyidea.org")
        g.policy_object = PolicyClass()
        new_response = get_webui_settings(req, resp)
        jresult = new_response.json
        self.assertEqual('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAZoAAAG'
                         'aAQAAAAAefbjOAAACFElEQVR42u1cS07FMBCL6AFypHd1jtQDVJrX'
                         'zD+FBbBDdhZPbVpviOV4nClDfj8+B0EEEUQQQQQRRFCAho/jnpnrd'
                         'uozHyJnXL4U9DH+MAj6HyBnhK60nIeRwVd/3eaD9h4ZgcCI0ylwa8'
                         'TlUiByX4371qkyDjICkBF9w1Bu1AMyAlMjljKYKKw5lQxqBLSPaLQ'
                         'wy1lz9BFAjMhaw/3k84e1BhgjtqHy4BbidhTH15KVfz0QjSgpaJKh'
                         'FFhmwhwFGYGiEUqGWauvMZXWoe4s7RXuGjjO8so8wm+DKmtuHOLJB'
                         'BkBU31GhWHG4fzecpIRQM7ysoVXjTBaZBRhOabuKWQEjkaMEWTY5S'
                         'FpYfUHGQGiES2anCEZLdTevQUZAVF91pFG5lISkuHegj4CSiO2Q29'
                         '94LrhWwc1Aq/WeAQQVpHqeByTkxEIu0Zrmupp1ONwnBqBoxHRHVNd'
                         'EVF4imyRBRmBkke4vWxXmVXRR0DWGrrwIlsbXb4SvTP0EVjOsrfaZ'
                         'mDVfqgRUIwojfBWqao/PMUe9BFozrL3R+QpaM1NdtWBOcstnNqPPW'
                         'tjISOgnGULsK8UhTjheJ2DPgJp1+gpdjXL2DuvarwjI5CcZX6oE/0'
                         'RfSfxrYOMgGNEbg4+V19usGMGVyOaZ2hf9dBHQPqIOPss95CbCPMI'
                         'zFqjjRlt+y4ZzCwR8wj+PxaCCCKIIIIIIuinoDczovv0cx3r0AAAA'
                         'ABJRU5ErkJggg==',
                         jresult.get("result").get("value").get("qr_image_android"))
        self.assertEqual('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAZoAAAG'
                         'aAQAAAAAefbjOAAACC0lEQVR42u2cUW7DMAxDheUAPlKvniPlAAa8'
                         'xpYtufnZ9jfw5aPo0vCnJiSSUmft99dpgAABAgQIECBAE2R+He/31'
                         '9Hsdd3vWh133/fmA68O+rI/XID+B8gZ0U86keHy0zcr/kF6DkYoMK'
                         'JTIB189YpzljZY0isIjNBjxDh4K3fDKLluwAjVGnGmNhE6Akbo6oh'
                         'eHm6CuORER2gyYnmN0SEeL3gNMUZsfrTfq1NWlPp8hG9PpEaMUnBT'
                         '4FwvQ0ykP2GERo04h2ystpmLWS08uqJrSNWIY9IiEqotvaRG6NWIu'
                         'NxrdDM69KQXDxihoyw/E6qWk4keXA4fCiNUasTQjqtKbJ4zBVboCB'
                         'kdMccX3ib2SZf3FHSEECNGZtm2uDLNPtEReoy43Guk/pF1RLU8D+X'
                         'bU1CWeciV+kfoCKcFjBBSlpFBeQCxzEWZwSU1QkdHeAblGnMbhcba'
                         'DIzQ6Rqbdtw2ZjyhQkfoeY3H5tTkwfAf6Ag997m8xiRDziPQEWru0'
                         '+ec0T+SI229Rhg6QowR3hz63bL5j3692KrTUpYx9sz7Ebb2bf0DGC'
                         'FSI9Lpxy7dGnflBRoYIaQs2xVrMzOrWg7DDB0hqCOO3YdWy/0DryH'
                         'MiLSTT2apzgiz+DlXVhTDgsIIOR0xzcVMJmJZhjxC1GtEFHGuuUZ/'
                         'jl1szTyC/8cCCBAgQIAAAfop6Bt9aCglBgbq7QAAAABJRU5ErkJgg'
                         'g==',
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
                   action="{0!s}={1!s}".format(ACTION.LOGOUT_REDIRECT, redir_uri))
        g.policy_object = PolicyClass()
        new_response = get_webui_settings(req, resp)
        jresult = new_response.json
        self.assertEqual(redir_uri,
                         jresult.get("result").get("value").get("logout_redirect_url"),
                         jresult)
        delete_policy("pol_logout_redirect")


    def test_09_get_webui_settings_token_pagesize(self):
        # Test that policies like tokenpagesize are also user dependent
        self.setUp_user_realms()

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
               "id": 1}
        resp = jsonify(res)

        new_response = get_webui_settings(req, resp)
        jresult = new_response.json
        self.assertEqual(jresult.get("result").get("value").get(
            ACTION.TOKENPAGESIZE), 15)

        # Set a policy. User has not token, so "token_wizard" will be True
        set_policy(name="pol_pagesize",
                   scope=SCOPE.WEBUI,
                   realm=self.realm1,
                   action="{0!s}=177".format(ACTION.TOKENPAGESIZE))
        g.policy_object = PolicyClass()
        new_response = get_webui_settings(req, resp)
        jresult = new_response.json
        self.assertEqual(jresult.get("result").get("value").get(
            ACTION.TOKENPAGESIZE), 177)

        # Now we change the policy pol_pagesize this way, that it is only valid for the user "root"
        set_policy(name="pol_pagesize",
                   scope=SCOPE.WEBUI,
                   realm=self.realm1,
                   user="root",
                   action="{0!s}=177".format(ACTION.TOKENPAGESIZE))
        # This way the user "cornelius" gets the default pagesize again
        g.policy_object = PolicyClass()
        new_response = get_webui_settings(req, resp)
        jresult = new_response.json
        self.assertEqual(jresult.get("result").get("value").get(
            ACTION.TOKENPAGESIZE), 15)

        delete_policy("pol_pagesize")

    def test_10_get_webui_settings_admin_dashboard(self):
        # Test admin_dashboard
        self.setUp_user_realms()

        # The request with an OTP value and a PIN of a user, who has not
        # token assigned
        builder = EnvironBuilder(method='POST',
                                 data={},
                                 headers={})
        env = builder.get_environ()
        env["REMOTE_ADDR"] = "192.168.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {}

        res = {"jsonrpc": "2.0",
               "result": {"status": True,
                          "value": {"role": "admin",
                                    "username": "cornelius"}},
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
                   action=ACTION.ADMIN_DASHBOARD)
        g.policy_object = PolicyClass()
        new_response = get_webui_settings(req, resp)
        jresult = new_response.json
        self.assertTrue(jresult.get("result").get("value").get(ACTION.ADMIN_DASHBOARD))

        delete_policy("pol_dashboard")

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
                   action=ACTION.CHANGE_PIN_FIRST_USE)
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
                   action="{0!s}=1d".format(ACTION.CHANGE_PIN_EVERY))
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
                   action="{0!s}=These are your options:<ul>".format(ACTION.CHALLENGETEXT_HEADER))
        # Set a policy for the footer
        set_policy(name="pol_footer",
                   scope=SCOPE.AUTH,
                   action="{0!s}=Happy authenticating!".format(ACTION.CHALLENGETEXT_FOOTER))
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
        self.assertEqual(message, "These are your options:<ul><li>enter the HOTP from your email</li>\n<li>enter the TOTP from your SMS</li>\nHappy authenticating!")

        # We do no html list
        set_policy(name="pol_header",
                   scope=SCOPE.AUTH,
                   action="{0!s}=These are your options:".format(ACTION.CHALLENGETEXT_HEADER))
        g.policy_object = PolicyClass()
        resp = jsonify(res)

        r = mangle_challenge_response(req, resp)
        message = r.json.get("detail", {}).get("message")
        self.assertTrue("<ul><li>" not in message, message)
        self.assertEqual(message, "These are your options:\nenter the HOTP from your email, enter the TOTP from your SMS\nHappy authenticating!")

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
        set_policy("auth01", scope=SCOPE.AUTHZ, action="{0!s}={1!s}".format(ACTION.AUTHORIZED, AUTHORIZED.DENY),
                   priority=2)
        g.policy_object = PolicyClass()

        # The request will fail.
        self.assertRaises(ValidateError, is_authorized, req, resp)

        # Now we set a 2nd policy with a higher priority
        set_policy("auth02", scope=SCOPE.AUTHZ, action="{0!s}={1!s}".format(ACTION.AUTHORIZED, AUTHORIZED.ALLOW),
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
        from privacyidea.lib.tokenclass import ROLLOUTSTATE
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
        set_policy("verify_toks", scope=SCOPE.ENROLL, action="{0!s}=hotp".format(ACTION.VERIFY_ENROLLMENT))
        g.policy_object = PolicyClass()

        new_resp = check_verify_enrollment(req, resp)
        detail = new_resp.json.get("detail")
        self.assertEqual(detail.get("verify").get("message"), VERIFY_ENROLLMENT_MESSAGE)
        self.assertEqual(detail.get("rollout_state"), ROLLOUTSTATE.VERIFYPENDING)
        # Also check the token object.
        self.assertEqual(tok.token.rollout_state, ROLLOUTSTATE.VERIFYPENDING)
        delete_policy("verify_toks")
