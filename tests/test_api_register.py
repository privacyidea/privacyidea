# -*- coding: utf-8 -*-
from urllib import urlencode
import json
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.realm import set_realm
from privacyidea.lib.policy import set_policy
from .base import MyTestCase
from privacyidea.lib.policy import SCOPE, ACTION, set_policy, delete_policy
from privacyidea.lib.resolvers.SQLIdResolver import IdResolver as SQLResolver


class RegisterTestCase(MyTestCase):
    """
    test the api.validate endpoints
    """
    parameters = {'Driver': 'sqlite',
                  'Server': '/tests/testdata/',
                  'Database': "testuser.sqlite",
                  'Table': 'users',
                  'Encoding': 'utf8',
                  'Editable': True,
                  'Map': '{ "username": "username", \
                    "userid" : "id", \
                    "email" : "email", \
                    "surname" : "name", \
                    "givenname" : "givenname", \
                    "password" : "password", \
                    "phone": "phone", \
                    "mobile": "mobile"}'
    }

    username = "corneliusReg"

    def test_00_delete_users(self):
        # If the test failed and some users are still in the database (from
        #  add_user) we delete them here.
        y = SQLResolver()
        y.loadConfig(self.parameters)
        uid = y.getUserId(self.username)
        y.delete_user(uid)

    def test_01_register_user(self):
        # create resolver and realm
        param = self.parameters
        param["resolver"] = "register"
        param["type"] = "sqlresolver"
        r = save_resolver(param)
        self. assertTrue(r > 0)

        added, failed = set_realm("register", resolvers=["register"])
        self.assertTrue(added > 0)
        self.assertEqual(len(failed), 0)

        # create policy
        r = set_policy(name="pol2", scope=SCOPE.REGISTER,
                       action="%s=%s, %s=%s" % (ACTION.REALM, "register",
                                                ACTION.RESOLVER, "register"))

        # Try to register, but missing parameter
        with self.app.test_request_context('/register',
                                           method='POST',
                                           data={"username": "cornelius",
                                                 "surname": "Kölbel"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

        # Register
        with self.app.test_request_context('/register',
                                           method='POST',
                                           data={"username": "corneliusReg",
                                                 "surname": "Kölbel",
                                                 "givenname": "Cornelius",
                                                 "password": "cammerah",
                                                 "email":
                                                     "cornelius@privacyidea.org"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)

        # Registering the user a second time will fail
        with self.app.test_request_context('/register',
                                           method='POST',
                                           data={"username": "corneliusReg",
                                                 "surname": "Kölbel",
                                                 "givenname": "Cornelius",
                                                 "password": "cammerah",
                                                 "email":
                                                     "cornelius@privacyidea.org"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

    def test_99_delete_users(self):
        self.test_00_delete_users()
