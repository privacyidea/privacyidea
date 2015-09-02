"""
This test file tests the lib.tokens.tiqrtoken
This depends on lib.tokenclass
"""

from .base import MyTestCase
from privacyidea.lib.tokens.tiqrtoken import TiqrTokenClass
from privacyidea.lib.token import init_token
from privacyidea.lib.error import ParameterError
import re


class TiQRTokenTestCase(MyTestCase):
    serial1 = "ser1"

    # set_user, get_user, reset, set_user_identifiers
    
    def test_01_create_token(self):
        pin = "test"
        token = init_token({"type": "tiqr",
                            "pin": pin})
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
        token = init_token({"type": "tiqr"})
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
