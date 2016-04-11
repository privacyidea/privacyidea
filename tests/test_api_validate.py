from urllib import urlencode
import json
from .base import MyTestCase
from privacyidea.lib.user import (User)
from privacyidea.lib.tokens.totptoken import HotpTokenClass
from privacyidea.models import (Token)
from privacyidea.lib.config import (set_privacyidea_config, get_token_types,
                                    get_inc_fail_count_on_false_pin,
                                    delete_privacyidea_config)
from privacyidea.lib.token import (get_tokens, init_token, remove_token,
                                   reset_token, enable_token, revoke_token)
from privacyidea.lib.policy import SCOPE, ACTION, set_policy, delete_policy
from privacyidea.lib.error import TokenAdminError

import smtpmock


PWFILE = "tests/testdata/passwords"


class ValidateAPITestCase(MyTestCase):
    """
    test the api.validate endpoints
    """

    def test_00_create_realms(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()

        # create a  token and assign it to the user
        db_token = Token(self.serials[0], tokentype="hotp")
        db_token.update_otpkey(self.otpkey)
        db_token.save()
        token = HotpTokenClass(db_token)
        self.assertTrue(token.token.serial == self.serials[0], token)
        token.set_user(User("cornelius", self.realm1))
        token.set_pin("pin")
        self.assertTrue(token.token.user_id == "1000", token.token.user_id)

    def test_02_validate_check(self):
        # is the token still assigned?
        tokenbject_list = get_tokens(serial=self.serials[0])
        tokenobject = tokenbject_list[0]
        self.assertTrue(tokenobject.token.user_id == "1000",
                        tokenobject.token.user_id)

        """                  Truncated
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
        """
        # test for missing parameter user
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"pass": "pin287082"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

        # test for missing parameter serial
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"pass": "pin287082"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

        # test for missing parameter "pass"
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "123456"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

    def test_03_check_user(self):
        # get the original counter
        tokenobject_list = get_tokens(serial=self.serials[0])
        hotp_tokenobject = tokenobject_list[0]
        count_1 = hotp_tokenobject.token.count

        # test successful authentication
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin287082"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is True, result)

        # Check that the counter is increased!
        tokenobject_list = get_tokens(serial=self.serials[0])
        hotp_tokenobject = tokenobject_list[0]
        count_2 = hotp_tokenobject.token.count
        self.assertTrue(count_2 > count_1, (hotp_tokenobject.token.serial,
                                            hotp_tokenobject.token.count,
                                            count_1,
                                            count_2))

        # test authentication fails with the same OTP
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin287082"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is False, result)

    def test_03a_check_user_get(self):
        # Reset the counter!
        count_1 = 0
        tokenobject_list = get_tokens(serial=self.serials[0])
        hotp_tokenobject = tokenobject_list[0]
        hotp_tokenobject.token.count = count_1
        hotp_tokenobject.token.save()

        # test successful authentication
        with self.app.test_request_context('/validate/check',
                                           method='GET',
                                           query_string=urlencode(
                                                    {"user": "cornelius",
                                                     "pass": "pin287082"})):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is True, result)

        # Check that the counter is increased!
        tokenobject_list = get_tokens(serial=self.serials[0])
        hotp_tokenobject = tokenobject_list[0]
        count_2 = hotp_tokenobject.token.count
        self.assertTrue(count_2 > count_1, (hotp_tokenobject.token.serial,
                                            hotp_tokenobject.token.count,
                                            count_1,
                                            count_2))

        # test authentication fails with the same OTP
        with self.app.test_request_context('/validate/check',
                                           method='GET',
                                           query_string=urlencode(
                                                    {"user": "cornelius",
                                                     "pass": "pin287082"})):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is False, result)

    def test_04_check_serial(self):
        # test authentication successful with serial
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": self.serials[0],
                                                 "pass": "pin969429"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is True, result)

        # test authentication fails with serial with same OTP
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": self.serials[0],
                                                 "pass": "pin969429"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            details = json.loads(res.data).get("detail")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is False, result)
            self.assertEqual(details.get("message"), "wrong otp value. "
                                                     "previous otp used again")

    def test_05_check_serial_with_no_user(self):
        # Check a token per serial when the token has no user assigned.
        init_token({"serial": "nouser",
                    "otpkey": self.otpkey,
                    "pin": "pin"})
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "nouser",
                                                 "pass": "pin359152"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            details = json.loads(res.data).get("detail")
            self.assertEqual(result.get("status"), True)
            self.assertEqual(result.get("value"), True)

    def test_05_check_serial_with_no_user(self):
        # Check a token per serial when the token has no user assigned.
        init_token({"serial": "nouser",
                    "otpkey": self.otpkey,
                    "pin": "pin"})
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "nouser",
                                                 "pass": "pin359152"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            details = json.loads(res.data).get("detail")
            self.assertEqual(result.get("status"), True)
            self.assertEqual(result.get("value"), True)

    def test_06_fail_counter(self):
        # test if a user has several tokens that the fail counter is increased
        # reset the failcounter
        reset_token(serial="SE1")
        init_token({"serial": "s2",
                    "genkey": 1,
                    "pin": "test"}, user=User("cornelius", self.realm1))
        init_token({"serial": "s3",
                    "genkey": 1,
                    "pin": "test"}, user=User("cornelius", self.realm1))
        # Now the user cornelius has 3 tokens.
        # SE1 with pin "pin"
        # token s2 with pin "test" and
        # token s3 with pin "test".

        self.assertTrue(get_inc_fail_count_on_false_pin())
        # We give an OTP PIN that does not match any token.
        # The failcounter of all tokens will be increased
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "XXXX123456"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertFalse(result.get("value"))

        tok = get_tokens(serial="SE1")[0]
        self.assertEqual(tok.token.failcount, 1)
        tok = get_tokens(serial="s2")[0]
        self.assertEqual(tok.token.failcount, 1)
        tok = get_tokens(serial="s3")[0]
        self.assertEqual(tok.token.failcount, 1)

        # Now we give the matching OTP PIN of one token.
        # Only one failcounter will be increased
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin123456"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertEqual(detail.get("serial"), "SE1")
            self.assertEqual(detail.get("message"), "wrong otp value")

        # Only the failcounter of SE1 (the PIN matching token) is increased!
        tok = get_tokens(serial="SE1")[0]
        self.assertEqual(tok.token.failcount, 2)
        tok = get_tokens(serial="s2")[0]
        self.assertEqual(tok.token.failcount, 1)
        tok = get_tokens(serial="s3")[0]
        self.assertEqual(tok.token.failcount, 1)

        set_privacyidea_config("IncFailCountOnFalsePin", False)
        self.assertFalse(get_inc_fail_count_on_false_pin())
        reset_token(serial="SE1")
        reset_token(serial="s2")
        reset_token(serial="s3")
        # If we try to authenticate with an OTP PIN that does not match any
        # token NO failcounter is increased!
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "XXXX123456"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertFalse(result.get("value"))

        tok = get_tokens(serial="SE1")[0]
        self.assertEqual(tok.token.failcount, 0)
        tok = get_tokens(serial="s2")[0]
        self.assertEqual(tok.token.failcount, 0)
        tok = get_tokens(serial="s3")[0]
        self.assertEqual(tok.token.failcount, 0)

        # Now we give the matching OTP PIN of one token.
        # Only one failcounter will be increased
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin123456"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertEqual(detail.get("serial"), "SE1")
            self.assertEqual(detail.get("message"), "wrong otp value")

        # Only the failcounter of SE1 (the PIN matching token) is increased!
        tok = get_tokens(serial="SE1")[0]
        self.assertEqual(tok.token.failcount, 1)
        tok = get_tokens(serial="s2")[0]
        self.assertEqual(tok.token.failcount, 0)
        tok = get_tokens(serial="s3")[0]
        self.assertEqual(tok.token.failcount, 0)

    def test_07_authentication_counter_exceeded(self):
        token_obj = init_token({"serial": "pass1", "pin": "123456",
                                "type": "spass"})
        token_obj.set_count_auth_max(5)

        for i in range(1, 5):
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"serial": "pass1",
                                                     "pass": "123456"}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = json.loads(res.data).get("result")
                self.assertEqual(result.get("value"), True)

        # The 6th authentication will fail
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "pass1",
                                                 "pass": "123456"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertEqual(result.get("value"), False)
            self.assertTrue("Authentication counter exceeded"
                            in detail.get("message"))

    def test_08_failcounter_counter_exceeded(self):
        token_obj = init_token({"serial": "pass2", "pin": "123456",
                                "type": "spass"})
        token_obj.set_maxfail(5)
        token_obj.set_failcount(5)
        # a valid authentication will fail
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": "pass2",
                                                 "pass": "123456"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertEqual(result.get("value"), False)
            self.assertEqual(detail.get("message"), "matching 1 tokens, "
                                                    "Failcounter exceeded")

    def test_10_saml_check(self):
        # test successful authentication
        set_privacyidea_config("ReturnSamlAttributes", "0")
        with self.app.test_request_context('/validate/samlcheck',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin338314"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            value = result.get("value")
            attributes = value.get("attributes")
            self.assertEqual(value.get("auth"), True)
            # No SAML return attributes
            self.assertEqual(attributes.get("email"), None)

        set_privacyidea_config("ReturnSamlAttributes", "1")

        with self.app.test_request_context('/validate/samlcheck',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": "pin254676"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            value = result.get("value")
            attributes = value.get("attributes")
            self.assertEqual(value.get("auth"), True)
            self.assertEqual(attributes.get("email"),
                             "user@localhost.localdomain")
            self.assertEqual(attributes.get("givenname"), "Cornelius")
            self.assertEqual(attributes.get("mobile"), "+491111111")
            self.assertEqual(attributes.get("phone"),  "+491234566")
            self.assertEqual(attributes.get("realm"),  "realm1")
            self.assertEqual(attributes.get("username"),  "cornelius")

    def test_11_challenge_response_hotp(self):
        # set a chalresp policy for HOTP
        with self.app.test_request_context('/policy/pol_chal_resp',
                                           data={'action':
                                                     "challenge_response=hotp",
                                                 'scope': "authentication",
                                                 'realm': '',
                                                 'active': True},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue('"setPolicy pol_chal_resp": 1' in res.data,
                            res.data)

        serial = "CHALRESP1"
        pin = "chalresp1"
        # create a token and assign to the user
        db_token = Token(serial, tokentype="hotp")
        db_token.update_otpkey(self.otpkey)
        db_token.save()
        token = HotpTokenClass(db_token)
        token.set_user(User("cornelius", self.realm1))
        token.set_pin(pin)
        # Set the failcounter
        token.set_failcount(5)
        # create the challenge by authenticating with the OTP PIN
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertFalse(result.get("value"))
            self.assertEqual(detail.get("message"), "please enter otp: ")
            transaction_id = detail.get("transaction_id")
        self.assertEqual(token.get_failcount(), 5)

        # send the OTP value
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "transaction_id":
                                                     transaction_id,
                                                 "pass": "359152"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertTrue(result.get("value"))

        self.assertEqual(token.get_failcount(), 0)
        # delete the token
        remove_token(serial=serial)

    def test_12_challenge_response_sms(self):
        # set a chalresp policy for SMS
        with self.app.test_request_context('/policy/pol_chal_resp',
                                           data={'action':
                                                     "challenge_response=sms",
                                                 'scope': "authentication",
                                                 'realm': '',
                                                 'active': True},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue('"setPolicy pol_chal_resp": 1' in res.data,
                            res.data)

        serial = "CHALRESP2"
        pin = "chalresp2"
        # create a token and assign to the user
        init_token({"serial": serial,
                    "type": "sms",
                    "otpkey": self.otpkey,
                    "phone": "123456",
                    "pin": pin}, user=User("cornelius", self.realm1))
        # create the challenge by authenticating with the OTP PIN
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertFalse(result.get("value"))
            self.assertTrue("The PIN was correct, "
                            "but the SMS could not be sent" in
                            detail.get("message"))
            transaction_id = detail.get("transaction_id")

        # disable the token. The detail->message should be empty
        r = enable_token(serial=serial, enable=False)
        self.assertEqual(r, True)
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertFalse(result.get("value"))
            self.assertEqual(detail.get("message"), "Token is disabled")

        # delete the token
        remove_token(serial=serial)

    @smtpmock.activate
    def test_13_challenge_response_email(self):
        smtpmock.setdata(response={"hans@dampf.com": (200, 'OK')})
        # set a chalresp policy for Email
        with self.app.test_request_context('/policy/pol_chal_resp',
                                           data={'action':
                                                     "challenge_response=email",
                                                 'scope': "authentication",
                                                 'realm': '',
                                                 'active': True},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue('"setPolicy pol_chal_resp": 1' in res.data,
                            res.data)

        serial = "CHALRESP3"
        pin = "chalresp3"
        # create a token and assign to the user
        init_token({"serial": serial,
                    "type": "email",
                    "otpkey": self.otpkey,
                    "email": "hans@dampf.com",
                    "pin": pin}, user=User("cornelius", self.realm1))
        # create the challenge by authenticating with the OTP PIN
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertFalse(result.get("value"))
            self.assertEqual(detail.get("message"), "Enter the OTP from the "
                                                    "Email:")
            transaction_id = detail.get("transaction_id")

        # send the OTP value
        # Test with parameter state.
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "state":
                                                     transaction_id,
                                                 "pass": "359152"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertTrue(result.get("value"))

        # delete the token
        remove_token(serial=serial)

    def test_14_check_validity_period(self):
        serial = "VP001"
        password = serial
        init_token({"serial": serial,
                    "type": "spass",
                    "pin": password}, user=User("cornelius", self.realm1))

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": password}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value"))

        # Set validity period
        token_obj = get_tokens(serial=serial)[0]
        token_obj.set_validity_period_end("01/01/15 10:00")
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": password}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertFalse(result.get("value"))
            details = json.loads(res.data).get("detail")
            self.assertTrue("Outside validity period" in details.get("message"))

        token_obj.set_validity_period_end("01/01/99 10:00")
        token_obj.set_validity_period_start("01/01/98 10:00")

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": password}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertFalse(result.get("value"))
            details = json.loads(res.data).get("detail")
            self.assertTrue("Outside validity period" in details.get("message"))

        # delete the token
        remove_token(serial="VP001")

    def test_15_validate_at_sign(self):
        serial1 = "Split001"
        serial2 = "Split002"
        init_token({"serial": serial1,
                    "type": "spass",
                    "pin": serial1}, user=User("cornelius", self.realm1))

        init_token({"serial": serial2,
                    "type": "spass",
                    "pin": serial2}, user=User("cornelius", self.realm2))

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "pass": serial1}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value"))

        set_privacyidea_config("splitAtSign", "0")
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user":
                                                    "cornelius@"+self.realm2,
                                                 "pass": serial2}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

        set_privacyidea_config("splitAtSign", "1")
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user":
                                                    "cornelius@"+self.realm2,
                                                 "pass": serial2}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value"))

        # The default behaviour - if the config entry does not exist,
        # is to split the @Sign
        delete_privacyidea_config("splitAtSign")
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user":
                                                    "cornelius@"+self.realm2,
                                                 "pass": serial2}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value"))

    def test_16_autoresync_hotp(self):
        serial = "autosync1"
        token = init_token({"serial": serial,
                            "otpkey": self.otpkey,
                            "pin": "async"}, User("cornelius", self.realm2))
        set_privacyidea_config("AutoResync", True)
        token.set_sync_window(10)
        token.set_count_window(5)
        # counter = 8, is out of sync
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user":
                                                    "cornelius@"+self.realm2,
                                                 "pass": "async399871"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), False)

        # counter = 9, will be autosynced.
        # Authentication is successful
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user":
                                                    "cornelius@"+self.realm2,
                                                 "pass": "async520489"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), True)

        delete_privacyidea_config("AutoResync")

    def test_17_auth_timelimit_success(self):
        user = User("timelimituser", realm=self.realm2)
        pin = "spass"
        # create a token
        token = init_token({"type": "spass",
                            "pin": pin}, user=user)

        # set policy for timelimit
        set_policy(name="pol_time1",
                   scope=SCOPE.AUTHZ,
                   action="{0!s}=2/20s".format(ACTION.AUTHMAXSUCCESS))

        for i in [1, 2]:
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "timelimituser",
                                                     "realm": self.realm2,
                                                     "pass": pin}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = json.loads(res.data).get("result")
                self.assertEqual(result.get("value"), True)

        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "timelimituser",
                                                 "realm": self.realm2,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), False)

        delete_policy("pol_time1")
        remove_token(token.token.serial)

    def test_18_auth_timelimit_fail(self):
        user = User("timelimituser", realm=self.realm2)
        pin = "spass"
        # create a token
        token = init_token({"type": "spass", "pin": pin}, user=user)

        # set policy for timelimit
        set_policy(name="pol_time1",
                   scope=SCOPE.AUTHZ,
                   action="{0!s}=2/20s".format(ACTION.AUTHMAXFAIL))

        for i in [1, 2]:
            with self.app.test_request_context('/validate/check',
                                               method='POST',
                                               data={"user": "timelimituser",
                                                     "realm": self.realm2,
                                                     "pass": "wrongpin"}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = json.loads(res.data).get("result")
                self.assertEqual(result.get("value"), False)

        # Now we do the correct authentication, but
        # as already two authentications failed, this will fail, too
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "timelimituser",
                                                 "realm": self.realm2,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), False)
            details = json.loads(res.data).get("detail")
            self.assertEqual(details.get("message"),
                             "Only 2 failed authentications per 0:00:20")

        delete_policy("pol_time1")
        remove_token(token.token.serial)

    def test_19_validate_passthru(self):
        # user passthru, realm: self.realm2, passwd: pthru
        set_policy(name="pthru", scope=SCOPE.AUTH, action=ACTION.PASSTHRU)

        # Passthru with GET request
        with self.app.test_request_context(
                '/validate/check',
                method='GET',
                query_string=urlencode({"user": "passthru",
                                        "realm": self.realm2,
                                        "pass": "pthru"})):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), True)

        # Passthru with POST Request
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "passthru",
                                                 "realm": self.realm2,
                                                 "pass": "pthru"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), True)

        delete_policy("pthru")

    def test_20_questionnaire(self):
        pin = "pin"
        serial = "QUST1234"
        questions = {"frage1": "antwort1",
                     "frage2": "antwort2",
                     "frage3": "antwort3"}
        j_questions = json.dumps(questions)

        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "question",
                                                 "pin": pin,
                                                 "serial": serial,
                                                 "questions": j_questions},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

        set_privacyidea_config("question.num_answers", 2)
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "question",
                                                 "pin": pin,
                                                 "serial": serial,
                                                 "questions": j_questions},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertEqual(value, True)

        # Start a challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": serial,
                                                 "pass": pin}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertFalse(result.get("value"))
            detail = json.loads(res.data).get("detail")
            transaction_id = detail.get("transaction_id")
            question = detail.get("message")
            self.assertTrue(question in questions)

        # Respond to the challenge
        answer = questions[question]
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"serial": serial,
                                                 "transaction_id":
                                                     transaction_id,
                                                 "pass": answer}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), True)

    def test_21_validate_disabled(self):
        # test a user with two tokens and otppin=userstore.
        # One token is disabled. But the user must be able to login with the
        # 2nd token
        # user disableduser, realm: self.realm2, passwd: superSecret
        set_policy(name="disabled",
                   scope=SCOPE.AUTH,
                   action="{0!s}={1!s}".format(ACTION.OTPPIN, "userstore"))
        # enroll two tokens
        r = init_token({"type": "spass", "serial": "spass1d"},
                       user=User("disableduser", self.realm2))
        r = init_token({"type": "spass", "serial": "spass2d"},
                       user=User("disableduser", self.realm2))
        # disable first token
        r = enable_token("spass1d", False)
        self.assertEqual(r, True)
        # Check that the user still can authenticate with the 2nd token
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "disableduser",
                                                 "realm": self.realm2,
                                                 "pass": "superSecret"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), True)

        # disable 2nd token
        r = enable_token("spass2d", False)
        r = enable_token("spass1d")
        self.assertEqual(r, True)
        # Check that the user still can authenticate with the first token
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "disableduser",
                                                 "realm": self.realm2,
                                                 "pass": "superSecret"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), True)

        delete_policy("disabled")

    def test_22_validate_locked(self):
        # test a user with two tokens
        # One token is locked/revoked.
        #  But the user must be able to login with the 2nd token
        # user lockeduser, realm: self.realm2
        # enroll two tokens
        user = "lockeduser"
        set_policy(name="locked",
                   scope=SCOPE.AUTH,
                   action="{0!s}={1!s}".format(ACTION.OTPPIN, "tokenpin"))
        r = init_token({"type": "spass", "serial": "spass1l",
                        "pin": "locked"},
                       user=User(user, self.realm2))
        r = init_token({"type": "spass", "serial": "spass2l",
                        "pin": "locked"},
                       user=User(user, self.realm2))
        # disable first token
        r = revoke_token("spass1l")
        self.assertEqual(r, True)
        # Check that the user still can authenticate with the 2nd token
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": user,
                                                 "realm": self.realm2,
                                                 "pass": "locked"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), True)

        remove_token("spass1l")
        remove_token("spass2l")
        delete_policy("locked")
