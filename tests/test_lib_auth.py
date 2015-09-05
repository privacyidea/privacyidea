"""
This tests the files
  lib/auth.py and
"""

from .base import MyTestCase
from privacyidea.lib.auth import (create_db_admin, verify_db_admin,
                                  list_db_admin, delete_db_admin,
                                  check_webui_user)
from privacyidea.lib.user import User
from flask import current_app


class AuthTestCase(MyTestCase):
    """
    Test the Auth module
    """

    def test_01_db_admin(self):

        create_db_admin(current_app, "mytestadmin", email="admin@localhost",
                        password="PSTwort")
        r = verify_db_admin("mytestadmin", "PSTwort")
        self.assertTrue(r)

        # This only prints to stdout!
        list_db_admin()

        # Delete the admin
        delete_db_admin("mytestadmin")

    def test_02_users(self):
        r, role, detail = check_webui_user(User("cornelius"), "test")
        self.assertFalse(r)
        self.assertEqual(role, "user")
