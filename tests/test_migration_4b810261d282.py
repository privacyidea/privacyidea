"""
Data transformation test for migration 4b810261d282
v3.14.1: Restart the id sequences of internaluserattribute and tokeninfo after their highest id

A data migration that inserts rows without an id leaves the id to the column default, for example 7d4e9b2c1a3f on
MariaDB. privacyIDEA takes the id of a new row from the sequence of the table, so that sequence can stay behind the
inserted rows.

upgrade()   — restarts internaluserattribute_seq and tokeninfo_seq at the id after the highest one of their table,
              on databases with sequences
downgrade() — leaves the sequences where they are

After the upgrade, new internal user attributes and token info rows can be added through the models next to the rows
that took their id from the column default.
"""

import os

import pytest
from sqlalchemy import text

from privacyidea.models.db import build_restart_sequence_sql
from tests.migration_test_utils import MigrationTestBase, is_mariadb, is_oracle, is_postgres

pytestmark = [
    pytest.mark.migration,
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL environment variable is not set",
    ),
]

# The revision right before the data migration that inserts internal user attributes without an id
BEFORE_INTERNAL_USER_ATTRIBUTE_MIGRATION = "3cafe2771cdd"


class TestMigration4b810261d282(MigrationTestBase):
    REVISION = "4b810261d282"
    PARENT_REVISION = "9e8487714b46"

    def test_upgrade_lets_the_model_add_internal_user_attributes(self, flask_app):
        """
        The fido2_user_id rows that 7d4e9b2c1a3f moves into internaluserattribute leave room for new internal user
        attributes added through the model.
        """
        engine = self._engine()
        self._load_seed_and_upgrade_to(engine, BEFORE_INTERNAL_USER_ATTRIBUTE_MIGRATION)
        self._insert_rows(engine, "customuserattribute", [
            {"user_id": f"moved{number}", "resolver": "resolver1", "realm_id": None, "Key": "fido2_user_id",
             "Value": f"moved-user-id-{number}", "Type": None}
            for number in range(3)
        ])
        engine.dispose()

        self._upgrade()

        from privacyidea.models import InternalUserAttribute, db
        for number in range(4):
            db.session.add(InternalUserAttribute(user_id=f"new{number}", resolver="resolver1", realm_id=None,
                                                 Key="fido2_user_id", Value=f"new-user-id-{number}"))
            db.session.commit()

        engine = self._engine()
        assert self._fetch_scalar(engine, "SELECT COUNT(*) FROM internaluserattribute") == 7
        engine.dispose()

    def test_upgrade_lets_the_model_add_token_info(self, flask_app):
        """
        Token info rows that took the next ids of tokeninfo_seq from the column default, while the sequence stayed
        behind them, leave room for new token info rows added through the model.
        """
        if not (is_postgres() or is_oracle() or is_mariadb()):
            pytest.skip("MySQL has no sequences, so every token info takes its id from AUTO_INCREMENT")
        engine = self._engine()
        self._load_seed_and_upgrade_to_parent(engine)
        token_id = 9001
        self._insert_rows(engine, "token", [
            {"id": token_id, "serial": f"U2F{token_id}", "tokentype": "deprecated", "active": False},
        ])
        # The sequence is in step with the table, then the marker rows of a deprecated u2f token take its next ids
        next_id = self._fetch_scalar(engine, "SELECT COALESCE(MAX(id), 0) FROM tokeninfo") + 1
        with engine.connect() as conn:
            conn.execute(text(build_restart_sequence_sql("tokeninfo_seq", next_id, engine.dialect.name)))
            conn.commit()
        markers = {"original_tokentype": "u2f", "original_active": "1", "deprecated_in": "3.14"}
        self._insert_rows(engine, "tokeninfo", [
            {"id": next_id + offset, "token_id": token_id, "Key": key, "Value": value, "Type": "", "Description": ""}
            for offset, (key, value) in enumerate(markers.items())
        ])
        token_info_count = self._fetch_scalar(engine, "SELECT COUNT(*) FROM tokeninfo")
        engine.dispose()

        self._upgrade()

        from privacyidea.models import TokenInfo, db
        new_keys = ["note", "label", "owner_hint", "location"]
        for key in new_keys:
            db.session.add(TokenInfo(token_id=token_id, Key=key, Value="value"))
            db.session.commit()

        engine = self._engine()
        assert self._fetch_scalar(engine, "SELECT COUNT(*) FROM tokeninfo") == token_info_count + len(new_keys)
        engine.dispose()
