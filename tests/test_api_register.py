# -*- coding: utf-8 -*-
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.realm import set_realm
from .base import MyApiTestCase
from privacyidea.lib.policy import SCOPE, ACTION, set_policy
from privacyidea.lib.resolvers.SQLIdResolver import IdResolver as SQLResolver
import json
from privacyidea.lib.smtpserver import add_smtpserver
from . import smtpmock
from privacyidea.lib.config import set_privacyidea_config
from privacyidea.lib.passwordreset import create_recoverycode
from privacyidea.lib.user import User
from privacyidea.lib.error import ERROR


class RegisterTestCase(MyApiTestCase):
    """
    test the api.register and api.recover endpoints
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

    usernames = ["corneliusReg", "corneliusRegFail"]

    def test_00_delete_users(self):
        # If the test failed and some users are still in the database (from
        #  add_user) we delete them here.
        y = SQLResolver()
        y.loadConfig(self.parameters)
        for username in self.usernames:
            uid = y.getUserId(username)
            y.delete_user(uid)

    @smtpmock.activate
    def test_01_register_user(self):
        smtpmock.setdata(response={"cornelius@privacyidea.org": (200, "OK")})
        # create resolver and realm
        param = self.parameters
        param["resolver"] = "register"
        param["type"] = "sqlresolver"
        r = save_resolver(param)
        self. assertTrue(r > 0)

        added, failed = set_realm("register", resolvers=["register"])
        self.assertTrue(len(added) > 0, added)
        self.assertEqual(len(failed), 0, failed)

        # create policy
        r = set_policy(name="pol2", scope=SCOPE.REGISTER,
                       action="{0!s}={1!s}, {2!s}={3!s}".format(ACTION.REALM, "register",
                                                ACTION.RESOLVER, "register"))

        # Try to register, but missing parameter
        with self.app.test_request_context('/register',
                                           method='POST',
                                           data={"username": "cornelius",
                                                 "surname": "Kölbel"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

        # Register fails, missing SMTP config
        with self.app.test_request_context('/register',
                                           method='POST',
                                           data={"username": "corneliusRegFail",
                                                 "surname": "Kölbel",
                                                 "givenname": "Cornelius",
                                                 "password": "cammerah",
                                                 "email":
                                                     "cornelius@privacyidea.org"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)
            data = json.loads(res.data.decode('utf8'))
            self.assertEqual(data.get("result").get("error").get("code"), ERROR.REGISTRATION)
            self.assertEqual(data.get("result").get("error").get("message"),
                         u'ERR402: No SMTP server configuration specified!')

        # Set SMTP config and policy
        add_smtpserver("myserver", "1.2.3.4", sender="pi@localhost")
        set_policy("pol3", scope=SCOPE.REGISTER,
                   action="{0!s}=myserver".format(ACTION.EMAILCONFIG))
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

        # get the register status
        with self.app.test_request_context('/register',
                                           method='GET'):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            data = json.loads(res.data.decode('utf8'))
            self.assertEqual(data.get("result").get("value"), True)

    @smtpmock.activate
    def test_02_reset_password(self):
        smtpmock.setdata(response={"cornelius@privacyidea.org": (200, "OK")})
        set_privacyidea_config("recovery.identifier", "myserver")
        with self.app.test_request_context('/recover',
                                           method='POST',
                                           data={"user": "corneliusReg",
                                                 "realm": "register",
                                                 "email":
                                                     "cornelius@privacyidea.org"}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res.data)
            data = json.loads(res.data.decode('utf8'))
            self.assertEqual(data.get("result").get("value"), True)

    @smtpmock.activate
    def test_03_set_new_password(self):
        smtpmock.setdata(response={"cornelius@privacyidea.org": (200, "OK")})
        # Get the recovery code
        recoverycode = "reccode"
        new_password = "topsecret"
        user = User("corneliusReg", "register")
        r = create_recoverycode(user, recoverycode=recoverycode)
        self.assertEqual(r, True)
        # Use the recoverycode to set a new password
        with self.app.test_request_context('/recover/reset',
                                           method='POST',
                                           data={"user": "corneliusReg",
                                                 "realm": "register",
                                                 "recoverycode": recoverycode,
                                                 "password": new_password}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res.data)
            data = json.loads(res.data.decode('utf8'))
            self.assertEqual(data.get("result").get("value"), True)

        # send an invalid recoverycode
        with self.app.test_request_context('/recover/reset',
                                           method='POST',
                                           data={"user": "corneliusReg",
                                                 "realm": "register",
                                                 "recoverycode": "asdf",
                                                 "password": new_password}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res.data)
            data = json.loads(res.data.decode('utf8'))
            self.assertEqual(data.get("result").get("value"), False)

        # test the new password


    def test_99_delete_users(self):
        self.test_00_delete_users()
