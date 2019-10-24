# -*- coding: utf-8 -*-

"""
This file tests the web UI for creating certificate requests

implementation is contained webui/certificate.py
"""
import json
from .base import MyTestCase
import os
from privacyidea.lib.caconnectors.localca import LocalCAConnector


REQUESTKEY = """MIICQDCCASgwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDPPNQzDhLE5trNtlahHCa7JhyKSnOoWIq2HrOLmdIdB8KSiXnAadjI3yhhmB6z/q4rvXip925H3KOgFoyFAsFOkv1ybvDIAymbuABuwIOVyDQgNpyz5eTmdnOjGq1AluBTVADsdnmaxg1+tr0p7IPzy4mky2wAugzFeA//abiU9ARwQz/Ynten+13OdY7a58QHsZ3eb4hLtk2az/m8+p/NMm32OgsNI0J47JdCvw5NYFbh0wLyGcuEV5DlcKGigzWG4tqGn/mKxHmzUijay7s0ytPakUrPjXaismub+Zb9CSraESNN8MvWsrEOEmyaGWWYh8rk7iTORKyQj50bxSqdAgMBAAEWADANBgkqhkiG9w0BAQQFAAOCAQEAjqR8Cv+UZeGXP9v00/T4ClH2wCtQea9oLklllElsU+x9UNjrPITpZGwiKdCtrPSDy+QeqzecSXi23LL05s6RKATnQt31EPRLLPuHRwkpbHD+n/XJtqv5Byge/KJX+Xt8xb+cLKfGJmQibnV/vu83TL8on91pUB4BXuaSu3UXJOFnrG0E2h4rpGE8FrK3JrIruQe2FAcal/KRGzsgHp/vq90OibH0ZJQE3kNg+JkOlzBTTn73+Q39y/E6CW7fD8iFtNRF0xhZYJ/AgflLMQeQUeKRb0Qaillz/DnWQFuVqLoCdahvv6jt58nXmqHv6oMfRg0R2qF2jMFfGtI15Hixzw=="""
CAKEY = "cakey.pem"
CACERT = "cacert.pem"
OPENSSLCNF = "openssl.cnf"
WORKINGDIR = "tests/testdata/ca"


class WebUICertificateTestCase(MyTestCase):

    my_serial = "myToken"
    foreign_serial = "notMyToken"

    def setUp(self):
        """
        For each test we need to initialize the users
        """
        self.setUp_user_realms()

    def test_01_cert_request(self):
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "selfservice@realm1",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), res.data)
            # In self.at_user we store the user token
            authtoken = result.get("value")

        # Check the form
        with self.app.test_request_context('/certificate',
                                           method='POST',
                                           data={"authtoken": authtoken.get("token")}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertEqual(res.mimetype, 'text/html', res)
            # Check the form
            self.assertTrue(b"privacyIDEA Certificate Request" in res.data)
            self.assertTrue(b"Key strength" in res.data)
            self.assertTrue(b'input type="hidden" name="authtoken"' in res.data)

        # Check that missing authentication will result in an error
        with self.app.test_request_context('/certificate',
                                           method='POST',
                                           data={}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

        # GET-Request will fail, Method not allowed
        with self.app.test_request_context('/certificate',
                                           method='GET',
                                           data={}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 405, res)

    def test_02_cert_enrolled(self):
        # Setup the CA
        self.authenticate()
        cwd = os.getcwd()
        with self.app.test_request_context('/caconnector/localCA',
                                           data={'type': 'local',
                                                 'cakey': CAKEY,
                                                 'cacert': CACERT,
                                                 'openssl.cnf': OPENSSLCNF,
                                                 "WorkingDir": cwd + "/" + WORKINGDIR},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json['result']
            self.assertTrue(result["status"], result)
            self.assertTrue(result["value"] == 1, result)

        # Get the users authtoken
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "selfservice@realm1",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json['result']
            self.assertTrue(result.get("status"), res.data)
            # In self.at_user we store the user token
            authtoken = result.get("value")

        # Check the form
        with self.app.test_request_context('/certificate/enroll',
                                           method='POST',
                                           data={"authtoken": authtoken.get("token"),
                                                 "requestkey": REQUESTKEY,
                                                 "ca": "localCA"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertEqual(res.mimetype, 'text/html', res)
            # Check the form
            self.assertTrue(b"The certificate with token serial" in res.data)
            self.assertTrue(b"Certificate to Browser" in res.data)
            self.assertTrue(b'data:application/x-x509-user-cert;base64' in res.data)

        # Check that missing authentication will result in an error
        with self.app.test_request_context('/certificate/enroll',
                                           method='POST',
                                           data={}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

        # GET-Request will fail, Method not allowed
        with self.app.test_request_context('/certificate/enroll',
                                           method='GET',
                                           data={}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 405, res)
