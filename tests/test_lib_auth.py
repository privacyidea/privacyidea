"""
This tests the files
  lib/auth.py and
"""
from sqlalchemy import select

from privacyidea.models import Admin, db
from .base import MyTestCase
from privacyidea.lib.auth import (canonical_db_admin_login, create_db_admin, verify_db_admin,
                                  get_all_db_admins, delete_db_admin,
                                  check_webui_user, db_admin_exists)
from privacyidea.lib.user import User


class AuthTestCase(MyTestCase):
    """
    Test the Auth module
    """

    def test_01_db_admin(self):

        create_db_admin("mytestadmin", email="admin@localhost",
                        password="PSTwort")
        r = verify_db_admin("mytestadmin", "PSTwort")
        self.assertTrue(r)
        admin = db.session.scalars(select(Admin).filter_by(username="mytestadmin")).first()
        self.assertEqual("admin@localhost", admin.email)
        self.assertNotEqual("PSTwort", admin.password)  # password is stored encrypted

        self.assertTrue(db_admin_exists("mytestadmin"))
        self.assertFalse(db_admin_exists("noKnownUser"))

        # Change password
        create_db_admin("mytestadmin", password="supersecret")
        r = verify_db_admin("mytestadmin", "supersecret")
        self.assertTrue(r)
        admin = db.session.scalars(select(Admin).filter_by(username="mytestadmin")).first()
        self.assertEqual("admin@localhost", admin.email)    # Email unchanged

        # Change email only
        create_db_admin("mytestadmin", email="newadmin@localhost")
        r = verify_db_admin("mytestadmin", "supersecret")
        self.assertTrue(r)
        admin = db.session.scalars(select(Admin).filter_by(username="mytestadmin")).first()
        self.assertEqual("newadmin@localhost", admin.email)  # Email changed

        # This only prints to stdout!
        get_all_db_admins()

        # Delete the admin
        delete_db_admin("mytestadmin")

    def test_02_users(self):
        r, role, detail = check_webui_user(User("cornelius"), "test")
        self.assertFalse(r)
        self.assertEqual(role, "user")

    def test_03_empty_passsword(self):
        create_db_admin("mytestadmin", email="admin@localhost",
                        password="PSTwort")
        r = verify_db_admin("mytestadmin", None)
        self.assertFalse(r)

        # Delete the admin
        delete_db_admin("mytestadmin")

    def test_04_canonical_db_admin_login(self):
        # The name the admin table stores is what a local admin's authentication-log rows and their
        # conditional-access lock are keyed by, so a login that matched an account is recorded as that account
        # spells it - otherwise, wherever the lookup is case-insensitive, each spelling would count its own
        # failures and a lock would be walked around by varying the case.
        create_db_admin("CanonAdmin", password="secret")
        try:
            self.assertEqual("CanonAdmin", canonical_db_admin_login("CanonAdmin"))
            # A name matching no account is returned untouched: there is no better spelling to be had, and the
            # row still has to be recorded under the name that was tried.
            self.assertEqual("no-such-admin", canonical_db_admin_login("no-such-admin"))
            self.assertIsNone(canonical_db_admin_login(None))
        finally:
            delete_db_admin("CanonAdmin")
