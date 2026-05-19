"""
This test file tests the lib.tokens.yubicotoken
This depends on lib.tokenclass
"""
from unittest.mock import patch

from privacyidea.lib.token import init_token, remove_token, get_tokens, import_tokens
from .base import MyTestCase
from privacyidea.lib.tokens.yubicotoken import (YubicoTokenClass, YUBICO_URL)
from privacyidea.models import Token
import responses
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

    # The two fixtures below are verbatim request/response pairs captured
    # from https://api.yubico.com/wsapi/2.0/verify
    # The ``h=`` values were computed by YubiCloud itself, so verifying them
    # locally is a non-circular regression test for the HMAC whitelist in
    # privacyidea.lib.tokens.yubikeytoken.
    # NOTE: The API ID/key below were registered solely for these fixtures
    # and are considered public. Do not use them for anything else.
    YUBICLOUD_API_ID = "119564"
    YUBICLOUD_API_KEY = "W4xuhNuYDdysTrZzceKXm4kw4dI="
    YUBICLOUD_OTP = "vvccccccccvvjnkckcilhkfkvelejbnucncttbjnflte"
    YUBICLOUD_TOKENID = "vvccccccccvv"

    # status=OK capture (full field set incl. sl).
    YUBICLOUD_OK_NONCE = "5859842555790891ee43f3bdb4e103fa4673186b"
    YUBICLOUD_OK_BODY = (
        "h=LwE1Ojk1kWNUN2YntJNKQuhWQJY=\r\n"
        "t=2026-04-20T14:05:53Z0704\r\n"
        "otp=vvccccccccvvjnkckcilhkfkvelejbnucncttbjnflte\r\n"
        "nonce=5859842555790891ee43f3bdb4e103fa4673186b\r\n"
        "sl=100\r\n"
        "status=OK\r\n"
    )

    # status=REPLAYED_OTP capture (no sl field — exercises the case where a
    # legitimate response omits optional fields).
    YUBICLOUD_REPLAY_NONCE = "87e40880272bac0b94bb18f6342ce76d528ddc28"
    YUBICLOUD_REPLAY_BODY = (
        "h=S4Vp52zdQinaj2x3fvch7o61QIY=\r\n"
        "t=2026-04-20T14:06:00Z0720\r\n"
        "otp=vvccccccccvvjnkckcilhkfkvelejbnucncttbjnflte\r\n"
        "nonce=87e40880272bac0b94bb18f6342ce76d528ddc28\r\n"
        "status=REPLAYED_OTP\r\n"
    )

    def _enroll_yubicloud_token(self, serial):
        db_token = Token(serial, tokentype="yubico")
        db_token.save()
        token = YubicoTokenClass(db_token)
        # update() validates and truncates yubico.tokenid to 12 chars.
        token.update({"yubico.tokenid": self.YUBICLOUD_TOKENID})
        return token

    @responses.activate
    def test_05b_check_otp_yubicloud_real_ok(self):
        """Verified against a real YubiCloud ``status=OK`` response."""
        set_privacyidea_config("yubico.id", self.YUBICLOUD_API_ID)
        set_privacyidea_config("yubico.secret", self.YUBICLOUD_API_KEY)
        set_privacyidea_config("yubico.do_post", False)

        responses.add(responses.GET, YUBICO_URL, body=self.YUBICLOUD_OK_BODY)
        responses.add(responses.POST, YUBICO_URL, body=self.YUBICLOUD_OK_BODY)

        token = self._enroll_yubicloud_token("UBCMREAL_OK")
        try:
            # Pin the nonce to the captured one so YubiCloud's real h= stays
            # valid — our code never re-signs anything in this path.
            with patch("privacyidea.lib.tokens.yubicotoken.geturandom",
                       return_value=self.YUBICLOUD_OK_NONCE):
                self.assertEqual(1, token.check_otp(self.YUBICLOUD_OTP))
        finally:
            remove_token("UBCMREAL_OK")
            set_privacyidea_config("yubico.id", "")
            set_privacyidea_config("yubico.secret", "")

    @responses.activate
    def test_05c_check_otp_yubicloud_real_replayed(self):
        """Real YubiCloud ``status=REPLAYED_OTP`` — signature still must verify."""
        set_privacyidea_config("yubico.id", self.YUBICLOUD_API_ID)
        set_privacyidea_config("yubico.secret", self.YUBICLOUD_API_KEY)
        set_privacyidea_config("yubico.do_post", False)

        responses.add(responses.GET, YUBICO_URL,
                      body=self.YUBICLOUD_REPLAY_BODY)
        responses.add(responses.POST, YUBICO_URL,
                      body=self.YUBICLOUD_REPLAY_BODY)

        token = self._enroll_yubicloud_token("UBCMREAL_REPLAY")
        try:
            with (patch("privacyidea.lib.tokens.yubicotoken.geturandom",
                        return_value=self.YUBICLOUD_REPLAY_NONCE),
                  self.assertLogs("privacyidea.lib.tokens.yubicotoken",
                                  level="WARNING") as lc):
                # Non-OK status returns the default -1, but only after the
                # signature check has passed; if the whitelist were wrong
                # we'd see an ERROR-level "hash ... does not match" entry.
                self.assertEqual(-1, token.check_otp(self.YUBICLOUD_OTP))
            self.assertFalse(
                any("does not match the data" in m for m in lc.output),
                f"response signature verification failed: {lc.output}",
            )
            self.assertTrue(
                any("REPLAYED_OTP" in m for m in lc.output),
                f"expected REPLAYED_OTP warning, got: {lc.output}",
            )
        finally:
            remove_token("UBCMREAL_REPLAY")
            set_privacyidea_config("yubico.id", "")
            set_privacyidea_config("yubico.secret", "")

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

    def test_09_yubico_token_export(self):
        token = init_token(param={'serial': "OATH12345678",
                                  'type': 'yubico',
                                  'otpkey': self.otpkey,
                                  'yubico.tokenid': 'vvbgidlghkhgfbvetefnbrfibfctu'})
        self.assertRaises(NotImplementedError, token.export_token)

        # Clean up
        token.delete_token()

    def test_10_yubico_token_import(self):
        token_data = [{
            "serial": "123456",
            "type": "yubico",
            "description": "this token can't be imported",
            "otpkey": self.otpkey,
            "issuer": "privacyIDEA",
        }]
        before_import = get_tokens()
        import_tokens(token_data)
        after_import = get_tokens()
        self.assertEqual(len(before_import), len(after_import))
