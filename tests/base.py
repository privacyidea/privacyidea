# -*- coding: utf-8 -*-

import unittest
import json
import mock

from privacyidea.app import create_app
from privacyidea.config import TestingConfig
from privacyidea.models import db, save_config_timestamp
from privacyidea.lib.resolver import (save_resolver)
from privacyidea.lib.realm import (set_realm)
from privacyidea.lib.user import User
from privacyidea.lib.auth import create_db_admin
from privacyidea.lib.auditmodules.base import Audit


PWFILE = "tests/testdata/passwords"
PWFILE2 = "tests/testdata/passwd"


class FakeFlaskG(object):
    policy_object = None
    logged_in_user = {}
    audit_object = None


class FakeAudit(Audit):

    def __init__(self):
        self.audit_data = {}


class MyTestCase(unittest.TestCase):
    resolvername1 = "resolver1"
    resolvername2 = "Resolver2"
    resolvername3 = "reso3"
    realm1 = "realm1"
    realm2 = "realm2"
    realm3 = "realm3"
    serials = ["SE1", "SE2", "SE3"]
    otpkey = "3132333435363738393031323334353637383930"
    valid_otp_values = ["755224",
                        "287082",
                        "359152",
                        "969429",
                        "338314",
                        "254676",
                        "287922",
                        "162583",
                        "399871",
                        "520489"]

    
    @classmethod
    def setUpClass(cls):
        cls.app = create_app('testing', "")
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        db.create_all()
        # save the current timestamp to the database to avoid hanging cached
        # data
        save_config_timestamp()
        db.session.commit()
        # Create an admin for tests.
        create_db_admin(cls.app, "testadmin", "admin@test.tld", "testpw")

    def setUp_user_realms(self):
        # create user realm
        rid = save_resolver({"resolver": self.resolvername1,
                             "type": "passwdresolver",
                             "fileName": PWFILE})
        self.assertTrue(rid > 0, rid)

        (added, failed) = set_realm(self.realm1,
                                    [self.resolvername1])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 1)

        user = User(login="root",
                    realm=self.realm1,
                    resolver=self.resolvername1)

        user_str = "{0!s}".format(user)
        self.assertTrue(user_str == "<root.resolver1@realm1>", user_str)

        self.assertFalse(user.is_empty())
        self.assertTrue(User().is_empty())

        user_repr = "{0!r}".format(user)
        expected = "User(login='root', realm='realm1', resolver='resolver1')"
        self.assertTrue(user_repr == expected, user_repr)

    def setUp_user_realm2(self):
        # create user realm
        rid = save_resolver({"resolver": self.resolvername1,
                             "type": "passwdresolver",
                             "fileName": PWFILE})
        self.assertTrue(rid > 0, rid)

        (added, failed) = set_realm(self.realm2,
                                    [self.resolvername1])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 1)

        user = User(login="root",
                    realm=self.realm2,
                    resolver=self.resolvername1)

        user_str = "{0!s}".format(user)
        self.assertTrue(user_str == "<root.resolver1@realm2>", user_str)

        self.assertFalse(user.is_empty())
        self.assertTrue(User().is_empty())

        user_repr = "{0!r}".format(user)
        expected = "User(login='root', realm='realm2', resolver='resolver1')"
        self.assertTrue(user_repr == expected, user_repr)

    def setUp_user_realm3(self):
        # create user realm
        rid = save_resolver({"resolver": self.resolvername3,
                             "type": "passwdresolver",
                             "fileName": PWFILE2})
        self.assertTrue(rid > 0, rid)

        (added, failed) = set_realm(self.realm3,
                                    [self.resolvername3])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 1)

        user = User(login="root",
                    realm=self.realm3,
                    resolver=self.resolvername3)

        user_str = "{0!s}".format(user)
        self.assertTrue(user_str == "<root.reso3@realm3>", user_str)

        self.assertFalse(user.is_empty())
        self.assertTrue(User().is_empty())

        user_repr = "{0!r}".format(user)
        expected = "User(login='root', realm='realm3', resolver='reso3')"
        self.assertTrue(user_repr == expected, user_repr)

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.drop_all()
        cls.app_context.pop()

    def authenticate(self):
        with self.app.test_request_context('/auth',
                                           data={"username": "testadmin",
                                                 "password": "testpw"},
                                           method='POST'):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertTrue(result.get("status"), res.data)
            self.at = result.get("value").get("token")

    def authenticate_selfservice_user(self):
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username":
                                                     "selfservice@realm1",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertTrue(result.get("status"), res.data)
            # In self.at_user we store the user token
            self.at_user = result.get("value").get("token")
            # check that this is a user
            role = result.get("value").get("role")
            self.assertTrue(role == "user", result)
            self.assertEqual(result.get("value").get("realm"), "realm1")


class OverrideConfigTestCase(MyTestCase):
    """
    helper class that allows to modify the app config processed by ``create_app``.
    This can be useful if config values need to be adjusted *for app creation*.
    For that, just override the inner ``Config`` class.
    """
    class Config(TestingConfig):
        pass

    @classmethod
    def setUpClass(cls):
        """ override privacyidea.config.config["testing"] with the inner config class """
        with mock.patch.dict("privacyidea.config.config", {"testing": cls.Config}):
            MyTestCase.setUpClass()


class MyApiTestCase(MyTestCase):
    @classmethod
    def cls_auth(cls, app):
        with app.test_request_context('/auth', data={"username": "testadmin",
                                                     "password": "testpw"},
                                      method='POST'):
            res = app.full_dispatch_request()
            assert res.status_code == 200
            result = res.json.get("result")
            assert result.get("status")
            cls.at = result.get("value").get("token")

    @classmethod
    def setUpClass(cls):
        super(MyApiTestCase, cls).setUpClass()
        cls.cls_auth(cls.app)
