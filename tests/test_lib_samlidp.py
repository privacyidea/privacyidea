"""
This test file tests the lib/samlidp.py
"""
from .base import MyTestCase
from privacyidea.lib.error import ConfigAdminError
from privacyidea.lib.samlidp import (add_samlidp, delete_samlidp,
                                     fetch_metadata, get_samlidp_list,
                                     get_samlidp)
import responses

# Some long data
METADATA = 300 * "1234567890"


class SAMLIdPTestCase(MyTestCase):

    def test_01_create_samlidp(self):
        r = add_samlidp(identifier="myserver",
                        metadata_url="http://example.com")
        self.assertTrue(r > 0)
        # update
        r = add_samlidp(identifier="myserver",
                        metadata_url="http://example.com/sub",
                        active=False)
        r = add_samlidp(identifier="myserver2",
                        metadata_url="http://example.com/2")

        server_list = get_samlidp_list()
        self.assertTrue(server_list)
        self.assertEqual(len(server_list), 2)
        server_list = get_samlidp_list(active=True)
        self.assertTrue(server_list)
        self.assertEqual(len(server_list), 1)

        saml_object = get_samlidp("myserver2")
        self.assertEqual(saml_object.active, True)
        self.assertEqual(saml_object.metadata_url, "http://example.com/2")

        for server in ["myserver", "myserver2"]:
            r = delete_samlidp(server)
            self.assertTrue(r > 0)

        server_list = get_samlidp_list()
        self.assertEqual(len(server_list), 0)

    def test_02_missing_configuration(self):
        self.assertRaises(ConfigAdminError, get_samlidp, "notExisting")

    @responses.activate
    def test_03_fetch_metadata(self):
        responses.add(responses.GET, "http://example.com",
                      status=200, content_type='text/html',
                      body=METADATA)
        r = add_samlidp(identifier="myserver",
                        metadata_url="http://example.com")
        self.assertTrue(r > 0)
        metadata = fetch_metadata("myserver")

        self.assertEqual(metadata, METADATA)

        saml_object = get_samlidp("myserver")
        self.assertEqual(saml_object.metadata_cache, METADATA)
