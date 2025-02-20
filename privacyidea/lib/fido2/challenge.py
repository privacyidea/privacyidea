from typing import Union

from webauthn.helpers import bytes_to_base64url

from privacyidea.api.lib.utils import get_required_one_of, get_optional_one_of, get_required
from privacyidea.lib import fido2
from privacyidea.lib.config import get_from_config
from privacyidea.lib.crypto import geturandom
from privacyidea.lib.error import ResourceNotFoundError, AuthError
from privacyidea.lib.fido2.config import FIDO2ConfigOptions
from privacyidea.lib.token import log
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.tokens.passkeytoken import PasskeyTokenClass
from privacyidea.models import Challenge


def get_fido2_nonce() -> str:
    """
    Generate a random 32 byte nonce for fido2 challenges. The nonce is encoded in base64url.
    """
    return bytes_to_base64url(geturandom(32))


def create_fido2_challenge(rp_id: str, user_verification: str = "preferred", transaction_id: Union[str, None] = None,
                           serial: Union[str, None] = None) -> dict:
    """
    Returns a fido2 challenge. If a serial is provided, the challenge is bound to the token with the serial. By default,
    the challenge is not bound to a token, which is the general use-case of FIDO2.
    The challenge validity time is set to either WebauthnChallengeValidityTime, DefaultChallengeValidityTime or 120s
    in that order of evaluation.
    The user_verification parameter can be one of "required", "preferred" or "discouraged". If the value is not one of
    these, "preferred" is used. user_verification is saved in the challenge data field.
    The returned dict has the format:
        ::

            {
                "transaction_id": "12345678901234567890",
                "challenge": <32 random bytes base64url encoded>,
                "rpId": "example.com",
                "message": "Please authenticate with your Passkey!",
                "userVerification": "preferred"
            }
    """
    challenge = fido2.challenge.get_fido2_nonce()
    message = PasskeyTokenClass.get_default_challenge_text_auth()
    validity = int(get_from_config(FIDO2ConfigOptions.CHALLENGE_VALIDITY_TIME,
                                   get_from_config('DefaultChallengeValidityTime', 120)))
    user_verification_values = ["required", "preferred", "discouraged"]
    if user_verification not in user_verification_values:
        log.warning(f"Invalid user_verification value {user_verification}. Using 'preferred' instead.")
        user_verification = "preferred"

    db_challenge = Challenge(serial or "", transaction_id=transaction_id, challenge=challenge,
                             data=f"user_verification={user_verification}", validitytime=validity)
    db_challenge.save()
    transaction_id = db_challenge.transaction_id
    return {
        "transaction_id": transaction_id,
        "challenge": challenge,
        "message": message,
        "rpId": rp_id,
        "user_verification": user_verification
    }


def verify_fido2_challenge(transaction_id: str, token: TokenClass, params: dict) -> int:
    """
    Verify the response for a fido2 challenge with the given token.
    Params is required to have the keys:
    - authenticatorData or authenticatordata
    - clientDataJSON or clientdata
    - signature or signaturedata
    - userHandle or userhandle
    - HTTP_ORIGIN

    If no challenge is found for the transaction_id, a ResourceNotFoundError is raised.
    If the challenge has timed out, an AuthError is raised.
    If the challenge is bound to a token serial and the token serial does not match the input token, an AuthError
    is raised.
    """
    db_challenges = Challenge.query.filter(Challenge.transaction_id == transaction_id).all()
    if not db_challenges:
        raise ResourceNotFoundError(f"Challenge with transaction_id {transaction_id} not found.")

    challenge = next((db_challenge for db_challenge in db_challenges if
                      (db_challenge.serial == token.get_serial() or not db_challenge.serial)),
                     None)
    if not challenge:
        log.error(f"Challenge with transaction_id {transaction_id} is not meant for token {token.get_serial()}.")
        raise AuthError(f"The challenge {transaction_id} is not meant for the token {token.get_serial()}.")

    if not challenge.is_valid():
        log.error(f"Challenge with transaction_id {transaction_id} has timed out.")
        raise AuthError(f"The challenge {transaction_id} has timed out.")

    # Get the user_verification requirement from the challenge data
    uv_string = challenge.get_data()
    parts = uv_string.split("=")
    if len(parts) != 2 or parts[0] != "user_verification":
        log.error(f"Invalid user_verification data in challenge with transaction_id {transaction_id}.")
        raise AuthError(f"Invalid user_verification data in challenge {transaction_id}.")
    user_verification = parts[1]
    if user_verification not in ["required", "preferred", "discouraged"]:
        log.error(
            f"Invalid user_verification value {user_verification} in challenge with transaction_id {transaction_id}."
        )
        raise AuthError(f"Invalid user_verification value {user_verification} in challenge {transaction_id}.")

    options = {
        "challenge": challenge.challenge,
        "authenticatorData": get_required_one_of(params, ["authenticatorData", "authenticatordata"]),
        "clientDataJSON": get_required_one_of(params, ["clientDataJSON", "clientdata"]),
        "signature": get_required_one_of(params, ["signature", "signaturedata"]),
        "userHandle": get_optional_one_of(params, ["userHandle", "userhandle"]),
        "HTTP_ORIGIN": get_required(params, "HTTP_ORIGIN"),
        "user_verification": user_verification
    }
    # These parameters are required for compatibility with the old WebAuthnToken class
    if token.type == "webauthn":
        options.update({"credential_id": get_required_one_of(params, ["credential_id", "credentialid"])})
    options.update({"user": token.user})
    ret = token.check_otp(None, options=options)
    # On success, remove all challenges with the transaction_id
    if ret > 0:
        for db_challenge in db_challenges:
            db_challenge.delete()
    return ret
