"""
Tests for the database migration script c3d4e5f6a7b8 that clears the
challenge table to remove legacy (non-dict) challenge data.
"""
from sqlalchemy import select, text

from privacyidea.lib.crypto import encryptPassword
from privacyidea.models import Challenge, db
from .base import MyTestCase


class MigrationClearChallengesTestCase(MyTestCase):
    """
    Test the migration logic for clearing the challenge table.
    """

    def test_01_migration_deletes_all_challenges(self):
        """The migration deletes every row from the challenge table."""
        # Insert a few challenges with different data formats
        c1 = Challenge(serial="MIG_CLR01", transaction_id="clr_tid001",
                       data={"otp": "123456"}, validitytime=300)
        c2 = Challenge(serial="MIG_CLR02", transaction_id="clr_tid002",
                       data={"positions": "2,5,3"}, validitytime=300)
        c3 = Challenge(serial="MIG_CLR03", transaction_id="clr_tid003",
                       validitytime=120)
        c1.save()
        c2.save()
        c3.save()

        # Verify rows exist
        count = db.session.execute(
            text("SELECT COUNT(*) FROM challenge")
        ).scalar()
        self.assertGreaterEqual(count, 3)

        # Simulate the migration
        db.session.execute(text("DELETE FROM challenge"))
        db.session.commit()

        # Verify table is empty
        count = db.session.execute(
            text("SELECT COUNT(*) FROM challenge")
        ).scalar()
        self.assertEqual(count, 0)

    def test_02_migration_handles_empty_table(self):
        """The migration is safe on an already-empty challenge table."""
        # Ensure table is empty
        db.session.execute(text("DELETE FROM challenge"))
        db.session.commit()

        # Running the migration DELETE on an empty table should not raise
        db.session.execute(text("DELETE FROM challenge"))
        db.session.commit()

        count = db.session.execute(
            text("SELECT COUNT(*) FROM challenge")
        ).scalar()
        self.assertEqual(count, 0)
