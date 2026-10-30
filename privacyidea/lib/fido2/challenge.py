import logging
from datetime import datetime, timezone
from dataclasses import dataclass
from webauthn.helpers import bytes_to_base64url

from privacyidea.lib.params import get_required_one_of, get_optional_one_of, get_required, get_optional
from privacyidea.lib import fido2
from privacyidea.lib.cache.redis import ChallengeDTO
from privacyidea.lib.challenge import get_challenges, cancel_challenge, consume_challenge
from privacyidea.lib.conditional_access.authentication_event_types import AUTH_EVENT_REASON_KEY, AuthEventReason
from privacyidea.lib.config import get_from_config
from privacyidea.models import Challenge
from privacyidea.lib.crypto import geturandom
from privacyidea.lib.error import ResourceNotFoundError, AuthError
from privacyidea.lib.fido2.config import FIDO2ConfigOptions
from privacyidea.lib.fido2.policy_action import FIDO2PolicyAction, PasskeyAction
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.tokens.passkeytoken import PasskeyTokenClass
from privacyidea.lib.tokens.webauthn import UserVerificationLevel
from privacyidea.lib.utils import is_true

log = logging.getLogger(__name__)

# From the weakest to the strictest requirement
USER_VERIFICATION_ORDER = (UserVerificationLevel.DISCOURAGED, UserVerificationLevel.PREFERRED,
                           UserVerificationLevel.REQUIRED)


def get_fido2_nonce() -> str:
    """
    Generate a random 32 byte nonce for fido2 challenges. The nonce is encoded in base64url.
    """
    return bytes_to_base64url(geturandom(32))


def create_fido2_challenge(rp_id: str, user_verification: str = "preferred", transaction_id: str | None = None,
                           serial: str | None = None, nonce: str | None = None) -> dict:
    """
    Returns a fido2 challenge. The challenge validity time is set to either WebauthnChallengeValidityTime,
    DefaultChallengeValidityTime or 120s in that order of evaluation.
    The user_verification parameter can be one of "required", "preferred" or "discouraged". If the value is not one of
    these, "preferred" is used. user_verification is saved in the challenge data field.
    If a serial is provided, the challenge is bound to the token with the serial.
    This is the case when using the passkey_trigger_by_pin policy, where the passkey acts as a challenge-response token
    that is triggered via the user and PIN. The challenge should then only be usable with the corresponding token.
    By default, the challenge is not bound to a token, which is the general use-case of FIDO2, to allow usernameless
    logins.
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
    if not nonce:
        nonce = fido2.challenge.get_fido2_nonce()
    message = PasskeyTokenClass.get_default_challenge_text_auth()
    validity = int(get_from_config(FIDO2ConfigOptions.CHALLENGE_VALIDITY_TIME,
                                   get_from_config('DefaultChallengeValidityTime', 120)))
    if user_verification not in USER_VERIFICATION_ORDER:
        log.warning(f"Invalid user_verification value {user_verification}. Using 'preferred' instead.")
        user_verification = "preferred"

    # Use the canonical policy-action constant as the key so verify_fido2_challenge can read it
    # uniformly without knowing about the raw "user_verification" string.
    data = {FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT: user_verification}

    from privacyidea.lib.token import create_challenge
    db_challenge = create_challenge(serial=serial or "", transaction_id=transaction_id,
                                    challenge=nonce, data=data, validitytime=validity)
    transaction_id = db_challenge.transaction_id
    return {
        "transaction_id": transaction_id,
        "challenge": nonce,
        "message": message,
        "rpId": rp_id,
        # "user_verification" is the browser-facing field name
        "user_verification": user_verification
    }


@dataclass
class FIDOVerificationResult:
    success: int
    challenge: "Challenge | ChallengeDTO"


@dataclass
class FIDO2TokenState:
    """
    Whether a token may authenticate, and the state that refuses it if it may not.
    """
    usable: bool
    message: str = ""
    reason: AuthEventReason | None = None


def check_fido2_token_state(token: TokenClass) -> FIDO2TokenState:
    """
    Apply the token checks that ``check_token_list`` runs before any verification: revoked, authentication
    counters, active, fail counter, validity period and rollout state.

    A FIDO2 answer that carries a credential_id is handled outside ``check_token_list`` - the view resolves the
    token from the credential itself - so the views call this before verifying the response. The answers of the PIN
    change via ``/validate/check`` skip ``check_token_list`` as well and use it, too. The state is
    returned instead of raised, because each view phrases its own response and writes its own
    authentication-log row from the reason.
    """
    # Revocation first, as check_serial_pass does: revoke() also locks the token, and check_reset_failcount()
    # calls the lock-protected reset() once the clear timeout has elapsed, which would raise here instead of
    # letting the token report that it is revoked.
    if token.is_revoked():
        return FIDO2TokenState(False, "Token is revoked", AuthEventReason.TOKEN_REVOKED)
    token.check_reset_failcount()
    messages = []
    if not token.check_all(messages):
        return FIDO2TokenState(False, ", ".join(messages), token.auth_details.get(AUTH_EVENT_REASON_KEY))
    return FIDO2TokenState(True)


def record_fido2_login_success(token: TokenClass) -> None:
    """
    The success bookkeeping of ``check_token_list`` for the FIDO2 login paths: count the authentication unless
    the no_auth_counter config switches the counters off, reset the fail counter and record the time of this
    authentication.

    The views call this once the login is accepted. A verified assertion is not yet an accepted login - the
    view can still refuse it - so last_auth is written here and not where the assertion is verified.
    """
    if not is_true(get_from_config(key="no_auth_counter")):
        token.inc_count_auth_success()
    token.reset()
    token.write_tokeninfo(PolicyAction.LASTAUTH, datetime.now(timezone.utc).isoformat(timespec="seconds"))


def has_unbound_challenge(transaction_id: str) -> bool:
    """
    Check whether the transaction has a challenge that is not bound to a token. Such a challenge comes from
    /validate/initialize and starts a passkey login without a username.
    """
    return any(not challenge.serial for challenge in get_challenges(transaction_id=transaction_id))


class ChallengeExpiredError(AuthError):
    """
    The challenge of the transaction had timed out when the response arrived.
    """


def verify_fido2_challenge(transaction_id: str, token: TokenClass, params: dict,
                           minimum_user_verification: str | None = None) -> FIDOVerificationResult:
    """
    Verify the response for a fido2 challenge with the given token.
    Params is required to have the keys:
    - authenticatorData or authenticatordata
    - clientDataJSON or clientdata
    - signature or signaturedata
    - userHandle or userhandle
    - HTTP_ORIGIN

    If no challenge is found for the transaction_id, a ResourceNotFoundError is raised.
    If the challenge has timed out, a ChallengeExpiredError (an AuthError) is raised.
    If the challenge is bound to a token serial and the token serial does not match the input token, an AuthError
    is raised.

    The user verification requirement is taken from the challenge. If minimum_user_verification is given, the
    stricter of the two values applies.
    """
    db_challenges = get_challenges(transaction_id=transaction_id)
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
        raise ChallengeExpiredError(f"The challenge {transaction_id} has timed out.")

    # New challenges store the value under FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT.
    # Challenges created by older code used the raw "user_verification" string instead.
    # The translation happens here so token classes can always read the constant without a fallback.
    data = challenge.get_data()
    if not isinstance(data, dict):
        log.error(f"Invalid challenge data for transaction_id {transaction_id}.")
        raise AuthError(f"Invalid challenge data for transaction_id {transaction_id}.")
    user_verification = (data.get(FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT)
                         or data.get("user_verification"))
    if user_verification not in USER_VERIFICATION_ORDER:
        log.error(
            f"Invalid user_verification value {user_verification!r} in challenge {transaction_id}."
        )
        raise AuthError(f"Invalid user_verification value in challenge {transaction_id}.")
    if minimum_user_verification:
        user_verification = max(user_verification, minimum_user_verification, key=USER_VERIFICATION_ORDER.index)

    options = {
        "challenge": challenge.challenge,
        "authenticatorData": get_required_one_of(params, ["authenticatorData", "authenticatordata"]),
        "clientDataJSON": get_required_one_of(params, ["clientDataJSON", "clientdata"]),
        "signature": get_required_one_of(params, ["signature", "signaturedata"]),
        "userHandle": get_optional_one_of(params, ["userHandle", "userhandle"]),
        "HTTP_ORIGIN": get_required(params, "HTTP_ORIGIN"),
        FIDO2PolicyAction.USER_VERIFICATION_REQUIREMENT: user_verification
    }
    # These parameters are required for compatibility with the old WebAuthnToken class
    if token.type == "webauthn":
        options.update({
            "credential_id": get_required_one_of(params, ["credential_id", "credentialid"]),
            # Authorization restrictions resolved by the webauthntoken_request and webauthntoken_authz prepolicies
            FIDO2PolicyAction.REQ: get_optional(params, FIDO2PolicyAction.REQ),
            FIDO2PolicyAction.AUTHENTICATOR_SELECTION_LIST: get_optional(
                params, FIDO2PolicyAction.AUTHENTICATOR_SELECTION_LIST),
        })
    if token.type == "passkey":
        # Passkey-only policy restrictions resolved by the fido2_auth prepolicy, forwarded here since this
        # function builds its own curated options dict rather than passing params through unchanged.
        options.update({
            PasskeyAction.AllowedAuthenticatorDeviceTypes: get_optional(
                params, PasskeyAction.AllowedAuthenticatorDeviceTypes),
            PasskeyAction.EnforceUserHandle: get_optional(params, PasskeyAction.EnforceUserHandle),
        })
    options.update({"user": token.user})
    ret = token.check_otp(None, options=options)
    if ret > 0 and not consume_challenge(challenge):
        # The assertion is valid, but another request already used this challenge, so this one is not accepted.
        # Consume only after a verified assertion: a wrong one must not remove the challenge of the right request.
        # A synced passkey reports sign count 0, so the challenge is the only replay guard on that path.
        log.info(f"The challenge {transaction_id} of token {token.get_serial()} was used by another request.")
        ret = -1
    result = FIDOVerificationResult(ret, challenge)
    # On success, remove the remaining challenges with the transaction_id from both
    # Redis (when active) and the DB.
    if result.success > 0:
        cancel_challenge(transaction_id)
    return result
