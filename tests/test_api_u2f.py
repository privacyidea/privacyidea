from .base import MyTestCase
import json
import os
from privacyidea.lib.error import (TokenAdminError, ParameterError)
from privacyidea.lib.token import get_tokens, init_token, assign_token
from privacyidea.lib.user import User
from privacyidea.lib.caconnector import save_caconnector
from urllib import urlencode

PWFILE = "tests/testdata/passwords"
IMPORTFILE = "tests/testdata/import.oath"
IMPORTFILE2 = "tests/testdata/empty.oath"
YUBICOFILE = "tests/testdata/yubico-oath.csv"
OTPKEY = "3132333435363738393031323334353637383930"
OTPKEY2 = "010fe88d31948c0c2e3258a4b0f7b11956a258ef"
OTPVALUES2 = ["551536", "703671", "316522", "413789"]


class APIU2fTestCase(MyTestCase):

    serial = "U2F001"

    def test_000_setup_realms(self):
        self.setUp_user_realms()

    def test_01_register_u2f(self):
        # step 1
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "u2f",
                                                 "serial": self.serial},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            response = json.loads(res.data)
            result = response.get("result")
            details = response.get("detail")
            self.assertEqual(result.get("value"), True)

            serial = details.get("serial")
            self.assertEqual(serial[:3], "U2F")
            self.assertEqual(details.get("u2fRegisterRequest").get(
                "version"), "U2F_V2")
            challenge = details.get("u2fRegisterRequest").get("challenge")
            self.assertTrue(len(challenge) > 20)

        # step 2
        # We need to send back regData and clientData.
        REG_DATA = "BQRFnd8XtfZzsTK68VPK64Bcjiog_ZzyYNuzjaaGwpPnSpifxaqQV4_4IMxVlGS3CLoQmNAR41MSMxZHG0dENLRmQGnk4OqRxGRHmUOOLmDkGgdIJycQe79JCERV1gqGnWAOFBg_bH4WFSxZwnX-IMRcl3zW_X442QNrrdFySvXrba4wggIcMIIBBqADAgECAgQ4Zt91MAsGCSqGSIb3DQEBCzAuMSwwKgYDVQQDEyNZdWJpY28gVTJGIFJvb3QgQ0EgU2VyaWFsIDQ1NzIwMDYzMTAgFw0xNDA4MDEwMDAwMDBaGA8yMDUwMDkwNDAwMDAwMFowKzEpMCcGA1UEAwwgWXViaWNvIFUyRiBFRSBTZXJpYWwgMTM4MzExNjc4NjEwWTATBgcqhkjOPQIBBggqhkjOPQMBBwNCAAQ3jfx0DHOblHJO09Ujubh2gQZWwT3ob6-uzzjZD1XiyAob_gsw3FOzXefQRblty48r-U-o4LkDFjx_btwuSHtxoxIwEDAOBgorBgEEAYLECgEBBAAwCwYJKoZIhvcNAQELA4IBAQIaR2TKAInPkq24f6hIU45yzD79uzR5KUMEe4IWqTm69METVio0W2FHWXlpeUe85nGqanwGeW7U67G4_WAnGbcd6zz2QumNsdlmb_AebbdPRa95Z8BG1ub_S04JoxQYNLaa8WRlzN7POgqAnAqkmnsZQ_W9Tj2uO9zP3mpxOkkmnqz7P5zt4Lp5xrv7p15hGOIPD5V-ph7tUmiCJsq0LfeRA36X7aXi32Ap0rt_wyfnRef59YYr7SmwaMuXKjbIZSLesscZZTMzXd-uuLb6DbUCasqEVBkGGqTRfAcOmPov1nHUrNDCkOR0obR4PsJG4PiamIfApNeoXGYpGbok6nucMEYCIQC_yerJqB3mnuAJGfbdKuOIx-Flxr-VSQ2nAkUUE_50dQIhAJE2NL1Xs2oVEG4bFzEM86TfS7nkHxad89aYmUrII49V"
        CLIENT_DATA = "eyJ0eXAiOiJuYXZpZ2F0b3IuaWQuZmluaXNoRW5yb2xsbWVudCIsImNoYWxsZW5nZSI6ImdXbndtYnFSMl9YOE91RFhId0dyQWNmUTBUajN4YTVfZ2RJMjBYcVlsdTg9Iiwib3JpZ2luIjoiaHR0cDovL2xvY2FsaG9zdDo1MDAwIiwiY2lkX3B1YmtleSI6IiJ9"
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"serial": serial,
                                                 "type": "u2f",
                                                 "regdata": REG_DATA,
                                                 "clientdata": CLIENT_DATA},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            response = json.loads(res.data)
            result = response.get("result")
            details = response.get("detail")
            self.assertEqual(result.get("value"), True)

    def test_02_validate(self):
        # assign token to user
        r = assign_token(self.serial, User("cornelius", self.realm1),
                         pin="u2f")
        self.assertEqual(r, True)

        # Issue challenge
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user":
                                                    "cornelius@"+self.realm1,
                                                 "pass": "u2f"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertEqual(result.get("value"), False)
            transaction_id = detail.get("transaction_id")
            self.assertEqual(len(transaction_id), len('01350277175811850842'))
            self.assertTrue("Please confirm with your U2F token" in
                            detail.get("message"), detail.get("message"))
            attributes = detail.get("attributes")
            u2f_sign_request = attributes.get("u2fSignRequest")
            self.assertTrue("appId" in u2f_sign_request)
            self.assertTrue("challenge" in u2f_sign_request)
            self.assertTrue("keyHandle" in u2f_sign_request)
            self.assertEqual(u2f_sign_request.get("version"), "U2F_V2")

        # TODO: calculate the response for the challenge
        # Send the response
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "pass": "",
                                                 "transaction_id":
                                                     transaction_id,
                                                 "clientdata": "TODO",
                                                 "signaturedata": "TODO"}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertEqual(result.get("value"), True)
            self.assertEqual(result.get("value"), True)

