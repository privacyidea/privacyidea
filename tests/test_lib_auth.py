"""
This tests the files
  lib/auth.py and
"""
from sqlalchemy import select

from privacyidea.models import Admin, db
from .base import MyTestCase
from privacyidea.lib.auth import (create_db_admin, verify_db_admin,
                                  list_db_admin, delete_db_admin,
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
        list_db_admin()

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
