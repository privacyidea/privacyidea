"""
This test file tests the lib.tokens.u2ftoken
This depends on lib.tokenclass
"""

from .base import MyTestCase
from privacyidea.lib.tokens.u2ftoken import U2fTokenClass
from privacyidea.lib.token import init_token
from privacyidea.lib.error import ParameterError
import re
import binascii
from urllib import urlencode
import json

REG_DATA = "BQQl1XrxeV4jir9opH729wDeYnjYM5LeYr2qkbqNE5cbm_UYovMgImflArJbvt97EB8TaziM3BrwWEuvLkIniFaSQM6A1rTR7P51aKf_9fL1_dKied5RbRrEO69CoFoi-kWE3le9eQNXyDVj1MgpJkv-F58nAEAEHknQY3vCd2aEEQswggIcMIIBBqADAgECAgQ4Zt91MAsGCSqGSIb3DQEBCzAuMSwwKgYDVQQDEyNZdWJpY28gVTJGIFJvb3QgQ0EgU2VyaWFsIDQ1NzIwMDYzMTAgFw0xNDA4MDEwMDAwMDBaGA8yMDUwMDkwNDAwMDAwMFowKzEpMCcGA1UEAwwgWXViaWNvIFUyRiBFRSBTZXJpYWwgMTM4MzExNjc4NjEwWTATBgcqhkjOPQIBBggqhkjOPQMBBwNCAAQ3jfx0DHOblHJO09Ujubh2gQZWwT3ob6-uzzjZD1XiyAob_gsw3FOzXefQRblty48r-U-o4LkDFjx_btwuSHtxoxIwEDAOBgorBgEEAYLECgEBBAAwCwYJKoZIhvcNAQELA4IBAQIaR2TKAInPkq24f6hIU45yzD79uzR5KUMEe4IWqTm69METVio0W2FHWXlpeUe85nGqanwGeW7U67G4_WAnGbcd6zz2QumNsdlmb_AebbdPRa95Z8BG1ub_S04JoxQYNLaa8WRlzN7POgqAnAqkmnsZQ_W9Tj2uO9zP3mpxOkkmnqz7P5zt4Lp5xrv7p15hGOIPD5V-ph7tUmiCJsq0LfeRA36X7aXi32Ap0rt_wyfnRef59YYr7SmwaMuXKjbIZSLesscZZTMzXd-uuLb6DbUCasqEVBkGGqTRfAcOmPov1nHUrNDCkOR0obR4PsJG4PiamIfApNeoXGYpGbok6nucMEUCIQCrb315bbFcgQSQdiZ2TCxIFWuxnpr1d2MnsGpC3gZ-VAIgWPdkPaabsnJ4ElE2GIEWsM-aqHu642N86MN3eTwb_RA"
KEY_HANDLE_HEX = 'ce80d6b4d1ecfe7568a7fff5f2f5fdd2a279de516d1ac43baf42a05a22fa4584de57bd790357c83563d4c829264bfe179f270040041e49d0637bc2776684110b'
APP_ID = "http://localhost:5000"


class U2FTokenTestCase(MyTestCase):

    def test_00_users(self):
        self.setUp_user_realms()

    def test_01_create_token(self):
        pin = "test"
        # Init step1
        token = init_token({"type": "u2f",
                            "pin": pin})
        serial = token.token.serial

        self.assertEqual(token.type, "u2f")

        prefix = U2fTokenClass.get_class_prefix()
        self.assertEqual(prefix, "U2F")

        info = U2fTokenClass.get_class_info()
        self.assertEqual(info.get("type"), "u2f")

        info = U2fTokenClass.get_class_info("type")
        self.assertEqual(info, "u2f")

        idetail = token.get_init_detail()
        detail_serial = idetail.get("serial")
        self.assertEqual(serial, detail_serial)

        registerRequest = idetail.get("u2fRegisterRequest")
        version = registerRequest.get("version")
        self.assertEqual(version, "U2F_V2")
        challenge = registerRequest.get("challenge")
        self.assertEqual(len(challenge), 44)

        # Init step 2
        token = init_token({"type": "u2f",
                            "serial": serial,
                            "regdata": REG_DATA})
        idetail = token.get_init_detail()
        subject = idetail.get("u2fRegisterResponse").get("subject")
        self.assertEqual(subject, 'Yubico U2F EE Serial 13831167861')

        #
        # Do some authentication
        #

        # challenge
        is_chalrequest = token.is_challenge_request(pin)
        self.assertEqual(is_chalrequest, True)

        res, message, t_id, response = token.create_challenge()
        self.assertTrue(res)
        self.assertEqual(message, "Please confirm with your U2F token")
        self.assertEqual(len(t_id), 20)
        u2f_sign_request = response.get("u2fSignRequest")
        version = u2f_sign_request.get("version")
        self.assertEqual(version, "U2F_V2")
        key_handle = u2f_sign_request.get("keyHandle")
        key_handle_hex = binascii.hexlify(key_handle)
        self.assertTrue("appId" in u2f_sign_request, u2f_sign_request)
        self.assertTrue("challenge" in u2f_sign_request, u2f_sign_request)
        self.assertTrue("keyHandle" in u2f_sign_request, u2f_sign_request)
        self.assertEqual(key_handle_hex, KEY_HANDLE_HEX)
        self.assertEqual(u2f_sign_request.get("appId"), APP_ID)
        self.assertEqual(len(u2f_sign_request.get("challenge")), 64)

