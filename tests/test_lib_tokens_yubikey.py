"""
This test file tests the lib.tokens.yubikeytoken

"""
PWFILE = "tests/testdata/passwords"

from .base import MyTestCase
from privacyidea.lib.tokens.yubikeytoken import (YubikeyTokenClass,
                                                 yubico_api_signature,
                                                 yubico_check_api_signature)
from privacyidea.lib.token import init_token
from privacyidea.models import (Token)
from flask import Request, g
from werkzeug.test import EnvironBuilder
from privacyidea.lib.config import set_privacyidea_config


class YubikeyTokenTestCase(MyTestCase):
    """
    Test the Yubikey in Yubico AES mode.
    """
    resolvername1 = "resolver1"
    resolvername2 = "Resolver2"
    resolvername3 = "reso3"
    realm1 = "realm1"
    realm2 = "realm2"
    serial1 = "UBAM01382015_1"
    otpkey = "9163508031b20d2fbb1868954e041729"
    pin = "yubikeypin"

    public_uid = "ecebeeejedecebeg"
    valid_otps = [
        public_uid + "fcniufvgvjturjgvinhebbbertjnihit",
        public_uid + "tbkfkdhnfjbjnkcbtbcckklhvgkljifu",
        public_uid + "ktvkekfgufndgbfvctgfrrkinergbtdj",
        public_uid + "jbefledlhkvjjcibvrdfcfetnjdjitrn",
        public_uid + "druecevifbfufgdegglttghghhvhjcbh",
        public_uid + "nvfnejvhkcililuvhntcrrulrfcrukll",
        public_uid + "kttkktdergcenthdredlvbkiulrkftuk",
        public_uid + "hutbgchjucnjnhlcnfijckbniegbglrt",
        public_uid + "vneienejjnedbfnjnnrfhhjudjgghckl",
    ]

    further_otps = [
        public_uid + "krgevltjnujcnuhtngjndbhbiiufbnki",
        public_uid + "kehbefcrnlfejedfdulubuldfbhdlicc",
        public_uid + "ljlhjbkejkctubnejrhuvljkvglvvlbk",
        public_uid + "eihtnehtetluntirtirrvblfkttbjuih",

    ]

    def test_01_enroll_yubikey_and_auth(self):
        db_token = Token(self.serial1, tokentype="yubikey")
        db_token.save()
        token = YubikeyTokenClass(db_token)
        token.set_otpkey(self.otpkey)
        token.set_otplen(48)
        token.set_pin(self.pin)
        token.save()
        self.assertTrue(token.token.serial == self.serial1, token)
        self.assertTrue(token.token.tokentype == "yubikey", token.token)
        self.assertTrue(token.type == "yubikey", token)
        class_prefix = token.get_class_prefix()
        self.assertTrue(class_prefix == "UBAM", class_prefix)
        self.assertTrue(token.get_class_type() == "yubikey", token)

        # Test a bunch of otp values
        old_r = 0
        for otp in self.valid_otps:
            r = token.check_otp(otp)
            # check if the newly returned counter is bigger than the old one
            self.assertTrue(r > old_r, (r, old_r))
            old_r = r

        # test otp_exist
        r = token.check_otp_exist(self.further_otps[0])
        self.assertTrue(r > old_r, (r, old_r))

    def test_02_get_class_info(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = YubikeyTokenClass(db_token)
        ttype = token.get_class_info("type")
        self.assertTrue(ttype == "yubikey", ttype)
        ci = token.get_class_info()
        self.assertTrue(ci.get("title") == "Yubikey in AES mode", ci)

    def test_03_is_challenge_request(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = YubikeyTokenClass(db_token)

        r = token.is_challenge_request(self.pin)
        self.assertTrue(r)

    def test_04_check_yubikey_pass(self):
        # Check_yubikey_pass only works without pin!
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = YubikeyTokenClass(db_token)
        token.set_pin("")
        token.save()
        r, opt = YubikeyTokenClass.check_yubikey_pass(self.further_otps[1])
        self.assertTrue(r)
        self.assertTrue(opt.get("message") == "matching 1 tokens", opt)

        # check failcounter
        self.assertEqual(db_token.failcount, 0)

        # the same otp value must not be usable again
        r, opt = YubikeyTokenClass.check_yubikey_pass(self.further_otps[1])
        self.assertFalse(r)
        self.assertTrue(opt.get("message") == "wrong otp value", opt)

        # check failcounter
        self.assertEqual(db_token.failcount, 1)

        # check an otp value, that does not match a token
        r, opt = YubikeyTokenClass.check_yubikey_pass(
            "fcebeeejedecebegfcniufvgvjturjgvinhebbbertjnihit")
        self.assertFalse(r)
        #self.assertTrue(opt.get("action_detail") ==
        #                "The serial UBAM@1382015 could not be found!", opt)
        self.assertTrue(opt.get("action_detail") ==
                        "The prefix fcebeeejedecebeg could not be found!", opt)


        # check for an invalid OTP
        r, opt = YubikeyTokenClass.check_yubikey_pass(self.further_otps[0])
        self.assertFalse(r)
        self.assertTrue(opt.get("message") == "wrong otp value", opt)

        # check failcounter
        self.assertEqual(db_token.failcount, 2)

    def test_05_check_maxfail(self):
        # Check_yubikey_pass only works without pin!
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = YubikeyTokenClass(db_token)
        token.set_pin("")
        token.save()
        token.set_maxfail(5)
        old_failcounter = token.get_failcount()
        token.set_failcount(5)
        # Failcount equals maxfail, so an authentication with a valid OTP
        # will fail
        r, opt = YubikeyTokenClass.check_yubikey_pass(self.further_otps[2])
        self.assertFalse(r)
        self.assertTrue(opt.get("message") == "matching 1 tokens, "
                                              "Failcounter exceeded", opt)
        # check failcounter
        self.assertEqual(db_token.failcount, 5)
        token.set_failcount(old_failcounter)

    def test_09_api_signature(self):
        api_key = "LqeG/IZscF1f7/oGQBqNnGY7MLk="
        signature = "0KRJecfPNSrpZ79+xODbJl0HM8I="
        data = {"otp": "ececegecejeeedehfftnecrrfcfibfbklhvetghgrvtjdtvv",
                "nonce": "blablafoo",
                "h": signature,
                "timestamp": "time"}

        h = yubico_api_signature(data, api_key)
        self.assertEqual(h, signature)
        self.assertEqual(yubico_check_api_signature(data, api_key,
                                                    signature), True)
        self.assertEqual(yubico_check_api_signature(data, api_key), True)

    def test_10_api_endpoint(self):
        fixed = "ebedeeefegeheiej"
        otpkey = "cc17a4d77eaed96e9d14b5c87a02e718"
        uid = "000000000000"
        otps = ["ebedeeefegeheiejtjtrutblehenfjljrirgdihrfuetljtt",
                "ebedeeefegeheiejlekvlrlkrcluvctenlnnjfknrhgtjned",
                "ebedeeefegeheiejktudedbktcnbuntrhdueikggtrugckij",
                "ebedeeefegeheiejjvjncbnffdrvjcvrbgdfufjgndfetieu",
                "ebedeeefegeheiejdruibhvlvktcgfjiruhltketifnitbuk"
        ]

        token = init_token({"type": "yubikey",
                            "otpkey": otpkey,
                            "otplen": len(otps[0]),
                            "yubikey.prefix": fixed,
                            "serial": "UBAM12345678_1"})

        builder = EnvironBuilder(method='GET',
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        nonce = "random nonce"
        apiid = "hallo"
        apikey = "1YMEbMZijD3DzL21UfKGnOOI13c="
        set_privacyidea_config("yubikey.apiid.{0!s}".format(apiid), apikey)
        req.all_data = {'id': apiid,
                        "otp": otps[0],
                        "nonce": nonce}
        text_type, result = YubikeyTokenClass.api_endpoint(req, g)
        self.assertEqual(text_type, "plain")
        self.assertTrue("status=OK" in result, result)
        self.assertTrue("nonce={0!s}".format(nonce) in result, result)

    def test_11_strip_whitespace(self):
        fixed = "ebedeeefegeheiej"
        # The backend automatically strips whitespace from the OTP key
        otpkey = "cc 17 a4 d7 7e ae d9 6e 9d 14 b5 c8 7a 02 e7 18"
        uid = "000000000000"
        otps = ["ebedeeefegeheiejtjtrutblehenfjljrirgdihrfuetljtt",
                "ebedeeefegeheiejlekvlrlkrcluvctenlnnjfknrhgtjned",
                "ebedeeefegeheiejktudedbktcnbuntrhdueikggtrugckij",
                "ebedeeefegeheiejjvjncbnffdrvjcvrbgdfufjgndfetieu",
                "ebedeeefegeheiejdruibhvlvktcgfjiruhltketifnitbuk"
        ]

        token = init_token({"type": "yubikey",
                            "otpkey": otpkey,
                            "otplen": len(otps[0]),
                            "yubikey.prefix": fixed,
                            "serial": "UBAM12345678_1"})

        builder = EnvironBuilder(method='GET',
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        nonce = "random nonce"
        apiid = "hallo"
        apikey = "1YMEbMZijD3DzL21UfKGnOOI13c="
        set_privacyidea_config("yubikey.apiid.{0!s}".format(apiid), apikey)
        req.all_data = {'id': apiid,
                        "otp": otps[0],
                        "nonce": nonce}
        text_type, result = YubikeyTokenClass.api_endpoint(req, g)
        self.assertEqual(text_type, "plain")
        self.assertTrue("status=OK" in result, result)
        self.assertTrue("nonce={0!s}".format(nonce) in result, result)

    def test_98_wrong_tokenid(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = YubikeyTokenClass(db_token)
        token.add_tokeninfo("yubikey.tokenid", "wrongid!")
        token.save()

        # check an OTP value
        r = token.check_otp(self.further_otps[2])
        self.assertTrue(r == -2, r)

    def test_99_delete_token(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = YubikeyTokenClass(db_token)
        # delete the token
        token.delete_token()
