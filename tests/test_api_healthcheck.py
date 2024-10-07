from privacyidea.lib.resolver import save_resolver
from tests import ldap3mock
from tests.base import MyApiTestCase
from tests.test_api_validate import LDAPDirectory


class APIHealthcheckTestCase(MyApiTestCase):
    def test_healthz(self):
        def check_healthz_status(expected_status_code, expected_ready_status, app_ready_value):
            self.app.config['APP_READY'] = app_ready_value
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, expected_status_code,
                             f"Expected status code {expected_status_code}, got {res.status_code}")
            result = res.json.get("result")
            self.assertIsNotNone(result, "Expected JSON result, got None")
            self.assertIn("value", result, f"Expected 'value' in result, got {result}")
            self.assertEqual(result.get("value").get("status"), expected_ready_status,
                             f"Expected status '{expected_ready_status}', got {result.get('value').get('status')}")

        with self.app.test_request_context('/healthz/', method='GET'):
            check_healthz_status(503, "not healthy", False)
            check_healthz_status(200, "healthy", True)

    def test_livez(self):
        with self.app.test_request_context('/healthz/livez', method='GET'):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, f"Expected status code 200, got {res.status_code}")
            result = res.json.get("result")
            self.assertIsNotNone(result, "Expected 'result' in response JSON, but got None")
            self.assertIn("value", result, f"Expected 'value' key in result, got {result}")
            self.assertEqual(result.get("value"), "OK", f"Expected 'OK' as value, got {result.get('value')}")

    def test_readyz(self):
        def check_readyz_status(expected_status_code, expected_ready_status, app_ready_value):
            self.app.config['APP_READY'] = app_ready_value
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, expected_status_code,
                             f"Expected status code {expected_status_code}, got {res.status_code}")
            result = res.json.get("result")
            self.assertIsNotNone(result, "Expected JSON result, got None")
            self.assertIn("value", result, f"Expected 'value' in result, got {result}")
            self.assertEqual(result.get("value").get("status"), expected_ready_status,
                             f"Expected status '{expected_ready_status}', got {result.get('value').get('status')}")

        with self.app.test_request_context('/healthz/readyz', method='GET'):
            check_readyz_status(503, "not ready", False)
            check_readyz_status(200, "ready", True)

    @ldap3mock.activate
    def test_resolversz(self):
        def check_resolvers(res, expected_status_code, expected_status, ldap_expected_status,
                            sql_expected_status):
            assert res.status_code == expected_status_code, f"Expected status code {expected_status_code}, got {res.status_code}"
            result = res.json.get("result")
            assert result is not None, "Expected JSON result, got None"
            assert result.get("value").get(
                "status") == expected_status, f"Expected '{expected_status}' status, got {result.get('value').get('status')}"

            ldap_resolvers = result.get("value").get("ldapresolvers")
            sql_resolvers = result.get("value").get("sqlresolvers")

            assert ldap_resolvers is not None, "Expected 'ldapresolvers' in result, but got None"
            assert sql_resolvers is not None, "Expected 'sqlresolvers' in result, but got None"

            assert all(status == ldap_expected_status for status in
                       ldap_resolvers.values()), f"At least one LDAP resolver does not have '{ldap_expected_status}' status."
            assert all(status == sql_expected_status for status in
                       sql_resolvers.values()), f"At least one SQL resolver does not have '{sql_expected_status}' status."

        ldap3mock.setLDAPDirectory(LDAPDirectory)

        with self.app.test_request_context('/healthz/resolversz', method='GET'):
            res = self.app.full_dispatch_request()
            check_resolvers(res, 200, "OK", ldap_expected_status="fail", sql_expected_status="fail")

            ldapr = save_resolver({
                'LDAPURI': 'ldap://localhost',
                'LDAPBASE': 'o=test',
                'BINDDN': 'cn=manager,ou=example,o=test',
                'BINDPW': 'ldaptest',
                'LOGINNAMEATTRIBUTE': 'cn',
                'LDAPSEARCHFILTER': '(cn=*)',
                'MULTIVALUEATTRIBUTES': '["groups"]',
                'USERINFO': '{ "username": "cn",'
                            '"phone" : "telephoneNumber", '
                            '"mobile" : "mobile", '
                            '"email" : "mail", '
                            '"surname" : "sn", '
                            '"groups": "memberOf", '
                            '"givenname" : "givenName" }',
                'UIDTYPE': 'DN',
                "resolver": "test_ldapresolver",
                "type": "ldapresolver"
            })

            sqlr = save_resolver({
                'Driver': 'sqlite',
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
                             "mobile": "mobile"}',
                'resolver': "test_sqlresolver",
                'type': "sqlresolver"
            })

            self.assertGreater(ldapr, 0, "LDAP resolver creation failed.")
            self.assertGreater(sqlr, 0, "SQL resolver creation failed.")

            res = self.app.full_dispatch_request()
            check_resolvers(res, 200, "OK", ldap_expected_status="OK", sql_expected_status="OK")
