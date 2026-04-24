# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Test helpers for cryptographic operations — replaces passlib usage in tests.
"""
import base64
import hashlib
import hmac
import os

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

_ph = PasswordHasher()


def argon2_verify(password, hash_str):
    """Verify an argon2 hash. Returns True if the password matches, False otherwise."""
    try:
        return _ph.verify(hash_str, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def _ab64_encode(data: bytes) -> str:
    """Base64 encode with '.' instead of '+' and no '=' padding (passlib ab64 / pbkdf2 format)."""
    return base64.b64encode(data).rstrip(b'=').replace(b'+', b'.').decode('ascii')


def _ab64_decode(s: str) -> bytes:
    """Decode passlib ab64: replace '.' with '+', restore '=' padding."""
    s = s.replace('.', '+')
    pad = (4 - len(s) % 4) % 4
    return base64.b64decode(s + '=' * pad)


def pbkdf2_sha512_hash(password: str, rounds: int, salt_size: int = 10) -> str:
    """Hash a password using PBKDF2-HMAC-SHA512 in passlib's $pbkdf2-sha512$ format."""
    if isinstance(password, str):
        password = password.encode('utf-8')
    salt = os.urandom(salt_size)
    dk = hashlib.pbkdf2_hmac('sha512', password, salt, rounds)
    return '${fmt}${rounds}${salt}${dk}'.format(
        fmt='pbkdf2-sha512',
        rounds=rounds,
        salt=_ab64_encode(salt),
        dk=_ab64_encode(dk),
    )


def pbkdf2_sha512_verify(password: str, hash_str: str) -> bool:
    """Verify a password against a $pbkdf2-sha512$ hash."""
    if isinstance(password, str):
        password = password.encode('utf-8')
    try:
        parts = hash_str.split('$')
        # format: $pbkdf2-sha512$<rounds>$<salt>$<hash>
        rounds = int(parts[2])
        salt = _ab64_decode(parts[3])
        stored_dk = _ab64_decode(parts[4])
        computed_dk = hashlib.pbkdf2_hmac('sha512', password, salt, rounds)
        return hmac.compare_digest(computed_dk, stored_dk)
    except Exception:
        return False
