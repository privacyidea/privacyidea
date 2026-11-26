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


def test_text_column_equals_uses_like_on_oracle_only():
    table = sa.table("tokeninfo", sa.column("Key", sa.Unicode()), sa.column("Value", sa.UnicodeText()))
    statement = sa.select(table.c.Key).where(table.c.Key == "key", text_column_equals(table.c.Value, "a_b%c/d"))
    oracle_sql = str(statement.compile(dialect=oracle.dialect()))
    assert "LIKE :param_1 ESCAPE '/'" in oracle_sql
    # Oracle has no boolean type, and the condition must not get an appended "= 1"
    assert "= 1" not in oracle_sql
    for dialect in (postgresql.dialect(), mysql.dialect(), sqlite.dialect()):
        sql = str(statement.compile(dialect=dialect))
        assert "LIKE" not in sql
        assert sql.count(" = ") == 2


def test_text_column_equals_adds_the_table_of_the_column_to_the_from_list():
    token = sa.table("token", sa.column("id", sa.Integer()))
    tokeninfo = sa.table("tokeninfo", sa.column("Value", sa.UnicodeText()))
    # No other part of the statement names the table tokeninfo
    statement = sa.select(token.c.id).where(text_column_equals(tokeninfo.c.Value, "x"))
    for dialect in (oracle.dialect(), postgresql.dialect(), mysql.dialect(), sqlite.dialect()):
        assert "FROM token, tokeninfo " in " ".join(str(statement.compile(dialect=dialect)).split())


def test_text_column_equals_gets_parentheses_inside_a_comparison():
    table = sa.table("tokeninfo", sa.column("Value", sa.UnicodeText()))
    condition = text_column_equals(table.c.Value, "x")
    for dialect in (oracle.dialect(), postgresql.dialect(), mysql.dialect(), sqlite.dialect()):
        condition_sql = str(condition.compile(dialect=dialect))
        where_sql = str(sa.select(table.c.Value).where(condition).compile(dialect=dialect))
        assert where_sql.endswith(f"WHERE {condition_sql}")
        compared_sql = str(sa.select(table.c.Value).where(condition == sa.false()).compile(dialect=dialect))
        assert f"WHERE ({condition_sql}) = " in compared_sql


def test_text_column_equals_escapes_the_value_on_oracle_only():
    condition = text_column_equals(sa.column("Value", sa.UnicodeText()), "a_b%c/d")
    for dialect, expected in ((oracle.dialect(), "a/_b/%c//d"),
                              (postgresql.dialect(), "a_b%c/d"),
                              (mysql.dialect(), "a_b%c/d"),
                              (sqlite.dialect(), "a_b%c/d")):
        # The compiler lists the one bind parameter under its internal and under its rendered name
        (bind,) = set(condition.compile(dialect=dialect).binds.values())
        process = bind.type.dialect_impl(dialect).bind_processor(dialect)
        assert expected == process(bind.value)


def test_text_column_equals_matches_exactly_and_with_case_on_sqlite():
    # The statement is built again for every value, so this also checks that a cached statement gets the new value
    engine = sa.create_engine("sqlite://")
    table = sa.Table("text_probe", sa.MetaData(), sa.Column("value", sa.UnicodeText()))
    table.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(table.insert(), [{"value": "ABC"}, {"value": "a_c"}])

        def matches(value: str) -> list[str]:
            statement = sa.select(table.c.value).where(text_column_equals(table.c.value, value))
            return connection.execute(statement).scalars().all()

        assert ["ABC"] == matches("ABC")
        assert [] == matches("abc")
        assert ["a_c"] == matches("a_c")
        assert [] == matches("a%")
        # The condition is the only part of the statement that names the table
        count = sa.select(sa.func.count()).where(text_column_equals(table.c.value, "ABC"))
        assert 1 == connection.execute(count).scalar()
