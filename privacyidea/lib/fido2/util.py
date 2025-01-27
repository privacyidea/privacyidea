import hashlib

from webauthn import base64url_to_bytes

from privacyidea.lib.token import create_tokenclass_object, log, get_tokens
from privacyidea.lib.tokenclass import ROLLOUTSTATE, TokenClass
from privacyidea.lib.user import User
from privacyidea.models import TokenInfo, Token, Challenge


def get_fido2_token_by_credential_id(credential_id: str):
    """
    Find a fido2 token (WebAuthn or Passkey) by the credential_id.

    :param credential_id: The credential_id as returned by an authenticator
    :return: The token object or None
    """
    h = hashlib.sha256(base64url_to_bytes(credential_id))
    credential_id_hash = h.hexdigest()
    try:
        token_id = (TokenInfo.query.filter(TokenInfo.Key == "credential_id_hash")
                    .filter(TokenInfo.Value == credential_id_hash).first().token_id)
        token = Token.query.filter(Token.id == token_id).first()
        return create_tokenclass_object(token)
    except Exception as ex:
        log.warning(f"Failed to find credential with id: {credential_id}. {ex}")
        return None


def get_fido2_token_by_transaction_id(transaction_id: str):
    """
    Find a fido2 token (WebAuthn or Passkey) by the transaction_id of the challenge.
    If the challenge or the token is not found, or the token is not a FIDO2 token, None is returned.

    :param transaction_id: The transaction_id of the challenge
    :return: The token object or None
    """
    challenge = Challenge.query.filter(Challenge.transaction_id == transaction_id).first()
    if not challenge:
        log.info(f"Challenge with transaction_id {transaction_id} not found.")
        return None
    token = Token.query.filter(Token.serial == challenge.serial).first()
    if not token:
        log.info(f"Token with serial {challenge.serial} not found.")
        return None
    if token.tokentype not in ["webauthn", "passkey"]:
        log.info(f"Token with serial {challenge.serial} is not a FIDO2 token, but {token.get_tokentype()}.")
        return None
    return create_tokenclass_object(token)


def get_credential_ids_for_user(user: User) -> list:
    """
    Get a list of credential ids of passkey or webauthn token for a user.
    Can be used to avoid double registration of an authenticator.

    :param user: The user object
    :return: A list of credential ids
    """
    credential_ids = []
    for token in get_tokens(user=user, token_type_list=["passkey"]):
        if token.token.rollout_state != ROLLOUTSTATE.CLIENTWAIT:
            cred_id = token.token.get_otpkey().getKey().decode("utf-8")
            credential_ids.append(cred_id)
    return credential_ids
