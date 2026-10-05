# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for WebAuthn/FIDO2 prepolicies (privacyidea.api.lib.prepolicy)."""


from privacyidea.api.lib.prepolicy import (fido2_auth, webauthntoken_authz,
                                           fido2_enroll, webauthntoken_request)
from privacyidea.lib.error import PolicyError
from privacyidea.lib.fido2.policy_action import FIDO2PolicyAction
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policy import (set_policy, delete_policy, SCOPE)
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
from privacyidea.lib.utils import hexlify_and_unicode
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


class PrePolicyWebauthnTestCase(PrePolicyHelperMixin, MyApiTestCase):

    def setUp(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        self.setUp_user_realm3()

    def test_26a_webauthn_auth_validate_triggerchallenge(self):
        class RequestMock(object):
            pass

        # Normal request
        request = RequestMock()
        request.all_data = {
            'user': 'foo'
        }

        fido2_auth(request, None)
        self.assertEqual(set(request.all_data.get(FIDO2PolicyAction.ALLOWED_TRANSPORTS)),
                         set(DEFAULT_ALLOWED_TRANSPORTS.split()))
        self.assertEqual(request.all_data.get(WebAuthnTokenClass.get_class_type() + '_' + PolicyAction.CHALLENGETEXT),
                         DEFAULT_CHALLENGE_TEXT_AUTH)

        # Request via serial
        request = RequestMock()
        request.all_data = {
            'serial': WebAuthnTokenClass.get_class_prefix() + '123'
        }
        fido2_auth(request, None)
        self.assertEqual(set(request.all_data.get(FIDO2PolicyAction.ALLOWED_TRANSPORTS)),
                         set(DEFAULT_ALLOWED_TRANSPORTS.split()))
        self.assertEqual(request.all_data.get(WebAuthnTokenClass.get_class_type() + '_' + PolicyAction.CHALLENGETEXT),
                         DEFAULT_CHALLENGE_TEXT_AUTH)

        # Not a WebAuthn token, policies are loaded regardless
        request = RequestMock()
        request.all_data = {
            'serial': 'FOO123'
        }
        fido2_auth(request, None)
        self.assertEqual(set(DEFAULT_ALLOWED_TRANSPORTS.split()),
                         set(request.all_data.get(FIDO2PolicyAction.ALLOWED_TRANSPORTS)))
        self.assertEqual(DEFAULT_CHALLENGE_TEXT_AUTH,
                         request.all_data.get(WebAuthnTokenClass.get_class_type() + '_' + PolicyAction.CHALLENGETEXT))

        # With policies
        allowed_transports = ALLOWED_TRANSPORTS
        challengetext = "Lorem Ipsum"
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTH,
            action=FIDO2PolicyAction.ALLOWED_TRANSPORTS + '=' + allowed_transports + ','
                   + WebAuthnTokenClass.get_class_type() + '_' + PolicyAction.CHALLENGETEXT + '=' + challengetext
        )
        request = RequestMock()
        request.all_data = {
            'user': 'foo'
        }
        fido2_auth(request, None)
        self.assertEqual(set(request.all_data.get(FIDO2PolicyAction.ALLOWED_TRANSPORTS)),
                         set(allowed_transports.split()))
        self.assertEqual(request.all_data.get(WebAuthnTokenClass.get_class_type() + '_' + PolicyAction.CHALLENGETEXT),
                         challengetext)

        # Delete policy
        delete_policy("WebAuthn")

    def test_26b_webauthn_auth_validate_check(self):
        class RequestMock(object):
            pass

        # Normal request
        request = RequestMock()
        request.all_data = {
            'user': 'foo',
            'pass': '1234'
        }
        fido2_auth(request, None)
        self.assertEqual(set(request.all_data.get(FIDO2PolicyAction.ALLOWED_TRANSPORTS)),
                         set(DEFAULT_ALLOWED_TRANSPORTS.split()))
        self.assertEqual(request.all_data.get(WebAuthnTokenClass.get_class_type() + '_' + PolicyAction.CHALLENGETEXT),
                         DEFAULT_CHALLENGE_TEXT_AUTH)

        # Request via serial
        request = RequestMock()
        request.all_data = {
            'user': 'foo',
            'serial': WebAuthnTokenClass.get_class_prefix() + '123',
            'pass': '1234'
        }
        fido2_auth(request, None)
        self.assertEqual(set(request.all_data.get(FIDO2PolicyAction.ALLOWED_TRANSPORTS)),
                         set(DEFAULT_ALLOWED_TRANSPORTS.split()))
        self.assertEqual(request.all_data.get(WebAuthnTokenClass.get_class_type() + '_' + PolicyAction.CHALLENGETEXT),
                         DEFAULT_CHALLENGE_TEXT_AUTH)

        # Not a WebAuthn token, policies are loaded regardless
        request = RequestMock()
        request.all_data = {
            'user': 'foo',
            'serial': 'FOO123',
            'pass': '1234'
        }
        fido2_auth(request, None)
        self.assertEqual(set(DEFAULT_ALLOWED_TRANSPORTS.split()),
                         set(request.all_data.get(FIDO2PolicyAction.ALLOWED_TRANSPORTS)))
        self.assertEqual(DEFAULT_CHALLENGE_TEXT_AUTH,
                         request.all_data.get(WebAuthnTokenClass.get_class_type() + '_' + PolicyAction.CHALLENGETEXT))

        # With policies
        allowed_transports = ALLOWED_TRANSPORTS
        challengetext = "Lorem Ipsum"
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTH,
            action=FIDO2PolicyAction.ALLOWED_TRANSPORTS + '=' + allowed_transports + ','
                   + WebAuthnTokenClass.get_class_type() + '_' + PolicyAction.CHALLENGETEXT + '=' + challengetext
        )
        request = RequestMock()
        request.all_data = {
            'user': 'foo',
            'pass': '1234'
        }
        fido2_auth(request, None)
        self.assertEqual(set(request.all_data.get(FIDO2PolicyAction.ALLOWED_TRANSPORTS)),
                         set(allowed_transports.split()))
        self.assertEqual(request.all_data.get(WebAuthnTokenClass.get_class_type() + '_' + PolicyAction.CHALLENGETEXT),
                         challengetext)

        # Delete policy
        delete_policy("WebAuthn")

    def test_26c_webauthn_auth_auth(self):
        class RequestMock(object):
            pass

        # Normal request
        request = RequestMock()
        request.all_data = {
            'username': 'foo',
            'password': '1234'
        }
        fido2_auth(request, None)
        self.assertEqual(set(request.all_data.get(FIDO2PolicyAction.ALLOWED_TRANSPORTS)),
                         set(DEFAULT_ALLOWED_TRANSPORTS.split()))
        self.assertEqual(request.all_data.get(WebAuthnTokenClass.get_class_type() + '_' + PolicyAction.CHALLENGETEXT),
                         DEFAULT_CHALLENGE_TEXT_AUTH)

        # With policies
        allowed_transports = ALLOWED_TRANSPORTS
        challengetext = "Lorem Ipsum"
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTH,
            action=FIDO2PolicyAction.ALLOWED_TRANSPORTS + '=' + allowed_transports + ','
                   + WebAuthnTokenClass.get_class_type() + '_' + PolicyAction.CHALLENGETEXT + '=' + challengetext
        )
        request = RequestMock()
        request.all_data = {
            'username': 'foo',
            'password': '1234'
        }
        fido2_auth(request, None)
        self.assertEqual(set(request.all_data.get(FIDO2PolicyAction.ALLOWED_TRANSPORTS)),
                         set(allowed_transports.split()))
        self.assertEqual(request.all_data.get(WebAuthnTokenClass.get_class_type() + '_' + PolicyAction.CHALLENGETEXT),
                         challengetext)

        # Delete policy
        delete_policy("WebAuthn")

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
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.REQ),
                         list())

        # Not a WebAuthn authorization
        request = RequestMock()
        request.all_data = {
            "user": "foo",
            "pass": ""
        }
        webauthntoken_authz(request, None)
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.REQ),
                         None)

        # With policies
        allowed_certs = "subject/.*Yubico.*/"
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTHZ,
            action=FIDO2PolicyAction.REQ + '=' + allowed_certs
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
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.REQ),
                         [allowed_certs])

        # Delete policy
        delete_policy("WebAuthn")

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
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.REQ),
                         list())

        # Not a WebAuthn authorization
        request = RequestMock()
        request.all_data = {
            "username": "foo",
            "password": ""
        }
        webauthntoken_authz(request, None)
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.REQ),
                         None)

        # With policies
        allowed_certs = "subject/.*Yubico.*/"
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTHZ,
            action=FIDO2PolicyAction.REQ + '=' + allowed_certs
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
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.REQ),
                         [allowed_certs])

        # Delete policy
        delete_policy("WebAuthn")

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
            fido2_enroll(request, None)

        # Malformed RP_ID
        set_policy(
            name="WebAuthn1",
            scope=SCOPE.ENROLL,
            action=FIDO2PolicyAction.RELYING_PARTY_ID + '=' + 'https://' + rp_id + ','
                   + FIDO2PolicyAction.RELYING_PARTY_NAME + '=' + rp_name
        )
        request = RequestMock()
        request.all_data = {
            "type": WebAuthnTokenClass.get_class_type()
        }
        with self.assertRaises(PolicyError):
            fido2_enroll(request, None)

        # Missing RP_NAME
        set_policy(
            name="WebAuthn1",
            scope=SCOPE.ENROLL,
            action=FIDO2PolicyAction.RELYING_PARTY_ID + '=' + rp_id
        )
        request = RequestMock()
        request.all_data = {
            "type": WebAuthnTokenClass.get_class_type()
        }
        with self.assertRaises(PolicyError):
            fido2_enroll(request, None)

        set_policy(
            name="WebAuthn1",
            scope=SCOPE.ENROLL,
            action=FIDO2PolicyAction.RELYING_PARTY_ID + '=' + rp_id + ','
                   + FIDO2PolicyAction.RELYING_PARTY_NAME + '=' + rp_name
        )

        # Normal request
        request = RequestMock()
        request.all_data = {
            "type": WebAuthnTokenClass.get_class_type()
        }
        fido2_enroll(request, None)
        self.assertEqual(rp_id, request.all_data.get(FIDO2PolicyAction.RELYING_PARTY_ID))
        self.assertEqual(rp_name, request.all_data.get(FIDO2PolicyAction.RELYING_PARTY_NAME))
        self.assertEqual(None, request.all_data.get(FIDO2PolicyAction.AUTHENTICATOR_ATTACHMENT))
        self.assertEqual([PUBLIC_KEY_CREDENTIAL_ALGORITHMS[x]
                          for x in PUBKEY_CRED_ALGORITHMS_ORDER
                          if x in DEFAULT_PUBLIC_KEY_CREDENTIAL_ALGORITHM_PREFERENCE],
                         request.all_data.get(FIDO2PolicyAction.PUBLIC_KEY_CREDENTIAL_ALGORITHMS))
        self.assertEqual(DEFAULT_AUTHENTICATOR_ATTESTATION_LEVEL,
                         request.all_data.get(FIDO2PolicyAction.AUTHENTICATOR_ATTESTATION_LEVEL))
        self.assertEqual(DEFAULT_AUTHENTICATOR_ATTESTATION_FORM,
                         request.all_data.get(FIDO2PolicyAction.AUTHENTICATOR_ATTESTATION_FORM))
        self.assertEqual(DEFAULT_CHALLENGE_TEXT_ENROLL,
                         request.all_data.get(WebAuthnTokenClass.get_class_type() + '_' + PolicyAction.CHALLENGETEXT))

        # Not a WebAuthn token: policy values are not loaded
        request = RequestMock()
        request.all_data = {
            "type": "footoken"
        }
        fido2_enroll(request, None)
        self.assertEqual(None, request.all_data.get(FIDO2PolicyAction.RELYING_PARTY_ID))
        self.assertEqual(None, request.all_data.get(FIDO2PolicyAction.RELYING_PARTY_NAME))
        self.assertEqual(None, request.all_data.get(FIDO2PolicyAction.AUTHENTICATOR_ATTACHMENT))
        self.assertEqual(None, request.all_data.get(FIDO2PolicyAction.PUBLIC_KEY_CREDENTIAL_ALGORITHMS))
        self.assertEqual(None, request.all_data.get(FIDO2PolicyAction.AUTHENTICATOR_ATTESTATION_LEVEL))
        self.assertEqual(None, request.all_data.get(FIDO2PolicyAction.AUTHENTICATOR_ATTESTATION_FORM))
        self.assertEqual(None,
                         request.all_data.get(WebAuthnTokenClass.get_class_type() + '_' + PolicyAction.CHALLENGETEXT))

        # With policies
        authenticator_attachment = AuthenticatorAttachmentType.CROSS_PLATFORM
        public_key_credential_algorithm_preference = 'ecdsa'
        authenticator_attestation_level = AttestationLevel.TRUSTED
        authenticator_attestation_form = AttestationForm.INDIRECT
        challengetext = "Lorem Ipsum"
        set_policy(
            name="WebAuthn2",
            scope=SCOPE.ENROLL,
            action=FIDO2PolicyAction.AUTHENTICATOR_ATTACHMENT + '=' + authenticator_attachment + ','
                   + FIDO2PolicyAction.PUBLIC_KEY_CREDENTIAL_ALGORITHMS + '='
                   + public_key_credential_algorithm_preference + ','
                   + FIDO2PolicyAction.AUTHENTICATOR_ATTESTATION_LEVEL + '=' + authenticator_attestation_level + ','
                   + FIDO2PolicyAction.AUTHENTICATOR_ATTESTATION_FORM + '=' + authenticator_attestation_form + ','
                   + WebAuthnTokenClass.get_class_type() + '_' + PolicyAction.CHALLENGETEXT + '=' + challengetext
        )
        request = RequestMock()
        request.all_data = {
            "type": WebAuthnTokenClass.get_class_type()
        }
        fido2_enroll(request, None)
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.AUTHENTICATOR_ATTACHMENT),
                         authenticator_attachment)
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.PUBLIC_KEY_CREDENTIAL_ALGORITHMS),
                         [PUBLIC_KEY_CREDENTIAL_ALGORITHMS[
                              public_key_credential_algorithm_preference
                          ]])
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.AUTHENTICATOR_ATTESTATION_LEVEL),
                         authenticator_attestation_level)
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.AUTHENTICATOR_ATTESTATION_FORM),
                         authenticator_attestation_form)
        self.assertEqual(request.all_data.get(WebAuthnTokenClass.get_class_type() + '_' + PolicyAction.CHALLENGETEXT),
                         challengetext)

        # Malformed policies
        request = RequestMock()
        request.all_data = {
            "type": WebAuthnTokenClass.get_class_type()
        }
        set_policy(
            name="WebAuthn2",
            scope=SCOPE.ENROLL,
            action=FIDO2PolicyAction.PUBLIC_KEY_CREDENTIAL_ALGORITHMS + '=' + 'b0rked'
        )
        with self.assertRaises(PolicyError):
            fido2_enroll(request, None)
        set_policy(
            name="WebAuthn2",
            scope=SCOPE.ENROLL,
            action=FIDO2PolicyAction.AUTHENTICATOR_ATTESTATION_LEVEL + '=' + 'b0rked'
        )
        with self.assertRaises(PolicyError):
            fido2_enroll(request, None)
        set_policy(
            name="WebAuthn2",
            scope=SCOPE.ENROLL,
            action=FIDO2PolicyAction.AUTHENTICATOR_ATTESTATION_FORM + '=' + 'b0rked'
        )
        with self.assertRaises(PolicyError):
            fido2_enroll(request, None)

        # Delete policy
        delete_policy("WebAuthn1")
        delete_policy("WebAuthn2")

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
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.TIMEOUT),
                         DEFAULT_TIMEOUT * 1000)
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT),
                         DEFAULT_USER_VERIFICATION_REQUIREMENT)
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.AUTHENTICATOR_SELECTION_LIST),
                         None)
        self.assertEqual(request.all_data.get('HTTP_ORIGIN'),
                         ORIGIN)

        # On a recognised request the origin comes from the environment, not from the parameter
        request = RequestMock()
        request.all_data = {
            "type": WebAuthnTokenClass.get_class_type(),
            "HTTP_ORIGIN": "https://attacker.example"
        }
        request.environ = {
            "HTTP_ORIGIN": ORIGIN
        }
        webauthntoken_request(request, None)
        self.assertEqual(request.all_data.get('HTTP_ORIGIN'), ORIGIN)

        # On a request this decorator does not recognise, the parameter is dropped rather than left in
        # place: the origin of an assertion may only ever come from the request itself.
        request = RequestMock()
        request.all_data = {
            "type": "footoken",
            "HTTP_ORIGIN": "https://attacker.example"
        }
        request.environ = {
            "HTTP_ORIGIN": ORIGIN
        }
        webauthntoken_request(request, None)
        self.assertIsNone(request.all_data.get('HTTP_ORIGIN'))

        # Not a WebAuthn token
        request = RequestMock()
        request.all_data = {
            "type": "footoken"
        }
        request.environ = {
            "HTTP_ORIGIN": ORIGIN
        }
        webauthntoken_request(request, None)
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.TIMEOUT),
                         None)
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT),
                         None)
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.AUTHENTICATOR_SELECTION_LIST),
                         None)
        self.assertEqual(request.all_data.get('HTTP_ORIGIN'),
                         None)

        # With policies
        timeout = 30
        user_verification_requirement = UserVerificationLevel.REQUIRED
        authenticator_selection_list = 'foo bar baz'
        set_policy(
            name="WebAuthn",
            scope=SCOPE.ENROLL,
            action=FIDO2PolicyAction.TIMEOUT + '=' + str(timeout) + ','
                   + FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT + '=' + user_verification_requirement + ','
                   + FIDO2PolicyAction.AUTHENTICATOR_SELECTION_LIST + '=' + authenticator_selection_list
        )
        request = RequestMock()
        request.all_data = {
            "type": WebAuthnTokenClass.get_class_type()
        }
        request.environ = {
            "HTTP_ORIGIN": ORIGIN
        }
        webauthntoken_request(request, None)
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.TIMEOUT),
                         timeout * 1000)
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT),
                         user_verification_requirement)
        self.assertEqual(set(request.all_data.get(FIDO2PolicyAction.AUTHENTICATOR_SELECTION_LIST)),
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
            action=FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT + '=' + 'b0rked'
        )
        with self.assertRaises(PolicyError):
            webauthntoken_request(request, None)

        # Delete policy
        delete_policy("WebAuthn")

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
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.TIMEOUT),
                         DEFAULT_TIMEOUT * 1000)
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT),
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
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.TIMEOUT),
                         DEFAULT_TIMEOUT * 1000)
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT),
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
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.TIMEOUT),
                         None)
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT),
                         None)
        self.assertEqual(request.all_data.get('HTTP_ORIGIN'),
                         None)

        # With policies
        timeout = 30
        user_verification_requirement = UserVerificationLevel.REQUIRED
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTH,
            action=FIDO2PolicyAction.TIMEOUT + '=' + str(timeout) + ','
                   + FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT + '=' + user_verification_requirement
        )
        request = RequestMock()
        request.all_data = {
            "user": "foo"
        }
        request.environ = {
            "HTTP_ORIGIN": ORIGIN
        }
        webauthntoken_request(request, None)
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.TIMEOUT),
                         timeout * 1000)
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT),
                         user_verification_requirement)

        # Delete policy
        delete_policy("WebAuthn")

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
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.TIMEOUT),
                         DEFAULT_TIMEOUT * 1000)
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT),
                         DEFAULT_USER_VERIFICATION_REQUIREMENT)
        self.assertEqual(request.all_data.get('HTTP_ORIGIN'),
                         ORIGIN)

        # With policies
        timeout = 30
        user_verification_requirement = UserVerificationLevel.REQUIRED
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTH,
            action=FIDO2PolicyAction.TIMEOUT + '=' + str(timeout) + ','
                   + FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT + '=' + user_verification_requirement
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
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.TIMEOUT),
                         timeout * 1000)
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT),
                         user_verification_requirement)

        # Delete policy
        delete_policy("WebAuthn")

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
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.AUTHENTICATOR_SELECTION_LIST),
                         None)
        self.assertEqual(request.all_data.get('HTTP_ORIGIN'),
                         ORIGIN)

        # With policies
        authenticator_selection_list = 'foo bar baz'
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTHZ,
            action=FIDO2PolicyAction.AUTHENTICATOR_SELECTION_LIST + '=' + authenticator_selection_list
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
        self.assertEqual(set(request.all_data.get(FIDO2PolicyAction.AUTHENTICATOR_SELECTION_LIST)),
                         set(authenticator_selection_list.split()))

        # Delete policy
        delete_policy("WebAuthn")

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
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.TIMEOUT),
                         DEFAULT_TIMEOUT * 1000)
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT),
                         DEFAULT_USER_VERIFICATION_REQUIREMENT)
        self.assertEqual(request.all_data.get('HTTP_ORIGIN'),
                         ORIGIN)

        # With policies
        timeout = 30
        user_verification_requirement = UserVerificationLevel.REQUIRED
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTH,
            action=FIDO2PolicyAction.TIMEOUT + '=' + str(timeout) + ','
                   + FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT + '=' + user_verification_requirement
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
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.TIMEOUT),
                         timeout * 1000)
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT),
                         user_verification_requirement)

        # Delete policy
        delete_policy("WebAuthn")

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
        self.assertEqual(request.all_data.get(FIDO2PolicyAction.AUTHENTICATOR_SELECTION_LIST),
                         None)
        self.assertEqual(request.all_data.get('HTTP_ORIGIN'),
                         ORIGIN)

        # With policies
        authenticator_selection_list = 'foo bar baz'
        set_policy(
            name="WebAuthn",
            scope=SCOPE.AUTHZ,
            action=FIDO2PolicyAction.AUTHENTICATOR_SELECTION_LIST + '=' + authenticator_selection_list
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
        self.assertEqual(set(request.all_data.get(FIDO2PolicyAction.AUTHENTICATOR_SELECTION_LIST)),
                         set(authenticator_selection_list.split()))

        # Delete policy
        delete_policy("WebAuthn")
