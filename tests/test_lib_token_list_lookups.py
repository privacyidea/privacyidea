# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Assert how many user store and database lookups one page of the token list costs.

The counts are what keeps the token list from resolving its owners and containers one token at a
time. A timing assertion would say the same thing far less reliably, so this counts round trips.
"""
from contextlib import contextmanager

import mock
from sqlalchemy import delete, event, select
from sqlalchemy.engine import Engine

from privacyidea.lib.container import add_token_to_container, find_container_by_serial, init_container
from privacyidea.lib.realm import set_realm
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.resolvers.LDAPIdResolver import IdResolver as LDAPResolver
from privacyidea.lib.token import (convert_token_objects_to_dicts, get_tokens, get_tokens_paginate, init_token,
                                   remove_token)
from privacyidea.lib.user import User
from privacyidea.models import db, Token, TokenContainerToken, TokenOwner
from . import ldap3mock
from .base import MyTestCase

NUM_TOKENS = 12

LDAP_DIRECTORY = [{"dn": f"cn=user{i:02d},ou=example,o=test",
                   "attributes": {"cn": f"user{i:02d}",
                                  "sn": f"Sur{i:02d}",
                                  "givenName": f"Given{i:02d}",
                                  "email": f"user{i:02d}@test.com",
                                  "userPassword": "pw",
                                  "oid": str(i)}} for i in range(NUM_TOKENS)]

LDAP_PARAMS = {"LDAPURI": "ldap://localhost",
               "LDAPBASE": "o=test",
               "BINDDN": "cn=user00,ou=example,o=test",
               "BINDPW": "pw",
               "LOGINNAMEATTRIBUTE": "cn",
               "LDAPSEARCHFILTER": "(cn=*)",
               "USERINFO": '{ "username": "cn", "email": "email", "surname": "sn", "givenname": "givenName" }',
               "UIDTYPE": "oid",
               # The per-process cache would hide the lookups these tests are about. The value has
               # to be a string: an integer 0 does not survive being saved.
               "CACHE_TIMEOUT": "0",
               "resolver": "ldapreso",
               "type": "ldapresolver"}


@contextmanager
def count_ldap_searches():
    """Collect the search filters the LDAP resolver sends while the block runs."""
    search_filters = []
    original_search = LDAPResolver._search

    def counting_search(self, search_base, search_filter, attributes):
        search_filters.append(search_filter)
        return original_search(self, search_base, search_filter, attributes)

    with mock.patch.object(LDAPResolver, "_search", counting_search):
        yield search_filters


@contextmanager
def count_statements():
    """Collect the SQL statements that are executed while the block runs."""
    statements = []

    def on_execute(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(Engine, "before_cursor_execute", on_execute)
    try:
        yield statements
    finally:
        event.remove(Engine, "before_cursor_execute", on_execute)


def count_containing(statements, fragment):
    return len([statement for statement in statements if fragment in statement])


class TokenListLookupTestCase(MyTestCase):
    """
    All tests of this class work on the tokens enrolled in setUpClass, and scope their queries to
    those serials so that tokens another test left behind can not change the counts.
    """

    serial_wildcard = "LIST*"

    @classmethod
    @ldap3mock.activate
    def setUpClass(cls):
        super().setUpClass()
        ldap3mock.setLDAPDirectory(LDAP_DIRECTORY)
        save_resolver(LDAP_PARAMS)
        set_realm("ldaprealm", [{"name": "ldapreso"}])

        cls.container_serial = init_container({"type": "generic"})["container_serial"]
        for i in range(NUM_TOKENS):
            user = User(login=f"user{i:02d}", realm="ldaprealm")
            token = init_token({"type": "hotp", "genkey": 1, "serial": f"LIST{i:02d}"}, user=user)
            add_token_to_container(cls.container_serial, token.get_serial())

    @ldap3mock.activate
    def test_01_page_of_distinct_owners_costs_one_search(self):
        ldap3mock.setLDAPDirectory(LDAP_DIRECTORY)

        with count_ldap_searches() as search_filters:
            with count_statements() as statements:
                result = get_tokens_paginate(serial=self.serial_wildcard, psize=NUM_TOKENS, page=1)

        self.assertEqual(NUM_TOKENS, len(result["tokens"]), result)
        # Every token has a different owner, and they are all resolved with one search
        self.assertEqual(1, len(search_filters), search_filters)
        self.assertEqual(NUM_TOKENS, len(set(token["username"] for token in result["tokens"])), result)
        self.assertEqual("user00", result["tokens"][0]["username"], result)
        self.assertEqual("ldaprealm", result["tokens"][0]["user_realm"], result)
        self.assertFalse(result["tokens"][0]["user_editable"], result)

        # The owners and the containers of the page are each read with one query, not one per token
        self.assertEqual(1, count_containing(statements, "tokenowner.token_id IN"), statements)
        self.assertEqual(1, count_containing(statements, "FROM tokencontainertoken"), statements)
        self.assertEqual({self.container_serial}, set(token["container_serial"] for token in result["tokens"]), result)

    @ldap3mock.activate
    def test_02_convert_token_objects_to_dicts_costs_one_search(self):
        ldap3mock.setLDAPDirectory(LDAP_DIRECTORY)
        tokens = get_tokens(serial_wildcard=self.serial_wildcard)

        with count_ldap_searches() as search_filters:
            with count_statements() as statements:
                token_dicts = convert_token_objects_to_dicts(tokens, user=None, user_role="admin")

        self.assertEqual(NUM_TOKENS, len(token_dicts), token_dicts)
        self.assertEqual(1, len(search_filters), search_filters)
        self.assertEqual(1, count_containing(statements, "tokenowner.token_id IN"), statements)
        self.assertEqual(1, count_containing(statements, "FROM tokencontainertoken"), statements)
        self.assertEqual(NUM_TOKENS, len(set(token["username"] for token in token_dicts)), token_dicts)

    @ldap3mock.activate
    def test_03_owners_beyond_one_chunk_are_split_over_searches(self):
        ldap3mock.setLDAPDirectory(LDAP_DIRECTORY)

        # A page with more owners than fit into one filter is spread over several searches, and
        # still resolves every one of them
        with mock.patch("privacyidea.lib.resolvers.LDAPIdResolver.BATCH_SEARCH_CHUNK_SIZE", 5):
            with count_ldap_searches() as search_filters:
                result = get_tokens_paginate(serial=self.serial_wildcard, psize=NUM_TOKENS, page=1)

        self.assertEqual(3, len(search_filters), search_filters)
        self.assertEqual(NUM_TOKENS, len(set(token["username"] for token in result["tokens"])), result)

    @ldap3mock.activate
    def test_04_a_failing_owner_does_not_cost_the_page(self):
        ldap3mock.setLDAPDirectory(LDAP_DIRECTORY)
        failing_user_id = "7"

        def failing_get_user_info(self, user_id, attributes=None):
            if user_id == failing_user_id:
                raise Exception("The user store is not reachable")
            return {"username": f"user{int(user_id):02d}"}

        # When the batch fails, the users are looked up one by one, so only the token whose owner
        # keeps failing is marked and the rest of the page still renders
        with mock.patch.object(LDAPResolver, "get_user_info_batch", side_effect=Exception("batch failed")):
            with mock.patch.object(LDAPResolver, "get_user_info", failing_get_user_info):
                result = get_tokens_paginate(serial=self.serial_wildcard, psize=NUM_TOKENS, page=1)

        usernames = {token["serial"]: token["username"] for token in result["tokens"]}
        self.assertEqual("**resolver error**", usernames[f"LIST{int(failing_user_id):02d}"], usernames)
        self.assertEqual("user00", usernames["LIST00"], usernames)
        self.assertEqual(1, len([name for name in usernames.values() if name == "**resolver error**"]), usernames)

    @ldap3mock.activate
    def test_05_an_owner_without_a_resolver_is_marked(self):
        ldap3mock.setLDAPDirectory(LDAP_DIRECTORY)

        with mock.patch("privacyidea.lib.token.query.get_resolver_object", return_value=None):
            result = get_tokens_paginate(serial=self.serial_wildcard, psize=NUM_TOKENS, page=1)

        self.assertEqual(NUM_TOKENS, len(result["tokens"]), result)
        for token in result["tokens"]:
            self.assertEqual("**resolver error**", token["username"], token)
            self.assertNotIn("user_editable", token, token)

    @ldap3mock.activate
    def test_06_a_resolver_that_can_not_be_loaded_is_marked(self):
        ldap3mock.setLDAPDirectory(LDAP_DIRECTORY)

        # Building a resolver applies its configuration, which raises on a broken one. That must
        # mark its tokens rather than fail the whole list
        with mock.patch("privacyidea.lib.token.query.get_resolver_object",
                        side_effect=Exception("the resolver configuration is broken")):
            result = get_tokens_paginate(serial=self.serial_wildcard, psize=NUM_TOKENS, page=1)

        self.assertEqual(NUM_TOKENS, len(result["tokens"]), result)
        for token in result["tokens"]:
            self.assertEqual("**resolver error**", token["username"], token)

    @ldap3mock.activate
    def test_07_a_token_in_two_containers_reports_the_same_one_every_time(self):
        ldap3mock.setLDAPDirectory(LDAP_DIRECTORY)
        # The association table permits a token in several containers, in which case the page has to
        # settle on one of them instead of following the order the rows come back in
        second_serial = init_container({"type": "generic"})["container_serial"]
        second_container_id = find_container_by_serial(second_serial)._db_container.id
        token_id = get_tokens(serial="LIST00")[0].token.id
        TokenContainerToken(token_id=token_id, container_id=second_container_id).save()

        try:
            container_serials = set()
            for _ in range(3):
                result = get_tokens_paginate(serial="LIST00", psize=1, page=1)
                container_serials.add(result["tokens"][0]["container_serial"])
            self.assertEqual({self.container_serial}, container_serials, container_serials)
        finally:
            db.session.execute(delete(TokenContainerToken)
                               .where(TokenContainerToken.token_id == token_id)
                               .where(TokenContainerToken.container_id == second_container_id))
            db.session.commit()

    @ldap3mock.activate
    def test_07a_an_owner_row_without_a_resolver_is_marked(self):
        ldap3mock.setLDAPDirectory(LDAP_DIRECTORY)
        owner = db.session.scalars(
            select(TokenOwner).join(Token, Token.id == TokenOwner.token_id).where(Token.serial == "LIST00")
        ).unique().one()
        original_resolver = owner.resolver

        # An assignment that names no resolver leaves the login name unknowable, so that token is
        # marked while the rest of the page renders. Such a token is not reachable through the
        # paginated list, whose node filter matches the owner against the configured resolvers, so
        # this goes through the conversion the container endpoints use.
        owner.resolver = ""
        db.session.commit()
        try:
            tokens = get_tokens(serial_wildcard=self.serial_wildcard, all_nodes=True)
            token_dicts = convert_token_objects_to_dicts(tokens, user=None, user_role="admin")
            usernames = {token["serial"]: token["username"] for token in token_dicts}
            self.assertEqual("**resolver error**", usernames["LIST00"], usernames)
            self.assertEqual("user01", usernames["LIST01"], usernames)
        finally:
            owner.resolver = original_resolver
            db.session.commit()

    @ldap3mock.activate
    def test_08_tokens_sharing_an_owner_are_looked_up_once(self):
        ldap3mock.setLDAPDirectory(LDAP_DIRECTORY)
        init_token({"type": "hotp", "genkey": 1, "serial": "LISTSHARED"},
                   user=User(login="user00", realm="ldaprealm"))

        requested_user_ids = []
        original_batch = LDAPResolver.get_usernames_batch

        def recording_batch(self, user_ids):
            requested_user_ids.extend(user_ids)
            return original_batch(self, user_ids)

        try:
            # A resolver without a batch lookup of its own pays for every repeated ID, so the page
            # must not hand the same owner in twice
            with mock.patch.object(LDAPResolver, "get_usernames_batch", recording_batch):
                result = get_tokens_paginate(serial=self.serial_wildcard, psize=NUM_TOKENS + 1, page=1)

            self.assertEqual(NUM_TOKENS + 1, len(result["tokens"]), result)
            self.assertEqual(NUM_TOKENS, len(requested_user_ids), requested_user_ids)
            self.assertEqual(1, requested_user_ids.count("0"), requested_user_ids)
            usernames = {token["serial"]: token["username"] for token in result["tokens"]}
            self.assertEqual("user00", usernames["LISTSHARED"], usernames)
            self.assertEqual("user00", usernames["LIST00"], usernames)
        finally:
            remove_token("LISTSHARED")
