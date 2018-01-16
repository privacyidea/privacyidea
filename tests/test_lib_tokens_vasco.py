"""
This test file tests the lib.tokens.vascotoken
This depends on lib.tokenclass
"""
import functools
from binascii import hexlify

import mock

from privacyidea.lib.error import ParameterError
from privacyidea.lib.tokens.vascotoken import VascoTokenClass
from privacyidea.models import Token
from tests.base import MyTestCase

def mock_verification(replacement):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            with mock.patch('privacyidea.lib.tokens.vasco.vasco_dll') as mock_dll:
                mock_dll.AAL2VerifyPassword.side_effect = replacement
                return f(*args, **kwargs)
        return wrapper
    return decorator

def mock_success(data, params, password, challenge):
    # fake a new blob
    data._obj.Blob = "Y" * 224
    return 0

def mock_failure(data, params, password, challenge):
    # fake a new blob
    data._obj.Blob = "Y"*224
    return 42

def mock_missing_dll(replacement):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            with mock.patch('privacyidea.lib.tokens.vasco.vasco_dll') as mock_dll:
                mock_dll.return_value = None
                return f(*args, **kwargs)
        return wrapper
    return decorator


class VascoTokenTest(MyTestCase):
    otppin = "topsecret"
    serial1 = "ser1"
    serial2 = "ser2"
    resolvername1 = "resolver1"
    resolvername2 = "Resolver2"
    resolvername3 = "reso3"
    realm1 = "realm1"
    realm2 = "realm2"

    def test_01_create_token(self):
        db_token = Token(self.serial1, tokentype="vasco")
        db_token.save()
        token = VascoTokenClass(db_token)
        token.update({"otpkey": hexlify("X" * 248),
                      "pin": self.otppin})
        self.assertTrue(token.token.serial == self.serial1, token)
        self.assertTrue(token.token.tokentype == "vasco", token.token.tokentype)
        self.assertTrue(token.type == "vasco", token)
        class_prefix = token.get_class_prefix()
        self.assertTrue(class_prefix == "VASC", class_prefix)
        self.assertTrue(token.get_class_type() == "vasco", token)

    def test_02_genkey_fails(self):
        db_token = Token(self.serial2, tokentype="vasco")
        db_token.save()
        token = VascoTokenClass(db_token)
        self.assertRaises(ParameterError, token.update, {"genkey": "1"})
        token.delete_token()

    @mock_missing_dll
    def test_03_no_vasco_library(self):
        db_token = Token(self.serial2, tokentype="vasco")
        db_token.save()
        token = VascoTokenClass(db_token)
        token.update({"otpkey": hexlify("X"*248),
                      "pin": self.otppin})
        self.assertRaises(RuntimeError, token.authenticate, "{}123456".format(self.otppin))
        token.delete_token()

    @mock_verification(mock_failure)
    def test_04_failure(self):
        db_token = Token(self.serial2, tokentype="vasco")
        db_token.save()
        token = VascoTokenClass(db_token)
        token.update({"otpkey": hexlify("X"*248),
                      "pin": self.otppin})
        r = token.authenticate("{}123456".format(self.otppin))
        self.assertEqual(r[0], True)
        self.assertEqual(r[1], -1)
        # failure, but the token secret has been updated nonetheless
        key = token.token.get_otpkey().getKey()
        self.assertEqual(key, "X"*24 + "Y"*224)
        token.delete_token()

    @mock_verification(mock_success)
    def test_05_success(self):
        db_token = Token(self.serial2, tokentype="vasco")
        db_token.save()
        token = VascoTokenClass(db_token)
        token.update({"otpkey": hexlify("X"*248),
                      "pin": self.otppin})
        r = token.authenticate("{}123456".format(self.otppin))
        self.assertEqual(r[0], True)
        self.assertEqual(r[1], 0) # TODO: that is success?
        # failure, but the token secret has been updated nonetheless
        key = token.token.get_otpkey().getKey()
        self.assertEqual(key, "X"*24 + "Y"*224)
        token.delete_token()