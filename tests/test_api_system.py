import os

import json

from .base import MyApiTestCase

from privacyidea.lib.policy import PolicyClass, set_policy, delete_policy, ACTION, SCOPE
from privacyidea.lib.config import (set_privacyidea_config,
                                    delete_privacyidea_config, SYSCONF)
from privacyidea.lib.caconnector import save_caconnector, delete_caconnector
from privacyidea.lib.caconnectors.localca import ATTR
from privacyidea.lib.radiusserver import add_radius, delete_radius
from privacyidea.lib.resolver import save_resolver, delete_resolver, CENSORED
from .test_lib_resolver import LDAPDirectory, ldap3mock
from .test_lib_caconnector import CACERT, CAKEY, WORKINGDIR, OPENSSLCNF
from urllib.parse import urlencode

PWFILE = "tests/testdata/passwords"
POLICYFILE = "tests/testdata/policy.cfg"
POLICYEMPTY = "tests/testdata/policy_empty_file.cfg"


class APIConfigTestCase(MyApiTestCase):

    def test_00_get_empty_config(self):
        with self.app.test_request_context('/system/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
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
            self.assertTrue(res.status_code == 200, res)
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
            self.assertTrue(res.status_code == 200, res)
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
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(result["status"] is True, result)
            self.assertTrue(result["value"]["DefaultOtpLen"] == "insert",
                            result)

        with self.app.test_request_context('/system/DefaultMaxFailCount',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue(result["value"] == 1,result)

        with self.app.test_request_context('/system/DefaultMaxFailCount',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue(result["value"] is None, result)

        # test unknown parameter
        with self.app.test_request_context('/system/setDefault',
                                           data={"unknown": "xx"},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            # "unknown" is an unknown Default Parameter. So a ParamterError
            # is raised.
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

    def test_04_set_policy(self):
        with self.app.test_request_context('/policy/pol1',
                                           data={'action': "enroll",
                                                 'scope': "selfservice",
                                                 'realm': "r1",
                                                 'resolver': "test",
                                                 'user': ["admin"],
                                                 'time': "",
                                                 'client': "127.12.12.12",
                                                 'active': True},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertEqual(result['value']['setPolicy pol1'], 1, res.json)

        # Set a policy with a more complicated client which might interfere
        # with override client
        set_privacyidea_config(SYSCONF.OVERRIDECLIENT, "10.0.0.1")
        with self.app.test_request_context('/policy/pol1',
                                           data={'action': "enroll",
                                                 'scope': "selfservice",
                                                 'realm': "r1",
                                                 'resolver': "test",
                                                 'user': ["admin"],
                                                 'time': "",
                                                 'client': "10.0.0.0/8, "
                                                           "172.16.200.1",
                                                 'active': True},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json['result']
            self.assertTrue(result["status"], result)
            self.assertEqual(result['value']['setPolicy pol1'], 1, result)
        delete_privacyidea_config(SYSCONF.OVERRIDECLIENT)

        # setting policy with invalid name fails
        with self.app.test_request_context('/policy/invalid policy name',
                                           data={'action': "enroll",
                                                 'scope': "selfservice",
                                                 'client': "127.12.12.12",
                                                 'active': True},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            # An invalid policy name raises an exception
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

        # setting policy with an empty name
        with self.app.test_request_context('/policy/enroll',
                                           data={'scope': "selfservice",
                                                 'client': "127.12.12.12",
                                                 'active': True},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            # An invalid policy name raises an exception
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

    def test_05_get_policy(self):
        with self.app.test_request_context('/policy/pol1',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue("pol1" == result["value"][0].get("name"), res.data)

    def test_06_export_policy(self):
        with self.app.test_request_context('/policy/export/test.cfg',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            body = res.data
            self.assertTrue(b'name = pol1' in body, res.data)
            self.assertTrue(b"[pol1]" in body, res.data)

    def test_07_update_and_delete_policy(self):
        with self.app.test_request_context('/policy/pol_update_del',
                                           data={'action': "enroll",
                                                 'scope': "selfservice",
                                                 'realm': "r1",
                                                 'resolver': "test",
                                                 'user': "admin",
                                                 'time': "",
                                                 'client': "127.12.12.12",
                                                 'active': True},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue(result["value"]["setPolicy pol_update_del"] > 0,
                            res.data)

        # update policy
        with self.app.test_request_context('/policy/pol_update_del',
                                           data={'action': "enroll",
                                                 'scope': "selfservice",
                                                 'realm': "r1",
                                                 'client': "1.1.1.1"},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["value"]["setPolicy pol_update_del"] > 0,
                            res.data)

        # get policy
        with self.app.test_request_context('/policy/pol_update_del',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
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
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)

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
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue(result["value"] == [], result)

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
            self.assertTrue(res.status_code == 200, res)
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
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            data = result["value"]["testL"]["data"]
            self.assertEqual(data.get("BINDPW"), CENSORED)

        with self.app.test_request_context('/resolver/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
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
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertGreaterEqual(result["value"], 1, result)
            res_id = result["value"]

        with self.app.test_request_context('/resolver/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue("resolver1" in result["value"], result)
            self.assertTrue("filename" in result["value"]["resolver1"]["data"])

        # Get a non existing resolver
        with self.app.test_request_context('/resolver/unknown',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            # The value is empty
            self.assertTrue(result["value"] == {}, result)

        # Get only editable resolvers
        with self.app.test_request_context('/resolver/',
                                           method='GET',
                                           query_string=urlencode({
                                               "editable": "1"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            # The value is empty
            self.assertTrue(result["value"] == {}, result)

        # this will fetch all resolvers
        with self.app.test_request_context('/resolver/',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
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
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")
            self.assertTrue("resolver1" in value, value)

        # get a resolver name
        with self.app.test_request_context('/resolver/resolver1',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(result["status"] is True, result)
            self.assertTrue("resolver1" in result["value"], result)
            self.assertTrue("filename" in result["value"]["resolver1"]["data"])


        # get a resolver name
        with self.app.test_request_context('/resolver/resolver1',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue("resolver1" in result["value"], result)
            self.assertTrue("filename" in result["value"]["resolver1"]["data"])

        # delete the resolver
        with self.app.test_request_context('/resolver/resolver1',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(result["status"] is True, result)
            self.assertEqual(result["value"], res_id, result)

        # delete a non existing resolver
        with self.app.test_request_context('/resolver/xycswwf',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(result["status"] is True, result)
            # Trying to delete a non existing resolver returns -1
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
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            # The resolver was created. The ID of the resolver is returend.
            self.assertGreaterEqual(result["value"], 1, result)
            res_id = result["value"]

        # create a realm
        with self.app.test_request_context('/realm/{0!s}'.format(realmname),
                                           method='POST',
                                           data={"resolvers": resolvername},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            # The resolver was created
            self.assertTrue(len(result["value"].get("added")) == 1, result)
            self.assertTrue(len(result["value"].get("failed")) == 0, result)

        # create a realm with multiple resolvers
        with self.app.test_request_context('/realm/realm2',
                                           method='POST',
                                           json={"resolvers": [resolvername, "resolver2"]},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
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
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
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
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue("adminrealm" in result["value"], result)

        # try to delete the resolver in the realm
        with self.app.test_request_context('/resolver/{0!s}'.format(resolvername),
                                            method='DELETE',
                                            headers={'Authorization': self.at}):
            # The resolver must not be deleted, since it is contained in a realm
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

        # delete the realm
        with self.app.test_request_context('/realm/{0!s}'.format(realmname),
                                            method='DELETE',
                                            headers={'Authorization': self.at}):
            # The realm gets deleted
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            # The realm is successfully deleted: value is the id in
            # the db, should be >= 1
            self.assertGreaterEqual(result["value"], 1, result)

        # delete the second realm
        with self.app.test_request_context('/realm/realm2',
                                           method='DELETE',
                                           headers={'Authorization': self.at}):
            # The realm gets deleted
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
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
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
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
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)

        # create a realm
        with self.app.test_request_context('/realm/{0!s}'.format(realmname),
                                           method='POST',
                                           data={"resolvers": resolvername,
                                                 "priority.defresolver": 10},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"], result)

        # get the default realm
        with self.app.test_request_context('/defaultrealm',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue("defrealm" in result["value"], result)

        # clear the default realm
        with self.app.test_request_context('/defaultrealm',
                                            method='DELETE',
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)

        # get the default realm
        with self.app.test_request_context('/defaultrealm',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue(result["value"] == {}, result)

        # set the default realm
        with self.app.test_request_context('/defaultrealm/defrealm',
                                            method='POST',
                                            headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)


        # get the default realm
        with self.app.test_request_context('/defaultrealm',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            self.assertTrue(res.status_code == 200, res)
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue("defrealm" in result["value"], result)

    def test_11_import_policy(self):
        with self.app.test_request_context('/policy/import/policy.cfg',
                                           method='POST',
                                           data=dict(file=(POLICYFILE,
                                                           'policy.cfg')),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result["status"] is True, result)
            self.assertTrue(result["value"] == 2, result)
            # check if policies are there
            P = PolicyClass()
            p1 = P.match_policies(name="importpol1")
            self.assertTrue(len(p1) == 1, p1)
            p2 = P.match_policies(name="importpol2")
            self.assertTrue(len(p2) == 1, p2)

        # import empty file
        with self.app.test_request_context("/policy/import/"
                                           "policy_empty_file.cfg",
                                           method='POST',
                                           data=dict(file=(POLICYEMPTY,
                                                           "policy_empty_file.cfg")),
                                           headers={'Authorization': self.at}):

            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

    def test_12_test_check_policy(self):
        # test invalid policy name "check"
        with self.app.test_request_context('/policy/check',
                                           method='POST',
                                           data={"realm": "*",
                                                 "action": "action1, action2",
                                                 "scope": "scope1",
                                                 "user": "*, -user1",
                                                 "client": "172.16.0.0/16, "
                                                           "-172.16.1.1"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

        with self.app.test_request_context('/policy/pol1',
                                           method='POST',
                                           data={"realm": "*",
                                                 "action": "action1, action2",
                                                 "scope": "scope1",
                                                 "user": "*, -user1",
                                                 "client": "172.16.0.0/16, "
                                                           "-172.16.1.1"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")


        with self.app.test_request_context('/policy/pol2',
                                           method='POST',
                                           data={"realm": "*",
                                                 "action": "action3=value, "
                                                           "action4",
                                                 "scope": "scope1",
                                                 "user": "admin, superuser",
                                                 "client": "172.16.1.1"},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertTrue(res.status_code == 200, res)

        # CHECK: user=superuser, action=action1, client=172.16.1.1
        # is not allowed
        with self.app.test_request_context('/policy/check',
                                           method='GET',
                                           query_string=urlencode({"realm":
                                                                       "realm1",
                                                                   "action":
                                                                       "action1",
                                                                   "scope": "scope1",
                                                                   "user": "superuser",
                                                                   "client":
                                                                       "172.16.1.1"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertFalse(result.get("value").get("allowed"), result)

        # CHECK: user=superuser, action=action1, client=172.16.1.2
        # is allowed
        with self.app.test_request_context('/policy/check',
                                           method='GET',
                                           query_string=urlencode({"realm": "realm2",
                                                 "action": "action1",
                                                 "scope": "scope1",
                                                 "user": "superuser",
                                                 "client": "172.16.1.2"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value").get("allowed"), result)


        # CHECK: user=superuser, action=action3, client=172.16.1.2
        # is not allowed
        with self.app.test_request_context('/policy/check',
                                           method='GET',
                                           query_string=urlencode({"realm": "realm3",
                                                 "action": "action3",
                                                 "scope": "scope1",
                                                 "user": "superuser",
                                                 "client": "172.16.1.2"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertFalse(result.get("value").get("allowed"), result)


        # CHECK: user=superuser, action=action3, client=172.16.1.1
        # is allowed
        with self.app.test_request_context('/policy/check',
                                           method='GET',
                                           query_string=urlencode({"realm": "realm1",
                                                 "action": "action3",
                                                 "scope": "scope1",
                                                 "user": "superuser",
                                                 "client": "172.16.1.1"}),
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            self.assertTrue(result.get("value").get("allowed"), result)


    def test_13_get_policy_defs(self):
        with self.app.test_request_context('/policy/defs',
                                           method='GET',
                                           data={},
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
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
            self.assertTrue(res.status_code == 200, res)
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
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            conditions = result.get("value")
            self.assertIn("sections", conditions)
            self.assertIn("userinfo", conditions["sections"])
            self.assertIn("description", conditions["sections"]["userinfo"])
            self.assertIn("comparators", conditions)
            self.assertIn("contains", conditions["comparators"])
            self.assertIn("description", conditions["comparators"]["contains"])

    def test_14_enable_disable_policy(self):
        with self.app.test_request_context('/policy/pol2',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertTrue(res.status_code == 200, res)
            pol = result.get("value")
            self.assertTrue(pol[0].get("active"), pol[0])

        # Disable policy
        with self.app.test_request_context('/policy/disable/pol2',
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertTrue(res.status_code == 200, res)

        with self.app.test_request_context('/policy/pol2',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertTrue(res.status_code == 200, res)
            pol = result.get("value")
            self.assertFalse(pol[0].get("active"), pol[0])

        # enable Policy
        with self.app.test_request_context('/policy/enable/pol2',
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertTrue(res.status_code == 200, res)

        with self.app.test_request_context('/policy/pol2',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            result = res.json.get("result")
            self.assertTrue(res.status_code == 200, res)
            pol = result.get("value")
            self.assertTrue(pol[0].get("active"), pol[0])

    def test_15_get_documentation(self):
        with self.app.test_request_context('/system/documentation',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertEqual(res.mimetype, 'text/plain', res)
            self.assertTrue(b"privacyIDEA configuration documentation" in
                            res.data)

    def test_16_get_hsm(self):
        with self.app.test_request_context('/system/hsm',
                                           method='GET',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")
            self.assertTrue(value.get("is_ready"), value)

        # HSM is already set up. We do not need to set a password
        with self.app.test_request_context('/system/hsm',
                                           data={"password": "xx"},
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 400, res)

    def test_17_test_token_config(self):
        with self.app.test_request_context('/system/test/hotp',
                                           method='POST',
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
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
            self.assertTrue(res.status_code == 200, res)
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
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")
            # hex encoded value
            self.assertEqual(len(value), 44)
            # This is base64. We can decode
            import base64
            base64.b64decode(value)

    def test_19_get_gpg_keys(self):
        with self.app.test_request_context('/system/gpgkeys',
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            value = result.get("value")
            # We probably have no keys in here
            # But value returns a dictionary with the KeyID and "armor" and
            # "fingerprint"
            pass

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
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            pass

        with self.app.test_request_context('/resolver/{0}'.format(resolvername),
                                           method="GET",
                                           headers={'Authorization': self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json.get("result")
            params = result.get("value").get(resolvername).get("data")
            # the returned password is censored
            self.assertEqual(params.get("BINDPW"), CENSORED)
            # the intenal password is correct
            internal_resolver_config = self.app_context.g._request_local_store.get("config_object").resolver.get(resolvername)
            self.assertEqual(internal_resolver_config.get("data").get("BINDPW"), "ldaptest")

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

        def _check_caconnector_response(res):
            result = json.loads(res.data.decode('utf8')).get("result")
            value = result["value"]
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
