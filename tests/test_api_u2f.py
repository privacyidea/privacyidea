from .base import MyTestCase
import json
import os
from privacyidea.lib.error import (TokenAdminError, ParameterError)
from privacyidea.lib.token import get_tokens, init_token
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

class APIU2fTestCase(MyTestCase):

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

    def test_01_register_u2f(self):
        # step 1
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "u2f"},
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

        regData = "asdf"
        clientData = "asdf"
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"serial": serial,
                                                 "type": "u2f",
                                                 "regdata": regData,
                                                 "clientdata": clientData},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            response = json.loads(res.data)
            result = response.get("result")
            details = response.get("detail")
            self.assertEqual(result.get("value"), True)
