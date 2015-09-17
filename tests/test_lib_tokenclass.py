"""
This test file tests the lib.tokenclass

The lib.tokenclass depends on the DB model and lib.user
"""
PWFILE = "tests/testdata/passwords"

from .base import MyTestCase
from privacyidea.lib.resolver import (save_resolver)
from privacyidea.lib.realm import (set_realm)
from privacyidea.lib.user import (User)
from privacyidea.lib.tokenclass import (TokenClass,
                                        DATE_FORMAT)
from privacyidea.models import (Token,
                                 Config,
                                Challenge)
import datetime


class TokenBaseTestCase(MyTestCase):
    '''
    Test the token on the database level
    '''
    resolvername1 = "resolver1"
    resolvername2 = "Resolver2"
    resolvername3 = "reso3"
    realm1 = "realm1"
    realm2 = "realm2"
    serial1 = "SE123456"
    
    # set_user, get_user, reset, set_user_identifiers
    
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
        
        user_str = "%s" % user
        self.assertTrue(user_str == "<root.resolver1@realm1>", user_str)
        
        self.assertFalse(user.is_empty())
        self.assertTrue(User().is_empty())
        
        user_repr = "%r" % user
        expected = "User(login='root', realm='realm1', resolver='resolver1')"
        self.assertTrue(user_repr == expected, user_repr)

    def test_01_create_token(self):
        db_token = Token(self.serial1, tokentype="unknown")
        db_token.save()
        token = TokenClass(db_token)
        self.assertTrue(token.token.serial == self.serial1, token)
        self.assertTrue(token.token.tokentype == "unknown", token.token)
        self.assertTrue(token.type == "unknown", token)
        
        token.set_type("newtype")
        self.assertTrue(token.token.tokentype == "newtype", token.token)
        self.assertTrue(token.type == "newtype", token)
        self.assertTrue(token.get_type() == "newtype", token)
        
        self.assertTrue(token.get_class_prefix() == "UNK", token)
        self.assertTrue(token.get_class_type() is None, token)
        token.save()

        info = token.get_class_info()
        self.assertTrue(info == {}, "%s" % info)
        
    def test_02_set_user(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TokenClass(db_token)
        self.assertTrue(token.token.tokentype == "newtype",
                        token.token.tokentype)
        self.assertTrue(token.type == "newtype", token.type)
        
        token.set_user(User(login="cornelius",
                            realm=self.realm1))
        self.assertTrue(token.token.resolver_type == "passwdresolver",
                        token.token.resolver_type)
        self.assertTrue(token.token.resolver == self.resolvername1,
                        token.token.resolver)
        self.assertTrue(token.token.user_id == "1000",
                        token.token.user_id)
        
        user_object = token.get_user()
        self.assertTrue(user_object.login == "cornelius",
                        user_object)
        self.assertTrue(user_object.resolver == self.resolvername1,
                        user_object)
        
        token.set_user_identifiers(2000, self.resolvername1, "passwdresolver")
        self.assertTrue(int(token.token.user_id) == 2000, token.token.user_id)

    def test_03_reset_failcounter(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TokenClass(db_token)
        token.token.failcount = 10
        token.reset()
        self.assertTrue(token.token.failcount == 0,
                        token.token.failcount)
        
    def test_04_base_methods(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TokenClass(db_token)
        self.assertTrue(token.check_otp("123456", 1, 10) == -1)
        self.assertTrue(token.get_otp() == (-2, 0, 0, 0))
        res = token.get_multi_otp()
        self.assertTrue(res[0] is False, res)
        
        c = token.create_challenge("transactionid")
        self.assertTrue(c[0], c)
        self.assertTrue("transactionid" in c[2], c)

        c = token.create_challenge()
        self.assertTrue(c[0], c)

        # set the description
        token.set_description("something new")
        self.assertTrue(token.token.description == "something new",
                        token.token)
        
        # set defaults
        token.set_defaults()
        self.assertTrue(token.token.otplen == 6)
        self.assertTrue(token.token.sync_window == 1000)
        
        token.resync("1234", "3456")
        
        token.token.count_window = 17
        self.assertTrue(token.get_otp_count_window() == 17)
        
        token.token.count = 18
        self.assertTrue(token.get_otp_count() == 18)
        
        token.token.active = False
        self.assertTrue(token.is_active() is False)
        
        token.token.failcount = 7
        self.assertTrue(token.get_failcount() == 7)
        token.set_failcount(8)
        self.assertTrue(token.token.failcount == 8)
        
        token.token.maxfail = 12
        self.assertTrue(token.get_max_failcount() == 12)
        
        self.assertTrue(token.get_user_id() == token.token.user_id)
        
        self.assertTrue(token.get_serial() == "SE123456", token.token.serial)
        self.assertTrue(token.get_tokentype() == "newtype",
                        token.token.tokentype)
        
        token.set_so_pin("sopin")
        token.set_user_pin("userpin")
        token.set_otpkey("123456")
        token.set_otplen(8)
        token.set_otp_count(1000)
        self.assertTrue(len(token.token.so_pin) == 32,
                        token.token.so_pin)
        self.assertTrue(len(token.token.user_pin) == 32,
                        token.token.user_pin)
        self.assertTrue(len(token.token.key_enc) == 32,
                        token.token.key_enc)
        self.assertTrue(token.get_otplen() == 8)
        self.assertTrue(token.token.count == 1000,
                        token.token.count)
        
        token.set_maxfail(1000)
        self.assertTrue(token.token.maxfail == 1000)
        
        token.set_count_window(52)
        self.assertTrue(token.get_count_window() == 52)
        
        token.set_sync_window(53)
        self.assertTrue(token.get_sync_window() == 53)

    def test_06_set_pin(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TokenClass(db_token)
        token.set_pin("hallo")
        (ph1, pseed) = token.get_pin_hash_seed()
        # check the database
        token.set_pin("blubber")
        ph2 = token.token.pin_hash
        self.assertTrue(ph1 != ph2)
        token.set_pin_hash_seed(ph1, pseed)
        
    def test_07_enable(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TokenClass(db_token)
        token.enable(False)
        self.assertTrue(token.token.active is False)
        token.enable()
        self.assertTrue(token.token.active)        
        
    def test_05_get_set_realms(self):
        set_realm(self.realm2)
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TokenClass(db_token)
        realms = token.get_realms()
        self.assertTrue(len(realms) == 1, realms)
        token.set_realms([self.realm1, self.realm2])
        realms = token.get_realms()
        self.assertTrue(len(realms) == 2, realms)
        
    def test_99_delete_token(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TokenClass(db_token)
        token.delete_token()
        
        db_token = Token.query.filter_by(serial=self.serial1).first()
        self.assertTrue(db_token is None, db_token)

    def test_08_info(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TokenClass(db_token)
        token.set_hashlib("sha1")
        tinfo = token.token.get_info()
        self.assertTrue("hashlib" in tinfo, tinfo)
        
    def test_09_failcount(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TokenClass(db_token)
        start = token.token.failcount
        end = token.inc_failcount()
        self.assertTrue(end == start + 1, (end, start))
        
    def test_10_get_hashlib(self):
        # check if functions are returned
        for hl in ["sha1", "md5", "sha256", "sha512",
                   "sha224", "sha384", "", None]:
            self.assertTrue(hasattr(TokenClass.get_hashlib(hl),
                                    '__call__'),
                            TokenClass.get_hashlib(hl))
    
    def test_11_tokeninfo(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TokenClass(db_token)
        token.add_tokeninfo("key1", "value2")
        info1 = token.get_tokeninfo()
        self.assertTrue("key1" in info1, info1)
        token.add_tokeninfo("key2", "value3")
        info2 = token.get_tokeninfo()
        self.assertTrue("key2" in info2, info2)
        token.set_tokeninfo(info1)
        info2 = token.get_tokeninfo()
        self.assertTrue("key2" not in info2, info2)
        self.assertTrue(token.get_tokeninfo("key1") == "value2",
                        info2)
        
        # auth counter
        token.set_count_auth_success_max(200)
        token.set_count_auth_max(1000)
        token.set_count_auth_success(100)
        token.inc_count_auth_success()
        token.set_count_auth(200)
        token.inc_count_auth()
        self.assertTrue(token.get_count_auth_success_max() == 200)
        self.assertTrue(token.get_count_auth_success() == 101)
        self.assertTrue(token.get_count_auth_max() == 1000)
        self.assertTrue(token.get_count_auth() == 201)
        
        self.assertTrue(token.check_auth_counter())
        token.set_count_auth_max(10)
        self.assertFalse(token.check_auth_counter())
        token.set_count_auth_max(1000)
        token.set_count_auth_success_max(10)
        self.assertFalse(token.check_auth_counter())
        
        # handle validity end date
        token.set_validity_period_end("30/12/14 16:00")
        end = token.get_validity_period_end()
        self.assertTrue(end == "30/12/14 16:00", end)
        self.assertRaises(Exception,
                          token.set_validity_period_end, "wrong date")
        # handle validity start date
        token.set_validity_period_start("30/12/13 16:00")
        start = token.get_validity_period_start()
        self.assertTrue(start == "30/12/13 16:00", start)
        self.assertRaises(Exception,
                          token.set_validity_period_start, "wrong date")
        
        self.assertFalse(token.check_validity_period())
        # THe token is valid till 2021, this should be enough!
        token.set_validity_period_end("30/12/21 16:00")
        self.assertTrue(token.check_validity_period())

        token.set_validity_period_end("2015-05-22T22:00:00.000Z")
        end = token.get_validity_period_end()
        self.assertEqual(end, "22/05/15 22:00")

        token.set_validity_period_start("2015-05-22T22:00:00.000Z")
        start = token.get_validity_period_start()
        self.assertEqual(start, "22/05/15 22:00")

        # check validity period
        # +5 days
        end_date = datetime.datetime.now() + datetime.timedelta(5)
        end = end_date.strftime(DATE_FORMAT)
        token.set_validity_period_end(end)
        # - 5 days
        start_date = datetime.datetime.now() - datetime.timedelta(5)
        start = start_date.strftime(DATE_FORMAT)
        token.set_validity_period_start(start)
        self.assertTrue(token.check_validity_period())
        
        # check before start date
        # +5 days
        end_date = datetime.datetime.now() + datetime.timedelta(5)
        end = end_date.strftime(DATE_FORMAT)
        token.set_validity_period_end(end)
        # + 2 days
        start_date = datetime.datetime.now() + datetime.timedelta(2)
        start = start_date.strftime(DATE_FORMAT)
        token.set_validity_period_start(start)
        self.assertFalse(token.check_validity_period())
        
        # check after enddate
        # -1 day
        end_date = datetime.datetime.now() - datetime.timedelta(1)
        end = end_date.strftime(DATE_FORMAT)
        token.set_validity_period_end(end)
        # - 10 days
        start_date = datetime.datetime.now() - datetime.timedelta(10)
        start = start_date.strftime(DATE_FORMAT)
        token.set_validity_period_start(start)
        self.assertFalse(token.check_validity_period())

    def test_11_tokeninfo_with_type(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TokenClass(db_token)
        token.add_tokeninfo("radius.secret", "secret", value_type="password")
        info1 = token.get_tokeninfo()
        self.assertTrue("radius.secret" in info1, info1)
        self.assertTrue("radius.secret.type" in info1, info1)

        info = token.get_tokeninfo("radius.secret")
        self.assertTrue(info == "secret")

    def test_11_tokeninfo_encrypt(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TokenClass(db_token)

        token.add_tokeninfo("radius.secret", "topSecret",
                            value_type="password")
        info1 = token.get_tokeninfo()
        self.assertTrue("radius.secret" in info1, info1)
        self.assertTrue("radius.secret.type" in info1, info1)
        # get_tokeninfo without parameters does not decrypt!
        self.assertTrue(info1.get("radius.secret") != "topSecret",
                        info1.get("radius.secret"))

        # get_tokeninfo with parameter does decrypt!
        info = token.get_tokeninfo("radius.secret")
        self.assertTrue(info == "topSecret", info)

        # THe same with set_tokeninfo
        token.set_tokeninfo({"radius.secret": "otherSecret",
                             "radius.secret.type": "password"})
        info1 = token.get_tokeninfo()
        self.assertTrue("radius.secret" in info1, info1)
        self.assertTrue("radius.secret.type" in info1, info1)
        # get_tokeninfo without parameters does not decrypt!
        self.assertTrue(info1.get("radius.secret") != "otherSecret",
                        info1.get("radius.secret"))

        # get_tokeninfo with parameter does decrypt!
        info = token.get_tokeninfo("radius.secret")
        self.assertTrue(info == "otherSecret", info)

    def test_12_inc_otp_counter(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TokenClass(db_token)
        
        token.set_otp_count(10)
        self.assertTrue(token.token.count == 10, token.token.count)
        # increase counter by 1
        token.inc_otp_counter()
        self.assertTrue(token.token.count == 11, token.token.count)
        # increase counter to 21
        Config(Key="DefaultResetFailCount", Value=True).save()
        token.inc_otp_counter(counter=20)
        self.assertTrue(token.token.count == 21, token.token.count)

    def test_13_check_otp(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TokenClass(db_token)
        self.assertTrue(token.check_otp_exist("123456") == -1)
        
    def test_14_split_pin_pass(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TokenClass(db_token)
        
        token.token.otplen = 6
        # postpend pin
        from privacyidea.lib.config import set_prepend_pin
        set_prepend_pin(False)
        (_res, pin, value) = token.split_pin_pass("123456test")
        self.assertTrue(pin == "test", pin)
        self.assertTrue(value == "123456", value)
        # prepend pin
        set_prepend_pin(True)
        res, pin, value = token.split_pin_pass("test123456")
        self.assertTrue(pin == "test", pin)
        self.assertTrue(value == "123456", value)
        
    def test_15_check_pin(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TokenClass(db_token)
        token.set_pin("test")
        self.assertTrue(token.check_pin("test"))
        self.assertFalse(token.check_pin("wrong pin"))
        
    def test_15_status_validation(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TokenClass(db_token)
        token.status_validation_fail()
        token.status_validation_success()
#        d = token.get_vars()
#        self.assertTrue("type" in d, d)
#        self.assertTrue("mode" in d, d)
#        self.assertTrue("token" in d, d)

    def test_16_init_detail(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TokenClass(db_token)
        token.add_init_details("otpkey", "secretkey")
        detail = token.get_init_detail()
        self.assertTrue("otpkey" in detail, detail)

        # but the otpkey must not be written to token.token.info (DB)
        self.assertTrue("otpkey" not in token.token.get_info(),
                        token.token.get_info())

        token.get_QRimage_data({"googleurl": "hotp://"})
        self.assertRaises(Exception, token.set_init_details, "unvalid value")
        token.set_init_details({"detail1": "value1"})
        self.assertTrue("detail1" in token.get_init_details(),
                        token.get_init_details())

    def test_16_tokeninfo(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TokenClass(db_token)
        token.set_tokeninfo({"something": "else"})
        ti = token.get_tokeninfo()
        self.assertTrue("something" in ti, ti)
        token.add_tokeninfo("nochwas", "Wert")
        ti = token.get_tokeninfo()
        self.assertTrue("something" in ti, ti)
        self.assertTrue("nochwas" in ti, ti)

    def test_17_update_token(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TokenClass(db_token)
        # Failed update: genkey wrong
        self.assertRaises(Exception,
                          token.update,
                          {"description": "new desc",
                           "genkey": "17"})
        # Failed update: genkey and otpkey used at the same time
        self.assertRaises(Exception,
                          token.update,
                          {"otpkey": "123456",
                           "genkey": "1"})
        
        token.update({"otpkey": "123456",
                      "pin": "654321",
                      "otplen": 6})
        self.assertTrue(token.check_pin("654321"))
        self.assertTrue(token.token.otplen == 6)
        
        # save pin encrypted
        token.update({"genkey": 1,
                      "pin": "secret",
                      "encryptpin": "true"})
        # check if the PIN is encrypted
        self.assertTrue(token.token.pin_hash.startswith("@@"),
                        token.token.pin_hash)
        
        # update token without otpkey
        token.update({"description": "test"})

    def test_18_challenges(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TokenClass(db_token)

        db_token.set_pin("test")
        # No challenge request
        req = token.is_challenge_request("test", User(login="cornelius",
                                                      realm=self.realm1))
        self.assertFalse(req, req)
        # A challenge request
        req = token.is_challenge_request("test",
                                         User(login="cornelius",
                                              realm=self.realm1),
                                         {"data": "a challenge"})
        self.assertTrue(req, req)

        resp = token.is_challenge_response(User(login="cornelius",
                                                realm=self.realm1),
                                            "test123456")
        self.assertFalse(resp, resp)
        resp = token.is_challenge_response(User(login="cornelius",
                                                realm=self.realm1),
                                            "test123456",
                                            options={"transaction_id": "123456789"})
        self.assertTrue(resp, resp)

        # test if challenge is valid
        C = Challenge("S123455", transaction_id="tid", challenge="Who are you?")
        C.save()
        self.assertTrue(C.is_valid())

    def test_19_pin_otp_functions(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        db_token.set_pin("test")
        token = TokenClass(db_token)
        self.assertTrue(db_token.otplen == 6, 6)
        (res, pin, otp) = token.split_pin_pass("test123456")
        self.assertTrue(pin == "test", pin)
        self.assertTrue(otp == "123456", otp)
        self.assertTrue(token.check_pin(pin), pin)
        self.assertTrue(token.check_otp("123456") == -1)

        res = token.authenticate("test123456")
        self.assertTrue(res == (True, -1, None), res)

    def test_20_check_challenge_response(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        db_token.set_pin("test")
        token = TokenClass(db_token)
        r = token.check_challenge_response(user=None,
                                           passw="123454")
        # check that challenge does not match
        self.assertTrue(r == -1)

        # create a challenge and match the transaction_id
        c = Challenge(self.serial1, transaction_id="mytransaction",
                      challenge="Blah, what now?")
        # save challenge to the database
        c.save()
        r = token.check_challenge_response(user=None,
                                           passw="123454",
                                           options={"state": "mytransaction"})
        # The challenge matches, but the OTP does not match!
        self.assertTrue(r == -1, r)
        
        # test the challenge janitor
        c1 = Challenge(self.serial1, transaction_id="t1", validitytime=0)
        c1.save()
        c2 = Challenge(self.serial1, transaction_id="t2", validitytime=0)
        c2.save()
        c3 = Challenge(self.serial1, transaction_id="t3", validitytime=0)
        c3.save()
        c4 = Challenge(self.serial1, transaction_id="t4", validitytime=0)
        c4.save()
        # Delete potentiall expired challenges
        token.challenge_janitor()
        # Check, that the challenge does not exist anymore
        r = Challenge.query.filter(Challenge.transaction_id == "t1").count()
        self.assertTrue(r == 0, r)

    def test_21_get_token_data_as_dict(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TokenClass(db_token)
        token_data = token.get_as_dict()

        print(token_data)
        self.assertTrue("info" in token_data)
        self.assertTrue(token_data.get("user_id") == "2000")
        self.assertTrue(token_data.get("tokentype") == "newtype")
        self.assertTrue(token_data.get("count_window") == 52)

    def test_22_store_tokeninfo_longer_than_2000_byte(self):
        data = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDJy0rLoxqc8SsY8DVAFi" \
               "jMsQyCvhBu4K40hdZOacXK4O6OgnacnSKN56MP6pzz2+4svzvDzwvkFsvf3" \
               "4pbsgDF67PPSCsimmjEQjf0UfamBKh0cl181CbPYsph3UTBOCgHh3FFDXBd" \
               "uPK4DQzEVQpmqe80h+lsvQ81qPYagbRW6fpd0uWn9H7a/qiLQZsiKLL07HGB" \
               "+NwWue4os0r9s4qxeG76K6QM7nZKyC0KRAz7CjAf+0X7YzCOu2pzyxVdj/" \
               "T+KArFcMmq8Vdz24mhcFFXTzU3wveas1A9rwamYWB+Spuohh/OrK3wDsrry" \
               "StKQv7yofgnPMsTdaL7XxyQVPCmh2jVl5ro9BPIjTXsre9EUxZYFVr3EIECR" \
               "DNWy3xEnUHk7Rzs734Rp6XxGSzcSLSju8/MBzUVe35iXfXDRcqTcoA0700pI" \
               "b1ANYrPUO8Up05v4EjIyBeU61b4ilJ3PNcEVld6FHwP3Z7F068ef4DXEC/d" \
               "7pibrp4Up61WYQIXV/utDt3NDg/Zf3iqoYcJNM/zIZx2j1kQQwqtnbGqxJM" \
               "rL6LtClmeWteR4420uZxafLE9AtAL4nnMPuubC87L0wJ88un9teza/N02K" \
               "JMHy01Yz3iJKt3Ou9eV6kqOei3kvLs5dXmriTHp6g9whtnN6/Liv9SzZPJ" \
               "Ts8YfThi34Wccrw== NetKnights GmbH"

        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TokenClass(db_token)

        token.add_tokeninfo("sshkey", data, value_type="password")

        sshkey = token.get_tokeninfo("sshkey")
        self.assertTrue(sshkey == data, sshkey)

    def test_31_revoke(self):
        db_token = Token.query.filter_by(serial=self.serial1).first()
        token = TokenClass(db_token)
        token.revoke()
        self.assertTrue(token.is_revoked())
        self.assertTrue(token.is_locked())
        self.assertTrue(token.token.active is False)
        # A revoked token can not be enabled anymore
        self.assertRaises(Exception, token.enable)

