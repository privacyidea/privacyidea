"""
This test file tests the lib.token methods.

The lib.token depends on the DB model and lib.user and
all lib.tokenclasses

This tests the token functions on an interface level

We start with simple database functions:

getTokens4UserOrSerial
gettokensoftype
getToken....
"""
from privacyidea.lib.error import privacyIDEAError
from privacyidea.lib.token import init_token, assign_tokengroup, unassign_tokengroup
from privacyidea.lib.tokengroup import set_tokengroup, delete_tokengroup, get_tokengroups
from privacyidea.models import Tokengroup
from .base import MyTestCase


class TokenTestCase(MyTestCase):

    def test_01_create_tokengroup(self):
        r = set_tokengroup("gruppe1", "my first typo")
        self.assertGreaterEqual(r, 1)
        tg = Tokengroup.query.filter_by(id=r).first()
        self.assertEqual(tg.Description, "my first typo")

        # Set again should update with new description
        r = set_tokengroup("gruppe1", "my first group")
        self.assertGreaterEqual(r, 1)
        tg = Tokengroup.query.filter_by(id=r).first()
        self.assertEqual(tg.Description, "my first group")

    def test_02_delete_tokengroup(self):  #
        self.group1_id = 0

        def create_token_group():
            self.group1_id = set_tokengroup("group1", "my first group")
            self.assertGreaterEqual(self.group1_id, 1)
            groups = get_tokengroups("group1")
            self.assertEqual(1, len(groups))

        create_token_group()
        self.group2_id = set_tokengroup("group2", "my second group")

        # Try to delete non-existing token group (invalid id)
        with self.assertRaises(privacyIDEAError) as exception:
            delete_tokengroup(tokengroup_id=100)
        self.assertEqual("Token group with ID '100' does not exist.", exception.exception.message)

        # Try to delete non-existing token group (invalid name)
        with self.assertRaises(privacyIDEAError) as exception:
            delete_tokengroup(name="nonexistinggroup")
        self.assertEqual("Token group with name 'nonexistinggroup' does not exist.", exception.exception.message)

        # Try to delete non-existing token group (valid name, but different id)
        with self.assertRaises(privacyIDEAError) as exception:
            delete_tokengroup(name="group1", tokengroup_id=self.group2_id)
        self.assertEqual(f"Token group with name 'group1' with ID '{self.group2_id}' does not exist.",
                         exception.exception.message)

        # Try to delete group if token is still assigned
        token = init_token({"type": "hotp"})
        assign_tokengroup(token.get_serial(), "group1")
        with self.assertRaises(privacyIDEAError) as exception:
            delete_tokengroup(name="group1")
        self.assertEqual("The token group with name 'group1' still has 1 tokens assigned.", exception.exception.message)
        # Remove token from group
        unassign_tokengroup(token.get_serial(), "group1")

        # Try to delete without name and ID
        with self.assertRaises(privacyIDEAError) as exception:
            delete_tokengroup()
        self.assertEqual("You need to specify either a tokengroup ID or a name.", exception.exception.message)

        # Successfully delete by id
        delete_tokengroup(tokengroup_id=self.group1_id)
        tg = get_tokengroups("group1")
        self.assertEqual(0, len(tg))

        # Successfully delete by name
        delete_tokengroup("group2")
        tg = get_tokengroups("group2")
        self.assertEqual(0, len(tg))

        # Successfully delete by name and id
        create_token_group()
        delete_tokengroup(name="group1", tokengroup_id=self.group1_id)
        tg = get_tokengroups("group1")
        self.assertEqual(0, len(tg))

    def test_03_get_tokengroups(self):
        r1 = set_tokengroup("gruppe1", "my first group")
        self.assertGreaterEqual(r1, 1)

        r2 = set_tokengroup("gruppe2", "my 2nd group")
        self.assertGreater(r2, r1)

        tgroups = get_tokengroups()
        self.assertEqual(len(tgroups), 2)

        tgroups = get_tokengroups(name="gruppe1")
        self.assertEqual(len(tgroups), 1)

        tgroups = get_tokengroups(id=r2)
        self.assertEqual(len(tgroups), 1)

        self.assertEqual(tgroups[0].name, "gruppe2")
