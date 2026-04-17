"""
Unit tests for privacyidea.lib.resolvers.unix_crypt

Tests the pure-Python implementations of $1$ (md5_crypt), $5$ (sha256_crypt),
and $6$ (sha512_crypt) against known test vectors from the Drepper spec and
passlib.
"""
import unittest

from privacyidea.lib.resolvers.unix_crypt import (
    verify_md5_crypt,
    verify_sha256_crypt,
    verify_sha512_crypt,
    generate_md5_crypt,
    generate_sha256_crypt,
    generate_sha512_crypt,
    _h64_encode,
    _h64_encode_transposed,
    _repeat_string,
)


class SHA512CryptTestCase(unittest.TestCase):
    """Test vectors for sha512_crypt ($6$)."""

    # passlib built-in test vector (rounds=1000)
    KNOWN_HASHES = [
        ("test",
         "$6$rounds=1000$test$2M/Lx6MtobqjLjobw0Wmo4Q5OFx5nVLJvmgseatA6oMn"
         "yWeBdRDx4DU.1H3eGmse6pgsOgDisWBGI5c7TZauS0"),
    ]

    # Real hashes from the privacyidea test fixture (default rounds=5000)
    FIXTURE_HASHES = [
        ("test",
         "$6$2Qgbc373ijbL0dCj$s3McoKE6YZaHbicinECTJuLXTOkSsv1SJ3pjsJFAmIVb"
         "8DtnZdSi8NiYgqerhf9MZYXqbNzaG6u3di1ii43mZ/"),
        ("password",
         "$6$/TytwRo.7v7GqQUX$gtKKgyc.FFf2N9Ab74OxNWbGp8icog6YbcSvnRBlW3RAv"
         "OsUn6GO.YwHTfqYmZzv4OJ6LiEMNMSBdsHhmK4dd/"),
        ("spass",
         "$6$/e2CFzHmqwoyODq2$VGVjEGePob0vFO26W82ZORxvMLT1AcUC94ptLiS0H4qoB5"
         "EV..6yTwQ3ugxJhNGlaLK0n1bXSLjaMIHGlo8FB1"),
        ("pthru",
         "$6$aaKECZpmVcO4k4P4$pNsPFB1QpoWVmCZmQzUFLgs/VPHZK2FZxd5YFRU9upD51"
         "1QUy3Lz2ulbHGIxw5JIDXMOQPLoaY7km9BLf4Kiq1"),
        ("superSecret",
         "$6$m28emqdIYdHEtCwl$GSCGgPaSuq9pMiUD9kfdpWAJsKToxdBTC0i7RE0xTWKPob"
         "chH0BEATQaMDFsmEQ20PR1yABMgRRPrehzIaF5k1"),
        ("pw%45#test",
         "$6$v2DXJ54ZkmA3bv2R$g6f4A8c8Sfy10r5F99uF.s5IH1pQue.4cEzyXWjtiZe9Gt"
         "YB58nAKTeCTdok3lyI0LuF3Tq6MQIblpHLgW3Vj1"),
    ]

    # Unicode password from test fixture
    UNICODE_HASH = (
        "pässwörd",
        "$6$fQqNLMhHk5BeU/Xv$tk2VAYncX5RZLPxA5hNkPjx2d65rhjZKVYR/w2EtL.2rus"
        "QNq/6s06acuGe7gZ.5Vk8QwdcVgPFVcnqg4s.qq0",
    )

    def test_known_vectors(self):
        for password, hash_str in self.KNOWN_HASHES:
            self.assertTrue(verify_sha512_crypt(password, hash_str),
                            f"Failed to verify {password!r}")

    def test_fixture_hashes(self):
        for password, hash_str in self.FIXTURE_HASHES:
            self.assertTrue(verify_sha512_crypt(password, hash_str),
                            f"Failed to verify {password!r}")

    def test_unicode_password(self):
        password, hash_str = self.UNICODE_HASH
        self.assertTrue(verify_sha512_crypt(password, hash_str))

    def test_wrong_password(self):
        for password, hash_str in self.KNOWN_HASHES + self.FIXTURE_HASHES:
            self.assertFalse(verify_sha512_crypt("wrongpassword", hash_str))

    def test_generate_and_verify(self):
        h = generate_sha512_crypt("mypassword", rounds=1000)
        self.assertTrue(h.startswith("$6$rounds=1000$"))
        self.assertTrue(verify_sha512_crypt("mypassword", h))
        self.assertFalse(verify_sha512_crypt("other", h))

    def test_generate_default_rounds(self):
        h = generate_sha512_crypt("test")
        self.assertTrue(h.startswith("$6$rounds=656000$"))
        self.assertTrue(verify_sha512_crypt("test", h))

    def test_malformed_hash(self):
        self.assertFalse(verify_sha512_crypt("test", "$6$"))
        self.assertFalse(verify_sha512_crypt("test", "notahash"))
        self.assertFalse(verify_sha512_crypt("test", ""))

    def test_reject_sha256_hash(self):
        """$5$ hash must not verify as $6$."""
        sha256_hash = "$5$rounds=1000$test$QmQADEXMG8POI5WDsaeho0P36yK3Tcrgboabng6bkb/"
        self.assertFalse(verify_sha512_crypt("test", sha256_hash))


class SHA256CryptTestCase(unittest.TestCase):
    """Test vectors for sha256_crypt ($5$)."""

    KNOWN_HASHES = [
        ("test",
         "$5$rounds=1000$test$QmQADEXMG8POI5WDsaeho0P36yK3Tcrgboabng6bkb/"),
        ("testpassword",
         "$5$mqbRfhh1P.AbtPL0$pnhYuGNPkAJFa6tnF2dvdAusRlixZHjIWlsCqOz9sL2"),
    ]

    def test_known_vectors(self):
        for password, hash_str in self.KNOWN_HASHES:
            self.assertTrue(verify_sha256_crypt(password, hash_str),
                            f"Failed to verify {password!r}")

    def test_wrong_password(self):
        for password, hash_str in self.KNOWN_HASHES:
            self.assertFalse(verify_sha256_crypt("wrongpassword", hash_str))

    def test_generate_and_verify(self):
        h = generate_sha256_crypt("mypassword", rounds=1000)
        self.assertTrue(h.startswith("$5$rounds=1000$"))
        self.assertTrue(verify_sha256_crypt("mypassword", h))
        self.assertFalse(verify_sha256_crypt("other", h))

    def test_reject_sha512_hash(self):
        """$6$ hash must not verify as $5$."""
        sha512_hash = ("$6$rounds=1000$test$2M/Lx6MtobqjLjobw0Wmo4Q5OFx5nVLJ"
                        "vmgseatA6oMnyWeBdRDx4DU.1H3eGmse6pgsOgDisWBGI5c7TZauS0")
        self.assertFalse(verify_sha256_crypt("test", sha512_hash))

    def test_implicit_rounds(self):
        """Default rounds=5000 omits 'rounds=' from the hash string."""
        h = generate_sha256_crypt("test", rounds=5000)
        self.assertNotIn("rounds=", h)
        self.assertTrue(verify_sha256_crypt("test", h))


class MD5CryptTestCase(unittest.TestCase):
    """Test vectors for md5_crypt ($1$)."""

    KNOWN_HASHES = [
        ("test", "$1$test$pi/xDtU5WFVRqYS6BMU8X/"),
        ("password", "$1$3azHgidD$SrJPt7B.9rekpmwJwtON31"),
        ("testpassword", "$1$CktFSGbj$pM2OHk4XSJuEntMjgEVTq0"),
    ]

    def test_known_vectors(self):
        for password, hash_str in self.KNOWN_HASHES:
            self.assertTrue(verify_md5_crypt(password, hash_str),
                            f"Failed to verify {password!r}")

    def test_wrong_password(self):
        for password, hash_str in self.KNOWN_HASHES:
            self.assertFalse(verify_md5_crypt("wrongpassword", hash_str))

    def test_generate_and_verify(self):
        h = generate_md5_crypt("mypassword")
        self.assertTrue(h.startswith("$1$"))
        self.assertTrue(verify_md5_crypt("mypassword", h))
        self.assertFalse(verify_md5_crypt("other", h))

    def test_malformed_hash(self):
        self.assertFalse(verify_md5_crypt("test", "$1$"))
        self.assertFalse(verify_md5_crypt("test", "notahash"))
        self.assertFalse(verify_md5_crypt("test", ""))

    def test_empty_password(self):
        h = generate_md5_crypt("")
        self.assertTrue(verify_md5_crypt("", h))
        self.assertFalse(verify_md5_crypt("notempty", h))


class H64EncodeTestCase(unittest.TestCase):
    """Test the crypt-style base64 encoding helpers."""

    def test_encode_empty(self):
        self.assertEqual(_h64_encode(b''), '')

    def test_encode_single_byte(self):
        # 0x00 -> two chars: _ITOA64[0], _ITOA64[0] = '..'
        self.assertEqual(_h64_encode(b'\x00'), '..')

    def test_encode_three_bytes(self):
        # 3 bytes should produce 4 chars
        result = _h64_encode(b'\x01\x02\x03')
        self.assertEqual(len(result), 4)

    def test_encode_transposed(self):
        data = bytes(range(4))  # 0x00, 0x01, 0x02, 0x03
        offsets = (2, 0, 3, 1)
        # transposed = 0x02, 0x00, 0x03, 0x01
        expected = _h64_encode(bytes([0x02, 0x00, 0x03, 0x01]))
        self.assertEqual(_h64_encode_transposed(data, offsets), expected)

    def test_repeat_string(self):
        self.assertEqual(_repeat_string(b'abc', 7), b'abcabca')
        self.assertEqual(_repeat_string(b'abc', 3), b'abc')
        self.assertEqual(_repeat_string(b'abc', 1), b'a')
