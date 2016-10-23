"""
This test file tests the lib.clientapplicaton.py
"""
from .base import MyTestCase
from datetime import datetime
from privacyidea.lib.clientapplication import (get_clientapplication,
                                               save_clientapplication)


class ClientApplicationTestCase(MyTestCase):
    """
    Test the ClientApplication functions
    """
    def test_01_save_and_get(self):
        save_clientapplication("1.2.3.4", "PAM")
        save_clientapplication("1.2.3.4", "RADIUS")
        save_clientapplication("1.2.3.4", "OTRS")
        save_clientapplication("1.2.3.4", "SAML")
        save_clientapplication("10.1.1.1", "SAML")

        r = get_clientapplication()
        self.assertEqual(len(r), 4)

        r = get_clientapplication(group_by="ip")
        self.assertEqual(len(r), 2)

        r = get_clientapplication(clienttype="SAML")
        self.assertEqual(len(r), 1)
        self.assertEqual(len(r.get("SAML")), 2)

        r = get_clientapplication(ip="1.2.3.4")
        self.assertEqual(len(r), 4)

        r = get_clientapplication(ip="1.2.3.4")
        # 4 clienttypes in IP 1.2.3.4
        self.assertEqual(len(r), 4)
        self.assertEqual(r["OTRS"][0]["ip"], "1.2.3.4")
        self.assertEqual(r["PAM"][0]["ip"], "1.2.3.4")
        self.assertTrue(r["RADIUS"][0]["lastseen"] < datetime.now())
        self.assertTrue(r["SAML"][0]["lastseen"] < datetime.now())
