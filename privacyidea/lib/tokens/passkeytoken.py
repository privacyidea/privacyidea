# (c) NetKnights GmbH 2024,  https://netknights.it
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-FileCopyrightText: 2024 Nils Behlen <nils.behlen@netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
#
import json
import logging
from hashlib import sha256

import cryptography.x509
from cryptography.hazmat._oid import NameOID
from cryptography.hazmat.primitives import serialization
from cryptography.x509 import Certificate, NameAttribute
from flask_babel import lazy_gettext
from webauthn import (generate_registration_options,
                      options_to_json, verify_registration_response, verify_authentication_response)
from webauthn.authentication.verify_authentication_response import VerifiedAuthentication
from webauthn.helpers import bytes_to_base64url, base64url_to_bytes, parse_attestation_object
from webauthn.helpers.cose import COSEAlgorithmIdentifier
from webauthn.helpers.exceptions import InvalidRegistrationResponse, InvalidAuthenticationResponse, InvalidJSONStructure
from webauthn.helpers.structs import (AttestationConveyancePreference, AuthenticatorSelectionCriteria,
                                      ResidentKeyRequirement,
                                      PublicKeyCredentialDescriptor, UserVerificationRequirement, AttestationObject,
                                      PublicKeyCredentialCreationOptions)
from webauthn.registration.verify_registration_response import VerifiedRegistration

from privacyidea.api.lib.utils import get_optional, get_required, get_required_one_of, get_optional_one_of
from privacyidea.lib import _
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.config import get_from_config
from privacyidea.lib.crypto import geturandom, get_rand_digit_str
from privacyidea.lib.decorators import check_token_locked
from privacyidea.lib.error import EnrollmentError, ParameterError, ERROR
from privacyidea.lib.log import log_with
from privacyidea.lib.policy import ACTION, SCOPE
from privacyidea.lib.tokenclass import TokenClass, ROLLOUTSTATE, AUTHENTICATIONMODE
from privacyidea.lib.tokens.webauthntoken import WEBAUTHNCONFIG, WEBAUTHNACTION, WEBAUTHNINFO
from privacyidea.models import Challenge

log = logging.getLogger(__name__)


class PasskeyAction:
    AttestationConveyancePreference = "passkey_attestation_conveyance_preference"


class PasskeyTokenClass(TokenClass):
    """
    Implements a token class for passkeys (fido2). This is very similar to the webauthn token class, but uses a lib
    for registration and authentication. It is less configurable, always requires resident key and uses excluded
    credentials by default.
    It shares the following policy configuration with the webauthn token class:
        - RP_ID
        - RP_NAME
        - USER_VERIFICATION_REQUIREMENT (default: PREFERRED)
        - PUBLIC_KEY_CREDENTIAL_ALGORITHMS (default: ECDSA_SHA_256, RSASSA_PKCS1_v1_5_SHA_256)
    """

    mode = [AUTHENTICATIONMODE.CHALLENGE]

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
        return bytes_to_base64url(geturandom(32))

    @staticmethod
    @log_with(log)
    def get_class_info(key=None, ret='all'):
        """
        """
        res = {
            "type": "passkey",
            "title": "Passkey",
            "description": _("Passkey: A secret stored on a device, unlocked with biometrics."),
            "init": {},
            'config': {},
            'user': ['enroll'],
            'ui_enroll': ["admin", "user"],
            'policy': {
                SCOPE.AUTH: {
                    ACTION.CHALLENGETEXT: {
                        'type': 'str',
                        'desc': _("Alternative challenge message to use when authenticating with a passkey."
                                  "You can also use tags for replacement, "
                                  "check the documentation for more details.")
                    }
                },
                SCOPE.ENROLL: {
                    PasskeyAction.AttestationConveyancePreference: {
                        'type': 'str',
                        'desc': _("Request attestation from the authenticator during the registration. The attestation "
                                  "certificate will be saved in the token info. The default value is 'none'."),
                        'value': [v for v in AttestationConveyancePreference],
                        'group': 'WebAuthn'
                    }
                }
            }
        }
        return res.get(key, {}) if key else res

    @log_with(log)
    def get_init_detail(self, params=None, user=None):
        """
        First step of enrollment: Returns the registration data for the passkey token.
        Also creates a challenge in the database which has to be verified in the second step.
        The following parameters are required in params:
        - "webauthn_relying_party_id" (WEBAUTHNACTION.RELYING_PARTY_ID)
        - "webauthn_relying_party_name" (WEBAUTHNACTION.RELYING_PARTY_NAME)

        The following parameters are optional in params to customize the registration:
        - "registered_credential_ids": A list of credential IDs that are already registered with the user.
        - WEBAUTHNACTION.PUBLIC_KEY_CREDENTIAL_ALGORITHMS (default: ECDSA_SHA_256, RSASSA_PKCS1_v1_5_SHA_256)
        - WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT (default: PREFERRED)
        - PasskeyAction.AttestationConveyancePreference (default: NONE)
        """
        if self.token.rollout_state == ROLLOUTSTATE.CLIENTWAIT:
            token_user = self.user or user
            if not token_user:
                raise ParameterError("User must be provided for passkey enrollment!",
                                     id=ERROR.PARAMETER_USER_MISSING)

            rp_id = get_required(params, WEBAUTHNACTION.RELYING_PARTY_ID)
            rp_name = get_required(params, WEBAUTHNACTION.RELYING_PARTY_NAME)

            response_detail: dict = TokenClass.get_init_detail(self, params, token_user)

            nonce_base64 = self._get_nonce()
            challenge_validity: int = int(get_from_config(WEBAUTHNCONFIG.CHALLENGE_VALIDITY_TIME,
                                                          get_from_config('DefaultChallengeValidityTime', 120)))
            challenge: Challenge = Challenge(serial=self.token.serial,
                                             transaction_id=None,  # will be generated by the challenge
                                             challenge=nonce_base64,
                                             data=None,
                                             session="",
                                             validitytime=challenge_validity)
            challenge.save()

            # Excluded Credentials
            reg_ids = get_optional(params, "registered_credential_ids") or []
            registered_credential_ids: list[bytes] = [base64url_to_bytes(cred_id) for cred_id in reg_ids]
            excluded_credentials: list[PublicKeyCredentialDescriptor] = ([PublicKeyCredentialDescriptor(id=cred)
                                                                          for cred in registered_credential_ids])

            # Key Algorithms
            pub_key_algorithms = get_optional(params, WEBAUTHNACTION.PUBLIC_KEY_CREDENTIAL_ALGORITHMS,
                                              default=[COSEAlgorithmIdentifier.ECDSA_SHA_256,
                                                       COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256])

            # User Verification
            user_verification: UserVerificationRequirement = UserVerificationRequirement.PREFERRED
            if WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT in params:
                user_verification = UserVerificationRequirement(params[WEBAUTHNACTION.USER_VERIFICATION_REQUIREMENT])

            # Attestation (None is recommended for passkeys)
            attestation: AttestationConveyancePreference = AttestationConveyancePreference.NONE
            if PasskeyAction.AttestationConveyancePreference in params:
                attestation = AttestationConveyancePreference(params[PasskeyAction.AttestationConveyancePreference])

            registration_options: PublicKeyCredentialCreationOptions = generate_registration_options(
                rp_id=rp_id,
                rp_name=rp_name,
                user_name=token_user.login,
                user_display_name=token_user.login,
                attestation=attestation,
                authenticator_selection=AuthenticatorSelectionCriteria(
                    resident_key=ResidentKeyRequirement.REQUIRED,
                    user_verification=user_verification,
                ),
                challenge=base64url_to_bytes(nonce_base64),
                exclude_credentials=excluded_credentials,
                supported_pub_key_algs=pub_key_algorithms,
                timeout=12000,
            )

            options_json: str = options_to_json(registration_options)
            response_detail["passkey_registration"] = json.loads(options_json)
            response_detail["transaction_id"] = challenge.transaction_id

            # Add RP ID and name to the token info
            self.add_tokeninfo(WEBAUTHNINFO.RELYING_PARTY_ID, registration_options.rp.id)
            self.add_tokeninfo(WEBAUTHNINFO.RELYING_PARTY_NAME, registration_options.rp.name)
            self.add_tokeninfo("user_id", bytes_to_base64url(registration_options.user.id))
        else:
            response_detail = {}
        return response_detail

    def update(self, param, reset_failcount=True):
        """
        Second step of enrollment: Verify the registration data from the authenticator with challenge from the database.
        If the registration is successful, the token is set to enrolled and metadata is written to the token info.
        To complete the registration, the following parameters are required in param:
        - attestationObject
        - clientDataJSON
        - credential_id
        - rawId
        - authenticatorAttachment
        - transaction_id
        - HTTP_ORIGIN
        - WEBAUTHNACTION.RELYING_PARTY_ID ("webauthn_relying_party_id")
        """
        response_detail = {"details": {"serial": self.token.serial}}

        attestation = get_optional(param, "attestationObject")
        print(f"attestation: {attestation}")
        client_data = get_optional(param, "clientDataJSON")
        print(f"client_data: {client_data}")

        if not (attestation and client_data) and not self.token.rollout_state == ROLLOUTSTATE.CLIENTWAIT:
            self.token.rollout_state = ROLLOUTSTATE.CLIENTWAIT
            # Set the description in the first enrollment step
            if "description" in param:
                self.set_description(param["description"])

        elif attestation and client_data and self.token.rollout_state == ROLLOUTSTATE.CLIENTWAIT:
            # Finalize the registration by verifying the registration data from the authenticator
            cred_id = get_required(param, "credential_id")
            cred_id_raw = get_required(param, "rawId")
            authenticator_attachment = get_required(param, "authenticatorAttachment")
            transaction_id = get_required(param, "transaction_id")
            expected_rp_id = get_required(param, WEBAUTHNACTION.RELYING_PARTY_ID)
            expected_origin = get_required(param, "HTTP_ORIGIN")

            serial = self.token.serial
            challenge_list = [challenge for challenge in get_challenges(serial=serial, transaction_id=transaction_id)
                              if challenge.is_valid()]

            if not len(challenge_list):
                raise EnrollmentError(f"The enrollment challenge does not exist or has timed out for {serial}")
            try:
                registration_verification: VerifiedRegistration = verify_registration_response(
                    credential={
                        "id": cred_id,
                        "rawId": cred_id_raw,
                        "response": {
                            "attestationObject": attestation,
                            "clientDataJSON": client_data
                        },
                        "type": "public-key",
                        "authenticatorAttachment": authenticator_attachment,
                    },
                    expected_challenge=challenge_list[0].challenge.encode("utf-8"),
                    expected_origin=expected_origin,
                    expected_rp_id=expected_rp_id,
                )
            except InvalidRegistrationResponse as ex:
                log.error(f"Invalid registration response: {ex}")
                raise EnrollmentError(f"Invalid registration response: {ex}")
            except InvalidJSONStructure as ex:
                log.error(f"Invalid JSON structure: {ex}")
                raise EnrollmentError(f"Invalid JSON structure: {ex}")

            print(f"device type: {registration_verification.credential_device_type}")
            print(f"backed up: {registration_verification.credential_backed_up}")
            # Verification successful, set the token to enrolled and save information returned by the authenticator
            self.token.rollout_state = ROLLOUTSTATE.ENROLLED
            public_key_enc: str = bytes_to_base64url(registration_verification.credential_public_key)
            self.add_tokeninfo("public_key", public_key_enc)
            self.add_tokeninfo("aaguid", registration_verification.aaguid)
            self.add_tokeninfo("sign_count", registration_verification.sign_count)
            # Protect the credential_id by setting it as the token secret
            self.set_otpkey(bytes_to_base64url(registration_verification.credential_id))
            # Add a hash of the credential_id to the token info to be able to find
            # the token faster given the credential_id
            self.add_tokeninfo("credential_id_hash", sha256(registration_verification.credential_id).hexdigest())

            # If the attestation object contains a x5c certificate, save it in the token info
            # and set the description to the CN if it is not already set
            if registration_verification.attestation_object:
                att_obj: AttestationObject = parse_attestation_object(registration_verification.attestation_object)
                if att_obj.att_stmt and att_obj.att_stmt.x5c:
                    att_cert: Certificate = cryptography.x509.load_der_x509_certificate(att_obj.att_stmt.x5c[0])
                    pem: str = (att_cert.public_bytes(serialization.Encoding.PEM)
                                .decode("utf-8").replace("\n", ""))
                    self.add_tokeninfo("attestation_certificate", pem)
                    if not self.token.description:
                        attributes: list[NameAttribute] = att_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
                        if attributes:
                            self.set_description(attributes[0].value)
        return response_detail

    @check_token_locked
    def check_otp(self, otpval, counter=None, window=None, options=None):
        """
        :param otpval: Unused for this token type
        :type otpval: None
        :param counter: Unused for this token type
        :type counter: int
        :param window: Unused for this token type
        :type window: None
        :param options: Contains the data from the client, along with policy configurations.
                        For compatibility with the WebAuthnTokenClass, some keys can have multiple names.
                        The following keys are required:
                        - "challenge"
                        - "authenticatorData" or "authenticatordata"
                        - "clientDataJSON" or "clientdata"
                        - "signature" or "signaturedata"
                        - "userHandle" or "userhandle"
                        - "HTTP_ORIGIN"
                        The following keys are optional:
                        - "webauthn_user_verification_requirement", defaults to preferred

        :type options: dict
        :return: A numerical value where values larger than zero indicate success.
        :rtype: int
        """
        authenticator_data = get_required_one_of(options, ["authenticatorData", "authenticatordata"])
        client_data_json = get_required_one_of(options, ["clientDataJSON", "clientdata"])
        signature = get_required_one_of(options, ["signature", "signaturedata"])
        user_handle = get_optional_one_of(options, ["userHandle", "userhandle"])
        expected_challenge = get_required(options, "challenge").encode("utf-8")
        expected_origin = get_required(options, "HTTP_ORIGIN")
        user_verification = get_optional(options, "user_verification", "preferred")

        credential_id = self.token.get_otpkey().getKey().decode("utf-8")
        rp_id = self.get_tokeninfo(WEBAUTHNINFO.RELYING_PARTY_ID)

        try:
            verified_authentication: VerifiedAuthentication = verify_authentication_response(
                credential={
                    "id": credential_id,
                    "rawId": credential_id,
                    "response": {
                        "authenticatorData": authenticator_data,
                        "clientDataJSON": client_data_json,
                        "signature": signature,
                        "userHandle": user_handle,
                    },
                    "type": "public-key",
                    "authenticatorAttachment": "cross-platform",
                    "clientExtensionResults": {},
                },
                expected_challenge=expected_challenge,
                expected_rp_id=rp_id,
                expected_origin=expected_origin,
                require_user_verification=user_verification == "required",
                credential_current_sign_count=int(self.get_tokeninfo("sign_count")),
                credential_public_key=base64url_to_bytes(self.get_tokeninfo("public_key")),
            )
        except InvalidAuthenticationResponse as ex:
            log.info(f"Passkey authentication failed: {ex}")
            return -1

        self.add_tokeninfo("sign_count", verified_authentication.new_sign_count)
        return 1

    @classmethod
    def get_default_challenge_text_auth(cls) -> str:
        return str(lazy_gettext("Please authenticate with your passkey!"))

    @classmethod
    def get_default_challenge_text_register(cls) -> str:
        return str(lazy_gettext("Please confirm the registration your passkey!"))

    def create_challenge(self, transactionid=None, options=None):
        """
        Requires the key "webauthn_relying_party_id" (WEBAUTHNACTION.RELYING_PARTY_ID) in the option dict.
        Returns a fido2 challenge that is not bound to a user/credential. The user has to be resolved by
        the credential_id that returned with the response to this challenge.
        The returned dict has the format:
        {
            "transaction_id": "12345678901234567890",
            "challenge": <32 random bytes base64url encoded>,
            "rpId": "example.com",
            "message": "Please authenticate with your Passkey!"
        }
        The challenge nonce is encoded in base64url.
        """
        rp_id = get_required(options, WEBAUTHNACTION.RELYING_PARTY_ID)
        challenge = bytes_to_base64url(geturandom(32))
        transaction_id = get_rand_digit_str(20)
        message = PasskeyTokenClass.get_default_challenge_text_auth()
        db_challenge = Challenge(self.get_serial(), transaction_id=transaction_id, challenge=challenge)
        db_challenge.save()
        ret = {
            "transaction_id": transaction_id,
            "challenge": challenge,
            "message": message,
            "rpId": rp_id
        }
        return ret

    @log_with(log)
    def use_for_authentication(self, options):
        return self.is_active()

    @classmethod
    def is_multichallenge_enrollable(cls):
        return True
