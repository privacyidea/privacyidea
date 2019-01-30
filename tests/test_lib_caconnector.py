"""
This test file tests the lib.caconnector.py and
lib.caconnectors.localca.py
"""
from .base import MyTestCase
import os
import six
import shutil
from io import StringIO
from mock import patch
from privacyidea.lib.caconnectors.localca import LocalCAConnector, ATTR
from OpenSSL import crypto
from privacyidea.lib.utils import int_to_hex, to_unicode
from privacyidea.lib.error import CAError
from privacyidea.lib.caconnector import (get_caconnector_list,
                                         get_caconnector_class,
                                         get_caconnector_config,
                                         get_caconnector_config_description,
                                         get_caconnector_object,
                                         get_caconnector_type,
                                         get_caconnector_types,
                                         save_caconnector, delete_caconnector)

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

REQUEST_USER = """-----BEGIN CERTIFICATE REQUEST-----
MIICjDCCAXQCAQAwRzELMAkGA1UEBhMCREUxDzANBgNVBAgMBkhlc3NlbjEUMBIG
A1UECgwLcHJpdmFjeWlkZWExETAPBgNVBAMMCHVzZXJjZXJ0MIIBIjANBgkqhkiG
9w0BAQEFAAOCAQ8AMIIBCgKCAQEA3C/RXymX1HzDU8gwvUtncCwka7he6yF6SBJW
fIFcSHW2aOv28phOUFHRf2xz8wqnrr5IXuXW4dkqfDJuTv0I9lpUSSNzw7kHGNHv
s6z4ityUlqSQOo503+YNNxu9W7clGlY52m+Rql4cdPP5fBQBgxJldse7/jZblely
ZYPtPpgwcfqH3aM2WjADLibgYdG/Aj+2Bh9KiSgcXKL/Tr6U5ozg2oLxnSkySDBz
tAT2Qh6+9+IyMic8nYkvcD6Fmm9cxQnAjDIvciLJ0pUftqxyYHK3gk1rzlvjANDS
L1jG4BDlUcpNOy7mfquE1lbxkzWgk2QmgXUvkbUWBjgL28wtBwIDAQABoAAwDQYJ
KoZIhvcNAQELBQADggEBADPFLT1HVbYtVFsthnBj/UX3qs3NoLE9W5llV9Z5JEsE
yQgANX3hiL6m3uVyPBOZVBqCKO8ZC5VzO99zpQ+3BaWQUCuxXbmjJrA8kzIwmRL6
yJz7YpmbQzOPSlbmFguiVs8Mhhfo6NB2oMx0uV6mCMnoX1thfkIOz6+AKTIoWexV
6/X2VXR1zEPxMCF3eqAClleF+RbKcTXfLSoxaRAdDtuUOERqu9EUpIFEsGFwu/zS
y/hmHFGvyDotqmmdxUeXpw2qW882mWZdLtb3TQorvknrOjhtcRZ4/c5X5f4Fv73K
PwFuUcQ1S7UsaJqyysFSx/SA36F0zEjSwbqJwQAKlzA=
-----END CERTIFICATE REQUEST-----"""

SPKAC = "SPKAC=MIICQDCCASgwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggE" \
        "KAoIBAQDSgYkgUUgPc/QRMiTVHxz9XPW25sXwUoHc0q9mSnyTMWFcr" \
        "9FtBnADYHxyDIjdSc2eAmzSWtdTD" \
        "/PavmlktQ8MAOOzUEejs5u6E1DWWFpLqzngEcoKJ2cDeCJmbZIeG1xJru" \
        "Zr0Y47nQbTxqxNU0MQq+iWwYeCl5mPINOZEjcxhOGK/ykDXyKQPn+b4CDBr" \
        "dyuTDkaMZYXAoyy2bQNIBKbfYZU/TP9wSpiRvhgls9uAW8i3xNH55fsBXIjo2" \
        "L4+u+snHLwN8svN8+QqCdRhsbXeAiPfiWiFXCi+xy2FV6gl4uBTAkoiic7lLxx2" \
        "1txN5orFuBvtcn1S08gumXPr62tAgMBAAEWADANBgkqhkiG9w0BAQQFAAOCAQEAe" \
        "nI3N4LdQF3R0Jn+pjldo65K4BERTnfhtcyYH4nCTNKvvwSvTv9eBvuJ6ZWqIy9aRFX" \
        "Zngl4ZFyrqZYNufPPdlMVMwbJ4L6iphkcQjzCbrvQDvzVwH4SOGmuIHYyjrIzmg" \
        "P+e7XvXVr0Vl6zMHWalGGSNPWwrSj6FXw6G7qm7Qd9CYvGDxA0qxo6tL/KCjv" \
        "q+4qNB1rfy9Gy3xBr3ZfIa15/bLSvO9dPx6cW8Jv6Vb8w6UizwhGMfh55KOc1wVf" \
        "ofEpwbLM9PyvVAoszL9JpQHIs6S0zZ5bwt2eUjzc7GnzxxIVlR7/xIQiizzbW22" \
        "rmtBFA3aIp5RExiEpvBD88hg==\n" \
        "CN=Steve Test\n" \
        "emailAddress=steve@openssl.org"


class CAConnectorTestCase(MyTestCase):
    """
    Test the CA connector lib functions
    """
    def test_01_base_functions(self):
        types = get_caconnector_types()
        self.assertEqual(types, ["local"])

        calist = get_caconnector_list()
        self.assertEqual(calist, [])

        connector_class = get_caconnector_class("local")
        self.assertEqual(connector_class, LocalCAConnector)

        description = get_caconnector_config_description("local")
        self.assertEqual(description.get("local").get("cakey"), "string")
        self.assertEqual(description.get("local").get("cacert"), "string")

    def test_02_db_caconnector(self):
        pass
        # save a CA connector
        ca_id = save_caconnector({"caconnector": "myCA",
                                  "type": "local",
                                  "cakey": "/opt/ca/key.pem",
                                  "cacert": "/opt/ca/cert.pem"})
        self.assertTrue(ca_id > 0, ca_id)
        # Update the CA connector
        save_caconnector({"caconnector": "myCA",
                          "type": "local",
                          "WorkingDir": "/opt/ca",
                          "Password": "secret",
                          "type.Password": "password"})
        # check if connector is in DB
        calist = get_caconnector_list()
        self.assertEqual(len(calist), 1)
        calist = get_caconnector_list(filter_caconnector_type="local")
        self.assertEqual(len(calist), 1)
        # check the config values of "myCA"
        self.assertEqual(calist[0].get("data").get("WorkingDir"), "/opt/ca")
        self.assertEqual(calist[0].get("data").get("cakey"), "/opt/ca/key.pem")

        # get the CA connector list without a config
        calist = get_caconnector_list(return_config=False)
        self.assertEqual(len(calist), 1)
        # check that there are no values
        self.assertEqual(calist[0].get("data"), {})

        # test the CA connector:
        config = get_caconnector_config("myCA")
        self.assertEqual(config.get("WorkingDir"), "/opt/ca")
        self.assertEqual(config.get("cakey"), "/opt/ca/key.pem")
        # get_caconnector_object()
        ca_obj = get_caconnector_object("myCA")
        self.assertTrue(ca_obj.connector_type, "local")
        catype = get_caconnector_type("myCA")
        self.assertTrue(catype, "local")

        # delete the CA connector
        delete_caconnector("myCA")

        # check if connector is deleted from DB
        self.assertEqual(len(calist), 1)

    def test_03_errors(self):
        # unknown type
        self.assertRaises(Exception, save_caconnector,
                          {"caconnector": "unknown", "type": "unknown"})

        caobj = get_caconnector_object("not-existing")
        self.assertEqual(caobj, None)


class LocalCATestCase(MyTestCase):
    """
    Test the local CA connector
    """

    def test_01_create_ca_connector(self):
        # cakey missing
        self.assertRaises(CAError, LocalCAConnector, "localCA",
                          {"cacert": "..."})
        # cacert missing
        self.assertRaises(CAError, LocalCAConnector, "localCA",
                          {"cakey": "..."})

        cacon = LocalCAConnector("localCA", {"cacert": "...",
                                             "cakey": "..."})

        self.assertEqual(cacon.name, "localCA")

    def test_02_sign_cert(self):
        cacon = LocalCAConnector("localCA", {"cacert": "...",
                                             "cakey": "..."})
        # set the parameters:
        cwd = os.getcwd()
        cacon.set_config({"cakey": CAKEY, "cacert": CACERT,
                          "openssl.cnf": OPENSSLCNF,
                          "WorkingDir": cwd + "/" + WORKINGDIR})

        cert = cacon.sign_request(REQUEST,
                                  {"CSRDir": "",
                                   "CertificateDir": "",
                                   "WorkingDir": cwd + "/" + WORKINGDIR})
        serial = cert.get_serial_number()

        self.assertEqual("{0!r}".format(cert.get_issuer()),
                         "<X509Name object "
                         "'/C=DE/ST=Hessen/O=privacyidea/CN=CA001'>")
        self.assertEqual("{0!r}".format(cert.get_subject()),
                         "<X509Name object "
                         "'/C=DE/ST=Hessen/O=privacyidea/CN=requester"
                         ".localdomain'>")

        # Revoke certificate
        r = cacon.revoke_cert(cert)
        serial_hex = int_to_hex(serial)
        self.assertEqual(r, serial_hex)

        # Create the CRL
        r = cacon.create_crl()
        self.assertEqual(r, "crl.pem")
        # Check if the serial number is contained in the CRL!
        filename = os.path.join(cwd, WORKINGDIR, "crl.pem")
        f = open(filename)
        buff = f.read()
        f.close()
        crl = crypto.load_crl(crypto.FILETYPE_PEM, buff)
        revoked_certs = crl.get_revoked()
        found_revoked_cert = False
        for revoked_cert in revoked_certs:
            s = to_unicode(revoked_cert.get_serial())
            if s == serial_hex:
                found_revoked_cert = True
                break
        self.assertTrue(found_revoked_cert)

        # Create the CRL and check the overlap period. But no need to create
        # a new CRL.
        r = cacon.create_crl(check_validity=True)
        self.assertEqual(r, None)

        # Now we overlap at any cost!
        cacon.set_config({"cakey": CAKEY, "cacert": CACERT,
                          "openssl.cnf": OPENSSLCNF,
                          "WorkingDir": cwd + "/" + WORKINGDIR,
                          ATTR.CRL_OVERLAP_PERIOD: 1000})
        r = cacon.create_crl(check_validity=True)
        self.assertEqual(r, "crl.pem")

    def test_03_sign_user_cert(self):
        cwd = os.getcwd()
        cacon = LocalCAConnector("localCA",
                                 {"cakey": CAKEY,
                                  "cacert": CACERT,
                                  "openssl.cnf": OPENSSLCNF,
                                  "WorkingDir": cwd + "/" + WORKINGDIR})

        cert = cacon.sign_request(REQUEST_USER)
        self.assertEqual("{0!r}".format(cert.get_issuer()),
                         "<X509Name object "
                         "'/C=DE/ST=Hessen/O=privacyidea/CN=CA001'>")
        self.assertEqual("{0!r}".format(cert.get_subject()),
                         "<X509Name object "
                         "'/C=DE/ST=Hessen/O=privacyidea/CN=usercert'>")

    def test_04_sign_SPKAC_request(self):
        cwd = os.getcwd()
        cacon = LocalCAConnector("localCA",
                                 {"cakey": CAKEY,
                                  "cacert": CACERT,
                                  "openssl.cnf": OPENSSLCNF,
                                  "WorkingDir": cwd + "/" + WORKINGDIR})

        cert = cacon.sign_request(SPKAC, options={"spkac": 1})
        self.assertEqual("{0!r}".format(cert.get_issuer()),
                         "<X509Name object "
                         "'/C=DE/ST=Hessen/O=privacyidea/CN=CA001'>")
        self.assertEqual("{0!r}".format(cert.get_subject()),
                         "<X509Name object '/CN=Steve Test"
                         "/emailAddress=steve@openssl.org'>")

    def test_05_templates(self):
        cwd = os.getcwd()
        cacon = LocalCAConnector("localCA",
                                 {"cakey": CAKEY,
                                  "cacert": CACERT,
                                  "openssl.cnf": OPENSSLCNF,
                                  "WorkingDir": cwd + "/" + WORKINGDIR,
                                  ATTR.TEMPLATE_FILE: "templates.yaml"})
        templates = cacon.get_templates()
        self.assertTrue("user" in templates)
        self.assertTrue("webserver" in templates)
        self.assertTrue("template3" in templates)
        cert = cacon.sign_request(SPKAC, options={"spkac": 1,
                                                  "template": "webserver"})
        expires = to_unicode(cert.get_notAfter())
        import datetime
        dt = datetime.datetime.strptime(expires, "%Y%m%d%H%M%SZ")
        ddiff = dt - datetime.datetime.now()
        # The certificate is signed for 750 days
        self.assertTrue(ddiff.days > 740, ddiff.days)
        self.assertTrue(ddiff.days < 760, ddiff.days)


class CreateLocalCATestCase(MyTestCase):
    """
    test creating a new CA using the local caconnector
    """
    def test_01_create_ca(self):
        cwd = os.getcwd()
        workdir = os.path.join(cwd, WORKINGDIR + '2')
        if os.path.exists(workdir):
            shutil.rmtree(workdir)
        inputstr = six.text_type(workdir + '\n\n\n\n\n\ny\n')
        with patch('sys.stdin', StringIO(inputstr)):
            caconfig = LocalCAConnector.create_ca('localCA2')
            self.assertEqual(caconfig.get("WorkingDir"), workdir)
            cacon = LocalCAConnector('localCA2', caconfig)
            self.assertEqual(cacon.name, 'localCA2')
            self.assertEqual(cacon.workingdir, workdir)
            # check if the generated files exist
            self.assertTrue(os.path.exists(os.path.join(workdir, 'cacert.pem')))
