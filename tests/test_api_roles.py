"""
This file tests the authentication of admin users and normal user (
selfservice) on the REST API.
The interesting implementation is contained in api/auth.py
"""
import json
from .base import MyTestCase
from privacyidea.lib.error import (ParameterError, ConfigAdminError)
from privacyidea.lib.policy import get_policies
from urllib import urlencode

PWFILE = "tests/testdata/passwords"


class APIRolesTestCase(MyTestCase):

    def setUp(self):
        """
        For each test we need to initialize the self.at and the self.at_user
        members.
        """
        self.setUp_user_realms()
        self.authenticate()
        self.authenitcate_selfserive_user()

    def authenitcate_selfserive_user(self):
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username":
                                                     "selfservice@realm1",
                                                 "password": "test"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("status"), res.data)
            # In self.at_user we store the user token
            self.at_user = result.get("value").get("token")
            # check that this is a user
            role = result.get("value").get("role")
            self.assertTrue(role == "user", result)

    def test_00_authenitcate_admin_fail(self):
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "admin",
                                                 "password": "testpw"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

    def test_01_authenitcate_admin(self):
        with self.app.test_request_context('/auth',
                                           method='POST',
                                           data={"username": "testadmin",
                                                 "password": "testpw"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data).get("result")
            self.assertTrue(result.get("status"), res.data)
            # In self.at_user we store the user token
            self.at_admin = result.get("value").get("token")
            # check that this is a user
            role = result.get("value").get("role")
            self.assertTrue(role == "admin", result)

    def test_02_user_not_allowed(self):
        # The user is not allowed to read system information
        with self.app.test_request_context('/system/',
                                           method='GET',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

        with self.app.test_request_context('/token/',
                                           method='GET',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

        with self.app.test_request_context('/realm/',
                                           method='GET',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

        with self.app.test_request_context('/resolver/',
                                           method='GET',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

        with self.app.test_request_context('/user/',
                                           method='GET',
                                           headers={'Authorization':
                                                        self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)
