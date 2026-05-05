# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for generic prepolicy actions (privacyidea.api.lib.prepolicy)."""
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


class PrePolicyActionsTestCase(PrePolicyHelperMixin, MyApiTestCase):

    def setUp(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        self.setUp_user_realm3()

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
                   action=r"{0!s}=/.*@mydomain\..*".format(PolicyAction.REQUIREDEMAIL))
        g.policy_object = PolicyClass()
        # request, that matches the policy
        req.all_data = {"email": "user@mydomain.net"}
        # This email is allowed
        r = required_email(req)
        self.assertTrue(r)

        # This email is not allowed
        req.all_data = {"email": "user@otherdomain.net"}
        # This email is allowed
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
                   action="{0!s}".format(PolicyAction.RESYNC))
        g.policy_object = PolicyClass()
        req.all_data = {"user": "cornelius", "realm": self.realm1}
        # There is a user policy without password reset, so an exception is
        # raised
        self.assertRaises(PolicyError, check_anonymous_user, req,
                          PolicyAction.PASSWORDRESET)

        # The password reset is allowed
        set_policy(name="recover",
                   scope=SCOPE.USER,
                   action="{0!s}".format(PolicyAction.PASSWORDRESET))
        g.policy_object = PolicyClass()
        r = check_anonymous_user(req, PolicyAction.PASSWORDRESET)
        self.assertEqual(r, True)

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
                   action="{0!s}=department sth".format(PolicyAction.DELETE_USER_ATTRIBUTES))
        req.all_data = {"user": "cornelius", "realm": self.realm1, "attrkey": "department"}
        check_custom_user_attributes(req, "delete")

        # Now try to delete a different key
        req.all_data = {"user": "cornelius", "realm": self.realm1, "attrkey": "difkey"}
        self.assertRaises(PolicyError, check_custom_user_attributes, req, "delete")

        # Allow to delete diffkey
        set_policy("set_custom_attr2", scope=SCOPE.ADMIN,
                   action="{0!s}=difkey".format(PolicyAction.DELETE_USER_ATTRIBUTES))
        req.all_data = {"user": "cornelius", "realm": self.realm1, "attrkey": "difkey"}
        check_custom_user_attributes(req, "delete")

        # Now we set the policy to allow to delete any attribute
        set_policy("set_custom_attr2", scope=SCOPE.ADMIN,
                   action="{0!s}=*".format(PolicyAction.DELETE_USER_ATTRIBUTES))
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
                   action="{0!s}=:department: finance devel :color: * :*: 1 2 ".format(
                       PolicyAction.SET_USER_ATTRIBUTES))
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
                   action="{0!s}=:*: *".format(PolicyAction.SET_USER_ATTRIBUTES))
        req.all_data = {"user": "cornelius", "realm": self.realm1,
                        "key": "size", "value": "3"}
        check_custom_user_attributes(req, "set")

    def test_63_check_token_action_user_success(self):
        # Mock request object
        self.setUp_user_realms()
        self.setUp_user_realm3()
        req, token = self.mock_token_request("user")

        # Generic policy
        set_policy(name="policy", scope=SCOPE.USER, action="enable")
        self.assertTrue(check_token_action(request=req, action="enable"))
        delete_policy("policy")

        # Policy for resolver
        set_policy(name="policy", scope=SCOPE.USER, action="enable", resolver=[self.resolvername3])
        self.assertTrue(check_token_action(request=req, action="enable"))
        delete_policy("policy")

        # Policy for realm
        set_policy(name="policy", scope=SCOPE.USER, action="enable", realm=[self.realm3])
        self.assertTrue(check_token_action(request=req, action="enable"))
        delete_policy("policy")

        # Policy for user
        set_policy(name="policy", scope=SCOPE.USER, action="enable", user="root", realm=[self.realm3],
                   resolver=[self.resolvername3])
        self.assertTrue(check_token_action(request=req, action="enable"))
        delete_policy("policy")

        token.delete_token()

    def test_64_check_token_action_user_denied(self):
        # Mock request object
        self.setUp_user_realms()
        self.setUp_user_realm3()
        req, token = self.mock_token_request("user")

        # No enable policy
        set_policy(name="policy", scope=SCOPE.USER, action="disable")
        self.assertRaises(PolicyError, check_token_action, request=req, action="enable")
        delete_policy("policy")

        # Policy for another resolver
        set_policy(name="policy", scope=SCOPE.USER, action="enable", resolver=[self.resolvername1])
        self.assertRaises(PolicyError, check_token_action, request=req, action="enable")
        delete_policy("policy")

        # Policy for another realm
        # the token is in this realm, but it is not the realm of the user
        set_policy(name="policy", scope=SCOPE.USER, action="enable", realm=[self.realm1])
        self.assertRaises(PolicyError, check_token_action, request=req, action="enable")
        delete_policy("policy")

        # Policy for another user
        set_policy(name="policy", scope=SCOPE.USER, action="enable", user="hans", realm=[self.realm3],
                   resolver=[self.resolvername3])
        self.assertRaises(PolicyError, check_token_action, request=req, action="enable")
        delete_policy("policy")

        token.delete_token()

    def test_65_check_token_action_admin_success(self):
        self.setUp_user_realms()
        self.setUp_user_realm3()
        req, token = self.mock_token_request("admin")

        # Generic policy
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ADD_TOKEN)
        self.assertTrue(check_token_action(request=req, action=PolicyAction.CONTAINER_ADD_TOKEN))
        # Request user is different from token owner: use token owner (can only happen in add/remove token)
        req.User = User("selfservice", self.realm1, self.resolvername1)
        self.assertTrue(check_token_action(request=req, action=PolicyAction.CONTAINER_ADD_TOKEN))
        delete_policy("policy")

        # Policy for resolver
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ADD_TOKEN,
                   resolver=[self.resolvername3])
        self.assertTrue(check_token_action(request=req, action=PolicyAction.CONTAINER_ADD_TOKEN))
        # Request user is different from token owner: use token owner (can only happen in add/remove token)
        req.User = User("selfservice", self.realm1, self.resolvername1)
        self.assertTrue(check_token_action(request=req, action=PolicyAction.CONTAINER_ADD_TOKEN))
        delete_policy("policy")

        # Policy for realm3 of the user
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ADD_TOKEN, realm=[self.realm3])
        self.assertTrue(check_token_action(request=req, action=PolicyAction.CONTAINER_ADD_TOKEN))
        # Request user is different from token owner: use token owner (can only happen in add/remove token)
        req.User = User("selfservice", self.realm1, self.resolvername1)
        self.assertTrue(check_token_action(request=req, action=PolicyAction.CONTAINER_ADD_TOKEN))
        delete_policy("policy")

        # Policy for additional token realm realm1
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ADD_TOKEN, realm=[self.realm1])
        self.assertTrue(check_token_action(request=req, action=PolicyAction.CONTAINER_ADD_TOKEN))
        # Request user is different from token owner: use token owner (can only happen in add/remove token)
        req.User = User("selfservice", self.realm1, self.resolvername1)
        self.assertTrue(check_token_action(request=req, action=PolicyAction.CONTAINER_ADD_TOKEN))
        delete_policy("policy")

        # Policy for user
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ADD_TOKEN, user="root",
                   realm=[self.realm3], resolver=[self.resolvername3])
        self.assertTrue(check_token_action(request=req, action=PolicyAction.CONTAINER_ADD_TOKEN))
        # Request user is different from token owner: use token owner (can only happen in add/remove token)
        req.User = User("selfservice", self.realm1, self.resolvername1)
        self.assertTrue(check_token_action(request=req, action=PolicyAction.CONTAINER_ADD_TOKEN))
        delete_policy("policy")

        token.delete_token()

        # Token without user
        req, token = self.mock_token_request_no_user("admin")

        # Generic policy
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.ENABLE)
        self.assertTrue(check_token_action(request=req, action=PolicyAction.ENABLE))
        delete_policy("policy")

        # Policy for realm: only assign is allowed for token without user
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.ASSIGN, realm=[self.realm1])
        self.assertTrue(check_token_action(request=req, action=PolicyAction.ASSIGN))
        delete_policy("policy")

        token.delete_token()

    def test_66_check_token_action_admin_denied(self):
        self.setUp_user_realms()
        self.setUp_user_realm3()
        req, token = self.mock_token_request("admin")

        # No enable policy
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.DISABLE)
        self.assertRaises(PolicyError, check_token_action, request=req, action=PolicyAction.ENABLE)
        delete_policy("policy")

        # Policy for another resolver
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ADD_TOKEN,
                   resolver=[self.resolvername1])
        self.assertRaises(PolicyError, check_token_action, request=req, action=PolicyAction.CONTAINER_ADD_TOKEN)
        # Request user would be allowed, but token owner not (can only happen in add/remove token)
        req.User = User("selfservice", self.realm1, self.resolvername1)
        self.assertRaises(PolicyError, check_token_action, request=req, action=PolicyAction.CONTAINER_ADD_TOKEN)
        delete_policy("policy")

        # Policy for another realm
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.ENABLE, realm=["realm2"])
        self.assertRaises(PolicyError, check_token_action, request=req, action=PolicyAction.ENABLE)
        delete_policy("policy")
        # Assign not allowed if token is in another realm
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.ASSIGN, realm=["realm2"])
        self.assertRaises(PolicyError, check_token_action, request=req, action=PolicyAction.ASSIGN)
        delete_policy("policy")

        # Policy for another user
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.ENABLE, user="hans", realm=[self.realm3],
                   resolver=[self.resolvername3])
        self.assertRaises(PolicyError, check_token_action, request=req, action=PolicyAction.ENABLE)
        delete_policy("policy")

        token.delete_token()

        # Token without user and realm
        req, token = self.mock_token_request_no_user("admin")

        # Policy for resolver
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.ENABLE, resolver=[self.resolvername3])
        self.assertRaises(PolicyError, check_token_action, request=req, action=PolicyAction.ENABLE)
        delete_policy("policy")

        # Policy for realm
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.ENABLE, realm=[self.realm1])
        self.assertRaises(PolicyError, check_token_action, request=req, action=PolicyAction.ENABLE)
        delete_policy("policy")

        # Policy for user
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.ENABLE, user="root", realm=[self.realm3],
                   resolver=[self.resolvername3])
        self.assertRaises(PolicyError, check_token_action, request=req, action=PolicyAction.ENABLE)
        delete_policy("policy")

        token.delete_token()

    def test_71_check_token_list_action_admin(self):
        # Mock request object
        self.setUp_user_realms()
        self.setUp_user_realm2()
        self.setUp_user_realm3()
        req, token = self.mock_token_request("admin")
        req.User = User()

        # create token with another user from another realm and resolver and token without a user
        token_another_realm = init_token({"type": "hotp", "genkey": True}, user=User("hans", self.realm2))
        token_no_user = init_token({"type": "hotp", "genkey": True})
        serial_list = [token_no_user.get_serial(), token.get_serial(), token_another_realm.get_serial()]
        req.all_data["serials"] = serial_list

        # Generic policy
        set_policy(name="policy", scope=SCOPE.ADMIN, action="enable")
        self.assertTrue(check_token_action(request=req, action="enable"))
        for s in serial_list:
            self.assertIn(s, req.all_data["serials"])
        self.assertListEqual([], req.all_data["not_authorized_serials"])
        delete_policy("policy")

        # Policy for resolver
        req.all_data["serials"] = serial_list
        del req.all_data["not_authorized_serials"]
        set_policy(name="policy", scope=SCOPE.ADMIN, action="enable", resolver=[self.resolvername3])
        self.assertTrue(check_token_action(request=req, action="enable"))
        self.assertEqual([token.get_serial()], req.all_data["serials"])
        unauthorized = req.all_data["not_authorized_serials"]
        self.assertIn(token_no_user.get_serial(), unauthorized)
        self.assertIn(token_another_realm.get_serial(), unauthorized)
        delete_policy("policy")

        # Policy for realm
        req.all_data["serials"] = serial_list
        del req.all_data["not_authorized_serials"]
        set_policy(name="policy", scope=SCOPE.ADMIN, action="enable", realm=[self.realm3])
        self.assertTrue(check_token_action(request=req, action="enable"))
        self.assertEqual([token.get_serial()], req.all_data["serials"])
        unauthorized = req.all_data["not_authorized_serials"]
        self.assertIn(token_no_user.get_serial(), unauthorized)
        self.assertIn(token_another_realm.get_serial(), unauthorized)
        delete_policy("policy")

        # Policy for user
        req.all_data["serials"] = serial_list
        del req.all_data["not_authorized_serials"]
        set_policy(name="policy", scope=SCOPE.ADMIN, action="enable", user="root", realm=[self.realm3],
                   resolver=[self.resolvername3])
        self.assertTrue(check_token_action(request=req, action="enable"))
        self.assertEqual([token.get_serial()], req.all_data["serials"])
        unauthorized = req.all_data["not_authorized_serials"]
        self.assertIn(token_no_user.get_serial(), unauthorized)
        self.assertIn(token_another_realm.get_serial(), unauthorized)
        delete_policy("policy")

        token.delete_token()
        token_another_realm.delete_token()
        token_no_user.delete_token()

    def test_72_check_user_params_user_success(self):
        set_policy(name="policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_ASSIGN_USER)
        # Mock request object
        self.setUp_user_realm4_with_2_resolvers()
        req = self.mock_request_user_params("user")

        # User params are equal to logged-in user
        self.assertTrue(check_user_params(request=req, action=PolicyAction.CONTAINER_ASSIGN_USER))

        # Empty user params
        req.all_data = {}
        self.assertTrue(check_user_params(request=req, action=PolicyAction.CONTAINER_ASSIGN_USER))

        delete_policy("policy")

    def test_73_check_user_params_user_denied(self):
        # Mock request object
        self.setUp_user_realm2()
        self.setUp_user_realm4_with_2_resolvers()
        req = self.mock_request_user_params("user")

        # Different realm
        req.all_data = {'user': 'cornelius', 'realm': self.realm2}
        self.assertRaises(PolicyError, check_user_params, request=req, action=PolicyAction.CONTAINER_ASSIGN_USER)

        # Different user
        req.all_data = {'user': 'selfservice', 'realm': self.realm4}
        self.assertRaises(PolicyError, check_user_params, request=req, action=PolicyAction.CONTAINER_ASSIGN_USER)

        # Different resolver
        req.all_data = {'user': 'cornelius', 'realm': self.realm4, 'resolver': self.resolvername3}
        self.assertRaises(PolicyError, check_user_params, request=req, action=PolicyAction.CONTAINER_ASSIGN_USER)

        # completely different user
        req.all_data = {'user': 'hans', 'realm': self.realm2}
        self.assertRaises(PolicyError, check_user_params, request=req, action=PolicyAction.CONTAINER_ASSIGN_USER)

    def test_74_check_user_params_admin_success(self):
        # Mock request object
        self.setUp_user_realm4_with_2_resolvers()
        req = self.mock_request_user_params("admin")

        # Generic policy
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ASSIGN_USER)
        self.assertTrue(check_user_params(request=req, action=PolicyAction.CONTAINER_ASSIGN_USER))
        delete_policy("policy")

        # Policy for the realm
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ASSIGN_USER, realm=self.realm4)
        self.assertTrue(check_user_params(request=req, action=PolicyAction.CONTAINER_ASSIGN_USER))
        delete_policy("policy")

        # Policy for the resolver
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ASSIGN_USER,
                   resolver=self.resolvername1)
        self.assertTrue(check_user_params(request=req, action=PolicyAction.CONTAINER_ASSIGN_USER))
        delete_policy("policy")

        # Policy for the user
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ASSIGN_USER, user="cornelius",
                   realm=self.realm4, resolver=self.resolvername1)
        self.assertTrue(check_user_params(request=req, action=PolicyAction.CONTAINER_ASSIGN_USER))
        delete_policy("policy")

        # Empty user params
        req.all_data = {}
        req.User = User()
        self.assertTrue(check_user_params(request=req, action=PolicyAction.CONTAINER_ASSIGN_USER))

    def test_75_check_user_params_user_denied(self):
        # Mock request object
        self.setUp_user_realm2()
        self.setUp_user_realm4_with_2_resolvers()
        req = self.mock_request_user_params("user")
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ASSIGN_USER, user="cornelius",
                   realm=self.realm4, resolver=self.resolvername1)

        # Different realm
        req.all_data = {'user': 'cornelius', 'realm': self.realm2}
        self.assertRaises(PolicyError, check_user_params, request=req, action=PolicyAction.CONTAINER_ASSIGN_USER)

        # Different user
        req.all_data = {'user': 'selfservice', 'realm': self.realm4}
        self.assertRaises(PolicyError, check_user_params, request=req, action=PolicyAction.CONTAINER_ASSIGN_USER)

        # Different resolver
        req.all_data = {'user': 'cornelius', 'realm': self.realm4, 'resolver': self.resolvername3}
        self.assertRaises(PolicyError, check_user_params, request=req, action=PolicyAction.CONTAINER_ASSIGN_USER)

        # completely different user
        req.all_data = {'user': 'hans', 'realm': self.realm2}
        self.assertRaises(PolicyError, check_user_params, request=req, action=PolicyAction.CONTAINER_ASSIGN_USER)

        delete_policy("policy")
