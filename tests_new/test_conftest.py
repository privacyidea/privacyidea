# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
The base fixtures isolate the tests from each other.

Each pair has one test that leaves something behind and one that expects nothing. Both pass in any order only if the
fixtures reset that state.
"""
import socket

import pytest
from flask import current_app, g, has_app_context
from pytest_socket import SocketConnectBlockedError
from sqlalchemy import func, select

from privacyidea.lib import health
from privacyidea.lib.resolvers import LDAPIdResolver
from privacyidea.lib.token import get_tokens, init_token
from privacyidea.models import Config, db

TIMESTAMP_KEY = "__timestamp__"


def _row_counts() -> dict[str, int]:
    return {table.name: db.session.execute(select(func.count()).select_from(table)).scalar_one()
            for table in db.metadata.sorted_tables}


def test_token_written_by_a_test_is_in_the_database(clean_db):
    init_token({"type": "spass", "serial": "LEFT-BEHIND"})

    assert [token.token.serial for token in get_tokens()] == ["LEFT-BEHIND"]


def test_clean_db_starts_with_empty_tables_except_the_config_timestamp(clean_db):
    counts = _row_counts()

    assert {name: count for name, count in counts.items() if count} == {"config": 1}
    assert db.session.execute(select(Config.Key)).scalars().all() == [TIMESTAMP_KEY]


def test_ids_start_at_one(clean_db):
    token = init_token({"type": "spass", "serial": "FIRST"})

    assert token.token.id == 1


def test_value_set_on_g_by_a_test(app_context):
    g.left_behind = True

    assert g.left_behind


def test_app_context_starts_with_empty_g(app_context):
    assert list(iter(g)) == []


def test_value_put_into_the_app_local_store_by_a_test(app_context):
    current_app.config.setdefault("_app_local_store", {})["left_behind"] = True

    assert current_app.config["_app_local_store"]["left_behind"]


def test_app_context_starts_with_empty_app_local_store(app_context):
    assert current_app.config.get("_app_local_store", {}) == {}


def test_pure_logic_needs_no_app_context():
    assert not has_app_context()


def test_entry_put_into_the_ldap_cache_by_a_test(app_context):
    LDAPIdResolver.CACHE["left-behind"] = {}

    assert "left-behind" in LDAPIdResolver.CACHE


def test_app_context_starts_with_empty_ldap_cache(app_context):
    assert LDAPIdResolver.CACHE == {}


def test_entry_put_into_the_health_cache_by_a_test(app_context):
    health._CACHE["left-behind"] = (0, None)

    assert "left-behind" in health._CACHE


def test_app_context_starts_with_empty_health_cache(app_context):
    assert health._CACHE == {}


# TEST-NET-1 (RFC 5737): never routed, so a connection attempt cannot reach anything
OTHER_HOST = ("192.0.2.1", 389)


def test_connection_to_another_host_is_blocked():
    with socket.socket() as client, pytest.raises(SocketConnectBlockedError):
        client.connect(OTHER_HOST)


def test_connection_to_localhost_is_allowed():
    with socket.socket() as server, socket.socket() as client:
        server.bind(("127.0.0.1", 0))
        server.listen()

        client.connect(server.getsockname())

        assert client.getpeername() == server.getsockname()


@pytest.mark.integration
def test_integration_test_may_connect_to_another_host():
    with socket.socket() as client:
        client.settimeout(0.01)
        # The connection itself fails, but it is attempted instead of blocked
        with pytest.raises(OSError):
            client.connect(OTHER_HOST)
