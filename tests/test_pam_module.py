"""
This test tests the authmodules/pam_python/privacyidea_pam.py
"""
from .base import MyTestCase

from authmodules.pam_python.privacyidea_pam import (pam_sm_authenticate,
                                                    save_auth_item,
                                                    check_offline_otp)
import responses
import json
import sqlite3


SQLFILE = "pam-test.sqlite"
# test100000
# test100001
# test100002
RESP = {1: '$pbkdf2-sha512$19000$Scl5TwmhtPae856zFgJgLA$ZQAqtqmGTf6IY0t9jg2MCg'
           'd92XzxdijFcT4BNVsvONNpHwZkiKsHrf0oeckS8rRQ9KWBdMwZsQzhu8PkpyXnbA',
        2: '$pbkdf2-sha512$19000$4Lx3bi1FiBHiXGutVYpRqg$9mPHGSh1Ylz0PTEMwJKFw'
           '6tB.avOfYhqJsEnl3KMF8vIE//YUrtwNs4IN6ZU4OeoxFZejebOTtxt8wZjp4140w',
        3: '$pbkdf2-sha512$19000$JATgHGNsDSEEIGRMqXXOmQ$Ub67KeNbwObsFk7mwTetNf'
           'lwTOEKXMzJ5BTblZsu3bV4KAP1rEW6nUPfqLf6/f2yoNhpX1mCS3dt77EBKtJM.A'
}

# TEST100000
# TEST100001
# TEST100002
RESP2 = {1: '$pbkdf2-sha512$19000$DgGA0FrL2ZsTIuS8txYCoA$HAAMTr34j5pMwMA9XZ'
            'euNtNbvHklY0axMKlceqdaCfYzdml9MBH05tgZqvrQToYqCHPDQoBD.GH5/UGvs'
            '7HF4g',
         2: '$pbkdf2-sha512$19000$wfifc07p3dvb.1.LcU6ptQ$NmnYnWMMc9KuCSDG5I'
            'f94qGTmLekRF7Fn9rE4nDxCGuaXBasvEuIyEdp.h2RNqvjbsFd6A/U1T5/9eMC/'
            '7v9GQ',
         3: '$pbkdf2-sha512$19000$53zvvddai/He'
            '.x9DyJnTGg$aUapWKcp21B2eSQzVVKtv9e.9Xs3aoNxg30dgU6TjyzaaHZcUNpvz'
            '7Cqj6yeTFYi1nzQ151I2z8sZWjln1fyag'
}



SUCCESS_BODY = {"detail": {"message": "matching 1 tokens",
                           "serial": "PISP0000AB00",
                           "type": "spass"},
                "id": 1,
                "jsonrpc": "2.0",
                "result": {"status": True,
                           "value": True
                },
                "auth_items": {"offline": [{"username": "corny",
                                            "response": RESP}
                ]
                },
                "version": "privacyIDEA unknown"
}

FAIL_BODY = {"detail": {"message": "wrong otp value"},
                "id": 1,
                "jsonrpc": "2.0",
                "result": {"status": True,
                           "value": False
                },
                "version": "privacyIDEA unknown"
}


class PAMH(object):

    PAM_AUTH_ERR = 0
    PAM_SUCCESS = 1

    exception = Exception

    def __init__(self, user, password):
        self.authtok = password
        self.user = user

    def get_user(self, dummy):
        return self.user


class PAMTestCase(MyTestCase):

    @classmethod
    def setUpClass(cls):
        conn = sqlite3.connect(SQLFILE)
        c = conn.cursor()
        try:
            c.execute("DROP table authitems")
            conn.commit()
        except:
            pass
        conn.close()
        MyTestCase.setUpClass()

    def test_01_check_offline_otp(self):
        # Check with no entries in the database
        r = check_offline_otp("cornelius", "test123456", SQLFILE)
        self.assertFalse(r)

        # Save some values to the database
        r = save_auth_item(SQLFILE,
                           "cornelius",
                           "TOK001",
                           "HOTP",
                           {"offline": [{"username": "corny",
                                         "response": RESP}
                           ]
                           })
        r = check_offline_otp("cornelius", "test100000", SQLFILE)
        self.assertTrue(r)
        # Authenticating with the same value a second time, fails
        r = check_offline_otp("cornelius", "test100000", SQLFILE)
        self.assertFalse(r)

    @responses.activate
    def test_02_authenticate_offline(self):
        responses.add(responses.POST,
                      "http://my.privacyidea.server/validate/check",
                      body=json.dumps(SUCCESS_BODY),
                      content_type="application/json")

        pamh = PAMH("cornelius", "test100001")
        flags = None
        argv = ["url=http://my.privacyidea.server",
                "sqlfile=%s" % SQLFILE]
        r = pam_sm_authenticate(pamh, flags, argv)
        self.assertEqual(r, PAMH.PAM_SUCCESS)

        # Auhenticate the second time offline
        pamh = PAMH("cornelius", "test100002")
        flags = None
        argv = ["url=http://my.privacyidea.server",
                "sqlfile=%s" % SQLFILE]
        r = pam_sm_authenticate(pamh, flags, argv)
        self.assertEqual(r, PAMH.PAM_SUCCESS)

        # Now there are no offline values left

    @responses.activate
    def test_03_authenticate_online(self):
        # authenticate online and fetch offline values
        responses.add(responses.POST,
                      "http://my.privacyidea.server/validate/check",
                      body=json.dumps(SUCCESS_BODY),
                      content_type="application/json")
        pamh = PAMH("cornelius", "test999999")
        flags = None
        argv = ["url=http://my.privacyidea.server",
                "sqlfile=%s" % SQLFILE]
        r = pam_sm_authenticate(pamh, flags, argv)
        self.assertTrue(r)
        # Now the offlne values are stored

    def test_04_authenticate_offline(self):
        # and authenticate offline again.
        pamh = PAMH("cornelius", "test100000")
        flags = None
        argv = ["url=http://my.privacyidea.server",
                "sqlfile=%s" % SQLFILE]
        r = pam_sm_authenticate(pamh, flags, argv)
        self.assertTrue(r)

    def test_05_two_tokens(self):
        # Save some values to the database
        r = save_auth_item(SQLFILE,
                           "cornelius",
                           "TOK001",
                           "HOTP",
                           {"offline": [{"username": "corny",
                                         "response": RESP}
                           ]
                           })
        r = save_auth_item(SQLFILE,
                           "cornelius",
                           "TOK002",
                           "HOTP",
                           {"offline": [{"username": "corny",
                                         "response": RESP2}
                           ]
                           })

        pamh = PAMH("cornelius", "test100001")
        flags = None
        argv = ["url=http://my.privacyidea.server",
                "sqlfile=%s" % SQLFILE]
        r = pam_sm_authenticate(pamh, flags, argv)
        self.assertEqual(r, PAMH.PAM_SUCCESS)

        # An older OTP value of the first token is deleted
        pamh = PAMH("cornelius", "test100000")
        flags = None
        argv = ["url=http://my.privacyidea.server",
                "sqlfile=%s" % SQLFILE]
        r = pam_sm_authenticate(pamh, flags, argv)
        self.assertNotEqual(r, PAMH.PAM_SUCCESS)

        # An older value with another token can authenticate!
        pamh = PAMH("cornelius", "TEST100000")
        flags = None
        argv = ["url=http://my.privacyidea.server",
                "sqlfile=%s" % SQLFILE]
        r = pam_sm_authenticate(pamh, flags, argv)
        self.assertEqual(r, PAMH.PAM_SUCCESS)
