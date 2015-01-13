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
        self.assertTrue(r == "otpauth://hotp/mylabel?secret=CI2FM6A&counter=0",
                        r)
        r = create_oathtoken_url("12345678")
        self.assertTrue(r == "oathtoken:///addToken?name=mylabel&"
                             "lockdown=true&key=12345678",
                             r)
        r = create_oathtoken_url("12345678", type="totp")
        self.assertTrue(r == "oathtoken:///addToken?name=mylabel&"
                             "lockdown=true&key=12345678&timeBased=true",
                             r)
        r = create_motp_url("12345678")
        self.assertTrue(r == "motp://privacyidea:mylabel?secret=12345678", r)

