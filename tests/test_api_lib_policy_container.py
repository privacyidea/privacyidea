# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for container-scope prepolicies (privacyidea.api.lib.prepolicy)."""
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


class PrePolicyContainerTestCase(PrePolicyHelperMixin, MyApiTestCase):

    def setUp(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        self.setUp_user_realm3()

    def test_67_check_container_action_user_success(self):
        # Mock request object
        self.setUp_user_realms()
        self.setUp_user_realm3()

        # User is the container owner
        req, container = self.mock_container_request("user")

        # Generic policy
        set_policy(name="policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_DESCRIPTION)
        self.assertTrue(check_container_action(request=req, action=PolicyAction.CONTAINER_DESCRIPTION))
        delete_policy("policy")

        # Policy for resolver
        set_policy(name="policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_DESCRIPTION,
                   resolver=[self.resolvername3])
        self.assertTrue(check_container_action(request=req, action=PolicyAction.CONTAINER_DESCRIPTION))
        delete_policy("policy")

        # Policy for realm
        set_policy(name="policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_DESCRIPTION, realm=[self.realm3])
        self.assertTrue(check_container_action(request=req, action=PolicyAction.CONTAINER_DESCRIPTION))
        delete_policy("policy")

        # Policy for user
        set_policy(name="policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_DESCRIPTION, user="root",
                   realm=[self.realm3], resolver=[self.resolvername3])
        self.assertTrue(check_container_action(request=req, action=PolicyAction.CONTAINER_DESCRIPTION))
        delete_policy("policy")

        container.delete()

        # Container has no owner: only allowed for assign and create
        req, container = self.mock_container_request_no_user("user")
        # Generic policy
        set_policy(name="policy", scope=SCOPE.USER,
                   action=[PolicyAction.CONTAINER_ASSIGN_USER, PolicyAction.CONTAINER_CREATE])
        self.assertTrue(check_container_action(request=req, action=PolicyAction.CONTAINER_ASSIGN_USER))
        container.delete()
        self.assertTrue(check_container_action(request=req, action=PolicyAction.CONTAINER_CREATE))
        delete_policy("policy")

    def test_68_check_container_action_user_denied(self):
        self.setUp_user_realms()
        self.setUp_user_realm3()

        # Container of the user
        req, container = self.mock_container_request("user")

        # No description policy
        set_policy(name="policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_CREATE)
        self.assertRaises(PolicyError, check_container_action, request=req, action=PolicyAction.CONTAINER_DESCRIPTION)
        delete_policy("policy")

        # Policy for another resolver
        set_policy(name="policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_DESCRIPTION,
                   resolver=[self.resolvername1])
        self.assertRaises(PolicyError, check_container_action, request=req, action=PolicyAction.CONTAINER_DESCRIPTION)
        delete_policy("policy")

        # Policy for another realm (realm of container, but not realm from user)
        set_policy(name="policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_DESCRIPTION, realm=[self.realm1])
        self.assertRaises(PolicyError, check_container_action, request=req, action=PolicyAction.CONTAINER_DESCRIPTION)
        delete_policy("policy")

        # Policy for another user of the same realm
        set_policy(name="policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_DESCRIPTION, user="hans",
                   realm=[self.realm3],
                   resolver=[self.resolvername3])
        self.assertRaises(PolicyError, check_container_action, request=req, action=PolicyAction.CONTAINER_DESCRIPTION)
        delete_policy("policy")

        container.delete()

        # request user differs from container owner
        set_policy(name="policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_DESCRIPTION)
        selfservice = User(login="selfservice", realm=self.realm1, resolver=self.resolvername1)
        req.User = selfservice
        self.assertRaises(PolicyError, check_container_action, request=req, action=PolicyAction.CONTAINER_DESCRIPTION)
        delete_policy("policy")

        # Container has no owner: only allowed for assign and create
        req, container = self.mock_container_request_no_user("user")
        # Generic policy
        set_policy(name="policy", scope=SCOPE.USER,
                   action=[PolicyAction.CONTAINER_ASSIGN_USER, PolicyAction.CONTAINER_DESCRIPTION])
        self.assertRaises(PolicyError, check_container_action, request=req, action=PolicyAction.CONTAINER_DESCRIPTION)
        delete_policy("policy")
        container.delete()

    def test_69_check_container_action_admin_success(self):
        self.setUp_user_realms()
        self.setUp_user_realm3()
        req, container = self.mock_container_request("admin")

        # Generic policy
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DESCRIPTION)
        self.assertTrue(check_container_action(request=req, action=PolicyAction.CONTAINER_DESCRIPTION))
        # request user differs from container owner: uses container owner (can only happen in token init)
        selfservice = User(login="selfservice", realm=self.realm1, resolver=self.resolvername1)
        req.User = selfservice
        self.assertTrue(check_container_action(request=req, action=PolicyAction.CONTAINER_DESCRIPTION))
        delete_policy("policy")

        # Policy for resolver
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DESCRIPTION,
                   resolver=[self.resolvername3])
        self.assertTrue(check_container_action(request=req, action=PolicyAction.CONTAINER_DESCRIPTION))
        # request user differs from container owner: uses container owner (can only happen in token init)
        selfservice = User(login="selfservice", realm=self.realm1, resolver=self.resolvername1)
        req.User = selfservice
        self.assertTrue(check_container_action(request=req, action=PolicyAction.CONTAINER_DESCRIPTION))
        delete_policy("policy")

        # Policy for realm3 of the user
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DESCRIPTION, realm=[self.realm3])
        self.assertTrue(check_container_action(request=req, action=PolicyAction.CONTAINER_DESCRIPTION))
        # request user differs from container owner: uses container owner (can only happen in token init)
        selfservice = User(login="selfservice", realm=self.realm1, resolver=self.resolvername1)
        req.User = selfservice
        self.assertTrue(check_container_action(request=req, action=PolicyAction.CONTAINER_DESCRIPTION))
        delete_policy("policy")

        # Policy for additional container realm1 and wrong realm 2
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DESCRIPTION,
                   realm=[self.realm2, self.realm1])
        self.assertTrue(check_container_action(request=req, action=PolicyAction.CONTAINER_DESCRIPTION))
        # request user differs from container owner: uses container owner (can only happen in token init)
        selfservice = User(login="selfservice", realm=self.realm1, resolver=self.resolvername1)
        req.User = selfservice
        self.assertTrue(check_container_action(request=req, action=PolicyAction.CONTAINER_DESCRIPTION))
        delete_policy("policy")

        # Policy for user
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DESCRIPTION, user="root",
                   realm=[self.realm3],
                   resolver=[self.resolvername3])
        self.assertTrue(check_container_action(request=req, action=PolicyAction.CONTAINER_DESCRIPTION))
        # request user differs from container owner: uses container owner (can only happen in token init)
        selfservice = User(login="selfservice", realm=self.realm1, resolver=self.resolvername1)
        req.User = selfservice
        self.assertTrue(check_container_action(request=req, action=PolicyAction.CONTAINER_DESCRIPTION))
        delete_policy("policy")

        container.delete()

        # container without user
        req, container = self.mock_container_request_no_user("admin")

        # Generic policy
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DESCRIPTION)
        self.assertTrue(check_container_action(request=req, action=PolicyAction.CONTAINER_DESCRIPTION))
        delete_policy("policy")

        # Policy for realm: only assign is allowed
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ASSIGN_USER, realm=[self.realm1])
        self.assertTrue(check_container_action(request=req, action=PolicyAction.CONTAINER_ASSIGN_USER))
        delete_policy("policy")

        container.delete()

    def test_70_check_container_action_admin_denied(self):
        self.setUp_user_realms()
        self.setUp_user_realm3()
        req, container = self.mock_container_request("admin")

        # No enable policy
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_CREATE)
        self.assertRaises(PolicyError, check_container_action, request=req, action=PolicyAction.CONTAINER_DESCRIPTION)
        delete_policy("policy")

        # Policy for another resolver
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DESCRIPTION,
                   resolver=[self.resolvername1])
        self.assertRaises(PolicyError, check_container_action, request=req, action=PolicyAction.CONTAINER_DESCRIPTION)
        # request user would be allowed, but not the container owner (only possible in token init)
        req.User = User(login="selfservice", realm=self.realm1, resolver=self.resolvername1)
        self.assertRaises(PolicyError, check_container_action, request=req, action=PolicyAction.CONTAINER_DESCRIPTION)
        delete_policy("policy")

        # Policy for another realm
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DESCRIPTION, realm=["realm2"])
        self.assertRaises(PolicyError, check_container_action, request=req, action=PolicyAction.CONTAINER_DESCRIPTION)
        delete_policy("policy")
        # assign not allowed if container is in another realm
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ASSIGN_USER, realm=["realm2"])
        self.assertRaises(PolicyError, check_container_action, request=req, action=PolicyAction.CONTAINER_DESCRIPTION)
        delete_policy("policy")

        # Policy for another user of the same realm
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DESCRIPTION, user="hans",
                   realm=[self.realm3],
                   resolver=[self.resolvername3])
        self.assertRaises(PolicyError, check_container_action, request=req, action=PolicyAction.CONTAINER_DESCRIPTION)
        delete_policy("policy")

        container.delete()

        # container without user
        req, container = self.mock_container_request_no_user("admin")

        # Policy for resolver
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DESCRIPTION,
                   resolver=[self.resolvername3])
        self.assertRaises(PolicyError, check_container_action, request=req, action=PolicyAction.CONTAINER_DESCRIPTION)
        delete_policy("policy")

        # Policy for realm
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DESCRIPTION, realm=[self.realm1])
        self.assertRaises(PolicyError, check_container_action, request=req, action=PolicyAction.CONTAINER_DESCRIPTION)
        delete_policy("policy")

        # Policy for a user
        set_policy(name="policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DESCRIPTION, user="root",
                   realm=[self.realm3],
                   resolver=[self.resolvername3])
        self.assertRaises(PolicyError, check_container_action, request=req, action=PolicyAction.CONTAINER_DESCRIPTION)
        delete_policy("policy")

        container.delete()

    def test_76_check_client_container_action_user_success(self):
        self.setUp_user_realms()
        self.setUp_user_realm3()

        # container with user and realm
        req, container = self.mock_client_container_request()

        # Generic policy
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER)
        self.assertTrue(check_client_container_action(request=req, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER))
        delete_policy("policy")

        # Policy for resolver
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER,
                   resolver=[self.resolvername3])
        self.assertTrue(check_client_container_action(request=req, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER))
        delete_policy("policy")

        # Policy for user realm
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER,
                   realm=[self.realm3])
        self.assertTrue(check_client_container_action(request=req, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER))
        delete_policy("policy")

        # Policy for additional realm
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER,
                   realm=[self.realm1])
        self.assertTrue(check_client_container_action(request=req, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER))
        delete_policy("policy")

        # Policy for user
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER, user="root",
                   realm=[self.realm3], resolver=[self.resolvername3])
        self.assertTrue(check_client_container_action(request=req, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER))
        delete_policy("policy")

        container.delete()

        # container without user
        req, container = self.mock_client_container_request_no_user()
        # Generic policy
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER)
        self.assertTrue(check_client_container_action(request=req, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER))
        delete_policy("policy")

        # container with realms
        container.set_realms([self.realm1, self.realm3], add=False)
        # Policy for realm1
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER,
                   realm=[self.realm1])
        self.assertTrue(check_client_container_action(request=req, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER))
        delete_policy("policy")
        # Policy for realm3
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER,
                   realm=[self.realm3])
        self.assertTrue(check_client_container_action(request=req, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER))
        delete_policy("policy")
        container.delete()

    def test_77_check_client_container_action_user_denied(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        self.setUp_user_realm3()

        # container with user and realm
        req, container = self.mock_client_container_request()

        # No rollover policy
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.DISABLE_CLIENT_TOKEN_DELETION)
        self.assertRaises(PolicyError, check_client_container_action, request=req,
                          action=PolicyAction.CONTAINER_CLIENT_ROLLOVER)
        delete_policy("policy")

        # Policy for another resolver
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER,
                   resolver=[self.resolvername1])
        self.assertRaises(PolicyError, check_client_container_action, request=req,
                          action=PolicyAction.CONTAINER_CLIENT_ROLLOVER)
        delete_policy("policy")

        # Policy for another realm
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER,
                   realm=[self.realm2])
        self.assertRaises(PolicyError, check_client_container_action, request=req,
                          action=PolicyAction.CONTAINER_CLIENT_ROLLOVER)
        delete_policy("policy")

        # Policy for another user of the same realm
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER, user="hans",
                   realm=[self.realm3],
                   resolver=[self.resolvername3])
        self.assertRaises(PolicyError, check_client_container_action, request=req,
                          action=PolicyAction.CONTAINER_CLIENT_ROLLOVER)
        delete_policy("policy")

        container.delete()

        # container without user
        req, container = self.mock_client_container_request_no_user()
        # Policy for a realm
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER,
                   realm=self.realm1)
        self.assertRaises(PolicyError, check_client_container_action, request=req,
                          action=PolicyAction.CONTAINER_CLIENT_ROLLOVER)
        delete_policy("policy")

        # Policy for a resolver
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER,
                   resolver=self.resolvername1)
        self.assertRaises(PolicyError, check_client_container_action, request=req,
                          action=PolicyAction.CONTAINER_CLIENT_ROLLOVER)
        delete_policy("policy")

        # Policy for a user
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER,
                   realm=self.realm1,
                   user="hans")
        self.assertRaises(PolicyError, check_client_container_action, request=req,
                          action=PolicyAction.CONTAINER_CLIENT_ROLLOVER)
        delete_policy("policy")

        # Policy with all actions in the scope disabled action
        set_policy(name="policy", scope=SCOPE.CONTAINER, realm=self.realm1,
                   user="hans")
        self.assertRaises(PolicyError, check_client_container_action, request=req,
                          action=PolicyAction.CONTAINER_CLIENT_ROLLOVER)
        delete_policy("policy")

        # container with realms
        container.set_realms([self.realm1, self.realm3], add=False)
        # policy for another realm
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER,
                   realm=[self.realm2])
        self.assertRaises(PolicyError, check_client_container_action, request=req,
                          action=PolicyAction.CONTAINER_CLIENT_ROLLOVER)
        delete_policy("policy")

        # policy for a user
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER,
                   realm=[self.realm1],
                   user="hans")
        self.assertRaises(PolicyError, check_client_container_action, request=req,
                          action=PolicyAction.CONTAINER_CLIENT_ROLLOVER)
        delete_policy("policy")

        container.delete()

    def test_78_container_registration_config_success(self):
        self.setUp_user_realms()
        self.setUp_user_realm3()

        # Set a policy only valid for another realm
        set_policy("policy_realm2", SCOPE.CONTAINER,
                   action={PolicyAction.CONTAINER_SERVER_URL: "https://test.com",
                           PolicyAction.CONTAINER_REGISTRATION_TTL: 60,
                           PolicyAction.CONTAINER_CHALLENGE_TTL: 50,
                           PolicyAction.CONTAINER_SSL_VERIFY: "False"},
                   realm=self.realm2)

        # policy including server url + default values for ttl and ssl_verify
        req, container = self.mock_container_request("user")
        set_policy("policy", SCOPE.CONTAINER, action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.com"})
        container_registration_config(req)
        self.assertEqual("https://pi.com", req.all_data["server_url"])
        self.assertEqual(10, req.all_data["registration_ttl"])
        self.assertEqual(2, req.all_data["challenge_ttl"])
        self.assertEqual("True", req.all_data["ssl_verify"])
        delete_policy("policy")
        container.delete()

        # specifying valid values in generic policy
        req, container = self.mock_container_request("user")
        set_policy("generic_policy", SCOPE.CONTAINER,
                   action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.com",
                           PolicyAction.CONTAINER_REGISTRATION_TTL: 20,
                           PolicyAction.CONTAINER_CHALLENGE_TTL: 6,
                           PolicyAction.CONTAINER_SSL_VERIFY: "False"},
                   priority=3)
        container_registration_config(req)
        self.assertEqual("https://pi.com", req.all_data["server_url"])
        self.assertEqual(20, req.all_data["registration_ttl"])
        self.assertEqual(6, req.all_data["challenge_ttl"])
        self.assertEqual("False", req.all_data["ssl_verify"])
        container.delete()

        # specifying valid values in policy for realm with higher priority than generic policy
        req, container = self.mock_container_request("user")
        set_policy("policy", SCOPE.CONTAINER,
                   action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.com",
                           PolicyAction.CONTAINER_REGISTRATION_TTL: 30,
                           PolicyAction.CONTAINER_CHALLENGE_TTL: 8,
                           PolicyAction.CONTAINER_SSL_VERIFY: "False"},
                   realm=self.realm3,
                   priority=1)
        container_registration_config(req)
        self.assertEqual("https://pi.com", req.all_data["server_url"])
        self.assertEqual(30, req.all_data["registration_ttl"])
        self.assertEqual(8, req.all_data["challenge_ttl"])
        self.assertEqual("False", req.all_data["ssl_verify"])
        delete_policy("policy")
        delete_policy("generic_policy")
        container.delete()

        # specifying invalid values sets default values
        req, container = self.mock_container_request("user")
        set_policy("policy", SCOPE.CONTAINER, action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.com",
                                                      PolicyAction.CONTAINER_REGISTRATION_TTL: -20,
                                                      PolicyAction.CONTAINER_CHALLENGE_TTL: -6,
                                                      PolicyAction.CONTAINER_SSL_VERIFY: "maybe"})
        container_registration_config(req)
        self.assertEqual("https://pi.com", req.all_data["server_url"])
        self.assertEqual(10, req.all_data["registration_ttl"])
        self.assertEqual(2, req.all_data["challenge_ttl"])
        self.assertEqual("True", req.all_data["ssl_verify"])
        delete_policy("policy")
        container.delete()

        delete_policy("policy_realm2")

    def test_79_container_registration_config_fail(self):
        self.setUp_user_realms()
        self.setUp_user_realm3()

        # policy without server url shall raise error
        req, container = self.mock_container_request("user")
        self.assertRaises(PolicyError, container_registration_config, req)
        container.delete()

        # specifying valid values in policy for another realm
        req, container = self.mock_container_request("user")
        set_policy("policy", SCOPE.CONTAINER, action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.com",
                                                      PolicyAction.CONTAINER_REGISTRATION_TTL: 20,
                                                      PolicyAction.CONTAINER_CHALLENGE_TTL: 6,
                                                      PolicyAction.CONTAINER_SSL_VERIFY: "False"}, realm=self.realm2)
        self.assertRaises(PolicyError, container_registration_config, req)
        delete_policy("policy")

        # conflicting policies for server url shall raise error
        req, container = self.mock_container_request("user")
        set_policy("policy1", SCOPE.CONTAINER, action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.com"})
        set_policy("policy2", SCOPE.CONTAINER, action={PolicyAction.CONTAINER_SERVER_URL: "https://test.com"})
        self.assertRaises(PolicyError, container_registration_config, req)
        delete_policy("policy1")
        delete_policy("policy2")
        container.delete()

        # conflicting policies for registration ttl shall raise error
        req, container = self.mock_container_request("user")
        set_policy("policy1", SCOPE.CONTAINER,
                   action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.com",
                           PolicyAction.CONTAINER_REGISTRATION_TTL: 20})
        set_policy("policy2", SCOPE.CONTAINER, action={PolicyAction.CONTAINER_REGISTRATION_TTL: 30})
        self.assertRaises(PolicyError, container_registration_config, req)
        delete_policy("policy1")
        delete_policy("policy2")
        container.delete()

        # conflicting policies for challenge ttl shall raise error
        req, container = self.mock_container_request("user")
        set_policy("policy1", SCOPE.CONTAINER,
                   action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.com",
                           PolicyAction.CONTAINER_CHALLENGE_TTL: 20})
        set_policy("policy2", SCOPE.CONTAINER, action={PolicyAction.CONTAINER_CHALLENGE_TTL: 30})
        self.assertRaises(PolicyError, container_registration_config, req)
        delete_policy("policy1")
        delete_policy("policy2")
        container.delete()

        # conflicting policies for challenge ttl shall raise error
        req, container = self.mock_container_request("user")
        set_policy("policy1", SCOPE.CONTAINER,
                   action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.com",
                           PolicyAction.CONTAINER_SSL_VERIFY: "False"})
        set_policy("policy2", SCOPE.CONTAINER, action={PolicyAction.CONTAINER_SSL_VERIFY: "True"})
        self.assertRaises(PolicyError, container_registration_config, req)
        delete_policy("policy1")
        delete_policy("policy2")
        container.delete()

    def test_80_smartphone_config(self):
        self.setUp_user_realms()
        self.setUp_user_realm3()

        # No container policy at all: use default values
        req, container = self.mock_container_request("user", "smartphone")
        self.assertTrue(smartphone_config(req))
        policies = req.all_data["client_policies"]
        self.assertFalse(policies[PolicyAction.CONTAINER_CLIENT_ROLLOVER])
        self.assertFalse(policies[PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER])
        self.assertFalse(policies[PolicyAction.DISABLE_CLIENT_TOKEN_DELETION])
        self.assertFalse(policies[PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER])
        container.delete()

        # Set a policy only valid for another realm
        set_policy("policy_realm2", SCOPE.CONTAINER,
                   action=[PolicyAction.CONTAINER_CLIENT_ROLLOVER,
                           PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER,
                           PolicyAction.DISABLE_CLIENT_TOKEN_DELETION,
                           PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER],
                   realm=self.realm2)

        # No policy: use default values
        req, container = self.mock_container_request("user", "smartphone")
        self.assertTrue(smartphone_config(req))
        policies = req.all_data["client_policies"]
        self.assertFalse(policies[PolicyAction.CONTAINER_CLIENT_ROLLOVER])
        self.assertFalse(policies[PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER])
        self.assertFalse(policies[PolicyAction.DISABLE_CLIENT_TOKEN_DELETION])
        self.assertFalse(policies[PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER])
        container.delete()

        # Generic policy defined
        set_policy("policy", SCOPE.CONTAINER,
                   action=[PolicyAction.CONTAINER_CLIENT_ROLLOVER,
                           PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER,
                           PolicyAction.DISABLE_CLIENT_TOKEN_DELETION,
                           PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER])
        req, container = self.mock_container_request("user", "smartphone")
        self.assertTrue(smartphone_config(req))
        policies = req.all_data["client_policies"]
        self.assertTrue(policies[PolicyAction.CONTAINER_CLIENT_ROLLOVER])
        self.assertTrue(policies[PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER])
        self.assertTrue(policies[PolicyAction.DISABLE_CLIENT_TOKEN_DELETION])
        self.assertTrue(policies[PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER])
        container.delete()
        delete_policy("policy")

        # Policy for realm defined
        set_policy("policy", SCOPE.CONTAINER,
                   action=[PolicyAction.CONTAINER_CLIENT_ROLLOVER,
                           PolicyAction.DISABLE_CLIENT_TOKEN_DELETION],
                   realm=self.realm3)
        req, container = self.mock_container_request("user", "smartphone")
        self.assertTrue(smartphone_config(req))
        policies = req.all_data["client_policies"]
        self.assertTrue(policies[PolicyAction.CONTAINER_CLIENT_ROLLOVER])
        self.assertFalse(policies[PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER])
        self.assertTrue(policies[PolicyAction.DISABLE_CLIENT_TOKEN_DELETION])
        self.assertFalse(policies[PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER])
        container.delete()

        # wrong container type
        req, container = self.mock_container_request("user", "generic")
        self.assertFalse(smartphone_config(req))
        self.assertNotIn("client_policies", req.all_data.keys())
        container.delete()

        # Invalid container serial provided
        req, container = self.mock_container_request("user", "smartphone")
        container.delete()
        self.assertFalse(smartphone_config(req))
        self.assertNotIn("client_policies", req.all_data.keys())

        # No container_serial provided
        req, token = self.mock_token_request("admin")
        self.assertFalse(smartphone_config(req))
        self.assertNotIn("client_policies", req.all_data.keys())
        token.delete_token()

        delete_policy("policy")
        delete_policy("policy_realm2")

    def test_81_check_client_container_disabled_action_user_denied(self):
        self.setUp_user_realms()
        self.setUp_user_realm3()

        # container with user and realm
        req, container = self.mock_client_container_request()

        # Generic policy
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER)
        self.assertRaises(PolicyError, check_client_container_disabled_action, request=req,
                          action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER)
        delete_policy("policy")

        # Policy for resolver
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   resolver=[self.resolvername3])
        self.assertRaises(PolicyError, check_client_container_disabled_action, request=req,
                          action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER)
        delete_policy("policy")

        # Policy for user realm
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   realm=[self.realm3])
        self.assertRaises(PolicyError, check_client_container_disabled_action, request=req,
                          action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER)
        delete_policy("policy")

        # Policy for additional realm
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   realm=[self.realm1])
        self.assertRaises(PolicyError, check_client_container_disabled_action, request=req,
                          action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER)
        delete_policy("policy")

        # Policy for user
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   user="root",
                   realm=[self.realm3], resolver=[self.resolvername3])
        self.assertRaises(PolicyError, check_client_container_disabled_action, request=req,
                          action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER)
        delete_policy("policy")

        container.delete()

        # container without user
        req, container = self.mock_client_container_request_no_user()
        # Generic policy
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER)
        self.assertRaises(PolicyError, check_client_container_disabled_action, request=req,
                          action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER)
        delete_policy("policy")

        # container with realms
        container.set_realms([self.realm1, self.realm3], add=False)
        # Policy for realm1
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   realm=[self.realm1])
        self.assertRaises(PolicyError, check_client_container_disabled_action, request=req,
                          action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER)
        delete_policy("policy")
        # Policy for realm3
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   realm=[self.realm3])
        self.assertRaises(PolicyError, check_client_container_disabled_action, request=req,
                          action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER)
        delete_policy("policy")
        container.delete()

    def test_82_check_client_container_action_user_success(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        self.setUp_user_realm3()

        # container with user and realm
        req, container = self.mock_client_container_request()

        # No policy in the container scope at all
        self.assertTrue(
            check_client_container_disabled_action(request=req,
                                                   action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER))

        # No unregister policy
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER)
        self.assertTrue(
            check_client_container_disabled_action(request=req,
                                                   action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER))
        delete_policy("policy")

        # Policy for another resolver
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   resolver=[self.resolvername1])
        self.assertTrue(
            check_client_container_disabled_action(request=req,
                                                   action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER))
        delete_policy("policy")

        # Policy for another realm
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   realm=[self.realm2])
        self.assertTrue(
            check_client_container_disabled_action(request=req,
                                                   action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER))
        delete_policy("policy")

        # Policy for another user of the same realm
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   user="hans",
                   realm=[self.realm3],
                   resolver=[self.resolvername3])
        self.assertTrue(
            check_client_container_disabled_action(request=req,
                                                   action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER))
        delete_policy("policy")

        container.delete()

        # container without user
        req, container = self.mock_client_container_request_no_user()
        # Policy for a realm
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   realm=self.realm1)
        self.assertTrue(
            check_client_container_disabled_action(request=req,
                                                   action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER))
        delete_policy("policy")

        # Policy for a resolver
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   resolver=self.resolvername1)
        self.assertTrue(
            check_client_container_disabled_action(request=req,
                                                   action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER))
        delete_policy("policy")

        # Policy for a user
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   realm=self.realm1,
                   user="hans")
        self.assertTrue(
            check_client_container_disabled_action(request=req,
                                                   action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER))
        delete_policy("policy")

        # Policy with all actions in the scope disabled action
        set_policy(name="policy", scope=SCOPE.CONTAINER, realm=self.realm1,
                   user="hans")
        self.assertTrue(
            check_client_container_disabled_action(request=req,
                                                   action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER))
        delete_policy("policy")

        # container with realms
        container.set_realms([self.realm1, self.realm3], add=False)
        # policy for another realm
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   realm=[self.realm2])
        self.assertTrue(
            check_client_container_disabled_action(request=req,
                                                   action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER))
        delete_policy("policy")

        # policy for a user
        set_policy(name="policy", scope=SCOPE.CONTAINER, action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   realm=[self.realm1],
                   user="hans")
        self.assertTrue(
            check_client_container_disabled_action(request=req,
                                                   action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER))
        delete_policy("policy")

        container.delete()

    def test_83_rss_age_admin(self):
        # Test default for admins:
        g.logged_in_user = {"username": "super",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 headers={})
        env = builder.get_environ()
        req = Request(env)
        req.User = User("cornelius")
        req.all_data = {}
        r = rss_age(req, None)
        self.assertTrue(r)
        self.assertEqual(180, req.all_data.get(f"{PolicyAction.RSS_AGE}"))

    def test_84_rss_age_user(self):
        g.logged_in_user = {"username": "cornelius",
                            "role": "user"}
        builder = EnvironBuilder(method='POST',
                                 headers={})
        env = builder.get_environ()
        # Test default for users:
        req = Request(env)
        req.User = User("cornelius")
        req.all_data = {}
        r = rss_age(req, None)
        self.assertTrue(r)
        self.assertEqual(0, req.all_data.get(f"{PolicyAction.RSS_AGE}"))

        # Set policy for user to 12 days.
        set_policy(name="rssage",
                   scope=SCOPE.WEBUI,
                   action=f"{PolicyAction.RSS_AGE}=12")
        req = Request(env)
        req.User = User("cornelius")
        req.all_data = {}
        r = rss_age(req, None)
        self.assertTrue(r)
        self.assertEqual(12, req.all_data.get(f"{PolicyAction.RSS_AGE}"))

        # Now test a bogus policy
        set_policy(name="rssage",
                   scope=SCOPE.WEBUI,
                   action=[f"{PolicyAction.RSS_AGE}=blubb"])
        req = Request(env)
        req.User = User("cornelius")
        req.all_data = {}
        r = rss_age(req, None)
        self.assertTrue(r)
        # We receive the default of 0
        self.assertEqual(0, req.all_data.get(f"{PolicyAction.RSS_AGE}"))

        delete_policy("rssage")

    def test_85_hide_container_info(self):
        self.setUp_user_realm3()
        # ---- Admin ----
        req, container = self.mock_container_request("admin", "smartphone")

        # No policy set
        hide_container_info(req)
        self.assertSetEqual(set(), set(req.all_data["hide_container_info"]))

        # Set admin, helpdesk and user policies
        set_policy(name="admin", scope=SCOPE.ADMIN,
                   action=f"{PolicyAction.HIDE_CONTAINER_INFO}=initially_synchronized device")
        set_policy(name="user", scope=SCOPE.USER,
                   action=f"{PolicyAction.HIDE_CONTAINER_INFO}=initially_synchronized challenge_ttl encrypt_algorithm "
                          f"encrypt_key_algorithm encrypt_mode hash_algorithm key_algorithm server_url")

        # admin
        hide_container_info(req)
        self.assertSetEqual({"initially_synchronized", "device"}, set(req.all_data["hide_container_info"]))

        # ---- Helpdesk ----
        set_policy(name="admin", scope=SCOPE.ADMIN,
                   action=f"{PolicyAction.HIDE_CONTAINER_INFO}=device", realm=self.realm1)
        # request including  user
        hide_container_info(req)
        self.assertSetEqual({"device"}, set(req.all_data["hide_container_info"]))
        # request not including user and container has no owner, but is in realm1
        req, container = self.mock_container_request_no_user("admin", "smartphone")
        container.set_realms([self.realm1], add=True)
        req.pi_allowed_container_realms = [self.realm3]
        hide_container_info(req)
        self.assertSetEqual({"device"}, set(req.all_data["hide_container_info"]))

        # ---- User ----
        req, container = self.mock_container_request("user", "smartphone")
        hide_container_info(req)
        self.assertSetEqual({"initially_synchronized", "challenge_ttl", "encrypt_algorithm", "encrypt_key_algorithm",
                             "encrypt_mode", "hash_algorithm", "key_algorithm", "server_url"},
                            set(req.all_data["hide_container_info"]))

        delete_policy("admin")
        delete_policy("user")

    def test_86_force_server_generate_key_user(self):
        g.logged_in_user = {"username": "hans",
                            "realm": self.realm1,
                            "resolver": self.resolvername1,
                            "role": "user"}
        user = User("hans", self.realm1)
        builder = EnvironBuilder(method='POST',
                                 headers={})
        env = builder.get_environ()
        # Test default for users:
        request = Request(env)
        request.User = user
        request.all_data = {"type": "hotp"}
        set_policy("enroll", SCOPE.USER, action="enrollHOTP, enrollTOTP")

        # Policy is not set
        g.policies = {}
        force_server_generate_key(request)
        self.assertFalse(g.policies.get(f"hotp_{PolicyAction.FORCE_SERVER_GENERATE}"))

        # Set policy for different token type
        g.policies = {}
        set_policy("totp_genkey", scope=SCOPE.USER, action=f"totp_{PolicyAction.FORCE_SERVER_GENERATE}")
        force_server_generate_key(request)
        self.assertFalse(g.policies.get(f"hotp_{PolicyAction.FORCE_SERVER_GENERATE}"))
        self.assertNotIn(f"totp_{PolicyAction.FORCE_SERVER_GENERATE}", g.policies)

        # Set policy for hotp
        g.policies = {}
        set_policy("hotp_genkey", scope=SCOPE.USER, action=f"hotp_{PolicyAction.FORCE_SERVER_GENERATE}")
        force_server_generate_key(request)
        self.assertTrue(g.policies.get(f"hotp_{PolicyAction.FORCE_SERVER_GENERATE}"))
        self.assertNotIn(f"totp_{PolicyAction.FORCE_SERVER_GENERATE}", g.policies)

        # Test for TOTP
        g.policies = {}
        request.all_data = {"type": "totp"}
        force_server_generate_key(request)
        self.assertTrue(g.policies.get(f"totp_{PolicyAction.FORCE_SERVER_GENERATE}"))
        self.assertNotIn(f"hotp_{PolicyAction.FORCE_SERVER_GENERATE}", g.policies)

        # Test for mOTP
        set_policy("motp_genkey", scope=SCOPE.USER, action=f"motp_{PolicyAction.FORCE_SERVER_GENERATE}")
        g.policies = {}
        request.all_data = {"type": "motp", "motppin": "123"}
        force_server_generate_key(request)
        self.assertTrue(g.policies.get(f"motp_{PolicyAction.FORCE_SERVER_GENERATE}"))
        self.assertNotIn(f"hotp_{PolicyAction.FORCE_SERVER_GENERATE}", g.policies)
        self.assertNotIn(f"totp_{PolicyAction.FORCE_SERVER_GENERATE}", g.policies)

        # Test for applspec
        set_policy("applspec_genkey", scope=SCOPE.USER, action=f"applspec_{PolicyAction.FORCE_SERVER_GENERATE}")
        g.policies = {}
        request.all_data = {"type": "applspec", "motppin": "123", "service_id": "123"}
        force_server_generate_key(request)
        self.assertTrue(g.policies.get(f"applspec_{PolicyAction.FORCE_SERVER_GENERATE}"))
        self.assertNotIn(f"hotp_{PolicyAction.FORCE_SERVER_GENERATE}", g.policies)
        self.assertNotIn(f"totp_{PolicyAction.FORCE_SERVER_GENERATE}", g.policies)
        self.assertNotIn(f"motp_{PolicyAction.FORCE_SERVER_GENERATE}", g.policies)

        # Test for a token type not having this policy
        g.policies = {}
        request.all_data = {"type": "spass"}
        force_server_generate_key(request)
        self.assertFalse(g.policies.get(f"spass_{PolicyAction.FORCE_SERVER_GENERATE}"))
        self.assertNotIn(f"hotp_{PolicyAction.FORCE_SERVER_GENERATE}", g.policies)
        self.assertNotIn(f"totp_{PolicyAction.FORCE_SERVER_GENERATE}", g.policies)
        self.assertNotIn(f"motp_{PolicyAction.FORCE_SERVER_GENERATE}", g.policies)
        self.assertNotIn(f"applspec_{PolicyAction.FORCE_SERVER_GENERATE}", g.policies)

        delete_policy("enroll")
        delete_policy("totp_genkey")
        delete_policy("hotp_genkey")
        delete_policy("motp_genkey")
        delete_policy("applspec_genkey")

    def test_86_force_server_generate_key_admin(self):
        g.logged_in_user = {"username": self.testadmin, "realm": "",
                            "role": "admin"}
        builder = EnvironBuilder(method='POST',
                                 headers={})
        env = builder.get_environ()
        # Test default for users:
        request = Request(env)
        request.User = User()
        request.all_data = {"type": "hotp"}
        set_policy("enroll", SCOPE.ADMIN, action="enrollHOTP, enrollTOTP")

        # Policy is not set
        g.policies = {}
        force_server_generate_key(request)
        self.assertFalse(g.policies.get(f"hotp_{PolicyAction.FORCE_SERVER_GENERATE}"))

        # Set policy for hotp
        g.policies = {}
        set_policy("hotp_genkey", scope=SCOPE.ADMIN, action=f"hotp_{PolicyAction.FORCE_SERVER_GENERATE}")
        force_server_generate_key(request)
        self.assertTrue(g.policies.get(f"hotp_{PolicyAction.FORCE_SERVER_GENERATE}"))

        # Test for TOTP
        set_policy("totp_genkey", scope=SCOPE.ADMIN, action=f"totp_{PolicyAction.FORCE_SERVER_GENERATE}")
        g.policies = {}
        request.all_data = {"type": "totp"}
        force_server_generate_key(request)
        self.assertTrue(g.policies.get(f"totp_{PolicyAction.FORCE_SERVER_GENERATE}"))
        self.assertNotIn(f"hotp_{PolicyAction.FORCE_SERVER_GENERATE}", g.policies)

        # Test for mOTP
        set_policy("motp_genkey", scope=SCOPE.ADMIN, action=f"motp_{PolicyAction.FORCE_SERVER_GENERATE}")
        g.policies = {}
        request.all_data = {"type": "motp", "motppin": "123"}
        force_server_generate_key(request)
        self.assertTrue(g.policies.get(f"motp_{PolicyAction.FORCE_SERVER_GENERATE}"))
        self.assertNotIn(f"hotp_{PolicyAction.FORCE_SERVER_GENERATE}", g.policies)
        self.assertNotIn(f"totp_{PolicyAction.FORCE_SERVER_GENERATE}", g.policies)

        # Test for applspec
        set_policy("applspec_genkey", scope=SCOPE.ADMIN, action=f"applspec_{PolicyAction.FORCE_SERVER_GENERATE}")
        g.policies = {}
        request.all_data = {"type": "applspec", "motppin": "123", "service_id": "123"}
        force_server_generate_key(request)
        self.assertTrue(g.policies.get(f"applspec_{PolicyAction.FORCE_SERVER_GENERATE}"))
        self.assertNotIn(f"hotp_{PolicyAction.FORCE_SERVER_GENERATE}", g.policies)
        self.assertNotIn(f"totp_{PolicyAction.FORCE_SERVER_GENERATE}", g.policies)
        self.assertNotIn(f"motp_{PolicyAction.FORCE_SERVER_GENERATE}", g.policies)

        delete_policy("enroll")
        delete_policy("totp_genkey")
        delete_policy("hotp_genkey")
        delete_policy("motp_genkey")
        delete_policy("applspec_genkey")
