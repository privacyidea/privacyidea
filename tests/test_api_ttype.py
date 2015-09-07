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
