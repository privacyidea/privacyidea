# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Key handling for push token tests: the key pair of the simulated smartphone and the
signature checks of what the server signs, for RSA (PKCS1v15) and ECDSA (DER) keys,
both with SHA-256 and base32 encoded signatures as on the wire.
"""
from base64 import b32decode, b32encode, b64decode

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa

from privacyidea.lib.tokens.pushtoken import strip_pem_headers
from privacyidea.lib.utils import to_bytes, to_unicode


def sign_data(private_key, data: bytes) -> bytes:
    """Sign like the push protocol does: PKCS1v15 for RSA, DER encoded ECDSA for EC, SHA-256 for both."""
    if isinstance(private_key, rsa.RSAPrivateKey):
        return private_key.sign(data, padding.PKCS1v15(), hashes.SHA256())
    if isinstance(private_key, ec.EllipticCurvePrivateKey):
        return private_key.sign(data, ec.ECDSA(hashes.SHA256()))
    raise TypeError(f"Unsupported private key type {type(private_key)}")


def verify_signature(public_key, signature: bytes, data: bytes) -> None:
    """Verify a push signature, raises InvalidSignature if it does not match."""
    if isinstance(public_key, rsa.RSAPublicKey):
        public_key.verify(signature, data, padding.PKCS1v15(), hashes.SHA256())
    elif isinstance(public_key, ec.EllipticCurvePublicKey):
        public_key.verify(signature, data, ec.ECDSA(hashes.SHA256()))
    else:
        raise TypeError(f"Unsupported public key type {type(public_key)}")


def load_server_public_key(pem: str):
    """Load the server public key as the token stores it in the tokeninfo (PEM)."""
    return serialization.load_pem_public_key(to_bytes(pem), default_backend())


def load_public_key_from_detail(public_key_b64: str):
    """Load the server public key the smartphone gets in ``detail.public_key``
    (base64 DER without PEM headers: PKCS#1 for RSA, SubjectPublicKeyInfo for EC)."""
    return serialization.load_der_public_key(b64decode(public_key_b64), default_backend())


class SmartphoneKey:
    """The key pair of a simulated privacyIDEA Authenticator app."""

    def __init__(self, private_key) -> None:
        self.private_key = private_key
        self.public_key = private_key.public_key()
        self.public_key_pem = to_unicode(self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo))
        # The smartphone sends the public key urlsafe and without the -----BEGIN header
        self.public_key_urlsafe = strip_pem_headers(self.public_key_pem).replace("+", "-").replace("/", "_")

    @classmethod
    def rsa(cls, key_size: int = 4096) -> "SmartphoneKey":
        return cls(rsa.generate_private_key(public_exponent=65537, key_size=key_size, backend=default_backend()))

    @classmethod
    def ec(cls, curve: ec.EllipticCurve = None) -> "SmartphoneKey":
        return cls(ec.generate_private_key(curve or ec.SECP256R1(), default_backend()))

    def sign(self, data: str | bytes) -> bytes:
        return sign_data(self.private_key, to_bytes(data))

    def sign_b32(self, data: str | bytes) -> str:
        return to_unicode(b32encode(self.sign(data)))


class ServerKey:
    """A server key pair in the PEM form the push token keeps in its tokeninfo."""

    def __init__(self, private_key) -> None:
        self.private_key = private_key
        if isinstance(private_key, rsa.RSAPrivateKey):
            private_format = serialization.PrivateFormat.TraditionalOpenSSL
        else:
            private_format = serialization.PrivateFormat.PKCS8
        self.private_key_pem = to_unicode(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=private_format,
            encryption_algorithm=serialization.NoEncryption()))
        self.public_key_pem = to_unicode(private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo))

    @classmethod
    def rsa(cls, key_size: int = 4096) -> "ServerKey":
        return cls(rsa.generate_private_key(public_exponent=65537, key_size=key_size, backend=default_backend()))

    @classmethod
    def ec(cls) -> "ServerKey":
        return cls(ec.generate_private_key(ec.SECP256R1(), default_backend()))


def verify_b32_signature(public_key, signature_b32: str, data: str | bytes) -> None:
    verify_signature(public_key, b32decode(signature_b32), to_bytes(data))
