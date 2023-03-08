# -*- coding: utf-8 -*-
"""
This test file tests the lib/machine.py for attaching and detaching tokens
"""

HOSTSFILE = "tests/testdata/hosts"
from .base import MyTestCase
from privacyidea.lib.machine import (attach_token, detach_token, add_option,
                                     delete_option, list_machine_tokens,
                                     list_token_machines, get_auth_items)
from privacyidea.lib.token import init_token, get_tokens
from privacyidea.lib.machineresolver import save_resolver


sshkey = "ssh-rsa " \
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


class MachineTokenTestCase(MyTestCase):
    """
    Test the attaching of tokens to machines
    """
    serial = "myToken"
    resolvername = "reso1"
    serial2 = "ser1"
    serialHotp = "hotp2"

    def test_00_setup(self):
        token1 = init_token({"type": "spass", "serial": self.serial})
        resolver1 = save_resolver({"name": self.resolvername,
                                   "type": "hosts",
                                   "filename": HOSTSFILE})
        init_token({"type": "hotp", "serial": self.serialHotp, "otpkey": "313233"})

    def test_01_attach_token(self):
        mt = attach_token(self.serial, "luks", hostname="gandalf")
        self.assertEqual(mt.token.serial, self.serial)
        self.assertEqual(mt.token.machine_list[0].machine_id, "192.168.0.1")

        # look at token, if we see the machine.
        tok = get_tokens(serial=self.serial)[0]
        self.assertEqual(tok.token.machine_list[0].machine_id, "192.168.0.1")

        # problem attaching token with incomplete machine definition (missing
        #  resolver)
        self.assertRaises(Exception, attach_token, self.serial, "luks",
                          machine_id="192.168.0.1")

    def test_02_detach_token(self):
        detach_token(self.serial, "luks", hostname="gandalf")

        # look at token, if we do not see the machine
        tok = get_tokens(serial=self.serial)[0]
        machine_list = tok.token.machine_list
        self.assertEqual(len(machine_list), 0)

    def test_03_add_delete_option(self):
        mt = attach_token(self.serial, "luks", hostname="gandalf")
        self.assertEqual(mt.token.serial, self.serial)
        self.assertEqual(mt.token.machine_list[0].machine_id, "192.168.0.1")

        r = add_option(serial=self.serial, application="luks",
                       hostname="gandalf", options={"option1": "value1",
                                                    "option2": "valü2"})
        self.assertEqual(r, 2)

        # The options are accessible via the Token!!!
        tok = get_tokens(serial=self.serial)[0]
        option_list = tok.token.machine_list[0].option_list
        self.assertEqual(len(option_list), 2)
        for option in option_list:
            if option.mt_key == "option1":
                self.assertEqual(option.mt_value, "value1")
            elif option.mt_key == "option2":
                self.assertEqual(option.mt_value, "valü2")
            else:
                self.fail("Unspecified Option! {0!s}".format(option.mt_key))

        r = delete_option(serial=self.serial, application="luks",
                          hostname="gandalf", key="option1")
        self.assertEqual(r, 1)

        # The options are accessible via the Token!!!
        tok = get_tokens(serial=self.serial)[0]
        option_list = tok.token.machine_list[0].option_list
        self.assertEqual(len(option_list), 1)

    def test_04_list_tokens_for_machine(self):
        serial = "serial2"
        init_token({"type": "spass", "serial": serial})
        mt = attach_token(serial, "luks", hostname="gandalf")

        tokenlist = list_machine_tokens(hostname="gandalf")

        self.assertEqual(len(tokenlist), 2)

    def test_05_list_machines_for_token(self):
        machinelist = list_token_machines(self.serial)

        self.assertEqual(len(machinelist), 1)
        self.assertEqual(machinelist[0].get("resolver"), "reso1")
        self.assertEqual(machinelist[0].get("machine_id"), "192.168.0.1")

    def test_10_auth_items(self):
        # create an SSH token
        token_obj = init_token({"serial": self.serial2, "type": "sshkey",
                                "sshkey": sshkey})
        self.assertEqual(token_obj.type, "sshkey")

        # Attach the token to the machine "gandalf" with the application SSH
        r = attach_token(hostname="gandalf", serial=self.serial2,
                         application="ssh", options={"user": "testuser"})

        self.assertEqual(r.machine_id, "192.168.0.1")

        # fetch the auth_items for application SSH on machine gandalf
        ai = get_auth_items("gandalf", ip="192.168.0.1", application="ssh")
        sshkey_auth_items = ai.get("ssh")
        self.assertEqual(len(sshkey_auth_items), 1)
        self.assertTrue(sshkey_auth_items[0].get("sshkey").startswith(
            "ssh-rsa"))

        # fetch the auth_items with user restriction for SSH
        ai = get_auth_items("gandalf", ip="192.168.0.1", application="ssh",
                            filter_param={"user": "testuser"})
        sshkey_auth_items = ai.get("ssh")
        self.assertEqual(len(sshkey_auth_items), 1)
        self.assertTrue(sshkey_auth_items[0].get("sshkey").startswith(
            "ssh-rsa"))

        # try to fetch SSH keys for user, who has no ssh keys
        ai = get_auth_items("gandalf", ip="192.168.0.1", application="ssh",
                            filter_param={"user": "nonExist"})
        sshkey_auth_items = ai.get("ssh")
        # None or an empty list
        self.assertFalse(sshkey_auth_items)
        # detach token
        detach_token(self.serial2, "ssh", hostname="gandalf")
        mt = list_token_machines(self.serial2)
        self.assertEqual(0, len(mt))

    def test_11_attach_token_without_machine(self):
        mt = attach_token(self.serialHotp, "offline")
        self.assertEqual(mt.token.serial, self.serialHotp)

        # look at token, if we see the machine.
        tok = get_tokens(serial=self.serialHotp)[0]
        self.assertEqual(tok.token.machine_list[0].machine_id, None)
        self.assertEqual(tok.token.machine_list[0].application, "offline")

    def test_12_list_tokens_without_machine(self):
        tokenlist = list_machine_tokens(serial=self.serialHotp, application="offline")
        self.assertEqual(len(tokenlist), 1)

    def test_13_get_authitems_without_machine(self):
        # fetch the auth_items for application offline and token serialHotp
        ai = get_auth_items(application="offline", serial=self.serialHotp)
        offline_auth_items = ai.get("offline")
        self.assertEqual(len(offline_auth_items), 1)
        offline_auth_item = offline_auth_items[0]
        self.assertIn("refilltoken", offline_auth_item)
        self.assertIn("response", offline_auth_item)
        # The counter of the HOTP token is set to >100
        tok = get_tokens(serial=self.serialHotp)[0]
        self.assertEqual(tok.token.count, 100)

    def test_14_detach_token_without_machine(self):
        detach_token(self.serialHotp, "offline")

        # look at token, if we do not see the machine
        tok = get_tokens(serial=self.serialHotp)[0]
        machine_list = tok.token.machine_list
        self.assertEqual(len(machine_list), 0)

    def test_15_detach_ssh_by_service_id(self):
        token_obj = init_token({"serial": self.serial2, "type": "sshkey",
                                "sshkey": sshkey})
        self.assertEqual(token_obj.type, "sshkey")

        # Attach the token to the machine "gandalf" with the application SSH
        r = attach_token(serial=self.serial2,
                         application="ssh", options={"user": "testuser", "service_id": "webserver"})
        r = attach_token(serial=self.serial2,
                         application="ssh", options={"user": "root", "service_id": "mailserver"})
        r = attach_token(serial=self.serial2,
                         application="ssh", options={"user": "testuser", "service_id": "mailserver"})
        mt = list_token_machines(self.serial2)
        self.assertEqual(3, len(mt), mt)

        # Detach only one application
        detach_token(self.serial2, "ssh", filter_params={"user": "testuser", "service_id": "mailserver"})
        mt = list_token_machines(self.serial2)
        self.assertEqual(2, len(mt))

        # Detach all remaining applications
        detach_token(self.serial2, "ssh")
        mt = list_token_machines(self.serial2)
        self.assertEqual(0, len(mt))
