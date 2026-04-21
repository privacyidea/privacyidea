# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for token-enrollment prepolicies (privacyidea.api.lib.prepolicy)."""
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

from .api_lib_policy_common import PrePolicyHelperMixin


class PrePolicyEnrollTestCase(PrePolicyHelperMixin, MyApiTestCase):

    def setUp(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        self.setUp_user_realm3()

    def test_01b_token_specific_pin_policy(self):
        create_realm("home", [{'name': self.resolvername1}])
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
                       PolicyAction.OTPPINMAXLEN, "10",
                       PolicyAction.OTPPINMINLEN, "4",
                       PolicyAction.OTPPINCONTENTS, "cn"),
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
        # Good OTP length, but missing numbers
        self.assertRaises(PolicyError, check_otp_pin, req)

        # finally delete policy
        delete_policy("pol1")
        delete_realm("home")

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
                   action="enrollTOTP, enrollHOTP, {0!s}".format(PolicyAction.IMPORT),
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
                   action="{0!s}={1!s}".format(PolicyAction.MAXACTIVETOKENUSER, 1))
        g.policy_object = PolicyClass()
        # The user has one token, everything is fine.
        init_token({"serial": "NEW001", "type": "hotp",
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
                   action="hotp_{0!s}={1!s}".format(PolicyAction.MAXACTIVETOKENUSER, 1))
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
                   action="{0!s}={1!s}".format(PolicyAction.MAXTOKENUSER, 2))
        g.policy_object = PolicyClass()
        # The user has one token, everything is fine.
        self.setUp_user_realms()
        init_token({"serial": "NEW001", "type": "hotp",
                    "otpkey": "1234567890123456"},
                   user=User(login="cornelius",
                             realm=self.realm1))
        tokenobject_list = get_tokens(user=User(login="cornelius",
                                                realm=self.realm1))
        self.assertTrue(len(tokenobject_list) == 1)
        self.assertTrue(check_max_token_user(req))

        # Now the user gets his second token
        init_token({"serial": "NEW002", "type": "hotp",
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
                   action="{0!s}={1!s}".format(PolicyAction.MAXTOKENUSER, 12))
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
                   action="hotp_{0!s}={1!s}".format(PolicyAction.MAXTOKENUSER, 2))
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

        # and we succeed in issuing a new totp token
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
        # Add the first token into the realm
        init_token({"serial": "NEW001", "type": "hotp",
                    "otpkey": "1234567890123456"})
        set_realms("NEW001", [self.realm1])
        # check the realm, only one token is in it the policy condition will
        # pass
        tokenobject_list = get_tokens(realm=self.realm1)
        self.assertTrue(len(tokenobject_list) == 1)
        self.assertTrue(check_max_token_realm(req))

        # add a second token to the realm
        init_token({"serial": "NEW002", "type": "hotp",
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
                   action=f"{PolicyAction.SETREALM}={self.realm1}",
                   realm=self.realm2)
        g.policy_object = PolicyClass()

        # request, that matches the policy
        req.all_data = {}
        req.User = User()
        set_realm(req)
        # Check, that the realm was not set, since there was no user in the request
        self.assertEqual(req.all_data.get("realm"), None)

        req.all_data = {}
        req.User = User(login="cornelius", realm=self.realm2)
        set_realm(req)
        # Check, if the realm was modified to the realm specified in the policy
        self.assertEqual(req.all_data.get("realm"), self.realm1)

        # do not set realm if set_realm policy is set
        req.all_data = {"realm": self.realm3, "user": "cornelius"}
        req.User = User(login="cornelius", realm=self.realm3)
        g.policies = {PolicyAction.SET_REALM: self.realm3}
        set_realm(req)
        # Check that realm was not modified
        self.assertEqual(self.realm3, req.all_data.get("realm"))
        self.assertEqual(User("cornelius", self.realm3), req.User)
        g.policies = {}

        # A request, that does not match the policy:
        req.all_data = {"realm": "otherrealm"}
        set_realm(req)
        # Check, if the realm is still the same
        self.assertEqual(req.all_data.get("realm"), "otherrealm")

        # If there are several policies, which will produce different realms,
        #  we get an exception
        set_policy(name="pol2",
                   scope=SCOPE.AUTHZ,
                   action=f"{PolicyAction.SETREALM}=ConflictRealm",
                   realm=self.realm2)
        g.policy_object = PolicyClass()
        # This request will trigger two policies with different realms to set
        req.all_data = {"realm": self.realm2}
        req.User = User(login="cornelius", realm=self.realm2)
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
                   action="{0!s}={1!s}".format(PolicyAction.TOKENLABEL, "<u>@<r>"))
        set_policy(name="pol2",
                   scope=SCOPE.ENROLL,
                   action="{0!s}={1!s}".format(PolicyAction.TOKENISSUER, "myPI"))
        g.policy_object = PolicyClass()

        # request, that matches the policy
        req.all_data = {"user": "cornelius",
                        "realm": "home"}
        init_tokenlabel(req)

        # Check, if the tokenlabel was added
        self.assertEqual(req.all_data.get(PolicyAction.TOKENLABEL), "<u>@<r>")
        # Check, if the tokenissuer was added
        self.assertEqual(req.all_data.get(PolicyAction.TOKENISSUER), "myPI")
        # Check, if force_app_pin wasn't added (since there is no policy)
        self.assertNotIn(PolicyAction.FORCE_APP_PIN, req.all_data, req.all_data)

        # reset the request data and start again with force_app_pin policy
        set_policy(name="pol3",
                   scope=SCOPE.ENROLL,
                   action="hotp_{0!s}=True".format(PolicyAction.FORCE_APP_PIN))
        req.all_data = {"user": "cornelius",
                        "realm": "home"}
        init_tokenlabel(req)
        # Check, if force_app_pin was added and is True
        self.assertTrue(req.all_data.get('force_app_pin'))
        self.assertEqual(req.all_data.get(PolicyAction.APP_FORCE_UNLOCK), "pin")

        # Check that the force_app_pin policy isn't set for totp token
        req.all_data = {"user": "cornelius",
                        "realm": "home",
                        "type": "TOTP"}
        init_tokenlabel(req)
        # Check, that force_app_pin wasn't added
        self.assertNotIn(PolicyAction.FORCE_APP_PIN, req.all_data, req.all_data)

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
                   action="{0!s}={1!s}".format(PolicyAction.OTPPINRANDOM, size_policy))
        set_policy(name="pincontent",
                   scope=SCOPE.ADMIN,
                   action="{0!s}={1!s}".format(PolicyAction.OTPPINCONTENTS, contents_policy))
        set_policy(name="pinhandling",
                   scope=SCOPE.ENROLL,
                   action="{0!s}=privacyidea.lib.pinhandling.base.PinHandler".format(
                       PolicyAction.PINHANDLING))
        g.policy_object = PolicyClass()

        # request, that matches the policy
        req.all_data = {
            "user": "cornelius",
            "realm": "realm1"
        }

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
                   action="{0!s}={1!s}".format(PolicyAction.OTPPINSETRANDOM, size_policy))
        set_policy(name="pincontent",
                   scope=SCOPE.ADMIN,
                   action="{0!s}={1!s}".format(PolicyAction.OTPPINCONTENTS, contents_policy))
        g.policy_object = PolicyClass()

        # request, that matches the policy
        req.all_data = {
            "user": "cornelius",
            "realm": "realm1"
        }

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
            required = ["".join([CHARLIST_CONTENTPOLICY[c] for c in policy[1:]])]
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
            required = [CHARLIST_CONTENTPOLICY[c] for c in policy]
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
                   action="{0!s}=10".format(TANAction.TANTOKEN_COUNT))
        g.policy_object = PolicyClass()

        # request, that matches the policy
        req.all_data = {}
        req.User = User()
        tantoken_count(req)
        # Check if the tantoken count is set
        self.assertEqual(req.all_data.get("tantoken_count"), "10")

        # finally delete policy
        delete_policy("tanpol")

    def test_23_enroll_different_tokentypes_in_different_resolvers(self):
        # One realm has different resolvers.
        # The different users are allowed to enroll different tokentypes.
        realm = "myrealm"
        # We need this, to create the resolver3
        self.setUp_user_realm3()
        (added, failed) = create_realm(realm,
                                       [
                                           {'name': self.resolvername1},
                                           {'name': self.resolvername3}])
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
                   action=PolicyAction.APPLICATION_TOKENTYPE)
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
                   action="{0!s}={1!s}".format(PolicyAction.REGISTRATIONCODE_LENGTH, 6))
        set_policy(name="reg_contents",
                   scope=SCOPE.ENROLL,
                   action="{0!s}={1!s}".format(PolicyAction.REGISTRATIONCODE_CONTENTS, "+n"))
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
                   action="{0!s}={1!s}".format(PolicyAction.PASSWORD_LENGTH, 6))
        set_policy(name="pw_contents",
                   scope=SCOPE.ENROLL,
                   action="{0!s}={1!s}".format(PolicyAction.PASSWORD_CONTENTS, "+n"))
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
                   action=PolicyAction.INCREASE_FAILCOUNTER_ON_CHALLENGE)

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
                   action=["{0!s}=hotp".format(PolicyAction.REQUIRE_DESCRIPTION)])
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

    def test_61a_required_description_on_edit(self):
        self.setUp_user_realms()
        serial = "HOTP1"

        init_token({"serial": serial, "type": "hotp", "otpkey": "2", "user": "cornelius"})

        # Set policies
        set_policy(name="require_description_on_edit",
                   scope=SCOPE.TOKEN,
                   action=[f"{PolicyAction.REQUIRE_DESCRIPTION_ON_EDIT}=hotp"])

        set_policy(name="set_description",
                   scope=SCOPE.ADMIN,
                   action=PolicyAction.SETDESCRIPTION)

        with self.app.test_request_context('token/description/' + serial,
                                           method='POST',
                                           data={'description': 'test'},
                                           headers={'Authorization': self.at}):
            # This should work because the description is set
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)

        with self.app.test_request_context('token/description/' + serial,
                                           method='POST',
                                           data={'description': ""},
                                           headers={'Authorization': self.at}):
            # Description is empty, this should not work
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403)
            result = res.json.get("result")
            self.assertIn("Description required for hotp token.", result.get("error").get("message"))

        remove_token(serial=serial)
        delete_policy("require_description_on_edit")
        delete_policy("set_description")

    def test_01_sms_identifier(self):
        # every admin is allowed to enroll sms token with gw1 or gw2
        set_policy("sms1", scope=SCOPE.ADMIN, action="{0!s}=gw1 gw2".format(SMSAction.GATEWAYS))
        set_policy("sms2", scope=SCOPE.ADMIN, action="{0!s}=gw3".format(SMSAction.GATEWAYS))

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
        set_policy("sms1", scope=SCOPE.USER, action="{0!s}=gw4".format(SMSAction.GATEWAYS))

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
        from privacyidea.lib.tokens.pushtoken import PushAction
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
        g.policies = {}
        req = Request(env)
        req.User = User()
        req.all_data = {
            "type": "push"}
        # In this case we have no firebase config. We will raise an exception
        self.assertRaises(PolicyError, pushtoken_add_config, req, "init")
        # if we have a non existing firebase config, we will raise an exception
        req.all_data = {
            "type": "push",
            PushAction.FIREBASE_CONFIG: "non-existing"}
        self.assertRaises(PolicyError, pushtoken_add_config, req, "init")

        # Set a policy for the firebase config to use.
        set_policy(name="push_pol",
                   scope=SCOPE.ENROLL,
                   action="{0!s}=some-fb-config,"
                          "{1!s}=https://privacyidea.com/enroll,"
                          "{2!s}=10".format(PushAction.FIREBASE_CONFIG,
                                            PushAction.REGISTRATION_URL,
                                            PushAction.TTL))
        g.policy_object = PolicyClass()
        g.policies = {}
        req.all_data = {"type": "push"}
        pushtoken_add_config(req, "init")
        policies = g.policies
        self.assertEqual("some-fb-config", policies.get(PushAction.FIREBASE_CONFIG))
        self.assertEqual("https://privacyidea.com/enroll", policies.get(PushAction.REGISTRATION_URL))
        self.assertEqual("10", policies.get(PushAction.TTL))
        self.assertEqual("1", policies.get(PushAction.SSL_VERIFY))
        self.assertFalse(policies.get(PushAction.USE_PIA_SCHEME))

        # the request tries to inject a rogue value, but we assure sslverify=1
        g.policy_object = PolicyClass()
        g.policies = {}
        req.all_data = {
            "type": "push",
            "sslverify": "rogue"}
        pushtoken_add_config(req, "init")
        self.assertEqual("1", g.policies.get(PushAction.SSL_VERIFY))

        # set sslverify="0"
        set_policy(name="push_pol2",
                   scope=SCOPE.ENROLL,
                   action="{0!s}=0".format(PushAction.SSL_VERIFY))
        g.policy_object = PolicyClass()
        g.policies = {}
        req.all_data = {"type": "push"}
        pushtoken_add_config(req, "init")
        self.assertEqual("some-fb-config", g.policies.get(PushAction.FIREBASE_CONFIG))
        self.assertEqual("0", g.policies.get(PushAction.SSL_VERIFY))

        # Set policy to use pia scheme
        set_policy("pia_scheme", scope=SCOPE.ENROLL, action=PushAction.USE_PIA_SCHEME)
        req.all_data = {"type": "push"}
        g.policies = {}
        pushtoken_add_config(req, "init")
        self.assertTrue(g.policies.get(PushAction.USE_PIA_SCHEME))

        # finally delete policy
        delete_policy("push_pol")
        delete_policy("push_pol2")
        delete_policy("pia_scheme")

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
        pushtoken_validate(req, None)
        self.assertEqual(req.all_data.get(PushAction.WAIT), False)

        # Now we use the policy, to set the push_wait seconds
        set_policy(name="push1", scope=SCOPE.AUTH, action="{0!s}=10".format(PushAction.WAIT))
        req.all_data = {}
        g.policy_object = PolicyClass()
        pushtoken_validate(req, None)
        self.assertEqual(req.all_data.get(PushAction.WAIT), 10)

        delete_policy("push1")

    def test_24b_push_disable_wait_policy(self):
        # We send a fake push_wait that is not in the policies
        class RequestMock(object):
            pass

        req = RequestMock()
        req.all_data = {"push_wait": "120"}
        pushtoken_disable_wait(req, None)
        self.assertEqual(req.all_data.get(PushAction.WAIT), False)

        # But even with a policy, the function still sets PUSH_ACTION.WAIT to False
        set_policy(name="push1", scope=SCOPE.AUTH, action="{0!s}=10".format(PushAction.WAIT))
        req = RequestMock()
        req.all_data = {"push_wait": "120"}
        pushtoken_disable_wait(req, None)
        self.assertEqual(req.all_data.get(PushAction.WAIT), False)

        delete_policy("push1")
