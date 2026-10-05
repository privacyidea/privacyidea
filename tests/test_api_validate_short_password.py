# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later


from privacyidea.lib.tokens.totptoken import HotpTokenClass
from privacyidea.lib.tokens.yubikeytoken import YubikeyTokenClass
from privacyidea.lib.user import (User)
from privacyidea.models import (Token)
from .base import MyApiTestCase



class ValidateShortPasswordTestCase(MyApiTestCase):
    yubi_otpkey = "9163508031b20d2fbb1868954e041729"

    public_uid = "ecebeeejedecebeg"
    valid_yubi_otps = [
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

    def test_00_setup_tokens(self):
        self.setUp_user_realms()

        pin = ""
        # create a token and assign it to the user
        db_token = Token(self.serials[0], tokentype="hotp")
        db_token.update_otpkey(self.otpkey)
        db_token.save()
        token = HotpTokenClass(db_token)
        self.assertEqual(self.serials[0], token.token.serial)
        self.assertEqual(6, token.token.otplen)
        token.add_user(User("cornelius", self.realm1))
        token.set_pin(pin)

        # create a yubikey and assign it to the user
        db_token = Token(self.serials[1], tokentype="yubikey")
        db_token.update_otpkey(self.yubi_otpkey)
        db_token.otplen = 48
        db_token.save()
        token = YubikeyTokenClass(db_token)
        self.assertEqual(self.serials[1], token.token.serial)
        self.assertEqual(len(self.valid_yubi_otps[0]), token.token.otplen)
        token.add_user(User("cornelius", self.realm1))
        token.set_pin(pin)

        # Successful authentication with HOTP
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "{0!s}{1!s}".format(pin, self.valid_otp_values[0])}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))

        # verify the Yubikey AES mode
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "{0!s}{1!s}".format(pin, self.valid_yubi_otps[0])}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))


class Initialize(MyApiTestCase):

    def test01_no_type(self):
        with self.app.test_request_context('/validate/initialize',
                                           method='POST',
                                           data={"type": ""}):
            res = self.app.full_dispatch_request()
            self.assertEqual(400, res.status_code, res)
            self.assertIn("result", res.json)
            self.assertIn("error", res.json["result"])
            error = res.json["result"]["error"]
            self.assertIn("code", error)
            self.assertIn("message", error)
            self.assertEqual(905, error["code"], error)
            self.assertEqual("ERR905: Missing parameter: type", error["message"], error)
