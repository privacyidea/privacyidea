from privacyidea.lib.token import init_token
from tests.base import MyTestCase


class PasskeyTokenTestCase(MyTestCase):

    def test_01_init(self):
        ret = init_token({"type": "passkey"})
