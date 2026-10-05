# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Check that get_orphaned_serials decides like TokenClass.is_orphaned, while asking each resolver once
for a whole chunk of tokens instead of once per token.
"""
from unittest import mock

from privacyidea.lib.realm import set_realm
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.resolvers.HTTPResolver import HTTPResolver
from privacyidea.lib.token import get_orphaned_serials, get_tokens, init_token
from privacyidea.lib.user import User
from privacyidea.models import TokenOwner
from . import ldap3mock
from .base import MyTestCase
from .test_lib_token_list_lookups import count_ldap_searches

LDAP_DIRECTORY = [{"dn": f"cn=user{i:02d},ou=example,o=test",
                   "attributes": {"cn": f"user{i:02d}",
                                  "sn": f"Sur{i:02d}",
                                  "givenName": f"Given{i:02d}",
                                  "email": f"user{i:02d}@test.com",
                                  "userPassword": "pw",
                                  "oid": str(i)}} for i in range(3)]

LDAP_PARAMS = {"LDAPURI": "ldap://localhost",
               "LDAPBASE": "o=test",
               "BINDDN": "cn=user00,ou=example,o=test",
               "BINDPW": "pw",
               "LOGINNAMEATTRIBUTE": "cn",
               "LDAPSEARCHFILTER": "(cn=*)",
               "USERINFO": '{ "username": "cn", "email": "email", "surname": "sn", "givenname": "givenName" }',
               "UIDTYPE": "oid",
               # The per-process cache would hide the lookups these tests count
               "CACHE_TIMEOUT": "0",
               "resolver": "orphanldap",
               "type": "ldapresolver"}

HTTP_PARAMS = {"resolver": "orphanhttp",
               "type": "httpresolver",
               "endpoint": "http://localhost:8080/get-data",
               "method": "GET",
               "requestMapping": """{"id": "{userid}"}""",
               "responseMapping": """{"username": "{data.the_username}"}""",
               "hasSpecialErrorHandler": False}


class OrphanedTokenTestCase(MyTestCase):

    serial_wildcard = "ORPH*"

    @classmethod
    @ldap3mock.activate
    def setUpClass(cls):
        super().setUpClass()
        ldap3mock.setLDAPDirectory(LDAP_DIRECTORY)
        save_resolver(LDAP_PARAMS)
        set_realm("orphanldaprealm", [{"name": "orphanldap"}])
        save_resolver(HTTP_PARAMS)
        set_realm("orphanhttprealm", [{"name": "orphanhttp"}])

        for i in range(3):
            init_token({"type": "spass", "serial": f"ORPHEXISTS{i}"},
                       user=User(login=f"user{i:02d}", realm="orphanldaprealm"))
        init_token({"type": "spass", "serial": "ORPHNOOWNER"})
        owners = {"ORPHDELETEDUSER": {"user_id": "99", "resolver": "orphanldap", "realmname": "orphanldaprealm"},
                  "ORPHDELETEDRESOLVER": {"user_id": "1000", "resolver": "deletedresolver"},
                  "ORPHNOREALM": {"user_id": "1", "resolver": "orphanldap"},
                  "ORPHNORESOLVER": {"user_id": "1", "resolver": ""},
                  "ORPHUNREACHABLE": {"user_id": "1", "resolver": "orphanhttp", "realmname": "orphanhttprealm"}}
        for serial, owner in owners.items():
            token = init_token({"type": "spass", "serial": serial})
            TokenOwner(token_id=token.token.id, **owner).save()

    @ldap3mock.activate
    def test_01_same_result_as_is_orphaned(self):
        ldap3mock.setLDAPDirectory(LDAP_DIRECTORY)
        tokens = get_tokens(serial_wildcard=self.serial_wildcard)
        self.assertEqual(9, len(tokens), tokens)

        with mock.patch.object(HTTPResolver, "getUsername", side_effect=Exception("not reachable")):
            for orphaned_on_error in [True, False]:
                expected = {token.token.serial for token in tokens if token.is_orphaned(orphaned_on_error)}
                self.assertSetEqual(expected, get_orphaned_serials(tokens, orphaned_on_error), orphaned_on_error)

            # Spelled out, so that a change of is_orphaned can not silently change both sides
            certainly_orphaned = {"ORPHDELETEDUSER", "ORPHDELETEDRESOLVER", "ORPHNOREALM"}
            self.assertSetEqual(certainly_orphaned | {"ORPHNORESOLVER", "ORPHUNREACHABLE"},
                                get_orphaned_serials(tokens, orphaned_on_error=True))
            self.assertSetEqual(certainly_orphaned, get_orphaned_serials(tokens, orphaned_on_error=False))

    @ldap3mock.activate
    def test_02_each_resolver_is_asked_once(self):
        ldap3mock.setLDAPDirectory(LDAP_DIRECTORY)
        tokens = get_tokens(serial_wildcard=self.serial_wildcard)

        with mock.patch.object(HTTPResolver, "getUsername", return_value="user01") as http_get_username:
            with count_ldap_searches() as search_filters:
                orphaned_serials = get_orphaned_serials(tokens)

        # Five tokens of the LDAP resolver are resolved with one search, and the one of the HTTP resolver
        # with one lookup. The deleted resolver and the owner without a resolver are not asked at all.
        self.assertEqual(1, len(search_filters), search_filters)
        self.assertEqual(1, http_get_username.call_count)
        self.assertNotIn("ORPHUNREACHABLE", orphaned_serials)

    def test_03_no_tokens(self):
        self.assertSetEqual(set(), get_orphaned_serials([]))
