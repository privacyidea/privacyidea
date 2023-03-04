"""
This test file tests the lib.tokens.vascotoken
This depends on lib.tokenclass
"""
import functools
from binascii import hexlify

import mock

from privacyidea.lib.error import ParameterError
from privacyidea.lib.token import check_serial_pass
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

def _set_next_blob(data):
    """
    update ``data._obj.Blob``: Increment the contents by 1.
    i.e. "XXX...X" is replaced with "YYY...Y".
    """
    data._obj.Blob = b"".join(bytes((x + 1,)) for x in data._obj.Blob)

def mock_success(data, params, password, challenge):
    # fake a new blob
    _set_next_blob(data)
    return 0

def create_mock_failure(return_value):
    def mock_failure(data, params, password, challenge):
        # fake a new blob
        _set_next_blob(data)
        return return_value
    return mock_failure

def mock_missing_dll(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        with mock.patch('privacyidea.lib.tokens.vasco.vasco_dll', None):
            return f(*args, **kwargs)
    return wrapper

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
        token.update({"otpkey": hexlify(b"X" * 248).decode("utf-8"),
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
        token.update({"otpkey": hexlify(b"X"*248).decode("utf-8"),
                      "pin": self.otppin})
        self.assertRaises(RuntimeError, token.authenticate, "{}123456".format(self.otppin))
        token.delete_token()

    @mock_verification(create_mock_failure(1))
    def test_04_failure(self):
        db_token = Token(self.serial2, tokentype="vasco")
        db_token.save()
        token = VascoTokenClass(db_token)
        token.update({"otpkey": hexlify(b"X"*248).decode("utf-8"),
                      "pin": self.otppin})
        r = token.authenticate("{}123456".format(self.otppin))
        self.assertEqual(r[0], True)
        self.assertEqual(r[1], -1)
        # failure, but the token secret has been updated nonetheless
        key = token.token.get_otpkey().getKey()
        self.assertEqual(key, b"X"*24 + b"Y"*224)
        # wrong PIN, the token secret has not been updated
        r = token.authenticate("WRONG123456".format(self.otppin))
        self.assertEqual(r[0], False)
        self.assertEqual(r[1], -1)
        key = token.token.get_otpkey().getKey()
        self.assertEqual(key, b"X"*24 + b"Y"*224)
        # another failure, but the token secret has been updated again!
        r = token.authenticate("{}234567".format(self.otppin))
        self.assertEqual(r[0], True)
        self.assertEqual(r[1], -1)
        key = token.token.get_otpkey().getKey()
        self.assertEqual(key, b"X"*24 + b"Z"*224)
        token.delete_token()

    @mock_verification(mock_success)
    def test_05_success(self):
        db_token = Token(self.serial2, tokentype="vasco")
        db_token.save()
        token = VascoTokenClass(db_token)
        token.update({"otpkey": hexlify(b"X"*248).decode("utf-8"),
                      "pin": self.otppin})
        # wrong PIN, the token secret has not been updated
        r = token.authenticate("WRONG123456".format(self.otppin))
        self.assertEqual(r[0], False)
        self.assertEqual(r[1], -1)
        key = token.token.get_otpkey().getKey()
        self.assertEqual(key, b"X"*24 + b"X"*224)
        # correct PIN + OTP
        r = token.authenticate("{}123456".format(self.otppin))
        self.assertEqual(r[0], True)
        self.assertEqual(r[1], 0) # TODO: that is success?
        key = token.token.get_otpkey().getKey()
        self.assertEqual(key, b"X"*24 + b"Y"*224)
        # another success
        r = token.authenticate("{}234567".format(self.otppin))
        self.assertEqual(r[0], True)
        self.assertEqual(r[1], 0)  # TODO: that is success?
        key = token.token.get_otpkey().getKey()
        self.assertEqual(key, b"X"*24 + b"Z"*224)
        token.delete_token()

    def test_06_reuse(self):
        db_token = Token(self.serial2, tokentype="vasco")
        db_token.save()
        token = VascoTokenClass(db_token)
        token.update({"otpkey": hexlify(b"X" * 248).decode("utf-8"),
                      "pin": self.otppin})

        @mock_verification(mock_success)
        def _step1():
            # correct PIN + OTP
            return token.authenticate("{}123456".format(self.otppin))

        r = _step1()
        self.assertEqual(r[0], True)
        self.assertEqual(r[1], 0)  # TODO: that is success?
        key = token.token.get_otpkey().getKey()
        self.assertEqual(key, b"X" * 24 + b"Y" * 224)

        # set another pin
        token.set_pin("anotherpin")

        @mock_verification(create_mock_failure(201))
        def _step2():
            # correct PIN, wrong OTP
            return token.authenticate("anotherpin123456")

        # reuse
        r = _step2()
        self.assertEqual(r[0], True)
        self.assertEqual(r[1], -1)
        key = token.token.get_otpkey().getKey()
        self.assertEqual(key, b"X" * 24 + b"Z" * 224)

        # correct PIN + OTP
        @mock_verification(mock_success)
        def _step3():
            # correct PIN + OTP
            return token.authenticate("anotherpin234567")

        r = _step3()
        self.assertEqual(r[0], True)
        self.assertEqual(r[1], 0)
        key = token.token.get_otpkey().getKey()
        self.assertEqual(key, b"X" * 24 + b"[" * 224)

        token.delete_token()

    def test_07_failures(self):
        db_token = Token(self.serial2, tokentype="vasco")
        db_token.save()
        token = VascoTokenClass(db_token)
        token.update({"otpkey": hexlify(b"X"*248).decode('utf-8'),
                      "pin": self.otppin})

        @mock_verification(create_mock_failure(123))
        def _step1():
            return token.authenticate("{}123456".format(self.otppin))

        r = _step1()
        self.assertEqual(r[0], True)
        self.assertEqual(r[1], -1)
        # failure, but the token secret has been updated nonetheless
        key = token.token.get_otpkey().getKey()
        self.assertEqual(key, b"X"*24 + b"Y"*224)

        @mock_verification(create_mock_failure(202))
        def _step2():
            return token.authenticate("{}123456".format(self.otppin))
        r = _step2()
        self.assertEqual(r[0], True)
        self.assertEqual(r[1], -1)
        # failure, but the token secret has been updated nonetheless
        key = token.token.get_otpkey().getKey()
        self.assertEqual(key, b"X"*24 + b"Z"*224)

        token.delete_token()

    def test_08_invalid_otpkey(self):
        db_token = Token(self.serial2, tokentype="vasco")
        db_token.save()
        token = VascoTokenClass(db_token)
        self.assertRaises(ParameterError,
                          token.update,
                          {"otpkey": hexlify(b"X"*250).decode("utf-8")}) # wrong length
        self.assertRaises(ParameterError,
                          token.update,
                          {"otpkey": "X"*496}) # not a hex-string
        token.delete_token()

    def test_09_failcount(self):
        db_token = Token(self.serial2, tokentype="vasco")
        db_token.save()
        token = VascoTokenClass(db_token)
        token.update({"otpkey": hexlify(b"A" * 248).decode("utf-8"),
                      "pin": self.otppin})

        @mock_verification(create_mock_failure(1))
        def _step1():
            # correct PIN, wrong OTP
            return check_serial_pass(self.serial2, "{}123456".format(self.otppin))

        self.assertTrue(token.check_failcount())
        # fail 10 times
        for _ in range(10 + 1):
            r = _step1()
            self.assertEqual(r[0], False)
            self.assertEqual(r[1].get('message'), 'wrong otp value')

        key = token.token.get_otpkey().getKey()
        self.assertEqual(key, b"A" * 24 + b"L" * 224)
        # fail counter has been exceeded
        self.assertFalse(token.check_failcount())

        @mock_verification(mock_success)
        def _step2():
            # correct PIN, wrong OTP
            return check_serial_pass(self.serial2, "{}123456".format(self.otppin))

        # subsequent authentication attempt fails due to fail counter
        r = _step2()
        self.assertEqual(r[0], False)
        self.assertEqual(r[1].get('message'), 'matching 1 tokens, Failcounter exceeded')
        # this actually does update the OTP key
        key = token.token.get_otpkey().getKey()
        self.assertEqual(key, b"A" * 24 + b"M" * 224)

        # reset the failcounter
        token.reset()

        # now, authentication works again
        r = _step2()
        self.assertEqual(r[0], True)
        self.assertEqual(r[1].get('message'), 'matching 1 tokens')
        key = token.token.get_otpkey().getKey()
        self.assertEqual(key, b"A" * 24 + b"N" * 224)

        token.delete_token()