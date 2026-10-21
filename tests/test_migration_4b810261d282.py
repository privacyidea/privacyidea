"""
Data transformation test for migration 4b810261d282
v3.14.1: Restart the id sequences of internaluserattribute and tokeninfo after their highest id

The data migrations 7d4e9b2c1a3f and a1e0ba6ad9dc insert rows without an id, so the database takes the id from the
column default. privacyIDEA takes the id of a new row from the sequence of the table.

upgrade()   — restarts internaluserattribute_seq and tokeninfo_seq at the id after the highest one of their table,
              on databases with sequences
downgrade() — leaves the sequences where they are

After the upgrade, new internal user attributes and token info rows can be added through the models next to the rows
the data migrations inserted.
"""

import os

import pytest

from tests.migration_test_utils import MigrationTestBase

pytestmark = [
    pytest.mark.migration,
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL environment variable is not set",
    ),
]

# The revisions right before the data migrations that insert rows without an id
BEFORE_INTERNAL_USER_ATTRIBUTE_MIGRATION = "3cafe2771cdd"
BEFORE_U2F_DEPRECATION_MIGRATION = "b1a2c3d4e5f6"


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
        The marker rows that a1e0ba6ad9dc adds to tokeninfo for u2f tokens leave room for new token info rows added
        through the model.
        """
        engine = self._engine()
        self._load_seed_and_upgrade_to(engine, BEFORE_U2F_DEPRECATION_MIGRATION)
        token_ids = [9001, 9002, 9003]
        self._insert_rows(engine, "token", [
            {"id": token_id, "serial": f"U2F{token_id}", "tokentype": "u2f", "active": True}
            for token_id in token_ids
        ])
        token_info_count = self._fetch_scalar(engine, "SELECT COUNT(*) FROM tokeninfo")
        engine.dispose()

        self._upgrade()

        from privacyidea.models import TokenInfo, db
        new_keys = ["note", "label", "owner_hint", "location"]
        for token_id in token_ids:
            for key in new_keys:
                db.session.add(TokenInfo(token_id=token_id, Key=key, Value="value"))
                db.session.commit()

        engine = self._engine()
        markers_per_token = 3
        expected = token_info_count + len(token_ids) * (markers_per_token + len(new_keys))
        assert self._fetch_scalar(engine, "SELECT COUNT(*) FROM tokeninfo") == expected
        engine.dispose()
