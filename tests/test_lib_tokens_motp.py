"""
This test file tests the lib.tokens.spasstoken
This depends on lib.tokenclass
"""

from .base import MyTestCase
from privacyidea.lib.tokens.motptoken import MotpTokenClass
from privacyidea.lib.tokens.mOTP import mTimeOtp
from privacyidea.models import Token
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.realm import set_realm
from privacyidea.lib.user import User
PWFILE = "tests/testdata/passwords"

class MotpTokenTestCase(MyTestCase):

    otppin = "topsecret"
    motppin = "1234"
    serial1 = "ser1"
    serial2 = "ser2"
    resolvername1 = "resolver1"
    resolvername2 = "Resolver2"
    resolvername3 = "reso3"
    realm1 = "realm1"
    realm2 = "realm2"

    def test_00_create_user_realm(self):
        rid = save_resolver({"resolver": self.resolvername1,
                             "type": "passwdresolver",
                             "fileName": PWFILE})
        self.assertTrue(rid > 0, rid)

        (added, failed) = set_realm(self.realm1,
                                    [self.resolvername1])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 1)

        user = User(login="root",
                    realm=self.realm1,
                    resolver=self.resolvername1)

        user_str = "{0!s}".format(user)
        self.assertTrue(user_str == "<root.resolver1@realm1>", user_str)

        self.assertFalse(user.is_empty())
        self.assertTrue(User().is_empty())

        user_repr = "{0!r}".format(user)
        expected = "User(login='root', realm='realm1', resolver='resolver1')"
        self.assertTrue(user_repr == expected, user_repr)

    def test_01_create_token(self):
        db_token = Token(self.serial1, tokentype="motp")
        db_token.save()
        token = MotpTokenClass(db_token)
        token.update({"otpkey": "909a4d4ba980b2c6",
                      "motppin": self.motppin,
                      "pin": self.otppin})
        self.assertTrue(token.token.serial == self.serial1, token)
        self.assertTrue(token.token.tokentype == "motp", token.token.tokentype)
        self.assertTrue(token.type == "motp", token)
        class_prefix = token.get_class_prefix()
        self.assertTrue(class_prefix == "PIMO", class_prefix)
        self.assertTrue(token.get_class_type() == "motp", token)

    def test_02_check_password(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = MotpTokenClass(db_token)

        # Wrong OTP value
        r = token.check_otp("aba73b")
        self.assertTrue(r == -1, r)

        # check pin+otp:
        token.set_pin(self.otppin)
        r = token.authenticate("{0!s}aba73b".format(self.otppin))
        self.assertTrue(r[0], r)
        self.assertTrue(r[1] == -1, r)

    def test_03_enroll_genkey(self):
        db_token = Token(self.serial2, tokentype="motp")
        db_token.save()
        token = MotpTokenClass(db_token)
        token.update({"genkey": "1",
                      "motppin": self.motppin,
                      "pin": self.otppin})
        db_token = Token.query.filter(Token.serial == self.serial2).first()
        token = MotpTokenClass(db_token)
        # check that the userpin is set
        self.assertTrue(token.token.user_pin, token.token.user_pin)
        # check that the otp value is set
        self.assertTrue(token.token.key_enc, token.token.key_enc)

    def test_16_init_detail(self):
        db_token = Token.query.filter_by(serial=self.serial2).first()
        token = MotpTokenClass(db_token)
        token.add_init_details("otpkey", "11223344556677889900")
        token.add_user(User(login="cornelius",
                            realm=self.realm1))
        token.save()
        self.assertEqual(token.token.first_owner.resolver, self.resolvername1)
        self.assertEqual(token.token.first_owner.user_id, "1000")

        user_object = token.user
        self.assertTrue(user_object.login == "cornelius",
                        user_object)
        self.assertTrue(user_object.resolver == self.resolvername1,
                        user_object)

        detail = token.get_init_detail()
        self.assertTrue("otpkey" in detail, detail)
        # but the otpkey must not be written to token.token.info (DB)
        # As this only writes the OTPkey to the internal init_details dict
        self.assertTrue("otpkey" not in token.token.get_info(),
                        token.token.get_info())

        # Now get the Token2 URL, which we only
        # get, if a user is specified.
        detail = token.get_init_detail(user=User("cornelius",
                                                 self.realm1))
        self.assertTrue("otpkey" in detail, detail)
        otpkey = detail.get("otpkey")
        self.assertTrue("img" in otpkey, otpkey)
        self.assertTrue("motpurl" in detail, detail)
        motpurl = detail.get("motpurl").get("value")
        self.assertTrue(motpurl == 'motp://privacyidea:mylabel?'
                        'secret=11223344556677889900', motpurl)
        self.assertRaises(Exception, token.set_init_details, "invalid value")
        token.set_init_details({"detail1": "value1"})
        self.assertTrue("detail1" in token.get_init_details(),
                        token.get_init_details())


    def test_04_class_methods(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = MotpTokenClass(db_token)

        info = token.get_class_info()
        self.assertTrue(info.get("title") == "mOTP Token", info.get(
            'title'))

        info = token.get_class_info("title")
        self.assertTrue(info == "mOTP Token", info)

    def test_05_test_vector(self):
        # Testvector from
        # https://github.com/neush/otpn900/blob/master/src/test_motp.c

        key = "0123456789abcdef"
        epoch = [ 129612120, 129612130, 0, 4, 129612244, 129612253]
        pins = ["6666", "6666", "1", "1", "77777777", "77777777"]
        otps = ["6ed4e4", "502a59", "bd94a4", "fb596e", "7abf75", "4d4ac4"]

        i = 0
        motp1 = mTimeOtp(key=key, pin=pins[0])
        for e in epoch:
            pin = pins[i]
            otp = otps[i]
            sotp = motp1.calcOtp(e, key, pin)

            self.assertTrue(sotp == otp, "{0!s}=={1!s}".format(sotp, otp))
            i += 1

    def test_06_reuse_otp_value(self):
        key = "0123456789abcdef"
        db_token = Token("motp002", tokentype="motp")
        db_token.save()
        token = MotpTokenClass(db_token)
        token.update({"otpkey": key,
                      "motppin": "6666",
                      "pin": "test"})
        self.assertTrue(token.token.tokentype == "motp", token.token.tokentype)
        self.assertTrue(token.type == "motp", token)
        class_prefix = token.get_class_prefix()
        self.assertTrue(class_prefix == "PIMO", class_prefix)
        self.assertTrue(token.get_class_type() == "motp", token)

        # Correct OTP value
        r = token.check_otp("6ed4e4", options={"initTime": 129612120})
        self.assertTrue(r == 129612120, r)

        # Check the same value again
        r = token.check_otp("6ed4e4", options={"initTime": 129612120})
        self.assertTrue(r == -1, r)
