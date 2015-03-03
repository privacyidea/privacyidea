"""
This test file tests the LDAP machine resolver in
lib/machines/ldap.py
"""

HOSTSFILE = "tests/testdata/hosts"
from .base import MyTestCase
from privacyidea.lib.machines.ldap import LdapMachineResolver
from privacyidea.lib.machines.base import MachineResolverError
import ldap3mock
import netaddr

LDAPDirectory = [{"dn": "cn=admin,ou=example,o=test",
                  "attributes": {"cn": "admin",
                                 "userPassword": "secret"}
                  },
                 {"dn": "cn=machine1,ou=example,o=test",
                  "attributes": {'cn': 'machine1',
                                 "objectClass": "computer",
                                 "dNSHostName": "machine1.example.test",
                                 "iPAddress": "1.2.3.4"}
                 },
                 {"dn": 'cn=machine2,ou=example,o=test',
                  "attributes": {'cn': 'machine2',
                                 "objectClass": "computer",
                                 "dNSHostName": "machine2.example.test"}
                 },
                 {"dn": 'cn=machine3,ou=example,o=test',
                  "attributes": {'cn': 'machine3',
                                 "objectClass": "computer",
                                 "dNSHostName": "machine3.example.test",
                                }
                 }]

MYCONFIG = {"HOSTNAMEATTRIBUTE": "dNSHostName",
            "LDAPURI": "ldap://1.2.3.4",
            "IDATTRIBUTE": "DN",
            "LDAPBASE": "o=test",
            "BINDDN": "cn=admin,ou=example,o=test",
            "BINDPW": "secret",
            "SEARCHFILTER": "(objectClass=computer)",
            "REVERSEFITLER": "(&(dNSHostName=%s)(objectClass=computer))"}


class LdapMachineTestCase(MyTestCase):
    """
    Test the LDAP Resolver
    """
    mreso = LdapMachineResolver("myResolver",
                                config=MYCONFIG)

    mrAD = LdapMachineResolver("myreso",
                               config={"LDAPURI": "ldap://172.16.200.202",
                                       "LDAPBASE": "dc=privacyidea,"
                                                   "dc=test",
                                       "BINDDN":
                                           "administrator@privacyidea.test",
                                       "BINDPW": "Test1234!",
                                       "HOSTNAMEATTRIBUTE": "dNSHostName"})


    def test_01_get_config_description(self):
        # Missing LDAPURI
        self.assertRaises(MachineResolverError, LdapMachineResolver,
                          "reso2", config={"IDATTRIBUTE": "na"})

        # Missing LDAPBASE
        self.assertRaises(MachineResolverError, LdapMachineResolver,
                          "reso2", config={"LDAPURI": "ldap://1.2.3.4"})

        desc = self.mreso.get_config_description()
        self.assertEqual(desc.get("ldap").get("config").get("LDAPURI"),
                         "string")

    """
    def test_01_get_machines(self):
        machines = self.mrAD.get_machines()
        self.assertEqual(len(machines), 1)
        self.assertEqual(machines[0].hostname, "dc01.privacyidea.test")

    def test_02_get_machine_id(self):
        id = self.mrAD.get_machine_id(hostname="dc01.privacyidea.test")
        self.assertEqual(id,
                         "CN=DC01,OU=Domain Controllers,DC=privacyidea,DC=test")
    """

    @ldap3mock.activate
    def test_03_get_machines(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        machines = self.mreso.get_machines()
        self.assertEqual(len(machines), 3)

        machines = self.mreso.get_machines(hostname="machine1.example.test")
        self.assertEqual(len(machines), 1)

        # THere is one machine, that contains "e2"
        machines = self.mreso.get_machines(hostname="e2",
                                           substring=True)
        self.assertEqual(len(machines), 1)

    def test_04_get_machines_any(self):
        # The MockLdap module can not handle complicates ldap searches like
        # (&(&( )( )( ))(|( )( )( )) )
        # so we only test the creation of the ldapsearch string
        filter = LdapMachineResolver.\
            _create_ldap_filter("(""objectClass=computer)",
                                "objectSid", "",
                                "dNSHostName", "",
                                "", "",
                                substring=True, any="substr")
        self.assertEqual(filter, "(&(&(objectClass=computer))"
                                 "(|(objectSid=*substr*)("
                                 "dNSHostName=*substr*)))")



    def test_05_get_single_machine(self):
        machine = self.mreso.get_machines(machine_id="cn=machine1,ou=example,o=test")[0]
        self.assertEqual(machine.id, "cn=machine1,ou=example,o=test")
        self.assertTrue(machine.has_hostname("machine1.example.test"))

    def test_06_get_machine_id(self):
        id = self.mreso.get_machine_id(hostname="not existing")
        self.assertTrue(id is None)

        id = self.mreso.get_machine_id(hostname="machine1.example.test")
        self.assertEqual(id, "cn=machine1,ou=example,o=test")

    @ldap3mock.activate
    def test_07_testconnection(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        (success, desc) = LdapMachineResolver.testconnection(MYCONFIG)
        self.assertTrue(success)
        self.assertEqual(desc, "Your LDAP config seems to be OK, 3 "
                               "machine objects found.")
