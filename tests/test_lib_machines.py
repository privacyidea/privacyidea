"""
This test file tests the lib/machine.py and lib/machines/* and all
the resolvers under it:

lib.machine
lib.machines.base
lib.machines.hosts
"""
from sqlalchemy import select

from privacyidea.models import db, MachineResolver, MachineResolverConfig

HOSTSFILE = "tests/testdata/hosts"
from .base import MyTestCase
from privacyidea.lib.machines import BaseMachineResolver
from privacyidea.lib.machines.hosts import HostsMachineResolver
from privacyidea.lib.machines.base import Machine, MachineResolverError
import netaddr
from privacyidea.lib.machineresolver import (get_resolver_list, save_resolver,
                                     delete_resolver, get_resolver_config,
                                     get_resolver_object, pretestresolver)
from privacyidea.lib.machine import get_machines


class MachineObjectTestCase(MyTestCase):

    def test_01_create_machine(self):
        m = Machine("noResolver", "id1", ip="1.2.3.4")
        self.assertEqual(m.ip, netaddr.IPAddress("1.2.3.4"))

        m = Machine("noResolver", "id2", ip=netaddr.IPAddress("1.2.3.4"))
        self.assertEqual(m.ip, netaddr.IPAddress("1.2.3.4"))

    def test_02_has_attributes(self):

        m1 = Machine("noResolver", "id1", hostname="gandalf", ip="1.2.3.4")
        m2 = Machine("noResolver", "id2", hostname=["gandalf", "borodin"],
                     ip=[netaddr.IPAddress("1.2.3.4"), netaddr.IPAddress(
                         "2.3.4.5")])

        self.assertTrue(m1.has_hostname("gandalf"))
        self.assertTrue(m2.has_hostname("gandalf"))
        self.assertTrue(m1.has_ip("1.2.3.4"))
        self.assertTrue(m2.has_ip("1.2.3.4"))


class MachineResolverTestCase(MyTestCase):

    """
    Test the handling of machines on the library level, which creates
    machine objects in the database.
    """

    def test_01_save_resolver(self):
        # Save a resolver in the database

        # Try to create a resolver, which type does not exist:
        self.assertRaises(Exception, save_resolver, {"name": "testresolver",
                                                     "type": "DNE",
                                                     "filename": HOSTSFILE})

        # Try to create a resolver, with wrong name:
        self.assertRaises(Exception, save_resolver, {"name": "=====",
                                                     "type": "hosts",
                                                     "filename": HOSTSFILE})

        # Create a hosts resolver
        mr_obj = save_resolver({"name": "testresolver",
                                "type": "hosts",
                                "filename": "somefile",
                                "unknown_param": "xyz"})
        self.assertTrue(mr_obj > 0)
        # Check that the data is written correctly to the database
        machine = db.session.scalars(select(MachineResolver).filter_by(id=mr_obj)).first()
        self.assertEqual("testresolver", machine.name)
        self.assertEqual("hosts", machine.rtype)
        # check configs
        configs = machine.rconfig.all()
        self.assertEqual(2, len(configs))
        file_config = None
        unknown_config = None
        for config in configs:
            self.assertEqual(mr_obj, config.resolver_id)
            if config.Key == "filename":
                file_config = config
            elif config.Key == "unknown_param":
                unknown_config = config
        self.assertEqual("filename", file_config.Key)
        self.assertEqual("somefile", file_config.Value)
        self.assertEqual("string", file_config.Type)
        self.assertEqual("", file_config.Description)
        self.assertEqual("unknown_param", unknown_config.Key)
        self.assertEqual("xyz", unknown_config.Value)
        self.assertEqual("", unknown_config.Type)
        self.assertEqual("", unknown_config.Description)

        # update the resolver
        mr_obj = save_resolver({"name": "testresolver",
                                "type": "hosts",
                                "filename": HOSTSFILE,
                                "type.filename": "string",
                                "desc.filename": "the filename with the hosts",
                                "pw": "secretöö",
                                "type.pw": "password"})
        self.assertTrue(mr_obj > 0)
        # Check that the data is written correctly to the database
        machine = db.session.scalars(select(MachineResolver).filter_by(id=mr_obj)).first()
        self.assertEqual("testresolver", machine.name)
        self.assertEqual("hosts", machine.rtype)
        # check configs
        configs = machine.rconfig.all()
        self.assertEqual(3, len(configs))
        file_config = None
        unknown_config = None
        pw_config = None
        for config in configs:
            self.assertEqual(mr_obj, config.resolver_id)
            if config.Key == "filename":
                file_config = config
            elif config.Key == "unknown_param":
                unknown_config = config
            elif config.Key == "pw":
                pw_config = config
        self.assertEqual("filename", file_config.Key)
        self.assertEqual(HOSTSFILE, file_config.Value)
        self.assertEqual("string", file_config.Type)
        self.assertEqual("the filename with the hosts", file_config.Description)
        self.assertEqual("pw", pw_config.Key)
        self.assertNotEqual("secretöö", pw_config.Value)   # encrypted in DB
        self.assertEqual("password", pw_config.Type)
        self.assertEqual("", pw_config.Description)
        # previously set config is still there
        self.assertEqual("unknown_param", unknown_config.Key)
        self.assertEqual("xyz", unknown_config.Value)
        self.assertEqual("", unknown_config.Type)
        self.assertEqual("", unknown_config.Description)

        # wrong machine resolver definitions
        # missing value with type
        self.assertRaises(Exception, save_resolver, {"name": "t2",
                                                     "type": "hosts",
                                                     "type.filename": "string"})

        # missing value with description
        self.assertRaises(Exception, save_resolver, {"name": "t2",
                                                     "type": "hosts",
                                                     "desc.filename": "s.t."})

    def test_02_list_resolvers(self):
        # check if the resolver, we created is in the database
        l = get_resolver_list()
        self.assertTrue("testresolver" in l, l)

        l = get_resolver_list(filter_resolver_name="testresolver")
        self.assertTrue("testresolver" in l, l)

        l = get_resolver_list(filter_resolver_type="hosts")
        self.assertTrue("testresolver" in l, l)

    def test_03_get_resolver_config(self):
        c = get_resolver_config("testresolver")
        self.assertSetEqual({"filename", "pw", "unknown_param"}, set(c.keys()))
        self.assertEqual(c.get("filename"), HOSTSFILE)
        self.assertEqual(c.get("pw"), "secretöö")
        self.assertEqual(c.get("unknown_param"), "xyz")

    def test_04_get_machines(self):
        # get resolver object
        reso_obj = get_resolver_object("testresolver")
        self.assertTrue(isinstance(reso_obj, HostsMachineResolver))
        self.assertEqual(reso_obj.type, "hosts")

    @staticmethod
    def test_05_pretest():
        (result, desc) = pretestresolver("hosts", {"filename": "/dev/null"})

    def test_06_get_all_machines(self):
        # get machines from all resolvers
        machines = get_machines()
        self.assertEqual(len(machines), 5)
        machines = get_machines(hostname="n")
        self.assertEqual(len(machines), 4)

        for machine in machines:
            # check if each machines is in resolver "testresolver"
            self.assertEqual(machine.resolver_name, "testresolver")

    def test_99_delete_resolver(self):
        machine_id = db.session.scalars(select(MachineResolver).filter_by(name="testresolver")).first().id
        delete_resolver("testresolver")
        l = get_resolver_list(filter_resolver_name="testresolver")
        self.assertTrue("testresolver" not in l, l)

        # Check that also the configs are deleted
        configs = db.session.scalars(select(MachineResolverConfig)).all()
        for config in configs:
            # Ensure there is no config with the deleted resolver_id and also no config without any resolver_id
            self.assertNotEqual(machine_id, config.resolver_id, config)
            self.assertIsNotNone(config.resolver_id, config)


class BaseMachineTestCase(MyTestCase):
    """
    Test the base resolver
    """
    mreso = BaseMachineResolver("newresolver",
                                config={"somekey": "somevalue"})

    def test_02_get_type(self):
        mtype = self.mreso.get_type()
        self.assertEqual(mtype, "base")

    def test_03_get_id(self):
        mid = self.mreso.get_machine_id(hostname="dummy")
        self.assertEqual(mid, "")

    def test_04_get_machines(self):
        machines = self.mreso.get_machines()
        self.assertEqual(machines, [])


class HostsMachineTestCase(MyTestCase):
    """
    Test the Hosts Resolver
    """
    mreso = HostsMachineResolver("myResolver",
                                 config={"filename": HOSTSFILE})

    def test_01_get_config_description(self):
        desc = self.mreso.get_config_description()
        self.assertEqual(desc.get("hosts").get("config").get("filename"),
                         "string")

    def test_02_get_machines(self):
        machines = self.mreso.get_machines()
        self.assertEqual(len(machines), 5)

        machines = self.mreso.get_machines(hostname="gandalf")
        self.assertEqual(len(machines), 1)

        machines = self.mreso.get_machines(hostname="gandalf",
                                           ip=netaddr.IPAddress("192.168.0.1"))
        self.assertEqual(len(machines), 1)

        # THere are 3 machines, whose name contains an "n"
        machines = self.mreso.get_machines(hostname="n",
                                           substring=True)
        self.assertEqual(len(machines), 4)

    def test_02_get_machines_any(self):
        machines = self.mreso.get_machines(any="19")
        # 3 machines with IP 192...
        self.assertEqual(len(machines), 4)

        machines = self.mreso.get_machines(any="in")
        # 3 machines: pippIN and borodIN
        self.assertEqual(len(machines), 2)

        machines = self.mreso.get_machines(any="0")
        # 4 machines: all IP addresses
        self.assertEqual(len(machines), 5)

        machines = self.mreso.get_machines(any="gandalf")
        # Only one machine
        self.assertEqual(len(machines), 2)

    def test_03_get_single_machine(self):
        machine = self.mreso.get_machines(machine_id="192.168.0.1")[0]
        self.assertEqual(machine.id, "192.168.0.1")
        self.assertEqual(machine.ip, netaddr.IPAddress("192.168.0.1"))
        self.assertTrue(machine.has_hostname("gandalf"))
        self.assertTrue(machine.has_hostname("whitewizard"))

        machine = self.mreso.get_machines(machine_id="192.168.1.10")[0]
        self.assertTrue(machine.has_ip(netaddr.IPAddress("192.168.1.10")))
        self.assertTrue(machine.has_ip("192.168.1.10"))
        self.assertTrue(machine.has_hostname("borodin"))

    def test_04_get_machine_id(self):
        id = self.mreso.get_machine_id(hostname="not existing")
        self.assertTrue(id is None)

        id = self.mreso.get_machine_id(hostname="gandalf")
        self.assertEqual(id, "192.168.0.1")

        id = self.mreso.get_machine_id(ip="192.168.0.2")
        self.assertEqual(id, "192.168.0.2")

    def test_05_failing_load_config(self):
        # missing filename
        self.assertRaises(MachineResolverError,
                          self.mreso.load_config,
                          {"name": "nothing"})
