# -*- coding: utf-8 -*-
"""
This test file tests the lib.crypto and lib.security.default
"""
from mock import call
import binascii

from privacyidea.config import TestingConfig
from privacyidea.lib.error import HSMException
from .base import MyTestCase, OverrideConfigTestCase
# need to import pkcs11mock before PyKCS11, because it may be replaced by a mock module
from .pkcs11mock import PKCS11Mock
from privacyidea.lib.crypto import (encryptPin, encryptPassword, decryptPin,
                                    decryptPassword, urandom, get_rand_digit_str,
                                    geturandom, get_alphanum_str, hash_with_pepper,
                                    verify_with_pepper, aes_encrypt_b64, aes_decrypt_b64,
                                    get_hsm, init_hsm, set_hsm_password, hash,
                                    encrypt, decrypt, Sign, generate_keypair,
                                    generate_password, pass_hash, verify_pass_hash)
from privacyidea.lib.utils import to_bytes, to_unicode
from privacyidea.lib.security.default import (SecurityModule,
                                              DefaultSecurityModule)
from privacyidea.lib.security.aeshsm import AESHardwareSecurityModule

from flask import current_app
import PyKCS11
from PyKCS11 import PyKCS11Error
import string
import passlib.hash


class SecurityModuleTestCase(MyTestCase):
    """
    Test the base class for security modules.
    """

    def test_00_security_module_base_class(self):
        hsm = SecurityModule({})
        self.assertTrue(hsm is not None, hsm)

        self.assertRaises(NotImplementedError, hsm.setup_module, {})
        self.assertRaises(NotImplementedError, hsm.random, 20)
        self.assertRaises(NotImplementedError, hsm.encrypt, "20", 'abcd')
        self.assertRaises(NotImplementedError, hsm.decrypt, "20", 'abcd')

    def test_01_default_security_module(self):
        config = current_app.config
        hsm = DefaultSecurityModule({"file": config.get("PI_ENCFILE")})
        hsm.setup_module({"file": config.get("PI_ENCFILE")})
        self.assertTrue(hsm is not None, hsm)
        self.assertTrue(hsm.secFile is not None, hsm.secFile)
        self.assertTrue(hsm.is_ready)

    def test_01_no_file_in_config(self):
        self.assertRaises(Exception, DefaultSecurityModule, {})

    def test_04_random(self):
        config = current_app.config
        hsm = DefaultSecurityModule({"file": config.get("PI_ENCFILE"),
                                     "crypted": True})
        r = hsm.random(20)
        self.assertTrue(len(r) == 20, r)
        self.assertFalse(hsm.is_ready)

    def test_05_encrypt_decrypt(self):
        config = current_app.config
        hsm = DefaultSecurityModule({"file": config.get("PI_ENCFILE")})

        cipher = hsm.encrypt(b"data", b"iv12345678901234")
        self.assertEqual(binascii.b2a_hex(cipher), b"ac17c4a5aa8703d7129c09158adc5fd4")
        text = hsm.decrypt(cipher, b"iv12345678901234")
        self.assertEqual(text, b"data")

        # check that we can decrypt values with default PKCS7 padding
        iv = b'1234567890abcdef'
        pkcs7_cipher = '98d005d6f87c01f1719199bc3df1beb8'
        legacy_cipher = 'bbcaff52640f9dc90be1c4e1df8a70b55a1194cc67d155722054317901e3646a'
        self.assertEqual(b'Hallo Welt', hsm.decrypt(binascii.unhexlify(pkcs7_cipher), iv))

        # check that we can decrypt values with legacy padding
        self.assertEqual(b'Hallo Welt', hsm.decrypt(binascii.unhexlify(legacy_cipher), iv))

        cipher = hsm.encrypt_pin("pin")
        text = hsm.decrypt_pin(cipher)
        self.assertEqual(text, "pin")

        cipher = hsm.encrypt_password("password")
        text = hsm.decrypt_password(cipher)
        self.assertEqual(text, "password")

    def test_06_password_encrypt_decrypt(self):
        res = DefaultSecurityModule.password_encrypt("secrettext", "password1")
        self.assertTrue(len(res) == len(
            "80f1833450a74224c32d03fe4161735c"
            ":c1944e8c0982d5c35992a9b25abad18a2"
            "8cac15585ed2fbab05bd2b1ea2cc44b"), res)

        res = DefaultSecurityModule.password_decrypt(res, "password1")
        self.assertTrue(res == b"secrettext", res)

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

        # decrypt some pins generated with 2.23
        pin1 = 'd2c920ad10513c8ea322b522751185a3:54f068cffb43ada1edd024087da614ec'
        self.assertEqual(decryptPin(pin1), 'test')
        pin2 = '223f414872122ad112eb9f17b05da0b8:123079d997cd18601414830ab7c97678'
        self.assertEqual(decryptPin(pin2), 'test')
        pin3 = '4af7590600286becde70b99b10493104:09e4133652c609f9697e1923cde72904'
        self.assertEqual(decryptPin(pin3), '1234')

    def test_01_encrypt_decrypt_pass(self):
        r = encryptPassword("passwörd".encode('utf8'))
        # encryptPassword returns unicode
        self.assertTrue(isinstance(r, str))
        pin = decryptPassword(r)
        # decryptPassword always returns unicode
        self.assertEqual(pin, "passwörd")

        r = encryptPassword("passwörd")
        pin = decryptPassword(r)
        self.assertEqual(pin, "passwörd")

        # decrypt some passwords generated with 2.23
        pw1 = '3d1bf9db4c75469b4bb0bc7c70133181:2c27ac3839ed2213b8399d0471b17136'
        self.assertEqual(decryptPassword(pw1), 'test123')
        pw2 = '3a1be65a234f723fe5c6969b818582e1:08e51d1c65aa74c4988d094c40cb972c'
        self.assertEqual(decryptPassword(pw2), 'test123')
        pw3 = '7a4d5e2f26978394e33715bc3e8188a3:90b2782112ad7bbc5b48bd10e5c7c096cfe4ef7d9d11272595dc5b6c7f21d98a'
        self.assertEqual(decryptPassword(pw3, ), 'passwörd')

        # TODO: add checks for broken paddings/encrypted values and malformed enc_data

        not_valid_password = b"\x01\x02\x03\x04\xff"
        r = encryptPassword(not_valid_password)
        # A non valid password will raise an exception during decryption
        self.assertEqual(decryptPassword(r), 'FAILED TO DECRYPT PASSWORD!')

        # A value with missing colon (IV) will fail to decrypt
        self.assertEqual(decryptPassword('test'), 'FAILED TO DECRYPT PASSWORD!')

    def test_02_encrypt_decrypt_eas_base64(self):
        import os
        key = os.urandom(16)
        data = b"This is so secret!"
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

        # check some data generated with 2.23
        hex_key = 'f84c2ddb09dee2a88194d5ac2156a8e4'
        data = b'secret data'
        enc_data = 'WNfUSNBNZF5kaPfujW8ueUi5Afas47pQ/3FHc3VymWM='
        d = aes_decrypt_b64(binascii.unhexlify(hex_key), enc_data)
        self.assertEqual(data, d)
        enc_data = 'RDDvdAJhCnw/tlYscTxv+6idHAQnQFY5VpUK8SFflYQ='
        d = aes_decrypt_b64(binascii.unhexlify(hex_key), enc_data)
        self.assertEqual(data, d)

        # TODO: add checks for broken paddings/encrypted values and malformed enc_data

    def test_03_hash(self):
        import os
        val = os.urandom(16)
        seed = os.urandom(16)
        h1 = hash(val, seed)
        self.assertEqual(h1, hash(val, seed))
        seed2 = os.urandom(16)
        self.assertNotEqual(h1, hash(val, seed2))

    def test_04_encrypt_decrypt_data(self):
        import os
        data = os.urandom(50)
        iv = os.urandom(16)
        c = encrypt(data, iv)
        # verify
        d = decrypt(binascii.unhexlify(c), iv)
        self.assertEqual(data, d)

        s = "Encryption Text with unicode chars: äöü"
        c = encrypt(s, iv)
        d = decrypt(binascii.unhexlify(c), iv)
        self.assertEqual(s, d.decode('utf8'))

        # TODO: add checks for broken paddings/encrypted values and malformed enc_data

        # check some data generated with 2.23
        s = 'passwörd'.encode('utf8')
        iv_hex = 'cd5245a2875007d30cc049c2e7eca0c5'
        enc_data_hex = '7ea55168952b33131077f4249cf9e52b5f2b572214ace13194c436451fe3788c'
        self.assertEqual(s, decrypt(binascii.unhexlify(enc_data_hex),
                                    binascii.unhexlify(iv_hex)))
        enc_data_hex = 'fb79a04d69e832aec8ffb4bbfe031b3bd28a2840150212d8c819e' \
                       '362b1711cc389aed70eaf27af53131ea446095da80e88c4caf791' \
                       'c709e9581ff0a5f1e19228dc4c3c278d148951acaab9a164c1770' \
                       '7166134f4ba6111055c65d72771c6f59c2dc150a53753f2cf4c47' \
                       'ec02901022f02a054d1fc7678fd4f66b47967a5d222a'
        self.assertEqual(b'\x01\x02' * 30,
                         decrypt(binascii.unhexlify(enc_data_hex),
                                 binascii.unhexlify(iv_hex)))

    def test_05_encode_decode(self):
        b_str = b'Hello World'
        self.assertEqual(to_unicode(b_str), b_str.decode('utf8'))
        u_str = 'Hello Wörld'
        self.assertEqual(to_unicode(u_str), u_str)
        self.assertEqual(to_bytes(b_str), b_str)
        self.assertEqual(to_bytes(u_str), u_str.encode('utf8'))

    def test_10_generate_keypair(self):
        keypub, keypriv = generate_keypair(rsa_keysize=4096)
        self.assertTrue(keypub.startswith("-----BEGIN RSA PUBLIC KEY-----"), keypub)
        self.assertTrue(keypriv.startswith("-----BEGIN RSA PRIVATE KEY-----"), keypriv)


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
        self.assertTrue(100 <= r <= 200, r)
        self.assertTrue(r % 10 == 0, r)
        r = urandom.randrange(100)
        self.assertTrue(r <= 100)

    def test_04_get_rand_digit_str(self):
        self.assertRaises(ValueError, get_rand_digit_str, 1)
        r = get_rand_digit_str(2)
        self.assertTrue(len(r) == 2, r)
        r = get_rand_digit_str(1001)
        self.assertTrue(len(r) == 1001, r)
        r = get_rand_digit_str(2500)
        self.assertTrue(len(r) == 2500)

    def test_05_get_alphanum_str(self):
        r = get_alphanum_str(20)
        self.assertEqual(len(r), 20)

    def test_06_hash_pepper(self):
        h = hash_with_pepper("superPassword")
        self.assertTrue("$argon2" in h, h)

        r = verify_with_pepper(h, "superPassword")
        self.assertEqual(r, True)

        r = verify_with_pepper(h, "super Password")
        self.assertEqual(r, False)

    def test_06_test_old_passwords(self):
        phash = passlib.hash.pbkdf2_sha512.hash(current_app.config.get("PI_PEPPER", "") + "test")
        self.assertTrue(phash.startswith("$pbkdf2"))
        r = verify_with_pepper(phash, "test")
        self.assertTrue(r)

    def test_07_generate_password(self):
        # test given default characters
        pass_numeric = generate_password(size=12, characters=string.digits)
        self.assertTrue(pass_numeric.isdigit())
        self.assertEqual(len(pass_numeric), 12)

        # test requirements, we loop to get some statistics
        default_chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
        for i in range(10):
            password_req = generate_password(size=3, characters=default_chars, requirements=["AB", "12"])
            # a character from each requirement must be found
            self.assertTrue(
                any(char in "AB" for char in password_req) and any(char in "12" for char in password_req))
            self.assertEqual(len(password_req), 3)

        # use letters for base and numbers for requirements
        # this cannot be achieved with a pin policy
        password = generate_password(size=10, characters=string.ascii_letters,
                                     requirements=[string.digits, string.digits, string.digits])
        self.assertEqual(10, len(password))
        self.assertEqual(3, sum(c.isdigit() for c in password))
        self.assertEqual(7, sum(c.isalpha() for c in password))

        # requirements define the minimum length of a password
        password = generate_password(size=0, characters='ABC',
                                     requirements=['1', '2', '3'])
        self.assertEqual(3, len(password))

        # empty characters variable raises an IndexError
        self.assertRaises(IndexError, generate_password, characters='')

        # negative size without requirements results in an empty password
        password = generate_password(size=-1)
        self.assertEqual(password, '')


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
            self.assertEqual(hsm.random(4), b"\x00\x01\x02\x03")
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
            with pkcs11.simulate_failure(pkcs11.session_mock.encrypt, 5,
                                         error=PyKCS11.CKR_SESSION_HANDLE_INVALID):
                encrypted = hsm.encrypt_password(password)
                # the session has been opened initially, and five times after that
                self.assertEqual(pkcs11.mock.openSession.mock_calls, [call(slot=1)] * 6)

            # simulate that decryption succeeds after five tries
            with pkcs11.simulate_failure(pkcs11.session_mock.decrypt, 5,
                                         error=PyKCS11.CKR_SESSION_HANDLE_INVALID):
                self.assertEqual(hsm.decrypt_password(encrypted), password)
                # the session has been opened initially, five times during encryption, and five times now
                self.assertEqual(pkcs11.mock.openSession.mock_calls, [call(slot=1)] * 11)

            # simulate that random generation succeeds after five tries
            with pkcs11.simulate_failure(pkcs11.session_mock.generateRandom, 5,
                                         error=PyKCS11.CKR_SESSION_HANDLE_INVALID):
                self.assertEqual(hsm.random(4), b"\x00\x01\x02\x03")
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
            with pkcs11.simulate_failure(pkcs11.session_mock.encrypt, 6,
                                         error=PyKCS11.CKR_SESSION_HANDLE_INVALID):
                with self.assertRaises(HSMException):
                    hsm.encrypt_password(password)
                # the session has been opened initially, and six times after that
                self.assertEqual(pkcs11.mock.openSession.mock_calls, [call(slot=1)] * 7)

            with pkcs11.simulate_failure(pkcs11.session_mock.encrypt, 1,
                                         error=PyKCS11.CKR_ARGUMENTS_BAD):
                with self.assertRaises(HSMException):
                    hsm.encrypt_password(password)

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
            with pkcs11.simulate_failure(pkcs11.session_mock.generateRandom, 1,
                                         error=PyKCS11.CKR_SESSION_HANDLE_INVALID), \
                    pkcs11.simulate_failure(pkcs11.mock.openSession, 1):
                with self.assertRaises(PyKCS11Error):
                    hsm.encrypt_password(password)
                self.assertEqual(pkcs11.mock.openSession.mock_calls, [call(slot=1)] * 2)

            # the Security Module is in a defunct state now
            # but we can recover from it!
            # simulate one failure, because this will make the security module
            # acquire a new session
            with pkcs11.simulate_failure(pkcs11.session_mock.generateRandom, 1,
                                         error=PyKCS11.CKR_SESSION_HANDLE_INVALID):
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
            self.assertIsInstance(get_hsm(), AESHardwareSecurityModule)
            r = encryptPin("test")
            pin = decryptPin(r)
            self.assertEqual(pin, "test")

            self.assertTrue(get_hsm().is_ready)
            self.assertEqual(self.pkcs11.session_mock.encrypt.call_count, 1)

    def test_02_fault_recovery(self):
        with self.pkcs11:
            hsm = get_hsm()
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


class AESHardwareSecurityModuleLibLevelPasswordTestCase(MyTestCase):
    """ test case for HSM module where the password is provided later """
    pkcs11 = PKCS11Mock()

    def setUp(self):
        """ set up config to load the AES HSM module """
        current_app.config["PI_HSM_MODULE"] = "privacyidea.lib.security.aeshsm.AESHardwareSecurityModule"
        current_app.config["PI_HSM_MODULE_MODULE"] = "testmodule"
        # the config misses the password
        with self.pkcs11:
            MyTestCase.setUp(self)

    def test_01_set_password(self):
        with self.pkcs11:
            hsm = init_hsm()
            self.assertIsInstance(hsm, AESHardwareSecurityModule)
            with self.assertRaises(HSMException):
                get_hsm()
            self.assertIs(get_hsm(require_ready=False), hsm)
            ready = set_hsm_password("test123!")
            self.assertTrue(ready)
            self.assertIs(hsm, init_hsm())
            self.assertIs(get_hsm(), hsm)


class SignObjectTestCase(MyTestCase):
    """ tests for the SignObject which signs/verifies using RSA """

    def test_00_create_sign_object(self):
        # test with invalid key data
        with self.assertRaises(Exception):
            Sign(b'This is not a private key', b'This is not a public key')
        with self.assertRaises(Exception):
            priv_key = open(current_app.config.get("PI_AUDIT_KEY_PRIVATE"), 'rb').read()
            Sign(private_key=priv_key,
                 public_key=b'Still not a public key')
        # this should work
        priv_key = open(current_app.config.get("PI_AUDIT_KEY_PRIVATE"), 'rb').read()
        pub_key = open(current_app.config.get("PI_AUDIT_KEY_PUBLIC"), 'rb').read()
        so = Sign(priv_key, pub_key)
        self.assertEqual(so.sig_ver, 'rsa_sha256_pss')

        # test missing keys
        so = Sign(public_key=pub_key)
        res = so.sign('testdata')
        self.assertEqual(res, '')
        so = Sign(private_key=priv_key)
        res = so.verify('testdata', 'testsig')
        self.assertFalse(res)

    def test_01_sign_and_verify_data(self):
        priv_key = open(current_app.config.get("PI_AUDIT_KEY_PRIVATE"), 'rb').read()
        pub_key = open(current_app.config.get("PI_AUDIT_KEY_PUBLIC"), 'rb').read()
        so = Sign(priv_key, pub_key)
        data = 'short text'
        sig = so.sign(data)
        self.assertTrue(sig.startswith(so.sig_ver), sig)
        self.assertTrue(so.verify(data, sig))

        data = b'A slightly longer text, this time in binary format.'
        sig = so.sign(data)
        self.assertTrue(so.verify(data, sig))

        # test with text larger than RSA key size
        data = b'\x01\x02' * 5000
        sig = so.sign(data)
        self.assertTrue(so.verify(data, sig))

        # now test a broken signature
        data = 'short text'
        sig = so.sign(data)
        sig_broken = sig[:-1] + '{:x}'.format((int(sig[-1], 16) + 1) % 16)
        self.assertFalse(so.verify(data, sig_broken))

        # test with non hex string
        sig_broken = sig[:-1] + 'x'
        self.assertFalse(so.verify(data, sig_broken))

        # now try to verify old signatures
        # first without enabling old signatures in config
        short_text_sig = 15197717811878792093921885389298262311612396877333963031070812155820116863657342817645537537961773450510020137791036591085713379948816070430789598146539509027948592633362217308056639775153575635684961642110792013775709164803544619582232081442445758263838942315386909453927493644845757192298617925455779136340217255670113943560463286896994555184188496806420559078552626485909484729552861477888246423469461421103010299470836507229490718177625822972845024556897040292571751452383573549412451282884349017186147757238775308192484937929135306435242403555592741059466194258607967889051881221759976135386624406095324595765010
        data = 'short text'
        self.assertFalse(so.verify(data, short_text_sig))

        # now we enable the checking of old signatures
        short_text_sig = 15197717811878792093921885389298262311612396877333963031070812155820116863657342817645537537961773450510020137791036591085713379948816070430789598146539509027948592633362217308056639775153575635684961642110792013775709164803544619582232081442445758263838942315386909453927493644845757192298617925455779136340217255670113943560463286896994555184188496806420559078552626485909484729552861477888246423469461421103010299470836507229490718177625822972845024556897040292571751452383573549412451282884349017186147757238775308192484937929135306435242403555592741059466194258607967889051881221759976135386624406095324595765010
        data = 'short text'
        self.assertTrue(so.verify(data, short_text_sig, verify_old_sigs=True))

        # verify a broken old signature
        broken_short_text_sig = short_text_sig + 1
        self.assertFalse(so.verify(data, broken_short_text_sig, verify_old_sigs=True))

        long_data_sig = 991763198885165486007338893972384496025563436289154190056285376683148093829644985815692167116166669178171916463844829424162591848106824431299796818231239278958776853940831433819576852350691126984617641483209392489383319296267416823194661791079316704545017249491961092046751201670544843607206698682190381208022128216306635574292359600514603728560982584561531193227312370683851459162828981766836503134221347324867936277484738573153562229478151744446530191383660477390958159856842222437156763388859923477183453362567547792824054461704970820770533637185477922709297916275611571003099205429044820469679520819043851809079
        long_data = b'\x01\x02' * 5000
        self.assertTrue(so.verify(long_data, long_data_sig, verify_old_sigs=True))


class DefaultHashAlgoListTestCase(MyTestCase):
    """Check if the default hash algorithm list is used."""

    def test_01_default_hash_algorithm_list(self):
        password = "password"

        pbkdf2_sha512_hash = '$pbkdf2-sha512$25000$XEvJOcf437tXam1Nydm79w$6eDPlPjRgnJGGK0j8a3to' \
                             'SZoSUvwZzcvEj96t7Hg.X/SC822EFaO2iWoHFTUc1NMsX6sgQyQqbjWxGXgRWNzkw'

        argon2_fail_hash = '$argon2id$v=19$m=102400,t=9,p=8$vZeyFqI0xhiDEIKw1przfg$8FX07S7VpaYae51Oe9Cj7g'

        # Checks if the first entry is taken from "DEFAULT_HASH_ALGO_LIST"
        ph = pass_hash(password)
        self.assertTrue(ph.startswith('$argon2'), ph)
        self.assertIn('t=9', ph.split('$')[3], ph)
        self.assertTrue(verify_pass_hash(password, ph))
        # Checks if the password can also be verified with pbkdf2_sha512 from "DEFAULT_HASH_ALGO_LIST".
        self.assertTrue(verify_pass_hash(password, pbkdf2_sha512_hash))
        # Checks if an error message is issued if algorithm is not contain in "PI_HASH_ALGO_LIST".
        self.assertRaises(passlib.exc.UnknownHashError, verify_pass_hash, password, 'password')
        # Checks if a faulty hash is failing.
        self.assertFalse(verify_pass_hash(password, argon2_fail_hash))


class CustomParamsDefaultHashAlgoListTestCase(OverrideConfigTestCase):
    """Check if the default hash algorithm list is used with params from config."""

    class Config(TestingConfig):
        # Set custom parameter for hash algorithms in pi.cfg.
        PI_HASH_ALGO_PARAMS = {'argon2__rounds': 5, 'argon2__memory_cost': 768}

    def test_01_default_hash_algorithm_list_with_custom_params(self):
        password = "password"

        pbkdf2_sha512_hash = '$pbkdf2-sha512$25000$XEvJOcf437tXam1Nydm79w$6eDPlPjRgnJGGK0j8a3to' \
                             'SZoSUvwZzcvEj96t7Hg.X/SC822EFaO2iWoHFTUc1NMsX6sgQyQqbjWxGXgRWNzkw'

        # Checks if the first entry is taken from "DEFAULT_HASH_ALGO_LIST"
        ph = pass_hash(password)
        self.assertTrue(ph.startswith('$argon2'), ph)
        self.assertIn('t=5', ph.split('$')[3], ph)
        self.assertIn('m=768', ph.split('$')[3], ph)
        self.assertTrue(verify_pass_hash(password, ph))
        # Checks if the password can also be verified with pbkdf2_sha512 from "DEFAULT_HASH_ALGO_LIST".
        self.assertTrue(verify_pass_hash(password, pbkdf2_sha512_hash))


class CustomHashAlgoListTestCase(OverrideConfigTestCase):
    """Test for custom list of hash algorithms in pi.cfg"""

    class Config(TestingConfig):
        # Set custom list of algorithms in pi.cfg.
        PI_HASH_ALGO_LIST = ['pbkdf2_sha1', 'pbkdf2_sha512', 'argon2']
        PI_HASH_ALGO_PARAMS = {'pbkdf2_sha1__rounds': 50000}

    def test_01_custom_hash_algorithm_list(self):
        password = "password"

        pbkdf2_sha512_hash = '$pbkdf2-sha512$25000$XEvJOcf437tXam1Nydm79w$6eDPlPjRgnJGGK0j8a3to' \
                             'SZoSUvwZzcvEj96t7Hg.X/SC822EFaO2iWoHFTUc1NMsX6sgQyQqbjWxGXgRWNzkw'

        argon2_hash = '$argon2id$v=19$m=102400,t=9,p=8$vZeyFqI0xhiDEIKw1przfg$8FX07S7VpaYae51Oe9Cj8g'

        argon2_fail_hash = '$argon2id$v=19$m=102400,t=9,p=8$vZeyFqI0xhiDEIKw1przfg$8FX07S7VpaYae51Oe9Cj7g'

        # Check if the first entry is taken from "PI_HASH_ALGO_LIST" .
        self.assertTrue(pass_hash(password).startswith('$pbkdf2$50000$'))
        # Checks if the password can also be verified with pbkdf2_sha512".
        self.assertTrue(verify_pass_hash(password, pbkdf2_sha512_hash))
        # Checks if the password can also be verified with argon2".
        self.assertTrue(verify_pass_hash(password, argon2_hash))
        # Checks if an error message is issued if algorithm is not contain in "PI_HASH_ALGO_LIST".
        self.assertRaises(passlib.exc.UnknownHashError, verify_pass_hash, password, 'password')
        # Checks if a faulty hash is failing.
        self.assertFalse(verify_pass_hash(password, argon2_fail_hash))
