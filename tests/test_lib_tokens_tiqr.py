"""
This test file tests the lib.tokens.tiqrtoken and lib.tokens.ocra
This depends on lib.tokenclass
"""

from .base import MyTestCase
from privacyidea.lib.tokens.tiqrtoken import TiqrTokenClass
from privacyidea.lib.tokens.ocra import OCRASuite, OCRA
from privacyidea.lib.token import init_token
from privacyidea.lib.error import ParameterError
import re
import binascii
from urllib import urlencode
import json
from flask import Request, g
from werkzeug.test import EnvironBuilder


class OCRASuiteTestCase(MyTestCase):

    def test_00_ocrasuite_fail(self):
        self.assertRaises(Exception, OCRASuite, "algo:crypto")
        self.assertRaises(Exception, OCRASuite,
                          "algo:crypto:data:ss")

        # NO OCRA-2
        self.assertRaises(Exception, OCRASuite,
                          "OCRA-2:HOTP-SHA1-6:QH10-S128")

        # no TOTP
        self.assertRaises(Exception, OCRASuite,
                          "OCRA-2:TOTP-SHA1-6:QH10-S128")

        # No unknown SHA
        self.assertRaises(Exception, OCRASuite,
                          "OCRA-1:HOTP-SHA3-6:QH10-S128")

        # No unknown truncation
        self.assertRaises(Exception, OCRASuite,
                          "OCRA-1:HOTP-SHA1-3:QH10-S128")

        # wrong cryptofunction
        self.assertRaises(Exception, OCRASuite,
                          "OCRA-1:HOTPSHA13:QH10-S128")

        # No HOTP
        self.assertRaises(Exception, OCRASuite,
                          "OCRA-1:TOTP-SHA1-4:QH10-S128")

        # check datainput
        # counter
        self.assertRaises(Exception, OCRASuite,
                          "OCRA-1:HOTP-SHA512-8:X-QN08-PSHA1")

        # challenge
        # wrong datainput
        self.assertRaises(Exception, OCRASuite,
                          "OCRA-1:HOTP-SHA512-8:CQX04PSHA1")
        self.assertRaises(Exception, OCRASuite,
                          "OCRA-1:HOTP-SHA512-8:C-Q-X-0-4-PSHA1")
        # wrong challenge type
        self.assertRaises(Exception, OCRASuite,
                          "OCRA-1:HOTP-SHA512-8:C-QX04-PSHA1")
        # challenge to short
        self.assertRaises(Exception, OCRASuite,
                          "OCRA-1:HOTP-SHA512-8:C-QN03-PSHA1")
        # challenge to long
        self.assertRaises(Exception, OCRASuite,
                          "OCRA-1:HOTP-SHA512-8:C-QN65-PSHA1")
        # challenge length not a number
        self.assertRaises(Exception, OCRASuite,
                          "OCRA-1:HOTP-SHA512-8:C-QNXX-PSHA1")

        # signature
        # unknown signature type
        self.assertRaises(Exception, OCRASuite,
                          "OCRA-1:HOTP-SHA512-8:C-QN04-XSHA1")
        # Wrong hash
        self.assertRaises(Exception, OCRASuite,
                          "OCRA-1:HOTP-SHA512-8:C-QN04-PSHA3")

        # Session length
        self.assertRaises(Exception, OCRASuite,
                          "OCRA-1:HOTP-SHA512-8:C-QN04-SXXX")

        self.assertRaises(Exception, OCRASuite,
                          "OCRA-1:HOTP-SHA512-8:C-QN04-S100")

        # Timestamp
        self.assertRaises(Exception, OCRASuite,
                          "OCRA-1:HOTP-SHA512-8:C-QN04-T10X")
        self.assertRaises(Exception, OCRASuite,
                          "OCRA-1:HOTP-SHA512-8:C-QN04-T100M")
        self.assertRaises(Exception, OCRASuite,
                          "OCRA-1:HOTP-SHA512-8:C-QN04-TxxM")

    def test_01_ocrasuite_success(self):
        os = OCRASuite("OCRA-1:HOTP-SHA1-6:QH10-S128")
        self.assertEqual(os.algorithm, "OCRA-1")
        self.assertEqual(os.sha, "SHA1")
        self.assertEqual(os.truncation, 6)
        self.assertEqual(os.challenge_type, "QH")
        self.assertEqual(os.challenge_length, 10)
        self.assertEqual(os.signature_type, "S")
        self.assertEqual(os.session_length, 128)
        os = OCRASuite("OCRA-1:HOTP-SHA512-8:C-QN08-PSHA1")
        self.assertEqual(os.sha, "SHA512")
        self.assertEqual(os.truncation, 8)
        self.assertEqual(os.counter, "C")
        self.assertEqual(os.challenge_type, "QN")
        self.assertEqual(os.signature_hash, "SHA1")
        os = OCRASuite("OCRA-1:HOTP-SHA256-6:QA10-T1M")
        self.assertEqual(os.time_frame, "M")
        self.assertEqual(os.time_value, 1)
        os = OCRASuite("OCRA-1:HOTP-SHA1-4:QH8-S512")

    def test_02_create_challenge(self):
        # test creation of hex challenge
        os = OCRASuite("OCRA-1:HOTP-SHA1-6:QH10-S128")
        c = os.create_challenge()
        self.assertEqual(len(c), 20)
        self.assertTrue("G" not in c, c)

        # test creation of alphanum challenge
        os = OCRASuite("OCRA-1:HOTP-SHA1-6:QA10-S128")
        c = os.create_challenge()
        self.assertEqual(len(c), 10)
        self.assertTrue("-" not in c, c)

        # test creation of numeric challenge
        os = OCRASuite("OCRA-1:HOTP-SHA1-6:QN10-S128")
        c = os.create_challenge()
        self.assertEqual(len(c), 10)
        # Test, if this is a number
        i_c = int(c)

KEY20 = "3132333435363738393031323334353637383930"
KEY32 = "3132333435363738393031323334353637383930313233343536373839303132"
KEY64 = "31323334353637383930313233343536373839303132333435363738393031323334" \
        "353637383930313233343536373839303132333435363738393031323334"


class OCRATestCase(MyTestCase):

    def test_01_one_way_chal_resp(self):
        # http://tools.ietf.org/html/rfc6287#appendix-C.1
        ocrasuite = "OCRA-1:HOTP-SHA1-6:QN08"
        testvectors = [
            {"Q": "00000000", "r": "237653"},
            {"Q": "11111111", "r": "243178"},
            {"Q": "22222222", "r": "653583"},
            {"Q": "33333333", "r": "740991"},
            {"Q": "44444444", "r": "608993"},
            {"Q": "55555555", "r": "388898"},
            {"Q": "66666666", "r": "816933"},
            {"Q": "77777777", "r": "224598"},
            {"Q": "88888888", "r": "750600"},
            {"Q": "99999999", "r": "294470"}
        ]
        for tv in testvectors:
            ocra_object = OCRA(ocrasuite, binascii.unhexlify(KEY20))
            r = ocra_object.get_response(tv.get("Q"))
            self.assertEqual(r, tv.get("r"))

    def test_02_one_way_chal_with_pin(self):
        # http://tools.ietf.org/html/rfc6287#appendix-C.1
        pin = "1234"
        ocrasuite = "OCRA-1:HOTP-SHA256-8:QN08-PSHA1"
        testvectors = [
            {"Q": "00000000", "r": "83238735"},
            {"Q": "11111111", "r": "01501458"},
            {"Q": "22222222", "r": "17957585"},
            {"Q": "33333333", "r": "86776967"},
            {"Q": "44444444", "r": "86807031"}
        ]
        for tv in testvectors:
            ocra_object = OCRA(ocrasuite, binascii.unhexlify(KEY32))
            r = ocra_object.get_response(tv.get("Q"), pin=pin)
            self.assertEqual(r, tv.get("r"))

    def test_03_one_way_chal_with_pin_and_counter(self):
        # http://tools.ietf.org/html/rfc6287#appendix-C.1
        pin = "1234"
        pin_hash = "7110eda4d09e062aa5e4a390b0a572ac0d2c0220"
        ocrasuite = "OCRA-1:HOTP-SHA256-8:C-QN08-PSHA1"
        testvectors = [
            {"Q": "12345678", "r": "65347737", "C": "0"},
            {"Q": "12345678", "r": "86775851", "C": "1"},
            {"Q": "12345678", "r": "78192410", "C": "2"},
            {"Q": "12345678", "r": "71565254", "C": "3"},
            {"Q": "12345678", "r": "10104329", "C": "4"},
            {"Q": "12345678", "r": "65983500", "C": "5"},
            {"Q": "12345678", "r": "70069104", "C": "6"},
            {"Q": "12345678", "r": "91771096", "C": "7"},
            {"Q": "12345678", "r": "75011558", "C": "8"},
            {"Q": "12345678", "r": "08522129", "C": "9"},
        ]
        # test with PIN
        for tv in testvectors:
            ocra_object = OCRA(ocrasuite, binascii.unhexlify(KEY32))
            r = ocra_object.get_response(tv.get("Q"), pin=pin,
                                         counter=tv.get("C"))
            self.assertEqual(r, tv.get("r"))

        # test with pin_hash
        for tv in testvectors:
            ocra_object = OCRA(ocrasuite, binascii.unhexlify(KEY32))
            r = ocra_object.get_response(tv.get("Q"), pin_hash=pin_hash,
                                         counter=tv.get("C"))
            self.assertEqual(r, tv.get("r"))

    def test_04_one_way_chal_with_counter_512(self):
        # http://tools.ietf.org/html/rfc6287#appendix-C.1
        ocrasuite = "OCRA-1:HOTP-SHA512-8:C-QN08"
        testvectors = [
            {"Q": "00000000", "C": "00000", "r": "07016083"},
            {"Q": "11111111", "C": "00001", "r": "63947962"},
            {"Q": "22222222", "C": "00002", "r": "70123924"},
            {"Q": "33333333", "C": "00003", "r": "25341727"},
            {"Q": "44444444", "C": "00004", "r": "33203315"},
            {"Q": "55555555", "C": "00005", "r": "34205738"},
            {"Q": "66666666", "C": "00006", "r": "44343969"},
            {"Q": "77777777", "C": "00007", "r": "51946085"},
            {"Q": "88888888", "C": "00008", "r": "20403879"},
            {"Q": "99999999", "C": "00009", "r": "31409299"},
        ]
        for tv in testvectors:
            ocra_object = OCRA(ocrasuite, binascii.unhexlify(KEY64))
            r = ocra_object.get_response(tv.get("Q"),
                                         counter=tv.get("C"))
            self.assertEqual(r, tv.get("r"))

    def test_05_one_way_chal_with_timestamp(self):
        # http://tools.ietf.org/html/rfc6287#appendix-C.1
        ocrasuite = "OCRA-1:HOTP-SHA512-8:QN08-T1M"
        testvectors = [
            {"Q": "00000000", "T": "132d0b6", "r": "95209754"},
            {"Q": "11111111", "T": "132d0b6", "r": "55907591"},
            {"Q": "22222222", "T": "132d0b6", "r": "22048402"},
            {"Q": "33333333", "T": "132d0b6", "r": "24218844"},
            {"Q": "44444444", "T": "132d0b6", "r": "36209546"}
        ]
        for tv in testvectors:
            ocra_object = OCRA(ocrasuite, binascii.unhexlify(KEY64))
            r = ocra_object.get_response(tv.get("Q"),
                                         timesteps=tv.get("T"))
            self.assertEqual(r, tv.get("r"))

    def test_06_plain_signature(self):
        # http://tools.ietf.org/html/rfc6287#appendix-C.3
        ocrasuite = "OCRA-1:HOTP-SHA256-8:QA08"
        testvectors = [
            {"Q": "SIG10000", "r": "53095496"},
            {"Q": "SIG11000", "r": "04110475"},
            {"Q": "SIG12000", "r": "31331128"},
            {"Q": "SIG13000", "r": "76028668"},
            {"Q": "SIG14000", "r": "46554205"}
        ]
        for tv in testvectors:
            ocra_object = OCRA(ocrasuite, binascii.unhexlify(KEY32))
            r = ocra_object.get_response(tv.get("Q"))
            self.assertEqual(r, tv.get("r"))

    def test_07_plain_signature_with_time(self):
        # http://tools.ietf.org/html/rfc6287#appendix-C.3
        ocrasuite = "OCRA-1:HOTP-SHA512-8:QA10-T1M"
        testvectors = [
            {"Q": "SIG1000000", "r": "77537423", "T": "132d0b6"},
            {"Q": "SIG1100000", "r": "31970405", "T": "132d0b6"},
            {"Q": "SIG1200000", "r": "10235557", "T": "132d0b6"},
            {"Q": "SIG1300000", "r": "95213541", "T": "132d0b6"},
            {"Q": "SIG1400000", "r": "65360607", "T": "132d0b6"}
        ]
        for tv in testvectors:
            ocra_object = OCRA(ocrasuite, binascii.unhexlify(KEY64))
            r = ocra_object.get_response(tv.get("Q"), timesteps=tv.get("T"))
            self.assertEqual(r, tv.get("r"))

    def test_08_create_data_input(self):
        # The ocrasuite is stored as a unicode in the webui. As it is used for
        # the OCRA datainput, it must be internally converted to a string.
        ocrasuite = u"OCRA-1:HOTP-SHA1-6:QN10"
        question = "1344454126"
        ocra_object = OCRA(ocrasuite, binascii.unhexlify(KEY20))
        r = ocra_object.create_data_input(question)

        # create data_input with missing counter
        ocrasuite = u"OCRA-1:HOTP-SHA1-6:C-QN10"
        ocra_object=OCRA(ocrasuite, binascii.unhexlify(KEY20))
        self.assertRaises(Exception, ocra_object.create_data_input, question)

        # create data_input with missing PIN
        ocrasuite = u"OCRA-1:HOTP-SHA1-6:QN10-PSHA1"
        ocra_object=OCRA(ocrasuite, binascii.unhexlify(KEY20))
        self.assertRaises(Exception, ocra_object.create_data_input, question)

        # create data_input with missing Timesteps
        ocrasuite = u"OCRA-1:HOTP-SHA1-6:QN10-T1M"
        ocra_object=OCRA(ocrasuite, binascii.unhexlify(KEY20))
        self.assertRaises(Exception, ocra_object.create_data_input, question)


class TiQRTokenTestCase(MyTestCase):
    serial1 = "ser1"

    # set_user, get_user, reset, set_user_identifiers

    def test_00_users(self):
        self.setUp_user_realms()

    def test_01_create_token(self):
        pin = "test"
        token = init_token({"type": "tiqr",
                            "pin": pin,
                            "serial": "TIQR1",
                            "user": "cornelius",
                            "realm": self.realm1})
        self.assertEqual(token.type, "tiqr")

        prefix = TiqrTokenClass.get_class_prefix()
        self.assertEqual(prefix, "TiQR")

        info = TiqrTokenClass.get_class_info()
        self.assertEqual(info.get("type"), "tiqr")

        info = TiqrTokenClass.get_class_info("type")
        self.assertEqual(info, "tiqr")

        idetail = token.get_init_detail()
        self.assertEqual(idetail.get("tiqrenroll").get("description"),
                         "URL for TiQR enrollment")
        self.assertTrue("serial" in idetail, idetail)
        self.assertTrue("img" in idetail.get("tiqrenroll"), idetail)
        self.assertTrue("value" in idetail.get("tiqrenroll"), idetail)

        # Check the challenge request
        r = token.is_challenge_request(pin)
        self.assertEqual(r, True)
        r = token.is_challenge_request(pin + "123456")
        self.assertEqual(r, False)

        # Check create_challenge
        r = token.create_challenge()
        self.assertEqual(r[0], True)
        self.assertEqual(r[1], "Please scan the QR Code")
        self.assertTrue("img" in r[3], r[3])
        self.assertTrue("value" in r[3], r[3])

    def test_02_api_endpoint(self):
        pin = "tiqr"
        token = init_token({"type": "tiqr",
                            "pin": pin,
                            "user": "cornelius",
                            "realm": self.realm1})
        idetail = token.get_init_detail()
        value = idetail.get("tiqrenroll").get("value")
        # 'tiqrenroll://None?action=metadata&session=b81ecdf74118dcf6fa1cd41d3d4b2fec56c9107f&serial=TiQR000163CB
        # get the serial and the session
        m = re.search('&serial=(.*)$', value)
        serial = m.group(1)
        m = re.search('&session=(.*)&', value)
        session = m.group(1)

        # test meta data
        builder = EnvironBuilder(method='POST',
                                 data={},
                                 headers={})
        env = builder.get_environ()
        # Set the remote address so that we can filter for it
        env["REMOTE_ADDR"] = "10.0.0.1"
        g.client_ip = env["REMOTE_ADDR"]
        req = Request(env)
        req.all_data = {"action": "metadata",
                        "session": session,
                        "serial": serial}

        r = TiqrTokenClass.api_endpoint(req, g)

        self.assertEqual(r[0], "json")
        self.assertTrue("identity" in r[1], r[1])
        self.assertTrue("service" in r[1], r[1])

        # Test invalid action
        req.all_data = {"action": "unknown"}
        self.assertRaises(Exception,
                          TiqrTokenClass.api_endpoint, req, g)

        # test enrollment with invalid session
        req.all_data = {"action": "enrollment",
                        "serial": serial,
                        "session": "123",
                        "secret": KEY20}

        self.assertRaises(ParameterError,
                          TiqrTokenClass.api_endpoint, req, g)

        # test enrollment with valid session
        req.all_data = {"action": "enrollment",
                        "serial": serial,
                        "session": session,
                        "secret": KEY20}
        r = TiqrTokenClass.api_endpoint(req, g)
        self.assertEqual(r[0], "plain")
        self.assertEqual(r[1], "OK")

        # test authentication endpoint
        # create a challenge by issuing validate/check with user and pin
        session = ""
        challenge = ""
        with self.app.test_request_context('/validate/check',
                                           method='GET',
                                           query_string=urlencode({
                                               "user": "cornelius",
                                               "realm": self.realm1,
                                               "pass": pin})):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertTrue(result.get("status") is True, result)
            self.assertTrue(result.get("value") is False, result)
            transaction_id = detail.get("transaction_id")
            image_url = detail.get("attributes").get("value")
            self.assertTrue(image_url.startswith("tiqrauth"))
            # u'tiqrauth://cornelius_realm1@org.privacyidea
            # /12335970131032896263/e0fac7bb2e3ea4219ead'
            # session = 12335970131032896263
            # challenge = e0fac7bb2e3ea4219ead
            r = image_url.split("/")
            session = r[3]
            challenge = r[4]

        ocrasuite = token.get_tokeninfo("ocrasuite")
        ocra_object = OCRA(ocrasuite, key=binascii.unhexlify(KEY20))
        # Calculate Response with the challenge.
        response = ocra_object.get_response(challenge)

        # First, send a wrong response
        req.all_data = {"response": "12345",
                        "userId": "cornelius_{0!s}".format(self.realm1),
                        "sessionKey": session,
                        "operation": "login"}
        r = TiqrTokenClass.api_endpoint(req, g)
        self.assertEqual(r[0], "plain")
        self.assertEqual(r[1], "INVALID_RESPONSE")

        # Send the correct response
        req.all_data = {"response": response,
                        "userId": "cornelius_{0!s}".format(self.realm1),
                        "sessionKey": session,
                        "operation": "login"}
        r = TiqrTokenClass.api_endpoint(req, g)
        self.assertEqual(r[0], "plain")
        self.assertEqual(r[1], "OK")

        # Send the same response a second time would not work
        # since the Challenge is marked as answered
        req.all_data = {"response": response,
                        "userId": "cornelius_{0!s}".format(self.realm1),
                        "sessionKey": session,
                        "operation": "login"}
        r = TiqrTokenClass.api_endpoint(req, g)
        self.assertEqual(r[0], "plain")
        self.assertEqual(r[1], "INVALID_CHALLENGE")

        # Finally we check the OTP status:
        r = token.check_challenge_response(options={"transaction_id":
                                                    transaction_id})
        self.assertTrue(r > 0, r)

        # Check the same challenge again. It will fail, since the
        # challenge was deleted from the database
        r = token.check_challenge_response(options={"transaction_id":
                                                    transaction_id})
        self.assertTrue(r < 0, r)


