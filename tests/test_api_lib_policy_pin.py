# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for PIN-related prepolicies (privacyidea.api.lib.prepolicy)."""
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
                                   get_one_token)
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
from privacyidea.lib.users.internal_user_attributes import InternalUserAttributes
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


class PrePolicyPinTestCase(PrePolicyHelperMixin, MyApiTestCase):

    def setUp(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        self.setUp_user_realm3()

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
                   action=PolicyAction.ENCRYPTPIN)
        g.policy_object = PolicyClass()

        # request, that matches the policy
        req.all_data = {
            "user": "cornelius",
            "realm": "home"
        }
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

        # Trying to enroll a token with a pin but without enrollpin right will result in a policy error.
        # checked by enroll_pin
        req.all_data = {"pin": "test",
                        "user": "cornelius",
                        "realm": self.realm1}

        with self.assertRaises(PolicyError):
            enroll_pin(req)

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
        create_realm("home", [{'name': self.resolvername1}])
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
                   action="{0!s}={1!s},{2!s}={3!s},{4!s}={5!s}".format(PolicyAction.OTPPINMAXLEN, "10",
                                                                       PolicyAction.OTPPINMINLEN, "4",
                                                                       PolicyAction.OTPPINCONTENTS, "cn"))
        g.policy_object = PolicyClass()

        req.all_data = {
            "user": "cornelius",
            "realm": "home"
        }
        req.User = User("cornelius", "home")
        # The minimum OTP length is 4
        self.assertRaises(PolicyError, check_otp_pin, req)

        req.all_data = {
            "user": "cornelius",
            "realm": "home",
            "pin": "12345566890012"
        }
        # Fail maximum OTP length
        self.assertRaises(PolicyError, check_otp_pin, req)

        req.all_data = {
            "user": "cornelius",
            "realm": "home",
            "pin": "123456"
        }
        # Good OTP length, but missing character A-Z
        self.assertRaises(PolicyError, check_otp_pin, req)

        req.all_data = {
            "user": "cornelius",
            "realm": "home",
            "pin": "abc123"
        }
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

        # The same types are exempt at /token/init, where no serial exists yet and only the
        # requested type is known.
        for token_type in ["certificate", "sshkey"]:
            req.all_data = {"type": token_type,
                            "realm": "home",
                            "user": "cornelius"}
            self.assertTrue(check_otp_pin(req))

        # The exemption only covers the absent PIN. The certificate token encrypts the PKCS#12
        # container with the PIN, so a PIN that is sent has to satisfy the policies.
        req.all_data = {"type": "certificate",
                        "realm": "home",
                        "user": "cornelius",
                        "pin": "1"}
        self.assertRaises(PolicyError, check_otp_pin, req)
        req.all_data = {"type": "certificate",
                        "realm": "home",
                        "user": "cornelius",
                        "pin": "abc123"}
        self.assertTrue(check_otp_pin(req))

        # A type that does use a PIN is still checked, and so is a type we do not know.
        for token_type in ["hotp", "an-unknown-type"]:
            req.all_data = {"type": token_type,
                            "realm": "home",
                            "user": "cornelius"}
            self.assertRaises(PolicyError, check_otp_pin, req)

        # check that no pin is checked during rollover or verify, as long as no PIN is given
        logging.getLogger('privacyidea').setLevel(logging.DEBUG)
        req.all_data = {
            "user": "cornelius",
            "realm": "home",
            "rollover": True
        }
        self.assertTrue(check_otp_pin(req))
        capture.check_present(("privacyidea.api.lib.prepolicy", "DEBUG",
                               "No PIN given for the rollover (True) or verification (None), skipping the PIN "
                               "policies."))
        req.all_data = {
            "user": "cornelius",
            "realm": "home",
            "verify": 123456
        }
        self.assertTrue(check_otp_pin(req))
        capture.check_present(("privacyidea.api.lib.prepolicy", "DEBUG",
                               "No PIN given for the rollover (None) or verification (123456), skipping the PIN "
                               "policies."))
        logging.getLogger('privacyidea').setLevel(logging.INFO)
        # A PIN that is given with the rollover or the verification is checked
        for flag in ({"rollover": True}, {"verify": 123456}):
            req.all_data = {"user": "cornelius", "realm": "home", "pin": "1", **flag}
            self.assertRaises(PolicyError, check_otp_pin, req)

        # finally delete policy
        delete_policy("pol1")
        delete_realm("home")

    @log_capture(level=logging.DEBUG)
    def test_09_pin_policies_admin(self, capture):
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

        # Set a policy that defines PIN policy
        set_policy(name="pol1",
                   scope=SCOPE.ADMIN,
                   action="{0!s}={1!s},{2!s}={3!s},{4!s}={5!s}".format(PolicyAction.OTPPINMAXLEN, "10",
                                                                       PolicyAction.OTPPINMINLEN, "4",
                                                                       PolicyAction.OTPPINCONTENTS, "cn"),
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
            "pin": "abc123"
        }
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

        # The same types are exempt at /token/init, where no serial exists yet and only the
        # requested type is known.
        for token_type in ["certificate", "sshkey"]:
            req.all_data = {"type": token_type,
                            "realm": "home",
                            "user": "cornelius"}
            self.assertTrue(check_otp_pin(req))

        # The exemption only covers the absent PIN. The certificate token encrypts the PKCS#12
        # container with the PIN, so a PIN that is sent has to satisfy the policies.
        req.all_data = {"type": "certificate",
                        "realm": "home",
                        "user": "cornelius",
                        "pin": "1"}
        self.assertRaises(PolicyError, check_otp_pin, req)
        req.all_data = {"type": "certificate",
                        "realm": "home",
                        "user": "cornelius",
                        "pin": "abc123"}
        self.assertTrue(check_otp_pin(req))

        # A type that does use a PIN is still checked, and so is a type we do not know.
        for token_type in ["hotp", "an-unknown-type"]:
            req.all_data = {"type": token_type,
                            "realm": "home",
                            "user": "cornelius"}
            self.assertRaises(PolicyError, check_otp_pin, req)

        # check that no pin is checked during rollover or verify, as long as no PIN is given
        logging.getLogger('privacyidea').setLevel(logging.DEBUG)
        req.all_data = {
            "user": "cornelius",
            "realm": "home",
            "rollover": True
        }
        self.assertTrue(check_otp_pin(req))
        capture.check_present(("privacyidea.api.lib.prepolicy", "DEBUG",
                               "No PIN given for the rollover (True) or verification (None), skipping the PIN "
                               "policies."))
        req.all_data = {
            "user": "cornelius",
            "realm": "home",
            "verify": 123456
        }
        self.assertTrue(check_otp_pin(req))
        capture.check_present(("privacyidea.api.lib.prepolicy", "DEBUG",
                               "No PIN given for the rollover (None) or verification (123456), skipping the PIN "
                               "policies."))
        logging.getLogger('privacyidea').setLevel(logging.INFO)
        # A PIN that is given with the rollover or the verification is checked
        for flag in ({"rollover": True}, {"verify": 123456}):
            req.all_data = {"user": "cornelius", "realm": "home", "pin": "1", **flag}
            self.assertRaises(PolicyError, check_otp_pin, req)

        # finally delete policy
        delete_policy("pol1")
        delete_realm("home")

    def test_09b_pin_policies_admin_by_serial(self):
        # An admin acting on an existing token by serial without a user parameter must still have
        # the realm-scoped PIN policy of the token owner enforced. The owner is derived from the
        # serial, so the empty request.User does not silently skip the realm-scoped policy.
        create_realm("home", [{'name': self.resolvername1}])
        g.logged_in_user = {"username": "super",
                            "realm": "",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST', headers={})
        env = builder.get_environ()
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)

        # A token owned by cornelius in realm "home"
        init_token({"type": "hotp", "serial": "PINBYSERIAL"}, user=User("cornelius", "home"))

        # Realm-scoped admin PIN policy that requires a complex PIN
        set_policy(name="pol1",
                   scope=SCOPE.ADMIN,
                   action="{0!s}={1!s},{2!s}={3!s}".format(PolicyAction.OTPPINMINLEN, "4",
                                                           PolicyAction.OTPPINCONTENTS, "cn"),
                   realm="home")
        g.policy_object = PolicyClass()

        # Admin sends only the serial and a weak PIN, with no user parameter -> empty request.User
        req.all_data = {"serial": "PINBYSERIAL", "pin": "12"}
        req.User = User()
        # The realm-scoped policy is matched against the token owner -> weak PIN is rejected
        self.assertRaises(PolicyError, check_otp_pin, req)

        # A PIN that complies with the owner's realm policy is accepted
        req.all_data = {"serial": "PINBYSERIAL", "pin": "abc123"}
        req.User = User()
        self.assertTrue(check_otp_pin(req))

        # An explicitly supplied user is honored over the token owner: naming a
        # user in a realm without a strict PIN policy uses that user's policies,
        # so the weak PIN is accepted. The owner's home-realm policy is only used
        # as a fallback when no user is supplied (empty request.User).
        req.all_data = {"serial": "PINBYSERIAL", "pin": "12",
                        "user": "cornelius", "realm": self.realm1}
        req.User = User("cornelius", self.realm1)
        self.assertTrue(check_otp_pin(req))

        delete_policy("pol1")
        remove_token("PINBYSERIAL")
        delete_realm("home")

    def test_09c_random_pin_contents_uses_param_user(self):
        # init_random_pin must resolve the OTPPINCONTENTS policy with the same
        # user as the OTPPINRANDOM lookup (the enrollment user from the request
        # params), not request.User. When request.User is empty but the params
        # carry the user (e.g. a realm injected by realmadmin), the user-scoped
        # contents policy must still apply to the generated PIN.
        create_realm("home", [{'name': self.resolvername1}])
        g.logged_in_user = {"username": "super",
                            "realm": "",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST', headers={})
        env = builder.get_environ()
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)

        # Enrollment generates a random PIN of length 12 (SCOPE.ENROLL) whose
        # contents must include a special character (OTPPINCONTENTS "s",
        # SCOPE.ADMIN, realm-scoped). "s" is a deterministic discriminator: the
        # fallback generate_password() charset is alphanumeric only, so a special
        # character can only appear when the contents policy was actually applied.
        set_policy(name="pol_rand", scope=SCOPE.ENROLL,
                   action="{0!s}={1!s}".format(PolicyAction.OTPPINRANDOM, "12"),
                   realm="home")
        set_policy(name="pol_contents", scope=SCOPE.ADMIN,
                   action="{0!s}={1!s}".format(PolicyAction.OTPPINCONTENTS, "s"),
                   realm="home")
        g.policy_object = PolicyClass()

        # Admin enrolls for cornelius@home: the user is in the params, but
        # request.User is empty.
        req.all_data = {"type": "hotp", "user": "cornelius", "realm": "home"}
        req.User = User()
        self.assertTrue(init_random_pin(req))

        # The realm-scoped contents policy was resolved via the param user (not
        # the empty request.User), so the generated PIN has the configured length
        # and contains a special character.
        pin = req.all_data["pin"]
        self.assertEqual(12, len(pin), pin)
        self.assertTrue(any(not c.isalnum() for c in pin), pin)

        delete_policy("pol_rand")
        delete_policy("pol_contents")
        delete_realm("home")

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


class PinPolicyEndpointTestCase(MyApiTestCase):
    """The PIN policies apply to the PIN an endpoint stores, whatever else the request contains."""

    def setUp(self) -> None:
        super().setUp()
        self.setUp_user_realms()
        self.addCleanup(self._remove_policies_and_tokens)

    @staticmethod
    def _remove_policies_and_tokens() -> None:
        for policy in PolicyClass().list_policies():
            delete_policy(policy["name"])
        for token in get_tokens():
            remove_token(token.token.serial)

    def _post(self, url: str, data: dict | None = None, authorization: str | None = None,
              json_body: dict | None = None) -> tuple[int, dict]:
        self.reset_flask_g()
        arguments = {"method": "POST", "headers": {"Authorization": authorization} if authorization else {}}
        if json_body is not None:
            arguments["json"] = json_body
        else:
            arguments["data"] = data or {}
        with self.app.test_request_context(url, **arguments):
            response = self.app.full_dispatch_request()
            return response.status_code, response.json

    def _user_authorization(self) -> str:
        self.authenticate_selfservice_user()
        return self.at_user

    def test_01_a_pin_given_with_rollover_or_verify_is_checked(self):
        set_policy("user", scope=SCOPE.USER, action="enrollHOTP, enrollpin, otp_pin_minlength=8", realm=self.realm1)
        authorization = self._user_authorization()

        status, result = self._post("/token/init", {"type": "hotp", "genkey": 1, "pin": "12", "serial": "ROLL1",
                                                    "rollover": "1"}, authorization)
        self.assertEqual(403, status, result)
        status, result = self._post("/token/init", {"type": "hotp", "otpkey": self.otpkey, "pin": "12",
                                                    "serial": "VERIFY1", "verify": "123456"}, authorization)
        self.assertEqual(403, status, result)
        # Without a PIN the rollover is not checked against the PIN policies
        status, result = self._post("/token/init", {"type": "hotp", "genkey": 1, "serial": "ROLL2",
                                                    "rollover": "1"}, authorization)
        self.assertEqual(200, status, result)

    def test_02_the_pin_the_endpoint_stores_is_checked(self):
        set_policy("user", scope=SCOPE.USER, action="enrollHOTP, enrollpin, setpin, otp_pin_minlength=8",
                   realm=self.realm1)
        set_policy("admin", scope=SCOPE.ADMIN, action="enrollHOTP, assign, otp_pin_minlength=8")
        authorization = self._user_authorization()

        # /token/init and /token/assign store "pin"
        status, result = self._post("/token/init", {"type": "hotp", "genkey": 1, "serial": "INIT1", "pin": "12",
                                                    "otppin": "Compliant123"}, authorization)
        self.assertEqual(403, status, result)
        init_token({"type": "hotp", "serial": "ASSIGN1", "otpkey": self.otpkey})
        status, result = self._post("/token/assign", {"serial": "ASSIGN1", "user": "cornelius", "realm": self.realm1,
                                                      "pin": "1", "otppin": "Compliant123"}, self.at)
        self.assertEqual(403, status, result)

        # /token/setpin stores "otppin", an empty one included
        init_token({"type": "hotp", "serial": "SETPIN1", "otpkey": self.otpkey, "pin": "oldpin123"},
                   user=User("selfservice", self.realm1))
        status, result = self._post("/token/setpin", {"serial": "SETPIN1", "otppin": "", "pin": "Whatever123"},
                                    authorization)
        self.assertEqual(403, status, result)
        self.assertTrue(get_one_token(serial="SETPIN1").token.check_pin("oldpin123"))
        status, result = self._post("/token/setpin", {"serial": "SETPIN1", "otppin": "Compliant123"},
                                    authorization)
        self.assertEqual(200, status, result)
        self.assertTrue(get_one_token(serial="SETPIN1").token.check_pin("Compliant123"))

    def test_03_the_type_specific_policy_applies_to_any_spelling_of_the_type(self):
        set_policy("user", scope=SCOPE.USER, action="enrollSPASS, enrollpin, spass_otp_pin_minlength=12",
                   realm=self.realm1)
        authorization = self._user_authorization()

        for token_type in ("spass", "SPASS", "Spass"):
            status, result = self._post("/token/init", {"type": token_type, "pin": "abc", "serial": "SPASS1"},
                                        authorization)
            self.assertEqual(403, status, (token_type, result))
        status, result = self._post("/token/init", {"type": "SPASS", "pin": "abcdefghijkl", "serial": "SPASS1"},
                                    authorization)
        self.assertEqual(200, status, result)

    def test_04_otppin_none_keeps_checking_the_pin_of_a_spass_token(self):
        init_token({"type": "spass", "serial": "SPASSNONE", "pin": "secret"}, user=User("cornelius", self.realm1))
        set_policy("none", scope=SCOPE.AUTH, action=f"{PolicyAction.OTPPIN}=none", realm=self.realm1)

        status, result = self._post("/validate/check", {"user": "cornelius", "realm": self.realm1, "pass": ""})
        self.assertEqual(200, status, result)
        self.assertFalse(result["result"]["value"], result)
        status, result = self._post("/validate/check", {"user": "cornelius", "realm": self.realm1, "pass": "secret"})
        self.assertTrue(result["result"]["value"], result)

    def test_05_a_container_template_returns_the_pin_of_the_template_but_not_a_generated_one(self):
        def init_container_from_template(template_token: dict) -> tuple[str, dict]:
            body = {"type": "generic", "user": "cornelius", "realm": self.realm1,
                    "template": {"name": "template1", "container_type": "generic",
                                 "template_options": {"tokens": [template_token]}}}
            status, result = self._post("/container/init", json_body=body, authorization=self.at)
            self.assertEqual(200, status, result)
            serial, token_result = next(iter(result["result"]["value"]["tokens"].items()))
            return serial, token_result["init_params"]

        set_policy("random_pin", scope=SCOPE.ENROLL, action=f"{PolicyAction.OTPPINRANDOM}=10")
        serial, init_params = init_container_from_template({"type": "hotp", "genkey": True, "user": True})
        self.assertNotIn("pin", init_params)
        self.assertTrue(get_one_token(serial=serial).token.pin_hash)

        delete_policy("random_pin")
        _serial, init_params = init_container_from_template({"type": "hotp", "genkey": True, "user": True,
                                                             "pin": "templatepin"})
        self.assertEqual("templatepin", init_params["pin"])
