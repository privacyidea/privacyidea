"""
This test file tests the lib/machine.py for attaching and detaching tokens
"""

HOSTSFILE = "tests/testdata/hosts"
from .base import MyTestCase
from privacyidea.lib.machine import (attach_token, detach_token, add_option,
                                     delete_option, list_machine_tokens,
                                     list_token_machines)
from privacyidea.lib.token import init_token, get_tokens
from privacyidea.lib.machineresolver import save_resolver

class MachineTokenTestCase(MyTestCase):
    """
    Test the attaching of tokens to machines
    """
    serial = "myToken"
    resolvername = "reso1"

    def test_00_setup(self):
        token1 = init_token({"type": "spass", "serial": self.serial})
        resolver1 = save_resolver({"name": self.resolvername,
                                   "type": "hosts",
                                   "filename": HOSTSFILE})
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
        # problem detaching token with incomplete machine definition (missing
        #  resolver)
        self.assertRaises(Exception, detach_token, self.serial, "luks",
                          machine_id="192.168.0.1")

    def test_03_add_delete_option(self):
        mt = attach_token(self.serial, "luks", hostname="gandalf")
        self.assertEqual(mt.token.serial, self.serial)
        self.assertEqual(mt.token.machine_list[0].machine_id, "192.168.0.1")

        r = add_option(serial=self.serial, application="luks",
                       hostname="gandalf", options={"option1": "value1",
                                                    "option2": "value2"})
        self.assertEqual(r, 2)

        # The options are accessible via the Token!!!
        tok = get_tokens(serial=self.serial)[0]
        option_list = tok.token.machine_list[0].option_list
        self.assertEqual(len(option_list), 2)

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
