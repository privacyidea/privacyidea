"""
This test tests the authmodules/Apache2/privacyidea_apache.py
"""
from .base import MyTestCase
from authmodules.apache2.privacyidea_apache import (OK, UNAUTHORIZED,
                                                    check_password,
                                                    ROUNDS, SALT_SIZE)
import responses
import json
from . import redismock
import passlib.hash


SUCCESS_BODY = {"detail": {"message": "matching 1 tokens",
                           "serial": "PISP0000AB00",
                           "type": "spass"},
                "id": 1,
                "jsonrpc": "2.0",
                "result": {"status": True,
                           "value": True
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


class ApacheTestCase(MyTestCase):

    pw_dig = passlib.hash.pbkdf2_sha512.using(rounds=ROUNDS, salt_size=SALT_SIZE).hash("test100001")

    @redismock.activate
    @responses.activate
    def test_01_success(self):
        responses.add(responses.POST,
                      "https://localhost/validate/check",
                      body=json.dumps(SUCCESS_BODY),
                      content_type="application/json")

        r = check_password({}, "cornelius", "test100001")
        self.assertEqual(r, OK)

    @redismock.activate
    def test_02_success_cache(self):
        # In this case, the password is successfully checked against the
        # redis database
        redismock.set_data({"+++cornelius": self.pw_dig})
        # The password is contained in the database and thus the privacyIDEA
        # server does not have to be asked. Therefor we can omit the response
        #  mock
        r = check_password({}, "cornelius", "test100001")
        self.assertEqual(r, OK)

    @redismock.activate
    @responses.activate
    def test_03_fail(self):
        responses.add(responses.POST,
                      "https://localhost/validate/check",
                      body=json.dumps(FAIL_BODY),
                      content_type="application/json")

        r = check_password({}, "cornelius", "test100002")
        self.assertEqual(r, UNAUTHORIZED)
