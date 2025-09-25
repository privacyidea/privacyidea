"""
This test file tests the lib/radiusserver.py
"""
import logging
from testfixtures import LogCapture
import pyrad

from .base import MyTestCase
from privacyidea.lib.error import ConfigAdminError, privacyIDEAError
from privacyidea.lib.radiusserver import (add_radius, delete_radius,
                                          get_radiusservers, get_radius,
                                          test_radius)
from . import radiusmock
DICT_FILE = "tests/testdata/dictionary"


# prevent nosetests to run test_radius as a unittest
test_radius.__test__ = False


class RADIUSServerTestCase(MyTestCase):

    def test_01_create_radius(self):
        r = add_radius(identifier="myserver", server="1.2.3.4",
                       secret="testing123")
        self.assertTrue(r > 0)
        r = add_radius(identifier="myserver1", server="1.2.3.4",
                       secret="testing123")
        self.assertTrue(r > 0)
        r = add_radius(identifier="myserver2", server="1.2.3.4",
                       secret="testing123")
        self.assertTrue(r > 0)

        server_list = get_radiusservers()
        self.assertTrue(server_list)
        self.assertEqual(len(server_list), 3)
        server_list = get_radiusservers(identifier="myserver")
        self.assertTrue(server_list[0].config.identifier, "myserver")
        self.assertTrue(server_list[0].config.port, 1812)

        for server in ["myserver", "myserver1", "myserver2"]:
            r = delete_radius(server)
            self.assertTrue(r > 0)

        server_list = get_radiusservers()
        self.assertEqual(len(server_list), 0)

    def test_02_updateserver(self):
        r = add_radius(identifier="myserver", server="1.2.3.4",
                       secret="testing123")
        self.assertTrue(r > 0)
        server_list = get_radiusservers(identifier="myserver")
        self.assertTrue(server_list[0].config.server, "1.2.3.4")
        r = add_radius(identifier="myserver", server="100.2.3.4",
                       secret="testing123")
        self.assertTrue(r > 0)
        server_list = get_radiusservers(identifier="myserver")
        self.assertTrue(server_list[0].config.server, "100.2.3.4")

    def test_03_missing_configuration(self):
        self.assertRaises(ConfigAdminError, get_radius, "notExisting")

    @radiusmock.activate
    def test_04_RADIUS_request(self):
        radiusmock.setdata(response=radiusmock.AccessAccept)
        logging.getLogger("privacyidea.lib.radiusserver").setLevel(logging.DEBUG)
        with LogCapture(level=logging.DEBUG) as lc:
            r = add_radius(identifier="myserver", server="1.2.3.4",
                           secret="testing123", dictionary=DICT_FILE)
            self.assertIn("'secret': 'HIDDEN'", lc.records[0].message)
            self.assertTrue(r > 0)

        radius = get_radius("myserver")
        with LogCapture(level=logging.DEBUG) as lc:
            r = radius.request("user", "password")
            self.assertIsInstance(r, pyrad.packet.Packet)
            self.assertEqual(r.code, pyrad.packet.AccessAccept)
            self.assertIn("{'password': 'HIDDEN'}", lc.records[0].message)

        radiusmock.setdata(response=radiusmock.AccessReject)
        r = radius.request("user", "password")
        self.assertIsInstance(r, pyrad.packet.Packet)
        self.assertEqual(r.code, pyrad.packet.AccessReject)

    @radiusmock.activate
    def test_05_timeout_RADIUS_request(self):
        radiusmock.setdata(response=radiusmock.AccessAccept, timeout=True)
        r = add_radius(identifier="myserver", server="1.2.3.4",
                       secret="testing123", dictionary=DICT_FILE)
        self.assertTrue(r > 0)
        radius = get_radius("myserver")
        # A timeout will return false
        with LogCapture(level=logging.WARNING) as lc:
            r = radius.request("user", "password")
            self.assertIsNone(r)
            self.assertIn("Timeout while contacting remote radius server 1.2.3.4",
                          lc.records[0].message)

    @radiusmock.activate
    def test_06_test_radius(self):
        radiusmock.setdata(response=radiusmock.AccessReject)
        r = test_radius(identifier="myserver", server="1.2.3.4",
                        user="user", password="password",
                        secret="testing123", dictionary=DICT_FILE)
        self.assertFalse(r)

        radiusmock.setdata(response=radiusmock.AccessAccept)
        r = test_radius(identifier="myserver", server="1.2.3.4",
                        user="user", password="password",
                        secret="testing123", dictionary=DICT_FILE)
        self.assertTrue(r)

        logging.getLogger("privacyidea.lib.radiusserver").setLevel(logging.DEBUG)
        with LogCapture(level=logging.DEBUG, attributes=lambda rec: (rec.levelname, rec.message)) as lc:
            radiusmock.setdata(response=radiusmock.AccessChallenge,
                               response_data={"Reply-Message": "Please enter OTP"})
            r = test_radius(identifier="myserver", server="1.2.3.4",
                            user="user", password="password",
                            secret="testing123", dictionary=DICT_FILE)
            self.assertFalse(r)
            self.assertNotIn("testing123", lc.records[0].message)
            self.assertIn("'password': 'HIDDEN', 'secret': 'HIDDEN'", lc.records[0].message)
            lc.check_present(("INFO", "RADIUS Server test failed! Server requires "
                                      "Challenge-Response (Answer: ['Please enter OTP'])"))

        # raises error on long secrets
        self.assertRaises(privacyIDEAError,
                          test_radius,
                          identifier="myserver", server="1.2.3.4",
                          user="user", password="password",
                          secret="x" * 96, dictionary=DICT_FILE)

    @radiusmock.activate
    def test_07_non_ascii(self):
        radiusmock.setdata(response=radiusmock.AccessAccept)
        r = add_radius(identifier="myserver", server="1.2.3.4",
                       secret="testing123", dictionary=DICT_FILE)
        self.assertTrue(r > 0)
        radius = get_radius("myserver")
        r = radius.request("nönäscii", "passwörd")
        self.assertIsInstance(r, pyrad.packet.Packet)
        self.assertEqual(r.code, pyrad.packet.AccessAccept)

    @radiusmock.activate
    def test_08_RADIUS_with_message_authenticator(self):
        # TODO: The RADIUS mock does not support the Message-Authenticator attribute
        #       so we can only test for the absence of the attribute
        r = add_radius(identifier="myserver", server="1.2.3.4",
                       secret="testing123", dictionary="deploy/privacyidea/dictionary",
                       options={"message_authenticator": True})
        self.assertTrue(r > 0)
        radius = get_radius("myserver")
        radiusmock.setdata(response=radiusmock.AccessAccept)
        with LogCapture(level=logging.WARNING) as lc:
            self.assertRaises(privacyIDEAError, radius.request, "user", "password")
            self.assertTrue(lc.records[0].message.startswith("Unable to verify Message-Authenticator "
                                                             "Attribute in response:"))
        delete_radius("myserver")
