"""
This test file tests the lib.tokens.yubicotoken
This depends on lib.tokenclass
"""

from .base import MyTestCase
from privacyidea.lib.tokens.yubicotoken import (YubicoTokenClass, YUBICO_URL)
from privacyidea.models import Token
import responses
import json
from privacyidea.lib.config import set_privacyidea_config


class YubicoTokenTestCase(MyTestCase):

    otppin = "topsecret"
    serial1 = "ser1"
    params1 = {"yubico.tokenid": "vvbgidlghkhgfbvetefnbrfibfctu"}

    success_body = """h=Ndk+Lx678Tb4nZjPCi1+geki9vU=
t=2015-01-28T15:22:57Z0508
otp=vvbgidlghkhgndujklhhudbcuttkcklhvjktrjbfukrt
nonce=5e1cdbcbb798af7445b60376aaf2c17b2f064f41
sl=25
status=OK"""

    fail_body = """h=3+BO86TdIuhg1gFpLj+PDyyxxu4=
t=2015-01-28T15:27:01Z0978
otp=vvbgidlghkhgndujklhhudbcuttkcklhvjktrjbfukrt
nonce=fbbfd6fead1f16372b493e7515396363cec90c00
status=REPLAYED_OTP"""

    def test_01_create_token(self):

        db_token = Token(self.serial1, tokentype="remote")
        db_token.save()
        token = YubicoTokenClass(db_token)
        token.update(self.params1)
        token.set_pin(self.otppin)

        self.assertTrue(token.token.serial == self.serial1, token)
        self.assertTrue(token.token.tokentype == "yubico",
                        token.token.tokentype)
        self.assertTrue(token.type == "yubico", token)
        class_prefix = token.get_class_prefix()
        self.assertTrue(class_prefix == "UBCM", class_prefix)
        self.assertTrue(token.get_class_type() == "yubico", token)

    def test_02_class_methods(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = YubicoTokenClass(db_token)

        info = token.get_class_info()
        self.assertTrue(info.get("title") == "Yubico Token",
                        "{0!s}".format(info.get("title")))

        info = token.get_class_info("title")
        self.assertTrue(info == "Yubico Token", info)

    @responses.activate
    def test_04_check_otp_success(self):
        responses.add(responses.GET, YUBICO_URL,
                      body=self.success_body)

        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = YubicoTokenClass(db_token)
        otpcount = token.check_otp("vvbgidlghkhgndujklhhudbcuttkcklhvjktrjrt")
        # Nonce and hash do not match
        self.assertTrue(otpcount == -2, otpcount)

    @responses.activate
    def test_04_check_otp_success_with_post_request(self):
        set_privacyidea_config("yubico.do_post", True)
        responses.add(responses.POST, YUBICO_URL,
                      body=self.success_body)

        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = YubicoTokenClass(db_token)
        otpcount = token.check_otp("vvbgidlghkhgndujklhhudbcuttkcklhvjktrjrt")
        # Nonce and hash do not match
        self.assertTrue(otpcount == -2, otpcount)
        set_privacyidea_config("yubico.do_post", False)


    @responses.activate
    def test_05_check_otp_fail(self):
        responses.add(responses.POST, YUBICO_URL,
                      body=self.fail_body)

        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = YubicoTokenClass(db_token)

        otpcount = token.check_otp("vvbgidlghkhgndujklhhudbcuttkcklhvjktrjrt")
        # Status != "OK".
        self.assertTrue(otpcount == -1, otpcount)

    def test_06_check_otp_ID_too_short(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = YubicoTokenClass(db_token)
        otpcount = token.check_otp("vvbgidlg")
        self.assertTrue(otpcount == -1, otpcount)

    def test_07_check_otp_ID_wrong(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = YubicoTokenClass(db_token)
        otpcount = token.check_otp("Xvbgidlghkhgndujklhhudbcuttkcklhvjktrjrt")
        self.assertTrue(otpcount == -1, otpcount)

    def test_08_init_ID_too_short(self):
        db_token = Token("neuYT", tokentype="remote")
        db_token.save()
        token = YubicoTokenClass(db_token)
        self.assertRaises(Exception, token.update,
                          {"yubico.tokenid": "vvbgidlg"})
