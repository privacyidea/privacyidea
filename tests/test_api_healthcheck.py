import json
from contextlib import contextmanager
from typing import Optional
from .pkcs11mock import PKCS11Mock
from privacyidea.lib.policy import SCOPE, PolicyAction, delete_policy, enable_policy, get_policies, set_policy
from privacyidea.lib.resolver import delete_resolver, save_resolver
from privacyidea.lib.security.aeshsm import AESHardwareSecurityModule
from tests import ldap3mock
from tests.base import MyApiTestCase
from tests.test_api_validate import LDAPDirectory


@contextmanager
def setup_policy(name: str, *args, **kwargs):
    """Create a policy as specified, and delete it after the block is done."""
    r = set_policy(name, *args, **kwargs)
    assert r > 0, f"Failed creating policy {name!r}."
    try:
        yield
    finally:
        delete_policy(name)

@contextmanager
def setup_resolver(name: str, **kwargs):
    kwargs["resolver"] = name
    r = save_resolver(kwargs)
    assert r > 0, f"Failed creating resolver {name!r}."
    try:
        yield
    finally:
        delete_resolver(name)


class APIHealthcheckTestCase(MyApiTestCase):
    def test_livez(self):
        with self.app.test_request_context('/healthz/livez', method='GET'):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200, f"Expected status code 200, got {res.status_code}")
            result = res.json.get("result")
            self.assertIsNotNone(result, "Expected 'result' in response JSON, but got None")
            self.assertIn("value", result, f"Expected 'value' key in result, got {result}")
            self.assertEqual(result.get("value").get("status"), "OK",
                             f"Expected 'OK' as value, got {result.get('value')}")

    def test_startupz(self):
        def check_status(expected_status_code, expected_ready_status, app_ready_value):
            self.app.config['APP_READY'] = app_ready_value
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, expected_status_code,
                             f"Expected status code {expected_status_code}, got {res.status_code}")
            result = res.json.get("result")
            self.assertIsNotNone(result, "Expected JSON result, got None")
            self.assertIn("value", result, f"Expected 'value' in result, got {result}")
            self.assertEqual(result.get("value").get("status"), expected_ready_status,
                             f"Expected status '{expected_ready_status}', got {result.get('value').get('status')}")

        with self.app.test_request_context('/healthz/startupz', method='GET'):
            check_status(503, "not started", False)
            check_status(200, "started", True)

    def test_readyz_and_healthz(self):
        def check_status(expected_status_code, expected_ready_status, app_ready_value):
            with PKCS11Mock():
                hsm = AESHardwareSecurityModule({
                    "module": "testmodule",
                    "password": "test123!"
                })
                self.assertIsNotNone(hsm)
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
            check_status(503, "not ready", False)
            check_status(200, "ready", True)
        with self.app.test_request_context('/healthz/', method='GET'):
            check_status(503, "not ready", False)
            check_status(200, "ready", True)

    @ldap3mock.activate
    def test_resolversz(self):
        def check_resolvers(expected_status_code: int,
                            expected_status: Optional[str] = None,
                            ldap_expected_status: Optional[str] = None,
                            sql_expected_status: Optional[str] = None,
                            auth_token: Optional[str] = None) -> None:
            headers = {'Authorization': auth_token} if auth_token is not None else {}
            with self.app.test_request_context('/healthz/resolversz', method='GET', headers=headers):
                res = self.app.full_dispatch_request()
                assert res.status_code == expected_status_code, (f"Expected status code {expected_status_code}, "
                                                                 f"got {res.status_code}")

                if expected_status is None:
                    return

                result = res.json.get("result")
                assert result is not None, "Expected JSON result, got None"
                assert result.get("value").get("status") == expected_status, (
                    f"Expected '{expected_status}' status, "
                    f"got {result.get('value').get('status')}"
                )

                result_value = result.get("value")
                ldap_resolvers = result_value.get("ldapresolver")
                sql_resolvers = result_value.get("sqlresolver")

                if ldap_expected_status is None:
                    assert 'ldapresolver' not in result_value, "Expected missing 'ldapresolver' in result, but is present"
                else:
                    assert ldap_resolvers is not None, "Expected 'ldapresolver' in result, but got None"
                    assert all(status == ldap_expected_status for status in ldap_resolvers.values()), \
                        f"At least one LDAP resolver does not have '{ldap_expected_status}' status."

                if sql_expected_status is None:
                    assert 'sqlresolver' not in result_value, "Expected missing 'sqlresolver' in result, but is present"
                else:
                    assert sql_resolvers is not None, "Expected 'sqlresolver' in result, but got None"
                    assert all(status == sql_expected_status for status in sql_resolvers.values()), \
                        f"At least one SQL resolver does not have '{sql_expected_status}' status."

        @contextmanager
        def setup_test_resolvers():
            ldap3mock.setLDAPDirectory(LDAPDirectory)
            ldapr = setup_resolver("test_ldapresolver", type="ldapresolver",
                LDAPURI="ldap://localhost", LDAPBASE="o=test",
                BINDDN="cn=manager,ou=example,o=test", BINDPW="ldaptest",
                LOGINNAMEATTRIBUTE="cn", LDAPSEARCHFILTER="(cn=*)",
                MULTIVALUEATTRIBUTES='["groups"]', UIDTYPE="DN",
                USERINFO=json.dumps({
                    "username": "cn",
                    "phone": "telephoneNumber",
                    "mobile": "mobile",
                    "email": "mail",
                    "surname": "sn",
                    "groups": "memberOf",
                    "givenname": "givenName",
                }),
            )
            sqlr = setup_resolver("test_sqlresolver", type="sqlresolver",
                Driver="sqlite", Server="/tests/testdata/",
                Database="testuser.sqlite", Table="users",
                Encoding="utf8", Editable=True,
                Map=json.dumps({
                    "username": "username",
                    "userid": "id",
                    "email": "email",
                    "surname": "name",
                    "givenname": "givenname",
                    "password": "password",
                    "phone": "phone",
                    "mobile": "mobile",
                }),
            )
            with ldapr, sqlr:
                yield

        check_resolvers(200, "OK", ldap_expected_status="fail", sql_expected_status="fail")
        with setup_test_resolvers():
            check_resolvers(200, "OK", ldap_expected_status="OK", sql_expected_status="OK")

        with setup_policy("auth_for_resolvers", scope=SCOPE.AUTHZ,
                          action=f"{PolicyAction.REQUIRE_AUTH_FOR_RESOLVER_DETAILS}=true"):
            check_resolvers(200, "OK")
            check_resolvers(200, "OK", ldap_expected_status="fail", sql_expected_status="fail", auth_token=self.at)
            check_resolvers(401, auth_token="")

            with setup_test_resolvers():
                check_resolvers(200, "OK")
                check_resolvers(200, "OK", ldap_expected_status="OK", sql_expected_status="OK", auth_token=self.at)
                check_resolvers(401, auth_token="")
