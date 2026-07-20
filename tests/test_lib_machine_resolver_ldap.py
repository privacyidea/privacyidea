# SPDX-FileCopyrightText: 2015 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
This test file tests the LDAP machine resolver in
lib/machines/ldap.py
"""
import netaddr

from .base import MyTestCase
from privacyidea.lib.machines.ldap import LdapMachineResolver
from privacyidea.lib.machines.base import MachineResolverError
from . import ldap3mock

HOSTSFILE = "tests/testdata/hosts"

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

        # THere is one machine that contains "e2"
        machines = self.mreso.get_machines(hostname="e2",
                                           substring=True)
        self.assertEqual(len(machines), 1)

    def test_04_get_machines_any(self):
        # The MockLdap module cannot handle complicates ldap searches like
        # (&(&( )( )( ))(|( )( )( )) )
        # so we only test the creation of the ldapsearch string
        ldap_filter = LdapMachineResolver.\
            _create_ldap_filter("(""objectClass=computer)",
                                "objectSid", "",
                                "dNSHostName", "",
                                "", "",
                                substring=True, any="substr")
        self.assertEqual(ldap_filter, "(&(&(objectClass=computer))"
                                      "(|(objectSid=*substr*)("
                                      "dNSHostName=*substr*)))")

    def test_05_get_single_machine(self):

        machines = self.mreso.get_machines(machine_id="cn=machine1,ou=example,o=test")
        self.assertEqual(len(machines), 1)
        machine = machines[0]
        self.assertEqual(machine.id, "cn=machine1,ou=example,o=test")
        self.assertTrue(machine.has_hostname("machine1.example.test"))

    def test_06_get_machine_id(self):
        machine_blueprintid = self.mreso.get_machine_id(hostname="not existing")
        self.assertTrue(machine_blueprintid is None)

        machine_blueprintid = self.mreso.get_machine_id(hostname="machine1.example.test")
        self.assertEqual(machine_blueprintid, "cn=machine1,ou=example,o=test")

    @ldap3mock.activate
    def test_07_testconnection(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        (success, desc) = LdapMachineResolver.testconnection(MYCONFIG)
        self.assertTrue(success)
        self.assertTrue(desc.startswith("Your LDAP machine resolver configuration seems to be OK, "
                                        "3 machine objects found"), desc)

    @ldap3mock.activate
    def test_08_start_tls(self):
        # Check that START_TLS and TLS_VERIFY are actually passed to the ldap3 Connection
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        config = MYCONFIG.copy()
        config['START_TLS'] = '1'
        config['TLS_VERIFY'] = '1'
        start_tls_resolver = LdapMachineResolver("myResolver", config=config)
        machines = start_tls_resolver.get_machines()
        self.assertEqual(len(machines), 3)
        # We check two things:
        # 1) start_tls has actually been called!
        self.assertTrue(start_tls_resolver.connection.start_tls_called)
        # 2) All Server objects were constructed with a non-None TLS context, but use_ssl=False
        for _, kwargs in ldap3mock.get_server_mock().call_args_list:
            self.assertIsNotNone(kwargs['tls'])
            self.assertFalse(kwargs['use_ssl'])

    @ldap3mock.activate
    def test_09_ldaps(self):
        # Check that use_ssl and tls are actually passed to the Connection
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        config = MYCONFIG.copy()
        config['LDAPURI'] = 'ldaps://1.2.3.4'
        config['TLS_VERIFY'] = '1'
        ldaps_resolver = LdapMachineResolver("myResolver", config=config)
        machines = ldaps_resolver.get_machines()
        self.assertEqual(len(machines), 3)
        # We check that all Server objects were constructed with a non-None TLS context and use_ssl=True
        for _, kwargs in ldap3mock.get_server_mock().call_args_list:
            self.assertIsNotNone(kwargs['tls'])
            self.assertTrue(kwargs['use_ssl'])

    @ldap3mock.activate
    def test_10_hostname_is_a_list_and_optional(self):
        directory = [{"dn": "cn=admin,ou=example,o=test",
                      "attributes": {"cn": "admin", "userPassword": "secret"}},
                     {"dn": "cn=multi,ou=example,o=test",
                      "attributes": {"cn": "multi",
                                     "objectClass": "computer",
                                     "dNSHostName": ["multi.example.test",
                                                     "alias.example.test"]}},
                     {"dn": "cn=nohost,ou=example,o=test",
                      "attributes": {"cn": "nohost",
                                     "objectClass": "computer",
                                     "dNSHostName": []}}]
        ldap3mock.setLDAPDirectory(directory)
        # Use a fresh resolver: self.mreso caches its bound connection (and
        # thus the directory) from an earlier test.
        resolver = LdapMachineResolver("myResolver", config=MYCONFIG)
        machines = resolver.get_machines()
        # A machine without a hostname is still returned, not dropped.
        self.assertEqual(2, len(machines))
        by_id = {m.id: m for m in machines}

        # All values of a multi-valued attribute are returned.
        multi = by_id["cn=multi,ou=example,o=test"]
        self.assertListEqual(["multi.example.test", "alias.example.test"], multi.hostname)
        self.assertTrue(multi.has_hostname("alias.example.test"))

        # A missing hostname is represented as an empty list.
        nohost = by_id["cn=nohost,ou=example,o=test"]
        self.assertListEqual([], nohost.hostname)

    @ldap3mock.activate
    def test_11_invalid_ip_does_not_drop_machine(self):
        directory = [{"dn": "cn=admin,ou=example,o=test",
                      "attributes": {"cn": "admin", "userPassword": "secret"}},
                     {"dn": "cn=goodip,ou=example,o=test",
                      "attributes": {"cn": "goodip",
                                     "objectClass": "computer",
                                     "dNSHostName": "goodip.example.test",
                                     "iPAddress": "1.2.3.4"}},
                     {"dn": "cn=badip,ou=example,o=test",
                      "attributes": {"cn": "badip",
                                     "objectClass": "computer",
                                     "dNSHostName": "badip.example.test",
                                     "iPAddress": "not-an-ip"}}]
        ldap3mock.setLDAPDirectory(directory)
        config = MYCONFIG.copy()
        config["IPATTRIBUTE"] = "iPAddress"
        resolver = LdapMachineResolver("myResolver", config=config)
        machines = resolver.get_machines()
        # An unparsable ip is dropped, but the machine is still returned.
        self.assertEqual(2, len(machines))
        by_id = {m.id: m for m in machines}
        self.assertEqual(netaddr.IPAddress("1.2.3.4"),
                         by_id["cn=goodip,ou=example,o=test"].ip)
        self.assertIsNone(by_id["cn=badip,ou=example,o=test"].ip)

    @ldap3mock.activate
    def test_12_skip_machine_without_id_attribute(self):
        directory = [{"dn": "cn=admin,ou=example,o=test",
                      "attributes": {"cn": "admin", "userPassword": "secret"}},
                     {"dn": "cn=withid,ou=example,o=test",
                      "attributes": {"cn": "withid",
                                     "objectClass": "computer",
                                     "objectSid": "S-1-5-21-100",
                                     "dNSHostName": "withid.example.test"}},
                     {"dn": "cn=noid,ou=example,o=test",
                      "attributes": {"cn": "noid",
                                     "objectClass": "computer",
                                     "dNSHostName": "noid.example.test"}}]
        ldap3mock.setLDAPDirectory(directory)
        config = MYCONFIG.copy()
        config["IDATTRIBUTE"] = "objectSid"
        resolver = LdapMachineResolver("myResolver", config=config)
        machines = resolver.get_machines()
        # The entry lacking the configured id attribute is skipped.
        self.assertEqual(1, len(machines))
        self.assertEqual("S-1-5-21-100", machines[0].id)
