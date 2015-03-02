"""
This testcase is used to test the REST API  in api/machines.py
"""
from .base import MyTestCase
import json
from privacyidea.lib.token import init_token, get_tokens

HOSTSFILE = "tests/testdata/hosts"


class APIMachinesTestCase(MyTestCase):

    def test_00_create_machine_resolver(self):
        # create a machine resolver
        with self.app.test_request_context('/machineresolver/machineresolver1',
                                           data={'type': 'hosts',
                                                 'filename': HOSTSFILE},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue(result["value"] == 1, result)

    def test_01_get_machine_list(self):
        with self.app.test_request_context('/machine/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertEqual(result["status"], True)
            self.assertEqual(len(result["value"]), 4)
            self.assertTrue("hostname" in result["value"][0].keys())
            self.assertTrue("id" in result["value"][0].keys())
            self.assertTrue("ip" in result["value"][0].keys())
            self.assertTrue("resolver_name" in result["value"][0].keys())

    def test_01_get_machine_list_any(self):
        with self.app.test_request_context('/machine/?any=192',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertEqual(result["status"], True)
            self.assertEqual(len(result["value"]), 3)
            self.assertTrue("hostname" in result["value"][0].keys())
            self.assertTrue("id" in result["value"][0].keys())
            self.assertTrue("ip" in result["value"][0].keys())
            self.assertTrue("resolver_name" in result["value"][0].keys())

    def test_02_attach_token(self):
        serial = "S1"
        # create token
        init_token({"serial": serial, "type": "spass"})

        with self.app.test_request_context('/machine/token',
                                           method='POST',
                                           data={"hostname": "gandalf",
                                                 "serial": serial,
                                                 "application": "luks",
                                                 "slot": "1"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertEqual(result["status"], True)
            self.assertTrue(result["value"] >= 1)

        # check if the options were set.
        token_obj = get_tokens(serial=serial)[0]
        self.assertEqual(token_obj.token.machine_list[0].application, "luks")
        self.assertEqual(token_obj.token.machine_list[0].option_list[0].mt_key,
                         "slot")

    def test_04_set_options(self):
        serial = "S1"
        with self.app.test_request_context('/machine/tokenoption',
                                           method='POST',
                                           data={"hostname": "gandalf",
                                                 "serial": serial,
                                                 "application": "luks",
                                                 "partition": "/dev/sdb1"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertEqual(result["status"], True)
            self.assertTrue(result["value"] >= 1)

        # check if the options were set.
        token_obj = get_tokens(serial=serial)[0]
        self.assertEqual(token_obj.token.machine_list[0].application, "luks")
        self.assertEqual(token_obj.token.machine_list[0].option_list[
                             1].mt_value, "/dev/sdb1")

        # delete slot!
        with self.app.test_request_context('/machine/tokenoption',
                                           method='POST',
                                           data={"hostname": "gandalf",
                                                 "serial": serial,
                                                 "application": "luks",
                                                 "slot": ""},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertEqual(result["status"], True)
            self.assertTrue(result["value"] >= 1)

        # check if the options were set.
        token_obj = get_tokens(serial=serial)[0]
        self.assertEqual(token_obj.token.machine_list[0].application, "luks")
        # As we deleted the slot, the partition now is the only entry in the
        # list
        self.assertEqual(token_obj.token.machine_list[0].option_list[
                             0].mt_value, "/dev/sdb1")

        # Overwrite option
        with self.app.test_request_context('/machine/tokenoption',
                                           method='POST',
                                           data={"hostname": "gandalf",
                                                 "serial": serial,
                                                 "application": "luks",
                                                 "partition": "/dev/sda1"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertEqual(result["status"], True)
            self.assertTrue(result["value"] >= 1)

        # check if the options were set.
        token_obj = get_tokens(serial=serial)[0]
        self.assertEqual(token_obj.token.machine_list[0].application, "luks")
        # As we deleted the slot, the partition now is the only entry in the
        # list
        self.assertEqual(token_obj.token.machine_list[0].option_list[
                             0].mt_value, "/dev/sda1")


    def test_05_list_machinetokens(self):
        with self.app.test_request_context('/machine/token?serial=S1',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertEqual(result["status"], True)
            self.assertEqual(len(result["value"]), 1)
            self.assertTrue(result["value"][0]["application"] == "luks")

        with self.app.test_request_context('/machine/token?hostname=gandalf',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertEqual(result["status"], True)
            self.assertEqual(len(result["value"]), 1)
            self.assertTrue(result["value"][0]["application"] == "luks")



    def test_99_detach_token(self):
        serial = "S1"
        # create token
        init_token({"serial": serial, "type": "spass"})

        # Gandalf is 192.168.0.1
        with self.app.test_request_context(
                '/machine/token/S1/192.168.0.1/machineresolver1/luks',
                method='DELETE',
                headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertEqual(result["status"], True)
            self.assertTrue(result["value"] >= 1)

        # check if the options were set.
        token_obj = get_tokens(serial=serial)[0]
        self.assertEqual(len(token_obj.token.machine_list), 0)

