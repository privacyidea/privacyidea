# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
The base fixtures isolate the tests from each other.

Each pair has one test that leaves something behind and one that expects nothing. Both pass in any order only if the
fixtures reset that state.
"""
from flask import current_app, g, has_app_context
from sqlalchemy import func, select

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
