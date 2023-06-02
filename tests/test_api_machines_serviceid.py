"""
This testcase is used to test the REST API  in api/machines.py
to fetch machine information and to attach token to machines
"""
import passlib

from privacyidea.lib.user import User
from .base import MyApiTestCase
import json
from privacyidea.lib.token import init_token, get_tokens, remove_token
from privacyidea.lib.machine import attach_token, detach_token, ANY_MACHINE, NO_RESOLVER
from privacyidea.lib.policy import (set_policy, delete_policy, ACTION, SCOPE)

HOSTSFILE = "tests/testdata/hosts"

SSHKEY = "ssh-rsa " \
         "AAAAB3NzaC1yc2EAAAADAQABAAACAQDJy0rLoxqc8SsY8DVAFijMsQyCv" \
         "hBu4K40hdZOacXK4O6OgnacnSKN56MP6pzz2+4svzvDzwvkFsvf34pbsgD" \
         "F67PPSCsimmjEQjf0UfamBKh0cl181CbPYsph3UTBOCgHh3FFDXBduPK4DQz" \
         "EVQpmqe80h+lsvQ81qPYagbRW6fpd0uWn9H7a/qiLQZsiKLL07HGB+NwWue4os" \
         "0r9s4qxeG76K6QM7nZKyC0KRAz7CjAf+0X7YzCOu2pzyxVdj/T+KArFcMmq8V" \
         "dz24mhcFFXTzU3wveas1A9rwamYWB+Spuohh/OrK3wDsrryStKQv7yofgnPMs" \
         "TdaL7XxyQVPCmh2jVl5ro9BPIjTXsre9EUxZYFVr3EIECRDNWy3xEnUHk7Rzs" \
         "734Rp6XxGSzcSLSju8/MBzUVe35iXfXDRcqTcoA0700pIb1ANYrPUO8Up05v4" \
         "EjIyBeU61b4ilJ3PNcEVld6FHwP3Z7F068ef4DXEC/d7pibrp4Up61WYQIXV/" \
         "utDt3NDg/Zf3iqoYcJNM/zIZx2j1kQQwqtnbGqxJMrL6LtClmeWteR4420uZx" \
         "afLE9AtAL4nnMPuubC87L0wJ88un9teza/N02KJMHy01Yz3iJKt3Ou9eV6kqO" \
         "ei3kvLs5dXmriTHp6g9whtnN6/Liv9SzZPJTs8YfThi34Wccrw== " \
         "NetKnights GmbH"
SSHKEY_ecdsa = "ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzd" \
               "HAyNTYAAABBBHGCdIk0pO1HFr/mF4oLb43ZRyQJ4K7ICLrAhAiQERVa0tUvyY5TE" \
               "zurWTqxSMx203rY77t6xnHLZBMPPpv8rk0= cornelius@puck"
OTPKEY = "3132333435363738393031323334353637383930"


class APIMachinesServiceIDTestCase(MyApiTestCase):

    serial1 = "SSHKEY1"
    serial2 = "SSHKEY2"
    serviceID1 = "webserver"
    serviceID2 = "mailserver"

    def test_01_create_sshkeys(self):
        # create two tokens
        token_obj = init_token({"serial": self.serial1, "type": "sshkey",
                                "sshkey": SSHKEY})
        self.assertEqual(token_obj.type, "sshkey")
        token_obj = init_token({"serial": self.serial2, "type": "sshkey",
                                "sshkey": SSHKEY_ecdsa})
        self.assertEqual(token_obj.type, "sshkey")

    def test_02_attach_tokens(self):
        # Do the following token attachemends:
        # * S1: webserver and mailserver
        # * S2: only mailserver
        # Attach token S1 to webserver
        with self.app.test_request_context('/machine/token',
                                           method='POST',
                                           data={"serial": self.serial1,
                                                 "application": "ssh",
                                                 "user": "root",
                                                 "service_id": self.serviceID1},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result["status"], True)
            self.assertTrue(result["value"] >= 1)
            mtid = result.get("value")

        # Attach S1 to mailserver
        with self.app.test_request_context('/machine/token',
                                           method='POST',
                                           data={"serial": self.serial1,
                                                 "application": "ssh",
                                                 "user": "root",
                                                 "service_id": self.serviceID2},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result["status"], True)
            self.assertTrue(result["value"] >= 1)
            mtid = result.get("value")

        # Attach S2 to mailserver
        with self.app.test_request_context('/machine/token',
                                           method='POST',
                                           data={"serial": self.serial2,
                                                 "application": "ssh",
                                                 "user": "root",
                                                 "service_id": self.serviceID2},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result["status"], True)
            self.assertTrue(result["value"] >= 1)
            mtid = result.get("value")

    def test_03_get_service_ids(self):
        # Get all machinetokens
        with self.app.test_request_context('/machine/token',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result["status"], True)
            value = result.get("value")
            self.assertEqual(len(value), 3)
            self.assertEqual(value[0]["application"], "ssh")
            self.assertEqual(value[1]["application"], "ssh")
            self.assertEqual(value[2]["application"], "ssh")

        # Get tokens for service_id self.serviceID1
        with self.app.test_request_context('/machine/token?service_id={0!s}'.format(self.serviceID1),
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result["status"], True)
            value = result.get("value")
            self.assertEqual(len(value), 1)
            self.assertEqual(value[0]["application"], "ssh")
            self.assertEqual(value[0].get("options").get("service_id"), self.serviceID1)
            self.assertEqual(value[0].get("serial"), self.serial1)

        # Get token for service_id self.serviceID2
        with self.app.test_request_context('/machine/token?service_id={0!s}'.format(self.serviceID2),
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result["status"], True)
            value = result.get("value")
            self.assertEqual(len(value), 2)
            self.assertEqual(value[0]["application"], "ssh")
            self.assertEqual(value[0].get("options").get("service_id"), self.serviceID2)
            self.assertEqual(value[0].get("serial"), self.serial1)
            self.assertEqual(value[1]["application"], "ssh")
            self.assertEqual(value[1].get("options").get("service_id"), self.serviceID2)
            self.assertEqual(value[1].get("serial"), self.serial2)

        # combine filter and get service_id self.serviceID2 for serial1
        with self.app.test_request_context('/machine/token?service_id={0!s}&serial={1!s}'.format(
                self.serviceID2, self.serial1),
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result["status"], True)
            value = result.get("value")
            self.assertEqual(len(value), 1)
            self.assertEqual(value[0]["application"], "ssh")
            self.assertEqual(value[0].get("options").get("service_id"), self.serviceID2)
            self.assertEqual(value[0].get("serial"), self.serial1)

        # Get token for service_id self.serviceID2 and the correct application
        with self.app.test_request_context('/machine/token?service_id={0!s}&application=ssh'.format(self.serviceID2),
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result["status"], True)
            value = result.get("value")
            self.assertEqual(len(value), 2)
            self.assertEqual(value[0]["application"], "ssh")
            self.assertEqual(value[0].get("options").get("service_id"), self.serviceID2)
            self.assertEqual(value[0].get("serial"), self.serial1)
            self.assertEqual(value[1]["application"], "ssh")
            self.assertEqual(value[1].get("options").get("service_id"), self.serviceID2)
            self.assertEqual(value[1].get("serial"), self.serial2)

        # Get token for service_id self.serviceID2 and the wrong application
        with self.app.test_request_context(
                '/machine/token?service_id={0!s}&application=openssh'.format(self.serviceID2),
                method='GET',
                headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result["status"], True)
            value = result.get("value")
            self.assertEqual(len(value), 0)

    def test_04_get_service_id_for_different_users(self):
        # Add another SSH key for user admin to self.serviceID2
        with self.app.test_request_context('/machine/token',
                                           method='POST',
                                           data={"serial": self.serial1,
                                                 "application": "ssh",
                                                 "user": "admin",
                                                 "service_id": self.serviceID2},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result["status"], True)
            self.assertTrue(result["value"] >= 1)
            mtid = result.get("value")

        # Get token for service_id self.serviceID2 and the application=ssh and the user=root
        with self.app.test_request_context(
                '/machine/token?service_id={0!s}&application=ssh&user=root'.format(self.serviceID2),
                method='GET',
                headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result["status"], True)
            value = result.get("value")
            self.assertEqual(len(value), 2)
            self.assertEqual(value[0]["application"], "ssh")
            self.assertEqual(value[0].get("options").get("service_id"), self.serviceID2)
            self.assertEqual(value[0].get("serial"), self.serial1)
            self.assertEqual(value[1]["application"], "ssh")
            self.assertEqual(value[1].get("options").get("service_id"), self.serviceID2)
            self.assertEqual(value[1].get("serial"), self.serial2)

        # Get token for service_id self.serviceID2 and the application=ssh and the user=admin
        with self.app.test_request_context(
                '/machine/token?service_id={0!s}&application=ssh&user=admin'.format(self.serviceID2),
                method='GET',
                headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result["status"], True)
            value = result.get("value")
            self.assertEqual(len(value), 1)
            self.assertEqual(value[0]["application"], "ssh")
            self.assertEqual(value[0].get("options").get("service_id"), self.serviceID2)
            self.assertEqual(value[0].get("serial"), self.serial1)

        # test filter and wildcards

        # Find all tokens attached to a *server
        with self.app.test_request_context(
                '/machine/token?service_id=*server*&application=ssh',
                method='GET',
                headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result["status"], True)
            value = result.get("value")
            self.assertEqual(len(value), 4)
            self.assertEqual(value[0]["application"], "ssh")

        # Find all tokens attached to the user *root*
        with self.app.test_request_context(
                '/machine/token?application=ssh&user=*oot',
                method='GET',
                headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result["status"], True)
            value = result.get("value")
            # 3 tokens are attached via user "root"
            self.assertEqual(len(value), 3)
            self.assertEqual(value[0]["application"], "ssh")

        # Find all tokens attached to the user *adm*
        with self.app.test_request_context(
                '/machine/token?application=ssh&user=*adm*',
                method='GET',
                headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result["status"], True)
            value = result.get("value")
            # One token is attached via user "admin"
            self.assertEqual(len(value), 1)
            self.assertEqual(value[0]["application"], "ssh")

        # Filter vor *KEY1
        with self.app.test_request_context(
                '/machine/token?application=ssh&serial=*KEY1',
                method='GET',
                headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result["status"], True)
            value = result.get("value")
            # One token is attached via user "admin"
            self.assertEqual(len(value), 3)
            for v in value:
                # We only get SSHKEY1
                self.assertEqual(v.get("serial"), self.serial1)

        # sort by service_id
        with self.app.test_request_context(
                '/machine/token?application=ssh&serial=*KEY1&sortby=service_id',
                method='GET',
                headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertEqual(result["status"], True)
            value = result.get("value")
            # One token is attached via user "admin"
            self.assertEqual(len(value), 3)
            self.assertEqual(value[0].get("options").get("user"), "root")
            self.assertEqual(value[1].get("options").get("user"), "admin")
            self.assertEqual(value[2].get("options").get("user"), "root")
