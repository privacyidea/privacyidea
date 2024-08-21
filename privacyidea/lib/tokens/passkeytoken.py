import logging
from hashlib import sha512, sha256

from webauthn import (generate_registration_options,
                      options_to_json, verify_registration_response, verify_authentication_response)
from webauthn.helpers import bytes_to_base64url, base64url_to_bytes
from webauthn.helpers.cose import COSEAlgorithmIdentifier
from webauthn.helpers.exceptions import InvalidRegistrationResponse, InvalidAuthenticationResponse
from webauthn.helpers.structs import (AttestationConveyancePreference, AuthenticatorAttachment,
                                      AuthenticatorSelectionCriteria, ResidentKeyRequirement)

from privacyidea.api.lib.utils import get_optional, get_required
from privacyidea.lib import _
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.config import get_from_config
from privacyidea.lib.crypto import geturandom
from privacyidea.lib.decorators import check_token_locked
from privacyidea.lib.error import EnrollmentError, ParameterError
from privacyidea.lib.log import log_with
from privacyidea.lib.policy import ACTION
from privacyidea.lib.tokenclass import TokenClass, ROLLOUTSTATE
from privacyidea.lib.tokens.webauthntoken import WEBAUTHNCONFIG, WEBAUTHNACTION, WEBAUTHNINFO
from privacyidea.models import Challenge

log = logging.getLogger(__name__)


class PasskeyTokenClass(TokenClass):

    def __init__(self, db_token):
        super().__init__(db_token)
        self.set_type(self.get_class_type())

    @staticmethod
    def get_class_type():
        return "passkey"

    @staticmethod
    def get_class_prefix():
        return "PIPK"

    @staticmethod
    def _get_nonce():
        return geturandom(32)

    @staticmethod
    @log_with(log)
    def get_class_info(key=None, ret='all'):
        """
        """
        res = {
            "type": "passkey",
            "title": "Passkey",
            "description": _("Passkey: A secret stored on one’s devices, unlocked with biometrics."),
            "init": {},
            'config': {},
            'user': ['enroll'],
            'ui_enroll': ["admin", "user"]
        }
        return res.get(key, {}) if key else res

    def _get_message(self, options):
        challenge_text = get_optional(options, f"{self.get_class_type()}_{ACTION.CHALLENGETEXT}")
        return challenge_text.format(self.token.description) if challenge_text else ''

    @log_with(log)
    def get_init_detail(self, params=None, user=None):
        """
        """
        if self.token.rollout_state == ROLLOUTSTATE.CLIENTWAIT:
            # Create the initial registration data and a challenge in the database
            response_detail = TokenClass.get_init_detail(self, params, user)
            if not user:
                raise ParameterError("User must be provided for passkey enrollment!")

            nonce = self._get_nonce()

            challenge_validity = int(get_from_config(WEBAUTHNCONFIG.CHALLENGE_VALIDITY_TIME,
                                                     get_from_config('DefaultChallengeValidityTime', 120)))
            challenge = Challenge(serial=self.token.serial,
                                  transaction_id=get_optional(params, 'transaction_id'),
                                  challenge=bytes_to_base64url(nonce),
                                  data=None,
                                  session=get_optional(params, 'session'),
                                  validitytime=challenge_validity)
            challenge.save()
            # To avoid registering the same authenticator multiple times, get other passkey token of the user
            # and set their credential ids in exclude_credentials
            """
            credential_ids = []
            existing_token = get_tokens(tokentype=self.type, user=self.user)
            for t in existing_token:
                if t.token.rollout_state != ROLLOUTSTATE.CLIENTWAIT:
                    credential_id = t.decrypt_otpkey()
                    credential_ids.append()
            """
            registration_options = generate_registration_options(
                rp_id=get_required(params, WEBAUTHNACTION.RELYING_PARTY_ID),
                rp_name=get_required(params, WEBAUTHNACTION.RELYING_PARTY_NAME),
                user_id=self.token.serial.encode("utf-8"),
                user_name=user.login,
                user_display_name=str(user),
                # Attestation=None is recommended for passkeys
                attestation=AttestationConveyancePreference.NONE,
                authenticator_selection=AuthenticatorSelectionCriteria(
                    authenticator_attachment=AuthenticatorAttachment.PLATFORM,
                    resident_key=ResidentKeyRequirement.REQUIRED,
                ),
                challenge=nonce,
                # exclude_credentials=credential_ids,
                supported_pub_key_algs=[COSEAlgorithmIdentifier.ECDSA_SHA_256,
                                        COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256],
                timeout=12000,
            )
            options_json = options_to_json(registration_options)
            response_detail["passkey_registration"] = options_json
            response_detail["transaction_id"] = challenge.transaction_id

            # Add RP ID and Name to the token info
            self.add_tokeninfo(WEBAUTHNINFO.RELYING_PARTY_ID, registration_options.rp.id)
            self.add_tokeninfo(WEBAUTHNINFO.RELYING_PARTY_NAME, registration_options.rp.name)

        elif self.token.rollout_state == "":
            # This is the second step of the init request: The registration is completed.
            response_detail = {
                "webAuthnRegisterResponse": {"subject": self.token.description}
            }

        else:
            response_detail = {}
        return response_detail

    def update(self, param, reset_failcount=True):
        """
        """
        response_detail = {"details": {"serial": self.token.serial}}

        attestation = get_optional(param, "attestationObject")
        client_data = get_optional(param, "clientDataJSON")

        if not (attestation and client_data) and not self.token.rollout_state == ROLLOUTSTATE.CLIENTWAIT:
            self.token.rollout_state = ROLLOUTSTATE.CLIENTWAIT
            # Set the description in the first enrollment step
            if "description" in param:
                self.set_description(get_optional(param, "description", default=""))

        elif attestation and client_data and self.token.rollout_state == ROLLOUTSTATE.CLIENTWAIT:
            # Finalize the registration by verifying the registration data from the authenticator
            cred_id = get_required(param, "id")
            cred_id_raw = get_required(param, "rawId")
            authenticator_attachment = get_required(param, "authenticatorAttachment")
            transaction_id = get_required(param, "transaction_id")
            serial = self.token.serial
            challenge_list = [challenge for challenge in get_challenges(serial=serial, transaction_id=transaction_id)
                              if challenge.is_valid()]

            if not len(challenge_list):
                raise EnrollmentError(f"The enrollment challenge does not exist or has timed out for {serial}")
            try:
                registration_verification = verify_registration_response(
                    credential={
                        "id": cred_id,
                        "rawId": cred_id_raw,
                        "response": {
                            "attestationObject": attestation,
                            "clientDataJSON": client_data,
                            "transports": ["internal"],
                        },
                        "type": "public-key",
                        "clientExtensionResults": {},
                        "authenticatorAttachment": authenticator_attachment,
                    },
                    expected_challenge=challenge_list[0].challenge.encode("utf-8"),
                    expected_origin=get_required(param, "HTTP_ORIGIN"),
                    expected_rp_id=get_required(param, WEBAUTHNACTION.RELYING_PARTY_ID),
                    require_user_verification=True,
                )
            except InvalidRegistrationResponse as ex:
                log.error(f"Invalid registration response: {ex}")
                raise EnrollmentError(f"Invalid registration response: {ex}")

            # Verification successful, set the token to enrolled and save information returned by the authenticator
            self.token.rollout_state = ROLLOUTSTATE.ENROLLED
            public_key_enc = bytes_to_base64url(registration_verification.credential_public_key)
            self.add_tokeninfo("public_key", public_key_enc)
            self.add_tokeninfo("aaguid", registration_verification.aaguid)
            self.add_tokeninfo("sign_count", registration_verification.sign_count)
            # Protect the credential_id by setting it as the token secret
            self.set_otpkey(bytes_to_base64url(registration_verification.credential_id))
            # Add a hash of the credential_id to the token info to be able to find
            # the token faster given the credential_id
            h = sha256(registration_verification.credential_id)
            self.add_tokeninfo("credential_id_hash", h.hexdigest())

        return response_detail

    @check_token_locked
    def check_otp(self, otpval, counter=None, window=None, options=None):
        """
        :param otpval: Unused for this token type
        :type otpval: None
        :param counter: The authentication counter
        :type counter: int
        :param window: Unused for this token type
        :type window: None
        :param options: Contains the data from the client, along with policy configurations.
        :type options: dict
        :return: A numerical value where values larger than zero indicate success.
        :rtype: int
        """

        credential_id = bytes_to_base64url(self.token.get_otpkey().getKey())
        rp_id = self.get_tokeninfo(WEBAUTHNINFO.RELYING_PARTY_ID)
        try:
            res = verify_authentication_response(
                credential={
                    "id": credential_id,
                    "rawId": credential_id,
                    "response": {
                        "authenticatorData": get_required(options, "authenticatorData"),
                        "clientDataJSON": get_required(options, "clientDataJSON"),
                        "signature": get_required(options, "signature"),
                        "userHandle": get_required(options, "userHandle"),
                    },
                    "type": "public-key",
                    "authenticatorAttachment": "cross-platform",
                    "clientExtensionResults": {},
                },
                expected_challenge=get_required(options, "challenge").encode("utf-8"),
                expected_rp_id=rp_id,
                expected_origin=get_required(options, "HTTP_ORIGIN"),
                require_user_verification=True,
                credential_current_sign_count=int(self.get_tokeninfo("sign_count")),
                credential_public_key=base64url_to_bytes(self.get_tokeninfo("public_key")),
            )
        except InvalidAuthenticationResponse as ex:
            log.info(f"Passkey authentication failed: {ex}")
            print(f"Passkey authentication failed: {ex}")
            return -1

        self.add_tokeninfo("sign_count", res.new_sign_count)
        return 1
