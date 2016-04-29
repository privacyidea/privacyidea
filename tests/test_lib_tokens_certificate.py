"""
This test file tests the lib.tokens.certificatetoken
"""

from .base import MyTestCase
from privacyidea.lib.tokens.certificatetoken import CertificateTokenClass
from privacyidea.models import Token
from privacyidea.lib.caconnector import save_caconnector
from privacyidea.lib.token import get_tokens
from privacyidea.lib.error import ParameterError
import os
from OpenSSL import crypto


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


class CertificateTokenTestCase(MyTestCase):

    serial1 = "CRT0001"
    serial2 = "CRT0002"
    serial3 = "CRT0003"

    def test_01_create_token_from_certificate(self):
        db_token = Token(self.serial1, tokentype="certificate")
        db_token.save()
        token = CertificateTokenClass(db_token)

        # just upload a ready certificate
        token.update({"certificate": CERT})
        self.assertTrue(token.token.serial == self.serial1, token)
        self.assertTrue(token.token.tokentype == "certificate",
                        token.token.tokentype)
        self.assertTrue(token.type == "certificate", token)
        class_prefix = token.get_class_prefix()
        self.assertTrue(class_prefix == "CRT", class_prefix)
        self.assertEqual(token.get_class_type(), "certificate")

        detail = token.get_init_detail()
        self.assertEqual(detail.get("certificate"), CERT)

    def test_02_create_token_from_request(self):
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

        db_token = Token(self.serial2, tokentype="certificate")
        db_token.save()
        token = CertificateTokenClass(db_token)

        # just upload a ready certificate
        token.update({"ca": "localCA",
                      "request": REQUEST})
        self.assertTrue(token.token.serial == self.serial2, token)
        self.assertTrue(token.token.tokentype == "certificate",
                        token.token.tokentype)
        self.assertTrue(token.type == "certificate", token)
        class_prefix = token.get_class_prefix()
        self.assertTrue(class_prefix == "CRT", class_prefix)
        self.assertTrue(token.get_class_type() == "certificate", token)

        detail = token.get_init_detail()
        certificate = detail.get("certificate")
        # At each testrun, the certificate might get another serial number!
        x509obj = crypto.load_certificate(crypto.FILETYPE_PEM, certificate)
        self.assertEqual("{0!r}".format(x509obj.get_issuer()),
                         "<X509Name object '/C=DE/ST=Hessen"
                         "/O=privacyidea/CN=CA001'>")
        self.assertEqual("{0!r}".format(x509obj.get_subject()),
                         "<X509Name object '/C=DE/ST=Hessen"
                         "/O=privacyidea/CN=requester.localdomain'>")

        # Test, if the certificate is also completely stored in the tokeninfo
        # and if we can retrieve it from the tokeninfo
        token = get_tokens(serial=self.serial2)[0]
        certificate = token.get_tokeninfo("certificate")
        x509obj = crypto.load_certificate(crypto.FILETYPE_PEM, certificate)
        self.assertEqual("{0!r}".format(x509obj.get_issuer()),
                         "<X509Name object '/C=DE/ST=Hessen"
                         "/O=privacyidea/CN=CA001'>")
        self.assertEqual("{0!r}".format(x509obj.get_subject()),
                         "<X509Name object '/C=DE/ST=Hessen"
                         "/O=privacyidea/CN=requester.localdomain'>")


    def test_03_class_methods(self):
        db_token = Token.query.filter(Token.serial == self.serial1).first()
        token = CertificateTokenClass(db_token)

        info = token.get_class_info()
        self.assertTrue(info.get("title") == "Certificate Token", info)

        info = token.get_class_info("title")
        self.assertTrue(info == "Certificate Token", info)

    def test_04_create_token_on_server(self):
        self.setUp_user_realms()
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

        db_token = Token(self.serial3, tokentype="certificate")
        db_token.save()
        token = CertificateTokenClass(db_token)

        # missing user
        self.assertRaises(ParameterError,
                          token.update, {"ca": "localCA","genkey": 1})

        token.update({"ca": "localCA", "genkey": 1,
                      "user": "cornelius"})

        self.assertEqual(token.token.serial, self.serial3)
        self.assertEqual(token.token.tokentype, "certificate")
        self.assertEqual(token.type, "certificate")

        detail = token.get_init_detail()
        certificate = detail.get("certificate")
        # At each testrun, the certificate might get another serial number!
        x509obj = crypto.load_certificate(crypto.FILETYPE_PEM, certificate)
        self.assertEqual("{0!r}".format(x509obj.get_issuer()),
                         "<X509Name object '/C=DE/ST=Hessen"
                         "/O=privacyidea/CN=CA001'>")
        self.assertEqual("{0!r}".format(x509obj.get_subject()),
                         "<X509Name object '/OU=realm1/CN=cornelius/emailAddress=user@localhost.localdomain'>")

        # Test, if the certificate is also completely stored in the tokeninfo
        # and if we can retrieve it from the tokeninfo
        token = get_tokens(serial=self.serial3)[0]
        certificate = token.get_tokeninfo("certificate")
        x509obj = crypto.load_certificate(crypto.FILETYPE_PEM, certificate)
        self.assertEqual("{0!r}".format(x509obj.get_issuer()),
                         "<X509Name object '/C=DE/ST=Hessen"
                         "/O=privacyidea/CN=CA001'>")
        self.assertEqual("{0!r}".format(x509obj.get_subject()),
                         "<X509Name object '/OU=realm1/CN=cornelius/emailAddress=user@localhost.localdomain'>")

        privatekey = token.get_tokeninfo("privatekey")
        self.assertTrue(privatekey.startswith("-----BEGIN PRIVATE KEY-----"))

        # check for pkcs12
        self.assertTrue(detail.get("pkcs12"))

