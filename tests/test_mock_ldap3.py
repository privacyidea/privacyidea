#-*- coding: utf-8 -*-
"""
This test file tests the test.ldap3mock
"""

import unittest
import ldap3
from . import ldap3mock
from privacyidea.lib.resolvers.LDAPIdResolver import trim_objectGUID

objectGUIDs = [
    '039b36ef-e7c0-42f3-9bf9-ca6a6c0d4d31',
    '039b36ef-e7c0-42f3-9bf9-ca6a6c0d4d77',
    '039b36ef-e7c0-42f3-9bf9-ca6a6c0d4d54',
    '039b36ef-e7c0-42f3-9bf9-ca6a6c0d4d88'
]

LDAPDirectory = [{"dn": "cn=alice,ou=example,o=test",
                 "attributes": {'cn': 'alice',
                                "sn": "Cooper",
                                "givenName": "Alice",
                                'userPassword': 'alicepw',
                                'oid': "2",
                                "homeDirectory": "/home/alice",
                                "email": "alice@test.com",
                                "accountExpires": 9223372036854775805,
                                "objectGUID": objectGUIDs[0],
                                'mobile': ["1234", "45678"]}},
                {"dn": 'cn=mini,ou=example,o=test',
                 "attributes": {'cn': 'mini',
                                "sn": "Cooper",
                                "givenName": "Mini",
                                'userPassword': 'minipw',
                                'oid': "2",
                                "homeDirectory": "/home/mini",
                                "email": "mini@test.com",
                                "accountExpires": 0,
                                "objectGUID": objectGUIDs[1],
                                'mobile': ["1234", "45678"]}},
                {"dn": 'cn=bob,ou=example,o=test',
                 "attributes": {'cn': 'bob',
                                "sn": "Marley",
                                "givenName": "Robert",
                                "description": "Bobs Account",
                                "email": "bob@example.com",
                                "mobile": "123456",
                                "homeDirectory": "/home/bob",
                                'userPassword': 'bobpwééé',
                                "accountExpires": 9223372036854775807,
                                "objectGUID": objectGUIDs[2],
                                'oid': "3"}},
                {"dn": 'cn=manager,ou=example,o=test',
                 "attributes": {'cn': 'manager',
                                "givenName": "Corny",
                                "sn": "keule",
                                "email": "ck@o",
                                "mobile": "123354",
                                "accountExpires": 9223372036854775808,
                                'userPassword': 'ldaptest',
                                "objectGUID": objectGUIDs[3],
                                'oid': "1"}}]


class LDAPMockTestCase(unittest.TestCase):
    """
    Test the ldap3mock
    """

    @ldap3mock.activate
    def setUp(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)

        host = "localhost"
        u = "manager"
        p = "ldaptest"
        self.base = "o=test"

        srv = ldap3.Server(host, port=389, use_ssl=False, connect_timeout=5)
        self.c = ldap3.Connection(srv, user=u, password=p,
                                  auto_referrals=False,
                                  client_strategy=ldap3.SYNC, check_names=True,
                                  authentication=ldap3.SIMPLE, auto_bind=False)
        self.c.open()
        self.c.bind()

    def tearDown(self):
        self.c.unbind()

    def test_00_wrong_basedn(self):

        s = "(&(cn=*))"
        base = "o=invalid"
        self.c.search(search_base=base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 0)

        s = "(!(cn=*))"
        base = "o=invalid"
        self.c.search(search_base=base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 0)

        s = "(|(cn=*)(sn=*))"
        base = "o=invalid"
        self.c.search(search_base=base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 0)

    def test_01_invalid_attribute(self):

        s = "(&(invalid=*))"
        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 0)

    def test_02_invalid_search_string(self):

        s = "(&cn=*))"
        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 0)

        s = "(&(cn=*)sn=*)"
        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 0)

    def test_03_simple_and_simple_equal_condition(self):
        dn = "cn=bob,ou=example,o=test"
        s = "(&(cn=bob))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=bob,ou=example,o=test"
        s = "(&(cn~=bob))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=alice,ou=example,o=test"
        dn1 = "cn=mini,ou=example,o=test"
        s = "(&(sn=Cooper))"
        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 2)
        self.assertTrue(self.c.response[0].get("dn") == dn)
        self.assertTrue(self.c.response[1].get("dn") == dn1)

        dn = "cn=alice,ou=example,o=test"
        dn1 = "cn=mini,ou=example,o=test"
        s = "(&(sn~=Cooper))"
        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 2)
        self.assertTrue(self.c.response[0].get("dn") == dn)
        self.assertTrue(self.c.response[1].get("dn") == dn1)

        dn = "cn=bob,ou=example,o=test"
        s = "(&(objectGUID=%s))" % trim_objectGUID(objectGUIDs[2])

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=bob,ou=example,o=test"
        s = "(&(objectGUID~=%s))" % trim_objectGUID(objectGUIDs[2])

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=bob,ou=example,o=test"
        s = "(&(email=bob@example.com))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=bob,ou=example,o=test"
        s = "(&(email~=bob@example.com))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=mini,ou=example,o=test"
        s = "(&(accountExpires=0))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=mini,ou=example,o=test"
        s = "(&(accountExpires~=0))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

    def test_04_simple_and_wildcard_equal_condition(self):

        dn = "cn=bob,ou=example,o=test"
        s = "(&(cn=bo*))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=bob,ou=example,o=test"
        s = "(&(cn~=bo*))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=bob,ou=example,o=test"
        s = "(&(cn=*ob))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=bob,ou=example,o=test"
        s = "(&(cn~=*ob))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=bob,ou=example,o=test"
        s = "(&(cn=b*b))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=bob,ou=example,o=test"
        s = "(&(cn~=b*b))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=bob,ou=example,o=test"
        s = "(&(email=bob@e*))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=bob,ou=example,o=test"
        s = "(&(email~=bob@e*))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

    def test_05_simple_and_simple_greater_condition(self):
        dn = "cn=bob,ou=example,o=test"
        s = "(&(oid>=3))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=manager,ou=example,o=test"
        s = "(&(accountExpires>=9223372036854775808))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

    def test_06_simple_and_simple_less_condition(self):
        dn = "cn=manager,ou=example,o=test"
        s = "(&(oid<=1))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=alice,ou=example,o=test"
        dn1 = "cn=mini,ou=example,o=test"
        s = "(&(accountExpires<=9223372036854775805))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 2)
        self.assertTrue(self.c.response[0].get("dn") == dn)
        self.assertTrue(self.c.response[1].get("dn") == dn1)

    def test_07_multi_and(self):
        dn = "cn=bob,ou=example,o=test"
        s = "(&(oid>=2)(sn=Marley))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=bob,ou=example,o=test"
        s = "(&(cn~=bob)(sn=*e*)(accountExpires>=100))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

    def test_08_simple_not_simple_equal_condition(self):
        dn = "cn=bob,ou=example,o=test"
        dn1 = "cn=manager,ou=example,o=test"
        s = "(!(sn=Cooper))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 2)
        self.assertTrue(self.c.response[0].get("dn") == dn)
        self.assertTrue(self.c.response[1].get("dn") == dn1)

        dn = "cn=bob,ou=example,o=test"
        dn1 = "cn=manager,ou=example,o=test"
        s = "(!(sn~=Cooper))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 2)
        self.assertTrue(self.c.response[0].get("dn") == dn)
        self.assertTrue(self.c.response[1].get("dn") == dn1)

        dn = "cn=alice,ou=example,o=test"
        dn1 = "cn=mini,ou=example,o=test"
        dn2 = "cn=manager,ou=example,o=test"
        s = "(!(objectGUID=%s))" % trim_objectGUID(objectGUIDs[2])

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 3)
        self.assertTrue(self.c.response[0].get("dn") == dn)
        self.assertTrue(self.c.response[1].get("dn") == dn1)
        self.assertTrue(self.c.response[2].get("dn") == dn2)

        dn = "cn=alice,ou=example,o=test"
        dn1 = "cn=mini,ou=example,o=test"
        dn2 = "cn=manager,ou=example,o=test"
        s = "(!(objectGUID~=%s))" % trim_objectGUID(objectGUIDs[2])

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 3)
        self.assertTrue(self.c.response[0].get("dn") == dn)
        self.assertTrue(self.c.response[1].get("dn") == dn1)
        self.assertTrue(self.c.response[2].get("dn") == dn2)

        dn = "cn=alice,ou=example,o=test"
        dn1 = "cn=mini,ou=example,o=test"
        dn2 = "cn=manager,ou=example,o=test"
        s = "(!(email=bob@example.com))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 3)
        self.assertTrue(self.c.response[0].get("dn") == dn)
        self.assertTrue(self.c.response[1].get("dn") == dn1)
        self.assertTrue(self.c.response[2].get("dn") == dn2)

        dn = "cn=alice,ou=example,o=test"
        dn1 = "cn=mini,ou=example,o=test"
        dn2 = "cn=manager,ou=example,o=test"
        s = "(!(email~=bob@example.com))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 3)
        self.assertTrue(self.c.response[0].get("dn") == dn)
        self.assertTrue(self.c.response[1].get("dn") == dn1)
        self.assertTrue(self.c.response[2].get("dn") == dn2)

        dn = "cn=alice,ou=example,o=test"
        dn1 = "cn=bob,ou=example,o=test"
        dn2 = "cn=manager,ou=example,o=test"
        s = "(!(accountExpires=0))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 3)
        self.assertTrue(self.c.response[0].get("dn") == dn)
        self.assertTrue(self.c.response[1].get("dn") == dn1)
        self.assertTrue(self.c.response[2].get("dn") == dn2)

        dn = "cn=alice,ou=example,o=test"
        dn1 = "cn=bob,ou=example,o=test"
        dn2 = "cn=manager,ou=example,o=test"
        s = "(!(accountExpires~=0))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 3)
        self.assertTrue(self.c.response[0].get("dn") == dn)
        self.assertTrue(self.c.response[1].get("dn") == dn1)
        self.assertTrue(self.c.response[2].get("dn") == dn2)

    def test_09_simple_not_wildcard_equal_condition(self):

        dn = "cn=bob,ou=example,o=test"
        dn1 = "cn=manager,ou=example,o=test"
        s = "(!(sn=Coope*))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 2)
        self.assertTrue(self.c.response[0].get("dn") == dn)
        self.assertTrue(self.c.response[1].get("dn") == dn1)

        dn = "cn=bob,ou=example,o=test"
        dn1 = "cn=manager,ou=example,o=test"
        s = "(!(sn~=Coope*))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 2)
        self.assertTrue(self.c.response[0].get("dn") == dn)
        self.assertTrue(self.c.response[1].get("dn") == dn1)

        dn = "cn=bob,ou=example,o=test"
        dn1 = "cn=manager,ou=example,o=test"
        s = "(!(sn=*ooper))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 2)
        self.assertTrue(self.c.response[0].get("dn") == dn)
        self.assertTrue(self.c.response[1].get("dn") == dn1)

        dn = "cn=bob,ou=example,o=test"
        dn1 = "cn=manager,ou=example,o=test"
        s = "(!(sn~=*ooper))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 2)
        self.assertTrue(self.c.response[0].get("dn") == dn)
        self.assertTrue(self.c.response[1].get("dn") == dn1)

        dn = "cn=bob,ou=example,o=test"
        dn1 = "cn=manager,ou=example,o=test"
        s = "(!(sn=Co*er))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 2)
        self.assertTrue(self.c.response[0].get("dn") == dn)
        self.assertTrue(self.c.response[1].get("dn") == dn1)

        dn = "cn=bob,ou=example,o=test"
        dn1 = "cn=manager,ou=example,o=test"
        s = "(!(sn~=Co*er))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 2)
        self.assertTrue(self.c.response[0].get("dn") == dn)
        self.assertTrue(self.c.response[1].get("dn") == dn1)

        dn = "cn=alice,ou=example,o=test"
        dn1 = "cn=mini,ou=example,o=test"
        dn2 = "cn=manager,ou=example,o=test"
        s = "(!(email=bob@e*))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 3)
        self.assertTrue(self.c.response[0].get("dn") == dn)
        self.assertTrue(self.c.response[1].get("dn") == dn1)
        self.assertTrue(self.c.response[2].get("dn") == dn2)

        dn = "cn=alice,ou=example,o=test"
        dn1 = "cn=mini,ou=example,o=test"
        dn2 = "cn=manager,ou=example,o=test"
        s = "(!(email~=bob@e*))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 3)
        self.assertTrue(self.c.response[0].get("dn") == dn)
        self.assertTrue(self.c.response[1].get("dn") == dn1)
        self.assertTrue(self.c.response[2].get("dn") == dn2)

    def test_10_simple_not_simple_greater_condition(self):
        dn = "cn=manager,ou=example,o=test"
        s = "(!(oid>=2))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=mini,ou=example,o=test"
        s = "(!(accountExpires>=1))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

    def test_11_simple_not_simple_less_condition(self):
        dn = "cn=bob,ou=example,o=test"
        s = "(!(oid<=2))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=manager,ou=example,o=test"
        s = "(!(accountExpires<=9223372036854775807))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

    def test_12_multi_not(self):
        dn = "cn=alice,ou=example,o=test"
        dn1 = "cn=bob,ou=example,o=test"
        dn2 = "cn=manager,ou=example,o=test"
        s = "(!(&(sn~=Cooper)(cn=mini)))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 3)
        self.assertTrue(self.c.response[0].get("dn") == dn)
        self.assertTrue(self.c.response[1].get("dn") == dn1)
        self.assertTrue(self.c.response[2].get("dn") == dn2)

        dn = "cn=mini,ou=example,o=test"
        s = "(!(|(cn~=bob)(sn=*le*)(accountExpires>=100)))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

    def test_13_simple_or_simple_equal_condition(self):
        dn = "cn=mini,ou=example,o=test"
        s = "(|(cn=mini))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=mini,ou=example,o=test"
        s = "(|(cn~=mini))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=bob,ou=example,o=test"
        s = "(|(objectGUID=%s))" % trim_objectGUID(objectGUIDs[2])

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=bob,ou=example,o=test"
        s = "(|(objectGUID~=%s))" % trim_objectGUID(objectGUIDs[2])

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=bob,ou=example,o=test"
        s = "(|(email=bob@example.com))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=bob,ou=example,o=test"
        s = "(|(email~=bob@example.com))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=mini,ou=example,o=test"
        s = "(|(accountExpires=0))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=mini,ou=example,o=test"
        s = "(|(accountExpires~=0))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

    def test_14_simple_or_wildcard_equal_condition(self):

        dn = "cn=manager,ou=example,o=test"
        s = "(|(cn=manage*))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=manager,ou=example,o=test"
        s = "(|(cn~=manage*))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=manager,ou=example,o=test"
        s = "(|(cn=*anager))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=manager,ou=example,o=test"
        s = "(|(cn~=*anager))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=manager,ou=example,o=test"
        s = "(|(cn=ma*er))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=manager,ou=example,o=test"
        s = "(|(cn~=ma*er))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=bob,ou=example,o=test"
        s = "(|(email=bob@e*))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=bob,ou=example,o=test"
        s = "(|(email~=bob@e*))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

    def test_15_simple_or_simple_greater_condition(self):
        dn = "cn=bob,ou=example,o=test"
        s = "(|(oid>=3))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=manager,ou=example,o=test"
        s = "(|(accountExpires>=9223372036854775808))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

    def test_16_simple_or_simple_less_condition(self):
        dn = "cn=manager,ou=example,o=test"
        s = "(|(oid<=1))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=mini,ou=example,o=test"
        s = "(|(accountExpires<=100))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

    def test_17_multi_or(self):
        dn = "cn=bob,ou=example,o=test"
        dn1 = "cn=mini,ou=example,o=test"
        s = "(|(oid>=3)(accountExpires=0))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 2)
        self.assertTrue(self.c.response[0].get("dn") == dn)
        self.assertTrue(self.c.response[1].get("dn") == dn1)

        dn = "cn=bob,ou=example,o=test"
        dn1 = "cn=manager,ou=example,o=test"
        dn2 = "cn=mini,ou=example,o=test"
        s = "(|(cn~=bob)(sn=ke*le)(accountExpires<=0))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 3)
        self.assertTrue(self.c.response[0].get("dn") == dn)
        self.assertTrue(self.c.response[1].get("dn") == dn1)
        self.assertTrue(self.c.response[2].get("dn") == dn2)

    def test_18_simple_and_multi_value_attribute(self):

        dn1 = "cn=alice,ou=example,o=test"
        dn2 = "cn=mini,ou=example,o=test"
        s = "(&(mobile=45678))"
        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 2)
        self.assertTrue(self.c.response[0].get("dn") == dn1)
        self.assertTrue(self.c.response[1].get("dn") == dn2)

    def test_19_simple_or_multi_value_attribute(self):

        dn1 = "cn=alice,ou=example,o=test"
        dn2 = "cn=mini,ou=example,o=test"
        s = "(|(mobile=45678))"
        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 2)
        self.assertTrue(self.c.response[0].get("dn") == dn1)
        self.assertTrue(self.c.response[1].get("dn") == dn2)

    def test_20_simple_not_multi_value_attribute(self):

        dn = "cn=bob,ou=example,o=test"
        dn1 = "cn=manager,ou=example,o=test"
        s = "(!(mobile=45678))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 2)
        self.assertTrue(self.c.response[0].get("dn") == dn)
        self.assertTrue(self.c.response[1].get("dn") == dn1)

    def test_21_not_multi_or_multi_value_attribute(self):
        dn = "cn=bob,ou=example,o=test"
        dn1 = "cn=manager,ou=example,o=test"
        s = "(!(|(mobile=1234)(mobile=45678)))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 2)
        self.assertTrue(self.c.response[0].get("dn") == dn)
        self.assertTrue(self.c.response[1].get("dn") == dn1)

    def test_22_two_levels_of_filter(self):
        dn = "cn=alice,ou=example,o=test"
        dn1 = "cn=bob,ou=example,o=test"
        dn2 = "cn=manager,ou=example,o=test"
        s = "(|(accountExpires>=9223372036854775807)(!(accountExpires=0)))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 3)
        self.assertTrue(self.c.response[0].get("dn") == dn)
        self.assertTrue(self.c.response[1].get("dn") == dn1)
        self.assertTrue(self.c.response[2].get("dn") == dn2)

        dn = "cn=alice,ou=example,o=test"
        s = "(&(accountExpires<=9223372036854775806)(!(accountExpires=0)))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

        dn = "cn=bob,ou=example,o=test"
        s = "(&(cn=*)(objectGUID~=%s))" % trim_objectGUID(objectGUIDs[2])

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

    def test_23_three_levels_of_filter(self):
        dn = "cn=alice,ou=example,o=test"
        s = "(&(cn=*)(&(accountExpires<=9223372036854775806)(!(accountExpires=0))))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

    def test_24_filter_containing_spaces(self):
        dn = "cn=bob,ou=example,o=test"
        s = "(&(description=Bobs Account))"

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

    def test_25_add_user(self):
        dn = "cn=John Smith,ou=example,o=test"
        data = { "sn" : "Smith",
                "cn" : "John Smith",
                "userPassword": "S3cr3t",
                }
        classes = ["top", "inetOrgPerson"]
        s = "(&(cn=John Smith)(objectClass=top))"

        r = self.c.add(dn, classes, data)
        self.assertTrue(r)

        self.c.search(search_base=self.base, search_filter=s, search_scope=ldap3.SUBTREE,
                attributes = ldap3.ALL_ATTRIBUTES, paged_size = 5)

        self.assertTrue(len(self.c.response) == 1)
        self.assertTrue(self.c.response[0].get("dn") == dn)

