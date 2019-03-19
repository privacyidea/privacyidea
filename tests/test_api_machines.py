"""
This testcase is used to test the REST API  in api/machines.py
to fetch machine information and to attach token to machines
"""
import passlib

from privacyidea.lib.user import User
from .base import MyApiTestCase
import json
from privacyidea.lib.token import init_token, get_tokens
from privacyidea.lib.machine import attach_token
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
OTPKEY = "3132333435363738393031323334353637383930"


class APIMachinesTestCase(MyApiTestCase):

    serial2 = "ser1"
    serial3 = "UBOM12345"
    serial4 = "OATH1234"

    def test_00_create_machine_resolver(self):
        # create a machine resolver
        with self.app.test_request_context('/machineresolver/machineresolver1',
                                           data={'type': 'hosts',
                                                 'filename': HOSTSFILE},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue(result["value"] == 1, result)

    def test_01_get_machine_list(self):
        with self.app.test_request_context('/machine/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertEqual(result["status"], True)
            self.assertEqual(len(result["value"]), 5)
            self.assertTrue("hostname" in result["value"][0])
            self.assertTrue("id" in result["value"][0])
            self.assertTrue("ip" in result["value"][0])
            self.assertTrue("resolver_name" in result["value"][0])

    def test_01_get_machine_list_any(self):
        with self.app.test_request_context('/machine/?any=192',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertEqual(result["status"], True)
            self.assertEqual(len(result["value"]), 4)
            self.assertTrue("hostname" in result["value"][0])
            self.assertTrue("id" in result["value"][0])
            self.assertTrue("ip" in result["value"][0])
            self.assertTrue("resolver_name" in result["value"][0])

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
            result = json.loads(res.data.decode('utf8')).get("result")
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
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertEquals(result["status"], True, result)
            self.assertGreaterEqual(result["value"]["added"], 1, result)
            self.assertEquals(result['value']['deleted'], 0, result)

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
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertEquals(result["status"], True, result)
            self.assertEquals(result["value"]["added"], 0, result)
            self.assertGreaterEqual(result['value']['deleted'], 1, result)

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
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertEquals(result["status"], True, result)
            self.assertGreaterEqual(result["value"]["added"], 1, result)
            self.assertEquals(result['value']['deleted'], 0, result)

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
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertEqual(result["status"], True)
            self.assertEqual(len(result["value"]), 1)
            self.assertTrue(result["value"][0]["application"] == "luks")

        with self.app.test_request_context('/machine/token?hostname=gandalf',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
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
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertEqual(result["status"], True)
            self.assertTrue(result["value"] >= 1)

        # check if the options were set.
        token_obj = get_tokens(serial=serial)[0]
        self.assertEqual(len(token_obj.token.machine_list), 0)

    def test_10_auth_items_ssh(self):
        # create an SSH token
        token_obj = init_token({"serial": self.serial2, "type": "sshkey",
                                "sshkey": SSHKEY})
        self.assertEqual(token_obj.type, "sshkey")

        # Attach the token to the machine "gandalf" with the application SSH
        r = attach_token(hostname="gandalf", serial=self.serial2,
                         application="ssh", options={"user": "testuser"})

        self.assertEqual(r.machine_id, "192.168.0.1")

        # fetch the auth_items for application SSH on machine gandalf
        with self.app.test_request_context(
                '/machine/authitem/ssh?hostname=gandalf',
                method='GET',
                headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertEqual(result["status"], True)
            sshkey = result["value"].get("ssh")[0].get("sshkey")
            self.assertTrue(sshkey.startswith("ssh-rsa"), sshkey)

        # fetch the auth_items for user testuser
        with self.app.test_request_context(
                '/machine/authitem/ssh?hostname=gandalf&user=testuser',
                method='GET',
                headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertEqual(result["status"], True)
            sshkey = result["value"].get("ssh")[0].get("sshkey")
            self.assertTrue(sshkey.startswith("ssh-rsa"), sshkey)

        # fetch auth_items for testuser, but with mangle policy
        # Remove everything that sounds like "SOMETHING\" in front of
        # the username
        set_policy(name="mangle1", scope=SCOPE.AUTH,
                   action="{0!s}=user/.*\\\\(.*)/\\1/".format(ACTION.MANGLE))
        with self.app.test_request_context(
                '/machine/authitem/ssh?hostname=gandalf&user=DOMAIN\\testuser',
                method='GET',
                headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertEqual(result["status"], True)
            sshkey = result["value"].get("ssh")[0].get("sshkey")
            self.assertTrue(sshkey.startswith("ssh-rsa"), sshkey)
        delete_policy("mangle1")

        # Now that the policy is deleted, we will not get the auth_items
        # anymore, since the username is not mangled.
        with self.app.test_request_context(
                '/machine/authitem/ssh?hostname=gandalf&user=DOMAIN\\testuser',
                method='GET',
                headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertEqual(result["status"], True)
            sshkeys = result["value"].get("ssh")
            # No user DOMAIN\\testuser and no SSH keys
            self.assertFalse(sshkeys)

        # fetch the auth_items on machine gandalf for all applications
        with self.app.test_request_context(
                '/machine/authitem?hostname=gandalf',
                method='GET',
                headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            sshkey = result["value"].get("ssh")[0].get("sshkey")
            self.assertTrue(sshkey.startswith("ssh-rsa"), sshkey)

    def test_11_auth_items_luks(self):
        # create TOTP/Yubikey token
        token_obj = init_token({"serial": self.serial3, "type": "totp",
                                "otpkey": "12345678"})
        self.assertEqual(token_obj.type, "totp")

        # Attach the token to the machine "gandalf" with the application SSH
        r = attach_token(hostname="gandalf", serial=self.serial3,
                         application="luks", options={"slot": "1",
                                                      "partition": "/dev/sda1"})

        self.assertEqual(r.machine_id, "192.168.0.1")

        # fetch the auth_items on machine gandalf for application luks
        with self.app.test_request_context(
                '/machine/authitem/luks?hostname=gandalf',
                method='GET',
                headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            slot = result["value"].get("luks")[0].get("slot")
            self.assertEqual(slot, "1")

        # fetch the auth_items on machine gandalf for application luks
        with self.app.test_request_context(
                '/machine/authitem/luks?hostname=gandalf&challenge=abcdef',
                method='GET',
                headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            slot = result["value"].get("luks")[0].get("slot")
            self.assertEqual(slot, "1")
            response = result["value"].get("luks")[0].get("response")
            self.assertEqual(response,
                             "93235fc7d1d444d0ec014ea9eafcc44fc65b73eb")

    def test_12_auth_items_offline(self):
        #create HOTP token for offline usage
        self.setUp_user_realms()
        token_obj = init_token({"serial": self.serial4, "type": "hotp",
                                "otpkey": OTPKEY,
                                "pin": "test"}, User("cornelius", self.realm1))
        self.assertEqual(token_obj.type, "hotp")
        self.assertEqual(token_obj.token.count, 0)

        # Attach the token to the machine "gandalf" with the application offline
        r = attach_token(hostname="gandalf", serial=self.serial4,
                         application="offline", options={"user": "cornelius",
                                                         "count": 17})

        self.assertEqual(r.machine_id, "192.168.0.1")

        # fetch the auth_items on machine gandalf for application "offline"
        with self.app.test_request_context(
                '/machine/authitem/offline?hostname=gandalf',
                method='GET',
                headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            offline_auth_item = result["value"].get("offline")[0]
            username = offline_auth_item.get("user")
            self.assertEqual(username, "cornelius")
            # check, if we got 17 otp values
            response = offline_auth_item.get("response")
            self.assertEqual(len(response), 17)
            self.assertEqual(token_obj.token.count, 17)
            self.assertTrue(passlib.hash.\
                            pbkdf2_sha512.verify("755224",
                                                 response.get('0')))

        self.assertEqual(token_obj.check_otp('187581'), -1) # count = 16
        with self.app.test_request_context(
                '/validate/check?user=cornelius&pass=test447589', # count = 17
                environ_base={'REMOTE_ADDR': '192.168.0.1'},
                method='GET'):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8'))
            self.assertTrue(result['result']['status'])
            self.assertTrue(result['result']['value'])
            offline_auth_item = result["auth_items"]["offline"][0]
            username = offline_auth_item.get("user")
            self.assertEqual(username, "cornelius")
            # check, if we got 17 otp values
            response = offline_auth_item.get("response")
            self.assertEqual(len(response), 17)
            self.assertEqual(token_obj.token.count, 35) # 17 + 17 + 1, because we consumed 447589
            self.assertTrue(passlib.hash.
                            pbkdf2_sha512.verify("test903435", # count = 18
                                                 response.get('18')))
            self.assertTrue(passlib.hash.
                            pbkdf2_sha512.verify("test749439", # count = 34
                                                 response.get('34')))
        self.assertEqual(token_obj.check_otp('747439'), -1) # count = 34
        self.assertEqual(token_obj.check_otp('037211'), 35) # count = 35
