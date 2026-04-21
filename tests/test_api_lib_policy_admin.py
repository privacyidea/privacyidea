# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for admin-scope prepolicies (privacyidea.api.lib.prepolicy)."""
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


class PrePolicyAdminTestCase(PrePolicyHelperMixin, MyApiTestCase):

    def setUp(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        self.setUp_user_realm3()

    def test_01_check_base_action(self):
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
        set_policy(name="pol1", scope=SCOPE.ADMIN, action=PolicyAction.ENABLE, client="10.0.0.0/8")
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
        set_policy(name="pol1", scope=SCOPE.ADMIN, action=PolicyAction.ENABLE, client="10.0.0.0/8",
                   realm=self.realm1)
        set_policy(name="pol2", scope=SCOPE.ADMIN, action="*", client="10.0.0.0/8", realm=self.realm2)
        g.policy_object = PolicyClass()
        # set a polrealm1 and a polrealm2
        init_token({"serial": "POL001", "type": "hotp", "otpkey": "1234567890123456"})
        set_realms("POL001", [self.realm1])

        init_token({"serial": "POL002", "type": "hotp", "otpkey": "1234567890123456"})
        set_realms("POL002", [self.realm2])

        # Token in realm1 can not be deleted
        req.all_data = {"serial": "POL001"}
        req.User = User()
        self.assertRaises(PolicyError, check_base_action, req, "delete")
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
                  "realm": "adminrealm"}

        admin2 = {"username": "admin1",
                  "role": "admin",
                  "realm": "realm2"}

        set_policy(name="pol",
                   scope=SCOPE.ADMIN,
                   action="*", adminrealm="adminrealm")
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
            "realm": "home"
        }

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
                   action=PolicyAction.APIKEY)
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
                   action="{0!s}=user/.*(.{{4}}$)/\\1/".format(PolicyAction.MANGLE))
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
                   action="{0!s}=realm/\\s//".format(PolicyAction.MANGLE))
        g.policy_object = PolicyClass()

        # request, that matches the policy
        req.all_data = {"realm": "lower Realm"}
        mangle(req)
        # Check if the realm was modified
        self.assertEqual(req.all_data.get("realm"), "lowerRealm")
        self.assertEqual(req.User, User("", "lowerrealm"))

        # do not mangle realm if set_realm policy is set
        req.all_data = {"realm": "lower Realm", "user": "Thiswillbesplit_user"}
        req.User = User("Thiswillbesplit_user", "lower Realm")
        g.policies = {PolicyAction.SET_REALM: "lower Realm"}
        mangle(req)
        # Check that realm was not modified, but username is modified
        self.assertEqual("lower Realm", req.all_data.get("realm"))
        self.assertEqual("user", req.all_data.get("user"))
        self.assertEqual(User("user", "lower realm"), req.User)

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
                   action="{0!s}={1!s}".format(PolicyAction.REMOTE_USER, REMOTE_USER.ACTIVE))

        r = is_remote_user_allowed(req)
        self.assertEqual(REMOTE_USER.ACTIVE, r)

        # Login for the REMOTE_USER is not allowed.
        # Only allowed for user "super", but REMOTE_USER=admin
        set_policy(name="ruser",
                   scope=SCOPE.WEBUI,
                   action="{0!s}={1!s}".format(PolicyAction.REMOTE_USER, REMOTE_USER.ACTIVE),
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
                   action="{0!s}={1!s}".format(PolicyAction.REMOTE_USER, REMOTE_USER.FORCE),
                   user="super")
        self.assertEqual(REMOTE_USER.FORCE, is_remote_user_allowed(req))

        set_privacyidea_config(SYSCONF.SPLITATSIGN, False)
        self.assertEqual(REMOTE_USER.DISABLE, is_remote_user_allowed(req))

        set_privacyidea_config(SYSCONF.SPLITATSIGN, True)
        delete_policy("ruser")

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
                        "realm": [self.realm3],
                        "resolver": [self.resolvername3],
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
                          "updateuser, enable, "
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
                   realm=f"{self.realm1}, {self.realm3}",
                   resolver=f"{self.resolvername1}, {self.resolvername3}",
                   )
        set_policy("polAdminB", scope=SCOPE.ADMIN,
                   action="set, revoke, adduser, resync, unassign, "
                          "tokenrealms, deleteuser, enrollTOTP, "
                          "enrollREGISTRATION, updateuser, enable, userlist, "
                          "getserial, disable, reset, getchallenges, losttoken,"
                          " assign, delete ",
                   realm=self.realm3,
                   resolver=self.resolvername3,
                   adminuser="adminB")
        g.policy_object = PolicyClass()
        # Test AdminA
        g.logged_in_user = {"username": "adminA",
                            "role": "admin",
                            "realm": ""}
        r = check_base_action(req, action=PolicyAction.POLICYWRITE)
        self.assertEqual(r, True)
        # Test AdminB
        g.logged_in_user = {"username": "adminB",
                            "role": "admin",
                            "realm": ""}
        # AdminB is allowed to add user
        r = check_base_action(req, action=PolicyAction.ADDUSER)
        self.assertEqual(r, True)
        # But admin b is not allowed to policywrite
        self.assertRaises(PolicyError, check_base_action, req,
                          action=PolicyAction.POLICYWRITE)
        # Test AdminC: is not allowed to do anything
        g.logged_in_user = {"username": "adminC",
                            "role": "admin",
                            "realm": ""}
        self.assertRaises(PolicyError, check_base_action, req,
                          action=PolicyAction.POLICYWRITE)
        delete_policy("polAdminA")
        delete_policy("polAdminB")

    def test_17_add_user(self):
        # Check if adding a user is restricted to the resolver
        # adminA is allowed to add users to resolverA but not to resolverB
        set_policy("userAdd", scope=SCOPE.ADMIN,
                   action="adduser",
                   adminuser="adminA",
                   realm=self.realm1,
                   resolver=self.resolvername1,
                   )
        builder = EnvironBuilder(method='POST')
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        req = Request(env)
        req.User = User()
        req.all_data = {"user": "new_user",
                        "resolver": self.resolvername1}
        g.policy_object = PolicyClass()
        g.logged_in_user = {"username": "adminA",
                            "role": "admin",
                            "realm": ""}
        # User can be added
        r = check_base_action(req, action=PolicyAction.ADDUSER)
        self.assertEqual(r, True)

        req.all_data = {"user": "new_user",
                        "resolver": self.resolvername3}

        # User can not be added in a different resolver
        self.assertRaises(PolicyError, check_base_action, req,
                          action=PolicyAction.ADDUSER)
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
                   action="{0!s}=1d".format(PolicyAction.AUDIT_AGE))
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
                   action="{0!s}=serial action".format(PolicyAction.HIDE_AUDIT_COLUMNS))
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
                   action="{0!s}=number realm".format(PolicyAction.HIDE_AUDIT_COLUMNS))
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
                   action="{0!s}=tokenkind unknown".format(PolicyAction.HIDE_TOKENINFO))
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
                   action="{0!s}=tokenkind unknown".format(PolicyAction.HIDE_TOKENINFO))
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
                   scope=SCOPE.ADMIN,
                   action="enrollHOTP")

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
        req.all_data = {}
        r = check_admin_tokenlist(req)
        self.assertTrue(r)
        # The admin1 has the policy "pol-realm1", so he is allowed to view all realms!
        self.assertEqual(req.pi_allowed_realms, [self.realm1])

        enable_policy("pol-realm1", False)
        # Now he only has the admin right to init tokens
        g.policy_object = PolicyClass()
        req = Request(env)
        req.all_data = {}
        r = check_admin_tokenlist(req)
        self.assertTrue(r)
        # The admin1 has the policy "pol-only-init", so he is not allowed to list tokens
        self.assertEqual(req.pi_allowed_realms, [])

        for pol in ["pol-realm1", "pol-all-realms", "pol-only-init"]:
            delete_policy(pol)

    def test_62_jwt_validity(self):
        user = User("cornelius", realm=self.realm1, resolver=self.resolvername1)

        # Default validity.
        validity = get_jwt_validity(user)
        self.assertEqual(timedelta(hours=1), validity)

        # Set policy
        set_policy(name="jwt_validity", scope=SCOPE.WEBUI, action=[f"{PolicyAction.JWTVALIDITY}=12"], realm=self.realm1)

        # The validity of the JWT is set.
        validity = get_jwt_validity(user)
        self.assertEqual(timedelta(seconds=12), validity)

        # Passing an empty user returns the default validity.
        validity = get_jwt_validity(User())
        self.assertEqual(timedelta(hours=1), validity)

        # Now test a bogus policy
        set_policy(name="jwt_validity", scope=SCOPE.WEBUI, action=[f"{PolicyAction.JWTVALIDITY}=oneMinute"])
        validity = get_jwt_validity(user)
        self.assertEqual(timedelta(hours=1), validity)

        delete_policy("jwt_validity")
