# -*- coding: utf-8 -*-
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
from .base import MyTestCase
from privacyidea.lib.error import privacyIDEAError, ResourceNotFoundError

from privacyidea.lib.tokengroup import set_tokengroup, delete_tokengroup, get_tokengroups
from privacyidea.models import Tokengroup


class TokenTestCase(MyTestCase):

    def test_01_create_tokengroup(self):

        r = set_tokengroup("gruppe1", "my first typo")
        self.assertGreaterEqual(r, 1)
        tg = Tokengroup.query.filter_by(id=r).first()
        self.assertEqual(tg.Description, "my first typo")

        r = set_tokengroup("gruppe1", "my first group")
        self.assertGreaterEqual(r, 1)
        tg = Tokengroup.query.filter_by(id=r).first()
        self.assertEqual(tg.Description, "my first group")

    def test_02_delete_tokengroup(self):
        r = set_tokengroup("gruppe1", "my first group")
        self.assertGreaterEqual(r, 1)

        delete_tokengroup("gruppe1")
        tg = Tokengroup.query.filter_by(name="gruppe1").all()
        self.assertEqual(len(tg), 0)

        r = set_tokengroup("gruppe1", "my other first group")
        self.assertGreaterEqual(r, 1)

        self.assertRaises(privacyIDEAError,
                          delete_tokengroup, tokengroup_id=(r + 1), name='gruppe1')

        delete_tokengroup(tokengroup_id=r)
        tg = Tokengroup.query.filter_by(name="gruppe1").all()
        self.assertEqual(len(tg), 0)

        self.assertRaises(ResourceNotFoundError, delete_tokengroup)

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





