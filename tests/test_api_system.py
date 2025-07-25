""" API testcases for the "/system/ endpoint """
import gnupg
import json
import os
import unittest
from urllib.parse import urlencode

from .base import MyApiTestCase

from privacyidea.lib.policy import PolicyClass, set_policy, delete_policy, ACTION, SCOPE
from privacyidea.lib.caconnector import save_caconnector, delete_caconnector
from privacyidea.lib.caconnectors.localca import ATTR
from privacyidea.lib.radiusserver import add_radius, delete_radius
from privacyidea.lib.resolver import save_resolver, delete_resolver, CENSORED
from privacyidea.lib.realm import delete_realm, get_realms
from privacyidea.models import db, NodeName
from .test_lib_resolver import LDAPDirectory, ldap3mock
from .test_lib_caconnector import CACERT, CAKEY, WORKINGDIR, OPENSSLCNF
from privacyidea.models import UserCache

PWFILE = "tests/testdata/passwords"
POLICYFILE = "tests/testdata/policy.cfg"
POLICYEMPTY = "tests/testdata/policy_empty_file.cfg"

try:
    _g = gnupg.GPG()
    gpg_available = True
except OSError as _e:
    gpg_available = False


class APIConfigTestCase(MyApiTestCase):

    def test_00_get_empty_config(self):
        with self.app.test_request_context('/system/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            self.assertTrue(res.json['result']['status'], res.json)

    def test_00_failed_auth(self):
        with self.app.test_request_context('/system/',
                                           method='GET'):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401, res)

    def test_01_set_config(self):
        with self.app.test_request_context('/system/setConfig',
                                           data={"key1": "value1",
                                                 "key2": "value2",
                                                 "key3": "value3"},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            value = res.json['result']['value']
            self.assertEqual(value.get("key1"),
                             "insert",
                             "This sometimes happens when test database was "
                             "not empty!")
            self.assertEqual(value.get("key2"), "insert")
            self.assertEqual(value.get("key3"), "insert")

    def test_02_update_config(self):
        with self.app.test_request_context('/system/setConfig',
                                           data={"key3": "new value"},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            self.assertEqual(res.json['result']['value']['key3'], 'update',
                             res.json)

    def test_03_set_and_del_default(self):
        with self.app.test_request_context('/system/setDefault',
                                           data={"DefaultMaxFailCount": 1,
                                                 "DefaultSyncWindow": 10,
                                                 "DefaultCountWindow": 12,
                                                 "DefaultOtpLen": 6,
                                                 "DefaultResetFailCount": 12},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertEqual(res.status_code, 200, res)
            self.assertTrue(result["status"], result)
            self.assertTrue(result["value"]["DefaultOtpLen"] == "insert",
                            result)

        with self.app.test_request_context('/system/DefaultMaxFailCount',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertEqual(result["value"], 1, result)

        with self.app.test_request_context('/system/DefaultMaxFailCount',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertIsNone(result["value"], result)

        # test unknown parameter
        with self.app.test_request_context('/system/setDefault',
                                           data={"unknown": "xx"},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            # "unknown" is an unknown Default Parameter. So a ParamterError
            # is raised.
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400, res)

    def test_04_set_policy(self):
        self.setUp_user_realms()
        with self.app.test_request_context('/policy/pol1',
                                           data={'action': ACTION.ENABLE,
                                                 'scope': SCOPE.USER,
                                                 'realm': self.realm1,
                                                 'resolver': self.resolvername1,
                                                 'user': ["admin"],
                                                 'time': "",
                                                 'client': "127.12.12.12",
                                                 'active': True},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertEqual(result['value']['setPolicy pol1'], 1, res.json)

        # Update the policy with a more complicated client
        with self.app.test_request_context('/policy/pol1',
                                           data={'action': ACTION.ENABLE,
                                                 'scope': SCOPE.USER,
                                                 'realm': self.realm1,
                                                 'resolver': self.resolvername1,
                                                 'user': ["admin"],
                                                 'time': "",
                                                 'client': "10.0.0.0/8, "
                                                           "172.16.200.1",
                                                 'active': True},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json['result']
            self.assertTrue(result["status"], result)
            self.assertGreaterEqual(result['value']['setPolicy pol1'], 1, result)

        # setting policy with invalid name fails
        with self.app.test_request_context('/policy/invalid policy name',
                                           data={'action': ACTION.ENABLE,
                                                 'scope': SCOPE.USER,
                                                 'client': "127.12.12.12",
                                                 'active': True},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            # An invalid policy name raises an exception
            res = self.app.full_dispatch_request()
            self.assertEqual(400, res.status_code, res)
            error = res.json.get("result").get("error")
            self.assertEqual(905, error.get("code"))
            self.assertIn("Policy name must not contain white spaces!", error.get("message"))

        # setting policy with a missing action
        with self.app.test_request_context('/policy/enroll',
                                           data={'scope': SCOPE.USER,
                                                 'client': "127.12.12.12",
                                                 'active': True},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            # An invalid policy name raises an exception
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400, res)
            error = res.json.get("result").get("error")
            self.assertEqual(905, error.get("code"))
            self.assertIn("Missing parameter: action", error.get("message"))

    def test_05_get_policy(self):
        with self.app.test_request_context('/policy/pol1',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertTrue("pol1" == result["value"][0].get("name"), res.data)

    def test_06_export_policy(self):
        with self.app.test_request_context('/policy/export/test.cfg',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            body = res.data
            self.assertTrue(b'name = pol1' in body, res.data)
            self.assertTrue(b"[pol1]" in body, res.data)
        delete_policy("pol1")

    def test_07_update_and_delete_policy(self):
        self.setUp_user_realms()
        with self.app.test_request_context('/policy/pol_update_del',
                                           data={'action': ACTION.ENABLE,
                                                 'scope': SCOPE.USER,
                                                 'realm': self.realm1,
                                                 'resolver': self.resolvername1,
                                                 'user': "admin",
                                                 'time': "",
                                                 'client': "127.12.12.12",
                                                 'active': True},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertTrue(result["value"]["setPolicy pol_update_del"] > 0,
                            res.data)

        # update policy
        with self.app.test_request_context('/policy/pol_update_del',
                                           data={'action': ACTION.ENABLE,
                                                 'scope': SCOPE.USER,
                                                 'realm': self.realm1,
                                                 'client': "1.1.1.1"},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["value"]["setPolicy pol_update_del"] > 0,
                            res.data)

        # get policy
        with self.app.test_request_context('/policy/pol_update_del',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            policy = {}
            for pol in result["value"]:
                if pol.get("name") == "pol_update_del":
                    policy = pol
                    break
            self.assertTrue("1.1.1.1" in policy.get("client"),
                            res.data)

        # delete policy again does not do anything
        with self.app.test_request_context('/policy/pol_update_del',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)

        # delete policy
        with self.app.test_request_context('/policy/pol_update_del',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 404)
            result = res.json.get("result")
            self.assertFalse(result["status"])

        # check policy
        with self.app.test_request_context('/policy/pol_update_del',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertTrue(result["value"] == [], result)

        delete_realm(self.realm1)
        delete_resolver(self.resolvername1)

    # Resolvers
    """
    We should move this to LDAP resolver tests and mock this.

    def test_08_pretestresolver(self):
        # This test fails, as there is no server at localhost.
        param = {'LDAPURI': 'ldap://localhost',
                 'LDAPBASE': 'o=test',
                 'BINDDN': 'cn=manager,ou=example,o=test',
                 'BINDPW': 'ldaptest',
                 'LOGINNAMEATTRIBUTE': 'cn',
                 'LDAPSEARCHFILTER': '(cn=*)',
                 'USERINFO': '{ "username": "cn",'
                             '"phone" : "telephoneNumber", '
                             '"mobile" : "mobile"'
                             ', "email" : "mail", '
                             '"surname" : "sn", '
                             '"givenname" : "givenName" }',
                 'UIDTYPE': 'DN',
                 'type': 'ldapresolver'}
        with self.app.test_request_context('/resolver/test',
                                           data=param,
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            detail = res.json.get("detail")
            self.assertFalse(result.get("value"), result)
            self.assertTrue("no active server available in server pool" in
                            detail.get("description"),
                            detail.get("description"))
    """

    def test_08_no_ldap_password(self):
        params = {'LDAPURI': 'ldap://localhost',
                  'LDAPBASE': 'o=test',
                  'BINDDN': 'cn=manager,ou=example,o=test',
                  'BINDPW': 'ldaptest',
                  'LOGINNAMEATTRIBUTE': 'cn',
                  'LDAPSEARCHFILTER': '(cn=*)',
                  'USERINFO': '{ "username": "cn", "phone": "telephoneNumber", '
                              '"mobile" : "mobile", "email": "mail", '
                              '"surname" : "sn", "givenname": "givenName" }',
                  'UIDTYPE': 'DN',
                  'type': 'ldapresolver',
                  'resolver': 'testL'}
        r = save_resolver(params)
        self.assertTrue(r)
        with self.app.test_request_context('/resolver/testL',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            data = result["value"]["testL"]["data"]
            self.assertEqual(data.get("BINDPW"), CENSORED)

        with self.app.test_request_context('/resolver/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            data = result["value"]["testL"]["data"]
            self.assertEqual(data.get("BINDPW"), CENSORED)

        r = delete_resolver(params.get("resolver"))
        self.assertTrue(r)

    def test_08_resolvers(self):
        with self.app.test_request_context('/resolver/resolver1',
                                           data={'type': 'passwdresolver',
                                                 'filename': PWFILE},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertGreaterEqual(result["value"], 1, result)
            res_id = result["value"]

        with self.app.test_request_context('/resolver/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertTrue("resolver1" in result["value"], result)
            self.assertTrue("filename" in result["value"]["resolver1"]["data"])

        # Get a non existing resolver
        with self.app.test_request_context('/resolver/unknown',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            # The value is empty
            self.assertTrue(result["value"] == {}, result)

        # Get only editable resolvers
        with self.app.test_request_context('/resolver/',
                                           method='GET',
                                           query_string=urlencode({
                                               "editable": "1"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            # The value is empty
            self.assertTrue(result["value"] == {}, result)

        # this will fetch all resolvers
        with self.app.test_request_context('/resolver/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            value = result.get("value")
            self.assertTrue("resolver1" in value, value)

        # get non-editable resolvers
        with self.app.test_request_context('/resolver/',
                                           method='GET',
                                           query_string=urlencode({
                                               "editable": "0"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            value = result.get("value")
            self.assertTrue("resolver1" in value, value)

        # get a resolver name
        with self.app.test_request_context('/resolver/resolver1',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertEqual(res.status_code, 200, res)
            self.assertTrue(result["status"], result)
            self.assertTrue("resolver1" in result["value"], result)
            self.assertTrue("filename" in result["value"]["resolver1"]["data"])

        # get a resolver name
        with self.app.test_request_context('/resolver/resolver1',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertTrue("resolver1" in result["value"], result)
            self.assertTrue("filename" in result["value"]["resolver1"]["data"])

        # delete the resolver
        with self.app.test_request_context('/resolver/resolver1',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertEqual(res.status_code, 200, res)
            self.assertTrue(result["status"], result)
            self.assertEqual(result["value"], res_id, result)

        # delete a non existing resolver
        with self.app.test_request_context('/resolver/xycswwf',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertEqual(res.status_code, 200, res)
            self.assertTrue(result["status"], result)
            # Trying to delete a non-existing resolver returns -1
            self.assertTrue(result["value"] == -1, result)

    def test_09_handle_realms(self):
        resolvername = "reso1_with_realm"
        realmname = "realm1_with_resolver"
        # create a resolver
        with self.app.test_request_context('/resolver/{0!s}'.format(resolvername),
                                           method='POST',
                                           data={"filename": PWFILE,
                                                 "type": "passwdresolver"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            # The resolver was created. The ID of the resolver is returend.
            self.assertGreaterEqual(result["value"], 1, result)
            res_id = result["value"]

        # create a realm
        with self.app.test_request_context('/realm/{0!s}'.format(realmname),
                                           method='POST',
                                           data={"resolvers": resolvername},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            # The resolver was created
            self.assertTrue(len(result["value"].get("added")) == 1, result)
            self.assertTrue(len(result["value"].get("failed")) == 0, result)

        # create a realm with multiple resolvers
        with self.app.test_request_context('/realm/realm2',
                                           method='POST',
                                           json={"resolvers": [resolvername, "resolver2"]},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            # The resolver was created
            self.assertEqual(len(result["value"].get("added")), 1, result)
            self.assertEqual(len(result["value"].get("failed")), 1, result)

        # display the realm
        with self.app.test_request_context('/realm/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            # The resolver was created = 1
            self.assertTrue(realmname in result["value"], result)
            realm_contents = result["value"].get(realmname)
            self.assertTrue(realm_contents.get("resolver")[0].get("name") ==
                            resolvername, result)

        # get the superuser realms
        with self.app.test_request_context('/realm/superuser',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertTrue("adminrealm" in result["value"], result)

        # try to delete the resolver in the realm
        with self.app.test_request_context('/resolver/{0!s}'.format(resolvername),
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            # The resolver must not be deleted, since it is contained in a realm
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400, res)

        # delete the realm
        with self.app.test_request_context('/realm/{0!s}'.format(realmname),
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            # The realm gets deleted
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            # The realm is successfully deleted: value is the id in
            # the db, should be >= 1
            self.assertGreaterEqual(result["value"], 1, result)

        # delete the second realm
        with self.app.test_request_context('/realm/realm2',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            # The realm gets deleted
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            # The realm is successfully deleted: value is the id in
            # the db, should be >= 1
            self.assertGreaterEqual(result["value"], 1, result)

        # Now, we can delete the resolver
        with self.app.test_request_context('/resolver/{0!s}'.format(resolvername),
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            # The resolver must not be deleted, since it is contained in a realm
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            # The resolver was deleted = 1
            self.assertEqual(result["value"], res_id, result)

    def test_10_default_realm(self):
        resolvername = "defresolver"
        realmname = "defrealm"
        with self.app.test_request_context('/resolver/{0!s}'.format(resolvername),
                                           method='POST',
                                           data={"filename": PWFILE,
                                                 "type": "passwdresolver"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)

        # create a realm
        with self.app.test_request_context('/realm/{0!s}'.format(realmname),
                                           method='POST',
                                           data={"resolvers": resolvername,
                                                 "priority.defresolver": 10},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)

        # get the default realm
        with self.app.test_request_context('/defaultrealm',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertTrue("defrealm" in result["value"], result)

        # clear the default realm
        with self.app.test_request_context('/defaultrealm',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)

        # get the default realm
        with self.app.test_request_context('/defaultrealm',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertTrue(result["value"] == {}, result)

        # set the default realm
        with self.app.test_request_context('/defaultrealm/defrealm',
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)

        # get the default realm
        with self.app.test_request_context('/defaultrealm',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            self.assertEqual(res.status_code, 200, res)
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertTrue("defrealm" in result["value"], result)

    def test_11_import_policy(self):
        with self.app.test_request_context('/policy/import/policy.cfg',
                                           method='POST',
                                           data=dict(file=(POLICYFILE,
                                                           'policy.cfg')),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertEqual(result["value"], 2, result)
            # check if policies are there
            pol = PolicyClass()
            p1 = pol.match_policies(name="importpol1")
            self.assertTrue(len(p1) == 1, p1)
            p2 = pol.match_policies(name="importpol2")
            self.assertTrue(len(p2) == 1, p2)
        delete_policy("importpol1")
        delete_policy("importpol2")

        # import empty file
        with self.app.test_request_context("/policy/import/"
                                           "policy_empty_file.cfg",
                                           method='POST',
                                           data=dict(file=(POLICYEMPTY,
                                                           "policy_empty_file.cfg")),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400, res)

    def test_12_test_check_policy(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        self.setUp_user_realm3()

        # test invalid policy name "check"
        with self.app.test_request_context('/policy/check',
                                           method='POST',
                                           data={"realm": "*",
                                                 "action": f"{ACTION.ENABLE}, {ACTION.DISABLE}",
                                                 "scope": SCOPE.USER,
                                                 "user": "*, -user1",
                                                 "client": "172.16.0.0/16, "
                                                           "-172.16.1.1"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400, res)

        with self.app.test_request_context('/policy/pol1',
                                           method='POST',
                                           data={"realm": "*",
                                                 "action": f"{ACTION.ENABLE}, {ACTION.DISABLE}",
                                                 "scope": SCOPE.USER,
                                                 "user": "*, -user1",
                                                 "client": "172.16.0.0/16, "
                                                           "-172.16.1.1"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertGreater(result.get("value")["setPolicy pol1"], 0, result)

        with self.app.test_request_context('/policy/pol2',
                                           method='POST',
                                           data={"realm": "*",
                                                 "action": f"{ACTION.HIDE_TOKENINFO}=hashlib, "
                                                           f"{ACTION.DELETE}",
                                                 "scope": SCOPE.USER,
                                                 "user": "admin, superuser",
                                                 "client": "172.16.1.1"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertGreater(result.get("value")["setPolicy pol2"], 1, result)

        # CHECK: user=superuser, action=enable, client=172.16.1.1
        # is not allowed
        with self.app.test_request_context('/policy/check',
                                           method='GET',
                                           query_string=urlencode({"realm": self.realm1,
                                                                   "action": ACTION.ENABLE,
                                                                   "scope": SCOPE.USER,
                                                                   "user": "superuser",
                                                                   "client": "172.16.1.1"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertFalse(result.get("value").get("allowed"), result)

        # CHECK: user=superuser, action=enable, client=172.16.1.2
        # is allowed
        with self.app.test_request_context('/policy/check',
                                           method='GET',
                                           query_string=urlencode({"realm": self.realm2,
                                                                   "action": ACTION.ENABLE,
                                                                   "scope": SCOPE.USER,
                                                                   "user": "superuser",
                                                                   "client": "172.16.1.2"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value").get("allowed"), result)

        # CHECK: user=superuser, action=hide_token_info, client=172.16.1.2
        # is not allowed
        with self.app.test_request_context('/policy/check',
                                           method='GET',
                                           query_string=urlencode({"realm": self.realm3,
                                                                   "action": ACTION.HIDE_TOKENINFO,
                                                                   "scope": SCOPE.USER,
                                                                   "user": "superuser",
                                                                   "client": "172.16.1.2"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertFalse(result.get("value").get("allowed"), result)

        # CHECK: user=superuser, action=hide_token_info, client=172.16.1.1
        # is allowed
        with self.app.test_request_context('/policy/check',
                                           method='GET',
                                           query_string=urlencode({"realm": self.realm1,
                                                                   "action": ACTION.HIDE_TOKENINFO,
                                                                   "scope": SCOPE.USER,
                                                                   "user": "superuser",
                                                                   "client": "172.16.1.1"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value").get("allowed"), result)

        delete_policy("pol1")
        delete_policy("pol2")

    def test_13_get_policy_defs(self):
        with self.app.test_request_context('/policy/defs',
                                           method='GET',
                                           data={},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            policies = result.get("value")
            admin_pol = policies.get("admin")
            self.assertTrue("enable" in admin_pol, admin_pol)
            self.assertTrue("enrollTOTP" in admin_pol, admin_pol)
            self.assertTrue("enrollHOTP" in admin_pol, admin_pol)
            self.assertTrue("enrollPW" in admin_pol, admin_pol)

        with self.app.test_request_context('/policy/defs/admin',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertEqual(res.status_code, 200, res)
            admin_pol = result.get("value")
            self.assertTrue("enable" in admin_pol, admin_pol)
            self.assertTrue("enrollTOTP" in admin_pol, admin_pol)
            self.assertTrue("enrollHOTP" in admin_pol, admin_pol)
            self.assertTrue("enrollPW" in admin_pol, admin_pol)

        with self.app.test_request_context('/policy/defs/conditions',
                                           method='GET',
                                           data={},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            conditions = result.get("value")
            self.assertIn("sections", conditions)
            self.assertIn("userinfo", conditions["sections"])
            self.assertIn("description", conditions["sections"]["userinfo"])
            self.assertIn("comparators", conditions)
            self.assertIn("contains", conditions["comparators"])
            self.assertIn("description", conditions["comparators"]["contains"])

    def test_14_enable_disable_policy(self):
        set_policy("pol2", scope=SCOPE.USER, action=ACTION.ENABLE)
        with self.app.test_request_context('/policy/pol2',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertEqual(res.status_code, 200, res)
            pol = result.get("value")
            self.assertTrue(pol[0].get("active"), pol[0])

        # Disable policy
        with self.app.test_request_context('/policy/disable/pol2',
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("status"), result)
            self.assertGreater(result.get("value"), 0, result)

        with self.app.test_request_context('/policy/pol2',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertEqual(res.status_code, 200, res)
            pol = result.get("value")
            self.assertFalse(pol[0].get("active"), pol[0])

        # enable Policy
        with self.app.test_request_context('/policy/enable/pol2',
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertEqual(res.status_code, 200, res)
            self.assertTrue(result.get("status"), result)
            self.assertGreater(result.get("value"), 0, result)

        with self.app.test_request_context('/policy/pol2',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertEqual(res.status_code, 200, res)
            pol = result.get("value")
            self.assertTrue(pol[0].get("active"), pol[0])

        delete_policy("pol2")

    def test_15_get_documentation(self):
        with self.app.test_request_context('/system/documentation',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            self.assertEqual(res.mimetype, 'text/plain', res)
            self.assertTrue(b"privacyIDEA configuration documentation" in
                            res.data)

    def test_16_get_hsm(self):
        with self.app.test_request_context('/system/hsm',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            value = result.get("value")
            self.assertTrue(value.get("is_ready"), value)

        # HSM is already set up. We do not need to set a password
        with self.app.test_request_context('/system/hsm',
                                           data={"password": "xx"},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400, res)

    def test_17_test_token_config(self):
        with self.app.test_request_context('/system/test/hotp',
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            details = res.json.get("detail")
            value = result.get("value")
            self.assertEqual(value, False)
            self.assertEqual(details.get("message"), "Not implemented")

    def test_18_test_random(self):
        with self.app.test_request_context('/system/random?len=32',
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            value = result.get("value")
            # hex encoded value
            self.assertEqual(len(value), 64)
            # This is hex, we can unhexlify
            import binascii
            binascii.unhexlify(value)

        with self.app.test_request_context('/system/random?len=32&encode=b64',
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            value = result.get("value")
            # hex encoded value
            self.assertEqual(len(value), 44)
            # This is base64. We can decode
            import base64
            base64.b64decode(value)

    @unittest.skipIf(not gpg_available, "'gpg' binary not available")
    def test_19_get_gpg_keys(self):
        with self.app.test_request_context('/system/gpgkeys',
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            value = result.get("value")
            # We probably have no keys in here
            # But value returns a dictionary with the KeyID and "armor" and
            # "fingerprint"
            self.assertIn("2F25BAF8645350BB", value, value)
            key_obj = value.get("2F25BAF8645350BB")
            self.assertIn("-----BEGIN PGP PUBLIC KEY BLOCK-----", key_obj.get("armor"), key_obj)
            self.assertEqual("6630FE8C6866433020D39FA02F25BAF8645350BB", key_obj.get("fingerprint"), value)

    @ldap3mock.activate
    def test_20_multiple_test_resolvers(self):
        ldap3mock.setLDAPDirectory(LDAPDirectory)
        params = {'LDAPURI': 'ldap://localhost',
                  'LDAPBASE': 'o=test',
                  'BINDDN': 'cn=manager,ou=example,o=test',
                  'BINDPW': 'ldaptest',
                  'LOGINNAMEATTRIBUTE': 'cn',
                  'LDAPSEARCHFILTER': '(cn=*)',
                  'USERINFO': '{ "username": "cn", "phone": "telephoneNumber", '
                              '"mobile" : "mobile", "email": "mail", '
                              '"surname" : "sn", "givenname": "givenName" }',
                  'UIDTYPE': 'DN'}

        resolvername = "blablaReso"
        params["resolver"] = resolvername
        params["type"] = "ldapresolver"
        with self.app.test_request_context('/resolver/{0}'.format(resolvername),
                                           data=params,
                                           method="POST",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertGreater(result["value"], 0, result)

        with (((self.app.test_request_context('/resolver/{0}'.format(resolvername),
                                              method="GET",
                                              headers={'Authorization': self.at})))):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            params = result.get("value").get(resolvername).get("data")
            # the returned password is censored
            self.assertEqual(params.get("BINDPW"), CENSORED)
            # the intenal password is correct
            int_res_cnf = self.app_context.g._request_local_store.get("config_object").resolver.get(resolvername)
            self.assertEqual(int_res_cnf.get("data").get("BINDPW"), "ldaptest")

    def test_21_read_write_resolver_policy(self):
        # create resolver
        resolvername = "reso21"
        params = {"resolver": resolvername,
                  "type": "passwdresolver",
                  "file": "/etc/passwd"}
        with self.app.test_request_context('/resolver/{0}'.format(resolvername),
                                           data=params,
                                           method="POST",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)

        # Set a read policy
        set_policy(name="pol_read", scope=SCOPE.ADMIN,
                   action=ACTION.RESOLVERREAD)

        # Now writing a resolver will fail
        with self.app.test_request_context('/resolver/{0}'.format(resolvername),
                                           data=params,
                                           method="POST",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403)

        # reading a resolver will succeed
        with self.app.test_request_context('/resolver/{0}'.format(resolvername),
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)

        # set a write policy
        set_policy(name="pol_write", scope=SCOPE.ADMIN,
                   action=ACTION.RESOLVERWRITE)

        # Now writing a resolver will succeed
        with self.app.test_request_context('/resolver/{0}'.format(resolvername),
                                           data=params,
                                           method="POST",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)

        # delete read policy
        delete_policy("pol_read")

        # reading a resolver will fail
        with self.app.test_request_context('/resolver/{0}'.format(resolvername),
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403)

        # writing a resolver will still succeed
        with self.app.test_request_context('/resolver/{0}'.format(resolvername),
                                           data=params,
                                           method="POST",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)

        delete_policy("pol_write")
        delete_resolver(resolvername)

    def test_22_list_radius_servers(self):
        add_radius("local", "localhost", "foobar")
        add_radius("remote", "remote.example.com", "secret", description="very far away")

        # cannot access the RADIUS server names without authorization
        with self.app.test_request_context("/system/names/radius",
                                           method="GET",
                                           headers={}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 401)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertIn("Missing Authorization header", result["error"]["message"])

        # if no admin policies are defined, admins can access the RADIUS servers
        with self.app.test_request_context("/system/names/radius",
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertEqual(set(result["value"]), {"local", "remote"})

        # if an admin policy is defined and enrollRADIUS is not allowed, admins cannot access the RADIUS servers
        set_policy("admin", scope=SCOPE.ADMIN, action=ACTION.AUDIT)
        with self.app.test_request_context("/system/names/radius",
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertIn("enrollRADIUS", result["error"]["message"])

        # with an enrollRADIUS action, admins can access the RADIUS servers
        set_policy("admin", scope=SCOPE.ADMIN, action=[ACTION.AUDIT, "enrollRADIUS"])
        with self.app.test_request_context("/system/names/radius",
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertEqual(set(result["value"]), {"local", "remote"})

        self.setUp_user_realms()
        self.authenticate_selfservice_user()

        # without a user action, users can access the RADIUS servers
        with self.app.test_request_context("/system/names/radius",
                                           method="GET",
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertEqual(set(result["value"]), {"local", "remote"})

        # if a user policy is defined and enrollRADIUS is not allowed, users cannot access the RADIUS servers
        set_policy("user", scope=SCOPE.USER, action=ACTION.AUDIT)
        with self.app.test_request_context("/system/names/radius",
                                           method="GET",
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertIn("enrollRADIUS", result["error"]["message"])

        # with an enrollRADIUS action, users can access the RADIUS servers
        set_policy("user", scope=SCOPE.USER, action="enrollRADIUS")
        with self.app.test_request_context("/system/names/radius",
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertEqual(set(result["value"]), {"local", "remote"})

        delete_policy("user")
        delete_policy("admin")
        delete_radius("local")
        delete_radius("remote")

    def test_23_list_ca_connectors(self):
        cwd = os.getcwd()
        save_caconnector({'type': 'local',
                          'secret': 'value',
                          'caconnector': 'localCA',
                          "cakey": CAKEY,
                          "cacert": CACERT,
                          "openssl.cnf": OPENSSLCNF,
                          "WorkingDir": cwd + "/" + WORKINGDIR,
                          ATTR.TEMPLATE_FILE: "templates.yaml"})

        def _check_caconnector_response(response):
            value = json.loads(response.data.decode('utf8')).get("result")["value"]
            self.assertEqual(len(value), 1)
            self.assertEqual(value[0]["connectorname"], "localCA")
            self.assertEqual(value[0]["data"], {})
            self.assertEqual(set(value[0]["templates"].keys()), {"template3", "webserver", "user"})

        # cannot access the CA connector names without authorization
        with self.app.test_request_context("/system/names/caconnector",
                                           method="GET",
                                           headers={}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 401)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertIn("Missing Authorization header", result["error"]["message"])

        # if no admin policies are defined, admins can access the CA connectors
        with self.app.test_request_context("/system/names/caconnector",
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            _check_caconnector_response(res)

        # if an admin policy is defined and enrollCERTIFICATE is not allowed, admins cannot access the CA connectors
        set_policy("admin", scope=SCOPE.ADMIN, action=ACTION.AUDIT)
        with self.app.test_request_context("/system/names/caconnector",
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertIn("enrollCERTIFICATE", result["error"]["message"])

        # with an enrollCERTIFICATE action, admins can access the CA connectors
        set_policy("admin", scope=SCOPE.ADMIN, action=[ACTION.AUDIT, "enrollCERTIFICATE"])
        with self.app.test_request_context("/system/names/caconnector",
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            _check_caconnector_response(res)

        self.setUp_user_realms()
        self.authenticate_selfservice_user()

        # without a user action, users can access the CA connectors
        with self.app.test_request_context("/system/names/caconnector",
                                           method="GET",
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            _check_caconnector_response(res)

        # if a user policy is defined and enrollCERTIFICATE is not allowed, users cannot access the CA connectors
        set_policy("user", scope=SCOPE.USER, action=ACTION.AUDIT)
        with self.app.test_request_context("/system/names/caconnector",
                                           method="GET",
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 403)
            result = json.loads(res.data.decode('utf8')).get("result")
            self.assertIn("enrollCERTIFICATE", result["error"]["message"])

        # with an enrollCERTIFICATE action, users can access the CA connectors
        set_policy("user", scope=SCOPE.USER, action="enrollCERTIFICATE")
        with self.app.test_request_context("/system/names/caconnector",
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
            _check_caconnector_response(res)

        delete_policy("user")
        delete_policy("admin")
        delete_caconnector("localCA")

    def test_24_delete_user_cache_endpoint(self):
        UserCache(username='alice', used_login='', resolver='',
                  user_id='', timestamp=None).save()
        UserCache(username='bob', used_login='', resolver='',
                  user_id='', timestamp=None).save()

        count = UserCache.query.count()
        self.assertEqual(count, 2, f"expected 2 cache rows, found {count}")

        with self.app.test_request_context('/system/user-cache',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res.data)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertTrue(result["value"]["status"], result)

        remaining = UserCache.query.count()
        self.assertEqual(remaining, 0,
                         f"user-cache still contains {remaining} rows")

    def test_30_realms_with_nodes(self):
        nd1_uuid = "8e4272a9-9037-40df-8aa3-976e4a04b5a9"
        save_resolver({
            "resolver": "local_resolver_1",
            "type": "passwdresolver",
            "file": "/etc/passwd"
        })
        with self.app.test_request_context('/realm/realm_with_node',
                                           method='POST',
                                           json={"resolvers": ["local_resolver_1"],
                                                 "node.local_resolver_1": nd1_uuid,
                                                 "priority.local_resolver_1": 10},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertEqual(len(result["value"].get("added")), 1, result)
        delete_realm("realm_with_node")
        delete_resolver("local_resolver_1")

    def test_31_realm_node_api(self):
        nd1_uuid = "8e4272a9-9037-40df-8aa3-976e4a04b5a9"
        nd2_uuid = "d1d7fde6-330f-4c12-88f3-58a1752594bf"
        save_resolver({
            "resolver": "local_resolver_1",
            "type": "passwdresolver",
            "file": "/etc/passwd"
        })
        save_resolver({
            "resolver": "local_resolver_2",
            "type": "passwdresolver",
            "file": "/etc/passwd"
        })
        save_resolver({
            "resolver": "global_resolver",
            "type": "passwdresolver",
            "file": "/etc/passwd"
        })
        # first the request without the node uuid in the database
        with self.app.test_request_context(f'/realm/realm_with_node/node/{nd1_uuid}',
                                           method='POST',
                                           json=[{"name": "local_resolver_1",
                                                  "priority": 10}],
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400, res)
            self.assertEqual('ERR905: The given node does not exist!',
                             res.json.get("result").get("error").get("message"),
                             res.json)

        # add the node name and uuid to the database
        db.session.add(NodeName(id=nd1_uuid, name="Node1"))
        db.session.add(NodeName(id=nd2_uuid, name="Node2"))
        db.session.commit()

        # try a weird priority value
        with self.app.test_request_context(f'/realm/realm_with_node/node/{nd1_uuid}',
                                           method='POST',
                                           json={"resolver": [{"name": "local_resolver_1",
                                                               "priority": "foo"}]},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400, res)
            self.assertEqual('ERR905: Could not verify data in request!',
                             res.json.get("result").get("error").get("message"),
                             res.json)
        # missing resolver name
        with self.app.test_request_context(f'/realm/realm_with_node/node/{nd1_uuid}',
                                           method='POST',
                                           json={"resolver": [{"priority": "10"}]},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 400, res)
            self.assertEqual('ERR905: Could not verify data in request!',
                             res.json.get("result").get("error").get("message"),
                             res.json)

        # try to add a non-existing resolver
        with self.app.test_request_context(f'/realm/realm_with_node/node/{nd1_uuid}',
                                           method='POST',
                                           json={"resolver": [{"name": "unknown_resolver",
                                                               "priority": 10}]},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertEqual(0, len(result["value"].get("added")), result)
            self.assertEqual(1, len(result["value"].get("failed")), result)
            self.assertIn("unknown_resolver", result["value"]["failed"], result)

        realm = get_realms()
        self.assertIn("realm_with_node", realm, realm)
        self.assertEqual(0, len(realm["realm_with_node"]["resolver"]), realm)

        # add a resolver to the realm
        with self.app.test_request_context(f'/realm/realm_with_node/node/{nd1_uuid}',
                                           method='POST',
                                           json={"resolver": [{"name": "local_resolver_1",
                                                               "priority": 10}]},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertEqual(1, len(result["value"].get("added")), result)
            self.assertEqual(0, len(result["value"].get("failed")), result)
            self.assertIn("local_resolver_1", result["value"]["added"], result)

        realm = get_realms()
        self.assertIn("realm_with_node", realm, realm)
        reso1 = next(r for r in realm["realm_with_node"]["resolver"] if r["name"] == "local_resolver_1")
        self.assertEqual(10, reso1["priority"], reso1)
        self.assertEqual(nd1_uuid, reso1["node"], reso1)

        # add the same realm on a different node with no priority
        with self.app.test_request_context(f'/realm/realm_with_node/node/{nd2_uuid}',
                                           method='POST',
                                           json={"resolver": [{
                                               "name": "local_resolver_1",
                                               "priority": None}]},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertEqual(2, len(result["value"].get("added")), result)
            self.assertEqual(0, len(result["value"].get("failed")), result)
            self.assertIn("local_resolver_1", result["value"]["added"], result)

        realm = get_realms()
        self.assertIn("realm_with_node", realm, realm)
        res_list = [r for r in realm["realm_with_node"]["resolver"] if r["name"] == "local_resolver_1"]
        # there should be two entries with the same resolver name
        self.assertEqual(2, len(res_list), res_list)
        # both node uuids should be in the resolver list
        reso1n1 = next(r for r in res_list if r["node"] == nd1_uuid)
        reso1n2 = next(r for r in res_list if r["node"] == nd2_uuid)
        # check the corresponding priorities
        self.assertEqual(10, reso1n1["priority"], reso1n1)
        self.assertEqual(None, reso1n2["priority"], reso1n2)

        # update priority of the resolver on the second node
        with self.app.test_request_context(f'/realm/realm_with_node/node/{nd2_uuid}',
                                           method='POST',
                                           json={"resolver": [{"name": "local_resolver_1",
                                                               "priority": "5"}]},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertEqual(2, len(result["value"].get("added")), result)
            self.assertEqual(0, len(result["value"].get("failed")), result)
            self.assertIn("local_resolver_1", result["value"]["added"], result)

        realm = get_realms()
        self.assertIn("realm_with_node", realm, realm)
        res_list = [r for r in realm["realm_with_node"]["resolver"] if r["name"] == "local_resolver_1"]
        # there should be two entries with the same resolver name
        self.assertEqual(2, len(res_list), res_list)
        # both node uuids should be in the resolver list
        reso1n1 = next(r for r in res_list if r["node"] == nd1_uuid)
        reso1n2 = next(r for r in res_list if r["node"] == nd2_uuid)
        # check the corresponding priorities
        self.assertEqual(10, reso1n1["priority"], reso1n1)
        self.assertEqual(5, reso1n2["priority"], reso1n2)

        # add a second resolver on the second node. We need to specify the
        # existing resolver as well otherwise it would be removed
        with self.app.test_request_context(f'/realm/realm_with_node/node/{nd2_uuid}',
                                           method='POST',
                                           json={"resolver": [{"name": "local_resolver_1",
                                                               "priority": "5"},
                                                              {"name": "local_resolver_2",
                                                               "priority": "20"}]},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertEqual(3, len(result["value"].get("added")), result)
            self.assertEqual(0, len(result["value"].get("failed")), result)
            self.assertIn("local_resolver_1", result["value"]["added"], result)

        realm = get_realms()
        self.assertIn("realm_with_node", realm, realm)
        res_list = [r for r in realm["realm_with_node"]["resolver"] if r["name"] == "local_resolver_1"]
        # there should be two entries with the same resolver name
        self.assertEqual(2, len(res_list), res_list)
        # both node uuids should be in the resolver list
        reso1n1 = next(r for r in res_list if r["node"] == nd1_uuid)
        reso1n2 = next(r for r in res_list if r["node"] == nd2_uuid)
        # check the corresponding priorities
        self.assertEqual(10, reso1n1["priority"], reso1n1)
        self.assertEqual(5, reso1n2["priority"], reso1n2)
        reso2n2 = next(r for r in realm["realm_with_node"]["resolver"] if r["name"] == "local_resolver_2")
        self.assertEqual(20, reso2n2["priority"], reso2n2)

        # remove priority on resolver on node 1
        with self.app.test_request_context(f'/realm/realm_with_node/node/{nd1_uuid}',
                                           method='POST',
                                           json={"resolver": [{"name": "local_resolver_1"}]},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertEqual(3, len(result["value"].get("added")), result)
            self.assertEqual(0, len(result["value"].get("failed")), result)
            self.assertIn("local_resolver_1", result["value"]["added"], result)

        realm = get_realms()
        self.assertIn("realm_with_node", realm, realm)
        reso1 = next(r for r in realm["realm_with_node"]["resolver"] if r["node"] == nd1_uuid)
        self.assertEqual("local_resolver_1", reso1["name"], reso1)
        self.assertEqual(None, reso1["priority"], reso1)

        # add an unspecific resolver to the realm
        with self.app.test_request_context('/realm/realm_with_node',
                                           method='POST',
                                           json={"resolvers": "global_resolver"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertEqual(4, len(result["value"].get("added")), result)
            self.assertEqual(0, len(result["value"].get("failed")), result)
            self.assertIn("global_resolver", result["value"]["added"], result)

        realm = get_realms()
        reso1 = next(r for r in realm["realm_with_node"]["resolver"] if not r["node"])
        self.assertEqual("global_resolver", reso1["name"], reso1)
        self.assertEqual(None, reso1["priority"], reso1)

        # remove resolver_1 on node 2
        with self.app.test_request_context(f'/realm/realm_with_node/node/{nd2_uuid}',
                                           method='POST',
                                           json={"resolver": [{"name": "local_resolver_2",
                                                               "priority": "20"}]},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertEqual(3, len(result["value"].get("added")), result)
            self.assertEqual(0, len(result["value"].get("failed")), result)
            self.assertIn("local_resolver_1", result["value"]["added"], result)

        realm = get_realms()
        self.assertIn("realm_with_node", realm, realm)
        res_list = [r for r in realm["realm_with_node"]["resolver"] if r["name"] == "local_resolver_1"]
        # there should be two entries with the same resolver name
        self.assertEqual(1, len(res_list), res_list)
        # both node uuids should be in the resolver list
        reso1n1 = next(r for r in res_list if r["node"] == nd1_uuid)
        # check the corresponding priorities
        self.assertEqual(None, reso1n1["priority"], reso1n1)
        reso2n2 = next(r for r in realm["realm_with_node"]["resolver"] if r["name"] == "local_resolver_2")
        self.assertEqual(20, reso2n2["priority"], reso2n2)

        # remove resolver on node 1
        with self.app.test_request_context(f'/realm/realm_with_node/node/{nd1_uuid}',
                                           method='POST',
                                           json={"resolver": []},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)
            self.assertEqual(2, len(result["value"].get("added")), result)
            self.assertEqual(0, len(result["value"].get("failed")), result)
            self.assertIn("local_resolver_2", result["value"]["added"], result)

        realm = get_realms()
        self.assertIn("realm_with_node", realm, realm)
        res_list = [r for r in realm["realm_with_node"]["resolver"] if r["name"] == "local_resolver_1"]
        # there should be two entries with the same resolver name
        self.assertEqual(0, len(res_list), res_list)
        # both node uuids should be in the resolver list
        reso2n2 = next(r for r in realm["realm_with_node"]["resolver"] if r["name"] == "local_resolver_2")
        self.assertEqual(20, reso2n2["priority"], reso2n2)

        delete_realm("realm_with_node")
        delete_resolver("local_resolver_1")
        delete_resolver("local_resolver_2")
