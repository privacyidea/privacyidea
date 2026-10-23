"""
Database-independent checks of how privacyIDEA adapts SQLAlchemy to Oracle.

They need no Oracle server: they call the conversion functions directly and compile against the Oracle dialect, so
they run in the regular unit-test run, which has no Oracle database.
"""
from collections.abc import Callable

import sqlalchemy as sa
from sqlalchemy.dialects import mysql, oracle, postgresql, sqlite
from sqlalchemy.schema import CreateTable

from privacyidea.lib.utils import text_column_equals
from privacyidea.models.db import deserialize_json_from_oracle, serialize_json_for_oracle
from privacyidea.models.utils import ORACLE_EMPTY_STRING, keep_empty_string_on_oracle

_probe = sa.Table("empty_string_probe", sa.MetaData(),
                  sa.Column("name", keep_empty_string_on_oracle(sa.Unicode(20))),
                  sa.Column("document", keep_empty_string_on_oracle(sa.Text())))


def _processors(column: sa.Column, dialect: sa.engine.Dialect) -> tuple[Callable | None, Callable | None]:
    column_type = column.type.dialect_impl(dialect)
    return column_type.bind_processor(dialect), column_type.result_processor(dialect, None)


def test_json_is_written_with_non_ascii_characters_as_they_are():
    assert '{"name": "jörg"}' == serialize_json_for_oracle({"name": "jörg"})


def test_json_text_is_parsed_and_a_decoded_value_is_returned_as_it_is():
    assert {"a": 1} == deserialize_json_from_oracle('{"a": 1}')
    assert {"a": 1} == deserialize_json_from_oracle(b'{"a": 1}')
    # python-oracledb decodes a column with an "IS JSON" check constraint itself
    decoded = {"a": 1}
    assert decoded is deserialize_json_from_oracle(decoded)


def test_the_oracle_dialect_uses_the_json_functions():
    dialect = oracle.dialect()
    assert serialize_json_for_oracle is dialect._json_serializer
    assert deserialize_json_from_oracle is dialect._json_deserializer


def test_oracle_stores_an_empty_string_as_the_placeholder():
    for column in _probe.columns:
        bind, result = _processors(column, oracle.dialect())
        assert ORACLE_EMPTY_STRING == bind("")
        assert "abc" == bind("abc")
        assert bind(None) is None
        assert "" == result(ORACLE_EMPTY_STRING)
        assert "abc" == result("abc")
        assert result(None) is None


def test_other_databases_store_the_empty_string_unchanged():
    for dialect in (postgresql.dialect(), mysql.dialect(), sqlite.dialect()):
        for column in _probe.columns:
            bind, _result = _processors(column, dialect)
            assert "" == (bind("") if bind else "")


def test_the_column_type_keeps_the_ddl_of_the_wrapped_type():
    unwrapped = sa.Table("empty_string_probe", sa.MetaData(),
                         sa.Column("name", sa.Unicode(20)),
                         sa.Column("document", sa.Text()))
    for dialect in (oracle.dialect(), postgresql.dialect(), mysql.dialect(), sqlite.dialect()):
        assert str(CreateTable(unwrapped).compile(dialect=dialect)) == str(CreateTable(_probe).compile(dialect=dialect))


def test_text_column_equals_matches_the_value_literally():
    compiled = text_column_equals(sa.column("Value", sa.UnicodeText()), "a_b%c/d").compile(dialect=oracle.dialect())
    assert "LIKE" in str(compiled)
    assert "ESCAPE '/'" in str(compiled)
    assert ["a/_b/%c//d"] == list(compiled.params.values())
