"""
This test file tests the lib.tokens.tiqrtoken and lib.tokens.ocra
This depends on lib.tokenclass
"""

from .base import MyTestCase
from privacyidea.lib.tokens.tiqrtoken import TiqrTokenClass
from privacyidea.lib.tokens.ocra import OCRASuite
from privacyidea.lib.token import init_token
from privacyidea.lib.error import ParameterError
import re


class OCRATestCase(MyTestCase):

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



class TiQRTokenTestCase(MyTestCase):
    serial1 = "ser1"

    # set_user, get_user, reset, set_user_identifiers

    def test_00_users(self):
        self.setUp_user_realms()

    def test_01_create_token(self):
        pin = "test"
        token = init_token({"type": "tiqr",
                            "pin": pin,
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
        pin = "1234"
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
        r = TiqrTokenClass.api_endpoint({"action": "metadata",
                                         "session": session,
                                         "serial": serial})

        self.assertEqual(r[0], "json")
        self.assertTrue("identity" in r[1], r[1])
        self.assertTrue("service" in r[1], r[1])

        # Test invalid action
        self.assertRaises(Exception,
                          TiqrTokenClass.api_endpoint, {"action": "unknown"})

        # test enrollment with invalid session
        self.assertRaises(ParameterError,
                          TiqrTokenClass.api_endpoint,
                          {"action": "enrollment",
                           "serial": serial,
                           "session": "123",
                           "secret": "313233"})

        # test enrollment with valid session
        r = TiqrTokenClass.api_endpoint({"action": "enrollment",
                                         "serial": serial,
                                         "session": session,
                                         "secret": "313233"})
        self.assertEqual(r[0], "text")
        self.assertEqual(r[1], "OK")

        # test authentication endpoint
        r = TiqrTokenClass.api_endpoint({"response": "12345",
                                         "userId": "1234",
                                         "sessionKey": "1234",
                                         "operation": "login"})
        self.assertEqual(r[0], "text")

