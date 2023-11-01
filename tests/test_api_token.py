# -*- coding: utf-8 -*-
from .base import MyApiTestCase, PWFILE2
import json
import os
import datetime
import codecs
from mock import mock
from privacyidea.lib.policy import (set_policy, delete_policy, SCOPE, ACTION,
                                    enable_policy,
                                    PolicyClass)
from privacyidea.lib.token import (get_tokens, init_token, remove_token,
                                   get_tokens_from_serial_or_user, enable_token,
                                   check_serial_pass, get_realms_of_token,
                                   assign_token, token_exist, add_tokeninfo)
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.realm import set_realm
from privacyidea.lib.user import User
from privacyidea.lib.event import set_event, delete_event, EventConfiguration
from privacyidea.lib.caconnector import save_caconnector
from urllib.parse import urlencode, quote
from privacyidea.lib.tokenclass import DATE_FORMAT
from privacyidea.lib.tokenclass import ROLLOUTSTATE
from privacyidea.lib.tokens.hotptoken import VERIFY_ENROLLMENT_MESSAGE
from privacyidea.lib.config import set_privacyidea_config, delete_privacyidea_config
from dateutil.tz import tzlocal
from privacyidea.lib import _
import os
import unittest
import mock
from privacyidea.lib.caconnectors.baseca import AvailableCAConnectors
from privacyidea.lib.caconnectors.msca import MSCAConnector
from .mscamock import CAServiceMock
from privacyidea.lib.caconnectors.msca import ATTR as MS_ATTR
from privacyidea.lib.token import init_token

# Mock for certificate from MSCA
MY_CA_NAME = "192.168.47.11"

MOCK_AVAILABLE_CAS = ['WIN-GG7JP259HMQ.nilsca.com\\nilsca-WIN-GG7JP259HMQ-CA',
                      'CA03.nilsca.com\\nilsca-CA03-CA']
MOCK_CA_TEMPLATES = ["User", "SmartcardLogon", "ApprovalRequired"]

MOCK_USER_CERT = """-----BEGIN CERTIFICATE-----
MIIGFTCCA/2gAwIBAgIBRjANBgkqhkiG9w0BAQsFADCBkTELMAkGA1UEBhMCREUx
DzANBgNVBAgTBkhlc3NlbjEPMA0GA1UEBxMGS2Fzc2VsMRgwFgYDVQQKEw9OZXRL
bmlnaHRzIEdtYkgxEDAOBgNVBAsTB2V4YW1wbGUxETAPBgNVBAMTCGxvY2FsIENB
MSEwHwYJKoZIhvcNAQkBFhJpbmZvQG5ldGtuaWdodHMuaXQwHhcNMjIwNzE4MDkw
OTMxWhcNMjQwNzA3MDkwOTMxWjBHMQswCQYDVQQGEwJERTEPMA0GA1UECAwGSGVz
c2VuMRQwEgYDVQQKDAtwcml2YWN5aWRlYTERMA8GA1UEAwwIdXNlcmNlcnQwggEi
MA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDcL9FfKZfUfMNTyDC9S2dwLCRr
uF7rIXpIElZ8gVxIdbZo6/bymE5QUdF/bHPzCqeuvkhe5dbh2Sp8Mm5O/Qj2WlRJ
I3PDuQcY0e+zrPiK3JSWpJA6jnTf5g03G71btyUaVjnab5GqXhx08/l8FAGDEmV2
x7v+NluV6XJlg+0+mDBx+ofdozZaMAMuJuBh0b8CP7YGH0qJKBxcov9OvpTmjODa
gvGdKTJIMHO0BPZCHr734jIyJzydiS9wPoWab1zFCcCMMi9yIsnSlR+2rHJgcreC
TWvOW+MA0NIvWMbgEOVRyk07LuZ+q4TWVvGTNaCTZCaBdS+RtRYGOAvbzC0HAgMB
AAGjggG/MIIBuzALBgNVHQ8EBAMCBeAwCQYDVR0TBAIwADAdBgNVHQ4EFgQU/BTR
8EuNAJDy9bhxnk6Xw5JUrQswgcYGA1UdIwSBvjCBu4AUgJJUh03rWtOETE9/aKgg
+S/Vy2WhgZekgZQwgZExCzAJBgNVBAYTAkRFMQ8wDQYDVQQIEwZIZXNzZW4xDzAN
BgNVBAcTBkthc3NlbDEYMBYGA1UEChMPTmV0S25pZ2h0cyBHbWJIMRAwDgYDVQQL
EwdleGFtcGxlMREwDwYDVQQDEwhsb2NhbCBDQTEhMB8GCSqGSIb3DQEJARYSaW5m
b0BuZXRrbmlnaHRzLml0ggkArBZTyBi/ZtkwdAYDVR0fBG0wazAqoCigJoYkaHR0
cHM6Ly9uZXRrbmlnaHRzLml0L25ldGtuaWdodHMuY3JsMD2gO6A5hjdodHRwczov
L29wZW5wcm9qZWN0Lm9mZmljZS5uZXRrbmlnaHRzLml0L25ldGtuaWdodHMuY3Js
MEMGCCsGAQUFBwEBBDcwNTAzBggrBgEFBQcwAoYnaHR0cHM6Ly9uZXRrbmlnaHRz
Lml0L25ldGtuaWdodHMtY2EuY3J0MA0GCSqGSIb3DQEBCwUAA4ICAQCWsFBzwvIm
ZWzmWZmCTNYc8c7O0wmNorfGp4c6yZjsffo8w+FLbsbkTb/U12mupKkMxTJmqUdb
q3zeVsRUG1Lg9K2iM5f9FWxrxbyecGJ04lVN/FTBHdUw9dmnTlIgbUo3ZK6doS1F
YcdDSYGkvUDMba0zvMy7A8MaGdtBWmvULLEw4pBcoxzjd7TtNGimVFH9mdS2YAj3
P5fTX0ReBfUX4JJB7XJFl4vdPetZ/93zDM12YxtytDa1KrtwAFcCAgTuBsd014LK
dMjsLOpiJzyKqol5OPsnkwhxqTEaPzCviMymMEwaZQLQDTbS62UBhMqv5oOOSy2l
Awx0eVSlPOFEyeg0PEO3G3SQjajrpxUkGEdb+krEazNd00gz6SNbSliT/GQS4tO4
VBC5Qos8/IabJpV5Bvqq4/7ZmVeAOXRQCVPomugzU1L6cs7GWCZpmuB7WG5VT+hL
+WGIKnWe8vmi+dWs1SRAjFEPKd5mjgeIiYh9D5n+0lBWYO7q6Hf+U4R0qlXHNS5p
+rNmCNAgo3LQGhxBZaCdpUNspZxGGCTba3P13zQupuXa7lKWHddwsZ4udnTgD6lI
WYx05kOaYFFvb1u8ub+qSExyHGX9Lh6w32RCoM8kJP7F6YCepKJRboka1/BY3GbF
17qsUVtb+0YLznMdHEFtWc51SpzA0h3a7w==
-----END CERTIFICATE-----"""


CERTIFICATE = """-----BEGIN CERTIFICATE-----
MIIHdTCCBV2gAwIBAgITMAAAAHozruIlHyAQtAAAAAAAejANBgkqhkiG9w0BAQsF
ADBGMRMwEQYKCZImiZPyLGQBGRYDY29tMRYwFAYKCZImiZPyLGQBGRYGbmlsc2Nh
MRcwFQYDVQQDEw5uaWxzY2EtQ0EwMy1DQTAeFw0yMjA3MjQxNjQzNDlaFw0yMzA3
MjQxNjQzNDlaMFUxEzARBgoJkiaJk/IsZAEZFgNjb20xFjAUBgoJkiaJk/IsZAEZ
FgZuaWxzY2ExDjAMBgNVBAMTBVVzZXJzMRYwFAYDVQQDEw1BZG1pbmlzdHJhdG9y
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAzb4UT/rOAT9CIhsdnK/d
ktJ/22y3PjlDQ2sTA/EF9Ad0vHZpKAuvGY7X/OPNxljyyn8IbVP8BwJEJMa0NEyM
BP4zDkDiILoCc1r39U9jbszGtt9UHTc5fVE2Jl+93D+oi2uirrad1iHn30G4eigq
aEjKqC3t4elGXlpybbSEOIeR/ZQRCyiExsIvKvsB+TZ6CXXRM4g8c0FbyL+UiXCh
8MC5LlBTHrEXZGn0LYHgqQ0OMum6VYqF8RtvSXm0f4jDDT5UiJs9HziMBPPuamMr
9cbbtIOqxHhBOn1L4cg+ccobYVnqxsTKMl7J6b8SKebGw2P+oFXaevFgmE0m7fpw
LQIDAQABo4IDSzCCA0cwHQYDVR0OBBYEFFM/7V0JB7Nle6tFySRbCXeACpbtMB8G
A1UdIwQYMBaAFLgiq+2UnxagGJRx6MJQEOuboBfNMIHIBgNVHR8EgcAwgb0wgbqg
gbeggbSGgbFsZGFwOi8vL0NOPW5pbHNjYS1DQTAzLUNBLENOPUNBMDMsQ049Q0RQ
LENOPVB1YmxpYyUyMEtleSUyMFNlcnZpY2VzLENOPVNlcnZpY2VzLENOPUNvbmZp
Z3VyYXRpb24sREM9bmlsc2NhLERDPWNvbT9jZXJ0aWZpY2F0ZVJldm9jYXRpb25M
aXN0P2Jhc2U/b2JqZWN0Q2xhc3M9Y1JMRGlzdHJpYnV0aW9uUG9pbnQwgb8GCCsG
AQUFBwEBBIGyMIGvMIGsBggrBgEFBQcwAoaBn2xkYXA6Ly8vQ049bmlsc2NhLUNB
MDMtQ0EsQ049QUlBLENOPVB1YmxpYyUyMEtleSUyMFNlcnZpY2VzLENOPVNlcnZp
Y2VzLENOPUNvbmZpZ3VyYXRpb24sREM9bmlsc2NhLERDPWNvbT9jQUNlcnRpZmlj
YXRlP2Jhc2U/b2JqZWN0Q2xhc3M9Y2VydGlmaWNhdGlvbkF1dGhvcml0eTAOBgNV
HQ8BAf8EBAMCBaAwPAYJKwYBBAGCNxUHBC8wLQYlKwYBBAGCNxUIhrbHcYa95yeB
1Y8bh6WhcIGbvAqBfJStI5DMCgIBZAIBBTApBgNVHSUEIjAgBggrBgEFBQcDAgYI
KwYBBQUHAwQGCisGAQQBgjcKAwQwNQYJKwYBBAGCNxUKBCgwJjAKBggrBgEFBQcD
AjAKBggrBgEFBQcDBDAMBgorBgEEAYI3CgMEMDMGA1UdEQQsMCqgKAYKKwYBBAGC
NxQCA6AaDBhBZG1pbmlzdHJhdG9yQG5pbHNjYS5jb20wTQYJKwYBBAGCNxkCBEAw
PqA8BgorBgEEAYI3GQIBoC4ELFMtMS01LTIxLTYwNDM1NTA3OS0zNzE5MzIxMzQ2
LTE4ODc1MjYzMzItNTAwMEQGCSqGSIb3DQEJDwQ3MDUwDgYIKoZIhvcNAwICAgCA
MA4GCCqGSIb3DQMEAgIAgDAHBgUrDgMCBzAKBggqhkiG9w0DBzANBgkqhkiG9w0B
AQsFAAOCAgEACiBnzQbxxS7cCTtvT6ODyXaJfl5F+WkeoazR7iQnMTIIuigGNeGY
q7YS92YPGlw8CBcjQ2VHG8ez4v4RaN0xnRDPOoVddG6JPjY4z0Cq+SCHW1W+yBH6
YNIoU22gx8qM4GWHEQvu33tU+gPHy0ZZceMoEWQVwpC9/Nq/bqEvbevrcXJDC20f
3Ob3kVJTqrwULYqcuzNW194NXE+hC5+Wjg3mMy7YJU0bE1XeYQxCzHs2T3Sd2O+C
9ZGvvykSS2MJsC0vW+sFpZ2Z6hDFduXzQqpzaORXe04p+dI88orjdu3yX898jOL0
YCmxCy/Rvm5+E15MW6Dh3BfUh6Zaeij3z3/xmE3kVaLA9PeWxG5+akW1KtQwD0PB
mH5q4AmzBj0ryhPfOvXKUSOBp+tLV9Fd4QW0rZgU6/ZTAC73mbh8sDBdXZYb+jzi
7iM6kqIma6T3mgODYg2d1WTmNx3z+8m+sBoUiwY0yQc22oWkTVXKqzOrg7SOuiSy
a3QX4OejnyxBSuNegL8EQhyxDCAdisRqgGLhtYh3RMegZn0WnJOlRPBHrniFkJBV
ub8B4Q4BtcXwyX1IjkSRVGhpmBKc+cykTR1GGR0L0JihMK85qWF/8vyYiwBq3z08
TdIfRtrzkM5Zw/U/p2/LWzbe/fCkqSC6SheI+/FDR7Bjz7xNxIZHonk=
-----END CERTIFICATE-----"""


CONF = {MS_ATTR.HOSTNAME: MY_CA_NAME,
        MS_ATTR.PORT: 50061,
        MS_ATTR.HTTP_PROXY: "0",
        MS_ATTR.CA: "CA03.nilsca.com\\nilsca-CA03-CA"}


IMPORTFILE = "tests/testdata/import.oath"
IMPORTFILE_GPG = "tests/testdata/import.oath.asc"
IMPORTFILE2 = "tests/testdata/empty.oath"
IMPORTPSKC = "tests/testdata/pskc-aes.xml"
IMPORTPSKC_PASS = "tests/testdata/pskc-password.xml"
PSK_HEX = "12345678901234567890123456789012"
YUBICOFILE = "tests/testdata/yubico-oath.csv"
YUBICOFILE_LONG = "tests/testdata/yubico-oath-long.csv"
OTPKEY = "3132333435363738393031323334353637383930"
OTPKEY2 = "010fe88d31948c0c2e3258a4b0f7b11956a258ef"
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


class API000TokenAdminRealmList(MyApiTestCase):

    def test_000_setup_realms(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()

        # create tokens
        t = init_token({"otpkey": self.otpkey},
                       tokenrealms=[self.realm1])

        t = init_token({"otpkey": self.otpkey},
                       tokenrealms=[self.realm2])

    def test_01_test_two_tokens(self):
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            # we have two tokens
            self.assertEqual(2, result.get("value").get("count"))

        # admin is allowed to see realm1
        set_policy(name="pol-realm1",
                   scope=SCOPE.ADMIN,
                   action=ACTION.TOKENLIST, user=self.testadmin, realm=self.realm1)

        # admin is allowed to list all realms
        set_policy(name="pol-all-realms",
                   scope=SCOPE.ADMIN,
                   action=ACTION.TOKENLIST, user=self.testadmin)

        # admin is allowed to only init, not list
        set_policy(name="pol-only-init",
                   scope=SCOPE.ADMIN)

        with self.app.test_request_context('/token/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            # we have two tokens
            self.assertEqual(2, result.get("value").get("count"))

        # Disable to be allowed to list all realms
        enable_policy("pol-all-realms", False)

        with self.app.test_request_context('/token/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            # we have one token
            self.assertEqual(1, result.get("value").get("count"))
            # The token is in realm1
            self.assertEqual(self.realm1,
                             result.get("value").get("tokens")[0].get("realms")[0])

        # Disable to be allowed to list realm1
        enable_policy("pol-realm1", False)

        with self.app.test_request_context('/token/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            # we have two tokens
            self.assertEqual(0, result.get("value").get("count"))

    def test_02_two_resolver_in_realm_policy_condition(self):
        self.setUp_user_realms()
        # add a second resolver to the realm
        save_resolver({"resolver": self.resolvername2,
                       "type": "passwdresolver",
                       "fileName": PWFILE2})
        added, failed = set_realm(self.realm1,
                                  [self.resolvername1, self.resolvername2])
        self.assertEqual(len(failed), 0)
        self.assertEqual(len(added), 2)

        # create token delete policy for "testadmin" on resolver1
        set_policy(name="pol-reso1",
                   scope=SCOPE.ADMIN,
                   action=','.join([ACTION.DELETE, ACTION.ASSIGN, ACTION.UNASSIGN,
                                    ACTION.DISABLE, ACTION.ENABLE, ACTION.AUDIT]),
                   adminuser=self.testadmin,
                   realm=self.realm1,
                   resolver=self.resolvername1)

        # create tokens for users in resolver 1 and 2
        t1 = init_token({'type': 'spass'}, user=User(login='franzi',
                                                     resolver=self.resolvername2,
                                                     realm=self.realm1))
        t2 = init_token({'type': 'spass'})

        # assigning a token to a user from resolver2 should fail
        with self.app.test_request_context('/token/assign',
                                           method='POST',
                                           data={"serial": t2.token.serial,
                                                 "user": "franzi",
                                                 "realm": self.realm1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(403, res.status_code, res.data)
            result = res.json.get("result")
            self.assertEqual(303, result.get('error').get('code'), result)
            self.assertIsNone(t2.token.first_owner, t2.token.first_owner)
        # check the audit log for a failed entry
        entry = self.find_most_recent_audit_entry(action='*/token/assign')
        self.assertFalse(entry['success'], entry)
        self.assertIn('Admin actions are defined, but the action assign', entry['info'], entry)

        # assigning the same token to a user from resolver1 should work
        with self.app.test_request_context('/token/assign',
                                           method='POST',
                                           data={"serial": t2.token.serial,
                                                 "user": "nönäscii",
                                                 "realm": self.realm1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res.data)
            result = res.json.get("result")
            self.assertTrue(result.get("value"), result)
            self.assertIsNotNone(t2.token.first_owner)
        # check the audit log for a  successful entry
        entry = self.find_most_recent_audit_entry(action='*/token/assign')
        self.assertTrue(entry['success'], entry)
        self.assertIn('pol-reso1', entry['policies'], entry)

        remove_token(t2.token.serial)

        # unassign a token from a user in resolver2 should fail
        with self.app.test_request_context('/token/unassign',
                                           method='POST',
                                           data={"serial": t1.token.serial},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403, res)
            result = res.json.get("result")
            self.assertEqual(result.get('error').get('code'), 303, result)

        t2 = init_token({'type': 'spass'}, user=User(login='nönäscii',
                                                     resolver=self.resolvername1,
                                                     realm=self.realm1))
        # unassign a token from a user in resolver1 should work
        with self.app.test_request_context('/token/unassign',
                                           method='POST',
                                           data={"serial": t2.token.serial},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"), result)
            self.assertIsNone(t2.token.first_owner)

        remove_token(t2.token.serial)

        # disabling an active token from a user from resolver2 should fail
        with self.app.test_request_context('/token/disable/{0!s}'.format(t1.token.serial),
                                           method='POST',
                                           data={},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403, res)
            result = res.json.get("result")
            self.assertEqual(result.get('error').get('code'), 303, result)

        # disableing an active token from a user from resolver1 should work
        t2 = init_token({'type': 'spass'}, user=User(login='nönäscii',
                                                     resolver=self.resolvername1,
                                                     realm=self.realm1))
        with self.app.test_request_context('/token/disable/{0!s}'.format(t2.token.serial),
                                           method='POST',
                                           data={},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get('value'), result)
            self.assertFalse(t2.is_active())

        remove_token(t2.token.serial)

        # enable an inactive token from a user from resolver2 should fail
        t1.enable(enable=False)
        with self.app.test_request_context('/token/enable/{0!s}'.format(t1.token.serial),
                                           method='POST',
                                           data={},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403, res)
            result = res.json.get("result")
            self.assertEqual(result.get('error').get('code'), 303, result)

        # enable an inactive token from a user from resolver1 should work
        t2 = init_token({'type': 'spass'}, user=User(login='nönäscii',
                                                     resolver=self.resolvername1,
                                                     realm=self.realm1))
        t2.enable(enable=False)
        with self.app.test_request_context('/token/enable/{0!s}'.format(t2.token.serial),
                                           method='POST',
                                           data={},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get('value'), result)
            self.assertTrue(t2.is_active())

        # token delete should fail for a token assigned to a user from resolver2
        with self.app.test_request_context('/token/{0!s}'.format(t1.token.serial),
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403, res)
            result = res.json.get("result")
            self.assertEqual(result.get('error').get('code'), 303, result)

        # token delete should work for a token assigned to a user from resolver1
        with self.app.test_request_context('/token/{0!s}'.format(t2.token.serial),
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get('value'), result)
            self.assertFalse(token_exist(t2.token.serial))

        # cleanup
        remove_token(t1.token.serial)
        delete_policy("pol-reso1")

class APIAttestationTestCase(MyApiTestCase):

    def test_00_realms_and_ca(self):
        # Setup realms and CA
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

    def test_01_enroll_certificate(self):
        # Enroll a certificate without a policy
        from .test_lib_tokens_certificate import YUBIKEY_CSR, BOGUS_ATTESTATION, YUBIKEY_ATTEST, ACTION

        # A bogus attestation certificate will fail!
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "certificate",
                                                 "request": YUBIKEY_CSR,
                                                 "attestation": BOGUS_ATTESTATION,
                                                 "ca": "localCA"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertEqual(400, res.status_code)
            self.assertEqual(10, result.get("error").get("code"))
            self.assertEqual('ERR10: certificate request does not match attestation certificate.',
                             result.get("error").get("message"))

        # If a valid attestation certificate can not be verified due to missing CA path, we will fail.
        from privacyidea.lib.tokens.certificatetoken import ACTION, REQUIRE_ACTIONS
        set_policy(name="pol_verify",
                   scope=SCOPE.ENROLL,
                   action="{0!s}={1!s}".format(ACTION.REQUIRE_ATTESTATION, REQUIRE_ACTIONS.REQUIRE_AND_VERIFY))
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "certificate",
                                                 "request": YUBIKEY_CSR,
                                                 "attestation": YUBIKEY_ATTEST,
                                                 "ca": "localCA"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertEqual(400, res.status_code)
            self.assertEqual(10, result.get("error").get("code"))
            self.assertEqual('ERR10: Failed to verify certificate chain of attestation certificate.',
                             result.get("error").get("message"))

        # The admin enrolls the certificate, so we need an admin policy
        set_policy("pol1", scope=SCOPE.ADMIN,
                   action="{0!s}=tests/testdata/attestation/".format(ACTION.TRUSTED_CA_PATH))
        set_policy("pol2", scope=SCOPE.ADMIN,
                   action="enrollCERTIFICATE")

        # If the attestation certificate matches and it is trusted, then we succeed.
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "certificate",
                                                 "request": YUBIKEY_CSR,
                                                 "attestation": YUBIKEY_ATTEST,
                                                 "ca": "localCA"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertEqual(200, res.status_code)
            self.assertTrue(result.get("value"))

        delete_policy("pol1")
        delete_policy("pol2")
        delete_policy("pol_verify")


class APITokenTestCase(MyApiTestCase):

    def setUp(self):
        super(APITokenTestCase, self).setUp()
        self.setUp_user_realms()

    def _create_temp_token(self, serial):
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"serial": serial,
                                                 "genkey": 1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)

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
            result = res.json.get("result")
            detail = res.json.get("detail")
            serial = detail.get("serial")
            self.assertTrue(result.get("status"), result)
            self.assertTrue(result.get("value"), result)
            self.assertTrue("value" in detail.get("googleurl"), detail)
            self.assertTrue("OATH" in serial, detail)
            remove_token(serial)

        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"type": "hotp",
                                                 "otpkey": self.otpkey,
                                                 "genkey": 0},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            data = res.json
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
            data = res.json
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
        init_token({"otpkey": self.otpkey}, tokenkind="hotp")
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            tokenlist = result.get("value").get("tokens")
            count = result.get("value").get("count")
            next = result.get("value").get("next")
            prev = result.get("value").get("prev")
            self.assertTrue(result.get("status"), result)
            self.assertGreaterEqual(len(tokenlist), 1, tokenlist)
            self.assertGreaterEqual(count, 1, result)
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
            result = res.json.get("result")
            detail = res.json.get("detail")
            tokenlist = result.get("value").get("tokens")
            # NO token assigned, yet
            self.assertGreaterEqual(len(tokenlist), 0, "{0!s}".format(tokenlist))

        # get unassigned tokens
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           query_string=urlencode({
                                               "assigned": False}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            tokenlist = result.get("value").get("tokens")
            self.assertTrue(len(tokenlist) == 1, len(tokenlist))

        # prepare active tests
        init_token({"serial": "totp1", "genkey": 1}, tokenkind="totp")
        enable_token("totp1", enable=False)
        # get active tokens
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           query_string=urlencode({
                                               "active": True}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            tokenlist = result.get("value").get("tokens")
            # NO token assigned, yet
            self.assertTrue(len(tokenlist) == 1, "{0!s}".format(tokenlist))

        # get inactive tokens
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           query_string=urlencode({
                                               "active": False}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            tokenlist = result.get("value").get("tokens")
            self.assertTrue(len(tokenlist) == 1, len(tokenlist))
            token0 = tokenlist[0]
            self.assertTrue(token0.get("serial") == "totp1", token0)

        # get all tokens
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            tokenlist = result.get("value").get("tokens")
            self.assertTrue(len(tokenlist) == 2, len(tokenlist))

        remove_token(serial="totp1")

        # get tokens with a specific tokeninfo
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           query_string=urlencode({
                                               "assigned": False,
                                           "infokey": "tokenkind",
                                           "infovalue": "hardware"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            detail = res.json.get("detail")
            tokenlist = result.get("value").get("tokens")
            self.assertEqual(len(tokenlist), 0)

        init_token({"serial": "hw001", "genkey": 1}, tokenkind="hardware")
        # get tokens with a specific tokeninfo
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           query_string=urlencode({
                                               "assigned": False,
                                               "infokey": "tokenkind",
                                               "infovalue": "hardware"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            detail = res.json.get("detail")
            tokenlist = result.get("value").get("tokens")
            self.assertEqual(len(tokenlist), 1)

        remove_token("hw001")

    def test_02_list_tokens_csv(self):
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           query_string=urlencode({"outform": "csv"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertEqual(res.mimetype, 'text/csv', res)
            self.assertTrue(b"info" in res.data, res.data)
            self.assertTrue(b"username" in res.data, res.data)
            self.assertTrue(b"user_realm" in res.data, res.data)

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
            result = res.json.get("result")
            detail = res.json.get("detail")
            tokenlist = result.get("value").get("tokens")
            count = result.get("value").get("count")
            next = result.get("value").get("next")
            prev = result.get("value").get("prev")
            self.assertTrue(len(tokenlist) == 2, res.data)
            self.assertTrue(count == 2, count)

        # list tokens, that look a bit like realm1
        search_realm = self.realm1[:-1] + "*"
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           query_string=urlencode({
                                               "tokenrealm": search_realm}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
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
            result = res.json.get("result")
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
            result = res.json.get("result")
            error = result.get("error")
#            self.assertEqual(error.get("message"),
#                             "ERR1103: Token already assigned to user "
#                             "User(login='cornelius', realm='realm1', "
#                             "resolver='resolver1')")
            self.assertRegex(error.get('message'),
                             r"ERR1103: Token already assigned to user "
                             r"User\(login=u?'cornelius', "
                             r"realm=u?'realm1', resolver=u?'resolver1'\)")

        # Now the user tries to assign a foreign token
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username":
                                                     "selfservice@realm1",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), res.data)
            # In self.at_user we store the user token
            self.at_user = result.get("value").get("token")

        with self.app.test_request_context('/token/assign',
                                           method='POST',
                                           data={"serial": "S1"},
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)
            result = res.json.get("result")
            error = result.get("error")
            self.assertEqual(error.get("message"), "ERR1103: Token already assigned to another user.")

        # Now unassign the token
        with self.app.test_request_context('/token/unassign',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value") == 1, result)

        # Assign the same token to another user will success
        with self.app.test_request_context('/token/assign',
                                           method='POST',
                                           data={"user": "shadow",
                                                 "realm": self.realm1,
                                                 "serial": "S1"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value") is True, result)

        # Unassign without any arguments will raise a ParameterError
        with self.app.test_request_context('/token/unassign',
                                           method='POST',
                                           data={},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

        # assign S3 and S4 to cornelius
        for serial in ("S3", "S4"):
            with self.app.test_request_context('/token/assign',
                                               method='POST',
                                               data={"user": "cornelius",
                                                     "realm": self.realm1,
                                                     "serial": serial,
                                                     "pin": "test"},
                                               headers={'Authorization': self.at}):
                res = self.app.full_dispatch_request()
                self.assertEqual(res.status_code, 200)

        # Check that it worked
        user = User('cornelius', self.realm1)
        tokens = get_tokens_from_serial_or_user(None, user)
        self.assertEqual({t.token.serial for t in tokens}, {"S3", "S4"})

        # unassign all
        with self.app.test_request_context('/token/unassign',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            self.assertTrue(result["value"], 2)

        # Check that it worked
        tokens = get_tokens_from_serial_or_user(None, user)
        self.assertEqual(tokens, [])

    def test_05_delete_token(self):
        self._create_temp_token("DToken")

        with self.app.test_request_context('/token/DToken',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value") == 1, result)

        # Try to remove token, that does not exist raises a 404
        with self.app.test_request_context('/token/DToken',
                                           method='DELETE',
                                           data={},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertEqual(res.status_code, 404)
            self.assertFalse(result.get("status"))

    def test_06_disable_enable_token(self):
        self._create_temp_token("EToken")

        # try to disable a token with no parameters
        with self.app.test_request_context('/token/disable',
                                           method='POST',
                                           data={},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

        # disable an assigned token
        r = assign_token("EToken", User("hans", self.realm1))
        self.assertTrue(r)
        with self.app.test_request_context('/token/disable/EToken',
                                           method='POST',
                                           data={},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value") == 1, result)

        # Check for the disabled token in the audit log, that also the user object is added
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           data={'action': "*disable*", "serial": "EToken"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            jres = res.json
            self.assertEqual(jres['result']['value']['auditdata'][0]['user'], "hans")

        # disable a disabled token will not count, so the value will be 0
        with self.app.test_request_context('/token/disable',
                                           method='POST',
                                           data={"serial": "EToken"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value") == 0, result)

        # enable the token again
        with self.app.test_request_context('/token/enable/EToken',
                                           method='POST',
                                           data={},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value") == 1, result)

        # try to enable an already enabled token returns value=0
        with self.app.test_request_context('/token/enable',
                                           method='POST',
                                           data={"serial": "EToken"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
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
            result = res.json.get("result")
            self.assertTrue(result.get("value") == 1, result)

        # test the failcount
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           query_string=urlencode({"serial":
                                                                       serial}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
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
            result = res.json.get("result")
            self.assertTrue(result.get("value") == 1, result)

    def test_07_resync(self):

        with self.app.test_request_context('/token/init', method="POST",
                                           data={"serial": "Resync01",
                                                 "otpkey": self.otpkey},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
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
            result = res.json.get("result")
            self.assertTrue(result.get("value") is False, result)

        # check that we have a failed request in the audit log
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           data={'action': "POST /token/resync/<serial>",
                                                 'serial': 'Resync01',
                                                 'success': '0'},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            self.assertEqual(len(res.json['result']['value']['auditdata']), 1, res.json)
            self.assertEqual(res.json['result']['value']['auditdata'][0]['success'], 0, res.json)

        # Successful resync with consecutive values
        with self.app.test_request_context('/token/resync',
                                            method="POST",
                                            data={"serial": "Resync01",
                                                  "otp1": 359152,
                                                  "otp2": 969429},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value") is True, result)

        # Check for a successful request in the audit log
        with self.app.test_request_context('/audit/',
                                           method='GET',
                                           data={'action': "POST /token/resync",
                                                 'serial': 'Resync01',
                                                 'success': '1'},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            self.assertEqual(len(res.json['result']['value']['auditdata']), 1, res.json)
            self.assertEqual(res.json['result']['value']['auditdata'][0]['success'], 1, res.json)

        # Get the OTP token and inspect the counter
        with self.app.test_request_context('/token/',
                                            method="GET",
                                            query_string=urlencode({"serial": "Resync01"}),
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
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
            result = res.json.get("result")
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
            self.assertEqual(res.status_code, 404)
            result = res.json.get("result")
            self.assertFalse(result["status"])

        # assign the token to the user selfservice@realm1.
        with self.app.test_request_context('/token/assign',
                                            method="POST",
                                            data={"serial": "Resync01",
                                                  "user": "selfservice@realm1"},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
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
            result = res.json.get("result")
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
            result = res.json.get("result")
            self.assertTrue(result.get("value") == 1, result)

        # Set both PINs of the token
        with self.app.test_request_context('/token/setpin/PToken',
                                            method="POST",
                                            data={"userpin": "test",
                                                  "sopin": "topsecret"},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value") == 2, result)

        # set a pin
        with self.app.test_request_context('/token/setpin/PToken',
                                            method="POST",
                                            data={"otppin": "test"},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value") == 1, result)

        # set an empty pin
        with self.app.test_request_context('/token/setpin/PToken',
                                            method="POST",
                                            data={"otppin": ""},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
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
            result = res.json.get("result")
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
            result = res.json.get("result")
            self.assertTrue(result.get("value") == 9, result)

        # check the values
        with self.app.test_request_context('/token/',
                                           method="GET",
                                           query_string=urlencode(
                                                   {"serial": "SET001"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
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

        # check for broken validity dates
        with self.app.test_request_context('/token/set/SET001',
                                           method="POST",
                                           data={"validity_period_start": "unknown"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400, res)
            result = res.json.get("result")
            self.assertEqual(result['error']['code'], 301, result)
            self.assertEqual(result['error']['message'],
                             "ERR301: Could not parse validity period start date!",
                             result)

    def test_10_set_token_realms(self):
        self._create_temp_token("REALM001")

        with self.app.test_request_context('/token/realm/REALM001',
                                            method="POST",
                                            data={"realms": "realm1, realm2"},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")
            self.assertTrue(value is True, result)

        with self.app.test_request_context('/token/',
                                            method="GET",
                                            query_string=urlencode({"serial": "REALM001"}),
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")
            token = value.get("tokens")[0]
            self.assertTrue(token.get("realms") == ["realm1"], token)

    def test_11_load_tokens(self):
        # Set dummy policy to verify faulty behaviour with #2209
        set_policy("dumm01", scope=SCOPE.USER, action=ACTION.DISABLE)
        # Load OATH CSV
        with self.app.test_request_context('/token/load/import.oath',
                                            method="POST",
                                            data={"type": "oathcsv",
                                                  "tokenrealms": self.realm1,
                                                  "file": (IMPORTFILE,
                                                           "import.oath")},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")['n_imported']
            self.assertTrue(value == 3, result)
        # check for a successful audit entry
        entry = self.find_most_recent_audit_entry(action='*/token/load/*')
        self.assertEqual(entry['success'], 1, entry)
        delete_policy("dumm01")

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
            result = res.json.get("result")
            value = result.get("value")['n_imported']
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
            result = res.json.get("result")
            value = result.get("value")['n_imported']
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
        # check for a failed audit entry
        entry = self.find_most_recent_audit_entry(action='*/token/load/*')
        self.assertEqual(entry['success'], 0, entry)

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
            result = res.json.get("result")
            value = result.get("value")['n_imported']
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
            result = res.json.get("result")
            value = result.get("value")['n_imported']
            self.assertTrue(value == 1, result)

    def test_11_load_tokens_tokenhandler(self):

        # create a new event to disable tokens after import
        r = set_event("token_disable", ["token_load"], "Token",
                      "disable", position="post")
        events = EventConfiguration()
        event_id = [event['id'] for event in events.events if event['name'] == 'token_disable'][0]

        # Load yubico.csv
        with self.app.test_request_context('/token/load/yubico.csv',
                                            method="POST",
                                            data={"type": "yubikeycsv",
                                                  "tokenrealms": self.realm1,
                                                  "file": (YUBICOFILE_LONG,
                                                           "yubico.csv")},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")['n_imported']
            self.assertTrue(value == 100, result)

        # check if imported tokens were disabled by event handler
        tokenobject_list = get_tokens(serial_wildcard="UBOM*", active=False)
        self.assertEqual(len(tokenobject_list), 100)

        # remove tokens
        for tok in tokenobject_list:
            remove_token(serial=tok.token.serial)
        # remove event
        delete_event(event_id)

    def test_11_load_tokens_only_to_specific_realm(self):
        # Load token to a realm
        def _clean_up_tokens():
            remove_token("token01")
            remove_token("token02")
            remove_token("token03")

        _clean_up_tokens()
        with self.app.test_request_context('/token/load/import.oath',
                                           method="POST",
                                           data={"type": "oathcsv",
                                                 "tokenrealms": self.realm1,
                                                 "file": (IMPORTFILE,
                                                          "import.oath")},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")['n_imported']
            self.assertTrue(value == 3, result)
        # Now check, if the tokens are in the realm
        from privacyidea.lib.token import get_realms_of_token
        r = get_realms_of_token("token01")
        self.assertIn(self.realm1, r)

        # Now set a policy, that allows the admin to upload the tokens into this realm
        set_policy(name="tokupload", scope=SCOPE.ADMIN, action=ACTION.IMPORT, realm=self.realm1,
                   adminuser="testadmin")
        _clean_up_tokens()
        with self.app.test_request_context('/token/load/import.oath',
                                           method="POST",
                                           data={"type": "oathcsv",
                                                 "tokenrealms": self.realm1,
                                                 "file": (IMPORTFILE,
                                                          "import.oath")},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")['n_imported']
            self.assertTrue(value == 3, result)
        # Now check, if the tokens are in the realm
        r = get_realms_of_token("token01")
        self.assertIn(self.realm1, r)

        # Now define a policy, that allows the user to upload tokens to some other realm
        set_policy(name="tokupload", scope=SCOPE.ADMIN, action=ACTION.IMPORT, realm="otherrealm",
                   adminuser="testadmin")
        _clean_up_tokens()
        with self.app.test_request_context('/token/load/import.oath',
                                           method="POST",
                                           data={"type": "oathcsv",
                                                 "tokenrealms": self.realm1,
                                                 "file": (IMPORTFILE,
                                                          "import.oath")},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 403, res)
            result = res.json.get("result")
            self.assertFalse(result.get("status"))
            self.assertEqual("Admin actions are defined, but you are not allowed to upload token files.",
                             result.get("error").get("message"))

        delete_policy("tokupload")

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
            result = res.json.get("result")
            value = result.get("value")
            self.assertTrue(value is True, result)

        with self.app.test_request_context('/token/setpin',
                                            method="POST",
                                            data={"serial": "FROM001",
                                                  "otppin": "test"},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
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
            result = res.json.get("result")
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
            result = res.json.get("result")
            value = result.get("value")
            self.assertTrue(value is True, result)

        # check in the database
        tokenobject_list = get_tokens(serial="TO001")
        token = tokenobject_list[0]
        # check the user
        self.assertEqual(token.token.first_owner.user_id, "1000")
        # check if the TO001 has a pin
        self.assertTrue(token.token.pin_hash.startswith("$argon2"))

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
            result = res.json.get("result")
            value = result.get("value")
            self.assertTrue(value is True, result)

        with self.app.test_request_context('/token/lost/LOST001',
                                            method="POST",
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
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
            result = res.json.get("result")
            value = result.get("value")
            self.assertEqual(value.get("count"), 25)
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
            result = res.json.get("result")
            value = result.get("value")
            self.assertEqual(value.get("serial"), "GETSERIAL2")

        # If one OTP values was found, it can not be used again
        with self.app.test_request_context('/token/getserial/316522',
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")
            self.assertEqual(value.get("serial"), None)


        # Will not find an assigned token
        with self.app.test_request_context('/token/getserial/413789'
                                           '?assigned=1',
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")
            self.assertNotEqual(value.get("serial"), "GETSERIAL2")

        # Will find a substr
        with self.app.test_request_context('/token/getserial/413789'
                                           '?unassigned=1&string=SERIAL',
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
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
            result = res.json.get("result")
            self.assertTrue(result.get("value"))
            detail = res.json.get("detail")
            registrationcode = detail.get("registrationcode")

        # check password
        with self.app.test_request_context('/validate/check',
                                           data={"user": "cornelius",
                                                 "pass": quote(registrationcode)},
                                           method="POST"):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"), (result, registrationcode))

        # check password again. THe second time it will fail, since the token
        # does not exist anymore.
        with self.app.test_request_context('/validate/check',
                                           data={"user": "cornelius",
                                                 "pass": quote(registrationcode)},
                                           method="POST"):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
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
                result = res.json.get("result")
                self.assertTrue(result.get("value"))
                detail = res.json.get("detail")

            token = get_tokens(serial="totp{0!s}".format(timestep))[0]
            self.assertEqual(token.timestep, int(timestep))

    def test_17_enroll_certificate(self):
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

        # Enroll a certificate token with a CSR
        with self.app.test_request_context('/token/init',
                                           data={"type": "certificate",
                                                 "request": REQUEST,
                                                 "ca": "localCA"},
                                           method="POST",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"))
            detail = res.json.get("detail")
            certificate = detail.get("certificate")
            self.assertTrue("-----BEGIN CERTIFICATE-----" in certificate)

        # Enroll a certificate token, also generating a private key
        with self.app.test_request_context('/token/init',
                                           data={"type": "certificate",
                                                 "genkey": "1",
                                                 "user": "cornelius",
                                                 "realm": self.realm1,
                                                 "ca": "localCA"},
                                           method="POST",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertTrue(result.get("value"))
            detail = json.loads(res.data.decode('utf8')).get("detail")
            self.assertIn("pkcs12", detail)

        # List tokens
        with self.app.test_request_context('/token/?type=certificate',
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertEqual(len(result["value"]["tokens"]), 2)

        # Finally we try to enroll a certificate with an attestation certificate required:
        from privacyidea.lib.tokens.certificatetoken import ACTION, REQUIRE_ACTIONS
        set_policy(name="pol1",
                   scope=SCOPE.ENROLL,
                   action="{0!s}={1!s}".format(ACTION.REQUIRE_ATTESTATION, REQUIRE_ACTIONS.REQUIRE_AND_VERIFY))
        with self.app.test_request_context('/token/init',
                                           data={"type": "certificate",
                                                 "request": REQUEST,
                                                 "ca": "localCA"},
                                           method="POST",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 403, res)
            result = res.json.get("result")
            self.assertFalse(result.get("status"))
            self.assertEqual(result.get("error").get("message"),
                             "A policy requires that you provide an attestation certificate.")

        delete_policy("pol1")


    def test_18_revoke_token(self):
        self._create_temp_token("RevToken")

        # revoke token
        with self.app.test_request_context('/token/revoke/RevToken',
                                           method='POST',
                                           data={},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
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
        self.assertEqual(r[1].get("message"), _("please enter otp: "))
        transaction_id = r[1].get("transaction_id")

        with self.app.test_request_context('/token/challenges/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
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
            result = res.json.get("result")
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
            result = res.json.get("result")
            value = result.get("value")
            self.assertEqual(value.get("count"), 0)

        # create a second challenge and a third cahllenge
        r = check_serial_pass(serial, "pin")
        r = check_serial_pass(serial, "pin")
        transaction_ids = []
        with self.app.test_request_context('/token/challenges/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")
            self.assertEqual(value.get("count"), 3)
            challenges = value.get("challenges")
            for challenge in challenges:
                # Fill the list of all transaction_ids
                transaction_ids.append(challenge.get("transaction_id"))

        # Now we only ask for the first transation id. This should return only ONE challenge
        with self.app.test_request_context('/token/challenges/',
                                            data={"transaction_id": transaction_ids[0]},
                                            method='GET',
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")
            self.assertEqual(value.get("count"), 1)
            challenges = value.get("challenges")
            self.assertEqual(challenges[0].get("transaction_id"), transaction_ids[0])

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
            result = res.json.get("result")
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
        all_admin_policies = P.list_policies()
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

        current_time = datetime.datetime.now(tzlocal())
        with mock.patch('privacyidea.lib.tokenclass.datetime') as mock_dt:
            mock_dt.now.return_value = current_time
            with self.app.test_request_context('/token/init',
                                               method='POST',
                                               data={"genkey": 1,
                                                     "pin": "123456"},
                                               headers={'Authorization': self.at}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                detail = res.json.get("detail")

                serial = detail.get("serial")
                token = get_tokens(serial=serial)[0]
                ti = token.get_tokeninfo("next_pin_change")
                self.assertEqual(ti, current_time.strftime(DATE_FORMAT))

        # If the administrator sets a PIN of the user, the next_pin_change
        # must also be created!

        token = init_token({"serial": "SP001", "type": "spass", "pin":
            "123456"})
        ti = token.get_tokeninfo("next_pin_change")
        self.assertEqual(ti, None)
        # Now we set the PIN
        current_time = datetime.datetime.now(tzlocal())
        with mock.patch('privacyidea.lib.tokenclass.datetime') as mock_dt:
            mock_dt.now.return_value = current_time
            with self.app.test_request_context('/token/setpin/SP001',
                                               method='POST',
                                               data={"otppin": "1234"},
                                               headers={'Authorization': self.at}):

                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)

                serial = "SP001"
                token = get_tokens(serial=serial)[0]
                ti = token.get_tokeninfo("next_pin_change")
                self.assertEqual(ti, current_time.strftime(DATE_FORMAT))

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
            result = res.json.get("result")
            self.assertTrue(result.get("value"), result)
        with self.app.test_request_context('/token/info/INF001/key2',
                                            method="POST",
                                            data={"value": "value 2"},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"), result)

        with self.app.test_request_context('/token/',
                                           method="GET",
                                           query_string=urlencode(
                                                   {"serial": "INF001"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")
            token = value.get("tokens")[0]
            self.assertTrue(value.get("count") == 1, result)

            tokeninfo = token.get("info")
            test_dict = {'key1': 'value 1', 'key2': 'value 2'}
            try:
                self.assertTrue(test_dict.viewitems() <= tokeninfo.viewitems())
            except AttributeError:
                self.assertTrue(test_dict.items() <= tokeninfo.items())

        # Overwrite an existing tokeninfo value
        with self.app.test_request_context('/token/info/INF001/key1',
                                            method="POST",
                                            data={"value": 'value 1 new'},
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"), result)

        with self.app.test_request_context('/token/',
                                           method="GET",
                                           query_string=urlencode(
                                                   {"serial": "INF001"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")
            token = value.get("tokens")[0]
            self.assertTrue(value.get("count") == 1, result)

            tokeninfo = token.get("info")
            test_dict = {'key1': 'value 1 new', 'key2': 'value 2'}
            try:
                self.assertTrue(test_dict.viewitems() <= tokeninfo.viewitems())
            except AttributeError:
                self.assertTrue(test_dict.items() <= tokeninfo.items())

        # Delete an existing tokeninfo value
        with self.app.test_request_context('/token/info/INF001/key1',
                                           method="DELETE",
                                           headers={'Authorization': self.at}):
           res = self.app.full_dispatch_request()
           self.assertTrue(res.status_code == 200, res)
           result = res.json.get("result")
           self.assertTrue(result.get("value"), result)

        # Delete a non-existing tokeninfo value
        with self.app.test_request_context('/token/info/INF001/key1',
                                            method="DELETE",
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"), result)

        # Try to delete with an unknown serial
        with self.app.test_request_context('/token/info/UNKNOWN/key1',
                                            method="DELETE",
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 404)
            result = res.json.get("result")
            self.assertFalse(result.get("status"))

        # Check that the tokeninfo is correct
        with self.app.test_request_context('/token/',
                                           method="GET",
                                           query_string=urlencode(
                                               {"serial": "INF001"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")
            token = value.get("tokens")[0]
            self.assertTrue(value.get("count") == 1, result)

            tokeninfo = token.get("info")
            try:
                self.assertTrue({'key2': 'value 2'}.viewitems() <= tokeninfo.viewitems())
            except AttributeError:
                self.assertTrue({'key2': 'value 2'}.items() <= tokeninfo.items())
            self.assertNotIn('key1', tokeninfo)

    def test_25_user_init_defaults(self):
        self.setUp_user_realms()
        self.authenticate_selfservice_user()
        # Now this user is authenticated as selfservice@realm1

        # first test with system configuration
        set_privacyidea_config('totp.hashlib', 'sha512')
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={
                                               "type": "totp",
                                               "genkey": 1,
                                               "user": "selfservice",
                                               "realm": "realm1"},
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(res.json.get('result').get("value"))
            detail = res.json.get("detail")
            googleurl = detail.get("googleurl")
            # TODO: The google URL states no hashlib (which means sha1) but the
            #       actual hashlib is sha512 since no hashlib parameter was
            #       send in the request.
            #       This is wrong and needs to be fixed in hotptoken.py:253
            self.assertFalse("sha1" in googleurl.get("value"))
            serial = detail.get("serial")
            token = get_tokens(serial=serial)[0]
            self.assertEqual(token.hashlib, "sha512")
            self.assertEqual(token.timestep, 30)
            self.assertEqual(token.token.otplen, 6)
            remove_token(serial)

        # Now create policy for sha256, overwriting the system config
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
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value"))
            detail = res.json.get("detail")
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
            result = res.json.get("result")
            self.assertTrue(result.get("value"))
            detail = res.json.get("detail")
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
            result = res.json.get("result")
            self.assertTrue(result.get("value"))
            detail = res.json.get("detail")
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
            data = res.json
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
            self.assertEqual(len(codecs.decode(seed, 'hex')), 42)
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
            result = res.json.get("result")
            self.assertEqual(result.get("status"), False)
            self.assertEqual(result.get("error").get("code"), 905)

    def test_28_enroll_app_with_image_url(self):
        set_policy("imgurl", scope=SCOPE.ENROLL,
                   action="{0!s}=https://example.com/img.png".format(ACTION.APPIMAGEURL))
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "genkey": "1",
                                                 "realm": self.realm1,
                                                 "serial": "goog1",
                                                 "pin": "test"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))
            self.assertTrue('image=https%3A//example.com/img.png' in detail.get("googleurl").get("value"),
                            detail.get("googleurl"))

        remove_token("goog1")
        delete_policy("imgurl")

    def test_29_user_set_description(self):
        self.authenticate_selfservice_user()
        # create a token for the user
        r = init_token({"serial": "SETDESC01",
                        "otpkey": self.otpkey},
                       user=User("selfservice", "realm1"))
        self.assertTrue(r)

        # create a token, that does not belong to the user
        r = init_token({"serial": "SETDESC02",
                        "otpkey": self.otpkey})
        self.assertTrue(r)

        # policy: allow user to set description
        set_policy(name="SETDESCPOL", scope=SCOPE.USER,
                   action=ACTION.SETDESCRIPTION)

        # successful set description on own token
        with self.app.test_request_context('/token/description/SETDESC01',
                                           method='POST',
                                           data={"description": "New Token"},
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertEqual(result.get("value"), 1)

        # check the description of the token
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           data={"serial": "SETDESC01"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertEqual(result.get("value").get("tokens")[0].get("description"),
                             "New Token")

        # fail to set description on foreign token
        with self.app.test_request_context('/token/description',
                                           method='POST',
                                           data={"serial": "SETDESC02",
                                                 "description": "new token"},
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 404, res)
            result = res.json.get("result")
            self.assertFalse(result.get("status"))
            self.assertEqual(result.get("error").get("message"),
                             "The requested token could not be found.")

        # cleanup
        delete_policy("SETDESCPOL")
        remove_token("SETDESC01")
        remove_token("SETDESC02")

    def test_30_force_app_pin(self):
        set_policy("app_pin", scope=SCOPE.ENROLL,
                   action={"hotp_" + ACTION.FORCE_APP_PIN: True,
                           "totp_" + ACTION.FORCE_APP_PIN: True})
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "genkey": "1",
                                                 "realm": self.realm1,
                                                 "serial": "goog2",
                                                 "type": 'TOTP',
                                                 "pin": "test"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json["result"]
            detail = res.json["detail"]
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))
            self.assertTrue('pin=True' in detail.get("googleurl").get("value"),
                            detail.get("googleurl"))

        remove_token("goog2")
        delete_policy('app_pin')

    def test_31_invalid_serial(self):
        # Run a test with an invalid serial
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"serial": "invalid/character",
                                                 "genkey": 1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)
            result = res.json.get("result")
            self.assertTrue("Invalid serial number" in result.get("error").get("message"))

    def test_32_set_random_pin(self):
        t = init_token({"genkey": 1})
        self.assertEqual(t.token.tokentype, "hotp")

        # We get an error, if there is no policy
        with self.app.test_request_context('/token/setrandompin',
                                           method='POST',
                                           data={"serial": t.token.serial},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)
            result = res.json.get("result")
            self.assertIn("You need to specify a policy 'otp_pin_set_random' in scope admin.",
                          result.get("error").get("message"))

        # Admin policy: admin is allowed to set random pin
        set_policy("allowed_to_set_pin", scope=SCOPE.ADMIN, action="{0!s}".format(ACTION.SETRANDOMPIN))
        # at least we need a otppinrandom policy (but not with length 0
        set_policy("pinpolrandom", scope=SCOPE.ADMIN, action="{0!s}=0".format(ACTION.OTPPINSETRANDOM))

        with self.app.test_request_context('/token/setrandompin',
                                           method='POST',
                                           data={"serial": t.token.serial},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)
            result = res.json.get("result")
            self.assertIn("We have an empty PIN. Please check your policy 'otp_pin_set_random'.",
                          result.get("error").get("message"))

        # at least we need a otppinrandom policy
        set_policy("pinpolrandom", scope=SCOPE.ADMIN, action="{0!s}=10".format(ACTION.OTPPINSETRANDOM))

        with self.app.test_request_context('/token/setrandompin',
                                           method='POST',
                                           data={"serial": t.token.serial},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertEqual(10, len(detail.get("pin")))

        # What happens, if we have two contradicting policies:
        set_policy("pinpolrandom2", scope=SCOPE.ADMIN, action="{0!s}=9".format(ACTION.OTPPINSETRANDOM))

        with self.app.test_request_context('/token/setrandompin',
                                           method='POST',
                                           data={"serial": t.token.serial},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 403, res)
            result = res.json.get("result")
            # contradicting values
            self.assertEqual(303, result.get("error").get("code"))

        # Now we adapt the priority of the policies:
        set_policy("pinpolrandom2", scope=SCOPE.ADMIN, action="{0!s}=9".format(ACTION.OTPPINSETRANDOM), priority=1)
        set_policy("pinpolrandom", scope=SCOPE.ADMIN, action="{0!s}=10".format(ACTION.OTPPINSETRANDOM), priority=2)

        with self.app.test_request_context('/token/setrandompin',
                                           method='POST',
                                           data={"serial": t.token.serial},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            detail = res.json.get("detail")
            self.assertEqual(9, len(detail.get("pin")))

        delete_policy("allowed_to_set_pin")
        delete_policy("pinpolrandom")
        delete_policy("pinpolrandom2")

    def test_33_hide_tokeninfo_user(self):
        set_policy(name="hide_tokeninfo_user",
                   scope=SCOPE.USER,
                   action="{0!s}=tokenkind unknown".format(ACTION.HIDE_TOKENINFO))
        t = init_token({"genkey": 1}, tokenkind='testing',
                       user=User('cornelius', realm=self.realm1))
        add_tokeninfo(t.token.serial, 'blabla', value='SomeValue')
        for i in ['blabla', 'tokenkind']:
            self.assertIn(i, t.get_tokeninfo(), t.get_tokeninfo())

        # check that the admin user can see all tokeninfo
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           data={'serial': t.token.serial},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            result = res.json.get("result")
            self.assertTrue(result.get('status'), result)
            toks = result.get('value').get('tokens')
            self.assertEqual(1, len(toks), toks)
            tok = toks[0]
            self.assertEqual('testing', tok.get('info').get('tokenkind'), tok)
            self.assertEqual('SomeValue', tok.get('info').get('blabla'), tok)

        # check that the "tokenkind" tokeninfo is hidden when calling as user
        with self.app.test_request_context('/auth',
                                           data={"username": 'cornelius',
                                                 "password": 'test'},
                                           method='POST'):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            user_token = result.get("value").get("token")
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           data={'serial': t.token.serial},
                                           headers={'Authorization': user_token}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            result = res.json.get("result")
            self.assertTrue(result.get('status'), result)
            toks = result.get('value').get('tokens')
            self.assertEqual(1, len(toks), toks)
            tok = toks[0]
            self.assertEqual('SomeValue', tok.get('info').get('blabla'), tok)
            self.assertNotIn('tokenkind', tok.get('info'), tok)

        delete_policy('hide_tokeninfo_user')

    def test_34_hide_tokeninfo_admin(self):
        set_policy(name="hide_tokeninfo_admin",
                   scope=SCOPE.ADMIN,
                   action="{0!s}=tokenkind unknown, {1!s}".format(ACTION.HIDE_TOKENINFO,
                                                                  ACTION.TOKENLIST))
        t = init_token({"genkey": 1}, tokenkind='testing')
        add_tokeninfo(t.token.serial, 'blabla', value='SomeValue')
        for i in ['blabla', 'tokenkind']:
            self.assertIn(i, t.get_tokeninfo(), t.get_tokeninfo())

        # check that the admin user can't see the tokenkind info
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           data={'serial': t.token.serial},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            result = res.json.get("result")
            self.assertTrue(result.get('status'), result)
            toks = result.get('value').get('tokens')
            self.assertEqual(1, len(toks), toks)
            tok = toks[0]
            self.assertEqual('SomeValue', tok.get('info').get('blabla'), tok)
            self.assertNotIn('tokenkind', tok.get('info'), tok)

        delete_policy('hide_tokeninfo_admin')

    def test_40_init_verify_hotp_token(self):
        set_policy("verify_toks1", scope=SCOPE.ENROLL, action="{0!s}=hotp top".format(ACTION.VERIFY_ENROLLMENT))
        set_policy("verify_toks2", scope=SCOPE.ENROLL, action="{0!s}=HOTP email".format(ACTION.VERIFY_ENROLLMENT))
        set_policy("require_description", scope=SCOPE.ENROLL, action="{0!s}=hotp".format(ACTION.REQUIRE_DESCRIPTION))
        # Enroll an HOTP token
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"otpkey": self.otpkey},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(403, res.status_code)
            result = res.json.get("result")
            self.assertFalse(result.get("status"))
            self.assertEqual("Description required for hotp token.", result.get("error").get("message"))

        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"otpkey": self.otpkey,
                                                 "description": "something"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            detail = res.json.get("detail")
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))
            self.assertEqual(detail.get("rollout_state"), ROLLOUTSTATE.VERIFYPENDING)
            self.assertEqual(detail.get("verify").get("message"), VERIFY_ENROLLMENT_MESSAGE)
            serial = detail.get("serial")
            tokenobj_list = get_tokens(serial=serial)
            # Check the token rollout state
            self.assertEqual(tokenobj_list[0].token.rollout_state, ROLLOUTSTATE.VERIFYPENDING)

        # Try to authenticate with this not readily enrolled token and fail
        with self.app.test_request_context('/validate/check',
                                           method='POST',
                                           data={'serial': serial,
                                                 'pass': self.valid_otp_values[0]}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            # we fail to authenticate with a token, that is in state verify_pending
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"))
            self.assertEqual(detail.get("message"), "matching 1 tokens, Token is not yet enrolled")

        # Now run the second step: verify enrollment, but fail with a wrong OTP value
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"serial": serial,
                                                 "verify": "111111"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(400, res.status_code)
            result = res.json.get("result")
            self.assertFalse(result.get("status"))
            self.assertEqual(result.get("error").get("code"), 905)
            self.assertEqual(result.get("error").get("message"), "ERR905: Verification of the new token failed.")

        # Now run the second step: verify enrollment and test again
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"serial": serial,
                                                 "verify": self.valid_otp_values[1]},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))
            tokenobj_list = get_tokens(serial=serial)
            # Check the token rollout state, it is empty now.
            self.assertEqual(ROLLOUTSTATE.ENROLLED, tokenobj_list[0].token.rollout_state)

        delete_policy("verify_toks1")
        delete_policy("verify_toks2")
        delete_policy("require_description")

    def test_41_init_verify_email_token(self):
        set_policy("verify_toks1", scope=SCOPE.ENROLL, action="{0!s}=email".format(ACTION.VERIFY_ENROLLMENT))
        # Enroll an email token
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"otpkey": self.otpkey,
                                                 "type": "email",
                                                 "email": "user@example.com"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            detail = res.json.get("detail")
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))
            self.assertEqual(detail.get("rollout_state"), ROLLOUTSTATE.VERIFYPENDING)
            self.assertEqual(detail.get("verify").get("message"), VERIFY_ENROLLMENT_MESSAGE)
            serial = detail.get("serial")
            tokenobj_list = get_tokens(serial=serial)
            # Check the token rollout state
            self.assertEqual(tokenobj_list[0].token.rollout_state, ROLLOUTSTATE.VERIFYPENDING)

        # Now run the second step: verify enrollment and test again
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"serial": serial,
                                                 "type": "email",
                                                 "verify": self.valid_otp_values[1]},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))
            tokenobj_list = get_tokens(serial=serial)
            # Check the token rollout state, it is empty now.
            self.assertEqual(ROLLOUTSTATE.ENROLLED, tokenobj_list[0].token.rollout_state)

        delete_policy("verify_toks1")

    def test_42_init_verify_sms_token(self):
        set_policy("verify_toks1", scope=SCOPE.ENROLL, action="{0!s}=sms".format(ACTION.VERIFY_ENROLLMENT))
        # Enroll an email token
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"otpkey": self.otpkey,
                                                 "type": "sms",
                                                 "phone": "+123456"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            detail = res.json.get("detail")
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))
            self.assertEqual(detail.get("rollout_state"), ROLLOUTSTATE.VERIFYPENDING)
            self.assertEqual(detail.get("verify").get("message"), VERIFY_ENROLLMENT_MESSAGE)
            serial = detail.get("serial")
            tokenobj_list = get_tokens(serial=serial)
            # Check the token rollout state
            self.assertEqual(tokenobj_list[0].token.rollout_state, ROLLOUTSTATE.VERIFYPENDING)

        # Now run the second step: verify enrollment and test again
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"serial": serial,
                                                 "type": "sms",
                                                 "verify": self.valid_otp_values[1]},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))
            tokenobj_list = get_tokens(serial=serial)
            # Check the token rollout state, it is empty now.
            self.assertEqual(ROLLOUTSTATE.ENROLLED, tokenobj_list[0].token.rollout_state)

        delete_policy("verify_toks1")

    def test_43_init_verify_index_token(self):
        set_policy("verify_toks1", scope=SCOPE.ENROLL, action="{0!s}=indexedsecret".format(ACTION.VERIFY_ENROLLMENT))
        # Enroll an indexed secret token
        SECRET = "ABCDEFGHIJHK"
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"otpkey": SECRET,
                                                 "type": "indexedsecret"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            detail = res.json.get("detail")
            secret = detail.get("otpkey").get("value").split("/")[2]
            result = res.json.get("result")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))
            self.assertEqual(SECRET, secret)
            self.assertEqual(detail.get("rollout_state"), ROLLOUTSTATE.VERIFYPENDING)
            message = detail.get("verify").get("message")
            self.assertTrue(message.startswith("Please enter the positions"))
            serial = detail.get("serial")
            tokenobj_list = get_tokens(serial=serial)
            # Check the token rollout state
            self.assertEqual(tokenobj_list[0].token.rollout_state, ROLLOUTSTATE.VERIFYPENDING)
            s_pos = message.strip("Please enter the positions ").strip(" from your secret.")
            positions = [int(x) for x in s_pos.split(",")]

        # Now run the second step: verify enrollment and test again
        otp = ""
        for x in positions:
            otp += secret[x-1]
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={"serial": serial,
                                                 "type": "indexedsecret",
                                                 "verify": otp},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertTrue(result.get("status"))
            self.assertTrue(result.get("value"))
            tokenobj_list = get_tokens(serial=serial)
            # Check the token rollout state, it is empty now.
            self.assertEqual(ROLLOUTSTATE.ENROLLED, tokenobj_list[0].token.rollout_state)

        delete_policy("verify_toks1")

    def test_44_init_token_with_required_description(self):
        # set require_description policy with value = 'hotp'
        set_policy(name="require_description",
                   scope=SCOPE.ENROLL,
                   action=["{0!s}=hotp".format(ACTION.REQUIRE_DESCRIPTION)])
        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={
                                               "otpkey": self.otpkey,
                                               "type": "hotp"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            # a policyerror should be raised because hotp needs a description
            self.assertEqual(result.get("error").get("message"),
                             "Description required for hotp token.")

        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={
                                               "otpkey": self.otpkey,
                                               "type": "hotp",
                                               "description": "test"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            # description is set, token should be rolled out
            self.assertTrue(res.status_code == 200, res)

        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={
                                               "otpkey": self.otpkey,
                                               "type": "totp"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            # check if rollout work as expected, if the token-type is not specified in require_description_pol
            self.assertTrue(res.status_code == 200, res)

        with self.app.test_request_context('/token/init',
                                           method='POST',
                                           data={
                                               "otpkey": self.otpkey,
                                               "description": "test"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            # check if rollout work as expected with no type set.
            self.assertTrue(res.status_code == 200, res)

        delete_policy("require_description")


class API00TokenPerformance(MyApiTestCase):

    token_count = 21

    def test_00_create_some_tokens(self):
        for i in range(0, self.token_count):
            init_token({"genkey": 1, "serial": "perf{0!s:0>3}".format(i)})
        toks = get_tokens(serial_wildcard="perf*")
        self.assertEqual(len(toks), self.token_count)

        for i in range(0,10):
            init_token({"genkey": 1, "serial": "TOK{0!s:0>3}".format(i)})
        toks = get_tokens(serial_wildcard="TOK*")
        self.assertEqual(len(toks), 10)

        self.setUp_user_realms()

    def test_01_number_of_tokens(self):
        # The GET /token returns a wildcard 100 tokens
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           data={"serial": "perf*"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value").get("count"), self.token_count)

        init_token({"genkey": 1, "serial": "realmtoken"}, tokenrealms=[self.realm1])
        toks = get_tokens(realm="*realm1*")
        self.assertEqual(len(toks), 1)

        # Request tokens in tokenrealm
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           data={"tokenrealm": "**"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            # Even if we fetch tokenrealm=** we also get all the tokens without a tokenrealm
            self.assertEqual(result.get("value").get("count"), self.token_count + 10 + 1)

        with self.app.test_request_context('/token/',
                                           method='GET',
                                           data={"tokenrealm": "*alm1*"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value").get("count"), 1)

        remove_token(serial="realmtoken")

    def test_02_several_requests(self):
        # Run GET challenges
        with self.app.test_request_context('/token/challenges/*',
                                           method='GET',
                                           data={"serial": "perf*"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result.get("value").get("count"), 0)

        # Run POST assign with a wildcard. This shall not assign.
        with self.app.test_request_context('/token/assign',
                                           method='POST',
                                           data={"user": "cornelius",
                                                 "realm": self.realm1,
                                                 "serial": "perf*",
                                                 "pin": "test"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 404)
            result = res.json.get("result")
            # Of course there is no exact token "perf*"
            self.assertFalse(result["status"])

        # run POST unassign with a wildcard. This shall not unassign
        from privacyidea.lib.token import assign_token, unassign_token
        assign_token("perf001", User("cornelius", self.realm1))
        with self.app.test_request_context('/token/unassign',
                                           method='POST',
                                           data={"serial": "perf*",
                                                 "pin": "test"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 404)
            result = res.json.get("result")
            # Of course there is no exact token "perf*", it does not match perf001
            self.assertFalse(result["status"])

        # Now we unassign the token anyways
        unassign_token("perf001")

        # run POST revoke with a wildcard
        with self.app.test_request_context('/token/revoke',
                                           method='POST',
                                           data={"serial": "perf*",
                                                 "pin": "test"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 404)
            result = res.json.get("result")
            # Of course there is no exact token "perf*", it does not match perf001
            self.assertFalse(result["status"])

        # run POST enable and disable with a wildcard
        with self.app.test_request_context('/token/disable',
                                           method='POST',
                                           data={"serial": "perf*"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 404)
            result = res.json.get("result")
            # Of course there is no exact token "perf*", it does not match perf001
            self.assertFalse(result["status"])

        with self.app.test_request_context('/token/enable',
                                           method='POST',
                                           data={"serial": "perf*"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 404)
            result = res.json.get("result")
            # Of course there is no exact token "perf*", it does not match perf001
            self.assertFalse(result["status"])

        # run DELETE /token with a wildcard
        with self.app.test_request_context('/token/perf*',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 404)
            result = res.json.get("result")
            # Of course there is no exact token "perf*", it does not match perf001
            self.assertFalse(result["status"])

        # run reset failcounter
        with self.app.test_request_context('/token/reset/perf*',
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 404)
            result = res.json.get("result")
            # Of course there is no exact token "perf*", it does not match perf001
            self.assertFalse(result["status"])

        # run reset failcounter
        with self.app.test_request_context('/token/resync/perf*',
                                           method='POST', data={"otp1": "123454",
                                                                "otp2": "123454"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code, 404)
            result = res.json.get("result")
            # Of course there is no exact token "perf*", it does not match perf001
            self.assertFalse(result["status"])

        # Try to set pin
        with self.app.test_request_context('/token/setpin/perf*',
                                           method='POST', data={"otppin": "123454"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 404)
            result = res.json.get("result")
            # Of course there is no exact token "perf*", it does not match perf001
            self.assertFalse(result["status"])

        # Try to set description
        with self.app.test_request_context('/token/set/perf*',
                                           method='POST', data={"description": "general token"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 404)
            result = res.json.get("result")
            # Of course there is no exact token "perf*", it does not match perf001
            self.assertFalse(result["status"])

        # Try to set realm
        with self.app.test_request_context('/token/realm/perf*',
                                           method='POST', data={"realms": self.realm1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 404)
            result = res.json.get("result")
            # Of course there is no exact token "perf*", it does not match perf001
            self.assertFalse(result["status"])

        # Try to copy the pin
        with self.app.test_request_context('/token/copypin',
                                           method='POST',
                                           data={"from": "perf*",
                                                 "to": "perf*"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)
            result = res.json.get("result")
            # Of course there is no exact token "perf*", it does not match perf001
            self.assertEqual(result.get("error").get("code"), 1016)
            self.assertEqual(result.get("error").get("message"), "ERR1016: No unique token to copy from found")

        with self.app.test_request_context('/token/copypin',
                                           method='POST',
                                           data={"from": "perf001",
                                                 "to": "perf*"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)
            result = res.json.get("result")
            # Of course there is no exact token "perf*", it does not match perf001
            self.assertEqual(result.get("error").get("code"), 1017)
            self.assertEqual(result.get("error").get("message"), "ERR1017: No unique token to copy to found")

        # Try to copy the user
        with self.app.test_request_context('/token/copyuser',
                                           method='POST',
                                           data={"from": "perf*",
                                                 "to": "perf*"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)
            result = res.json.get("result")
            # Of course there is no exact token "perf*", it does not match perf001
            self.assertEqual(result.get("error").get("code"), 1016)
            self.assertEqual(result.get("error").get("message"), "ERR1016: No unique token to copy from found")

        # Try to copy the user
        with self.app.test_request_context('/token/copyuser',
                                           method='POST',
                                           data={"from": "perf001",
                                                 "to": "perf*"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)
            result = res.json.get("result")
            # Of course there is no exact token "perf*", it does not match perf001
            self.assertEqual(result.get("error").get("code"), 1017)
            self.assertEqual(result.get("error").get("message"), "ERR1017: No unique token to copy to found")



        # Try to mark wildcard token as lost
        # Just to be clear, all tokens are assigned to the user cornelius
        for i in range(0,self.token_count):
            assign_token("perf{0!s:0>3}".format(i), User("cornelius", self.realm1))

        with self.app.test_request_context('/token/lost/perf*',
                                           method='POST',
                                           data={},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 404)
            result = res.json.get("result")
            # Of course there is no exact token "perf*", it does not match perf001
            self.assertFalse(result["status"])

        # unassign tokens again
        for i in range(0,self.token_count):
            unassign_token("perf{0!s:0>3}".format(i))

        # Try to set tokeninfo
        with self.app.test_request_context('/token/info/perf*/newkey',
                                           method='POST',
                                           data={"value": "newvalue"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 404)
            result = res.json.get("result")
            # Of course there is no exact token "perf*", it does not match perf001
            self.assertFalse(result["status"])

            toks = get_tokens(tokeninfo={"newkey": "newvalue"})
            # No token reveived this value!
            self.assertEqual(len(toks), 0)

        # Try to delete tokeninfo
        with self.app.test_request_context('/token/info/perf*/newkey',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 404)
            result = res.json.get("result")
            # Of course there is no exact token "perf*", it does not match perf001
            self.assertFalse(result["status"])


class APIDetermine_User_from_Serial_for_Policies(MyApiTestCase):
    """
    This Testclass verifies if a request, that only contains a serial will also
    honour policies, that are configured for users, if the serial is assigned to such a user.
    """

    def test_00_setup(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()

    def test_01_disabling_token(self):
        serial = "SPASS001"
        polname = "disabletokens"

        t = init_token({"type": "spass", "serial": serial}, user=User("cornelius", self.realm1))

        # We are using the "testadmin"
        with self.app.test_request_context('/token/disable',
                                           method='POST',
                                           data={"serial": serial},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            # One token disabled
            self.assertEqual(1, result.get("value"))

        enable_token(serial)
        # create a policy for realm1, the admin is allowed to disable the token
        set_policy(polname, scope=SCOPE.ADMIN, action=ACTION.DISABLE, realm=self.realm1, adminuser="testadmin")

        with self.app.test_request_context('/token/disable',
                                           method='POST',
                                           data={"serial": serial},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = res.json.get("result")
            # One token disabled
            self.assertEqual(1, result.get("value"))

        enable_token(serial)
        # change the policy for realm2, the admin is NOT allowed to disable the token
        set_policy(polname, scope=SCOPE.ADMIN, action=ACTION.DISABLE, realm=self.realm2, adminuser="testadmin")

        with self.app.test_request_context('/token/disable',
                                           method='POST',
                                           data={"serial": serial},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403)
            result = res.json.get("result")
            # One token disabled
            self.assertFalse(result.get("status"))
            self.assertEqual(303, result.get("error").get("code"))
            self.assertEqual("Admin actions are defined, but the action disable is not allowed!",
                             result.get("error").get("message"))

        remove_token(serial)
        delete_policy(polname)


class APIRolloutState(MyApiTestCase):

    def setUp(self):
        super(APIRolloutState, self).setUp()
        self.setUp_user_realms()

    def test_01_enroll_two_tokens(self):
        r = init_token({"2stepinit": 1,
                        "genkey": 1})
        self.assertEqual(r.rollout_state, ROLLOUTSTATE.CLIENTWAIT)
        serial1 = r.token.serial

        r = init_token({"genkey": 1})
        self.assertEqual(r.rollout_state, "")
        serial2 = r.token.serial

        # There are two tokens enrolled
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            # we have two tokens
            self.assertEqual(2, result.get("value").get("count"))

        # Only one token in the rollout state client_wait
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           data={"rollout_state": ROLLOUTSTATE.CLIENTWAIT},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            # we have one token
            self.assertEqual(1, result.get("value").get("count"))
            tok = result.get("value").get("tokens")[0]
            self.assertEqual(ROLLOUTSTATE.CLIENTWAIT, tok.get("rollout_state"))
            self.assertEqual(serial1, tok.get("serial"))

        # Test wildcard rollout_state filter
        r = init_token({"genkey": 1})
        self.assertEqual(r.rollout_state, "")
        serial3 = r.token.serial
        # Set a dummy rollout state
        r.token.rollout_state = "special"
        r.token.save()

        # Find rollout state "cliEntwait" and "spEcial"
        with self.app.test_request_context('/token/',
                                           method='GET',
                                           data={"rollout_state": "*e*"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            # we have two tokens
            self.assertEqual(2, result.get("value").get("count"))
            # We are not sure about the ordering. But one is serial1 and the other is serial3.
            tok = result.get("value").get("tokens")[0]
            self.assertIn(tok.get("serial"), [serial1, serial3])
            tok = result.get("value").get("tokens")[1]
            self.assertIn(tok.get("serial"), [serial1, serial3])


class APIMSCACertTestCase(MyApiTestCase):

    @unittest.skipUnless("privacyidea.lib.caconnectors.msca.MSCAConnector" in AvailableCAConnectors,
                         "Can not test MSCA. grpc module seems not available.")
    def test_00_setup(self):
        self.setUp_user_realms()
        # setup ca connector
        CONF["type"] = "microsoft"
        CONF["caconnector"] = "billCA"
        r = save_caconnector(CONF)
        self.assertEqual(r, 1)

    @unittest.skipUnless("privacyidea.lib.caconnectors.msca.MSCAConnector" in AvailableCAConnectors,
                         "Can not test MSCA. grpc module seems not available.")
    def test_01_msca_certificate_pending_and_enrolled(self):
        with mock.patch.object(MSCAConnector, "_connect_to_worker") as mock_conncect_worker:
            # Mock the CA to simulate a Pending Request - disposition 5
            mock_conncect_worker.return_value = CAServiceMock(CONF,
                                                              {"available_cas": MOCK_AVAILABLE_CAS,
                                                               "ca_templates": MOCK_CA_TEMPLATES,
                                                               "csr_disposition": 5,
                                                               "certificate": CERTIFICATE})
            # Issue a cert request to billCA for a ApprovalRequired Token.
            cert_tok = init_token({"type": "certificate",
                                   "ca": "billCA",
                                   "template": "ApprovalRequired",
                                   "genkey": 1,
                                   "user": "cornelius",
                                   "realm": self.realm1
                                   }, User("cornelius", self.realm1))
            self.assertEqual("certificate", cert_tok.type)
            self.assertEqual(ROLLOUTSTATE.PENDING, cert_tok.rollout_state)

            # Fetch the rolloutstate by fetching the token
            with self.app.test_request_context('/token/?serial={0!s}'.format(cert_tok.token.serial),
                                               method='GET',
                                               headers={'Authorization': self.at}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = res.json.get("result")
                token = result.get("value").get("tokens")[0]
                # certificate is still pending
                self.assertEqual(ROLLOUTSTATE.PENDING, token.get("rollout_state"))

            # Enroll the certificated
            mock_conncect_worker.return_value.disposition = 3

            # Fetch the rolloutstate again, now the token is enrolled
            with self.app.test_request_context('/token/?serial={0!s}'.format(cert_tok.token.serial),
                                               method='GET',
                                               headers={'Authorization': self.at}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = res.json.get("result")
                token = result.get("value").get("tokens")[0]
                # certificate is still pending
                self.assertEqual(ROLLOUTSTATE.ENROLLED, token.get("rollout_state"))

    @unittest.skipUnless("privacyidea.lib.caconnectors.msca.MSCAConnector" in AvailableCAConnectors,
                         "Can not test MSCA. grpc module seems not available.")
    def test_02_msca_certificate_pending_and_denied(self):
        with mock.patch.object(MSCAConnector, "_connect_to_worker") as mock_conncect_worker:
            # Mock the CA to simulate a Pending Request - disposition 5
            mock_conncect_worker.return_value = CAServiceMock(CONF,
                                                              {"available_cas": MOCK_AVAILABLE_CAS,
                                                               "ca_templates": MOCK_CA_TEMPLATES,
                                                               "csr_disposition": 5,
                                                               "certificate": CERTIFICATE})
            # Issue a cert request to billCA for a ApprovalRequired Token.
            cert_tok = init_token({"type": "certificate",
                                   "ca": "billCA",
                                   "template": "ApprovalRequired",
                                   "genkey": 1,
                                   "user": "cornelius",
                                   "realm": self.realm1
                                   }, User("cornelius", self.realm1))
            self.assertEqual("certificate", cert_tok.type)
            self.assertEqual(ROLLOUTSTATE.PENDING, cert_tok.rollout_state)

            # Fetch the rolloutstate by fetching the token
            with self.app.test_request_context('/token/?serial={0!s}'.format(cert_tok.token.serial),
                                               method='GET',
                                               headers={'Authorization': self.at}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = res.json.get("result")
                token = result.get("value").get("tokens")[0]
                # certificate is still pending
                self.assertEqual(ROLLOUTSTATE.PENDING, token.get("rollout_state"))

            # Enroll the certificated
            mock_conncect_worker.return_value.disposition = 2

            # Fetch the rolloutstate again, now the token is enrolled
            with self.app.test_request_context('/token/?serial={0!s}'.format(cert_tok.token.serial),
                                               method='GET',
                                               headers={'Authorization': self.at}):
                res = self.app.full_dispatch_request()
                self.assertTrue(res.status_code == 200, res)
                result = res.json.get("result")
                token = result.get("value").get("tokens")[0]
                # certificate is still pending
                self.assertEqual(ROLLOUTSTATE.DENIED, token.get("rollout_state"))


class APITokengroupTestCase(MyApiTestCase):

    def setUp(self):
        super(APITokengroupTestCase, self).setUp()
        self.setUp_user_realms()

    def test_01_add_tokengroups(self):
        serial = "testtok1"
        with self.app.test_request_context('/tokengroup/gruppe1',
                                           data={"description": "My Cool first group"},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = res.json['result']['value']
            self.assertGreaterEqual(value, 1)

        # Add a 2nd group
        with self.app.test_request_context('/tokengroup/gruppe2',
                                           data={"description": "My Cool first group"},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = res.json['result']['value']
            self.assertGreaterEqual(value, 1)

        init_token({"serial": serial, "type": "spass"})

        # Assign token to tokengroup
        with self.app.test_request_context('/token/group/{0!s}/gruppe1'.format(serial),
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = res.json['result']['value']
            self.assertGreaterEqual(value, 1)

        # Check token, there is the tokengroup "gruppe1"
        with self.app.test_request_context('/token/?serial={0!s}'.format(serial),
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = res.json['result']['value']
            tok = value["tokens"][0]
            self.assertEqual(tok.get("tokengroup"), ["gruppe1"])

        # Delete the tokengroup from the token
        with self.app.test_request_context('/token/group/{0!s}/gruppe1'.format(serial),
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = res.json['result']['value']
            self.assertEqual(value, 1)

        # Check token, there is no tokengroup
        with self.app.test_request_context('/token/?serial={0!s}'.format(serial),
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = res.json['result']['value']
            tok = value["tokens"][0]
            self.assertEqual(tok.get("tokengroup"), [])

        # Now assign the tokengroup grupp1 again.
        with self.app.test_request_context('/token/group/{0!s}/gruppe1'.format(serial),
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = res.json['result']['value']
            self.assertGreaterEqual(value, 1)

        # Now use the generic endpoint to SET tokengroups. We set "gruppe2", this will also remove "gruppe1"
        with self.app.test_request_context('/token/group/{0!s}'.format(serial),
                                           method='POST',
                                           data={"groups": ["gruppe2"]},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = res.json['result']['value']
            self.assertGreaterEqual(value, 1)
        # Check that the token has gruppe2 assigned and not gruppe1
        with self.app.test_request_context('/token/?serial={0!s}'.format(serial),
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            value = res.json['result']['value']
            tok = value["tokens"][0]
            self.assertEqual(tok.get("tokengroup"), ["gruppe2"])

        remove_token(serial)

    def test_02_non_existing_groups(self):
        serial = "testtok2"
        init_token({"serial": serial, "type": "spass"})

        # Assign token to non-existing tokengroup
        with self.app.test_request_context('/token/group/{0!s}/gaga'.format(serial),
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 404, res)
            result = res.json['result']
            self.assertFalse(result.get("status"))
            self.assertEqual(result.get("error").get("code"), 601)
            self.assertEqual(result.get("error").get("message"), "The tokengroup does not exist.")

        # Delete a non-existing tokengroup from the token
        with self.app.test_request_context('/token/group/{0!s}/gaga'.format(serial),
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 404, res)
            result = res.json['result']
            self.assertFalse(result.get("status"))
            self.assertEqual(result.get("error").get("code"), 601)
            self.assertEqual(result.get("error").get("message"), "The tokengroup does not exist.")

        remove_token(serial)

