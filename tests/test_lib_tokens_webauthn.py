"""
This test file tests the lib.tokens.webauthntoken, along with lib.tokens.webauthn.
This depends on lib.tokenclass
"""

from .base import MyTestCase
from privacyidea.lib.tokens.webauthntoken import WebAuthnTokenClass, WEBAUTHNACTION
from privacyidea.lib.token import init_token
from privacyidea.lib.policy import set_policy, SCOPE

RP_ID = 'example.com'
RP_NAME = 'ACME'


class WebAuthnTokenTestCase(MyTestCase):

    def test_00_users(self):
        self.setUp_user_realms()

        set_policy(name="WebAuthn",
                   scope=SCOPE.ENROLL,
                   action=WEBAUTHNACTION.RELYING_PARTY_NAME+"="+RP_NAME+","
                         +WEBAUTHNACTION.RELYING_PARTY_ID+"="+RP_ID)

    def test_01_create_token(self):
        pin = "1234"

        #
        # Init step 1
        #

        token = init_token({'type': 'webauthn',
                            'pin': pin})
        serial = token.token.serial

        self.assertEqual(token.type, "webauthn")
        self.assertEqual(WebAuthnTokenClass.get_class_prefix(), "WAN")
        self.assertEqual(WebAuthnTokenClass.get_class_info().get('type'), "webauthn")
        self.assertEqual(WebAuthnTokenClass.get_class_info('type'), "webauthn")
