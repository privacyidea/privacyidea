import hashlib
from typing import Union

from sqlalchemy import select
from webauthn import base64url_to_bytes

from privacyidea.lib.token import create_tokenclass_object, log, get_tokens
from privacyidea.lib.tokenclass import RolloutState, TokenClass
from privacyidea.lib.user import User
from privacyidea.models import TokenInfo, Token, Challenge, TokenCredentialIdHash, db


def get_fido2_token_by_credential_id(credential_id: str) -> Union[TokenClass, None]:
    """
    Find a FIDO2 token (WebAuthn or Passkey) by the credential_id.

    :param credential_id: The credential_id as returned by an authenticator
    :return: The token object or None
    """
    credential_id_hash = hash_credential_id(credential_id)
    try:
        tcih_stmt = select(TokenCredentialIdHash).where(TokenCredentialIdHash.credential_id_hash == credential_id_hash)
        tcih = db.session.scalar(tcih_stmt)
        if tcih:
            db_token = db.session.get(Token, tcih.token_id)
            if db_token:
                return create_tokenclass_object(db_token)
        else:
            log.debug(f"TokenCredentialIdHash entry not found for credential_id {credential_id}. Trying token info...")
            token_id_stmt = select(TokenInfo.token_id).where(TokenInfo.Key == "credential_id_hash", TokenInfo.Value == credential_id_hash)
            token_id = db.session.scalar(token_id_stmt)
            db_token = db.session.get(Token, token_id) if token_id else None
            if db_token:
                # Create a new TokenCredentialIdHash entry for the next time
                tcih = TokenCredentialIdHash(token_id=db_token.id, credential_id_hash=credential_id_hash)
                tcih.save()
                return create_tokenclass_object(db_token)
    except Exception as ex:
        log.warning(f"Error while trying to get token by credential id: {ex}")
    log.warning(f"Failed to find credential with id: {credential_id}.")
    return None


def get_fido2_token_by_transaction_id(transaction_id: str, credential_id: str) -> Union[TokenClass, None]:
    """
    Find a fido2 token (WebAuthn or Passkey) by the transaction_id of the challenge and the credential_id.
    First all challenges are retrieved with the transaction_id. Then the token is searched by the serial of the
    challenge, and lastly, the credential_id of eligible token found is compared with the one provided.
    If the challenge or the token is not found, or the token is not a FIDO2 token, None is returned.

    :param transaction_id: The transaction_id of the challenge
    :param credential_id: The credential_id as returned by an authenticator
    :return: The token object or None
    """
    stmt = select(Challenge).where(Challenge.transaction_id == transaction_id)
    challenges = db.session.scalars(stmt).all()
    if not challenges:
        log.info(f"No challenges with transaction_id {transaction_id} not found.")
        return None
    token = None
    for challenge in challenges:
        stmt = select(Token).where(Token.serial == challenge.serial)
        t = db.session.scalar(stmt)
        if not t:
            continue
        if t.tokentype == "webauthn":
            possible_token = create_tokenclass_object(t)
            cred_id = possible_token.decrypt_otpkey()
            if cred_id == credential_id:
                token = possible_token
                break
    if not token:
        log.info(f"No fido2 token found for transaction_id {transaction_id}.")
    return token


def get_credential_ids_for_user(user: User) -> list:
    """
    Get a list of credential ids of passkey or webauthn token for a user.
    Can be used to avoid double registration of an authenticator.

    :param user: The user object
    :return: A list of credential ids
    """
    credential_ids = []
    for token in get_tokens(user=user, token_type_list=["passkey"]):
        if token.token.rollout_state != RolloutState.CLIENTWAIT:
            cred_id = token.token.get_otpkey().getKey().decode("utf-8")
            credential_ids.append(cred_id)
    return credential_ids


def hash_credential_id(credential_id: Union[str, bytes]) -> str:
    """
    Hash a credential_id with SHA256 and return the hexdigest.

    :param credential_id: The credential_id to hash
    :return: The hexdigest of the hash
    """
    if isinstance(credential_id, str):
        credential_id = base64url_to_bytes(credential_id)
    return hashlib.sha256(credential_id).hexdigest()


def save_credential_id_hash(credentials_id_hash: str, token_id: int) -> None:
    """
    Save a credential_id hash for a token in the database.

    :param credentials_id_hash: The hash of the credential_id
    :param token_id: The id of the token
    """
    # Check if an entry with that hash already exists
    stmt = select(TokenCredentialIdHash).where(TokenCredentialIdHash.credential_id_hash == credentials_id_hash)
    tcih = db.session.scalar(stmt)
    if tcih:
        token = db.session.get(Token, tcih.token_id)
        if token.id == token_id:
            return
        else:
            # if the token is different, we need to delete the old entry
            log.warning(f"Existing entry in TokenCredentialIdHash for credential_id_hash {credentials_id_hash} and "
                        f"token_id {token.id}. Overwriting it with token_id {token_id}.")
            tcih.delete()
    TokenCredentialIdHash(token_id=token_id, credential_id_hash=credentials_id_hash).save()
