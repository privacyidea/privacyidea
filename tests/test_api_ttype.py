from urllib import urlencode
import json
from .base import MyTestCase
from privacyidea.lib.user import (User)
from privacyidea.lib.tokens.totptoken import HotpTokenClass
from privacyidea.models import (Token)
from privacyidea.lib.config import (set_privacyidea_config, get_token_types,
                                    get_inc_fail_count_on_false_pin,
                                    delete_privacyidea_config)
from privacyidea.lib.token import (get_tokens, init_token, remove_token,
                                   reset_token)

from privacyidea.lib.error import (ParameterError, UserError)

PWFILE = "tests/testdata/passwords"


class TtypeAPITestCase(MyTestCase):
    """
    test the api.ttype endpoints
    """

    def test_00_create_realms(self):
        self.setUp_user_realms()

    def test_01_tiqr(self):
        init_token({"serial": "TIQR1",
                    "type": "tiqr",
                    "user": "cornelius",
                    "realm": self.realm1})
        with self.app.test_request_context('/ttype/tiqr',
                                           method='POST',
                                           data={"action": "metadata",
                                                 "serial": "TIQR1",
                                                 "session": "12345"}):
            res = self.app.full_dispatch_request()
            data = json.loads(res.data)
            identity = data.get("identity")
            service = data.get("service")
            self.assertEqual(identity.get("displayName"), "Cornelius ")
            self.assertEqual(service.get("displayName"), "privacyIDEA")

    def test_02_u2f(self):
        set_privacyidea_config("u2f.appId", "https://puck.az.intern")
        with self.app.test_request_context('/ttype/u2f',
                                           method='GET'):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.mimetype, u'application/fido.trusted-apps+json')
            data = json.loads(res.data)
            self.assertTrue("trustedFacets" in data)

        # Check the audit log.
        with self.app.test_request_context('/audit/?action=*GET /ttype/*',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            json_response = json.loads(res.data)
            result = json_response.get("result")
            auditdata = result.get("value").get("auditdata")
            self.assertTrue(len(auditdata) > 0)
            self.assertEqual(auditdata[0].get("token_type"), "u2f")
