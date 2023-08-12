# -*- coding: utf-8 -*-
"""
This test file tests the lib.token methods.

The lib.token depends on the DB model and lib.user and
all lib.tokenclasses

This tests the token functions on an interface level

We start with simple database functions:

getTokens4UserOrSerial
gettokensoftype
getToken....
"""
from .base import MyTestCase, FakeAudit, FakeFlaskG
from privacyidea.lib.user import (User)
from privacyidea.lib.tokenclass import (TokenClass, TOKENKIND,
                                        FAILCOUNTER_EXCEEDED,
                                        FAILCOUNTER_CLEAR_TIMEOUT)
from privacyidea.lib.token import weigh_token_type
from privacyidea.lib.tokens.totptoken import TotpTokenClass
from privacyidea.models import (db, Token, Challenge, TokenRealm)
from privacyidea.lib.config import (set_privacyidea_config, get_token_types,
                                    delete_privacyidea_config, SYSCONF)
from privacyidea.lib.policy import (set_policy, SCOPE, ACTION, PolicyClass,
                                    delete_policy)
from privacyidea.lib.utils import b32encode_and_unicode, hexlify_and_unicode
from privacyidea.lib.error import PolicyError
import datetime
from dateutil import parser
import hashlib
import binascii
import warnings
from privacyidea.lib.token import (create_tokenclass_object,
                                   get_tokens, list_tokengroups,
                                   get_token_type, check_serial,
                                   get_num_tokens_in_realm,
                                   get_realms_of_token,
                                   token_exist, get_token_owner, is_token_owner,
                                   get_tokenclass_info,
                                   get_tokens_in_resolver, get_otp,
                                   get_token_by_otp, get_serial_by_otp,
                                   gen_serial, init_token, remove_token,
                                   set_realms, set_defaults, assign_token,
                                   unassign_token, resync_token,
                                   reset_token, set_pin, set_pin_user,
                                   set_pin_so, enable_token,
                                   is_token_active, set_hashlib, set_otplen,
                                   set_count_auth, add_tokeninfo,
                                   set_sync_window, set_count_window,
                                   set_description, get_multi_otp,
                                   set_max_failcount, copy_token_pin,
                                   copy_token_user, lost_token,
                                   check_token_list, check_serial_pass,
                                   check_realm_pass,
                                   check_user_pass,
                                   get_dynamic_policy_definitions,
                                   get_tokens_paginate,
                                   set_validity_period_end,
                                   set_validity_period_start, delete_tokeninfo,
                                   import_token, get_one_token,
                                   get_tokens_from_serial_or_user,
                                   get_tokens_paginated_generator,
                                   assign_tokengroup, unassign_tokengroup)
from privacyidea.lib.tokengroup import set_tokengroup, delete_tokengroup
from privacyidea.lib.error import (TokenAdminError, ParameterError,
                                   privacyIDEAError, ResourceNotFoundError)
from privacyidea.lib.tokenclass import DATE_FORMAT
from dateutil.tz import tzlocal

PWFILE = "tests/testdata/passwords"
OTPKEY = "3132333435363738393031323334353637383930"
OTPKE2 = "31323334353637383930313233343536373839AA"
CHANGED_KEY = '31323334353637383930313233343536373839AA'


class TokenTestCase(MyTestCase):
    """
    Test the lib.token on an interface level
    """

    def test_00_create_realms(self):
        self.setUp_user_realms()

    def test_01_create_token(self):
        for serial in self.serials:
            db_token = Token(serial, tokentype="totp")
            db_token.update_otpkey(self.otpkey)
            db_token.save()
            token = TotpTokenClass(db_token)
            self.assertTrue(token.token.serial == serial, token)
            self.assertTrue(token.token.tokentype == "totp",
                            token.token.tokentype)
            self.assertTrue(token.type == "totp", token)
            class_prefix = token.get_class_prefix()
            self.assertTrue(class_prefix == "TOTP", class_prefix)
            self.assertTrue(token.get_class_type() == "totp", token)

            # Now we create a tokenclass, without knowing, that it is TOTP
            token_object = create_tokenclass_object(db_token)
            # Do some tests, that we have a TotpTokenClass
            self.assertTrue(token_object.type == "totp", token_object.type)
            self.assertTrue(token_object.mode[0] == "authenticate",
                            token_object.mode)
            self.assertTrue(token_object.mode[1] == "challenge",
                            token_object.mode)

        # Test wrong type or old entry in database
        # a wrong token type will create None
        db_token = Token("asdf", tokentype="remnant")
        db_token.update_otpkey(self.otpkey)
        db_token.save()
        token_object = create_tokenclass_object(db_token)
        self.assertTrue(token_object is None, token_object)
        # delete the token, so that we do not get confused, later
        db_token.delete()

    def test_02_get_tokens(self):
        # get All tokens
        tokenobject_list = get_tokens()
        # Check if these are valid tokentypes
        self.assertTrue(len(tokenobject_list) > 0, tokenobject_list)
        for token_object in tokenobject_list:
            self.assertTrue(token_object.type in get_token_types(),
                            token_object.type)

        # get assigned tokens
        tokenobject_list = get_tokens(assigned=True)
        self.assertTrue(len(tokenobject_list) == 0, tokenobject_list)
        # get unassigned tokens
        tokenobject_list = get_tokens(assigned=False)
        self.assertTrue(len(tokenobject_list) > 0, tokenobject_list)
        # pass the wrong parameter
        # This will ignore the filter!
        tokenobject_list = get_tokens(assigned="True")
        self.assertTrue(len(tokenobject_list) > 0, tokenobject_list)

        # get tokens of type HOTP
        tokenobject_list = get_tokens(tokentype="hotp")
        self.assertTrue(len(tokenobject_list) == 0, tokenobject_list)
        # get tokens of type TOTP
        tokenobject_list = get_tokens(tokentype="totp")
        self.assertTrue(len(tokenobject_list) > 0, tokenobject_list)

        # Search for tokens in realm
        db_token = Token("hotptoken",
                         tokentype="hotp",
                         userid=1000,
                         resolver=self.resolvername1,
                         realm=self.realm1)
        db_token.update_otpkey(self.otpkey)
        db_token.save()
        tokenobject_list = get_tokens(realm=self.realm1)
        self.assertTrue(len(tokenobject_list) == 1, tokenobject_list)
        self.assertTrue(tokenobject_list[0].type == "hotp",
                        tokenobject_list[0].type)

        # get tokens for a given serial number
        tokenobject_list = get_tokens(serial="hotptoken")
        self.assertTrue(len(tokenobject_list) == 1, tokenobject_list)

        # ...but not in an unassigned state!
        tokenobject_list = get_tokens(serial="hotptoken", assigned=False)
        self.assertTrue(len(tokenobject_list) == 0, tokenobject_list)
        # get the tokens for the given user
        tokenobject_list = get_tokens(user=User(login="cornelius",
                                                realm=self.realm1))
        self.assertTrue(len(tokenobject_list) == 1, tokenobject_list)

        # get tokens for a given tokeninfo of the token!!!
        token = init_token({"type": "yubikey",
                            "serial": "yk1",
                            "yubikey.prefix": "vv123456",
                            "otpkey": self.otpkey})
        self.assertEqual(token.token.serial, "yk1")
        tokenobject_list = get_tokens(tokeninfo={"yubikey.prefix": "vv123456"})
        self.assertEqual(len(tokenobject_list), 1)
        self.assertEqual(tokenobject_list[0].get_tokeninfo("yubikey.prefix"),
                         "vv123456")
        remove_token("yk1")

        # Tokeninfo with more than one entry is not supported
        self.assertRaises(privacyIDEAError, get_tokens,
                          tokeninfo={"key1": "value1",
                                     "key2": "value2"})

        # wildcard matches do not work for the ``serial`` parameter
        tokenobject_list = get_tokens(serial="hotptoke*")
        self.assertEqual(len(tokenobject_list), 0)
        # get tokens with a wildcard serial
        tokenobject_list = get_tokens(serial_wildcard="SE*")
        self.assertEqual(len(tokenobject_list), 3)
        # get all tokens
        tokenobject_list = get_tokens(serial_wildcard="*")
        self.assertEqual(len(tokenobject_list), 4)

    def test_03_get_token_type(self):
        ttype = get_token_type("hotptoken")
        self.assertTrue(ttype == "hotp", ttype)

        # test correct behavior with wildcards
        self.assertEqual(get_token_type("SE1"), "totp")
        self.assertEqual(get_token_type("SE*"), "")
        self.assertEqual(get_token_type("*1"), "")
        self.assertEqual(get_token_type("hotptoke*"), "")

    def test_04_check_serial(self):
        r, nserial = check_serial("hotptoken")
        self.assertFalse(r, (r, nserial))

        r, nserial = check_serial("Canbeusedfor a new token")
        self.assertTrue(r, (r, nserial))

    def test_05_get_num_tokens_in_realm(self):
        # one active token
        self.assertTrue(get_num_tokens_in_realm(self.realm1) == 1,
                        "{0!r}".format(get_num_tokens_in_realm(self.realm1)))
        # No active tokens
        self.assertTrue(get_num_tokens_in_realm(self.realm1, active=False) == 0)

    def test_05_get_token_in_resolver(self):
        tokenobject_list = get_tokens_in_resolver(self.resolvername1)
        self.assertTrue(len(tokenobject_list) > 0)

    def test_06_get_realms_of_token(self):
        # Return a list of realmnames for a token
        self.assertTrue(get_realms_of_token("hotptoken") == [self.realm1],
                        "{0!s}".format(get_realms_of_token("hotptoken")))

    def test_07_token_exist(self):
        self.assertTrue(token_exist("hotptoken"))
        self.assertFalse(token_exist("does not exist"))
        self.assertFalse(token_exist(""))

    def test_08_token_owner(self):
        # get_token_owner
        user = get_token_owner("hotptoken")
        self.assertTrue(user.login == "cornelius", user)
        user = get_token_owner(self.serials[0])
        self.assertFalse(user)
        # for non existing token
        with self.assertRaises(ResourceNotFoundError):
            user = get_token_owner("does not exist")

        # check if the token owner is cornelius
        user = User("cornelius", realm=self.realm1, resolver=self.resolvername1)
        self.assertTrue(is_token_owner("hotptoken", user),
                        get_token_owner("hotptoken"))
        self.assertFalse(is_token_owner("hotptoken", User()),
                         get_token_owner("hotptoken"))
        self.assertFalse(is_token_owner(self.serials[1], user),
                         get_token_owner(self.serials[1]))

    def test_09_get_tokenclass_info(self):
        info = get_tokenclass_info("hotp")
        self.assertTrue("user" in info, info)
        self.assertTrue(info.get("type") == "hotp", info)

    def test_11_get_otp(self):
        otp = get_otp("hotptoken")
        self.assertTrue(otp[2] == "755224", otp)
        otp = get_otp(self.serials[0],
                      current_time=datetime.datetime(2014, 12, 4, 12, 0))
        self.assertTrue(otp[2] == "938938", otp)
        # the serial does not exist
        with self.assertRaises(ResourceNotFoundError):
            get_otp("does not exist")

    def test_12_get_token_by_otp(self):
        tokenobject = get_token_by_otp(get_tokens(), otp="755224")
        self.assertTrue(tokenobject.token.serial == "hotptoken", tokenobject)

        serial = get_serial_by_otp(get_tokens(), otp="287082")
        self.assertTrue(serial == "hotptoken", serial)

        # create a second HOTP token, so that we have two tokens,
        # that generate the same OTP value
        db_token = Token("token2",
                         tokentype="hotp")
        db_token.update_otpkey(self.otpkey)
        db_token.save()
        self.assertRaises(TokenAdminError, get_serial_by_otp,
                          get_tokens(), "287922")
        db_token.delete()

    def test_14_gen_serial(self):
        serial = gen_serial(tokentype="hotp")
        # check the beginning of the serial
        self.assertTrue("OATH0001" in serial, serial)

        serial = gen_serial(tokentype="hotp", prefix="blah")
        # check the beginning of the serial
        self.assertTrue("blah0001" in serial, serial)

        serial = gen_serial()
        # check the beginning of the serial
        self.assertTrue("PIUN0000" in serial, serial)

        set_privacyidea_config("SerialLength", 12)
        serial = gen_serial(tokentype="hotp")
        self.assertTrue("OATH0001" in serial, serial)
        self.assertEqual(len(serial), len("OATH") + 12)
        set_privacyidea_config("SerialLength", 8)

    def test_15_init_token(self):
        count = get_tokens(count=True)
        self.assertTrue(count == 4, count)
        tokenobject = init_token({"serial": "NEW001", "type": "hotp",
                                  "otpkey": "1234567890123456"},
                                 user=User(login="cornelius",
                                           realm=self.realm1))
        self.assertTrue(tokenobject.token.tokentype == "hotp",
                        tokenobject.token)
        # Now there is one more token in the database
        count = get_tokens(count=True)
        self.assertTrue(count == 5, count)

        # try to create unknown tokentype
        self.assertRaises(TokenAdminError, init_token, {"otpkey": "1234",
                                                        "type": "never_know"})

        # try to create the same token with another type
        self.assertRaises(TokenAdminError, init_token, {"otpkey": "1234",
                                                        "serial": "NEW001",
                                                        "type": "totp"})

        # try to update the same token with another user assignment
        self.assertRaises(TokenAdminError, init_token, {"otpkey": "1234",
                                                        "serial": "NEW001"},
                          user=User(login="hans", realm=self.realm1))
        # test that token was not assigned to the other user
        self.assertTrue(tokenobject.user == User(login="cornelius", realm=self.realm1))

        # update the existing token
        self.assertTrue(tokenobject.token.otplen == 6, tokenobject.token.otplen)
        tokenobject = init_token({"serial": "NEW001", "type": "hotp",
                                  "otpkey": "1234567890123456",
                                  "otplen": 8},
                                 user=User(login="cornelius",
                                           realm=self.realm1))
        self.assertTrue(tokenobject.token.otplen == 8, tokenobject.token.otplen)

        # add additional realms
        tokenobject = init_token({"serial": "NEW002", "type": "hotp",
                                  "otpkey": "1234567890123456",
                                  "realm": self.realm1})
        self.assertTrue(self.realm1 in tokenobject.token.get_realms(),
                        tokenobject.token.get_realms())

        tokenobject = init_token({"serial": "NEW003", "type": "hotp",
                                  "otpkey": "1234567890123456"},
                                 tokenrealms=[self.realm1])
        self.assertTrue(self.realm1 in tokenobject.token.get_realms(),
                        tokenobject.token.get_realms())

    def test_16_remove_token(self):
        self.assertRaises(ParameterError, remove_token)

        count1 = get_tokens(count=True)
        tokenobject = init_token({"type": "hotp",
                                  "otpkey": "1234567890123456",
                                  "realm": self.realm1})
        count2 = get_tokens(count=True)
        self.assertTrue(count2 == count1 + 1, count2)
        # check for the token association
        token_id = tokenobject.token.id
        realm_assoc = TokenRealm.query.filter(TokenRealm.token_id == \
            token_id).count()
        self.assertTrue(realm_assoc == 1, realm_assoc)
        # Add a challenge for this token
        challenge = Challenge(tokenobject.get_serial(), transaction_id="918273")
        challenge.save()
        chall_count = Challenge.query.filter(Challenge.serial ==
                                             tokenobject.get_serial()).count()
        self.assertTrue(chall_count == 1, chall_count)

        # remove the token
        count_remove = remove_token(serial=tokenobject.get_serial())
        self.assertTrue(count_remove == 1, count_remove)
        self.assertTrue(get_tokens(count=True) == count1)
        # check for the realm association
        realm_assoc = TokenRealm.query.filter(TokenRealm.token_id == \
            token_id).count()
        self.assertTrue(realm_assoc == 0, realm_assoc)
        # check if the challenge is removed
        chall_count = Challenge.query.filter(Challenge.serial ==
                                             tokenobject.get_serial()).count()
        self.assertTrue(chall_count == 0, chall_count)

    def test_16_set_realms(self):
        serial = "NEWREALM01"
        tokenobject = init_token({"serial": serial,
                                  "otpkey": "1234567890123456"})
        realms = get_realms_of_token(serial)
        self.assertEqual(realms, [], "{0!s}".format(realms))
        set_realms(serial, [self.realm1])
        realms = get_realms_of_token(serial)
        self.assertEqual(realms, [self.realm1], "{0!s}".format(realms))
        remove_token(serial=serial)
        realms = get_realms_of_token(serial)
        self.assertTrue(realms == [], "{0!s}".format(realms))


    def test_17_set_defaults(self):
        serial = "SETTOKEN"
        tokenobject = init_token({"serial": serial,
                                  "otpkey": "1234567890123456",
                                  "otplen": 8})
        self.assertTrue(tokenobject.token.otplen == 8)
        set_defaults(serial)
        self.assertTrue(tokenobject.token.otplen == 6)
        remove_token(serial)

    def test_18_assign_token(self):
        serial = "ASSTOKEN"
        user = User("cornelius", resolver=self.resolvername1,
                    realm=self.realm1)
        tokenobject = init_token({"serial": serial,
                                  "otpkey": "1234567890123456"})

        r = assign_token(serial, user, pin="1234")
        self.assertTrue(r)
        self.assertEqual(tokenobject.token.first_owner.user_id, "1000")

        # token already assigned...
        self.assertRaises(TokenAdminError, assign_token, serial,
                          User("shadow", realm=self.realm1))

        # unassign token
        r = unassign_token(serial)
        self.assertTrue(r)
        self.assertEqual(tokenobject.token.first_owner, None)

        remove_token(serial)
        # assign or unassign a token, that does not exist
        self.assertRaises(ResourceNotFoundError, assign_token, serial, user)
        self.assertRaises(ResourceNotFoundError, unassign_token, serial)

    def test_19_reset_resync(self):
        serial = "reset"
        tokenobject = init_token({"serial": serial,
                                  "otpkey": "1234567890123456"})
        otps = tokenobject.get_multi_otp(count=100)
        self.assertTrue(tokenobject.token.count == 0)
        # 20: '122407', 21: '505117', 22: '870960', 23: '139843', 24: '631376'
        self.assertTrue(otps[2].get("otp").get(20) == "122407", otps[2])
        self.assertTrue(tokenobject.token.count == 0)
        r = resync_token(serial, "122407", "505117")
        self.assertTrue(r)
        self.assertTrue(tokenobject.token.count == 22, tokenobject.token.count)
        tokenobject.token.failcount = 20
        r = reset_token(serial)
        self.assertTrue(r)
        self.assertTrue(tokenobject.token.failcount == 0)
        remove_token(serial)

        self.assertRaises(ParameterError, reset_token)

    def test_20_pin_token_so_user(self):
        serial = "pins"
        tokenobject = init_token({"serial": serial,
                                  "otpkey": "1234567890123456"})
        # user parameter is wrong
        self.assertRaises(ParameterError, set_pin, serial, None, "1234")
        # user and serial is missing
        self.assertRaises(ParameterError, set_pin)
        # now set the pin
        self.assertTrue(set_pin(serial, "1234") == 1)
        self.assertTrue(tokenobject.token.check_pin("1234"))
        self.assertTrue(tokenobject.token.user_pin == "")
        self.assertTrue(set_pin_user(serial, "1234") == 1)
        self.assertTrue(tokenobject.token.user_pin != "")
        self.assertTrue(tokenobject.token.so_pin == "")
        self.assertTrue(set_pin_so(serial, "1234") == 1)
        self.assertTrue(tokenobject.token.so_pin != "")
        remove_token(serial)


    def test_21_enable_disable(self):
        serial = "enable"
        tokenobject = init_token({"serial": serial,
                                  "otpkey": "1234567890123456"})
        # an active token does not need to be enabled
        r = enable_token(serial)
        self.assertTrue(r == 0, r)
        r = enable_token(serial, enable=False)
        self.assertTrue(r == 1, r)
        self.assertTrue(tokenobject.token.active == False,
                        tokenobject.token.active)
        self.assertFalse(is_token_active(serial))

        r = enable_token(serial)
        self.assertTrue(r == 1, r)
        self.assertTrue(is_token_active(serial))

        remove_token(serial)
        with self.assertRaises(ResourceNotFoundError):
            is_token_active(serial)

        self.assertRaises(ParameterError, enable_token)

    def test_22_set_hashlib(self):
        serial = "hashlib"
        tokenobject = init_token({"serial": serial,
                                  "otpkey": "1234567890123456"})

        r = set_hashlib(serial=serial, hashlib="sha256")
        self.assertTrue(r == 1)
        hashlib = tokenobject.token.get_info()
        self.assertTrue(hashlib.get("hashlib") == "sha256", hashlib)
        remove_token(serial)


    def test_23_set_otplen(self):
        serial = "otplen"
        tokenobject = init_token({"serial": serial,
                                  "otpkey": "1234567890123456"})

        r = set_otplen(serial=serial, otplen=8)
        self.assertTrue(r == 1)
        self.assertTrue(tokenobject.token.otplen == 8)
        remove_token(serial)

    def test_24_set_count_auth(self):
        serial = "count_auth"
        tokenobject = init_token({"serial": serial,
                                  "otpkey": "1234567890123456"})
        r = set_count_auth(serial=serial, count=100)
        self.assertTrue(r == 1)
        r = set_count_auth(serial=serial, count=101, max=True)
        self.assertTrue(r == 1)
        r = set_count_auth(serial=serial, count=102, success=True)
        self.assertTrue(r == 1)
        r = set_count_auth(serial=serial, count=103, max=True, success=True)
        self.assertTrue(r == 1)
        tinfo = tokenobject.token.get_info()
        self.assertTrue(tinfo.get("count_auth") == "100", tinfo)
        self.assertTrue(tinfo.get("count_auth_max") == "101", tinfo)
        self.assertTrue(tinfo.get("count_auth_success") == "102", tinfo)
        self.assertTrue(tinfo.get("count_auth_success_max") == "103", tinfo)

    def test_25_add_delete_tokeninfo(self):
        serial = "t1"
        tokenobject = init_token({"serial": serial, "genkey": 1})
        r = add_tokeninfo(serial, "something", "new")
        self.assertTrue(r == 1, r)
        tinfo1 = tokenobject.token.get_info()
        self.assertTrue(tinfo1.get("something") == "new", tinfo1)
        # delete existing tokeninfo entry
        r = delete_tokeninfo(serial, "something")
        self.assertEqual(r, 1)
        tinfo2 = tokenobject.token.get_info()
        self.assertNotIn("something", tinfo2)
        # delete non-existing tokeninfo entry
        r = delete_tokeninfo(serial, "somethingelse")
        self.assertEqual(r, 1) # this still returns 1, because 1 token was matched!
        # tokeninfo has not changed
        self.assertEqual(tokenobject.token.get_info(), tinfo2)
        # try to delete non-existing tokeninfo
        with self.assertRaises(ResourceNotFoundError):
            delete_tokeninfo('UNKNOWN-SERIAL', 'something')
        remove_token(serial)

    def test_26_set_sync_window(self):
        serial = "t1"
        tokenobject = init_token({"serial": serial, "genkey": 1})
        r = set_sync_window(serial, 23)
        self.assertTrue(r == 1, r)
        self.assertTrue(tokenobject.token.sync_window == 23,
                        tokenobject.token.sync_window)
        remove_token(serial)

    def test_27_set_count_window(self):
        serial = "t1"
        tokenobject = init_token({"serial": serial, "genkey": 1})
        r = set_count_window(serial, 45)
        self.assertTrue(r == 1, r)
        self.assertTrue(tokenobject.token.count_window == 45,
                        tokenobject.token.count_window)
        remove_token(serial)

    def test_28_set_description(self):
        serial = "t1"
        tokenobject = init_token({"serial": serial, "genkey": 1})
        r = set_description(serial, "new description")
        self.assertTrue(r == 1, r)
        self.assertTrue(tokenobject.token.description == "new description",
                        tokenobject.token.description)
        remove_token(serial)

    def test_29_get_multi_otp(self):
        r = get_multi_otp("hotptoken")
        self.assertTrue(r.get("error") == "No count specified", r)

        r = get_multi_otp("hotptoken", count=12)
        self.assertTrue(r.get("result") is True, r)
        self.assertTrue(len(r.get("otp")) == 12, r.get("otp"))

        # unknown serial number
        with self.assertRaises(ResourceNotFoundError):
            get_multi_otp("unknown", count=12)

    def test_30_set_max_failcount(self):
        serial = "t1"
        tokenobject = init_token({"serial": serial, "genkey": 1})
        r = set_max_failcount(serial, 112)
        self.assertTrue(r == 1, r)
        self.assertTrue(tokenobject.token.maxfail == 112,
                        "{0!s}".format(tokenobject.token.maxfail))
        remove_token(serial)

    def test_31_copy_token_pin(self):
        serial1 = "tcopy1"
        tobject1 = init_token({"serial": serial1, "genkey": 1})
        r = set_pin(serial1, "secret")
        self.assertTrue(r)
        serial2 = "tcopy2"
        tobject2 = init_token({"serial": serial2, "genkey": 1})
        r = copy_token_pin(serial1, serial2)
        self.assertTrue(r)

        # Now compare the pinhash
        self.assertTrue(tobject1.token.pin_hash == tobject2.token.pin_hash,
                        "{0!s} <> {1!s}".format(tobject1.token.pin_hash,
                                      tobject2.token.pin_hash))

        remove_token(serial1)
        remove_token(serial2)

    def test_32_copy_token_user(self):
        serial1 = "tcopy1"
        tobject1 = init_token({"serial": serial1, "genkey": 1})
        r = assign_token(serial1, User(login="cornelius", realm=self.realm1))
        self.assertTrue(r, r)
        serial2 = "tcopy2"
        tobject2 = init_token({"serial": serial2, "genkey": 1})

        r = copy_token_user(serial1, serial2)
        assert isinstance(tobject2, TokenClass)
        self.assertEqual(tobject2.token.first_owner.user_id, "1000")
        self.assertEqual(tobject2.token.first_owner.resolver, self.resolvername1)

        # check if the realms where copied:
        self.assertTrue(tobject2.get_realms() == [self.realm1])

        # check exceptions
        self.assertRaises(TokenAdminError, copy_token_user, serial1, "none")
        self.assertRaises(TokenAdminError, copy_token_user, "none", serial2)

        remove_token(serial1)
        remove_token(serial2)

    def test_33_lost_token(self):
        # create a token with a user
        serial1 = "losttoken"
        tobject1 = init_token({"serial": serial1, "genkey": 1})
        r = assign_token(serial1, User(login="cornelius", realm=self.realm1))
        self.assertTrue(r, r)

        # call the losttoken
        with self.assertRaises(ResourceNotFoundError):
            lost_token("doesnotexist")
        validity = 10
        r = lost_token(serial1)
        end_date = datetime.datetime.now(tzlocal()) + datetime.timedelta(days=validity)
        """
        r = {'end_date': '16/12/14 23:59',
             'pin': True, 'valid_to': 'xxxx', 'init': True, 'disable': 1,
             'user': True, 'serial': 'lostlosttoken', 'password':
             'EC7YRgr)ss9LcE*('}
        """
        self.assertTrue(r.get("pin"), r)
        self.assertTrue(r.get("init"), r)
        self.assertTrue(r.get("user"), r)
        self.assertTrue(r.get("serial") == "lost{0!s}".format(serial1), r)
        self.assertTrue(parser.parse(r.get("end_date")) <= end_date, r)
        remove_token("losttoken")
        remove_token("lostlosttoken")

    def test_34_check_token_list(self):
        # We can not authenticate with an unknown type
        # Such a token will not be returned by get_tokens...
        db_token = Token("serial72", tokentype="unknown")
        db_token.save()

        # set a matching OTP PIN for our hotp token
        set_pin("hotptoken", "hotppin40")
        tokenobject_list = get_tokens()

        # the HOTP token has the correct PIN but wrong otp value
        # The failcounter is increased
        hotp_tokenobject = get_tokens(serial="hotptoken")[0]
        hotp_tokenobject.set_pin("hotppin")
        hotp_tokenobject.save()
        old_failcount = hotp_tokenobject.token.failcount
        res, reply = check_token_list(tokenobject_list, "hotppin40123456")
        self.assertFalse(res)
        failcount = hotp_tokenobject.token.failcount
        self.assertEqual(failcount, old_failcount + 1, (old_failcount,
                                                        failcount))

        # if there is no token with at least a correct pin, we increase all
        # failcounters
        hotp_tokenobject = get_tokens(serial="hotptoken")[0]
        old_failcount = hotp_tokenobject.token.failcount
        res, reply = check_token_list(tokenobject_list, "everythingiswrong")
        self.assertFalse(res)
        failcount = hotp_tokenobject.token.failcount
        self.assertEqual(failcount, old_failcount + 1, (old_failcount,
                                                        failcount))

        # Now we do some successful auth with the HOTP token
        tokenobject_list = get_tokens(serial="hotptoken")
        """                        Truncated
           Count    Hexadecimal    Decimal        HOTP
           0        4c93cf18       1284755224     755224
           1        41397eea       1094287082     287082
           2         82fef30        137359152     359152
           3        66ef7655       1726969429     969429
           4        61c5938a       1640338314     338314
           5        33c083d4        868254676     254676
           6        7256c032       1918287922     287922
           7         4e5b397         82162583     162583
           8        2823443f        673399871     399871
           9        2679dc69        645520489     520489
           10                                     403154
           11                                     481090
           12                                     868912
           13                                     736127
        """
        hotp_tokenobject = tokenobject_list[0]
        old_counter = hotp_tokenobject.token.count
        res, reply = check_token_list(tokenobject_list, "hotppin399871")
        self.assertTrue(res)
        # check if the counter increased
        self.assertTrue(old_counter < hotp_tokenobject.token.count,
                        (old_counter, hotp_tokenobject.token.count))
        # but was it also increased in the database?
        tokenobject_list_new = get_tokens(serial="hotptoken")
        hotp_tokenobject_new = tokenobject_list_new[0]
        self.assertTrue(old_counter < hotp_tokenobject_new.token.count,
                        (old_counter, hotp_tokenobject.token.count))

        # False authentication
        old_failcount = hotp_tokenobject.token.failcount
        res, reply = check_token_list(tokenobject_list, "hotppin000000")
        self.assertFalse(res)
        # check the failcounter increased
        self.assertTrue(old_failcount + 1 == hotp_tokenobject.token.failcount)
        # Successful auth. The failcount needs to be resetted
        res, reply = check_token_list(tokenobject_list, "hotppin520489")
        self.assertTrue(res)
        self.assertTrue(hotp_tokenobject.token.failcount == 0)

        # Now we disable the hotp_tokenobject. If the token is disabled,
        # we must not be able to authenticate anymore with this very token.
        # But if the OTP value is valid, the counter is increased, anyway!
        old_counter = hotp_tokenobject.token.count
        hotp_tokenobject.enable(False)
        res, reply = check_token_list(tokenobject_list, "hotppin403154")
        self.assertFalse(res)
        self.assertTrue("Token is disabled" in reply.get("message"))
        self.assertEqual(old_counter + 1, hotp_tokenobject.token.count)
        # enable the token again
        hotp_tokenobject.enable(True)

        # Set HOTP as challenge response
        set_policy("check_token_list_CR", scope=SCOPE.AUTH, action="{0!s}=HOTP".format(
            ACTION.CHALLENGERESPONSE))

        hotp_tokenobject.add_tokeninfo("next_pin_change", "{0!s}".format(datetime.datetime(2019, 1, 7, 0, 0)))
        hotp_tokenobject.add_tokeninfo("next_password_change", "{0!s}".format(datetime.datetime(2019, 1, 7, 0, 0)))

        # Now the HOTP is a valid C/R token
        res, reply = check_token_list(tokenobject_list, "hotppin")
        self.assertFalse(res)
        self.assertTrue("multi_challenge" in reply)
        transaction_id = reply.get("transaction_id")
        res, reply = check_token_list(tokenobject_list, "481090", options={"transaction_id": transaction_id})
        self.assertTrue(res)

        # Create a challenge, but deactivate the token in the meantime:
        hotp_tokenobject.token.counter = 9
        hotp_tokenobject.save()
        res, reply = check_token_list(tokenobject_list, "hotppin")
        self.assertFalse(res)
        self.assertTrue("multi_challenge" in reply)
        transaction_id = reply.get("transaction_id")
        # deactivate token
        hotp_tokenobject.enable(False)
        hotp_tokenobject.save()
        res, reply = check_token_list(tokenobject_list, "481090", options={"transaction_id": transaction_id})
        self.assertFalse(res)

        # Have a challenge response token, but it is disabled.
        hotp_tokenobject.token.counter = 9
        hotp_tokenobject.save()
        res, reply = check_token_list(tokenobject_list, "hotppin")
        self.assertFalse(res)
        self.assertFalse("multi_challenge" in reply)
        self.assertEqual(reply.get("message"), "No active challenge response token found")

        hotp_tokenobject.enable()
        hotp_tokenobject.save()
        delete_policy("check_token_list_CR")

    def test_35_check_serial_pass(self):
        hotp_tokenobject = get_tokens(serial="hotptoken")[0]
        hotp_tokenobject.set_pin("hotppin")
        hotp_tokenobject.token.count = 10
        hotp_tokenobject.save()

        with self.assertRaises(ResourceNotFoundError):
            check_serial_pass("XXXXXXXXX", "password")

        #r = get_multi_otp("hotptoken", count=20)
        #self.assertTrue(r == 0, r)
        # 0: '520489', 1: '403154', 2: '481090', 3: '868912',
        # 4: '736127', 5: '229903', 6: '436521', 7: '186581',
        # 8: '447589', 9: '903435', 10: '578337', 11: '328281',
        # 12: '191635', 13: '184416', 14: '574561', 15: '797908'
        r, reply = check_serial_pass("hotptoken", "hotppin481090")
        self.assertTrue(r)
        # the same OTP value  must not match!
        # cko
        r, reply = check_serial_pass("hotptoken", "hotppin481090")
        self.assertFalse(r)

    def test_36_check_user_pass(self):
        hotp_tokenobject = get_tokens(serial="hotptoken")[0]
        user = User("shadow", realm=self.realm1)
        r, reply = check_user_pass(user, "passwordasdf")
        self.assertFalse(r)
        self.assertTrue(reply.get("message") == 'The user has no tokens '
                                                'assigned', "{0!s}".format(reply))

        user = User("cornelius", realm=self.realm1)
        r, reply = check_user_pass(user, "hotppin868912")
        self.assertTrue(r)
        r, reply = check_user_pass(user, "hotppin736127")
        #r = get_multi_otp("hotptoken", count=20)
        #self.assertTrue(r == 0, r)
        # 0: '520489', 1: '403154', 2: '481090', 3: '868912',
        # 4: '736127', 5: '229903', 6: '436521', 7: '186581',
        # 8: '447589', 9: '903435', 10: '578337', 11: '328281',
        # 12: '191635', 13: '184416', 14: '574561', 15: '797908'

    def test_36b_check_nonascii_pin(self):
        user = User("cornelius", self.realm1)
        serial = "nonasciipin"
        token = init_token({"type": "hotp",
                            "otpkey": self.otpkey,
                            "pin": "ünicøde",
                            "serial": serial}, user)
        r = check_user_pass(user, "µröng287082")
        self.assertEqual(r[0], False)
        self.assertEqual(r[1]['message'], 'wrong otp pin')
        r = check_user_pass(user, "ünicøde287082")
        self.assertEqual(r[0], True)
        r = check_user_pass(user, "ünicøde666666")
        self.assertEqual(r[0], False)
        self.assertEqual(r[1]['message'], 'wrong otp value')
        remove_token(serial)

    def test_37_challenge(self):
        # We create a challenge by first sending the PIN of the HOTP token
        # then we answer the challenge by sending the OTP.

        num1 = Challenge.query.filter(Challenge.serial == "hotptoken").count()
        # The correct PIN will create a challenge
        r, reply = check_serial_pass("hotptoken", "hotppin")
        self.assertTrue(r is False, r)
        num2 = Challenge.query.filter(Challenge.serial == "hotptoken").count()
        # check that the challenge is created
        self.assertTrue(num1 + 1 == num2, (num1, num2))
        self.assertTrue(type(reply) == dict, reply)
        transaction_id = reply.get("transaction_id","")
        self.assertTrue(len(transaction_id) > 10, reply)

        # Challenge Response, with the transaction id
        r, reply = check_serial_pass("hotptoken", "436521",
                                     {"transaction_id": transaction_id})
        self.assertTrue(r)
        self.assertTrue(reply.get("message") == "Found matching challenge",
                        reply)

    def test_40_dynamic_policies(self):
        p = get_dynamic_policy_definitions()
        self.assertTrue("user" in p, p)
        self.assertTrue("admin" in p, p)

        p = get_dynamic_policy_definitions(scope="admin")
        self.assertTrue("enrollTOTP" in p, p)
        self.assertTrue("enrollHOTP" in p, p)
        self.assertTrue("enrollPW" in p, p)

        # The SPASS token can have his own PIN policy
        self.assertTrue("spass_otp_pin_contents" in p, p)
        self.assertTrue("spass_otp_pin_maxlength" in p, p)
        self.assertTrue("spass_otp_pin_minlength" in p, p)

    def test_41_get_tokens_paginate(self):
        # create some tokens
        for serial in ["S1", "S2", "S3", "A8", "B", "X"]:
            init_token({"serial": serial, "type": "hotp",
                        "otpkey": self.otpkey,
                        "realm": self.realm1})
        token_count = 15
        # return pagination
        tokens = get_tokens_paginate(sortby=Token.serial, page=1, psize=5)
        self.assertTrue(len(tokens.get("tokens")) == 5,
                        len(tokens.get("tokens")))
        self.assertEqual(tokens.get("count"), token_count)
        self.assertTrue(tokens.get("next") == 2, tokens.get("next"))
        self.assertTrue(tokens.get("prev") is None, tokens.get("prev"))

        tokens = get_tokens_paginate(sortby=Token.serial, page=2, psize=5)
        self.assertEqual(len(tokens.get("tokens")), 5)
        self.assertEqual(tokens.get("count"), token_count)
        self.assertEqual(tokens.get("next"), 3)
        self.assertEqual(tokens.get("prev"), 1)

        tokens = get_tokens_paginate(sortby=Token.serial, page=3, psize=5)
        self.assertEqual(len(tokens.get("tokens")), 4)
        self.assertEqual(tokens.get("count"), token_count)
        self.assertEqual(tokens.get("next"), None)
        self.assertEqual(tokens.get("prev"), 2)

        # Test filtering and sorting
        tokens = get_tokens_paginate(assigned=True, page=1)
        self.assertTrue(len(tokens.get("tokens")) == 2,
                        len(tokens.get("tokens")))
        self.assertTrue(tokens.get("count") == 2, tokens.get("count"))
        self.assertTrue(tokens.get("next") is None, tokens.get("next"))
        self.assertTrue(tokens.get("prev") is None, tokens.get("prev"))

        tokens = get_tokens_paginate(sortby=Token.serial, page=1,
                                     sortdir="desc")
        self.assertTrue(len(tokens.get("tokens")), token_count-1)
        self.assertEqual(tokens.get("count"), token_count)
        self.assertTrue(tokens.get("next") is None, tokens.get("next"))
        self.assertTrue(tokens.get("prev") is None, tokens.get("prev"))

        # Test to retrieve tokens of user cornelius
        tokens = get_tokens_paginate(user=User("cornelius", "realm1"))
        self.assertTrue(len(tokens.get("tokens")) == 2,
                        len(tokens.get("tokens")))

        # test to retrieve tokens with not strict serial matching
        tokens = get_tokens_paginate(serial="hotp*")
        self.assertTrue(len(tokens.get("tokens")) == 1,
                        len(tokens.get("tokens")))

    def test_42_sort_tokens(self):
        # return pagination
        tokendata = get_tokens_paginate(sortby=Token.serial, page=1, psize=5)
        self.assertTrue(len(tokendata.get("tokens")) == 5,
                        len(tokendata.get("tokens")))

        # sort ascending
        tokendata = get_tokens_paginate(sortby=Token.serial, page=1, psize=100,
                                        sortdir="asc")
        self.assertTrue(len(tokendata.get("tokens")) >= 9,
                        len(tokendata.get("tokens")))

        tokens = tokendata.get("tokens")

        self.assertTrue(tokens[0].get("serial") == "A8",
                        tokens[0])
        # SQLite does not sort like other DBs
        if self.app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite'):
            self.assertEqual('hotptoken', tokens[-1].get("serial"), tokens[-1])
        else:
            self.assertEqual('X', tokens[-1].get("serial"), tokens[-1])

        # Reverse sorting
        tokendata = get_tokens_paginate(sortby=Token.serial, page=1, psize=100,
                                        sortdir="desc")
        tokens = tokendata.get("tokens")

        if self.app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite'):
            self.assertEqual('hotptoken', tokens[0].get("serial"), tokens[0])
        else:
            self.assertEqual('X', tokens[0].get("serial"), tokens[0])
        self.assertTrue(tokens[-1].get("serial") == "A8")

        # sort with string column
        tokendata = get_tokens_paginate(sortby="serial", page=1, psize=100,
                                        sortdir="asc")
        tokens = tokendata.get("tokens")

        if self.app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite'):
            self.assertEqual('hotptoken', tokens[-1].get("serial"), tokens[-1])
        else:
            self.assertEqual('X', tokens[-1].get("serial"), tokens[-1])
        self.assertTrue(tokens[0].get("serial") == "A8")

        tokendata = get_tokens_paginate(sortby="serial", page=1, psize=100,
                                        sortdir="desc")
        tokens = tokendata.get("tokens")

        if self.app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite'):
            self.assertEqual('hotptoken', tokens[0].get("serial"), tokens[0])
        else:
            self.assertEqual('X', tokens[0].get("serial"), tokens[0])
        self.assertTrue(tokens[-1].get("serial") == "A8")

        # try a different sort key
        tokendata = get_tokens_paginate(sortby="id", page=1, psize=100)
        tokens = tokendata.get("tokens")

        self.assertEqual(1, tokens[0].get("id"), tokens[0])
        self.assertGreaterEqual(tokens[-1].get("id"), len(tokens), tokens[-1])

        # unknown sort key results in sorting by serial
        tokendata = get_tokens_paginate(sortby="unknown", page=1, psize=100)
        tokens = tokendata.get("tokens")

        self.assertEqual('A8', tokens[0].get("serial"), tokens[0])

    def test_43_encryptpin(self):
        serial = "ENC01"
        # encrypt pin on init
        init_token({"serial": serial,
                    "genkey": 1,
                    "pin": "Hallo",
                    "encryptpin": True})
        tokenobj = get_tokens(serial=serial)[0]
        self.assertEqual(tokenobj.token.pin_hash[0:2], "@@")

        # set a hashed pin
        set_pin(serial, "test", encrypt_pin=False)
        tokenobj = get_tokens(serial=serial)[0]
        self.assertTrue(tokenobj.token.pin_hash[0:2] != "@@")

        # set an encrypted PIN
        set_pin(serial, "test", encrypt_pin=True)
        tokenobj = get_tokens(serial=serial)[0]
        self.assertEqual(tokenobj.token.pin_hash[0:2], "@@")

        # assign the token with a PIN
        assign_token(serial, User(login="cornelius", realm=self.realm1),
                     pin="WellWell", encrypt_pin=True)
        # check if pinhash starts with "@@" to indicate the encryption
        tokenobj = get_tokens(serial=serial)[0]
        self.assertEqual(tokenobj.token.pin_hash[0:2], "@@")

    def test_44_validity_period(self):
        serial = "VAL01"
        init_token({"serial": serial,
                    "genkey": 1,
                    "pin": "Hallo"})
        tokenobj = get_tokens(serial=serial)[0]

        r = set_validity_period_start(serial, None, "2015-05-22T20:21+0200")
        self.assertEqual(r, 1)
        r = set_validity_period_end(serial, None, "2015-05-28T20:22+0200")
        self.assertEqual(r, 1)

        vp = tokenobj.get_validity_period_start()
        self.assertEqual(vp, "2015-05-22T20:21+0200")
        vp = tokenobj.get_validity_period_end()
        self.assertEqual(vp, "2015-05-28T20:22+0200")

    def test_45_check_realm_pass(self):
        self.setUp_user_realms()
        # create a bunch of tokens in the realm

        # disabled token
        serial = "inactive"
        init_token({"serial": serial,
                    "otpkey": self.otpkey,
                    "pin": serial}, User("cornelius", self.realm1))
        enable_token(serial, False)

        # not assigned token
        serial = "not_assigned"
        init_token({"serial": serial,
                    "otpkey": self.otpkey,
                    "pin": serial}, tokenrealms=[self.realm1])

        # a normal token
        serial = "assigned"
        init_token({"serial": serial,
                    "otpkey": self.otpkey,
                    "pin": serial}, User("cornelius", self.realm1))

        # check if the tokens were created accordingly
        tokens = get_tokens(realm=self.realm1, tokentype="hotp",
                            assigned=False, serial="not_assigned")
        self.assertEqual(len(tokens), 1)

        tokens = get_tokens(realm=self.realm1, tokentype="hotp",
                            active=False, serial="inactive")
        self.assertEqual(len(tokens), 1)

        tokens = get_tokens(realm=self.realm1, tokentype="hotp",
                            active=True, assigned=True, serial="assigned")
        self.assertEqual(len(tokens), 1)

        # an inactive token does not match
        r = check_realm_pass(self.realm1, "inactive" + "287082")
        self.assertEqual(r[0], False)
        # The remaining tokens are checked, but the pin does not match,
        # so we get "wrong otp pin"
        self.assertEqual(r[1].get("message"), "wrong otp pin")

        # an unassigned token does not match
        r = check_realm_pass(self.realm1, "unassigned" + "287082")
        self.assertEqual(r[0], False)
        # The remaining tokens are checked, but the pin does not match,
        # so we get "wrong otp pin"
        self.assertEqual(r[1].get("message"), "wrong otp pin")

        # a token assigned to a user does match
        r = check_realm_pass(self.realm1, "assigned" + "287082")
        # One token in the realm matches the pin and the OTP value
        self.assertEqual(r[0], True)
        # The remaining tokens are checked, but the pin does not match,
        # so we get "wrong otp pin"
        self.assertEqual(r[1].get("message"), "matching 1 tokens")

        # try an unknown realm
        r = check_realm_pass(self.realm2, "assigned" + self.valid_otp_values[2])
        self.assertFalse(r[0])
        self.assertEqual(r[1].get("message"), "There is no active and assigned "
                                              "token in this realm")

        # check for optional parameter exclude/include type
        r = check_realm_pass(self.realm1, 'assigned' + self.valid_otp_values[2],
                             exclude_types='hotp')
        self.assertFalse(r[0])
        self.assertEqual(r[1].get("message"), "There is no active and assigned "
                                              "token in this realm, included types: None, "
                                              "excluded types: hotp")

        r = check_realm_pass(self.realm1, 'assigned' + self.valid_otp_values[2],
                             include_types='totp')
        self.assertFalse(r[0])
        self.assertEqual(r[1].get("message"), "There is no active and assigned "
                                              "token in this realm, included types: totp, "
                                              "excluded types: None")

        r = check_realm_pass(self.realm1, 'assigned' + self.valid_otp_values[2],
                             exclude_types='totp')
        self.assertTrue(r[0])
        self.assertEqual(r[1].get("message"), "matching 1 tokens")

        # check that include_types precedes exclude_types
        r = check_realm_pass(self.realm1, 'assigned' + self.valid_otp_values[3],
                             include_types='hotp', exclude_types='hotp')
        self.assertTrue(r[0])
        self.assertEqual(r[1].get("message"), "matching 1 tokens")

        remove_token(serial='not_assigned')
        remove_token(serial='inactive')
        remove_token(serial='assigned')

    def test_46_init_with_validity_period(self):
        token = init_token({"type": "hotp",
                            "genkey": 1,
                            "validity_period_start": "2014-05-22T22:00+0200",
                            "validity_period_end": "2014-10-23T23:00+0200"})
        self.assertEqual(token.type, "hotp")
        start = token.get_tokeninfo("validity_period_start")
        end = token.get_tokeninfo("validity_period_end")
        self.assertEqual(start, "2014-05-22T22:00+0200")
        self.assertEqual(end, "2014-10-23T23:00+0200")

    def test_47_use_yubikey_and_hotp(self):
        # fix problem https://github.com/privacyidea/privacyidea/issues/279
        user = User("cornelius", self.realm1)
        token = init_token({"type": "hotp",
                            "otpkey": self.otpkey,
                            "pin": "pin47"}, user)
        token = init_token({"type": "yubikey",
                            "otpkey": self.otpkey,
                            "pin": "pin47"}, user)
        r = check_user_pass(user, "pin47888888")
        self.assertEqual(r[0], False)
        self.assertEqual(r[1].get('message'), "wrong otp value")

    def test_48_challenge_request_two_tokens(self):
        # test the challenge request of two tokens. One token is active,
        # the other is disabled
        user = User("cornelius", self.realm1)
        pin = "test48"
        token_a = init_token({"serial": "CR2A",
                              "type": "hotp",
                              "otpkey": self.otpkey,
                              "pin": pin}, user)
        token_b = init_token({"serial": "CR2B",
                              "type": "hotp",
                              "otpkey": self.otpkey,
                              "pin": pin}, user)
        # disable token_b
        enable_token("CR2B", False)
        # Allow HOTP for chalresp
        set_policy("test48", scope=SCOPE.AUTH, action="{0!s}=HOTP".format(
            ACTION.CHALLENGERESPONSE))
        r, r_dict = check_token_list([token_a, token_b], pin, user)
        self.assertFalse(r)
        self.assertTrue("message" in r_dict)
        self.assertTrue("transaction_id" in r_dict)
        transaction_id = r_dict.get("transaction_id")

        # Now we try authenticate:
        r, r_dict = check_token_list([token_a, token_b], self.valid_otp_values[1], user,
                                     options={"transaction_id": transaction_id})
        self.assertTrue(r)

        # New challenge
        r, r_dict = check_token_list([token_a, token_b], pin, user)
        self.assertTrue("transaction_id" in r_dict)
        transaction_id = r_dict.get("transaction_id")

        # Now we run a bunch of failing responses to the challenge
        for i in range(0, 10):
            r, r_dict = check_token_list([token_a, token_b], self.valid_otp_values[1], user,
                                         options={"transaction_id": transaction_id})
            self.assertFalse(r)
        # Now we try the next value, which fails
        r, r_dict = check_token_list([token_a, token_b], self.valid_otp_values[2], user,
                                     options={"transaction_id": transaction_id})
        self.assertFalse(r)
        self.assertEqual(r_dict.get("message"), "Challenge matches, but token is not fit for challenge. Failcounter exceeded")

        remove_token("CR2A")
        remove_token("CR2B")
        delete_policy("test48")

    def test_49_challenge_request_multiple_tokens(self):
        # Test the challenges for multiple active tokens
        user = User("cornelius", self.realm1)
        pin = "test49"
        token_a = init_token({"serial": "CR2A",
                              "type": "hotp",
                              "otpkey": OTPKE2,
                              "pin": pin}, user)
        token_b = init_token({"serial": "CR2B",
                              "type": "hotp",
                              "otpkey": self.otpkey,
                              "pin": pin}, user)
        set_policy("test49", scope=SCOPE.AUTH, action="{0!s}=HOTP".format(
            ACTION.CHALLENGERESPONSE))
        # both tokens will be a valid challenge response token!
        r, r_dict = check_token_list([token_a, token_b], pin, user)
        multi_challenge = r_dict.get("multi_challenge")
        transaction_id = r_dict.get("transaction_id")
        self.assertEqual(multi_challenge[0].get("serial"), "CR2A")
        self.assertEqual(transaction_id,
                         multi_challenge[0].get("transaction_id"))
        self.assertEqual("interactive", multi_challenge[0].get("client_mode"))
        self.assertEqual(transaction_id,
                         multi_challenge[1].get("transaction_id"))
        self.assertEqual(multi_challenge[1].get("serial"), "CR2B")
        self.assertEqual("interactive", multi_challenge[1].get("client_mode"))

        # There are two challenges in the database
        r = Challenge.query.filter(Challenge.transaction_id ==
                                   transaction_id).all()
        self.assertEqual(len(r), 2)

        # Check the second response to the challenge, the second step in
        # challenge response:
        r, r_dict = check_token_list([token_a, token_b], "287082", user,
                                     options={"transaction_id": transaction_id})
        # The response is successfull
        self.assertTrue(r)
        # The matching token was CR2B
        self.assertEqual(r_dict.get("serial"), "CR2B")
        # All challenges of the transaction_id have been deleted on
        # successful authentication
        r = Challenge.query.filter(Challenge.transaction_id ==
                                transaction_id).all()
        self.assertEqual(len(r), 0)

        remove_token("CR2A")
        remove_token("CR2B")
        delete_policy("test49")

    def test_50_otpkeyformat(self):
        otpkey = b"\x01\x02\x03\x04\x05\x06\x07\x08\x0A"
        checksum = hashlib.sha1(otpkey).digest()[:4]
        # base32check(otpkey) = 'FIQVUTQBAIBQIBIGA4EAU==='
        # hex encoding
        tokenobject = init_token({"serial": "NEW001", "type": "hotp",
                                  "otpkey": binascii.hexlify(otpkey),
                                  "otpkeyformat": "hex"},
                                 user=User(login="cornelius",
                                           realm=self.realm1))
        self.assertTrue(tokenobject.token.tokentype == "hotp",
                        tokenobject.token)
        self.assertEqual(tokenobject.token.get_otpkey().getKey(),
                         binascii.hexlify(otpkey))
        remove_token("NEW001")
        # unknown encoding
        self.assertRaisesRegex(ParameterError,
                               "Unknown OTP key format",
                               init_token,
                               {"serial": "NEW001",
                                "type": "hotp",
                                "otpkey": binascii.hexlify(otpkey),
                                "otpkeyformat": "foobar"},
                               user=User(login="cornelius",
                                         realm=self.realm1))

        # successful base32check encoding
        base32check_encoding = b32encode_and_unicode(checksum + otpkey).strip("=")
        tokenobject = init_token({"serial": "NEW002", "type": "hotp",
                                  "otpkey": base32check_encoding,
                                  "otpkeyformat": "base32check"},
                                 user=User(login="cornelius",
                                           realm=self.realm1))
        self.assertTrue(tokenobject.token.tokentype == "hotp",
                        tokenobject.token)
        self.assertEqual(tokenobject.token.get_otpkey().getKey(),
                         binascii.hexlify(otpkey))
        remove_token("NEW002")

        # successful base32check encoding, but lower case
        base32check_encoding = b32encode_and_unicode(checksum + otpkey).strip("=")
        base32check_encoding = base32check_encoding.lower()
        tokenobject = init_token({"serial": "NEW002", "type": "hotp",
                                  "otpkey": base32check_encoding,
                                  "otpkeyformat": "base32check"},
                                 user=User(login="cornelius",
                                           realm=self.realm1))
        self.assertTrue(tokenobject.token.tokentype == "hotp",
                        tokenobject.token)
        self.assertEqual(tokenobject.token.get_otpkey().getKey(),
                         binascii.hexlify(otpkey))
        remove_token("NEW002")

        # base32check encoding with padding
        base32check_encoding = b32encode_and_unicode(checksum + otpkey)
        tokenobject = init_token({"serial": "NEW003", "type": "hotp",
                                  "otpkey": base32check_encoding,
                                  "otpkeyformat": "base32check"},
                                 user=User(login="cornelius",
                                           realm=self.realm1))
        self.assertTrue(tokenobject.token.tokentype == "hotp",
                        tokenobject.token)
        self.assertEqual(tokenobject.token.get_otpkey().getKey(),
                         binascii.hexlify(otpkey))
        remove_token("NEW003")
        # invalid base32check encoding (incorrect checksum due to typo)
        base32check_encoding = b32encode_and_unicode(checksum + otpkey)
        base32check_encoding = "A" + base32check_encoding[1:]
        self.assertRaisesRegex(ParameterError,
                               "Incorrect checksum",
                               init_token,
                               {"serial": "NEW004", "type": "hotp",
                                "otpkey": base32check_encoding,
                                "otpkeyformat": "base32check"},
                               user=User(login="cornelius", realm=self.realm1))

        # invalid base32check encoding (missing four characters => incorrect checksum)
        base32check_encoding = b32encode_and_unicode(checksum + otpkey)
        base32check_encoding = base32check_encoding[:-4]
        self.assertRaisesRegex(ParameterError,
                               "Incorrect checksum",
                               init_token,
                               {"serial": "NEW005", "type": "hotp",
                                "otpkey": base32check_encoding,
                                "otpkeyformat": "base32check"},
                               user=User(login="cornelius", realm=self.realm1))

        # invalid base32check encoding (too many =)
        base32check_encoding = b32encode_and_unicode(checksum + otpkey)
        base32check_encoding = base32check_encoding + "==="
        self.assertRaisesRegex(ParameterError,
                               "Invalid base32",
                               init_token,
                               {"serial": "NEW006", "type": "hotp",
                                "otpkey": base32check_encoding,
                                "otpkeyformat": "base32check"},
                               user=User(login="cornelius", realm=self.realm1))

        # invalid base32check encoding (wrong characters)
        base32check_encoding = b32encode_and_unicode(checksum + otpkey)
        base32check_encoding = "1" + base32check_encoding[1:]
        self.assertRaisesRegex(ParameterError,
                               "Invalid base32",
                               init_token,
                               {"serial": "NEW006", "type": "hotp",
                                "otpkey": base32check_encoding,
                                "otpkeyformat": "base32check"},
                               user=User(login="cornelius", realm=self.realm1))

        # invalid key (too short)
        base32check_encoding = b32encode_and_unicode(b'Yo')
        self.assertRaisesRegex(ParameterError,
                               "Too short",
                               init_token,
                               {"serial": "NEW006", "type": "hotp",
                                "otpkey": base32check_encoding,
                                "otpkeyformat": "base32check"},
                               user=User(login="cornelius", realm=self.realm1))

    def test_51_tokenkind(self):
        # A normal token will be of kind "software"
        tok = init_token({"type": "totp", "otpkey": self.otpkey})
        kind = tok.get_tokeninfo("tokenkind")
        self.assertEqual(kind, TOKENKIND.SOFTWARE)
        tok.delete_token()

        # A token, that is imported, will be of kind "hardware"
        tok = init_token({"type": "totp", "otpkey": self.otpkey},
                         tokenkind=TOKENKIND.HARDWARE)
        kind = tok.get_tokeninfo("tokenkind")
        self.assertEqual(kind, TOKENKIND.HARDWARE)
        tok.delete_token()

        # A yubikey initialized as HOTP is hardware
        tok = init_token({"type": "hotp", "otpkey": self.otpkey,
                          "serial": "UBOM111111"})
        kind = tok.get_tokeninfo("tokenkind")
        self.assertEqual(kind, TOKENKIND.HARDWARE)
        tok.delete_token()

        # A yubikey and yubicloud tokentype is hardware
        tok = init_token({"type": "yubikey", "otpkey": self.otpkey})
        kind = tok.get_tokeninfo("tokenkind")
        self.assertEqual(kind, TOKENKIND.HARDWARE)
        tok.delete_token()

        tok = init_token({"type": "yubico",
                          "yubico.tokenid": "123456789012"})
        kind = tok.get_tokeninfo("tokenkind")
        self.assertEqual(kind, TOKENKIND.HARDWARE)
        tok.delete_token()

        # 4eyes, radius and remote are virtual tokens
        tok = init_token({"type": "radius", "radius.identifier": "1",
                          "radius.user": "hans"})
        kind = tok.get_tokeninfo("tokenkind")
        self.assertEqual(kind, TOKENKIND.VIRTUAL)
        tok.delete_token()

        tok = init_token({"type": "remote", "remote.server": "1",
                          "radius.user": "hans"})
        kind = tok.get_tokeninfo("tokenkind")
        self.assertEqual(kind, TOKENKIND.VIRTUAL)
        tok.delete_token()

        tok = init_token({"type": "4eyes", "4eyes": "realm1",
                          "separator": ","})
        kind = tok.get_tokeninfo("tokenkind")
        self.assertEqual(kind, TOKENKIND.VIRTUAL)
        tok.delete_token()

    def test_52_import_token(self):
        tok = import_token("IMP001",
                           {"type": "totp",
                            "timeShift": "-122",
                            "timeStep": "30",
                            "otpkey": self.otpkey,
                            "counter": "121212"})
        self.assertEqual(tok.get_tokeninfo("timeShift"), "-122")
        self.assertEqual(tok.get_tokeninfo("timeStep"), "30")
        self.assertEqual(tok.get_otp_count(), 121212)
        remove_token("IMP001")

    def test_53_import_token(self):
        # Import token from a file with a user object
        tok = import_token("IMP002",
                           {"type": "totp",
                            "otpkey": self.otpkey,
                            "user": {"username": "cornelius",
                                     "resolver": self.resolvername1,
                                     "realm": self.realm1}})
        self.assertEqual(tok.get_user_id(), "1000")
        self.assertEqual(tok.get_user_displayname(), ('cornelius_realm1', 'Cornelius '))
        remove_token("IMP002")

    def test_54_helper_functions(self):
        user = User("cornelius", self.realm1)
        # unassign all tokens of cornelius, assign S1 and S2
        unassign_token(serial=None, user=user)
        assign_token(serial="S1", user=user)
        assign_token(serial="S2", user=user)
        self.assertEqual(get_one_token(serial="S1", user=None).token.serial, "S1")
        self.assertEqual(get_one_token(serial="hotptoken", user=None).token.serial, "hotptoken")
        self.assertEqual(get_one_token(serial="S1", user=user).token.serial, "S1")
        with self.assertRaises(ResourceNotFoundError):
            get_one_token(serial="doesnotexist", user=None)
        with self.assertRaises(ResourceNotFoundError):
            get_one_token(serial="hotptoken", user=user)
        with self.assertRaises(ResourceNotFoundError):
            get_one_token(serial="doesnotexist", user=user)
        with self.assertRaises(ResourceNotFoundError):
            get_one_token(serial="doesnotexist", user=user)
        # exact match
        with self.assertRaises(ResourceNotFoundError):
            get_one_token(serial="*", user=None)
        # more than 1 token
        with self.assertRaises(ParameterError):
            get_one_token(user=user)
        # get_tokens_from_serial_or_user tests
        shadow = User("shadow", self.realm1)
        self.assertEqual(len(get_tokens_from_serial_or_user(serial=None, user=user)), 2)
        self.assertEqual(len(get_tokens_from_serial_or_user(serial=None, user=shadow)), 0)
        self.assertEqual(len(get_tokens_from_serial_or_user(serial="S1", user=user)), 1)
        self.assertEqual(len(get_tokens_from_serial_or_user(serial="S2", user=user)), 1)
        self.assertEqual(len(get_tokens_from_serial_or_user(serial="hotptoken", user=None)), 1)
        with self.assertRaises(ResourceNotFoundError):
            get_tokens_from_serial_or_user(serial="S*", user=None)
        with self.assertRaises(ResourceNotFoundError):
            get_tokens_from_serial_or_user(serial="doesnotexist", user=None)
        with self.assertRaises(ResourceNotFoundError):
            get_tokens_from_serial_or_user(serial="S1", user=shadow)
        unassign_token(serial=None, user=user)

    def test_55_get_tokens_paginated_generator(self):
        def flatten_tokens(l):
            return [token.token.id for l2 in l for token in l2]

        # serial72 token has invalid type. Check behavior and remove it.
        self.assertEqual(list(get_tokens_paginated_generator(serial_wildcard="serial*")), [[]])
        # We need to remove the token directly in the DB since `remove_token()` would check the type
        db.session.query(Token).filter_by(serial="serial72").delete()
        db.session.commit()

        all_matching_tokens = get_tokens(serial_wildcard="S*")
        lists1 = list(get_tokens_paginated_generator(serial_wildcard="S*"))
        self.assertEqual(len(lists1), 1)
        self.assertEqual(len(lists1[0]), 6)
        lists2 = list(get_tokens_paginated_generator(serial_wildcard="S*", psize=2))
        self.assertEqual(len(lists2), 3)
        self.assertEqual(len(lists2[0]), 2)
        self.assertEqual(len(lists2[1]), 2)
        self.assertEqual(len(lists2[2]), 2)
        lists3 = list(get_tokens_paginated_generator(serial_wildcard="S*", psize=3))
        self.assertEqual(len(lists3), 2)
        self.assertEqual(len(lists3[0]), 3)
        self.assertEqual(len(lists3[1]), 3)
        lists4 = list(get_tokens_paginated_generator(serial_wildcard="S*", psize=4))
        self.assertEqual(len(lists4), 2)
        self.assertEqual(len(lists4[0]), 4)
        self.assertEqual(len(lists4[1]), 2)
        lists5 = list(get_tokens_paginated_generator(serial_wildcard="S*", psize=6))
        self.assertEqual(len(lists5), 1)
        self.assertEqual(len(lists5[0]), 6)
        self.assertEqual(set([t.token.id for t in all_matching_tokens]), set(flatten_tokens(lists1)))
        self.assertEqual(flatten_tokens(lists1), flatten_tokens(lists2))
        self.assertEqual(flatten_tokens(lists2), flatten_tokens(lists3))
        self.assertEqual(flatten_tokens(lists3), flatten_tokens(lists4))
        self.assertEqual(flatten_tokens(lists4), flatten_tokens(lists5))

        lists6 = list(get_tokens_paginated_generator(serial_wildcard="*DOESNOTEXIST*"))
        self.assertEqual(lists6, [])

    def test_56_get_tokens_paginated_generator_removal(self):
        all_serials = set(t.token.serial for t in get_tokens(serial_wildcard="S*"))
        # Test proper behavior if a matching token is deleted while paginating
        gen = get_tokens_paginated_generator(serial_wildcard="S*", psize=3)
        list1 = next(gen)
        remove_token(list1[0].token.serial)
        list2 = next(gen)
        # Check that we did not miss any tokens
        self.assertEqual(set(t.token.serial for t in list1 + list2), all_serials)

    def test_57a_check_invalid_serial(self):
        # This is an invalid serial, which will trigger an exception
        self.assertRaises(Exception, reset_token, "hans wurst")

        self.assertRaises(Exception, init_token,
                          {"serial": "invalid/chars",
                           "genkey": 1})

    def test_57b_registration_token_no_auth_counter(self):
        # Test, that a registration token is deleted even if no_auth_counter is used.
        from privacyidea.lib.config import set_privacyidea_config, delete_privacyidea_config
        set_privacyidea_config("no_auth_counter", 1)
        tok = init_token({"type": "registration"})
        serial = tok.token.serial
        detail = tok.get_init_detail()
        reg_password = detail.get("registrationcode")
        r, rdetail = check_token_list([tok], reg_password)
        self.assertTrue(r)
        self.assertEqual(rdetail["message"], "matching 1 tokens")
        delete_privacyidea_config("no_auth_counter")
        # Check that the token is deleted
        toks = get_tokens(serial=serial)
        self.assertEqual(len(toks), 0)

    def test_58_check_old_pin(self):
        serial = "pins"
        tokenobject = init_token({"serial": serial,
                                  "otpkey": "1234567890123456"})
        # now set the old pin
        from privacyidea.lib.crypto import hash
        tokenobject.token.pin_hash = hash("1234", b"1234567890")
        tokenobject.token.pin_seed = hexlify_and_unicode(b"1234567890")
        tokenobject.token.save()
        r = tokenobject.token.check_pin("1234")
        self.assertTrue(r)
        remove_token(serial)

    def test_59_weigh_token_types(self):

        class dummy_token(object):
            def __init__(self, type):
                self.type = type
        self.assertEqual(1000, weigh_token_type(dummy_token("push")))
        self.assertTrue(weigh_token_type(dummy_token("push")) > weigh_token_type(dummy_token("hotp")))
        self.assertTrue(weigh_token_type(dummy_token("push")) > weigh_token_type(dummy_token("HOTP")))
        self.assertTrue(weigh_token_type(dummy_token("PUSH")) > weigh_token_type(dummy_token("hotp")))


class TokenOutOfBandTestCase(MyTestCase):

    def test_00_create_realms(self):
        self.setUp_user_realms()

    def test_01_failcounter_no_increase(self):
        # The fail counter for tiqr tokens will not increase, since this
        # is a tokenmode outofband.
        user = User(login="cornelius", realm=self.realm1)
        pin1 = "pin1"
        token1 = init_token({"serial": pin1, "pin": pin1,
                             "type": "tiqr", "genkey": 1}, user=user)

        r = token1.get_failcount()
        self.assertEqual(r, 0)

        r, r_dict = check_token_list([token1], pin1, user=user, options={})
        self.assertFalse(r, r_dict)
        transaction_id = r_dict.get("transaction_id")

        # Now we check the status of the challenge several times and verify that the
        # failcounter is not increased:
        for i in range(1, 10):
            r, r_dict = check_token_list([token1], "", user=user, options={"transaction_id": transaction_id})
            self.assertFalse(r, r_dict)
            self.assertEqual(r_dict.get("type"), "tiqr", r_dict)

        r = token1.get_failcount()
        self.assertEqual(r, 0)

        # Now set the challenge to be answered and recheck:
        Challenge.query.filter(Challenge.transaction_id == transaction_id).update({"otp_valid": True})
        r, r_dict = check_token_list([token1], "", user=user, options={"transaction_id": transaction_id})
        self.assertTrue(r, r_dict)
        self.assertEqual(r_dict.get("message"), "Found matching challenge", r_dict)

        remove_token(pin1)


class TokenFailCounterTestCase(MyTestCase):
    """
    Test the lib.token on an interface level
    """

    def test_00_create_realms(self):
        self.setUp_user_realms()

    def test_01_failcounter_max_hotp(self):
        # Check if we can not authenticate with a token that has the maximum
        # failcounter
        user = User(login="cornelius", realm=self.realm1)
        token = init_token({"serial": "test47", "pin": "test47",
                            "type": "hotp", "otpkey": OTPKEY},
                           user=user)

        """                        Truncated
           Count    Hexadecimal    Decimal        HOTP
           0        4c93cf18       1284755224     755224
           1        41397eea       1094287082     287082
           2         82fef30        137359152     359152
           3        66ef7655       1726969429     969429
           4        61c5938a       1640338314     338314
           5        33c083d4        868254676     254676
           6        7256c032       1918287922     287922
           7         4e5b397         82162583     162583
           8        2823443f        673399871     399871
           9        2679dc69        645520489     520489
           10                                     403154
           11                                     481090
           12                                     868912
           13                                     736127
        """
        res, reply = check_user_pass(user, "test47287082")
        self.assertTrue(res)
        # Set the failcounter to maximum failcount
        token.set_failcount(10)
        # Authentication must fail, since the failcounter is reached
        res, reply = check_user_pass(user, "test47359152")
        self.assertFalse(res)
        self.assertEqual(reply.get("message"), "matching 1 tokens, "
                                               "Failcounter exceeded")

        remove_token("test47")

    def test_02_failcounter_max_totp(self):
        # Check if we can not authenticate with a token that has the maximum
        # failcounter
        user = User(login="cornelius", realm=self.realm1)
        pin = "testTOTP"
        token = init_token({"serial": pin, "pin": pin,
                            "type": "totp", "otpkey": OTPKEY},
                           user=user)
        """
        47251644    942826
        47251645    063321
        47251646    306773
        47251647    722053
        47251648    032819
        47251649    705493
        47251650    589836
        """
        res, reply = check_user_pass(user, pin + "942826",
                                     options={"initTime": 47251644 * 30})
        self.assertTrue(res)
        # Set the failcounter to maximum failcount
        token.set_failcount(10)
        # Authentication must fail, since the failcounter is reached
        res, reply = check_user_pass(user, pin + "032819",
                                     options={"initTime": 47251648 * 30})
        self.assertFalse(res)
        self.assertEqual(reply.get("message"), "matching 1 tokens, "
                                               "Failcounter exceeded")

        remove_token(pin)

    def test_03_inc_failcounter_of_all_tokens(self):
        # If a user has more than one token and authenticates with wrong OTP
        # PIN, the failcounter on all tokens should be increased
        user = User(login="cornelius", realm=self.realm1)
        pin1 = "pin1"
        pin2 = "pin2"
        token1 = init_token({"serial": pin1, "pin": pin1,
                             "type": "hotp", "genkey": 1}, user=user)
        token2 = init_token({"serial": pin2, "pin": pin2,
                             "type": "hotp", "genkey": 1}, user=user)

        # Authenticate with pin1 will increase first failcounter
        res, reply = check_user_pass(user, pin1 + "000000")
        self.assertEqual(res, False)
        self.assertEqual(reply.get("message"), "wrong otp value")

        self.assertEqual(token1.token.failcount, 1)
        self.assertEqual(token2.token.failcount, 0)

        # Authenticate with a wrong PIN will increase all failcounters
        res, reply = check_user_pass(user, "XXX" + "000000")
        self.assertEqual(res, False)
        self.assertEqual(reply.get("message"), "wrong otp pin")

        self.assertEqual(token1.token.failcount, 2)
        self.assertEqual(token2.token.failcount, 1)
        remove_token(pin1)
        remove_token(pin2)

    def test_04_reset_all_failcounters(self):
        from privacyidea.lib.policy import (set_policy, PolicyClass, SCOPE,
            ACTION)
        from flask import g

        set_policy("reset_all", scope=SCOPE.AUTH,
                   action=ACTION.RESETALLTOKENS)

        user = User(login="cornelius", realm=self.realm1)
        pin1 = "pin1"
        pin2 = "pin2"
        token1 = init_token({"serial": pin1, "pin": pin1,
                             "type": "spass"}, user=user)
        token2 = init_token({"serial": pin2, "pin": pin2,
                             "type": "spass"}, user=user)

        token1.inc_failcount()
        token2.inc_failcount()
        token2.inc_failcount()
        self.assertEqual(token1.token.failcount, 1)
        self.assertEqual(token2.token.failcount, 2)

        g.policy_object = PolicyClass()
        g.audit_object = FakeAudit()
        g.client_ip = None
        g.serial = None
        options = {"g": g}

        check_token_list([token1, token2], pin1, user=user,
                         options=options, allow_reset_all_tokens=True)

        self.assertEqual(token1.token.failcount, 0)
        self.assertEqual(token2.token.failcount, 0)

        # check with tokens without users
        unassign_token(pin1)
        unassign_token(pin1)
        # After unassigning we need to set the PIN again
        token1.set_pin(pin1)
        token2.set_pin(pin2)
        token1.inc_failcount()
        token2.inc_failcount()
        token2.inc_failcount()
        self.assertEqual(token1.token.failcount, 1)
        self.assertEqual(token2.token.failcount, 2)

        check_token_list([token1, token2], pin1, options=options,
                         allow_reset_all_tokens=True)

        self.assertEqual(token1.token.failcount, 0)
        self.assertEqual(token2.token.failcount, 0)

        # Clean up
        remove_token(pin1)
        remove_token(pin2)

    def test_05_reset_failcounter(self):
        tok = init_token({"type": "hotp",
                          "serial": "test05",
                          "otpkey": self.otpkey})
        # Set failcounter clear timeout to 1 minute
        set_privacyidea_config(FAILCOUNTER_CLEAR_TIMEOUT, 1)
        tok.token.count = 10
        tok.set_pin("hotppin")
        tok.set_failcount(10)
        exceeded_timestamp = datetime.datetime.now(tzlocal()) - datetime.timedelta(minutes=1)
        tok.add_tokeninfo(FAILCOUNTER_EXCEEDED, exceeded_timestamp.strftime(DATE_FORMAT))

        # OTP value #11
        res, reply = check_token_list([tok], "hotppin481090")
        self.assertTrue(res)
        set_privacyidea_config(FAILCOUNTER_CLEAR_TIMEOUT, 0)
        remove_token("test05")

    def test_06_reset_failcounter_out_of_sync(self):
        # Reset fail counter of a token that is out of sync
        # The fail counter will reset, even if the token is out of sync, since the
        # autoresync is handled in the tokenclass.authenticate.
        tok = init_token({"type": "hotp",
                          "serial": "test06",
                          "otpkey": self.otpkey})

        set_privacyidea_config("AutoResyncTimeout", "300")
        set_privacyidea_config("AutoResync", 1)

        tok.set_pin("hotppin")
        tok.set_count_window(2)

        res, reply = check_token_list([tok], "hotppin{0!s}".format(self.valid_otp_values[0]))
        self.assertTrue(res)

        # Now we set the failoucnter and the exceeded time.
        tok.set_failcount(10)
        exceeded_timestamp = datetime.datetime.now(tzlocal()) - datetime.timedelta(minutes=1)
        tok.add_tokeninfo(FAILCOUNTER_EXCEEDED, exceeded_timestamp.strftime(DATE_FORMAT))
        set_privacyidea_config(FAILCOUNTER_CLEAR_TIMEOUT, 1)

        # authentication with otp value #3 will fail
        res, reply = check_token_list([tok], "hotppin{0!s}".format(self.valid_otp_values[3]))
        self.assertFalse(res)

        # authentication with otp value #4 will resync and succeed
        res, reply = check_token_list([tok], "hotppin{0!s}".format(self.valid_otp_values[4]))
        self.assertTrue(res)
        self.assertEqual(tok.get_failcount(), 0)

        set_privacyidea_config(FAILCOUNTER_CLEAR_TIMEOUT, 0)
        delete_privacyidea_config("AutoResyncTimeout")
        delete_privacyidea_config("AutoResync")
        remove_token("test06")

    def test_07_reset_failcounter_on_pin_only(self):
        tok = init_token({"type": "hotp",
                          "serial": "test07",
                          "otpkey": self.otpkey})
        # Set failcounter clear timeout to 1 minute
        set_privacyidea_config(FAILCOUNTER_CLEAR_TIMEOUT, 1)
        tok.token.count = 10
        tok.set_pin("hotppin")
        tok.set_failcount(10)
        exceeded_timestamp = datetime.datetime.now(tzlocal()) - datetime.timedelta(minutes=1)
        tok.add_tokeninfo(FAILCOUNTER_EXCEEDED, exceeded_timestamp.strftime(DATE_FORMAT))

        # by default, correct PIN + wrong OTP value does not reset the failcounter
        res, reply = check_token_list([tok], "hotppin123456")
        self.assertEqual(tok.get_failcount(), 10)
        self.assertFalse(res)
        # with the corresponding config option ...
        set_privacyidea_config(SYSCONF.RESET_FAILCOUNTER_ON_PIN_ONLY, "True")
        # ... correct PIN + wrong OTP resets the failcounter ...
        res, reply = check_token_list([tok], "hotppin123456")
        self.assertEqual(tok.get_failcount(), 0)
        # ... but authentication still fails
        self.assertFalse(res)

        set_privacyidea_config(FAILCOUNTER_CLEAR_TIMEOUT, 0)
        delete_privacyidea_config(SYSCONF.RESET_FAILCOUNTER_ON_PIN_ONLY)
        remove_token("test07")


class PINChangeTestCase(MyTestCase):
    """
    Test the check_token_list from lib.token on an interface level
    """

    def test_00_create_realms(self):
        self.setUp_user_realms()
        # Set a policy to change the pin every 10d
        set_policy("every10d", scope=SCOPE.ENROLL, action="{0!s}=10d".format(ACTION.CHANGE_PIN_EVERY))
        # set policy for chalresp
        set_policy("chalresp", scope=SCOPE.AUTH, action="{0!s}=hotp".format(ACTION.CHALLENGERESPONSE))
        # Change PIN via validate
        set_policy("viaValidate", scope=SCOPE.AUTH, action=ACTION.CHANGE_PIN_VIA_VALIDATE)

    def test_01_successfully_change_pin(self):
        """
        Authentication per challenge response with an HOTP token and then
        do a successful PIN reset
        """
        g = FakeFlaskG()
        g.client_ip = "10.0.0.1"
        g.policy_object = PolicyClass()
        g.audit_object = FakeAudit()
        user_obj = User("cornelius", realm=self.realm1)
        # remove all tokens of cornelius
        remove_token(user=user_obj)
        tok = init_token({"type": "hotp",
                          "otpkey": self.otpkey, "pin": "test",
                          "serial": "PINCHANGE"}, tokenrealms=["r1"], user=user_obj)
        tok2 = init_token({"type": "hotp",
                          "otpkey": self.otpkey, "pin": "fail",
                          "serial": "NOTNEEDED"}, tokenrealms=["r1"], user=user_obj)
        # Set, that the token needs to change the pin
        tok.set_next_pin_change("-1d")
        # Check it
        self.assertTrue(tok.is_pin_change())

        # Trigger the first auth challenge by sending the PIN
        r, reply_dict = check_token_list([tok, tok2], "test", user=user_obj, options={"g": g})
        self.assertFalse(r)
        self.assertEqual('please enter otp: ', reply_dict.get("message"))
        transaction_id = reply_dict.get("transaction_id")

        # Now send the correct OTP value
        r, reply_dict = check_token_list([tok, tok2], self.valid_otp_values[1], user=user_obj,
                                         options={"transaction_id": transaction_id,
                                                  "g": g})
        self.assertFalse(r)
        self.assertEqual("Please enter a new PIN", reply_dict.get("message"))
        transaction_id = reply_dict.get("transaction_id")
        self.assertEqual("interactive", reply_dict.get('multi_challenge')[0].get('client_mode'))

        # Now send a new PIN
        newpin = "test2"
        r, reply_dict = check_token_list([tok, tok2], newpin, user=user_obj,
                                         options={"transaction_id": transaction_id,
                                                  "g": g})
        self.assertFalse(r)
        self.assertEqual("Please enter the new PIN again", reply_dict.get("message"))
        transaction_id = reply_dict.get("transaction_id")

        # Now send the new PIN a 2nd time
        r, reply_dict = check_token_list([tok, tok2], newpin, user=user_obj,
                                         options={"transaction_id": transaction_id,
                                                  "g": g})
        self.assertTrue(r)
        self.assertEqual("PIN successfully set.", reply_dict.get("message"))

        self.assertFalse(tok.is_pin_change())

        # Run an authentication with the new PIN
        r, reply_dict = check_token_list([tok, tok2], "{0!s}{1!s}".format(newpin, self.valid_otp_values[2]),
                                         user=user_obj, options={"g": g})
        self.assertTrue(r)
        self.assertFalse(reply_dict.get("pin_change"))
        self.assertTrue("next_pin_change" in reply_dict)

    def test_02_failed_change_pin(self):
        """
        Authentication with an HOTP token and then fail to
        change pin, since we present two different PINs.
        """
        g = FakeFlaskG()
        g.client_ip = "10.0.0.1"
        g.policy_object = PolicyClass()
        g.audit_object = FakeAudit()
        user_obj = User("cornelius", realm=self.realm1)
        # remove all tokens of cornelius
        remove_token(user=user_obj)
        tok = init_token({"type": "hotp",
                          "otpkey": self.otpkey, "pin": "test",
                          "serial": "PINCHANGE"}, tokenrealms=["r1"], user=user_obj)
        tok2 = init_token({"type": "hotp",
                          "otpkey": self.otpkey, "pin": "fail",
                          "serial": "NOTNEEDED"}, tokenrealms=["r1"], user=user_obj)
        # Set, that the token needs to change the pin
        tok.set_next_pin_change("-1d")
        # Check it
        self.assertTrue(tok.is_pin_change())

        # successfully authenticate, but thus trigger a PIN change
        r, reply_dict = check_token_list([tok, tok2], "test{0!s}".format(self.valid_otp_values[1]),
                                         user=user_obj, options={"g": g})
        self.assertFalse(r)
        self.assertEqual("Please enter a new PIN", reply_dict.get("message"))
        transaction_id = reply_dict.get("transaction_id")

        # Now send a new PIN
        newpin = "test2"
        r, reply_dict = check_token_list([tok, tok2], newpin, user=user_obj,
                                         options={"transaction_id": transaction_id,
                                                  "g": g})
        self.assertFalse(r)
        self.assertEqual("Please enter the new PIN again", reply_dict.get("message"))
        transaction_id = reply_dict.get("transaction_id")

        # Now send the new PIN a 2nd time
        r, reply_dict = check_token_list([tok, tok2], "falsePIN", user=user_obj,
                                         options={"transaction_id": transaction_id,
                                                  "g": g})
        self.assertFalse(r)
        self.assertEqual("PINs do not match", reply_dict.get("message"))

        # The PIN still needs to be changed!
        self.assertTrue(tok.is_pin_change())

    def test_03_failed_change_pin(self):
        """
        Authentication with an HOTP token and then fail to
        change pin, since we do not comply to the PIN policies :-)
        """
        g = FakeFlaskG()
        g.client_ip = "10.0.0.1"
        g.policy_object = PolicyClass()
        g.audit_object = FakeAudit()
        user_obj = User("cornelius", realm=self.realm1)
        # remove all tokens of cornelius
        remove_token(user=user_obj)
        tok = init_token({"type": "hotp",
                          "otpkey": self.otpkey, "pin": "test",
                          "serial": "PINCHANGE"}, tokenrealms=["r1"], user=user_obj)
        tok2 = init_token({"type": "hotp",
                          "otpkey": self.otpkey, "pin": "fail",
                          "serial": "NOTNEEDED"}, tokenrealms=["r1"], user=user_obj)
        # Set, that the token needs to change the pin
        tok.set_next_pin_change("-1d")
        # Check it
        self.assertTrue(tok.is_pin_change())
        # Require minimum length of 5
        set_policy("minpin", scope=SCOPE.USER, action="{0!s}=5".format(ACTION.OTPPINMINLEN))

        # successfully authenticate, but thus trigger a PIN change
        r, reply_dict = check_token_list([tok, tok2], "test{0!s}".format(self.valid_otp_values[1]),
                                         user=user_obj, options={"g": g})
        self.assertFalse(r)
        self.assertEqual("Please enter a new PIN", reply_dict.get("message"))
        transaction_id = reply_dict.get("transaction_id")

        # Now send a new PIN, which has only length 4 :-/
        newpin = "test"
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', category=DeprecationWarning)
            self.assertRaisesRegex(
                PolicyError, "The minimum OTP PIN length is 5", check_token_list,
                [tok, tok2], newpin, user=user_obj,
                options={"transaction_id": transaction_id,
                         "g": g})

        delete_policy("minpin")


class TokenGroupTestCase(MyTestCase):

    def test_01_add_tokengroups(self):
        # Create tokens
        serials = ["s1", "s2"]
        for s in serials:
            tok = init_token({"serial": s, "type": "spass"})

        # create tokengroups
        groups = [("g1", "Test A"), ("g2", "test B")]
        for g in groups:
            set_tokengroup(g[0], g[1])

        assign_tokengroup("s1", "g1")
        assign_tokengroup("s1", "g2")
        assign_tokengroup("s2", "g2")

        # Check the tokengroups of the first token
        tok1 = get_one_token(serial="s1")
        self.assertEqual(tok1.token.tokengroup_list[0].tokengroup.name, "g1")
        self.assertEqual(tok1.token.tokengroup_list[1].tokengroup.name, "g2")

        # check the tokengroups of the 2nd token
        tok2 = get_one_token(serial="s2")
        self.assertEqual(tok2.token.tokengroup_list[0].tokengroup.name, "g2")

        # Test a missing group information
        self.assertRaises(ResourceNotFoundError, assign_tokengroup, "s1")

        # list tokengroup assignments
        grouplist = list_tokengroups()
        self.assertEqual(len(grouplist), 3)
        # one token in group1
        grouplist = list_tokengroups("g1")
        self.assertEqual(len(grouplist), 1)
        self.assertEqual(grouplist[0].token.serial, "s1")
        # two tokens in group2
        grouplist = list_tokengroups("g2")
        self.assertEqual(len(grouplist), 2)

        # unassign tokengroups
        r = tok1.del_tokengroup("g1")
        # only the 2nd group remains
        self.assertEqual(tok1.token.tokengroup_list[0].tokengroup.name, "g2")
        # remove it
        unassign_tokengroup("s2", "g2")
        tok2 = get_one_token(serial="s2")
        self.assertEqual(len(tok2.token.tokengroup_list), 0)

        # check that deleting a tokengroup with tokens still assigned results in an error
        self.assertRaises(privacyIDEAError, delete_tokengroup, name='g2')

        # cleanup
        for s in serials:
            remove_token(s)
        delete_tokengroup('g1')
        delete_tokengroup('g2')


class ExportAndReencryptTestCase(MyTestCase):

    def test_00_create_tokens(self):

        tokens = [
            ("ser1", "hotp", self.otpkey),
            ("ser2", "totp", self.otpkey),
            ("ser3", "totp", self.otpkey)
        ]

        for t in tokens:
            init_token({"type": t[1],
                        "serial": t[0],
                        "otpkey": t[2],
                        "timeStep": 60})

        # export tokens
        token_dicts = []
        token_objects = get_tokens()
        for tok in token_objects:
            d = tok._to_dict()
            self.assertIn(d.get("type"), ["hotp", "totp"])
            self.assertEqual(self.otpkey, d.get("otpkey"))
            # Change the OTPKey
            d["otpkey"] = CHANGED_KEY
            # Change the timestep
            d["timeStep"] = 30
            token_dicts.append(d)

        # Update the otpkey
        for t in token_dicts:
            token_obj = get_tokens(serial=t.get("serial"))[0]
            # The .update() would re-save the otpkey with the new HSM.
            token_obj.update(t)

        # check for the new otpkey
        token_objects = get_tokens()
        for tok in token_objects:
            d = tok._to_dict()
            # Check that "reencryption" worked
            self.assertEqual(CHANGED_KEY, d.get("otpkey"))
            # Also check, that the tokeninfo for TOTP was updated
            if d.get("type") == "totp":
                self.assertEqual("30", d.get("timeStep"), d)
