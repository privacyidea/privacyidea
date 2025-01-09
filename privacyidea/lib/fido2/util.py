from webauthn.helpers import bytes_to_base64url

from privacyidea.lib.crypto import geturandom


def get_fido2_nonce() -> str:
    """
    Generate a random 32 byte nonce for fido2 challenges. The nonce is encoded in base64url.
    """
    return bytes_to_base64url(geturandom(32))
