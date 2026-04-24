# Pure-Python verification (and generation) for Unix crypt hash formats:
#   $1$  (md5_crypt)
#   $5$  (sha256_crypt)
#   $6$  (sha512_crypt)
#
# The algorithms are specified by:
#   - md5_crypt: Poul-Henning Kamp (FreeBSD, 1994)
#   - sha256_crypt / sha512_crypt: Ulrich Drepper (glibc, 2007)
#
# This implementation is adapted from passlib 1.7.4 (BSD license):
#   Copyright (c) 2008-2020 Assurance Technologies, LLC. All rights reserved.
#   https://foss.heptapod.net/python-libs/passlib
#
# The md5_crypt portion incorporates code derived from the original
# FreeBSD implementation by Poul-Henning Kamp, available under the
# "Beer-Ware License" (Revision 42).
#
# Only stdlib imports are used (hashlib, hmac, os, re).
import hashlib
import hmac
import os
import re

# Unix crypt base64 alphabet (./0-9A-Za-z), 6-bit little-endian encoding.
_ITOA64 = './0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'


def _h64_encode(data):
    """Encode *data* bytes with the Unix crypt base64 (little-endian, ``./0-9A-Za-z``)."""
    out = []
    i = 0
    n = len(data)
    while i < n:
        b0 = data[i]
        i += 1
        out.append(_ITOA64[b0 & 0x3f])
        b1 = data[i] if i < n else 0
        out.append(_ITOA64[((b0 >> 6) | (b1 << 2)) & 0x3f])
        if i >= n:
            break
        i += 1
        b2 = data[i] if i < n else 0
        out.append(_ITOA64[((b1 >> 4) | (b2 << 4)) & 0x3f])
        if i >= n:
            break
        i += 1
        out.append(_ITOA64[(b2 >> 2) & 0x3f])
    return ''.join(out)


def _h64_encode_transposed(source, offsets):
    """Transpose *source* bytes according to *offsets*, then h64-encode."""
    return _h64_encode(bytes(source[o] for o in offsets))


def _repeat_string(source, size):
    """Repeat (or truncate) *source* so its length equals *size*."""
    mult = 1 + (size - 1) // len(source)
    return (source * mult)[:size]


def _generate_salt(length):
    """Generate a random salt string of *length* characters from the crypt alphabet."""
    raw = os.urandom(length)
    return ''.join(_ITOA64[b % 64] for b in raw)


# Pre-calculated round offsets (lcm(2,3,7) = 42 round cycle).
_c_digest_offsets = (
    (0, 3), (5, 1), (5, 3), (1, 2), (5, 1), (5, 3), (1, 3),
    (4, 1), (5, 3), (1, 3), (5, 0), (5, 3), (1, 3), (5, 1),
    (4, 3), (1, 3), (5, 1), (5, 2), (1, 3), (5, 1), (5, 3),
)

# Transpose maps for the final digest encoding.
_256_transpose_map = (
    20, 10, 0, 11, 1, 21, 2, 22, 12, 23, 13, 3, 14, 4, 24, 5,
    25, 15, 26, 16, 6, 17, 7, 27, 8, 28, 18, 29, 19, 9, 30, 31,
)

_512_transpose_map = (
    42, 21, 0, 1, 43, 22, 23, 2, 44, 45, 24, 3, 4, 46, 25, 26,
    5, 47, 48, 27, 6, 7, 49, 28, 29, 8, 50, 51, 30, 9, 10, 52,
    31, 32, 11, 53, 54, 33, 12, 13, 55, 34, 35, 14, 56, 57, 36, 15,
    16, 58, 37, 38, 17, 59, 60, 39, 18, 19, 61, 40, 41, 20, 62, 63,
)


def _raw_sha2_crypt(pwd, salt, rounds, use_512=False):
    """Core SHA-256/512-crypt computation (pure Python).

    Returns the encoded checksum string (no ``$`` prefix).
    """
    if isinstance(pwd, str):
        pwd = pwd.encode('utf-8')
    salt = salt.encode('ascii') if isinstance(salt, str) else salt
    pwd_len = len(pwd)
    salt_len = len(salt)

    hash_const = hashlib.sha512 if use_512 else hashlib.sha256
    transpose_map = _512_transpose_map if use_512 else _256_transpose_map

    # Digest B
    db = hash_const(pwd + salt + pwd).digest()

    # Digest A
    a_ctx = hash_const(pwd + salt)
    a_ctx.update(_repeat_string(db, pwd_len))
    i = pwd_len
    while i:
        a_ctx.update(db if i & 1 else pwd)
        i >>= 1
    da = a_ctx.digest()

    # Digest P (password-length, repeating hash of pwd)
    if pwd_len < 96:
        dp = _repeat_string(hash_const(pwd * pwd_len).digest(), pwd_len)
    else:
        tmp_ctx = hash_const(pwd)
        for _ in range(pwd_len - 1):
            tmp_ctx.update(pwd)
        dp = _repeat_string(tmp_ctx.digest(), pwd_len)

    # Digest S (salt-length, repeating hash of salt)
    ds = hash_const(salt * (16 + da[0])).digest()[:salt_len]

    # Digest C — main rounds loop (42-round block optimisation)
    dp_dp = dp + dp
    dp_ds = dp + ds
    perms = [dp, dp_dp, dp_ds, dp_ds + dp, ds + dp, ds + dp_dp]
    data = [(perms[even], perms[odd]) for even, odd in _c_digest_offsets]

    dc = da
    blocks, tail = divmod(rounds, 42)
    while blocks:
        for even, odd in data:
            dc = hash_const(odd + hash_const(dc + even).digest()).digest()
        blocks -= 1

    if tail:
        pairs = tail >> 1
        for even, odd in data[:pairs]:
            dc = hash_const(odd + hash_const(dc + even).digest()).digest()
        if tail & 1:
            dc = hash_const(dc + data[pairs][0]).digest()

    return _h64_encode_transposed(dc, transpose_map)


# Regex for "$5$..." / "$6$..." hash strings.
_SHA2_RE = re.compile(
    r'^\$(5|6)\$(?:rounds=(\d+)\$)?([./0-9A-Za-z]{0,16})\$?([./0-9A-Za-z]*)$'
)


def _parse_sha2(hash_str):
    """Parse a ``$5$`` or ``$6$`` hash string.

    Returns ``(use_512, rounds, salt, checksum)`` or raises ``ValueError``.
    """
    m = _SHA2_RE.match(hash_str)
    if not m:
        raise ValueError(f"Invalid sha2-crypt hash: {hash_str[:20]!r}...")
    variant, rounds_str, salt, checksum = m.groups()
    use_512 = (variant == '6')
    rounds = int(rounds_str) if rounds_str else 5000
    # Spec: clip rounds to [1000, 999999999]
    rounds = max(1000, min(rounds, 999999999))
    return use_512, rounds, salt, checksum


def verify_sha256_crypt(password, hash_str):
    """Verify *password* against a ``$5$…`` hash.  Returns ``bool``."""
    try:
        use_512, rounds, salt, checksum = _parse_sha2(hash_str)
        if use_512:
            return False
        computed = _raw_sha2_crypt(password, salt, rounds, use_512=False)
        return hmac.compare_digest(computed, checksum)
    except Exception:
        return False


def verify_sha512_crypt(password, hash_str):
    """Verify *password* against a ``$6$…`` hash.  Returns ``bool``."""
    try:
        use_512, rounds, salt, checksum = _parse_sha2(hash_str)
        if not use_512:
            return False
        computed = _raw_sha2_crypt(password, salt, rounds, use_512=True)
        return hmac.compare_digest(computed, checksum)
    except Exception:
        return False


def generate_sha256_crypt(password, rounds=535000):
    """Hash *password* with sha256-crypt.  Returns the full ``$5$…`` string."""
    salt = _generate_salt(16)
    checksum = _raw_sha2_crypt(password, salt, rounds, use_512=False)
    if rounds == 5000:
        return f'$5${salt}${checksum}'
    return f'$5$rounds={rounds}${salt}${checksum}'


def generate_sha512_crypt(password, rounds=656000):
    """Hash *password* with sha512-crypt.  Returns the full ``$6$…`` string."""
    salt = _generate_salt(16)
    checksum = _raw_sha2_crypt(password, salt, rounds, use_512=True)
    if rounds == 5000:
        return f'$6${salt}${checksum}'
    return f'$6$rounds={rounds}${salt}${checksum}'


_MD5_MAGIC = b'$1$'

# Transpose map for the final md5-crypt digest encoding.
_md5_transpose_map = (12, 6, 0, 13, 7, 1, 14, 8, 2, 15, 9, 3, 5, 10, 4, 11)


def _raw_md5_crypt(pwd, salt):
    """Core md5-crypt computation (pure Python).

    Returns the encoded checksum string (no ``$`` prefix).
    """
    if isinstance(pwd, str):
        pwd = pwd.encode('utf-8')
    salt = salt.encode('ascii') if isinstance(salt, str) else salt
    pwd_len = len(pwd)

    # Digest B
    db = hashlib.md5(pwd + salt + pwd).digest()

    # Digest A
    a_ctx = hashlib.md5(pwd + _MD5_MAGIC + salt)
    a_ctx.update(_repeat_string(db, pwd_len))

    # Bit-loop (historical quirk: uses NUL byte, not db[0])
    i = pwd_len
    evenchar = pwd[:1]
    while i:
        a_ctx.update(b'\x00' if i & 1 else evenchar)
        i >>= 1
    da = a_ctx.digest()

    # 1000 rounds — same 42-round-block optimisation as sha2-crypt.
    pwd_pwd = pwd + pwd
    pwd_salt = pwd + salt
    perms = [pwd, pwd_pwd, pwd_salt, pwd_salt + pwd, salt + pwd, salt + pwd_pwd]
    data = [(perms[even], perms[odd]) for even, odd in _c_digest_offsets]

    dc = da
    # 23 full blocks of 42 = 966 rounds
    for _ in range(23):
        for even, odd in data:
            dc = hashlib.md5(odd + hashlib.md5(dc + even).digest()).digest()
    # 17 more pairs = 34 rounds → total 1000
    for even, odd in data[:17]:
        dc = hashlib.md5(odd + hashlib.md5(dc + even).digest()).digest()

    return _h64_encode_transposed(dc, _md5_transpose_map)


_MD5_RE = re.compile(r'^\$1\$([./0-9A-Za-z]{0,8})\$([./0-9A-Za-z]+)$')


def verify_md5_crypt(password, hash_str):
    """Verify *password* against a ``$1$…`` hash.  Returns ``bool``."""
    try:
        m = _MD5_RE.match(hash_str)
        if not m:
            return False
        salt, checksum = m.groups()
        computed = _raw_md5_crypt(password, salt)
        return hmac.compare_digest(computed, checksum)
    except Exception:
        return False


def generate_md5_crypt(password):
    """Hash *password* with md5-crypt.  Returns the full ``$1$…`` string."""
    salt = _generate_salt(8)
    checksum = _raw_md5_crypt(password, salt)
    return f'$1${salt}${checksum}'
