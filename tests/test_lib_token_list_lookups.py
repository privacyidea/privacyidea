# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Assert how many user store and database lookups one page of the token list costs.

The counts are what keeps the token list from resolving its owners and containers one token at a
time. A timing assertion would say the same thing far less reliably, so this counts round trips.
"""
import re
from contextlib import contextmanager
from itertools import product

import mock
import responses
from sqlalchemy import delete, event, select
from sqlalchemy.engine import Engine

from privacyidea.lib.container import add_token_to_container, find_container_by_serial, init_container
from privacyidea.lib.realm import delete_realm, set_realm
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.resolvers.HTTPResolver import HTTPResolver
from privacyidea.lib.resolvers.LDAPIdResolver import IdResolver as LDAPResolver
from privacyidea.lib.token import (convert_token_objects_to_dicts, get_orphaned_serials, get_tokens,
                                   get_tokens_paginate, init_token, remove_token)
from privacyidea.lib.token import query as token_query
from privacyidea.lib.token.tokengroups import set_tokengroups
from privacyidea.lib.tokengroup import delete_tokengroup, set_tokengroup
from privacyidea.lib.user import User
from privacyidea.models import db, NodeName, Realm, Token, TokenContainerToken, TokenOwner
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

HTTP_PARAMS = {"resolver": "orphanhttp",
               "type": "httpresolver",
               "endpoint": "http://localhost:8080/get-data",
               "method": "GET",
               "requestMapping": """{"id": "{userid}"}""",
               "responseMapping": """{"username": "{data.the_username}"}""",
               "hasSpecialErrorHandler": False}


@contextmanager
def count_ldap_searches():
    """Collect the search filters the LDAP resolver sends while the block runs."""
    search_filters = []
    original_search = LDAPResolver._search

    def counting_search(self, search_base, search_filter, attributes, **kwargs):
        search_filters.append(search_filter)
        return original_search(self, search_base, search_filter, attributes, **kwargs)

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
        self.assertSetEqual({self.container_serial}, set(token["container_serial"] for token in result["tokens"]), result)

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
            self.assertSetEqual({self.container_serial}, container_serials, container_serials)
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
        # marked while the rest of the page renders. This goes through the conversion the container
        # endpoints use.
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
    def test_07b_a_token_whose_owner_has_no_resolver_is_listed(self):
        ldap3mock.setLDAPDirectory(LDAP_DIRECTORY)
        owner_without_resolver, owner_of_deleted_resolver = db.session.scalars(
            select(TokenOwner).join(Token, Token.id == TokenOwner.token_id)
            .where(Token.serial.in_(["LIST00", "LIST01"])).order_by(Token.serial)
        ).unique().all()
        original_resolver = owner_without_resolver.resolver
        other_node = "11111111-2222-3333-4444-555555555555"

        # These tokens belong to no node: they are listed with and without node-specific resolvers, also if only
        # another node serves the realm of their owner
        owner_without_resolver.resolver = None
        owner_of_deleted_resolver.resolver = "deletedreso"
        db.session.add(NodeName(id=other_node, name="OtherNode"))
        db.session.commit()
        try:
            result = get_tokens_paginate(serial=self.serial_wildcard, psize=NUM_TOKENS, page=1)
            self.assertEqual(NUM_TOKENS, result["count"], result)
            usernames = {token["serial"]: token["username"] for token in result["tokens"]}
            self.assertEqual("**resolver error**", usernames["LIST00"], usernames)
            self.assertEqual("**resolver error**", usernames["LIST01"], usernames)

            set_realm("noderealm", [{"name": "ldapreso", "node": other_node}])
            try:
                result = get_tokens_paginate(serial=self.serial_wildcard, psize=NUM_TOKENS, page=1)
                self.assertEqual(NUM_TOKENS, result["count"], result)
                self.assertEqual(1, len(get_tokens(serial="LIST00")))
            finally:
                delete_realm("noderealm")

            # Only the other node serves the realm of the owners: the tokens of the owners it serves are left out
            set_realm("ldaprealm", [{"name": "ldapreso", "node": other_node}])
            try:
                result = get_tokens_paginate(serial=self.serial_wildcard, psize=NUM_TOKENS, page=1)
                self.assertSetEqual({"LIST00", "LIST01"}, {token["serial"] for token in result["tokens"]}, result)
                self.assertEqual(1, len(get_tokens(serial="LIST00")))
                self.assertEqual(1, len(get_tokens(serial="LIST01")))
                self.assertEqual([], get_tokens(serial="LIST02"))
                self.assertEqual(1, len(get_tokens(serial="LIST02", all_nodes=True)))

                # The resolver of the other owners also serves this node, in another realm: the realm of the
                # owners still leaves their tokens out
                set_realm("localrealm", [{"name": "ldapreso"}])
                try:
                    result = get_tokens_paginate(serial=self.serial_wildcard, psize=NUM_TOKENS, page=1)
                    self.assertSetEqual({"LIST00", "LIST01"}, {token["serial"] for token in result["tokens"]},
                                        result)
                finally:
                    delete_realm("localrealm")
            finally:
                set_realm("ldaprealm", [{"name": "ldapreso"}])
        finally:
            db.session.execute(delete(NodeName).where(NodeName.id == other_node))
            owner_without_resolver.resolver = original_resolver
            owner_of_deleted_resolver.resolver = original_resolver
            db.session.commit()

    @ldap3mock.activate
    def test_07c_the_owner_of_a_listed_token_is_read_again_afterwards(self):
        ldap3mock.setLDAPDirectory(LDAP_DIRECTORY)
        tokens = get_tokens(serial="LIST00")
        token_dicts = convert_token_objects_to_dicts(tokens, user=None, user_role="admin")
        self.assertEqual("user00", token_dicts[0]["username"], token_dicts)

        # The owner is removed in the same transaction, after the list was built: the token does not report the
        # owner the list read
        db_token = tokens[0].token
        db.session.execute(delete(TokenOwner).where(TokenOwner.token_id == db_token.id))
        try:
            self.assertIsNone(db_token.first_owner)
        finally:
            db.session.rollback()
        self.assertEqual("user00", get_tokens(serial="LIST00")[0].user.login)

    @ldap3mock.activate
    def test_07d_the_node_filter_keeps_tokens_without_owner_realm_or_realm_resolver(self):
        ldap3mock.setLDAPDirectory(LDAP_DIRECTORY)
        owner_without_realm, owner_in_a_realm_without_resolver = db.session.scalars(
            select(TokenOwner).join(Token, Token.id == TokenOwner.token_id)
            .where(Token.serial.in_(["LIST02", "LIST03"])).order_by(Token.serial)
        ).unique().all()
        original_realm_id = owner_without_realm.realm_id
        other_node = "11111111-2222-3333-4444-555555555555"
        init_token({"type": "hotp", "genkey": 1, "serial": "LISTUNASSIGNED"})
        set_realm("realmwithoutresolver", [])
        db.session.add(NodeName(id=other_node, name="OtherNode"))
        db.session.commit()
        set_realm("noderealm", [{"name": "ldapreso", "node": other_node}])
        try:
            # With a node-specific resolver in the configuration, the token without an owner, the owner without a
            # realm and the owner in a realm without a resolver are all listed
            owner_without_realm.realm_id = None
            owner_in_a_realm_without_resolver.realm_id = db.session.scalar(
                select(Realm.id).where(Realm.name == "realmwithoutresolver"))
            db.session.commit()
            result = get_tokens_paginate(serial=self.serial_wildcard, psize=NUM_TOKENS + 1, page=1)
            self.assertEqual(NUM_TOKENS + 1, result["count"], result)
            self.assertIn("LISTUNASSIGNED", [token["serial"] for token in result["tokens"]])
        finally:
            owner_without_realm.realm_id = original_realm_id
            owner_in_a_realm_without_resolver.realm_id = original_realm_id
            db.session.commit()
            delete_realm("noderealm")
            delete_realm("realmwithoutresolver")
            remove_token("LISTUNASSIGNED")
            db.session.execute(delete(NodeName).where(NodeName.id == other_node))
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

    @ldap3mock.activate
    def test_09_a_failing_owner_batch_query_falls_back_per_token(self):
        ldap3mock.setLDAPDirectory(LDAP_DIRECTORY)
        original_scalars = db.session.scalars
        batch_query_failed = False

        def failing_batch_query(stmt, *args, **kwargs):
            nonlocal batch_query_failed
            # The very first query selecting TokenOwner is the page-wide batch lookup (any
            # per-token fallback queries only run afterwards, once it has already failed), so
            # this fails only that one call and leaves everything else -- including the token
            # listing query itself, which also selects rows involving TokenOwner -- untouched.
            entities = [d["entity"] for d in getattr(stmt, "column_descriptions", [])]
            if not batch_query_failed and entities == [TokenOwner]:
                batch_query_failed = True
                raise Exception("the owner query for the whole page failed")
            return original_scalars(stmt, *args, **kwargs)

        # The page-wide owner query fails once (transient DB error); the fallback looks each
        # token's owner up individually, so the page still renders instead of failing outright.
        with mock.patch.object(db.session, "scalars", side_effect=failing_batch_query):
            result = get_tokens_paginate(serial=self.serial_wildcard, psize=NUM_TOKENS, page=1)

        self.assertTrue(batch_query_failed)
        self.assertEqual(NUM_TOKENS, len(result["tokens"]), result)
        usernames = {token["serial"]: token["username"] for token in result["tokens"]}
        self.assertEqual(NUM_TOKENS, len(set(usernames.values())), usernames)
        self.assertEqual("user00", usernames["LIST00"], usernames)

    @ldap3mock.activate
    def test_10_a_failing_container_batch_query_is_retried(self):
        ldap3mock.setLDAPDirectory(LDAP_DIRECTORY)
        original_execute = db.session.execute
        batch_query_failed = False

        def failing_batch_query(stmt, *args, **kwargs):
            nonlocal batch_query_failed
            # The page-wide container query is the one selecting the token ID next to the
            # container serial, so this leaves every other statement of the page untouched.
            columns = [d["name"] for d in getattr(stmt, "column_descriptions", [])]
            if not batch_query_failed and columns == ["token_id", "serial"]:
                batch_query_failed = True
                raise Exception("the container query for the whole page failed")
            return original_execute(stmt, *args, **kwargs)

        # The page-wide container query fails once (transient DB error); it is retried, so the
        # page still renders its containers instead of failing outright.
        with mock.patch.object(db.session, "execute", side_effect=failing_batch_query):
            result = get_tokens_paginate(serial=self.serial_wildcard, psize=NUM_TOKENS, page=1)

        self.assertTrue(batch_query_failed)
        self.assertEqual(NUM_TOKENS, len(result["tokens"]), result)
        container_serials = {token["container_serial"] for token in result["tokens"]}
        self.assertSetEqual({self.container_serial}, container_serials, container_serials)

    @ldap3mock.activate
    def test_11_a_failing_container_query_is_read_token_by_token(self):
        ldap3mock.setLDAPDirectory(LDAP_DIRECTORY)
        original_execute = db.session.execute
        container_queries = []

        def failing_page_query(stmt, *args, **kwargs):
            # The page-wide container query and its retry both fail, so the containers are read
            # one token at a time; every other statement of the page is left untouched.
            columns = [d["name"] for d in getattr(stmt, "column_descriptions", [])]
            if columns == ["token_id", "serial"]:
                container_queries.append(stmt)
                if len(container_queries) <= 2:
                    raise Exception("the container query for the whole page failed")
            return original_execute(stmt, *args, **kwargs)

        with mock.patch.object(db.session, "execute", side_effect=failing_page_query):
            result = get_tokens_paginate(serial=self.serial_wildcard, psize=NUM_TOKENS, page=1)

        # The page-wide query, its retry, and then one query per token
        self.assertEqual(2 + NUM_TOKENS, len(container_queries))
        self.assertEqual(NUM_TOKENS, len(result["tokens"]), result)
        container_serials = {token["container_serial"] for token in result["tokens"]}
        self.assertSetEqual({self.container_serial}, container_serials, container_serials)

    @ldap3mock.activate
    def test_12_token_details_of_a_page_are_read_with_one_query_each(self):
        ldap3mock.setLDAPDirectory(LDAP_DIRECTORY)
        set_tokengroup("listgroup")
        set_tokengroups("LIST03", ["listgroup"])
        try:
            with count_statements() as statements:
                result = get_tokens_paginate(serial=self.serial_wildcard, psize=NUM_TOKENS, page=1)

            # The token info, the token groups and the owners are read once for the page, not per token
            self.assertEqual(1, count_containing(statements, "FROM tokeninfo"), statements)
            self.assertEqual(1, count_containing(statements, "tokentokengroup"), statements)
            self.assertEqual(1, count_containing(statements, "FROM tokenowner"), statements)

            # The page is the same as when every token reads its own details
            with mock.patch("privacyidea.lib.token.query._load_page_details"):
                result_per_token = get_tokens_paginate(serial=self.serial_wildcard, psize=NUM_TOKENS, page=1)
            self.assertEqual(result_per_token["tokens"], result["tokens"])
            tokens = {token["serial"]: token for token in result["tokens"]}
            self.assertEqual(["listgroup"], tokens["LIST03"]["tokengroup"], tokens["LIST03"])
            self.assertEqual("ldapreso", tokens["LIST05"]["resolver"], tokens["LIST05"])
            self.assertEqual("5", tokens["LIST05"]["user_id"], tokens["LIST05"])
            self.assertIn("tokenkind", tokens["LIST05"]["info"], tokens["LIST05"])
        finally:
            set_tokengroups("LIST03", [])
            delete_tokengroup("listgroup")

    @ldap3mock.activate
    def test_13_token_details_that_can_not_be_read_for_the_page_are_read_per_token(self):
        ldap3mock.setLDAPDirectory(LDAP_DIRECTORY)
        expected = get_tokens_paginate(serial=self.serial_wildcard, psize=NUM_TOKENS, page=1)

        with mock.patch("privacyidea.lib.token.query.selectinload",
                        side_effect=Exception("the details of the page can not be read")):
            result = get_tokens_paginate(serial=self.serial_wildcard, psize=NUM_TOKENS, page=1)

        self.assertEqual(expected["tokens"], result["tokens"])

    @ldap3mock.activate
    def test_14_a_token_whose_owners_could_not_be_read_reads_its_owner_itself(self):
        ldap3mock.setLDAPDirectory(LDAP_DIRECTORY)
        token_id = get_tokens(serial="LIST05")[0].token.id
        original_select_owners = token_query._select_owners

        def failing_select_owners(token_ids: list[int]) -> list[TokenOwner]:
            # The page query, its retry and the query of the one token fail
            if len(token_ids) > 1 or token_ids == [token_id]:
                raise Exception("the owners can not be read")
            return original_select_owners(token_ids)

        with mock.patch("privacyidea.lib.token.query._select_owners", side_effect=failing_select_owners):
            result = get_tokens_paginate(serial=self.serial_wildcard, psize=NUM_TOKENS, page=1)

        # The token is not shown without an owner: it still reads its owner, only its login name is unknown
        tokens = {token["serial"]: token for token in result["tokens"]}
        self.assertEqual("ldapreso", tokens["LIST05"]["resolver"], tokens["LIST05"])
        self.assertEqual("5", tokens["LIST05"]["user_id"], tokens["LIST05"])
        self.assertEqual("", tokens["LIST05"]["username"], tokens["LIST05"])
        self.assertEqual("ldapreso", tokens["LIST06"]["resolver"], tokens["LIST06"])
        self.assertEqual("user06", tokens["LIST06"]["username"], tokens["LIST06"])

    @ldap3mock.activate
    def test_15_the_owners_are_only_joined_for_node_specific_resolvers(self):
        ldap3mock.setLDAPDirectory(LDAP_DIRECTORY)

        # Without a resolver that is restricted to a node, every node serves every owner: the list neither
        # joins the owners nor filters by node
        with count_statements() as statements:
            result = get_tokens_paginate(serial=self.serial_wildcard, psize=NUM_TOKENS, page=1)
        count_statement = [statement for statement in statements if "count(" in statement.lower()][0]
        self.assertNotIn("tokenowner", count_statement)
        self.assertEqual(NUM_TOKENS, result["count"], result)

        other_node = "11111111-2222-3333-4444-555555555555"
        db.session.add(NodeName(id=other_node, name="OtherNode"))
        db.session.commit()
        set_realm("noderealm", [{"name": "ldapreso", "node": other_node}])
        try:
            with count_statements() as statements:
                result = get_tokens_paginate(serial=self.serial_wildcard, psize=NUM_TOKENS, page=1)
            count_statement = [statement for statement in statements if "count(" in statement.lower()][0]
            self.assertIn("tokenowner", count_statement)
            self.assertEqual(NUM_TOKENS, result["count"], result)
        finally:
            delete_realm("noderealm")
            db.session.execute(delete(NodeName).where(NodeName.id == other_node))
            db.session.commit()

    @ldap3mock.activate
    def test_16_the_realm_filter_uses_the_realm_ids(self):
        ldap3mock.setLDAPDirectory(LDAP_DIRECTORY)

        for realm_filter in ("ldaprealm", "LDAPrealm", "ldap*", "*realm", "other,ldaprealm"):
            with count_statements() as statements:
                result = get_tokens_paginate(serial=self.serial_wildcard, psize=NUM_TOKENS, page=1,
                                             realm=realm_filter)
            self.assertEqual(NUM_TOKENS, result["count"], realm_filter)
            # The realm names are matched without a query on the realm table
            self.assertEqual(0, count_containing(statements, "FROM realm"), statements)

        self.assertEqual(0, get_tokens_paginate(serial=self.serial_wildcard, realm="ldap")["count"])
        self.assertEqual(NUM_TOKENS, get_tokens_paginate(serial=self.serial_wildcard,
                                                         allowed_realms=["LdapRealm"])["count"])
        self.assertEqual(0, get_tokens_paginate(serial=self.serial_wildcard, allowed_realms=["ldap*"])["count"])
        self.assertEqual(NUM_TOKENS, get_tokens_paginate(serial=self.serial_wildcard,
                                                         realm="*" * 50 + "realm")["count"])
        self.assertEqual(0, get_tokens_paginate(serial=self.serial_wildcard, realm="*" * 50 + "x")["count"])

    @ldap3mock.activate
    def test_17_the_realm_ids_are_compared_in_chunks(self):
        ldap3mock.setLDAPDirectory(LDAP_DIRECTORY)
        set_realm("chunkrealm", [{"name": "ldapreso"}])
        chunked = token_query._chunked
        try:
            with (mock.patch.object(token_query, "_chunked", lambda items: chunked(items, size=1)),
                  count_statements() as statements):
                result = get_tokens_paginate(serial=self.serial_wildcard, psize=NUM_TOKENS, page=1,
                                             realm="ldaprealm,chunkrealm", allowed_realms=["chunkrealm", "ldaprealm"])
            self.assertEqual(NUM_TOKENS, result["count"], result)
            count_statement = [statement for statement in statements if "count(" in statement.lower()][0]
            self.assertEqual(4, count_statement.count("tokenrealm.realm_id IN"), count_statement)
        finally:
            delete_realm("chunkrealm")

    @ldap3mock.activate
    def test_18_a_page_costs_the_same_queries_whatever_its_size(self):
        ldap3mock.setLDAPDirectory(LDAP_DIRECTORY)
        set_tokengroup("listgroup")
        set_tokengroups("LIST01", ["listgroup"])

        def selects_of_a_page(page_size: int) -> list[str]:
            with count_statements() as statements:
                result = get_tokens_paginate(serial=self.serial_wildcard, psize=page_size, page=1)
            self.assertEqual(page_size, len(result["tokens"]), result)
            return [statement for statement in statements if statement.lstrip().upper().startswith("SELECT")]

        try:
            selects_of_a_small_page = selects_of_a_page(2)
            self.assertEqual(len(selects_of_a_small_page), len(selects_of_a_page(NUM_TOKENS)))

            # Reading the owners is rolled back once, which expires the tokens of the page: they are loaded again
            # with the details of the page, not one by one
            original_select_owners = token_query._select_owners
            calls = []

            def select_owners_failing_once(token_ids: list[int]) -> list[TokenOwner]:
                calls.append(token_ids)
                if len(calls) == 1:
                    raise Exception("the owners can not be read")
                return original_select_owners(token_ids)

            with mock.patch("privacyidea.lib.token.query._select_owners", side_effect=select_owners_failing_once):
                self.assertEqual(len(selects_of_a_small_page), len(selects_of_a_page(NUM_TOKENS)))
            self.assertEqual(2, len(calls), calls)
        finally:
            set_tokengroups("LIST01", [])
            delete_tokengroup("listgroup")


class RealmIdsTestCase(MyTestCase):

    def test_01_get_realm_ids(self):
        realms = {"realm1": {"id": 1}, "Realm.Two": {"id": 2}, "realm_3": {"id": 3}, "realmx3": {"id": 4}}

        # Exact names compare case-insensitively
        self.assertEqual([1], token_query._get_realm_ids(realms, ["REALM1"]))
        self.assertEqual([2], token_query._get_realm_ids(realms, ["realm.two"]))
        # "*" matches any characters, "." and "_" only themselves
        self.assertEqual([1, 2, 3, 4], token_query._get_realm_ids(realms, [], ["realm*"]))
        self.assertEqual([2], token_query._get_realm_ids(realms, [], ["*.two"]))
        self.assertEqual([3], token_query._get_realm_ids(realms, [], ["realm_*"]))
        self.assertEqual([1, 3], token_query._get_realm_ids(realms, ["realm1"], ["*_3"]))
        self.assertEqual([], token_query._get_realm_ids(realms, ["realm"], ["x*"]))

    @staticmethod
    def _matches_wildcard(realm_name: str, pattern: str) -> bool:
        return token_query._get_realm_ids({realm_name: {"id": 1}}, [], [pattern]) == [1]

    def test_02_get_realm_ids_by_wildcard(self):
        matching = [("realm1", "realm1"), ("realm1", "*"), ("realm1", "realm*"), ("realm1", "*1"),
                    ("realm1", "*alm*"), ("realm1", "r*a*1"), ("realm1", "r**1"), ("realm1", "***"),
                    ("realm1", "realm1*"), ("realm1", "*realm1"), ("aa", "a*a"), ("aaa", "*a*a*"), ("", "*"),
                    ("realm?", "realm?"), ("realm[1]", "realm[1]"), ("realm[1]", "*[*]"), ("realm]", "*]")]
        for realm_name, pattern in matching:
            self.assertTrue(self._matches_wildcard(realm_name, pattern), (realm_name, pattern))

        # Only "*" is a wildcard, "?" and "[...]" match only themselves
        not_matching = [("realm1", "realm"), ("realm1", "realm1x"), ("realm1", "x*"), ("realm1", "*x"),
                        ("realm1", "*1*1"), ("a", "a*a"), ("realm1", "realm*11*"), ("realm1", "r*z*1"),
                        ("ab", "*b*a*"), ("", "x*"), ("realm1", "realm?"), ("realm1", "realm[0-9]"),
                        ("realm1", "realm[!x]"), ("realm1", "realm[1]")]
        for realm_name, pattern in not_matching:
            self.assertFalse(self._matches_wildcard(realm_name, pattern), (realm_name, pattern))

        # A pattern with many wildcards, in a row or in between other characters, is checked about as fast as a
        # short one
        self.assertFalse(self._matches_wildcard("my-corporate-active-directory-realm", "*" * 1000 + "x"))
        self.assertTrue(self._matches_wildcard("my-corporate-active-directory-realm", "*" * 1000 + "m"))
        self.assertFalse(self._matches_wildcard("a" * 200, "*a" * 100 + "b"))
        self.assertTrue(self._matches_wildcard("a" * 200, "*a" * 100 + "*"))

    def test_03_get_realm_ids_by_wildcard_like_a_regular_expression(self):
        # Every name of up to three characters matches a pattern of up to four characters exactly when the regular
        # expression with ".*" for each "*" and every other character escaped matches
        realm_names = ["".join(characters) for length in range(4) for characters in product("ab?[]", repeat=length)]
        realms = {realm_name: {"id": realm_id} for realm_id, realm_name in enumerate(realm_names)}
        patterns = ["".join(characters) for length in range(5) for characters in product("ab?[]*", repeat=length)]
        for pattern in patterns:
            regular_expression = re.compile(".*".join(re.escape(piece) for piece in pattern.split("*")), re.DOTALL)
            self.assertEqual([realm_id for realm_id, realm_name in enumerate(realm_names)
                              if regular_expression.fullmatch(realm_name)],
                             token_query._get_realm_ids(realms, [], [pattern]), pattern)


class OrphanedTokenTestCase(MyTestCase):
    """
    Check that get_orphaned_serials decides like TokenClass.is_orphaned, while asking each resolver once
    for a whole chunk of tokens instead of once per token.
    """

    serial_wildcard = "ORPH*"

    @classmethod
    @ldap3mock.activate
    def setUpClass(cls):
        super().setUpClass()
        ldap3mock.setLDAPDirectory(LDAP_DIRECTORY)
        save_resolver({**LDAP_PARAMS, "resolver": "orphanldap"})
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

        # Five tokens of the LDAP resolver are resolved with one search, plus one single lookup for the deleted
        # user the search did not find. The deleted resolver and the owner without a resolver are not asked at all.
        self.assertEqual(2, len(search_filters), search_filters)
        self.assertIn("(oid=99)", search_filters[1], search_filters)
        self.assertEqual(1, http_get_username.call_count)
        self.assertNotIn("ORPHUNREACHABLE", orphaned_serials)

    def test_03_no_tokens(self) -> None:
        self.assertSetEqual(set(), get_orphaned_serials([]))

    @ldap3mock.activate
    def test_04_id_the_batch_can_not_search_for(self):
        ldap3mock.setLDAPDirectory(LDAP_DIRECTORY)
        token = init_token({"type": "spass", "serial": "MALFORMEDID"})
        TokenOwner(token_id=token.token.id, user_id="malformed", resolver="orphanldap",
                   realmname="orphanldaprealm").save()
        tokens = get_tokens(serial="MALFORMEDID")
        trim_user_id = LDAPResolver._trim_user_id

        def failing_trim_user_id(resolver: LDAPResolver, user_id: str) -> str:
            # Like an objectGUID that is no UUID: the batch skips it, a single lookup raises
            if user_id == "malformed":
                raise ValueError("badly formed hexadecimal UUID string")
            return trim_user_id(resolver, user_id)

        with mock.patch.object(LDAPResolver, "_trim_user_id", autospec=True, side_effect=failing_trim_user_id):
            for orphaned_on_error in [True, False]:
                expected = {"MALFORMEDID"} if tokens[0].is_orphaned(orphaned_on_error) else set()
                self.assertSetEqual(expected, get_orphaned_serials(tokens, orphaned_on_error), orphaned_on_error)
            self.assertSetEqual(set(), get_orphaned_serials(tokens, orphaned_on_error=False))

    def test_05_http_user_store_error(self) -> None:
        tokens = get_tokens(serial="ORPHUNREACHABLE")
        # Not "no such user": a user store that fails to answer leaves the decision to orphaned_on_error
        with responses.RequestsMock() as mocked_responses:
            mocked_responses.add(responses.GET, "http://localhost:8080/get-data", status=503, body="{}")
            for orphaned_on_error in [True, False]:
                expected = {"ORPHUNREACHABLE"} if tokens[0].is_orphaned(orphaned_on_error) else set()
                self.assertSetEqual(expected, get_orphaned_serials(tokens, orphaned_on_error), orphaned_on_error)
            self.assertSetEqual(set(), get_orphaned_serials(tokens, orphaned_on_error=False))

    def test_06_owners_can_not_be_read(self) -> None:
        tokens = get_tokens(serial="ORPHDELETEDUSER")
        # Not even the owner is known, so like a user store that can not be asked, orphaned_on_error decides
        with mock.patch("privacyidea.lib.token.query._select_owners", side_effect=Exception("lock wait timeout")):
            self.assertSetEqual({"ORPHDELETEDUSER"}, get_orphaned_serials(tokens, orphaned_on_error=True))
            self.assertSetEqual(set(), get_orphaned_serials(tokens, orphaned_on_error=False))
