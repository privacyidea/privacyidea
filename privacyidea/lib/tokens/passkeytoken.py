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
from privacyidea.lib import fido2
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.config import get_from_config
from privacyidea.lib.decorators import check_token_locked
from privacyidea.lib.error import EnrollmentError, ParameterError, ERROR
from privacyidea.lib.fido2.config import FIDO2ConfigOptions
from privacyidea.lib.fido2.policy_action import FIDO2PolicyAction, PasskeyAction
from privacyidea.lib.fido2.token_info import FIDO2TokenInfo
from privacyidea.lib.fido2.util import hash_credential_id, save_credential_id_hash
from privacyidea.lib.log import log_with
from privacyidea.lib.policy import ACTION, SCOPE
from privacyidea.lib.tokenclass import TokenClass, ROLLOUTSTATE, AUTHENTICATIONMODE, CLIENTMODE
from privacyidea.models import Challenge

log = logging.getLogger(__name__)


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
    client_mode = CLIENTMODE.WEBAUTHN

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
    @log_with(log)
    def get_class_info(key=None, ret='all'):
        """
        Returns a dict with information about the passkey token class and related policy options.
        The parameter ret can be used to specify the "section" of the information that should be returned.
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
                    },
                    PasskeyAction.EnableTriggerByPIN: {
                        'type': 'bool',
                        'desc': _("When enabled, passkey token can be triggered with the PIN or via the "
                                  "/validate/triggerchallenge endpoint. For privacyIDEA plugins, "
                                  "this is not recommended. It is advised to use a condition, for example on a "
                                  "user-agent, with this policy."),
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
        - "webauthn_relying_party_id" (FIDO2PolicyAction.RELYING_PARTY_ID)
        - "webauthn_relying_party_name" (FIDO2PolicyAction.RELYING_PARTY_NAME)

        The following parameters are optional in params to customize the registration:
        - "registered_credential_ids": A list of credential IDs that are already registered with the user.
        - FIDO2PolicyAction.PUBLIC_KEY_CREDENTIAL_ALGORITHMS (default: ECDSA_SHA_256, RSASSA_PKCS1_v1_5_SHA_256)
        - FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT (default: PREFERRED)
        - PasskeyAction.AttestationConveyancePreference (default: NONE)
        """
        if self.token.rollout_state == ROLLOUTSTATE.CLIENTWAIT:
            token_user = self.user or user
            if not token_user:
                raise ParameterError("User must be provided for passkey enrollment!",
                                     id=ERROR.PARAMETER_USER_MISSING)

            rp_id = get_required(params, FIDO2PolicyAction.RELYING_PARTY_ID)
            rp_name = get_required(params, FIDO2PolicyAction.RELYING_PARTY_NAME)

            response_detail: dict = TokenClass.get_init_detail(self, params, token_user)
            response_detail['rollout_state'] = self.token.rollout_state
            nonce_base64 = fido2.challenge.get_fido2_nonce()
            challenge_validity: int = int(get_from_config(FIDO2ConfigOptions.CHALLENGE_VALIDITY_TIME,
                                                          get_from_config('DefaultChallengeValidityTime', 120)))
            challenge: Challenge = Challenge(serial=self.token.serial,
                                             transaction_id=None,  # will be generated by the challenge
                                             challenge=nonce_base64,
                                             data=None,
                                             session="",
                                             validitytime=challenge_validity)
            challenge.save()

            # User ID
            fido2_user_id = base64url_to_bytes(
                token_user.attributes[
                    FIDO2TokenInfo.USER_ID]) if FIDO2TokenInfo.USER_ID in token_user.attributes else None

            # Excluded Credentials
            reg_ids = get_optional(params, "registered_credential_ids") or []
            registered_credential_ids: list[bytes] = [base64url_to_bytes(cred_id) for cred_id in reg_ids]
            excluded_credentials: list[PublicKeyCredentialDescriptor] = ([PublicKeyCredentialDescriptor(id=cred)
                                                                          for cred in registered_credential_ids])

            # Key Algorithms
            pub_key_algorithms = get_optional(params, FIDO2PolicyAction.PUBLIC_KEY_CREDENTIAL_ALGORITHMS,
                                              default=[COSEAlgorithmIdentifier.ECDSA_SHA_256,
                                                       COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256])

            # User Verification
            user_verification: UserVerificationRequirement = UserVerificationRequirement.PREFERRED
            if FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT in params:
                user_verification = UserVerificationRequirement(params[FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT])

            # Attestation (None is recommended for passkeys)
            attestation: AttestationConveyancePreference = AttestationConveyancePreference.NONE
            if PasskeyAction.AttestationConveyancePreference in params:
                attestation = AttestationConveyancePreference(params[PasskeyAction.AttestationConveyancePreference])

            registration_options: PublicKeyCredentialCreationOptions = generate_registration_options(
                rp_id=rp_id,
                rp_name=rp_name,
                user_name=token_user.login,
                user_display_name=token_user.login,
                user_id=fido2_user_id,
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

            # Save the userid if there was none before
            if not fido2_user_id:
                fido2_user_id = registration_options.user.id
                token_user.set_attribute(FIDO2TokenInfo.USER_ID, bytes_to_base64url(fido2_user_id))

            options_json: str = options_to_json(registration_options)
            response_detail["passkey_registration"] = json.loads(options_json)
            response_detail["transaction_id"] = challenge.transaction_id

            # Add RP ID, Name and user_id to the token info
            self.add_tokeninfo_dict({
                FIDO2TokenInfo.RELYING_PARTY_ID: rp_id,
                FIDO2TokenInfo.RELYING_PARTY_NAME: rp_name,
                FIDO2TokenInfo.USER_ID: bytes_to_base64url(fido2_user_id)
            })
        else:
            response_detail = {}
        return response_detail

    def update(self, param, reset_failcount=True):
        """
        Second step of enrollment: Verify the registration data from the authenticator with the challenge from the
        database. If the registration is successful, the token is set to enrolled and metadata is written to the token
        info.
        To complete the registration, the following parameters are required in param:
        - attestationObject
        - clientDataJSON
        - credential_id
        - rawId
        - authenticatorAttachment
        - transaction_id
        - HTTP_ORIGIN
        - FIDO2PolicyAction.RELYING_PARTY_ID ("webauthn_relying_party_id")
        """
        response_detail = {"details": {"serial": self.token.serial}}

        attestation = get_optional(param, "attestationObject")
        client_data = get_optional(param, "clientDataJSON")

        if not (attestation and client_data) and not self.token.rollout_state == ROLLOUTSTATE.CLIENTWAIT:
            self.token.rollout_state = ROLLOUTSTATE.CLIENTWAIT
            self.token.active = False
            # Set the description in the first enrollment step
            if "description" in param:
                self.set_description(param["description"])

        elif attestation and client_data and self.token.rollout_state == ROLLOUTSTATE.CLIENTWAIT:
            # Finalize the registration by verifying the registration data from the authenticator
            credential_id = get_required(param, "credential_id")
            credential_id_raw = get_required(param, "rawId")
            authenticator_attachment = get_required(param, "authenticatorAttachment")
            transaction_id = get_required(param, "transaction_id")
            expected_rp_id = get_required(param, FIDO2PolicyAction.RELYING_PARTY_ID)
            expected_origin = get_required(param, "HTTP_ORIGIN")

            serial = self.token.serial
            challenges = [challenge for challenge in get_challenges(serial=serial, transaction_id=transaction_id)
                          if challenge.is_valid()]

            if not len(challenges):
                raise EnrollmentError(f"The enrollment challenge does not exist or has timed out for {serial}")
            try:
                registration_verification: VerifiedRegistration = verify_registration_response(
                    credential={
                        "id": credential_id,
                        "rawId": credential_id_raw,
                        "response": {
                            "attestationObject": attestation,
                            "clientDataJSON": client_data
                        },
                        "type": "public-key",
                        "authenticatorAttachment": authenticator_attachment,
                    },
                    expected_challenge=challenges[0].challenge.encode("utf-8"),
                    expected_origin=expected_origin,
                    expected_rp_id=expected_rp_id,
                )
            except InvalidRegistrationResponse as ex:
                log.error(f"Invalid registration response: {ex}")
                raise EnrollmentError(f"Invalid registration response: {ex}")
            except InvalidJSONStructure as ex:
                log.error(f"Invalid JSON structure: {ex}")
                raise EnrollmentError(f"Invalid JSON structure: {ex}")

            # Verification successful, set the token to enrolled and save information returned by the authenticator
            self.token.rollout_state = ROLLOUTSTATE.ENROLLED
            # Protect the credential_id by setting it as the token secret
            self.set_otpkey(bytes_to_base64url(registration_verification.credential_id))

            # Token Info
            credential_id_hash = hash_credential_id(credential_id)
            token_info: dict = {
                FIDO2TokenInfo.DEVICE_TYPE: registration_verification.credential_device_type,
                FIDO2TokenInfo.BACKED_UP: registration_verification.credential_backed_up,
                FIDO2TokenInfo.PUBLIC_KEY: bytes_to_base64url(registration_verification.credential_public_key),
                FIDO2TokenInfo.AAGUID: registration_verification.aaguid,
                FIDO2TokenInfo.SIGN_COUNT: registration_verification.sign_count,
                FIDO2TokenInfo.CREDENTIAL_ID_HASH: credential_id_hash
            }
            # Save the credential_id hash to an extra table to be able to find the token faster
            save_credential_id_hash(credential_id_hash, self.token.id)

            # If the attestation object contains a x5c certificate, save it in the token info
            # and set the description to the CN if it is not already set
            if registration_verification.attestation_object:
                attestation_object: AttestationObject = parse_attestation_object(
                    registration_verification.attestation_object)
                if attestation_object.att_stmt and attestation_object.att_stmt.x5c:
                    attestation_certificate: Certificate = cryptography.x509.load_der_x509_certificate(
                        attestation_object.att_stmt.x5c[0])
                    certificate_pem: str = (attestation_certificate.public_bytes(serialization.Encoding.PEM)
                                            .decode("utf-8").replace("\n", ""))
                    token_info[FIDO2TokenInfo.ATTESTATION_CERTIFICATE] = certificate_pem
                    if not self.token.description:
                        attributes: list[NameAttribute] = attestation_certificate.subject.get_attributes_for_oid(
                            NameOID.COMMON_NAME)
                        if attributes:
                            self.set_description(attributes[0].value)
            self.add_tokeninfo_dict(token_info)
            self.token.active = True
            # Remove the challenge
            challenges[0].delete()
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
        rp_id = self.get_tokeninfo(FIDO2TokenInfo.RELYING_PARTY_ID)

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
        return str(lazy_gettext("Please confirm the registration with your passkey!"))

    def create_challenge(self, transactionid=None, options=None):
        """
        Passkey does not create a challenge itself, it uses an open challenge acquired from /validate/initialize.
        By returning False here, passkey tokens will not generate a challenge via
        /validate/triggerchallenge -> create_challenge_from_tokens()
        Optionally, creating a challenge can be enabled by setting the passkey_trigger_by_pin policy
        """
        if options and PasskeyAction.EnableTriggerByPIN in options and options[PasskeyAction.EnableTriggerByPIN]:
            rp_id = get_required(options, FIDO2PolicyAction.RELYING_PARTY_ID)
            user_verification = get_optional(options, "user_verification", "preferred")
            challenge = fido2.challenge.create_fido2_challenge(rp_id, user_verification=user_verification,
                                                               transaction_id=transactionid, serial=self.token.serial)
            message = challenge["message"]
            transaction_id = challenge["transaction_id"]
            challenge_details = {"challenge": challenge["challenge"], "rpId": rp_id,
                                 "userVerification": user_verification}
            # TODO this vvv is horrible
            return True, message, transaction_id, challenge_details
        else:
            return False, "", "", {}

    @log_with(log)
    def use_for_authentication(self, options):
        return self.is_active()

    def inc_failcount(self):
        """
        Do not increment the fail count for passkey, since their authentication process is decoupled from the usual.
        """
        pass

    @classmethod
    def is_multichallenge_enrollable(cls):
        return True

    @log_with(log)
    def is_challenge_request(self, passw, user=None, options=None):
        """
        This token type is always challenge-response. If the pin matches, a challenge should be created.
        """
        if options and PasskeyAction.EnableTriggerByPIN in options and options[PasskeyAction.EnableTriggerByPIN]:
            return self.check_pin(passw, user=user, options=options)
        return False

    @check_token_locked
    def authenticate(self, passw, user=None, options=None):
        """
        This is called from check_tokenlist. Suppress missing params here so "wrong otp value" is returned if no
        authentication could be made.
        """
        try:
            authenticator_data = get_required_one_of(options, ["authenticatorData", "authenticatordata"])
            client_data_json = get_required_one_of(options, ["clientDataJSON", "clientdata"])
            signature = get_required_one_of(options, ["signature", "signaturedata"])
            user_handle = get_optional_one_of(options, ["userHandle", "userhandle"])
            expected_challenge = get_required(options, "challenge").encode("utf-8")
            expected_origin = get_required(options, "HTTP_ORIGIN")
            user_verification = get_optional(options, "user_verification", "preferred")
        except ParameterError as e:
            log.debug(f"Missing parameter for authentication with passkey: {e}")
            # TODO authenticate has horrible return values
            return False, -1, None

        pin_match = self.check_pin(passw, user=user, options=options)
        if not pin_match:
            return False, -1, None
        otp_match = self.check_otp(None, 0, None, options)
        return pin_match, otp_match, None
