"""
This tests the file lib.apps, which contains functions to create
the URLs for the smartphone enrollment
"""
from .base import MyTestCase

from privacyidea.lib.apps import (create_google_authenticator_url,
                                   create_motp_url,
                                   create_oathtoken_url)



class AppsTestCase(MyTestCase):

    def test_01_apps_urls(self):
        r = create_google_authenticator_url("12345678")
        self.assertTrue("otpauth://hotp/mylabel?secret=CI2FM6A&counter=1" in
                        r, r)
        r = create_oathtoken_url("12345678")
        self.assertEqual(r, "oathtoken:///addToken?name=mylabel&"
                            "lockdown=true&key=12345678")
        r = create_oathtoken_url("12345678", type="totp")
        self.assertEqual(r, "oathtoken:///addToken?name=mylabel&"
                             "lockdown=true&key=12345678&timeBased=true")
        r = create_motp_url("12345678")
        self.assertEqual(r, "motp://privacyidea:mylabel?secret=12345678")

