"""
This test tests the authmodules/pam_python/privacyidea_pam.py
"""
from .base import MyTestCase

from authmodules.pam_python.privacyidea_pam import (pam_sm_authenticate,
                                                    save_auth_item, check_otp)
import responses
import json

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


class PAMTestCase(MyTestCase):

    @responses.activate
    def test_authenticate(self):
        responses.add(responses.POST,
                      "http://my.privacyidea.server/validate/check",
                      body=json.dumps(SUCCESS_BODY),
                      content_type="application/json")
        pass
