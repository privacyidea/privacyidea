from .base import MyTestCase
import json
import os
import datetime
from privacyidea.lib.policy import (set_policy, delete_policy, SCOPE, ACTION,
                                    PolicyClass)
from privacyidea.lib.token import get_tokens, init_token, remove_token
from privacyidea.lib.user import User
from privacyidea.lib.caconnector import save_caconnector
from urllib import urlencode
from privacyidea.lib.token import check_serial_pass
from privacyidea.lib.tokenclass import DATE_FORMAT
from privacyidea.lib.config import set_privacyidea_config, delete_privacyidea_config
from dateutil.tz import tzlocal

PWFILE = "tests/testdata/passwords"
IMPORTFILE = "tests/testdata/import.oath"
IMPORTFILE_GPG = "tests/testdata/import.oath.asc"
IMPORTFILE2 = "tests/testdata/empty.oath"
IMPORTPSKC = "tests/testdata/pskc-aes.xml"
IMPORTPSKC_PASS = "tests/testdata/pskc-password.xml"
PSK_HEX = "12345678901234567890123456789012"
YUBICOFILE = "tests/testdata/yubico-oath.csv"
OTPKEY = "3132333435363738393031323334353637383930"
OTPKEY2 = "010fe88d31948c0c2e3258a4b0f7b11956a258ef"
OTPVALUES2 = ["551536", "703671", "316522", "413789"]
CERT = """-----BEGIN CERTIFICATE-----
MIIGXDCCBUSgAwIBAgITYwAAAA27DqXl0fVdOAAAAAAADTANBgkqhkiG9w0BAQsF
ADBCMRMwEQYKCZImiZPyLGQBGRYDb3JnMRkwFwYKCZImiZPyLGQBGRYJYXV0aC10
ZXN0MRAwDgYDVQQDEwdDQTJGMDAxMB4XDTE1MDIxMTE2NDE1M1oXDTE2MDIxMTE2
NDE1M1owgYExEzARBgoJkiaJk/IsZAEZFgNvcmcxGTAXBgoJkiaJk/IsZAEZFglh
dXRoLXRlc3QxDjAMBgNVBAMTBVVzZXJzMRowGAYDVQQDExFDb3JuZWxpdXMgS29l
bGJlbDEjMCEGCSqGSIb3DQEJARYUY29ybmVsaXVzQGJhbGZvby5uZXQwggEiMA0G
CSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQCN5xYqSoKhxKgywdWOjZTgOobPN5lN
DbSKQktdiG7asH0/Bzg8DIyd+k6wj5yncNhHKBhDJC/cAz3YAYY+KJj/tECLyt5V
AqZLuf3sTA/Ak/neHzXwrlo9PB67JxY4tgJcaR0Cml5oSx4ofRowOCrXv60Asfkl
+3lMRaNyEpQiSVdqIzGZAM1FIy0chwknMB8PfQhlC3v60rGiWoG65Rl5zuGl9lJC
nR990FGSIUW2GLCtI57QCCdBVHIBL+M0WNbdonk9qYSHm8ArFeoftsw2UxHQazM9
KftS7osJnQWOeNw+iIQIgZxLlyC9CBeKBCj3gIwLMEZRz6y951A9nngbAgMBAAGj
ggMJMIIDBTAOBgNVHQ8BAf8EBAMCBLAwHQYDVR0OBBYEFGFYluib3gs1BQQNB25A
FyEvQuoxMB8GA1UdIwQYMBaAFO9tVOusjflOf/y1lJuQ0YZej3vuMIHHBgNVHR8E
gb8wgbwwgbmggbaggbOGgbBsZGFwOi8vL0NOPUNBMkYwMDEsQ049Z2FuZGFsZixD
Tj1DRFAsQ049UHVibGljJTIwS2V5JTIwU2VydmljZXMsQ049U2VydmljZXMsQ049
Q29uZmlndXJhdGlvbixEQz1hdXRoLXRlc3QsREM9b3JnP2NlcnRpZmljYXRlUmV2
b2NhdGlvbkxpc3Q/YmFzZT9vYmplY3RDbGFzcz1jUkxEaXN0cmlidXRpb25Qb2lu
dDCBuwYIKwYBBQUHAQEEga4wgaswgagGCCsGAQUFBzAChoGbbGRhcDovLy9DTj1D
QTJGMDAxLENOPUFJQSxDTj1QdWJsaWMlMjBLZXklMjBTZXJ2aWNlcyxDTj1TZXJ2
aWNlcyxDTj1Db25maWd1cmF0aW9uLERDPWF1dGgtdGVzdCxEQz1vcmc/Y0FDZXJ0
aWZpY2F0ZT9iYXNlP29iamVjdENsYXNzPWNlcnRpZmljYXRpb25BdXRob3JpdHkw
PQYJKwYBBAGCNxUHBDAwLgYmKwYBBAGCNxUIheyJB4SuoT6EjYcBh+WGHoXd8y83
g7DpBYPZgFwCAWQCAQgwKQYDVR0lBCIwIAYKKwYBBAGCNxQCAgYIKwYBBQUHAwIG
CCsGAQUFBwMEMDUGCSsGAQQBgjcVCgQoMCYwDAYKKwYBBAGCNxQCAjAKBggrBgEF
BQcDAjAKBggrBgEFBQcDBDBEBgNVHREEPTA7oCMGCisGAQQBgjcUAgOgFQwTY29y
bnlAYXV0aC10ZXN0Lm9yZ4EUY29ybmVsaXVzQGJhbGZvby5uZXQwRAYJKoZIhvcN
AQkPBDcwNTAOBggqhkiG9w0DAgICAIAwDgYIKoZIhvcNAwQCAgCAMAcGBSsOAwIH
MAoGCCqGSIb3DQMHMA0GCSqGSIb3DQEBCwUAA4IBAQCVI9ULYQgLxOcDWAlWPE4g
ZRcbg65oCNdB0MBzTFhQZC/YFlSTNAGU2gUhnW+LoQ4N4sVnwxPbCRpsiA0ImqFU
hh/qcIV4JYthUGYdYkGjsc1YQjdLpYsg0GRUXTQHYjMQo6gvg1z/iMhzCCU8DbjT
DkTm/0JYVCt+vpvpigX/XWLWeHLHzPHFYAdBVAYgnwbTV4hgNIO98YRiMWsXOAIR
S/IreZ58alclwJJRIGTuOTKSCd+uE7QMALztDty7cjtpMANGrz1k/uUWg9T+UgQs
czZ68tF258iaWLPbsdRWqO160iy7eDSKWFFMR4HnfLHX/UPRSpBNGSHmvT1hbkUr
-----END CERTIFICATE-----"""

CAKEY = "cakey.pem"
CACERT = "cacert.pem"
OPENSSLCNF = "openssl.cnf"
WORKINGDIR = "tests/testdata/ca"
REQUEST = """-----BEGIN CERTIFICATE REQUEST-----
MIICmTCCAYECAQAwVDELMAkGA1UEBhMCREUxDzANBgNVBAgMBkhlc3NlbjEUMBIG
A1UECgwLcHJpdmFjeWlkZWExHjAcBgNVBAMMFXJlcXVlc3Rlci5sb2NhbGRvbWFp
bjCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAM2+FE/6zgE/QiIbHZyv
3ZLSf9tstz45Q0NrEwPxBfQHdLx2aSgLrxmO1/zjzcZY8sp/CG1T/AcCRCTGtDRM
jAT+Mw5A4iC6AnNa9/VPY27MxrbfVB03OX1RNiZfvdw/qItroq62ndYh599BuHoo
KmhIyqgt7eHpRl5acm20hDiHkf2UEQsohMbCLyr7Afk2egl10TOIPHNBW8i/lIlw
ofDAuS5QUx6xF2Rp9C2B4KkNDjLpulWKhfEbb0l5tH+Iww0+VIibPR84jATz7mpj
K/XG27SDqsR4QTp9S+HIPnHKG2FZ6sbEyjJeyem/EinmxsNj/qBV2nrxYJhNJu36
cC0CAwEAAaAAMA0GCSqGSIb3DQEBCwUAA4IBAQB7uJC6I1By0T29IZ0B1ue5YNxM
NDPbqCytRPMQ9awJ6niMMIQRS1YPhSFPWyEWrGKWAUvbn/lV0XHH7L/tvHg6HbC0
AjLc8qPH4Xqkb1WYV1GVJYr5qyEFS9QLZQLQDC2wk018B40MSwZWtsv14832mPu8
gP5WP+mj9LRgWCP1MdAR9pcNGd9pZMcCHQLxT76mc/eol4kb/6/U6yxBmzaff8eB
oysLynYXZkm0wFudTV04K0aKlMJTp/G96sJOtw1yqrkZSe0rNVcDs9vo+HAoMWO/
XZp8nprZvJuk6/QIRpadjRkv4NElZ2oNu6a8mtaO38xxnfQm4FEMbm5p+4tM
-----END CERTIFICATE REQUEST-----"""

class APITokenTestCase(MyTestCase):

    def _create_temp_token(self, serial):
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"serial": serial,
                                                 "genkey": 1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)

    def test_000_setup_realms(self):
        self.setUp_user_realms()

    def test_00_init_token(self):
        # hmac is now hotp.
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "hmac"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

        # missing parameter otpkey
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "hotp"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "hotp",
                                                 "otpkey": self.otpkey},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            self.assertTrue(result.get("status"), result)
            self.assertTrue(result.get("value"), result)
            self.assertTrue("value" in detail.get("googleurl"), detail)
            self.assertTrue("OATH" in detail.get("serial"), detail)

        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "hotp",
                                                 "otpkey": self.otpkey,
                                                 "genkey": 0},
                                           headers={'Authorization': self.at}):
                res = self.app.full_dispatch_request()
                data = json.loads(res.data)
                self.assertTrue(res.status_code == 200, res)
                result = data.get("result")
                detail = data.get("detail")
                self.assertTrue(result.get("status"), result)
                self.assertTrue(result.get("value"), result)
                self.assertTrue("value" in detail.get("googleurl"), detail)
                serial = detail.get("serial")
                self.assertTrue("OATH" in serial, detail)
        remove_token(serial)

        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "HOTP",
                                                 "otpkey": self.otpkey,
                                                 "pin": "1234",
                                                 "user": "cornelius",
                                                 "realm": self.realm1},
                                           headers={'Authorization': self.at}):
                res = self.app.full_dispatch_request()
                data = json.loads(res.data)
                self.assertTrue(res.status_code == 200, res)
                result = data.get("result")
                detail = data.get("detail")
                self.assertTrue(result.get("status"), result)
                self.assertTrue(result.get("value"), result)
                self.assertTrue("value" in detail.get("googleurl"), detail)
                serial = detail.get("serial")
                self.assertTrue("OATH" in serial, detail)
        remove_token(serial)

    def test_01_list_tokens(self):
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            tokenlist = result.get("value").get("tokens")
            count = result.get("value").get("count")
            next = result.get("value").get("next")
            prev = result.get("value").get("prev")
            self.assertTrue(result.get("status"), result)
            self.assertEqual(len(tokenlist), 1)
            self.assertTrue(count == 1, count)
            self.assertTrue(next is None, next)
            self.assertTrue(prev is None, prev)
            token0 = tokenlist[0]
            self.assertTrue(token0.get("username") == "", token0)
            self.assertTrue(token0.get("count") == 0, token0)
            self.assertTrue(token0.get("tokentype") == "hotp", token0)
            self.assertTrue(token0.get("tokentype") == "hotp", token0)
            self.assertTrue(token0.get("count_window") == 10, token0)
            self.assertTrue(token0.get("realms") == [], token0)
            self.assertTrue(token0.get("user_realm") == "", token0)

        # get assigned tokens
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           query_string=urlencode({
                                               "assigned": True}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            tokenlist = result.get("value").get("tokens")
            # NO token assigned, yet
            self.assertTrue(len(tokenlist) == 0, "{0!s}".format(tokenlist))

        # get unassigned tokens
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           query_string=urlencode({
                                               "assigned": False}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            tokenlist = result.get("value").get("tokens")
            self.assertTrue(len(tokenlist) == 1, len(tokenlist))

    def test_02_list_tokens_csv(self):
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           query_string=urlencode({"outform":
                                                                       "csv"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue("info" in res.data, res.data)
            self.assertTrue("username" in res.data, res.data)
            self.assertTrue("user_realm" in res.data, res.data)

    def test_03_list_tokens_in_one_realm(self):
        for serial in ["S1", "S2", "S3", "S4"]:
             with self.app.test_request_context('/token/init',
                                                method='POST',
                                                data={"type": "hotp",
                                                      "otpkey": self.otpkey,
                                                      "serial": serial},
                                                headers={'Authorization':
                                                             self.at}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)

        # tokens with realm
        for serial in ["R1", "R2"]:
            with self.app.test_request_context('/token/init', method='POST',
                                               data={"type": "hotp",
                                                     "otpkey": self.otpkey,
                                                     "serial": serial,
                                                     "realm": self.realm1},
                                               headers={'Authorization':
                                                            self.at}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)

        # list tokens of realm1
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           query_string=urlencode({
                                               "tokenrealm": self.realm1}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")
            tokenlist = result.get("value").get("tokens")
            count = result.get("value").get("count")
            next = result.get("value").get("next")
            prev = result.get("value").get("prev")
            self.assertTrue(len(tokenlist) == 2, res.data)
            self.assertTrue(count == 2, count)

    def test_04_assign_unassign_token(self):
        with self.app.test_request_context('/token/assign',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "serial": "S1",
                                                 "pin": "test"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") is True, result)

        # Assign the same token to another user will fail
        with self.app.test_request_context('/token/assign',
                                           method='POST',
                                           data={"user": "shadow",
                                                 "realm": self.realm1,
                                                 "serial": "S1"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

        # Now unassign the token
        with self.app.test_request_context('/token/unassign',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") is True, result)

        # Assign the same token to another user will success
        with self.app.test_request_context('/token/assign',
                                           method='POST',
                                           data={"user": "shadow",
                                                 "realm": self.realm1,
                                                 "serial": "S1"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") is True, result)

        # Unassign without any arguments will raise a ParameterError
        with self.app.test_request_context('/token/unassign',
                                           method='POST',
                                           data={},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

    def test_05_delete_token(self):
        self._create_temp_token("DToken")

        with self.app.test_request_context('/token/DToken',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") == 1, result)

        # Try to remove token, that does not exist returns a value=0
        with self.app.test_request_context('/token/DToken',
                                           method='DELETE',
                                           data={},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = json.loads(res.data).get("result")
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(result.get("value") == 0, result)

    def test_06_disable_enable_token(self):
        self._create_temp_token("EToken")

        # try to disable a token with no parameters
        with self.app.test_request_context('/token/disable',
                                           method='POST',
                                           data={},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

        # disable token
        with self.app.test_request_context('/token/disable/EToken',
                                           method='POST',
                                           data={},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") == 1, result)

        # disable a disabled token will not count, so the value will be 0
        with self.app.test_request_context('/token/disable',
                                           method='POST',
                                           data={"serial": "EToken"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") == 0, result)

        # enable the token again
        with self.app.test_request_context('/token/enable/EToken',
                                           method='POST',
                                           data={},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") == 1, result)

        # try to enable an already enabled token returns value=0
        with self.app.test_request_context('/token/enable',
                                           method='POST',
                                           data={"serial": "EToken"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") == 0, result)

    def test_07_reset_failcounter(self):
        serial = "RToken"
        self._create_temp_token(serial)

        # Set the failcounter to 12
        tokenobject_list = get_tokens(serial=serial)
        tokenobject_list[0].token.failcount = 12
        tokenobject_list[0].save()

        # reset the failcounter
        with self.app.test_request_context('/token/reset/RToken',
                                           method='POST',
                                           data={},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") == 1, result)

        # test the failcount
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           query_string=urlencode({"serial":
                                                                       serial}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            token = value.get("tokens")[0]
            self.assertTrue(value.get("count") == 1, value)
            self.assertTrue(token.get("failcount") == 0, token)

        # reset failcount again, will again return value=1
        with self.app.test_request_context('/token/reset',
                                           method='POST',
                                           data={"serial": serial},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") == 1, result)

    def test_07_resync(self):

        with self.app.test_request_context('/token/init', method="POST",
                                           data={"serial": "Resync01",
                                                 "otpkey": self.otpkey},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") == 1, result)

            """
                                             Truncated
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

        # Resync does not work with NON-consecutive values
        with self.app.test_request_context('/token/resync/Resync01',
                                            method="POST",
                                            data={"otp1": 287082,
                                                  "otp2": 969429},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") is False, result)

        # Successful resync with consecutive values
        with self.app.test_request_context('/token/resync',
                                            method="POST",
                                            data={"serial": "Resync01",
                                                  "otp1": 359152,
                                                  "otp2": 969429},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") is True, result)

        # Get the OTP token and inspect the counter
        with self.app.test_request_context('/token/',
                                            method="GET",
                                            query_string=urlencode({"serial": "Resync01"}),
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            token = value.get("tokens")[0]
            self.assertTrue(token.get("count") == 4, result)

        # Authenticate a user
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username":
                                                     "selfservice@realm1",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("status"), res.data)
            # In self.at_user we store the user token
            self.at_user = result.get("value").get("token")

        # The user fails to resync the token, since it does not belong to him
        with self.app.test_request_context('/token/resync',
                                            method="POST",
                                            data={"serial": "Resync01",
                                                  "otp1": 254676,
                                                  "otp2": 287922},
                                            headers={'Authorization':
                                                         self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") is False, result)

        # assign the token to the user selfservice@realm1.
        with self.app.test_request_context('/token/assign',
                                            method="POST",
                                            data={"serial": "Resync01",
                                                  "user": "selfservice@realm1"},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("value"), True)

        # let the user resync the token
        with self.app.test_request_context('/token/resync',
                                            method="POST",
                                            data={"serial": "Resync01",
                                                  "otp1": 254676,
                                                  "otp2": 287922},
                                            headers={'Authorization':
                                                         self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") is True, result)


    def test_08_setpin(self):
        self._create_temp_token("PToken")
        # Set one PIN of the token
        with self.app.test_request_context('/token/setpin',
                                            method="POST",
                                            data={"serial": "PToken",
                                                  "userpin": "test"},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") == 1, result)

        # Set both PINs of the token
        with self.app.test_request_context('/token/setpin/PToken',
                                            method="POST",
                                            data={"userpin": "test",
                                                  "sopin": "topsecret"},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") == 2, result)

        # set a pin
        with self.app.test_request_context('/token/setpin/PToken',
                                            method="POST",
                                            data={"otppin": "test"},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") == 1, result)

        # set an empty pin
        with self.app.test_request_context('/token/setpin/PToken',
                                            method="POST",
                                            data={"otppin": ""},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") == 1, result)

    def test_09_set_token_attributes(self):
        self._create_temp_token("SET001")
        # Set some things
        with self.app.test_request_context('/token/setpin',
                                            method="POST",
                                            data={"serial": "SET001",
                                                  "otppin": "test"},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") == 1, result)


        # Set all other values
        with self.app.test_request_context('/token/set/SET001',
                                            method="POST",
                                            data={"count_auth_max": 17,
                                                  "count_auth_success_max": 8,
                                                  "hashlib": "sha2",
                                                  "count_window": 11,
                                                  "sync_window": 999,
                                                  "max_failcount": 15,
                                                  "description": "Some Token",
                                                  "validity_period_start":
                                                      "2014-05-22T22:00+0200",
                                                  "validity_period_end":
                                                      "2014-05-22T23:00+0200"},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") == 9, result)

        # check the values
        with self.app.test_request_context('/token/',
                                           method="GET",
                                           query_string=urlencode(
                                                   {"serial": "SET001"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            token = value.get("tokens")[0]
            self.assertTrue(value.get("count") == 1, result)

            self.assertTrue(token.get("count_window") == 11, token)
            self.assertTrue(token.get("sync_window") == 999, token)
            self.assertTrue(token.get("maxfail") == 15, token)
            self.assertTrue(token.get("description") == "Some Token", token)
            tokeninfo = token.get("info")
            self.assertTrue(tokeninfo.get("hashlib") == "sha2", tokeninfo)
            self.assertTrue(tokeninfo.get("count_auth_max") == "17",
                            tokeninfo)
            self.assertTrue(tokeninfo.get("count_auth_success_max") == "8",
                            tokeninfo)
            self.assertEqual(tokeninfo.get("validity_period_start"),
                             "2014-05-22T22:00+0200")
            self.assertEqual(tokeninfo.get("validity_period_end"),
                             "2014-05-22T23:00+0200")

    def test_10_set_token_realms(self):
        self._create_temp_token("REALM001")

        with self.app.test_request_context('/token/realm/REALM001',
                                            method="POST",
                                            data={"realms": "realm1, realm2"},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertTrue(value is True, result)

        with self.app.test_request_context('/token/',
                                            method="GET",
                                            query_string=urlencode({"serial": "REALM001"}),
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            token = value.get("tokens")[0]
            self.assertTrue(token.get("realms") == ["realm1"], token)

    def test_11_load_tokens(self):
        # Load OATH CSV
        with self.app.test_request_context('/token/load/import.oath',
                                            method="POST",
                                            data={"type": "oathcsv",
                                                  "file": (IMPORTFILE,
                                                           "import.oath")},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertTrue(value == 3, result)

        # Load GPG encrypted OATH CSV
        with self.app.test_request_context('/token/load/import.oath.asc',
                                           method="POST",
                                           data={"type": "oathcsv",
                                                 "file": (IMPORTFILE_GPG,
                                                          "import.oath.asc")},
                                           headers={
                                               'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertTrue(value == 3, result)

        # Load yubico.csv
        with self.app.test_request_context('/token/load/yubico.csv',
                                            method="POST",
                                            data={"type": "yubikeycsv",
                                                  "tokenrealms": self.realm1,
                                                  "file": (YUBICOFILE,
                                                           "yubico.csv")},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertTrue(value == 3, result)

        # check if the token was put into self.realm1
        tokenobject_list = get_tokens(serial="UBOM508327_X")
        self.assertEqual(len(tokenobject_list), 1)
        token = tokenobject_list[0]
        self.assertEqual(token.token.realm_list[0].realm.name, self.realm1)

        # Try to load empty file
        with self.app.test_request_context('/token/load/empty.oath',
                                            method="POST",
                                            data={"type": "oathcsv",
                                                  "file": (IMPORTFILE2,
                                                           "empty.oath")},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

        # Try to load unknown file type
        with self.app.test_request_context('/token/load/import.oath',
                                            method="POST",
                                            data={"type": "unknown",
                                                  "file": (IMPORTFILE,
                                                           "import.oath")},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

        # Load PSKC file, encrypted PSK
        with self.app.test_request_context('/token/load/pskc-aes.xml',
                                            method="POST",
                                            data={"type": "pskc",
                                                  "psk": PSK_HEX,
                                                  "file": (IMPORTPSKC,
                                                           "pskc-aes.xml")},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertTrue(value == 1, result)

        # Load PSKC file, encrypted Password
        with self.app.test_request_context('/token/load/pskc-password.xml',
                                            method="POST",
                                            data={"type": "pskc",
                                                  "password": "qwerty",
                                                  "file": (IMPORTPSKC_PASS,
                                                           "pskc-password.xml")},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertTrue(value == 1, result)

    def test_12_copy_token(self):
        self._create_temp_token("FROM001")
        self._create_temp_token("TO001")
        with self.app.test_request_context('/token/assign',
                                            method="POST",
                                            data={"serial": "FROM001",
                                                  "user": "cornelius",
                                                  "realm": self.realm1},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertTrue(value is True, result)

        with self.app.test_request_context('/token/setpin',
                                            method="POST",
                                            data={"serial": "FROM001",
                                                  "otppin": "test"},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertTrue(value == 1, result)

        # copy the PIN
        with self.app.test_request_context('/token/copypin',
                                            method="POST",
                                            data={"from": "FROM001",
                                                  "to": "TO001"},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertTrue(value is True, result)

        # copy the user
        with self.app.test_request_context('/token/copyuser',
                                            method="POST",
                                            data={"from": "FROM001",
                                                  "to": "TO001"},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertTrue(value is True, result)

        # check in the database
        tokenobject_list = get_tokens(serial="TO001")
        token = tokenobject_list[0]
        # check the user
        self.assertTrue(token.token.user_id == "1000", token.token)
        # check if the TO001 has a pin
        self.assertTrue(len(token.token.pin_hash) == 64,
                        len(token.token.pin_hash))

    def test_13_lost_token(self):
        self._create_temp_token("LOST001")

        # call lost token for a token, that is not assigned.
        # THis will create an exception
        with self.app.test_request_context('/token/lost/LOST001',
                                            method="POST",
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

        # assign the token
        with self.app.test_request_context('/token/assign',
                                            method="POST",
                                            data={"serial": "LOST001",
                                                  "user": "cornelius",
                                                  "realm": self.realm1},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertTrue(value is True, result)

        with self.app.test_request_context('/token/lost/LOST001',
                                            method="POST",
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertTrue("end_date" in value, value)
            self.assertTrue(value.get("serial") == "lostLOST001", value)

        # check if the user cornelius now owns the token lostLOST001
        tokenobject_list = get_tokens(user=User("cornelius",
                                                realm=self.realm1),
                                      serial="lostLOST001")
        self.assertTrue(len(tokenobject_list) == 1, tokenobject_list)

    def test_14_get_serial_by_otp(self):
        self._create_temp_token("T1")
        self._create_temp_token("T2")
        self._create_temp_token("T3")
        init_token({"serial": "GETSERIAL",
                    "otpkey": OTPKEY})

        # Only get the number of tokens, which would be searched: 28
        with self.app.test_request_context('/token/getserial/162583?count=1',
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertEqual(value.get("count"), 28)
            self.assertEqual(value.get("serial"), None)

        # multiple tokens are matching!
        with self.app.test_request_context('/token/getserial/162583',
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

        init_token({"serial": "GETSERIAL2",
                    "otpkey": OTPKEY2})

        with self.app.test_request_context('/token/getserial/316522',
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertEqual(value.get("serial"), "GETSERIAL2")

        # If one OTP values was found, it can not be used again
        with self.app.test_request_context('/token/getserial/316522',
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertEqual(value.get("serial"), None)


        # Will not find an assigned token
        with self.app.test_request_context('/token/getserial/413789'
                                           '?assigned=1',
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertNotEqual(value.get("serial"), "GETSERIAL2")

        # Will find a substr
        with self.app.test_request_context('/token/getserial/413789'
                                           '?unassigned=1&string=SERIAL',
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertEqual(value.get("serial"), "GETSERIAL2")

    def test_15_registration_code(self):
        # Test the registration code token
        # create the registration code token
        with self.app.test_request_context('/token/init',
                                           data={"type": "registration",
                                                 "serial": "reg1",
                                                 "user": "cornelius"},
                                           method="POST",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value"))
            detail = json.loads(res.data).get("detail")
            registrationcode = detail.get("registrationcode")

        # check password
        with self.app.test_request_context('/validate/check',
                                           data={"user": "cornelius",
                                                 "pass": registrationcode},
                                           method="POST"):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value"))

        # check password again. THe second time it will fail, since the token
        # does not exist anymore.
        with self.app.test_request_context('/validate/check',
                                           data={"user": "cornelius",
                                                 "pass": registrationcode},
                                           method="POST"):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertFalse(result.get("value"))

    def test_16_totp_timestep(self):
        # Test the timestep of the token
        for timestep in ["30", "60"]:
            with self.app.test_request_context('/token/init',
                                               data={"type": "totp",
                                                     "serial": "totp{0!s}".format(
                                                             timestep),
                                                     "timeStep": timestep,
                                                     "genkey": "1"},
                                               method="POST",
                                               headers={'Authorization': self.at}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = json.loads(res.data).get("result")
                self.assertTrue(result.get("value"))
                detail = json.loads(res.data).get("detail")

            token = get_tokens(serial="totp{0!s}".format(timestep))[0]
            self.assertEqual(token.timestep, int(timestep))

    def test_17_enroll_certificate(self):
        cwd = os.getcwd()
        # setup ca connector
        r = save_caconnector({"cakey": CAKEY,
                              "cacert": CACERT,
                              "type": "local",
                              "caconnector": "localCA",
                              "openssl.cnf": OPENSSLCNF,
                              "CSRDir": "",
                              "CertificateDir": "",
                              "WorkingDir": cwd + "/" + WORKINGDIR})

        with self.app.test_request_context('/token/init',
                                           data={"type": "certificate",
                                                 "request": REQUEST,
                                                 "ca": "localCA"},
                                           method="POST",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value"))
            detail = json.loads(res.data).get("detail")
            certificate = detail.get("certificate")
            self.assertTrue("-----BEGIN CERTIFICATE-----" in certificate)

    def test_18_revoke_token(self):
        self._create_temp_token("RevToken")

        # revoke token
        with self.app.test_request_context('/token/revoke/RevToken',
                                           method='POST',
                                           data={},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") == 1, result)

        # Try to enable the revoked token
        with self.app.test_request_context('/token/enable/RevToken',
                                           method='POST',
                                           data={},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

    def test_19_get_challenges(self):
        set_policy("chalresp", scope=SCOPE.AUTHZ,
        action="{0!s}=hotp".format(ACTION.CHALLENGERESPONSE))
        token = init_token({"genkey": 1, "serial": "CHAL1", "pin": "pin"})
        serial = token.token.serial
        r = check_serial_pass(serial, "pin")
        # The OTP PIN is correct
        self.assertEqual(r[0], False)
        self.assertEqual(r[1].get("message"), "please enter otp: ")
        transaction_id = r[1].get("transaction_id")

        with self.app.test_request_context('/token/challenges/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertEqual(value.get("count"), 1)
            challenges = value.get("challenges")
            self.assertEqual(challenges[0].get("transaction_id"),
                             transaction_id)

        # There is one challenge for token CHAL1
        with self.app.test_request_context('/token/challenges/CHAL1',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertEqual(value.get("count"), 1)
            challenges = value.get("challenges")
            self.assertEqual(challenges[0].get("transaction_id"),
                             transaction_id)

        # There is no challenge for token CHAL2
        with self.app.test_request_context('/token/challenges/CHAL2',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            self.assertEqual(value.get("count"), 0)

        delete_policy("chalresp")

    def test_20_init_yubikey(self):
        # save yubikey.prefix
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={
                                               "type": "yubikey",
                                               "serial": "yk1",
                                               "otpkey": self.otpkey,
                                               "yubikey.prefix": "vv123456"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("status"), result)
            self.assertTrue(result.get("value"), result)

        tokens = get_tokens(serial="yk1")
        self.assertEqual(tokens[0].get_tokeninfo("yubikey.prefix"), "vv123456")

    def test_21_time_policies(self):
        # Here we test, if an admin policy does not match in time,
        # it still used to evaluate, that admin policies are defined at all
        set_policy(name="admin_time", scope=SCOPE.ADMIN,
                   action="enrollSPASS",
                   time="Sun: 0-23:59")
        tn = datetime.datetime.now()
        dow = tn.isoweekday()
        P = PolicyClass()
        all_admin_policies = P.get_policies(all_times=True)
        self.assertEqual(len(all_admin_policies), 1)
        self.assertEqual(len(P.policies), 1)

        if dow in [7]:
            # Only on sunday the admin is allowed to enroll a SPASS token. On
            # all other days this will raise an exception
            with self.app.test_request_context(
                    '/token/init',
                    method='POST',
                    data={"type": "spass"},
                    headers={'Authorization': self.at}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
        else:
            # On other days enrolling a spass token will trigger an error,
            # since the admin has no rights at all. Only on sunday.
            with self.app.test_request_context(
                    '/token/init',
                    method='POST',
                    data={"type": "spass"},
                    headers={'Authorization': self.at}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 403, res)

        delete_policy("admin_time")

    def test_22_delete_token_in_foreign_realm(self):
        # Check if a realm admin can not delete a token in another realm
        # Admin is only allowed to delete tokens in "testrealm"
        set_policy("deleteToken", scope=SCOPE.ADMIN,
                   action="delete",
                   user="testadmin",
                   realm="testrealm"
                   )
        r = init_token({"type": "SPASS", "serial": "SP001"},
                       user=User("cornelius", self.realm1))

        # Now testadmin tries to delete a token from realm1, which he can not
        #  access.
        with self.app.test_request_context('/token/SP001',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 403, res)

        remove_token("SP001")
        delete_policy("deleteToken")

    def test_23_change_pin_on_first_use(self):

        set_policy("firstuse", scope=SCOPE.ENROLL,
                   action=ACTION.CHANGE_PIN_FIRST_USE)

        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data = {"genkey": 1,
                                                   "pin": "123456"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")

            serial = detail.get("serial")
            token = get_tokens(serial=serial)[0]
            ti = token.get_tokeninfo("next_pin_change")
            ndate = datetime.datetime.now(tzlocal()).strftime(DATE_FORMAT)
            self.assertEqual(ti, ndate)

        # If the administrator sets a PIN of the user, the next_pin_change
        # must also be created!

        token = init_token({"serial": "SP001", "type": "spass", "pin":
            "123456"})
        ti = token.get_tokeninfo("next_pin_change")
        self.assertEqual(ti, None)
        # Now we set the PIN
        with self.app.test_request_context('/token/setpin/SP001',
                                           method='POST',
                                           data={"otppin": "1234"},
                                           headers={'Authorization': self.at}):

            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            detail = json.loads(res.data).get("detail")

            serial = "SP001"
            token = get_tokens(serial=serial)[0]
            ti = token.get_tokeninfo("next_pin_change")
            ndate = datetime.datetime.now(tzlocal()).strftime(DATE_FORMAT)
            self.assertEqual(ti, ndate)

        delete_policy("firstuse")

    def test_24_modify_tokeninfo(self):
        self._create_temp_token("INF001")
        # Set two tokeninfo values
        with self.app.test_request_context('/token/info/INF001/key1',
                                            method="POST",
                                            data={"value": "value 1"},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value"), result)
        with self.app.test_request_context('/token/info/INF001/key2',
                                            method="POST",
                                            data={"value": "value 2"},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value"), result)

        with self.app.test_request_context('/token/',
                                           method="GET",
                                           query_string=urlencode(
                                                   {"serial": "INF001"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            token = value.get("tokens")[0]
            self.assertTrue(value.get("count") == 1, result)

            tokeninfo = token.get("info")
            self.assertDictContainsSubset({'key1': 'value 1', 'key2': 'value 2'}, tokeninfo)

        # Overwrite an existing tokeninfo value
        with self.app.test_request_context('/token/info/INF001/key1',
                                            method="POST",
                                            data={"value": 'value 1 new'},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value"), result)

        with self.app.test_request_context('/token/',
                                           method="GET",
                                           query_string=urlencode(
                                                   {"serial": "INF001"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            token = value.get("tokens")[0]
            self.assertTrue(value.get("count") == 1, result)

            tokeninfo = token.get("info")
            self.assertDictContainsSubset({'key1': 'value 1 new', 'key2': 'value 2'}, tokeninfo)

        # Delete an existing tokeninfo value
        with self.app.test_request_context('/token/info/INF001/key1',
                                           method="DELETE",
                                           headers={'Authorization': self.at}):
           res = self.app.full_dispatch_request()
           self.assertTrue(res.status_code == 200, res)
           result = json.loads(res.data).get("result")
           self.assertTrue(result.get("value"), result)

        # Delete a non-existing tokeninfo value
        with self.app.test_request_context('/token/info/INF001/key1',
                                            method="DELETE",
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value"), result)

        # Try to delete with an unknown serial
        with self.app.test_request_context('/token/info/UNKNOWN/key1',
                                            method="DELETE",
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value") == False, result)

        # Check that the tokeninfo is correct
        with self.app.test_request_context('/token/',
                                           method="GET",
                                           query_string=urlencode(
                                               {"serial": "INF001"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            value = result.get("value")
            token = value.get("tokens")[0]
            self.assertTrue(value.get("count") == 1, result)

            tokeninfo = token.get("info")
            self.assertDictContainsSubset({'key2': 'value 2'}, tokeninfo)
            self.assertNotIn('key1', tokeninfo)

    def test_25_user_init_defaults(self):
        self.authenticate_selfservice_user()
        # Now this user is authenticated
        # selfservice@realm1

        # Create policy for sha256
        set_policy(name="init_details",
                   scope=SCOPE.USER,
                   action="totp_otplen=8,totp_hashlib=sha256,"
                          "totp_timestep=60,enrollTOTP")

        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={
                                               "type": "totp",
                                               "totp.hashlib": "sha1",
                                               "hashlib": "sha1",
                                               "genkey": 1,
                                               "user": "selfservice",
                                               "realm": "realm1"},
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value"))
            detail = json.loads(res.data).get("detail")
            googleurl = detail.get("googleurl")
            self.assertTrue("sha256" in googleurl.get("value"))
            serial = detail.get("serial")
            token = get_tokens(serial=serial)[0]
            self.assertEqual(token.hashlib, "sha256")
            self.assertEqual(token.token.otplen, 8)

        delete_policy("init_details")
        remove_token(serial)

        # Set OTP len using the system wide default
        set_privacyidea_config("DefaultOtpLen", 8)
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={
                                               "type": "totp",
                                               "totp.hashlib": "sha1",
                                               "hashlib": "sha1",
                                               "genkey": 1,
                                               "user": "selfservice",
                                               "realm": "realm1"},
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value"))
            detail = json.loads(res.data).get("detail")
            serial = detail.get("serial")
            token = get_tokens(serial=serial)[0]
            self.assertEqual(token.token.otplen, 8)

        remove_token(serial)

        # override the DefaultOtpLen
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={
                                               "type": "totp",
                                               "otplen": 6,
                                               "totp.hashlib": "sha1",
                                               "hashlib": "sha1",
                                               "genkey": 1,
                                               "user": "selfservice",
                                               "realm": "realm1"},
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("value"))
            detail = json.loads(res.data).get("detail")
            serial = detail.get("serial")
            token = get_tokens(serial=serial)[0]
            self.assertEqual(token.token.otplen, 6)

        remove_token(serial)
        delete_privacyidea_config("DefaultOtpLen")

    def test_26_supply_key_size(self):
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "HOTP",
                                                 "genkey": '1',
                                                 "pin": "1234",
                                                 "user": "cornelius",
                                                 "keysize": "42",
                                                 "realm": self.realm1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            data = json.loads(res.data)
            self.assertTrue(res.status_code == 200, res)
            result = data.get("result")
            detail = data.get("detail")
            self.assertTrue(result.get("status"), result)
            self.assertTrue(result.get("value"), result)
            self.assertTrue("value" in detail.get("googleurl"), detail)
            serial = detail.get("serial")
            self.assertTrue("OATH" in serial, detail)
            seed_url = detail.get("otpkey").get("value")
            self.assertEqual(seed_url[:len('seed://')], 'seed://')
            seed = seed_url[len('seed://'):]
            self.assertEqual(len(seed.decode('hex')), 42)
        remove_token(serial)

    def test_27_fail_to_assign_empty_serial(self):
        with self.app.test_request_context('/token/assign',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "serial": "",
                                                 "pin": "test"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)
            result = json.loads(res.data).get("result")
            self.assertEqual(result.get("status"), False)
            self.assertEqual(result.get("error").get("code"), 905)