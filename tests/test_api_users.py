from .base import MyTestCase
import json
from urllib import urlencode

PWFILE = "tests/testdata/passwd"


class APIUsersTestCase(MyTestCase):
       
    def test_00_get_empty_users(self):
        with self.app.test_request_context('/user/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue('"status": true' in res.data, res.data)
            self.assertTrue('"value": []' in res.data, res.data)

    def test_01_get_passwd_user(self):
        # create resolver
        with self.app.test_request_context('/resolver/r1',
                                           data=json.dumps({u"resolver": u"r1",
                                                 u"type": u"passwdresolver",
                                                 u"fileName": PWFILE}),
                                           method='POST',
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue('"status": true' in res.data, res.data)
            self.assertTrue('"value": 1' in res.data, res.data)
        
        # create realm
        realm = u"realm1"
        resolvers = u"r1, r2"
        with self.app.test_request_context('/realm/%s' % realm,
                                           data={u"resolvers": resolvers},
                                           method='POST',
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data)
            value = result.get("result").get("value")
            self.assertTrue('r1' in value["added"], res.data)
            self.assertTrue('r2' in value["failed"], res.data)
                   
        # get user list
        with self.app.test_request_context('/user/',
                                           query_string=urlencode({u"realm":
                                                                       realm}),
                                           method='GET',
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data)
            value = result.get("result").get("value")
            self.assertTrue('"username": "cornelius"' in res.data, res.data)
            self.assertTrue('"username": "corny"' in res.data, res.data)

        # get user list with search dict
        with self.app.test_request_context('/user/',
                                           query_string=urlencode({u"username":
                                                           "cornelius"}),
                                           method='GET',
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data)
            value = result.get("result").get("value")
            self.assertTrue('"username": "cornelius"' in res.data, res.data)
            self.assertTrue('"username": "corny"' not in res.data, res.data)
            
        # get user with a non existing realm
        with self.app.test_request_context('/user/',
                                           query_string=urlencode({"realm":
                                                            "non_existing"}),
                                           method='GET',
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data)
            value = result.get("result").get("value")
            self.assertTrue('"username": "cornelius"' not in res.data, res.data)
            self.assertTrue('"username": "corny"' not in res.data, res.data)
