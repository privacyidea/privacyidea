# -*- coding: utf-8 -*-
"""
This test file tests the lib.crypto and lib.security.default
"""

from .base import MyTestCase
from privacyidea.lib.crypto import (encryptPin, encryptPassword, decryptPin,
                                    decryptPassword, urandom,
                                    get_rand_digit_str, geturandom,
                                    get_alphanum_str)
from privacyidea.lib.security.default import (SecurityModule,
                                              DefaultSecurityModule)

from flask import current_app

class SecurityModuleTestCase(MyTestCase):
    """
    Test the base class for security modules.
    """

    def test_00_security_module_base_class(self):
        hsm = SecurityModule({})
        self.assertTrue(hsm is not None, hsm)

        self.assertRaises(NotImplementedError, hsm.encrypt_password, "password")
        self.assertRaises(NotImplementedError, hsm.decrypt_password, "password")
        self.assertRaises(NotImplementedError, hsm.decrypt_pin, "password")
        self.assertRaises(NotImplementedError, hsm.encrypt_pin, "password")
        self.assertRaises(NotImplementedError, hsm.setup_module, {})
        self.assertRaises(NotImplementedError, hsm.random, 20)
        self.assertRaises(NotImplementedError, hsm.encrypt, "20")
        self.assertRaises(NotImplementedError, hsm.decrypt, "20")

    def test_01_default_security_module(self):
        config = current_app.config
        hsm = DefaultSecurityModule({"file": config.get("PI_ENCFILE")})
        hsm.setup_module({"file": config.get("PI_ENCFILE")})
        self.assertTrue(hsm is not None, hsm)
        self.assertTrue(hsm.secFile is not None, hsm.secFile)

    def test_01_no_file_in_config(self):
        self.assertRaises(Exception, DefaultSecurityModule, {})

    def test_04_random(self):
        config = current_app.config
        hsm = DefaultSecurityModule({"file": config.get("PI_ENCFILE"),
                                     "crypted": True})
        r = hsm.random(20)
        self.assertTrue(len(r) == 20, r)

    def test_05_encrypt_decrypt(self):
        config = current_app.config
        hsm = DefaultSecurityModule({"file": config.get("PI_ENCFILE")})

        cipher = hsm.encrypt("data", "iv12345678901234")
        text = hsm.decrypt(cipher, "iv12345678901234")
        self.assertTrue(text == "data", text)

        cipher = hsm.encrypt_pin("data")
        text = hsm.decrypt_pin(cipher)
        self.assertTrue(text == "data", text)

        cipher = hsm.encrypt_password("data")
        text = hsm.decrypt_password(cipher)
        self.assertTrue(text == "data", text)

    def test_06_password_encrypt_decrypt(self):
        res = DefaultSecurityModule.password_encrypt("secrettext", "password1")
        self.assertTrue(len(res) == len(
            "80f1833450a74224c32d03fe4161735c"
            ":c1944e8c0982d5c35992a9b25abad18a2"
            "8cac15585ed2fbab05bd2b1ea2cc44b"), res)

        res = DefaultSecurityModule.password_decrypt(res, "password1")
        self.assertTrue(res == "secrettext", res)

        # encrypt and decrypt binary data like the enckey
        enckey = geturandom(96)
        cipher = DefaultSecurityModule.password_encrypt(enckey, "top secret "
                                                                "!!!")
        clear = DefaultSecurityModule.password_decrypt(cipher, "top secret "
                                                               "!!!")
        self.assertTrue(enckey == clear, (enckey, clear))

        # encrypt and decrypt binary data like the enckey
        enckey = geturandom(96)
        cipher = DefaultSecurityModule.password_encrypt(enckey, "topSecret123!")
        clear = DefaultSecurityModule.password_decrypt(cipher, "topSecret123!")
        self.assertTrue(enckey == clear, (enckey, clear))

    def test_07_encrypted_key_file(self):
        config = current_app.config
        hsm = DefaultSecurityModule({"file": config.get("PI_ENCFILE_ENC"),
                                     "crypted": True})
        # The HSM is not ready, since the file is crypted and we did not
        # provide the password, yet
        self.assertFalse(hsm.is_ready)

        # Now, provide the password, that will decrypt the encrypted file
        # But the password is missing
        self.assertRaises(Exception, hsm.setup_module, {})

        # As long as the HSM is not ready, we can not encrypt and not decrypt
        self.assertRaises(Exception, hsm.encrypt, "data", "iv")
        self.assertRaises(Exception, hsm.decrypt, "data", "iv")

        # If we provide a wrong password, that decryption will fail with a
        # unicode error and an exception is raised.
        self.assertRaises(Exception, hsm.setup_module,
                          {"password": "wrong PW"})

        # Now we provide the password
        hsm.setup_module({"password": "test1234!"})
        self.assertTrue(hsm.is_ready)
        self.assertTrue(0 in hsm.secrets, hsm.secrets)
        self.assertTrue(1 in hsm.secrets, hsm.secrets)
        self.assertTrue(2 in hsm.secrets, hsm.secrets)

        # test _get_secret
        # this raises an exception, that the file does not contain a 4th key
        self.assertRaises(Exception, hsm._get_secret, 4)

        # calling the same slot two times, returns the cache the second time
        self.assertTrue(hsm._get_secret(2))
        self.assertTrue(hsm._get_secret(2))


class CryptoTestCase(MyTestCase):
    """
    Test the token on the database level
    """

    def test_00_encrypt_decrypt_pin(self):
        r = encryptPin("test")
        pin = decryptPin(r)
        self.assertTrue(pin == "test", (r, pin))

    def test_01_encrypt_decrypt_pass(self):
        r = encryptPassword("passwörd")
        pin = decryptPassword(r)
        self.assertTrue(pin == "passwörd", (r, pin))


class RandomTestCase(MyTestCase):
    """
    Test the random functions from lib.crypto
    """

    def test_00_uniform(self):
        r = urandom.uniform(100)
        self.assertTrue(r <= 100, r)
        r = urandom.uniform(100, 200)
        self.assertTrue(100 <= r <= 200, r)
        r = urandom.uniform(200, 100)
        self.assertTrue(100 <= r <= 200, r)


    def test_01_randint(self):
        r = urandom.randint(100)
        self.assertTrue(r <= 100, r)
        r = urandom.randint(100, 200)
        self.assertTrue(100 <= r <= 200, r)
        r = urandom.randint(200, 100)
        self.assertTrue(100 <= r <= 200, r)

    def test_02_choice(self):
        list = "ABCDEFG"
        r = urandom.choice(list)
        self.assertTrue(r in list, r)
        self.assertTrue("H" != r, r)

    def test_03_randrange(self):
        r = urandom.randrange(100, 200, step=10)
        self.assertTrue(100<=r<=200, r)
        self.assertTrue(r % 10 == 0, r)
        r = urandom.randrange(100)
        self.assertTrue(r <= 100)

    def test_04_get_rand_digit_str(self):
        self.assertRaises(ValueError, get_rand_digit_str, 1)
        r = get_rand_digit_str(2)
        self.assertTrue(len(r) == 2, r)
        r = get_rand_digit_str(1001)
        self.assertTrue(len(r) == 1001, r)
        r = get_rand_digit_str(19182)
        self.assertTrue(len(r) == 19182)

    def test_05_get_alphanum_str(self):
        r = get_alphanum_str(20)
        self.assertEqual(len(r), 20)
