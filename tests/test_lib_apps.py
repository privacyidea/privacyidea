# coding: utf-8
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

        r = create_google_authenticator_url(tokentype="TOTP", key="123456",
                                            period=60)
        self.assertTrue("otpauth://TOTP/mylabel?secret=CI2FM&period"
                        "=60&digits=6&issuer=privacyIDEA" in r, r)

        r = create_oathtoken_url("12345678")
        self.assertEqual(r, "oathtoken:///addToken?name=mylabel&"
                            "lockdown=true&key=12345678")
        r = create_oathtoken_url("12345678", type="totp")
        self.assertEqual(r, "oathtoken:///addToken?name=mylabel&"
                             "lockdown=true&key=12345678&timeBased=true")
        r = create_motp_url("12345678")
        self.assertEqual(r, "motp://privacyidea:mylabel?secret=12345678")

    def test_02_extra_data(self):
        extra_data = {
            'somekey': 'somevalue',
            'sömekey': 'sömevälue',
            'anotherkey': 12345,
        }
        r = create_google_authenticator_url("12345678", extra_data=extra_data)
        self.assertIn("otpauth://hotp/mylabel?secret=CI2FM6A&counter=1", r)
        self.assertIn("&somekey=somevalue", r)
        self.assertIn("&s%C3%B6mekey=s%C3%B6mev%C3%A4lue", r)
        self.assertIn("&anotherkey=12345", r)

        r = create_oathtoken_url("12345678", type="totp", extra_data=extra_data)
        self.assertTrue(r.startswith("oathtoken:///addToken?name=mylabel&"
                                     "lockdown=true&key=12345678&timeBased=true"), r)
        self.assertIn("&somekey=somevalue", r)
        self.assertIn("&s%C3%B6mekey=s%C3%B6mev%C3%A4lue", r)
        self.assertIn("&anotherkey=12345", r)
