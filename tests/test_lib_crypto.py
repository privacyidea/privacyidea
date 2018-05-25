# -*- coding: utf-8 -*-
"""
This test file tests the lib.crypto and lib.security.default
"""
from mock import call

from privacyidea.lib.error import HSMException
from .base import MyTestCase
# need to import pkcs11mock before PyKCS11, because it may be replaced by a mock module
from .pkcs11mock import PKCS11Mock
from privacyidea.lib.crypto import (encryptPin, encryptPassword, decryptPin,
                                    decryptPassword, urandom,
                                    get_rand_digit_str, geturandom,
                                    get_alphanum_str,
                                    hash_with_pepper, verify_with_pepper, aes_encrypt_b64, aes_decrypt_b64, _get_hsm)
from privacyidea.lib.security.default import (SecurityModule,
                                              DefaultSecurityModule)
from privacyidea.lib.security.aeshsm import AESHardwareSecurityModule

from flask import current_app
from PyKCS11 import PyKCS11Error


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

    def test_02_encrypt_decrypt_eas_base64(self):
        import os
        key = os.urandom(16)
        data = "This is so secret!"
        s = aes_encrypt_b64(key, data)
        d = aes_decrypt_b64(key, s)
        self.assertEqual(data, d)

        otp_seed = os.urandom(20)
        s = aes_encrypt_b64(key, otp_seed)
        d = aes_decrypt_b64(key, s)
        self.assertEqual(otp_seed, d)

        otp_seed = os.urandom(32)
        s = aes_encrypt_b64(key, otp_seed)
        d = aes_decrypt_b64(key, s)
        self.assertEqual(otp_seed, d)


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

    def test_06_hash_pepper(self):
        h = hash_with_pepper("superPassword")
        self.assertTrue("$pbkdf2"in h, h)
        self.assertTrue("$10023"in h, h)

        r = verify_with_pepper(h, "superPassword")
        self.assertEqual(r, True)

        r = verify_with_pepper(h, "super Password")
        self.assertEqual(r, False)


class AESHardwareSecurityModuleTestCase(MyTestCase):
    """
    Test the AES HSM class for security modules.
    """

    def test_01_instantiate(self):
        with PKCS11Mock() as pkcs11:
            hsm = AESHardwareSecurityModule({
                "module": "testmodule",
                "password": "test123!"
            })
            self.assertIsNotNone(hsm)
            self.assertTrue(hsm.is_ready)
            self.assertIs(hsm.session, pkcs11.session_mock)
            self.assertEqual(pkcs11.mock.openSession.call_count, 1)

    def test_02_basic(self):
        with PKCS11Mock() as pkcs11:
            hsm = AESHardwareSecurityModule({
                "module": "testmodule",
            })
            self.assertFalse(hsm.is_ready)
            self.assertEqual(pkcs11.mock.openSession.call_count, 0)
            hsm.setup_module({
                "password": "test123!"
            })
            self.assertTrue(hsm.is_ready)
            self.assertEqual(pkcs11.mock.openSession.call_count, 1)
            self.assertIs(hsm.session, pkcs11.session_mock)

            # mock just returns \x00\x01... for random values
            self.assertEqual(hsm.random(4), "\x00\x01\x02\x03")
            pkcs11.session_mock.generateRandom.assert_called_once_with(4)

            password = "topSekr3t" * 16
            crypted = hsm.encrypt_password(password)
            # to generate the IV
            pkcs11.session_mock.generateRandom.assert_called_with(16)

            text = hsm.decrypt_password(crypted)
            self.assertEqual(text, password)
            self.assertEqual(pkcs11.session_mock.encrypt.call_count, 1)
            self.assertEqual(pkcs11.session_mock.encrypt.call_count, 1)

            # during the whole usage, we have only used one session
            self.assertEqual(pkcs11.mock.openSession.call_count, 1)

    def test_03_retry(self):
        with PKCS11Mock() as pkcs11:
            hsm = AESHardwareSecurityModule({
                "module": "testmodule",
            })
            hsm.setup_module({
                "password": "test123!"
            })
            self.assertTrue(hsm.is_ready)
            self.assertIs(hsm.session, pkcs11.session_mock)

            # session is opened once
            self.assertEqual(pkcs11.mock.openSession.mock_calls, [
                call(slot=1)
            ])

            # simulate that encryption succeeds after five tries
            password = "topSekr3t" * 16
            with pkcs11.simulate_failure(pkcs11.session_mock.encrypt, 5):
                encrypted = hsm.encrypt_password(password)
                # the session has been opened initially, and five times after that
                self.assertEqual(pkcs11.mock.openSession.mock_calls, [call(slot=1)] * 6)

            # simulate that decryption succeeds after five tries
            with pkcs11.simulate_failure(pkcs11.session_mock.decrypt, 5):
                self.assertEqual(hsm.decrypt_password(encrypted), password)
                # the session has been opened initially, five times during encryption, and five times now
                self.assertEqual(pkcs11.mock.openSession.mock_calls, [call(slot=1)] * 11)

            # simulate that random generation succeeds after five tries
            with pkcs11.simulate_failure(pkcs11.session_mock.generateRandom, 5):
                self.assertEqual(hsm.random(4), "\x00\x01\x02\x03")
                self.assertEqual(pkcs11.mock.openSession.mock_calls, [call(slot=1)] * 16)

    def test_04_fail_encrypt(self):
        with PKCS11Mock() as pkcs11:
            hsm = AESHardwareSecurityModule({
                "module": "testmodule",
            })
            hsm.setup_module({
                "password": "test123!"
            })
            self.assertTrue(hsm.is_ready)
            self.assertIs(hsm.session, pkcs11.session_mock)

            # session is opened once
            self.assertEqual(pkcs11.mock.openSession.mock_calls, [
                call(slot=1)
            ])

            # simulate that encryption still fails after five tries
            password = "topSekr3t" * 16
            with pkcs11.simulate_failure(pkcs11.session_mock.encrypt, 6):
                with self.assertRaises(HSMException):
                    hsm.encrypt_password(password)
                # the session has been opened initially, and six times after that
                self.assertEqual(pkcs11.mock.openSession.mock_calls, [call(slot=1)] * 7)

    def test_05_hsm_recovery(self):
        with PKCS11Mock() as pkcs11:
            hsm = AESHardwareSecurityModule({
                "module": "testmodule",
            })
            hsm.setup_module({
                "password": "test123!"
            })
            self.assertTrue(hsm.is_ready)
            self.assertIs(hsm.session, pkcs11.session_mock)

            self.assertEqual(pkcs11.mock.openSession.mock_calls, [
                call(slot=1)
            ])

            # encryption+decryption succeeds once
            password = "topSekr3t" * 16
            crypted = hsm.encrypt_password(password)
            text = hsm.decrypt_password(crypted)
            self.assertEqual(text, password)

            # simulate that the HSM disappears after that, so we cannot
            # even open a session
            with pkcs11.simulate_failure(pkcs11.session_mock.generateRandom, 1), \
                pkcs11.simulate_failure(pkcs11.mock.openSession, 1):
                with self.assertRaises(PyKCS11Error):
                    hsm.encrypt_password(password)
                self.assertEqual(pkcs11.mock.openSession.mock_calls, [call(slot=1)] * 2)

            # the Security Module is in a defunct state now
            # but we can recover from it!
            # simulate one failure, because this will make the security module
            # acquire a new session
            with pkcs11.simulate_failure(pkcs11.session_mock.generateRandom, 1):
                crypted = hsm.encrypt_password(password)
            text = hsm.decrypt_password(crypted)
            self.assertEqual(text, password)
            self.assertEqual(pkcs11.mock.openSession.mock_calls, [call(slot=1)] * 3)

    def test_06_wrong_password(self):
        with PKCS11Mock() as pkcs11:
            hsm = AESHardwareSecurityModule({
                "module": "testmodule",
            })
            with pkcs11.simulate_failure(pkcs11.mock.openSession, 1):
                with self.assertRaises(PyKCS11Error):
                    hsm.setup_module({
                        "password": "test123!"
                    })
            self.assertFalse(hsm.is_ready)
            hsm.setup_module({
                "password": "test123!"
            })
            self.assertTrue(hsm.is_ready)
            self.assertIs(hsm.session, pkcs11.session_mock)


class AESHardwareSecurityModuleLibLevelTestCase(MyTestCase):
    pkcs11 = PKCS11Mock()

    def setUp(self):
        """ set up config to load the AES HSM module """
        current_app.config["PI_HSM_MODULE"] = "privacyidea.lib.security.aeshsm.AESHardwareSecurityModule"
        current_app.config["PI_HSM_MODULE_MODULE"] = "testmodule"
        current_app.config["PI_HSM_MODULE_PASSWORD"] = "test123!"
        with self.pkcs11:
            MyTestCase.setUp(self)

    def test_01_simple(self):
        with self.pkcs11:
            self.assertIsInstance(_get_hsm(), AESHardwareSecurityModule)
            r = encryptPin("test")
            pin = decryptPin(r)
            self.assertEqual(pin, "test")

            self.assertTrue(_get_hsm().is_ready)
            self.assertEqual(self.pkcs11.session_mock.encrypt.call_count, 1)

    def test_02_fault_recovery(self):
        with self.pkcs11:
            hsm = _get_hsm()
            self.assertIsInstance(hsm, AESHardwareSecurityModule)

            # encryption initially works
            r = encryptPin("test")
            pin = decryptPin(r)
            self.assertEqual(pin, "test")
            self.assertTrue(hsm.is_ready)

            # the HSM disappears
            generate_random_call_count = self.pkcs11.session_mock.generateRandom.call_count
            open_session_call_count = self.pkcs11.mock.openSession.call_count
            with self.pkcs11.simulate_disconnect(100):
                with self.assertRaises(PyKCS11Error):
                    encryptPin("test")
                # we have tried to generate a random number once
                self.assertEqual(self.pkcs11.session_mock.generateRandom.call_count,
                                 generate_random_call_count + 1)
                # we have tried to open a new session once
                self.assertEqual(self.pkcs11.mock.openSession.call_count,
                                 open_session_call_count + 1)

            # HSM is now defunct

            # try to recover now
            r = encryptPin("test")
            pin = decryptPin(r)
            self.assertEqual(pin, "test")
