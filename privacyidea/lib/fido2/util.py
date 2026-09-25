import hashlib

from sqlalchemy import select
from webauthn import base64url_to_bytes

from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.error import EnrollmentError
from privacyidea.lib.token import create_tokenclass_object, log, get_tokens
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.tokenrolloutstate import RolloutState
from privacyidea.lib.tokens.webauthn import webauthn_b64_encode
from privacyidea.lib.user import User
from privacyidea.models import TokenInfo, Token, TokenCredentialIdHash, db


def get_fido2_token_by_credential_id(credential_id: str) -> TokenClass | None:
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
            # TokenInfo.Value is a CLOB on Oracle, which cannot be compared with "=" (ORA-00932).
            # LIKE works on every dialect, and the hash is a hex digest, so it carries no wildcards.
            token_id_stmt = select(TokenInfo.token_id).where(TokenInfo.Key == "credential_id_hash",
                                                             TokenInfo.Value.like(credential_id_hash))
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


def get_fido2_token_by_transaction_id(transaction_id: str, credential_id: str) -> TokenClass | None:
    """
    Find a fido2 token (WebAuthn or Passkey) by the transaction_id of the challenge and the credential_id.
    First all challenges are retrieved with the transaction_id. Then the token is searched by the serial of the
    challenge, and lastly, the credential_id of eligible token found is compared with the one provided.
    If the challenge or the token is not found, or the token is not a FIDO2 token, None is returned.

    :param transaction_id: The transaction_id of the challenge
    :param credential_id: The credential_id as returned by an authenticator
    :return: The token object or None
    """
    challenges = get_challenges(transaction_id=transaction_id)
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


def token_belongs_to_user(token: TokenClass, user: User) -> bool:
    """
    Check whether the user is one of the owners of the token. The owners are matched the same way as when the tokens
    of a user are looked up for an authentication.

    :param token: The token object
    :param user: The user object
    :return: True if the user owns the token
    """
    if not user or not user.uid:
        return False
    return get_tokens(serial=token.get_serial(), user=user, count=True) > 0


def get_credential_ids_for_user(user: User) -> list:
    """
    Get a list of credential ids of passkey or webauthn token for a user.
    Can be used to avoid double registration of an authenticator.

    Tokens that are still in CLIENTWAIT (enrollment unfinished) or that have been
    revoked are skipped: the credential is either not yet bound or intentionally
    retired, so the user must be allowed to enroll a fresh credential on the same
    authenticator. Disabled tokens are still included, since disabling is reversible.

    :param user: The user object
    :return: A list of credential ids (base64url-encoded)
    """
    credential_ids = []
    for token in get_tokens(user=user, token_type_list=["passkey", "webauthn"]):
        if token.token.rollout_state == RolloutState.CLIENTWAIT:
            continue
        if token.token.revoked:
            continue
        if token.type.lower() == "webauthn":
            cred_id = token.decrypt_otpkey()
        else:
            cred_id = token.token.get_otpkey().getKey().decode("utf-8")
        credential_ids.append(cred_id)
    return credential_ids


def hash_credential_id(credential_id: str | bytes) -> str:
    """
    Hash a credential_id with SHA256 and return the hexdigest.

    :param credential_id: The credential_id to hash
    :return: The hexdigest of the hash
    """
    if isinstance(credential_id, str):
        credential_id = base64url_to_bytes(credential_id)
    return hashlib.sha256(credential_id).hexdigest()


def credential_id_is_registered_to_other_token(credential_id: bytes, token_id: int) -> bool:
    """
    Check whether a credential is already registered to a token other than the one with the given id.

    The TokenCredentialIdHash table has an entry for every passkey and for every WebAuthn token enrolled or used since
    the table exists. A WebAuthn token enrolled before that is only found by comparing the credential ids of all
    WebAuthn tokens.

    :param credential_id: The raw credential_id
    :param token_id: The id of the token the credential is being registered to
    :return: True if another token already has this credential
    """
    stmt = select(TokenCredentialIdHash.token_id).where(
        TokenCredentialIdHash.credential_id_hash == hash_credential_id(credential_id))
    registered_token_id = db.session.scalar(stmt)
    if registered_token_id is not None:
        return registered_token_id != token_id

    credential_id_b64 = webauthn_b64_encode(credential_id)
    for token in get_tokens(tokentype="webauthn"):
        if token.token.id != token_id and token.decrypt_otpkey() == credential_id_b64:
            return True
    return False


def save_credential_id_hash(credentials_id_hash: str, token_id: int) -> None:
    """
    Save a credential_id hash for a token in the database.

    A credential belongs to a single token. If the hash is already registered to another token, that entry is kept
    and an EnrollmentError is raised.

    :param credentials_id_hash: The hash of the credential_id
    :param token_id: The id of the token
    """
    stmt = select(TokenCredentialIdHash).where(TokenCredentialIdHash.credential_id_hash == credentials_id_hash)
    tcih = db.session.scalar(stmt)
    if tcih:
        if tcih.token_id == token_id:
            return
        log.warning(f"The credential_id_hash {credentials_id_hash} is already registered to the token with id "
                    f"{tcih.token_id}. Refusing to register it to the token with id {token_id}.")
        raise EnrollmentError("The credential is already registered to another token.")
    TokenCredentialIdHash(token_id=token_id, credential_id_hash=credentials_id_hash).save()
