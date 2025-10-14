import copy
import json
from typing import Optional, Union

import mock
import responses
import pytest

from privacyidea.api.lib.utils import get_required
from privacyidea.lib.error import ResolverError, ParameterError
from privacyidea.lib.resolvers.EntraIDResolver import (EntraIDResolver, CLIENT_ID, TENANT, AUTHORITY, CLIENT_SECRET,
                                                       CLIENT_CREDENTIAL_TYPE, CLIENT_CERTIFICATE, PRIVATE_KEY_FILE,
                                                       CERTIFICATE_FINGERPRINT, ClientCredentialType,
                                                       PRIVATE_KEY_PASSWORD)
from privacyidea.lib.resolvers.HTTPResolver import (HTTPResolver, RequestConfig, EDITABLE, ATTRIBUTE_MAPPING,
                                                    METHOD, ENDPOINT, HEADERS, REQUEST_MAPPING,
                                                    BASE_URL, ERROR_RESPONSE, RESPONSE_MAPPING, HAS_ERROR_HANDLER,
                                                    CONFIG_AUTHORIZATION, PASSWORD, USERNAME, VERIFY_TLS, TLS_CA_PATH,
                                                    TIMEOUT, CONFIG_GET_USER_LIST, CONFIG_GET_USER_BY_ID,
                                                    CONFIG_GET_USER_BY_NAME, ADVANCED, CONFIG_CREATE_USER,
                                                    CONFIG_USER_AUTH, CONFIG_DELETE_USER, CONFIG_EDIT_USER, HTTPMethod)
from privacyidea.lib.resolvers.KeycloakResolver import KeycloakResolver, REALM
from tests.base import MyTestCase


class RequestConfigTestCase(MyTestCase):

    def test_01_init_success(self):
        # serialized dicts
        config_dict = {ENDPOINT: "http://example.com/users/{username}",
                       METHOD: "get",
                       HEADERS: '{"Content-Type": "application/json"}',
                       REQUEST_MAPPING: '{"customid": "{userid}", "accessKey": "secr3t!"}',
                       RESPONSE_MAPPING: '{"username": "{Username}", "email": "{Email}"}',
                       ERROR_RESPONSE: '{"success": false}'
                       }
        config = RequestConfig(config_dict, {}, {"userid": "1234", "username": "test"})
        self.assertTrue("http://example.com/users/test", config.endpoint)
        self.assertTrue(config_dict["method"], config.method)
        self.assertTrue(isinstance(config.headers, dict))
        self.assertEqual("application/json", config.headers["Content-Type"])
        self.assertTrue(isinstance(config.request_mapping, dict))
        self.assertEqual("1234", config.request_mapping["customid"])
        self.assertTrue(isinstance(config.response_mapping, dict))
        self.assertEqual("{Username}", config.response_mapping["username"])
        # error response is not set as the special error handling is not enabled
        self.assertFalse(config.has_error_handler)
        self.assertDictEqual({}, config.error_response)

        # dicts also works
        config_dict = {ENDPOINT: "http://example.com/users/{username}",
                       METHOD: "post",
                       HEADERS: {"Content-Type": "application/json"},
                       REQUEST_MAPPING: {"customid": "{userid}", "accessKey": "secr3t!"},
                       RESPONSE_MAPPING: {"username": "{Username}", "email": "{Email}"},
                       HAS_ERROR_HANDLER: True,
                       ERROR_RESPONSE: {"success": False}
                       }
        config = RequestConfig(config_dict, {}, {"userid": "1234", "username": "test"})
        self.assertTrue("http://example.com/users/test", config.endpoint)
        self.assertTrue(config_dict["method"], config.method)
        self.assertTrue(isinstance(config.headers, dict))
        self.assertEqual("application/json", config.headers["Content-Type"])
        self.assertTrue(isinstance(config.request_mapping, dict))
        self.assertEqual("1234", config.request_mapping["customid"])
        self.assertTrue(isinstance(config.response_mapping, dict))
        self.assertEqual("{Username}", config.response_mapping["username"])
        self.assertTrue(config.has_error_handler)
        self.assertDictEqual({"success": False}, config.error_response)

        # Empty strings for dicts are handled as empty dicts
        config_dict = {ENDPOINT: "http://example.com/users/{username}",
                       METHOD: "get",
                       HEADERS: '',
                       REQUEST_MAPPING: '',
                       RESPONSE_MAPPING: '',
                       HAS_ERROR_HANDLER: True,
                       ERROR_RESPONSE: ''
                       }
        config = RequestConfig(config_dict, {})
        self.assertDictEqual({}, config.headers)
        self.assertDictEqual({}, config.request_mapping)
        self.assertDictEqual({}, config.response_mapping)
        self.assertDictEqual({}, config.error_response)

        # different content type
        config_dict = {ENDPOINT: "http://example.com/checkPass",
                       METHOD: "post",
                       HEADERS: {"Content-Type": "application/x-www-form-urlencoded"},
                       REQUEST_MAPPING: "grant_type=password&client_id=admin-cli&username={username}&password={password}"
                       }
        config = RequestConfig(config_dict, {}, {"password": "1234", "username": "test"})
        self.assertEqual("grant_type=password&client_id=admin-cli&username=test&password=1234",
                         config.request_mapping)

    def test_02_init_invalid_params(self):
        # Invalid method
        config_dict = {ENDPOINT: "http://example.com/users/{username}",
                       METHOD: "invalid",
                       HEADERS: {"Content-Type": "application/json"},
                       REQUEST_MAPPING: {"customid": "{userid}", "accessKey": "secr3t!"},
                       RESPONSE_MAPPING: {"username": "{Username}", "email": "{Email}"},
                       HAS_ERROR_HANDLER: True,
                       ERROR_RESPONSE: {"success": False}
                       }
        self.assertRaises(ParameterError, RequestConfig, config_dict, {}, {"userid": "1234", "username": "test"})
        config_dict[METHOD] = "get"

        # Invalid headers JSON format
        config_dict[HEADERS] = "{'Content-Type': 'application/json'}"
        self.assertRaises(ParameterError, RequestConfig, config_dict, {}, {"userid": "1234", "username": "test"})
        config_dict[HEADERS] = {"Content-Type": "application/json"}

        # Invalid request mapping JSON format
        config_dict[RESPONSE_MAPPING] = '{"customid": "{userid}", "exact": True}'
        self.assertRaises(ParameterError, RequestConfig, config_dict, {}, {"userid": "1234", "username": "test"})
        config_dict[REQUEST_MAPPING] = {"customid": "{userid}", "accessKey": "secr3t!"}

        # Invalid response mapping JSON format
        config_dict[RESPONSE_MAPPING] = '{"username": "{Username}"; "email": "{Email}"}'
        self.assertRaises(ParameterError, RequestConfig, config_dict, {}, {"userid": "1234", "username": "test"})
        # Invalid datatype
        config_dict[RESPONSE_MAPPING] = ["username", "{Username}", "email", "{Email}"]
        self.assertRaises(ParameterError, RequestConfig, config_dict, {}, {"userid": "1234", "username": "test"})
        config_dict[RESPONSE_MAPPING] = '{"username": "{Username}", "email": "{Email}"}'

        # Invalid error response
        config_dict[ERROR_RESPONSE] = '{"success": False}'
        self.assertRaises(ParameterError, RequestConfig, config_dict, {}, {"userid": "1234", "username": "test"})
        # invalid datatype
        config_dict[ERROR_RESPONSE] = ["success", False]
        self.assertRaises(ParameterError, RequestConfig, config_dict, {}, {"userid": "1234", "username": "test"})

    def test_03_init_missing_params(self):
        # method is required
        config_dict = {ENDPOINT: "http://example.com/users/{username}",
                       HEADERS: {"Content-Type": "application/json"},
                       REQUEST_MAPPING: {"customid": "{userid}", "accessKey": "secr3t!"},
                       RESPONSE_MAPPING: {"username": "{Username}", "email": "{Email}"},
                       HAS_ERROR_HANDLER: True,
                       ERROR_RESPONSE: {"success": False}
                       }
        self.assertRaises(ParameterError, RequestConfig, config_dict, {}, {"userid": "1234", "username": "test"})
        config_dict[METHOD] = "get"

        # endpoint is required
        del config_dict[ENDPOINT]
        self.assertRaises(ParameterError, RequestConfig, config_dict, {}, {"userid": "1234", "username": "test"})


class HTTPResolverTestCase(MyTestCase):
    ENDPOINT = 'http://localhost:8080/get-data'
    METHOD = responses.GET
    REQUEST_MAPPING = """
        {"id": "{userid}"}
    """
    HEADERS = """
        {"Content-Type": "application/json", "charset": "UTF-8"}
    """
    RESPONSE_MAPPING = """
        {
            "username": "{data.the_username}",
            "email": "{data.the_email}",
            "mobile": "{data.the_phones.mobile}",
            "a_static_key": "a static value"
        }
    """
    HAS_SPECIAL_ERROR_HANDLER = True
    ERROR_RESPONSE_MAPPING = """
        {"success": false}
    """

    BODY_RESPONSE_OK = """
    {
        "success": true,
        "data": {
            "the_username": "PepePerez",
            "the_email": "pepe@perez.com",
            "the_full_name": "Pepe Perez",
            "the_phones": {
                "mobile": "+1123568974",
                "other": "+1154525894"
            }
        }
    }
    """

    BODY_RESPONSE_NOK = """
    {
        "success": false,
        "data": null
    }
    """

    def setUp(self):
        self.basic_config = {'endpoint': self.ENDPOINT,
                             'method': self.METHOD,
                             'headers': self.HEADERS,
                             'requestMapping': self.REQUEST_MAPPING,
                             'responseMapping': self.RESPONSE_MAPPING,
                             'hasSpecialErrorHandler': self.HAS_SPECIAL_ERROR_HANDLER,
                             'errorResponse': self.ERROR_RESPONSE_MAPPING}

        self.advanced_config = {BASE_URL: "https://example.com", EDITABLE: True,
                                ATTRIBUTE_MAPPING: {"username": "login", "userid": "id", "givenname": "first_name",
                                                    "surname": "last_name"},
                                CONFIG_GET_USER_BY_ID: {METHOD: HTTPMethod.GET.value, ENDPOINT: "/users/{userid}",
                                                        HAS_ERROR_HANDLER: True, ERROR_RESPONSE: '{"success": false}'},
                                CONFIG_GET_USER_BY_NAME: {METHOD: HTTPMethod.GET.value, ENDPOINT: "/users/{username}",
                                                          HAS_ERROR_HANDLER: True,
                                                          ERROR_RESPONSE: '{"success": false}'},
                                CONFIG_GET_USER_LIST: {METHOD: HTTPMethod.GET.value, ENDPOINT: "/users",
                                                       HAS_ERROR_HANDLER: True, ERROR_RESPONSE: '{"success": false}'},
                                CONFIG_CREATE_USER: {METHOD: HTTPMethod.POST.value, ENDPOINT: "/users",
                                                     REQUEST_MAPPING: '{"enabled": true}', HAS_ERROR_HANDLER: True,
                                                     ERROR_RESPONSE: '{"success": false}'},
                                CONFIG_EDIT_USER: {METHOD: HTTPMethod.PUT.value, ENDPOINT: "/users/{userid}",
                                                   HAS_ERROR_HANDLER: True, ERROR_RESPONSE: '{"success": false}'},
                                CONFIG_DELETE_USER: {METHOD: HTTPMethod.DELETE.value, ENDPOINT: "/users/{userid}",
                                                     HAS_ERROR_HANDLER: True, ERROR_RESPONSE: '{"success": false}'},
                                CONFIG_USER_AUTH: {METHOD: HTTPMethod.POST.value, ENDPOINT: "/auth",
                                                   REQUEST_MAPPING: '{"grant_type": "password", "username": "{username}", "password": "{password}"}',
                                                   RESPONSE_MAPPING: '{"access_token": "{access_token}"}',
                                                   HAS_ERROR_HANDLER: True, ERROR_RESPONSE: '{"success": false}'}
                                }

    def test_01_load_basic_config_success(self):
        # Test with valid data
        instance = HTTPResolver()
        instance.loadConfig(self.basic_config)
        rid = instance.getResolverId()
        self.assertEqual(rid, self.ENDPOINT)
        r_type = instance.getResolverClassDescriptor()
        self.assertTrue("httpresolver" in r_type)
        r_type = instance.getResolverDescriptor()
        self.assertTrue("httpresolver" in r_type)
        r_type = instance.getResolverType()
        self.assertEqual("httpresolver", r_type)
        self.assertEqual(self.ENDPOINT, instance.config_get_user_by_id.get(ENDPOINT))
        self.assertEqual(self.METHOD, instance.config_get_user_by_id.get(METHOD))
        self.assertEqual(self.RESPONSE_MAPPING, instance.config_get_user_by_id.get(RESPONSE_MAPPING))
        self.assertEqual(self.REQUEST_MAPPING, instance.config_get_user_by_id.get(REQUEST_MAPPING))
        self.assertEqual(self.HEADERS, instance.config_get_user_by_id.get(HEADERS))
        self.assertTrue(instance.config_get_user_by_id.get(HAS_ERROR_HANDLER))
        self.assertEqual(self.ERROR_RESPONSE_MAPPING, instance.config_get_user_by_id.get(ERROR_RESPONSE))

        # Minimal config
        params = {
            'endpoint': self.ENDPOINT,
            'method': self.METHOD,
            'responseMapping': self.RESPONSE_MAPPING
        }
        instance = HTTPResolver()
        instance.loadConfig(params)
        self.assertEqual(self.ENDPOINT, instance.config_get_user_by_id.get(ENDPOINT))
        self.assertEqual(self.METHOD, instance.config_get_user_by_id.get(METHOD))
        self.assertEqual(self.RESPONSE_MAPPING, instance.config_get_user_by_id.get(RESPONSE_MAPPING))

        # Also pass empty advanced parameters should still take the basic params
        params = {
            'endpoint': self.ENDPOINT,
            'method': self.METHOD,
            'responseMapping': self.RESPONSE_MAPPING,
            CONFIG_GET_USER_BY_ID: {}
        }
        instance = HTTPResolver()
        instance.loadConfig(params)
        self.assertEqual(self.ENDPOINT, instance.config_get_user_by_id.get(ENDPOINT))
        self.assertEqual(self.METHOD, instance.config_get_user_by_id.get(METHOD))
        self.assertEqual(self.RESPONSE_MAPPING, instance.config_get_user_by_id.get(RESPONSE_MAPPING))

    def test_02_load_basic_config_fails(self):
        resolver = HTTPResolver()
        params = {
            'endpoint': self.ENDPOINT,
            'method': self.METHOD,
            'headers': self.HEADERS,
            'requestMapping': self.REQUEST_MAPPING,
            'responseMapping': self.RESPONSE_MAPPING,
            'hasSpecialErrorHandler': self.HAS_SPECIAL_ERROR_HANDLER,
            'errorResponse': self.ERROR_RESPONSE_MAPPING
        }

        # Missing parameters
        del params['endpoint']
        self.assertRaises(ParameterError, resolver.loadConfig, params)
        params['endpoint'] = self.ENDPOINT
        del params['method']
        self.assertRaises(ParameterError, resolver.loadConfig, params)
        params['method'] = self.METHOD
        del params['responseMapping']
        self.assertRaises(ParameterError, resolver.loadConfig, params)
        params['responseMapping'] = self.RESPONSE_MAPPING

    def test_03_load_advanced_config_success(self):
        resolver = HTTPResolver()
        config = {BASE_URL: "https://example.com/api",
                  ATTRIBUTE_MAPPING: {"username": "login", "userid": "id"},
                  HEADERS: '{"Content-Type": "application/json"}',
                  EDITABLE: "True",
                  VERIFY_TLS: "True",
                  TLS_CA_PATH: "/path/to/ca.crt",
                  TIMEOUT: "30",
                  USERNAME: "testuser",
                  PASSWORD: "testpassword",
                  CONFIG_AUTHORIZATION: {METHOD: "POST", ENDPOINT: "https://example.com/auth",
                                         HEADERS: '{"Content-Type": "application/x-www-form-urlencoded"}',
                                         REQUEST_MAPPING: "grant_type=password&username={username}&password={password}",
                                         RESPONSE_MAPPING: '{"Authorization": "Baerer {access_token}"}',
                                         HAS_ERROR_HANDLER: True, ERROR_RESPONSE: '{"success": false}'},
                  CONFIG_GET_USER_LIST: {METHOD: "GET", ENDPOINT: "https://example.com/api/users"},
                  CONFIG_GET_USER_BY_ID: {METHOD: "GET", ENDPOINT: "https://example.com/api/users/{userid}"},
                  CONFIG_GET_USER_BY_NAME: {METHOD: "GET", ENDPOINT: "https://example.com/api/users",
                                            REQUEST_MAPPING: '{"username": "{username}", "exact": true}'}}

        resolver.loadConfig(config)
        self.assertDictEqual({"Content-Type": "application/json"}, resolver.headers)
        self.assertTrue(resolver.editable)
        self.assertEqual(config[TLS_CA_PATH], resolver.tls)
        self.assertEqual(30, resolver.timeout)

        # Pass with different datatypes
        config[HEADERS] = {"Content-Type": "application/json"}
        config[VERIFY_TLS] = False
        config[EDITABLE] = True
        config[TIMEOUT] = 60
        resolver.loadConfig(config)
        self.assertDictEqual({"Content-Type": "application/json"}, resolver.headers)
        self.assertTrue(resolver.editable)
        self.assertFalse(resolver.tls)
        self.assertEqual(60, resolver.timeout)

        # Empty string for headers is handled as empty dict
        config[HEADERS] = ''
        resolver.loadConfig(config)
        self.assertDictEqual({}, resolver.headers)

    def test_04_load_advanced_config_fails(self):
        config = {BASE_URL: "https://example.com/api",
                  ATTRIBUTE_MAPPING: {"username": "login", "userid": "id"},
                  CONFIG_GET_USER_BY_ID: {METHOD: "GET", ENDPOINT: "https://example.com/api/users/{userid}"},
                  HEADERS: '{"Content-Type": "application/json"}',
                  EDITABLE: "True",
                  VERIFY_TLS: "True",
                  TIMEOUT: "30"}
        # check that this is a valid config
        HTTPResolver().loadConfig(config)

        # Invalid JSON formats
        # Attribute mapping
        config[ATTRIBUTE_MAPPING] = "{'username': 'login', 'userid': 'id'}"
        self.assertRaises(ParameterError, HTTPResolver().loadConfig, config)
        del config[ATTRIBUTE_MAPPING]
        # header
        config[HEADERS] = "{'Content-Type': 'application/json'}"
        self.assertRaises(ParameterError, HTTPResolver().loadConfig, config)
        del config[HEADERS]
        # config user auth
        config[CONFIG_USER_AUTH] = ('{"endpoint": "/auth", "method": "post", "hasSpecialErrorHandler": True}')
        self.assertRaises(ParameterError, HTTPResolver().loadConfig, config)
        del config[CONFIG_USER_AUTH]

        # Invalid timeout
        config[TIMEOUT] = "30.5"
        self.assertRaises(ParameterError, HTTPResolver().loadConfig, config)

    @responses.activate
    def test_05_get_user_list(self):
        # Basic resolver without user list config returns empty list
        instance = HTTPResolver()
        instance.loadConfig(self.basic_config)
        users = instance.getUserList()
        self.assertEqual(len(users), 0)

        # success
        instance.loadConfig(self.advanced_config)
        responses.add(responses.GET, "https://example.com/users", status=200,
                      body="""[{"login": "testuser", "first_name": "Test", "last_name": "User", "id": "1234", "businessPhone": "+1234567890"},
                                {"login": "corny", "first_name": "Corny", "last_name": "Meier", "id": "5678"}]""")
        users = instance.getUserList()
        self.assertEqual(len(users), 2)
        self.assertEqual(users[0]['username'], 'testuser')
        self.assertEqual(users[0]['givenname'], 'Test')
        self.assertEqual(users[0]['surname'], 'User')
        self.assertEqual(users[0]['userid'], '1234')
        self.assertEqual(4, len(users[0]))

        # success with filter
        responses.add(responses.GET, "https://example.com/users?first_name=Test", status=200,
                      body="""[{"login": "testuser", "first_name": "Test", "last_name": "User", "id": "1234"}]""")
        users = instance.getUserList({"givenname": "Test", "favorite_color": "blue"})
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]['username'], 'testuser')

        # fails
        responses.add(responses.GET, "https://example.com/users", status=400,
                      body="""{"error": "Bad Request", "message": "Invalid request"}""")
        self.assertRaises(ResolverError, instance.getUserList)

        # custom error handling
        responses.add(responses.GET, "https://example.com/users", status=200, body="""{"success": false}""")
        self.assertRaises(ResolverError, instance.getUserList)

    @responses.activate
    def test_06_get_username(self):
        # Basic resolver
        responses.add(self.METHOD, self.ENDPOINT, status=200, adding_headers=json.loads(self.HEADERS),
                      body=self.BODY_RESPONSE_OK)
        instance = HTTPResolver()
        instance.loadConfig(self.basic_config)
        username = instance.getUsername('pepe_perez')
        self.assertEqual(username, 'PepePerez')

        # Advanced resolver success
        resolver = HTTPResolver()
        resolver.loadConfig(self.advanced_config)
        responses.add(responses.GET, "https://example.com/users/1234", status=200,
                      body="""{"login": "testuser", "first_name": "Test", "last_name": "User", "id": "1234"}""")
        username = resolver.getUsername('1234')
        self.assertEqual('testuser', username)

        # Error
        responses.add(responses.GET, "https://example.com/users/1234", status=404,
                      body="""{"error": "Not Found"}""")
        self.assertEqual("", resolver.getUsername('1234'))

        # Custom error handling
        responses.add(responses.GET, "https://example.com/users/1234", status=200,
                      body="""{"success": false}""")
        self.assertEqual("", resolver.getUsername('1234'))

    @responses.activate
    def test_07_get_user_id(self):
        # Basic resolver (no get user by name config) only echos the username
        instance = HTTPResolver()
        instance.loadConfig(self.basic_config)
        userid = instance.getUserId('pepe_perez')
        self.assertEqual(userid, 'pepe_perez')

        # success
        resolver = HTTPResolver()
        resolver.loadConfig(self.advanced_config)
        responses.add(responses.GET, "https://example.com/users/testuser", status=200,
                      body="""{"login": "testuser", "first_name": "Test", "last_name": "User", "id": "1234"}""")
        user_id = resolver.getUserId("testuser")
        self.assertEqual("1234", user_id)

        # Error
        responses.add(responses.GET, "https://example.com/users/testuser", status=404,
                      body="""{"error": "Not Found"}""")
        self.assertEqual("", resolver.getUserId('testuser'))

        # Custom error handling
        responses.add(responses.GET, "https://example.com/users/testuser", status=200,
                      body="""{"success": false}""")
        self.assertEqual("", resolver.getUserId('testuser'))

    def test_08_get_resolver_id(self):
        instance = HTTPResolver()
        rid = instance.getResolverId()
        self.assertEqual(rid, "")
        instance.loadConfig(self.basic_config)
        rid = instance.getResolverId()
        self.assertEqual(rid, self.ENDPOINT)

    @responses.activate
    def test_09_get_user(self):
        responses.add(
            self.METHOD,
            self.ENDPOINT,
            status=200,
            adding_headers=json.loads(self.HEADERS),
            body=self.BODY_RESPONSE_OK
        )
        responses.add(
            responses.POST,
            self.ENDPOINT,
            status=200,
            adding_headers=json.loads(self.HEADERS),
            body=self.BODY_RESPONSE_OK
        )
        user_id = 'PepePerez'

        # Test with valid data (method get)
        instance = HTTPResolver()
        instance.loadConfig(self.basic_config)
        config = RequestConfig(instance.config_get_user_by_id, instance.headers, {"{userid}": user_id})
        response = instance._get_user(user_id, config)
        self.assertEqual(response.get('username'), 'PepePerez')
        self.assertEqual(response.get('email'), 'pepe@perez.com')
        self.assertEqual(response.get('mobile'), '+1123568974')
        self.assertEqual(response.get('a_static_key'), 'a static value')

        # Test with valid data (method post)
        instance = HTTPResolver()
        instance.loadConfig({
            'endpoint': self.ENDPOINT,
            'method': 'POST',
            'requestMapping': self.REQUEST_MAPPING,
            'headers': self.HEADERS,
            'responseMapping': self.RESPONSE_MAPPING,
            'hasSpecialErrorHandler': self.HAS_SPECIAL_ERROR_HANDLER,
            'errorResponse': self.ERROR_RESPONSE_MAPPING
        })
        config = RequestConfig(instance.config_get_user_by_id, instance.headers, {"{userid}": user_id})
        response = instance._get_user(user_id, config)
        self.assertEqual(response.get('username'), 'PepePerez')
        self.assertEqual(response.get('email'), 'pepe@perez.com')
        self.assertEqual(response.get('mobile'), '+1123568974')
        self.assertEqual(response.get('a_static_key'), 'a static value')

    @responses.activate
    def test_10_get_user_special_error_handling(self):
        responses.add(
            self.METHOD,
            self.ENDPOINT,
            status=200,
            adding_headers=json.loads(self.HEADERS),
            body=self.BODY_RESPONSE_NOK
        )
        instance = HTTPResolver()
        instance.loadConfig(self.basic_config)
        config = RequestConfig(instance.config_get_user_by_id, instance.headers, {"{userid}": "PepePerez"})
        self.assertDictEqual({}, instance._get_user(user_identifier='PepePerez', config=config))

    @responses.activate
    def test_11_get_user_internal_error(self):
        responses.add(
            self.METHOD,
            self.ENDPOINT,
            status=500,
            adding_headers=json.loads(self.HEADERS),
        )
        instance = HTTPResolver()
        instance.loadConfig(self.basic_config)
        config = RequestConfig(instance.config_get_user_by_id, instance.headers, {"{userid}": "PepePerez"})
        self.assertDictEqual({}, instance._get_user(user_identifier='PepePerez', config=config))

    @responses.activate
    def test_12_testconnection_basic(self):
        responses.add(
            self.METHOD,
            self.ENDPOINT,
            status=200,
            adding_headers=json.loads(self.HEADERS),
            body=self.BODY_RESPONSE_OK
        )

        param = {
            'endpoint': self.ENDPOINT,
            'method': self.METHOD,
            'requestMapping': self.REQUEST_MAPPING,
            'headers': self.HEADERS,
            'responseMapping': self.RESPONSE_MAPPING,
            'hasSpecialErrorHandler': self.HAS_SPECIAL_ERROR_HANDLER,
            'errorResponse': self.ERROR_RESPONSE_MAPPING,
            'testUser': 'PepePerez'
        }
        success, description = HTTPResolver.testconnection(param)
        self.assertTrue(success)
        self.assertIn('Resolver config seems to be OK', description)
        # Check which configs were tested
        self.assertIn("Get user by name", description)
        self.assertIn("User List", description)
        self.assertNotIn("Get user by id", description)
        self.assertNotIn("Authorization", description)

        # Test with invalid params
        responses.add(
            self.METHOD,
            self.ENDPOINT,
            status=200,
            adding_headers=json.loads(self.HEADERS),
            body=self.BODY_RESPONSE_NOK
        )
        invalid_params = param.copy()
        invalid_params[METHOD] = None
        success, _ = HTTPResolver.testconnection(invalid_params)
        self.assertFalse(success)

    @responses.activate
    def test_13_testconnection_advanced(self):
        # --- success ---
        params = {BASE_URL: "https://example.com/api",
                  HEADERS: '{"Content-Type": "application/json"}',
                  CONFIG_AUTHORIZATION: {METHOD: "POST", ENDPOINT: "https://example.com/auth",
                                         REQUEST_MAPPING: '{"username": "{username}", "password": "{password}"}',
                                         RESPONSE_MAPPING: '{"access_token": "Baerer {access_token}"}'},
                  CONFIG_USER_AUTH: {METHOD: "POST", ENDPOINT: "https://example.com/auth",
                                     REQUEST_MAPPING: '{"username": "{username}", "password": "{password}"}'},
                  CONFIG_GET_USER_BY_ID: {METHOD: "GET", ENDPOINT: "/users/{userid}"},
                  CONFIG_GET_USER_BY_NAME: {METHOD: "GET", ENDPOINT: "/user",
                                            REQUEST_MAPPING: '{"login_name": "{username}", "exact": true}'},
                  CONFIG_GET_USER_LIST: {METHOD: "GET", ENDPOINT: "/users"},
                  EDITABLE: True,
                  CONFIG_CREATE_USER: {METHOD: "POST", ENDPOINT: "/users"},
                  CONFIG_EDIT_USER: {METHOD: "PUT", ENDPOINT: "/users/{userid}"},
                  CONFIG_DELETE_USER: {METHOD: "DELETE", ENDPOINT: "/users/{userid}"},
                  ATTRIBUTE_MAPPING: {"username": "login", "userid": "id", "givenname": "first_name",
                                      "surname": "last_name", "mail": "email"},
                  VERIFY_TLS: True,
                  TIMEOUT: "60"
                  }

        # Mock user and admin auth endpoint
        responses.add(
            responses.POST,
            "https://example.com/auth",
            status=200,
            body="""{"access_token": "123456789", "expires_in": 3600, "token_type": "Bearer"}"""
        )
        # Mock user list endpoint
        responses.add(
            responses.GET,
            "https://example.com/api/users",
            status=200,
            body="""[{"login": "hans", "id": "123"}, {"login": "lee", "id": "456"}]"""
        )
        # Mock get user by name endpoint
        responses.add(
            responses.GET,
            "https://example.com/api/user",
            status=200,
            body="""{"login": "hans", "id": "123"}"""
        )
        # Mock get user by id endpoint
        responses.add(
            responses.GET,
            "https://example.com/api/users/123",
            status=200,
            body="""{"login": "hans", "id": "123"}"""
        )

        # Add test user params
        params['test_username'] = 'hans'
        params['test_userid'] = '123'
        success, description = HTTPResolver.testconnection(params)
        self.assertTrue(success)
        self.assertIn("Resolver config seems to be OK", description)
        # Check which configs were tested
        self.assertIn("Authorization", description)
        self.assertIn("Get user by name", description)
        self.assertIn("Get user by ID", description)
        self.assertIn("User List", description)

        # --- Fails ----
        # Invalid configs
        params[CONFIG_CREATE_USER] = {METHOD: "get", ENDPOINT: "/users", REQUEST_MAPPING: "{'id': '{userid}'}"}
        success, description = HTTPResolver.testconnection(params)
        self.assertFalse(success)
        self.assertIn("Failed to load create user config", description)
        del params[CONFIG_CREATE_USER]

        params[CONFIG_EDIT_USER] = {ENDPOINT: "/users/{userid}"}
        success, description = HTTPResolver.testconnection(params)
        self.assertFalse(success)
        self.assertIn("Failed to load edit user config", description)
        del params[CONFIG_EDIT_USER]

        params[CONFIG_DELETE_USER] = {METHOD: "get"}
        success, description = HTTPResolver.testconnection(params)
        self.assertFalse(success)
        self.assertIn("Failed to load delete user config", description)
        del params[CONFIG_DELETE_USER]

        params[CONFIG_USER_AUTH] = {METHOD: "get", ENDPOINT: "/auth",
                                    REQUEST_MAPPING: "{'username': '{username}', 'password': '{password}'}"}
        success, description = HTTPResolver.testconnection(params)
        self.assertFalse(success)
        self.assertIn("Failed to load config to check user password", description)
        del params[CONFIG_USER_AUTH]

        # Mock error for user list
        responses.add(
            responses.GET,
            "https://example.com/api/users",
            status=400,
            body="""{"error": "Bad Request", "message": "Invalid request"}"""
        )
        success, description = HTTPResolver.testconnection(params)
        self.assertFalse(success)
        self.assertIn("Failed to get user list", description)

        # No user found for name without error
        responses.add(
            responses.GET,
            "https://example.com/api/user",
            status=200,
            body="""{}"""
        )
        success, description = HTTPResolver.testconnection(params)
        self.assertFalse(success)
        self.assertIn("No user found for username 'hans'", description)
        # No user found for name with error
        responses.add(
            responses.GET,
            "https://example.com/api/user",
            status=400,
            body="""{"error": "Not Found", "message": "User not found"}"""
        )
        success, description = HTTPResolver.testconnection(params)
        self.assertFalse(success)
        self.assertIn("No user found for username 'hans'", description)

        # passed username differs from resolved one
        params['test_username'] = 'lee'
        success, description = HTTPResolver.testconnection(params)
        self.assertFalse(success)
        self.assertIn("Defined username 'lee' does not match resolved username 'hans'", description)
        params['test_username'] = 'hans'  # Reset to valid username

        # No user found for id without error
        responses.add(
            responses.GET,
            "https://example.com/api/users/123",
            status=200,
            body="""{}"""
        )
        success, description = HTTPResolver.testconnection(params)
        self.assertFalse(success)
        self.assertIn("No user found for user ID '123'", description)
        # No user found for id with error
        responses.add(
            responses.GET,
            "https://example.com/api/users/123",
            status=400,
            body="""{"error": "Not Found", "message": "User not found"}"""
        )
        success, description = HTTPResolver.testconnection(params)
        self.assertFalse(success)
        self.assertIn("No user found for user ID '123'", description)

        # Failed to get access token
        responses.add(
            responses.POST,
            "https://example.com/auth",
            status=403,
            body="""{"error": "Forbidden", "message": "Invalid credentials"}"""
        )
        success, description = HTTPResolver.testconnection(params)
        self.assertFalse(success)
        self.assertIn("Failed to get authorization header", description)

        # Load config fails: Invalid timeout format
        params[TIMEOUT] = "30.5"
        success, description = HTTPResolver.testconnection(params)
        self.assertFalse(success)
        self.assertIn("Failed", description)

    @responses.activate
    def test_14_get_user_info(self):
        responses.add(self.METHOD, self.ENDPOINT, status=200, adding_headers=json.loads(self.HEADERS),
                      body=self.BODY_RESPONSE_OK)
        responses.add(self.METHOD, self.ENDPOINT, status=200, adding_headers=json.loads(self.HEADERS),
                      body=self.BODY_RESPONSE_NOK)

        # Test with valid response
        instance = HTTPResolver()
        instance.loadConfig(self.basic_config)
        response = instance.getUserInfo('PepePerez')
        self.assertEqual(response.get('username'), 'PepePerez')
        self.assertEqual(response.get('email'), 'pepe@perez.com')
        self.assertEqual(response.get('mobile'), '+1123568974')
        self.assertEqual(response.get('a_static_key'), 'a static value')

        # Test with invalid response
        self.assertDictEqual({}, instance.getUserInfo('PepePerez'))

    def test_15_get_config(self):
        resolver = HTTPResolver()
        default_config = resolver.get_config()
        self.assertDictEqual({}, default_config[HEADERS])
        self.assertFalse(default_config[EDITABLE])
        self.assertTrue(default_config[VERIFY_TLS])
        self.assertEqual(60, default_config[TIMEOUT])
        self.assertEqual("httpresolver", default_config["type"])

        self.assertNotIn(ADVANCED, default_config)
        self.assertNotIn(CONFIG_AUTHORIZATION, default_config)
        self.assertNotIn(CONFIG_GET_USER_LIST, default_config)
        self.assertNotIn(CONFIG_GET_USER_BY_ID, default_config)
        self.assertNotIn(CONFIG_GET_USER_BY_NAME, default_config)
        self.assertNotIn(ATTRIBUTE_MAPPING, default_config)
        self.assertNotIn(BASE_URL, default_config)

    def test_16_map(self):
        resolver = HTTPResolver()
        config = {CONFIG_GET_USER_BY_ID: {ENDPOINT: "http://example.com/users/{userid}", METHOD: HTTPMethod.GET.value},
                  ATTRIBUTE_MAPPING: {"username": "name", "userid": "id"}}
        resolver.loadConfig(config)
        mapping = resolver.map
        self.assertEqual(3, len(mapping))
        self.assertSetEqual({"username", "userid", "password"}, set(mapping.keys()))

    @responses.activate
    def test_17_add_user_success(self):
        resolver = HTTPResolver()
        resolver.loadConfig(self.advanced_config)
        user_data = {"username": "testuser", "givenname": "Test", "surname": "User"}

        # JSON response
        def add_user_callback(request):
            body = json.loads(request.body)
            self.assertEqual(body["login"], "testuser")
            self.assertEqual(body["first_name"], "Test")
            self.assertEqual(body["last_name"], "User")
            self.assertTrue(body["enabled"])
            return 201, {"Content-Type": "application/json"}, '{"id": "1234"}'

        responses.add_callback(responses.POST, "https://example.com/users", callback=add_user_callback)
        self.assertEqual("1234", resolver.add_user(user_data))

        # No content response
        responses.add(responses.POST, "https://example.com/users", status=204)
        responses.add(responses.GET, "https://example.com/users/testuser", status=200, body='{"id": "1234"}')
        self.assertEqual("1234", resolver.add_user(user_data))

        # No create config
        resolver = HTTPResolver()
        resolver.loadConfig(self.basic_config)
        self.assertEqual("", resolver.add_user(user_data))

    @responses.activate
    def test_18_add_user_fails(self):
        resolver = HTTPResolver()
        resolver.loadConfig(self.advanced_config)
        user_data = {"username": "testuser", "givenname": "Test", "surname": "User"}

        # HTTP error
        responses.add(responses.POST, "https://example.com/users", status=400, body='{"error": "User already exist"}')
        self.assertRaises(ResolverError, resolver.add_user, user_data)

        # custom error handling
        responses.add(responses.POST, "https://example.com/users", status=200,
                      body='{"success": false}')
        self.assertRaises(ResolverError, resolver.add_user, user_data)

    @responses.activate
    def test_19_update_user_success(self):
        resolver = HTTPResolver()
        resolver.loadConfig(self.advanced_config)
        uid = "1234"
        user_data = {"username": "testuser", "givenname": "Test", "surname": "User"}

        # JSON response
        def update_user_callback(request):
            body = json.loads(request.body)
            self.assertEqual(body["login"], "testuser")
            self.assertEqual(body["first_name"], "Test")
            self.assertEqual(body["last_name"], "User")
            return 200, {"Content-Type": "application/json"}, '{"id": "1234"}'

        responses.add_callback(responses.PUT, "https://example.com/users/1234", callback=update_user_callback)
        self.assertTrue(resolver.update_user(uid, user_data))

        # No content response
        responses.add(responses.PUT, "https://example.com/users/1234", status=204)
        self.assertTrue(resolver.update_user(uid, user_data))

    @responses.activate
    def test_20_update_user_fails(self):
        resolver = HTTPResolver()
        resolver.loadConfig(self.advanced_config)
        uid = "1234"
        user_data = {"username": "testuser", "givenname": "Test", "surname": "User"}

        # HTTP error
        responses.add(responses.PUT, "https://example.com/users/1234", status=400, body='{"error": "Bad Request"}')
        self.assertFalse(resolver.update_user(uid, user_data))

        # custom error handling
        responses.add(responses.POST, "https://example.com/users", status=200,
                      body='{"success": false}')
        self.assertFalse(resolver.update_user(uid, user_data))

        # No update config
        resolver = HTTPResolver()
        resolver.loadConfig(self.basic_config)
        self.assertFalse(resolver.update_user(uid, user_data))

    @responses.activate
    def test_21_delete_user_success(self):
        resolver = HTTPResolver()
        resolver.loadConfig(self.advanced_config)
        uid = "1234"

        responses.add(responses.DELETE, "https://example.com/users/1234", status=200, body='{"success": true}')
        self.assertTrue(resolver.delete_user(uid))

        # No content response
        responses.add(responses.DELETE, "https://example.com/users/1234", status=204)
        self.assertTrue(resolver.delete_user(uid))

    @responses.activate
    def test_22_delete_user_fails(self):
        resolver = HTTPResolver()
        resolver.loadConfig(self.advanced_config)
        uid = "1234"

        # HTTP error
        responses.add(responses.DELETE, "https://example.com/users/1234", status=400, body='{"error": "Bad Request"}')
        self.assertFalse(resolver.delete_user(uid))

        # custom error handling
        responses.add(responses.DELETE, "https://example.com/users", status=200,
                      body='{"success": false, "message": "Unknown user"}')
        self.assertFalse(resolver.delete_user(uid))

        # No delete config
        resolver = HTTPResolver()
        resolver.loadConfig(self.basic_config)
        self.assertFalse(resolver.delete_user(uid))

    def check_pass_callback(self, request):
        params = json.loads(request.body)
        if params.get("username") == "testuser" and params.get("password") == "testpassword" and params.get(
                "grant_type") == "password":
            return 200, {}, json.dumps({"token_type": "Bearer", "access_token": "12345"})
        else:
            return 401, {}, json.dumps({"error": "invalid_grant",
                                        "error_description": "Invalid user credentials"})

    @responses.activate
    def test_23_check_pass_success(self):
        resolver = HTTPResolver()
        resolver.loadConfig(self.advanced_config)

        # Mock user auth
        responses.add_callback(responses.POST, "https://example.com/auth", callback=self.check_pass_callback)

        self.assertTrue(resolver.checkPass("111-aaa-333", "testpassword", "testuser"))

    @responses.activate
    def test_24_check_pass_fails(self):
        resolver = HTTPResolver()
        resolver.loadConfig(self.advanced_config)

        # Mock user auth
        responses.add_callback(responses.POST, "https://example.com/auth", callback=self.check_pass_callback)
        self.assertFalse(resolver.checkPass("111-aaa-333", "wrongPassword", "testuser"))

        # Custom error handling
        resolver.config_user_auth[HAS_ERROR_HANDLER] = True
        resolver.config_user_auth[ERROR_RESPONSE] = {"success": False, "description": "Invalid credentials"}
        responses.add(responses.POST, "https://example.com/auth", status=200,
                      body="""{"success": false, "description": "Invalid credentials"}""")
        self.assertFalse(resolver.checkPass("111-aaa-333", "wrongPassword", "testuser"))

        # No user auth config
        resolver = HTTPResolver()
        resolver.loadConfig(self.basic_config)
        self.assertFalse(resolver.checkPass("111-aaa-333", "testpassword", "testuser"))


class ConfidentialClientApplicationMock:
    def __init__(self, client_id: str, authority: str, client_credential: Union[str, dict[str, str]]):
        self.client_id = client_id
        self.authority = authority
        self.client_credential = client_credential
        if isinstance(client_credential, dict):
            get_required(client_credential, "private_key")
            get_required(client_credential, "thumbprint")
        self.access_token = None

    def acquire_token_for_client(self, scopes):
        self.access_token = "123456789"
        return {
            'access_token': self.access_token,
            'expires_in': 3600,
            'token_type': 'Bearer'
        }


class ConfidentialClientApplicationMockError(ConfidentialClientApplicationMock):
    def acquire_token_for_client(self, scopes):
        return {
            "error": "ERR 123",
            "error_description": "Invalid client id"
        }


class EntraIDResolverTestCase(MyTestCase):

    def set_up_resolver(self, config_update: Optional[dict] = None):
        resolver = EntraIDResolver()
        config = {CLIENT_ID: "1234", CLIENT_CREDENTIAL_TYPE: ClientCredentialType.SECRET.value,
                  CLIENT_SECRET: "secret", TENANT: "organization"}
        if config_update:
            config.update(config_update)

        with mock.patch("privacyidea.lib.resolvers.EntraIDResolver.msal.ConfidentialClientApplication",
                        new=ConfidentialClientApplicationMock):
            resolver.loadConfig(config)
        return resolver

    def test_01_load_config_success(self):
        resolver = EntraIDResolver()
        # At least required parameters, the remaining parameters will be set to default values.
        config = {CLIENT_ID: "1234", CLIENT_CREDENTIAL_TYPE: ClientCredentialType.SECRET.value, CLIENT_SECRET: "secret",
                  TENANT: "organization"}

        with mock.patch("privacyidea.lib.resolvers.EntraIDResolver.msal.ConfidentialClientApplication",
                        new=ConfidentialClientApplicationMock):
            resolver.loadConfig(config)
        self.assertEqual(config[CLIENT_ID], resolver.client_id)
        self.assertEqual(config[CLIENT_SECRET], resolver.client_credential)
        self.assertEqual(config[TENANT], resolver.tenant)
        self.assertFalse(resolver._editable)

        # Use certificate
        config = {CLIENT_ID: "1234", TENANT: "organization",
                  CLIENT_CREDENTIAL_TYPE: ClientCredentialType.CERTIFICATE.value,
                  CLIENT_CERTIFICATE: {PRIVATE_KEY_FILE: "tests/testdata/private.pem",
                                       CERTIFICATE_FINGERPRINT: "fingerprint"}}
        with mock.patch("privacyidea.lib.resolvers.EntraIDResolver.msal.ConfidentialClientApplication",
                        new=ConfidentialClientApplicationMock):
            resolver.loadConfig(config)
        self.assertEqual(config[CLIENT_ID], resolver.client_id)
        self.assertEqual(config[TENANT], resolver.tenant)
        self.assertEqual(ClientCredentialType.CERTIFICATE, resolver.client_credential_type)
        self.assertIn("-----BEGIN RSA PRIVATE KEY-----", resolver.client_credential["private_key"])
        self.assertEqual(config[CLIENT_CERTIFICATE][CERTIFICATE_FINGERPRINT],
                         resolver.client_credential["thumbprint"])
        self.assertNotIn("passphrase", resolver.client_credential)  # Do not include passphrase if not available
        self.assertFalse(resolver._editable)

        # certificate with password
        config[CLIENT_CERTIFICATE][PRIVATE_KEY_PASSWORD] = "Test123"
        with mock.patch("privacyidea.lib.resolvers.EntraIDResolver.msal.ConfidentialClientApplication",
                        new=ConfidentialClientApplicationMock):
            resolver.loadConfig(config)
        self.assertEqual("Test123", resolver.client_credential["passphrase"])

    def test_02_load_config_fails(self):
        # Invalid authority
        config = {CLIENT_ID: "1234", CLIENT_CREDENTIAL_TYPE: ClientCredentialType.SECRET.value, CLIENT_SECRET: "secret",
                  TENANT: "organization"}
        # invalid when checking authority
        with pytest.raises(ParameterError, match="Invalid Authorization"):
            EntraIDResolver().loadConfig(config)

        # Missing parameters
        with mock.patch("privacyidea.lib.resolvers.EntraIDResolver.msal.ConfidentialClientApplication",
                        new=ConfidentialClientApplicationMock):
            with pytest.raises(ParameterError, match=TENANT):
                EntraIDResolver().loadConfig(
                    {CLIENT_ID: "1234", CLIENT_CREDENTIAL_TYPE: ClientCredentialType.SECRET.value,
                     CLIENT_SECRET: "secret"})

        with mock.patch("privacyidea.lib.resolvers.EntraIDResolver.msal.ConfidentialClientApplication",
                        new=ConfidentialClientApplicationMock):
            with pytest.raises(ParameterError, match=CLIENT_ID):
                EntraIDResolver().loadConfig({TENANT: "organization",
                                              CLIENT_CREDENTIAL_TYPE: ClientCredentialType.SECRET.value,
                                              CLIENT_SECRET: "secret"})

        with mock.patch("privacyidea.lib.resolvers.EntraIDResolver.msal.ConfidentialClientApplication",
                        new=ConfidentialClientApplicationMock):
            with pytest.raises(ParameterError, match=CLIENT_CREDENTIAL_TYPE):
                EntraIDResolver().loadConfig({TENANT: "organization", CLIENT_ID: "1234", CLIENT_SECRET: "secret"})

        # Use client secret
        with mock.patch("privacyidea.lib.resolvers.EntraIDResolver.msal.ConfidentialClientApplication",
                        new=ConfidentialClientApplicationMock):
            with pytest.raises(ParameterError, match=CLIENT_SECRET):
                EntraIDResolver().loadConfig({CLIENT_ID: "1234",
                                              CLIENT_CREDENTIAL_TYPE: ClientCredentialType.SECRET.value,
                                              TENANT: "organization"})

        # use certificate
        with mock.patch("privacyidea.lib.resolvers.EntraIDResolver.msal.ConfidentialClientApplication",
                        new=ConfidentialClientApplicationMock):
            with pytest.raises(ParameterError, match=CLIENT_CERTIFICATE):
                EntraIDResolver().loadConfig({CLIENT_ID: "1234",
                                              CLIENT_CREDENTIAL_TYPE: ClientCredentialType.CERTIFICATE.value,
                                              TENANT: "organization"})
        # subkeys of the certificate are missing
        with mock.patch("privacyidea.lib.resolvers.EntraIDResolver.msal.ConfidentialClientApplication",
                        new=ConfidentialClientApplicationMock):
            with pytest.raises(ParameterError, match=CERTIFICATE_FINGERPRINT):
                EntraIDResolver().loadConfig({CLIENT_ID: "1234",
                                              CLIENT_CREDENTIAL_TYPE: ClientCredentialType.CERTIFICATE.value,
                                              CLIENT_CERTIFICATE: {PRIVATE_KEY_FILE: "tests/testdata/private.pem"},
                                              TENANT: "organization"})
        with mock.patch("privacyidea.lib.resolvers.EntraIDResolver.msal.ConfidentialClientApplication",
                        new=ConfidentialClientApplicationMock):
            with pytest.raises(ParameterError, match=PRIVATE_KEY_FILE):
                EntraIDResolver().loadConfig({CLIENT_ID: "1234",
                                              CLIENT_CREDENTIAL_TYPE: ClientCredentialType.CERTIFICATE.value,
                                              CLIENT_CERTIFICATE: {CERTIFICATE_FINGERPRINT: "fingerprint"},
                                              TENANT: "organization"})
        # path to certificate is not valid
        with mock.patch("privacyidea.lib.resolvers.EntraIDResolver.msal.ConfidentialClientApplication",
                        new=ConfidentialClientApplicationMock):
            with mock.patch("privacyidea.lib.resolvers.EntraIDResolver.open", side_effect=FileNotFoundError):
                self.assertRaises(ParameterError, EntraIDResolver().loadConfig, {CLIENT_ID: "1234",
                                                                                 CLIENT_CREDENTIAL_TYPE: ClientCredentialType.CERTIFICATE.value,
                                                                                 CLIENT_CERTIFICATE: {
                                                                                     PRIVATE_KEY_FILE: "tests/testdata/private.pem",
                                                                                     CERTIFICATE_FINGERPRINT: "fingerprint"},
                                                                                 TENANT: "organization"})

    def test_03_getResolverClassDescriptor(self):
        descriptor = EntraIDResolver().getResolverClassDescriptor()

        self.assertIn("entraidresolver", descriptor)
        self.assertTrue(descriptor["entraidresolver"]["clazz"].endswith("EntraIDResolver"))
        config = descriptor["entraidresolver"]["config"]
        self.assertEqual(config[CLIENT_ID], "string")
        self.assertEqual(config[CLIENT_CREDENTIAL_TYPE], "string")
        self.assertEqual(config[CLIENT_SECRET], "password")
        self.assertEqual(config[CLIENT_CERTIFICATE], "dict_with_password")
        self.assertEqual(config[f"{CLIENT_CERTIFICATE}.{PRIVATE_KEY_PASSWORD}"], "password")
        self.assertEqual(config[TENANT], "string")
        self.assertEqual(config[EDITABLE], "bool")

    def test_04_get_auth_header(self):
        resolver = EntraIDResolver()

        config = {CLIENT_ID: "1234", CLIENT_CREDENTIAL_TYPE: ClientCredentialType.SECRET.value,
                  CLIENT_SECRET: "secret", TENANT: "organization"}
        with mock.patch("privacyidea.lib.resolvers.EntraIDResolver.msal.ConfidentialClientApplication",
                        new=ConfidentialClientApplicationMock):
            resolver.loadConfig(config)

        # success
        header = resolver._get_auth_header()
        self.assertSetEqual({"Authorization"}, set(header.keys()))
        self.assertEqual("Bearer 123456789", header["Authorization"])

        # fails
        with mock.patch("privacyidea.lib.resolvers.EntraIDResolver.msal.ConfidentialClientApplication",
                        new=ConfidentialClientApplicationMockError):
            resolver.loadConfig(config)
        self.assertRaises(ResolverError, resolver._get_auth_header)

    def test_05_entra_user_to_pi_user(self):
        resolver = self.set_up_resolver(
            {ATTRIBUTE_MAPPING: {"uid": "id", "username": "userPrincipalName", "givenname": "givenName",
                                 "surname": "surname", "email": "mail", "mobile": "mobilePhone",
                                 "phone": "businessPhones"}})

        entra_user = {"businessPhones": ["+1 425 555 0109"],
                      "displayName": "Adele Vance",
                      "givenName": "Adele",
                      "jobTitle": "Retail Manager",
                      "mail": "AdeleV@contoso.com",
                      "mobilePhone": "+1 425 555 0109",
                      "officeLocation": "18/2111",
                      "preferredLanguage": "en-US",
                      "surname": "Vance",
                      "userPrincipalName": "AdeleV@contoso.com",
                      "id": "87d349ed-44d7-43e1-9a83-5f2406dee5bd"
                      }

        pi_user = resolver._user_store_user_to_pi_user(entra_user)
        self.assertEqual(pi_user["uid"], entra_user["id"])
        self.assertEqual(pi_user["username"], entra_user["userPrincipalName"])
        self.assertEqual(pi_user["givenname"], entra_user["givenName"])
        self.assertEqual(pi_user["surname"], entra_user["surname"])
        self.assertEqual(pi_user["email"], entra_user["mail"])
        self.assertEqual(pi_user["mobile"], entra_user["mobilePhone"])
        self.assertEqual(pi_user["phone"], entra_user["businessPhones"])
        self.assertEqual(7, len(pi_user))

    @responses.activate
    def test_06_getUserList_success(self):
        resolver = self.set_up_resolver()

        responses.add(responses.GET, "https://graph.microsoft.com/v1.0/users", status=200,
                      body="""{"@odata.context": "https://graph.microsoft.com/v1.0/$metadata#users",
                     "value": [{"businessPhones": [],
                                "displayName": "Conf Room Adams",
                                "givenName": null,
                                "jobTitle": null,
                                "mail": "Adams@contoso.com",
                                "mobilePhone": null,
                                "officeLocation": null,
                                "preferredLanguage": null,
                                "surname": null,
                                "userPrincipalName": "Adams@contoso.com",
                                "id": "6ea91a8d-e32e-41a1-b7bd-d2d185eed0e0"},
                               {"businessPhones": ["425-555-0100"],
                                "displayName": "MOD Administrator",
                                "givenName": "MOD",
                                "jobTitle": null,
                                "mail": null,
                                "mobilePhone": "425-555-0101",
                                "officeLocation": null,
                                "preferredLanguage": "en-US",
                                "surname": "Administrator",
                                "userPrincipalName": "admin@contoso.com",
                                "id": "4562bcc8-c436-4f95-b7c0-4f8ce89dca5e"}]}""")

        user_list = resolver.getUserList()
        self.assertEqual(2, len(user_list))

    @responses.activate
    def test_07_getUserList_fails(self):
        resolver = self.set_up_resolver()

        # Mock an error response from the API
        responses.add(responses.GET, "https://graph.microsoft.com/v1.0/users", status=501,
                      body="""{"error": {"code": "NotImplemented", "message": "Property can not be returned within a user collection."}}""")
        self.assertRaises(ResolverError, resolver.getUserList)

        # Error response with no error code
        responses.add(responses.GET, "https://graph.microsoft.com/v1.0/users", status=400, body="""{}""")
        self.assertRaises(ResolverError, resolver.getUserList)

        # Custom error handling for successful response without users in the response
        resolver.config[CONFIG_GET_USER_LIST][HAS_ERROR_HANDLER] = True
        resolver.config[CONFIG_GET_USER_LIST][ERROR_RESPONSE] = {}
        responses.add(responses.GET, "https://graph.microsoft.com/v1.0/users", status=200, body="""{}""")
        self.assertRaises(ResolverError, resolver.getUserList)

    @responses.activate
    def test_08_get_UserInfo_success(self):
        resolver = self.set_up_resolver()

        user_id = "87d349ed-44d7-43e1-9a83-5f2406dee5bd"
        responses.add(responses.GET, f"https://graph.microsoft.com/v1.0/users/{user_id}", status=200,
                      body="""{"businessPhones": ["+1 425 555 0109"],
                               "displayName": "Adele Vance",
                               "givenName": "Adele",
                               "jobTitle": "Retail Manager",
                               "mail": "AdeleV@contoso.com",
                               "mobilePhone": "+1 425 555 0109",
                               "officeLocation": "18/2111",
                               "preferredLanguage": "en-US",
                               "surname": "Vance",
                               "userPrincipalName": "AdeleV@contoso.com",
                               "id": "87d349ed-44d7-43e1-9a83-5f2406dee5bd"
                            }""")

        user_info = resolver.getUserInfo(user_id)
        self.assertEqual(user_id, user_info["userid"])
        self.assertEqual("AdeleV@contoso.com", user_info["username"])
        self.assertEqual("Adele", user_info["givenname"])
        self.assertEqual("Vance", user_info["surname"])
        self.assertEqual("AdeleV@contoso.com", user_info["email"])
        self.assertEqual("+1 425 555 0109", user_info["mobile"])
        self.assertListEqual(["+1 425 555 0109"], user_info["phone"])
        self.assertEqual(7, len(user_info))

    @responses.activate
    def test_09_get_UserInfo_fails(self):
        resolver = self.set_up_resolver()
        user_id = "12345789"

        # User ID does not exists
        responses.add(responses.GET, f"https://graph.microsoft.com/v1.0/users/{user_id}", status=404,
                      body="""{"error": {"code": "Request_ResourceNotFound", 
                               "message": "Resource '12345789' does not exist or one of its queried reference-property objects are not present."}}"""
                      )
        self.assertDictEqual({}, resolver.getUserInfo(user_id))
        responses.add(responses.GET, f"https://graph.microsoft.com/v1.0/users/{user_id}", status=404, body="{}")
        self.assertDictEqual({}, resolver.getUserInfo(user_id))

        # Server is busy
        responses.add(responses.GET, f"https://graph.microsoft.com/v1.0/users/{user_id}", status=202, body="{}")
        self.assertDictEqual({}, resolver.getUserInfo(user_id))

        # Missing error message in response
        responses.add(responses.GET, f"https://graph.microsoft.com/v1.0/users/{user_id}", status=400, body="{}")
        self.assertDictEqual({}, resolver.getUserInfo(user_id))

        # Custom error handling for successful response without user info
        resolver.config[CONFIG_GET_USER_BY_ID][HAS_ERROR_HANDLER] = True
        resolver.config[CONFIG_GET_USER_BY_ID][ERROR_RESPONSE] = {"success": False, "message": "User not found"}
        responses.add(responses.GET, f"https://graph.microsoft.com/v1.0/users/{user_id}", status=200,
                      body="""{"success": false, "message": "User not found"}""")
        self.assertDictEqual({}, resolver.getUserInfo(user_id))

    @responses.activate
    def test_10_getUsername(self):
        resolver = self.set_up_resolver()

        # success
        user_id = "87d349ed-44d7-43e1-9a83-5f2406dee5bd"
        responses.add(responses.GET, f"https://graph.microsoft.com/v1.0/users/{user_id}", status=200,
                      body="""{"businessPhones": ["+1 425 555 0109"],
                               "displayName": "Adele Vance",
                               "givenName": "Adele",
                               "jobTitle": "Retail Manager",
                               "mail": "AdeleV@contoso.com",
                               "mobilePhone": "+1 425 555 0109",
                               "officeLocation": "18/2111",
                               "preferredLanguage": "en-US",
                               "surname": "Vance",
                               "userPrincipalName": "AdeleV@contoso.com",
                               "id": "87d349ed-44d7-43e1-9a83-5f2406dee5bd"
                            }""")

        self.assertEqual("AdeleV@contoso.com", resolver.getUsername(user_id))

        # User ID does not exists
        responses.add(responses.GET, f"https://graph.microsoft.com/v1.0/users/{user_id}", status=404,
                      body="""{"error": {"code": "Request_ResourceNotFound", 
                                       "message": "Resource '12345789' does not exist or one of its queried reference-property objects are not present."}}"""
                      )
        self.assertEqual("", resolver.getUsername(user_id))

    @responses.activate
    def test_11_getUserId(self):
        resolver = self.set_up_resolver()

        # success
        user_name = "AdeleV@contoso.com"
        responses.add(responses.GET, f"https://graph.microsoft.com/v1.0/users/{user_name}", status=200,
                      body="""{"businessPhones": ["+1 425 555 0109"],
                               "displayName": "Adele Vance",
                               "givenName": "Adele",
                               "jobTitle": "Retail Manager",
                               "mail": "AdeleV@contoso.com",
                               "mobilePhone": "+1 425 555 0109",
                               "officeLocation": "18/2111",
                               "preferredLanguage": "en-US",
                               "surname": "Vance",
                               "userPrincipalName": "AdeleV@contoso.com",
                               "id": "87d349ed-44d7-43e1-9a83-5f2406dee5bd"
                              }""")

        self.assertEqual("87d349ed-44d7-43e1-9a83-5f2406dee5bd", resolver.getUserId(user_name))

        # User ID does not exists
        responses.add(responses.GET, f"https://graph.microsoft.com/v1.0/users/{user_name}", status=404,
                      body="""{"error": {"code": "Request_ResourceNotFound", 
                                               "message": "Resource 'AdeleV@contoso.com' does not exist."}}"""
                      )
        self.assertEqual("", resolver.getUserId(user_name))

    @responses.activate
    def test_12_testconnection_success(self):
        params = {CLIENT_ID: "1234", CLIENT_CREDENTIAL_TYPE: ClientCredentialType.SECRET.value, CLIENT_SECRET: "secret",
                  TENANT: "organization", EDITABLE: True, "test_username": "AdeleV@contoso.com",
                  "test_userid": "87d349ed-44d7-43e1-9a83-5f2406dee5bd"}

        # user list response
        responses.add(responses.GET, "https://graph.microsoft.com/v1.0/users", status=200,
                      body="""{"@odata.context": "https://graph.microsoft.com/v1.0/$metadata#users",
                                "value": [{"businessPhones": [],
                                           "displayName": "Conf Room Adams",
                                           "givenName": null,
                                           "jobTitle": null,
                                           "mail": "Adams@contoso.com",
                                           "mobilePhone": null,
                                           "officeLocation": null,
                                           "preferredLanguage": null,
                                           "surname": null,
                                           "userPrincipalName": "Adams@contoso.com",
                                           "id": "6ea91a8d-e32e-41a1-b7bd-d2d185eed0e0"},
                                          {"businessPhones": ["425-555-0100"],
                                           "displayName": "MOD Administrator",
                                           "givenName": "MOD",
                                           "jobTitle": null,
                                           "mail": null,
                                           "mobilePhone": "425-555-0101",
                                           "officeLocation": null,
                                           "preferredLanguage": "en-US",
                                           "surname": "Administrator",
                                           "userPrincipalName": "admin@contoso.com",
                                           "id": "4562bcc8-c436-4f95-b7c0-4f8ce89dca5e"}]}""")

        # user by id response
        responses.add(responses.GET, "https://graph.microsoft.com/v1.0/users/87d349ed-44d7-43e1-9a83-5f2406dee5bd",
                      status=200, body="""{"businessPhones": ["+1 425 555 0109"],
                                           "displayName": "Adele Vance",
                                           "givenName": "Adele",
                                           "jobTitle": "Retail Manager",
                                           "mail": "AdeleV@contoso.com",
                                           "mobilePhone": "+1 425 555 0109",
                                           "officeLocation": "18/2111",
                                           "preferredLanguage": "en-US",
                                           "surname": "Vance",
                                           "userPrincipalName": "AdeleV@contoso.com",
                                           "id": "87d349ed-44d7-43e1-9a83-5f2406dee5bd"
                                        }""")

        # user by name response
        responses.add(responses.GET, "https://graph.microsoft.com/v1.0/users/AdeleV@contoso.com", status=200,
                      body="""{"businessPhones": ["+1 425 555 0109"],
                               "displayName": "Adele Vance",
                               "givenName": "Adele",
                               "jobTitle": "Retail Manager",
                               "mail": "AdeleV@contoso.com",
                               "mobilePhone": "+1 425 555 0109",
                               "officeLocation": "18/2111",
                               "preferredLanguage": "en-US",
                               "surname": "Vance",
                               "userPrincipalName": "AdeleV@contoso.com",
                               "id": "87d349ed-44d7-43e1-9a83-5f2406dee5bd"
                            }""")

        with mock.patch("privacyidea.lib.resolvers.EntraIDResolver.msal.ConfidentialClientApplication",
                        new=ConfidentialClientApplicationMock):
            #
            success, description = EntraIDResolver.testconnection(params)
            self.assertTrue(success)
            self.assertIn("Resolver config seems to be OK", description)
            # check which configs were tested
            self.assertIn("Get user by name", description)
            self.assertIn("Get user by ID", description)
            self.assertIn("User List", description)
            self.assertIn("Authorization", description)

    @responses.activate
    def test_13_testconnection_fails(self):
        params = {CLIENT_ID: "1234", CLIENT_CREDENTIAL_TYPE: ClientCredentialType.SECRET.value, CLIENT_SECRET: "secret",
                  TENANT: "organization", EDITABLE: True, "test_username": "AdeleV@contoso.com",
                  "test_userid": "87d349ed-44d7-43e1-9a83-5f2406dee5bd"}

        # --- responses for success ----
        # user list response
        responses.add(responses.GET, "https://graph.microsoft.com/v1.0/users", status=200,
                      body="""{"@odata.context": "https://graph.microsoft.com/v1.0/$metadata#users",
                                "value": [{"businessPhones": [],
                                            "displayName": "Conf Room Adams",
                                            "givenName": null,
                                            "jobTitle": null,
                                            "mail": "Adams@contoso.com",
                                            "mobilePhone": null,
                                            "officeLocation": null,
                                            "preferredLanguage": null,
                                            "surname": null,
                                            "userPrincipalName": "Adams@contoso.com",
                                            "id": "6ea91a8d-e32e-41a1-b7bd-d2d185eed0e0"},
                                           {"businessPhones": ["425-555-0100"],
                                            "displayName": "MOD Administrator",
                                            "givenName": "MOD",
                                            "jobTitle": null,
                                            "mail": null,
                                            "mobilePhone": "425-555-0101",
                                            "officeLocation": null,
                                            "preferredLanguage": "en-US",
                                            "surname": "Administrator",
                                            "userPrincipalName": "admin@contoso.com",
                                            "id": "4562bcc8-c436-4f95-b7c0-4f8ce89dca5e"}]}""")
        # user by id response
        responses.add(responses.GET, "https://graph.microsoft.com/v1.0/users/87d349ed-44d7-43e1-9a83-5f2406dee5bd",
                      status=200, body="""{"businessPhones": ["+1 425 555 0109"],
                                           "displayName": "Adele Vance",
                                           "givenName": "Adele",
                                           "jobTitle": "Retail Manager",
                                           "mail": "AdeleV@contoso.com",
                                           "mobilePhone": "+1 425 555 0109",
                                           "officeLocation": "18/2111",
                                           "preferredLanguage": "en-US",
                                           "surname": "Vance",
                                           "userPrincipalName": "AdeleV@contoso.com",
                                           "id": "87d349ed-44d7-43e1-9a83-5f2406dee5bd"
                                        }""")
        # user by name response
        responses.add(responses.GET, "https://graph.microsoft.com/v1.0/users/AdeleV@contoso.com", status=200,
                      body="""{"businessPhones": ["+1 425 555 0109"],
                               "displayName": "Adele Vance",
                               "givenName": "Adele",
                               "jobTitle": "Retail Manager",
                               "mail": "AdeleV@contoso.com",
                               "mobilePhone": "+1 425 555 0109",
                               "officeLocation": "18/2111",
                               "preferredLanguage": "en-US",
                               "surname": "Vance",
                               "userPrincipalName": "AdeleV@contoso.com",
                               "id": "87d349ed-44d7-43e1-9a83-5f2406dee5bd"
                            }""")

        # Invalid delete / edit / create user config
        with mock.patch("privacyidea.lib.resolvers.EntraIDResolver.msal.ConfidentialClientApplication",
                        new=ConfidentialClientApplicationMock):
            # Invalid delete config
            params[CONFIG_DELETE_USER] = {ENDPOINT: "/users/{userid}"}
            success, description = EntraIDResolver.testconnection(params)
            self.assertFalse(success)
            self.assertIn("Failed to load delete user config", description)
            del params[CONFIG_DELETE_USER]

            # Invalid Edit config
            params[CONFIG_EDIT_USER] = {METHOD: "random", ENDPOINT: "/users/{userid}"}
            success, description = EntraIDResolver.testconnection(params)
            self.assertFalse(success)
            self.assertIn("Failed to load edit user config", description)
            del params[CONFIG_EDIT_USER]

            # Invalid Edit config
            params[CONFIG_CREATE_USER] = {METHOD: "post", ENDPOINT: "/users/", REQUEST_MAPPING: "{'enabled': True}"}
            success, description = EntraIDResolver.testconnection(params)
            self.assertFalse(success)
            self.assertIn("Failed to load create user config", description)
            del params[CONFIG_CREATE_USER]

            # Invalid check user password config
            params[CONFIG_USER_AUTH] = {METHOD: "post"}
            success, description = EntraIDResolver.testconnection(params)
            self.assertFalse(success)
            self.assertIn("Failed to load config to check user password", description)
            del params[CONFIG_USER_AUTH]

        # Invalid read configs
        responses.add(responses.GET, "https://graph.microsoft.com/v1.0/users?%24select=aboutMe", status=501,
                      body="""{"error": {"code": "501", "message": "Not Implemented"}}""")
        with mock.patch("privacyidea.lib.resolvers.EntraIDResolver.msal.ConfidentialClientApplication",
                        new=ConfidentialClientApplicationMock):
            # invalid user property for collection
            params[CONFIG_GET_USER_LIST] = {METHOD: "GET", ENDPOINT: "/users",
                                            REQUEST_MAPPING: {"$select": "aboutMe"}}
            success, description = EntraIDResolver.testconnection(params)
            self.assertFalse(success)
            self.assertIn("Failed to get user list", description)

            # User by Name
            params[CONFIG_GET_USER_BY_NAME] = {ENDPOINT: "/users/{username}"}
            success, description = EntraIDResolver.testconnection(params)
            self.assertFalse(success)
            self.assertIn("Failed to get user by name", description)

            # User by ID
            params[CONFIG_GET_USER_BY_ID] = {METHOD: "GET", ENDPOINT: "/users/{userid}", HEADERS: "{'exact': true}"}
            success, description = EntraIDResolver.testconnection(params)
            self.assertFalse(success)
            self.assertIn("Failed to get user by ID", description)

        # Missing credential type
        del params[CLIENT_CREDENTIAL_TYPE]
        success, description = EntraIDResolver.testconnection(params)
        self.assertFalse(success)
        self.assertIn(CLIENT_CREDENTIAL_TYPE, description)
        params[CLIENT_CREDENTIAL_TYPE] = ClientCredentialType.SECRET.value

        # Invalid tenant in authorization config
        responses.add(responses.GET,
                      "https://login.microsoftonline.com/organization/v2.0/.well-known/openid-configuration",
                      status=400, body="""{"error": "invalid_tenant"}""")
        success, description = EntraIDResolver.testconnection(params)
        self.assertFalse(success)
        self.assertIn("Authorization", description)

        # Tenant valid, Client credential invalid
        responses.add(responses.GET,
                      "https://login.microsoftonline.com/organization/v2.0/.well-known/openid-configuration",
                      status=200,
                      body="""{"token_endpoint": "https://login.microsoftonline.com/123456789/oauth2/v2.0/token",
                            "authorization_endpoint": "https://login.microsoftonline.com/organization/oauth2/v2.0/authorize",
                            "device_authorization_endpoint": "https://login.microsoftonline.com/organization/oauth2/v2.0/devicecode"}""")
        responses.add(responses.POST, "https://login.microsoftonline.com/123456789/oauth2/v2.0/token", status=401,
                      body="""{"error": "invalid_client"}""")
        responses.add_passthru(
            "https://login.microsoftonline.com/common/discovery/instance?api-version=1.1&authorization_endpoint=https://login.microsoftonline.com/common/oauth2/authorize")
        success, description = EntraIDResolver.testconnection(params)
        self.assertFalse(success)
        self.assertIn("Failed to get authorization header", description)

    def test_14_get_search_params(self):
        # Advanced query is enabled by default
        resolver = EntraIDResolver()
        search_dict = {"username": "*test*", "userid": "1234", "givenname": "*", "email": "test*",
                       "favorite_color": "blue"}
        with mock.patch("logging.Logger.debug") as mock_log:
            search_params = resolver._get_search_params(search_dict)
            self.assertIn("$filter", search_params)
            correct_query = "(startswith(userPrincipalName, 'test') or endswith(userPrincipalName, 'test')) and id eq '1234' and (startswith(mail, 'test') or endswith(mail, 'test'))"
            self.assertEqual(correct_query, search_params["$filter"])
            mock_log.assert_called_with("Search parameter 'favorite_color' not found in attribute mapping. Search "
                                        "without this parameter.")

        # Do not allow advanced queries
        resolver.config[CONFIG_GET_USER_LIST][HEADERS] = ""
        search_params = resolver._get_search_params(search_dict)
        self.assertIn("$filter", search_params)
        correct_query = "startswith(userPrincipalName, 'test') and id eq '1234' and startswith(mail, 'test')"
        self.assertEqual(correct_query, search_params["$filter"])

        # Invalid Header also results in simple queries
        resolver.config[CONFIG_GET_USER_LIST][HEADERS] = "{'ConsistencyLevel': 'eventual'}"
        search_params = resolver._get_search_params(search_dict)
        self.assertIn("$filter", search_params)
        correct_query = "startswith(userPrincipalName, 'test') and id eq '1234' and startswith(mail, 'test')"
        self.assertEqual(correct_query, search_params["$filter"])

    def test_15_get_config(self):
        resolver = EntraIDResolver()

        # check default config
        default_config = resolver.get_config()
        self.assertDictEqual({}, default_config[HEADERS])
        self.assertFalse(default_config[EDITABLE])
        self.assertTrue(default_config[VERIFY_TLS])
        self.assertEqual("entraidresolver", default_config["type"])
        self.assertEqual(7, len(default_config[ATTRIBUTE_MAPPING]))
        self.assertEqual("https://graph.microsoft.com/v1.0", default_config[BASE_URL])
        self.assertIn(CONFIG_GET_USER_BY_ID, default_config)
        self.assertIn(CONFIG_GET_USER_LIST, default_config)
        self.assertIn(CONFIG_GET_USER_BY_NAME, default_config)
        self.assertTrue(default_config[ADVANCED])
        self.assertEqual("https://login.microsoftonline.com/{tenant}", default_config[AUTHORITY])
        self.assertNotIn(CLIENT_ID, default_config)
        self.assertNotIn(CLIENT_SECRET, default_config)
        self.assertNotIn(CLIENT_CERTIFICATE, default_config)

        # if we load a config, the new data will be included, but credentials are only returned censored
        with mock.patch("privacyidea.lib.resolvers.EntraIDResolver.msal.ConfidentialClientApplication",
                        new=ConfidentialClientApplicationMock):
            resolver.loadConfig({CLIENT_ID: "1234", CLIENT_CREDENTIAL_TYPE: ClientCredentialType.SECRET.value,
                                 CLIENT_SECRET: "secret", TENANT: "organization"})
        config = resolver.get_config()
        self.assertIn(CLIENT_ID, config)
        self.assertEqual("__CENSORED__", config[CLIENT_SECRET])
        with mock.patch("privacyidea.lib.resolvers.EntraIDResolver.msal.ConfidentialClientApplication",
                        new=ConfidentialClientApplicationMock):
            resolver.loadConfig({CLIENT_ID: "1234", CLIENT_CREDENTIAL_TYPE: ClientCredentialType.CERTIFICATE.value,
                                 CLIENT_CERTIFICATE: {PRIVATE_KEY_FILE: "tests/testdata/private.pem",
                                                      PRIVATE_KEY_PASSWORD: "Test1234",
                                                      CERTIFICATE_FINGERPRINT: "123456"}, TENANT: "organization"})
        config = resolver.get_config()
        self.assertEqual("__CENSORED__", config[CLIENT_CERTIFICATE][PRIVATE_KEY_PASSWORD])

    # Mock response for access token
    @staticmethod
    def add_user_callback(request):
        parameters = json.loads(request.body)
        status_code = 201
        resp_body = {"@odata.context": "https://graph.microsoft.com/v1.0/$metadata#users/$entity",
                     "id": "123456789",
                     "userPrincipalName": parameters.get("userPrincipalName"),
                     "displayName": parameters.get("displayName"),
                     "givenName": parameters.get("givenName"),
                     "surname": parameters.get("surname"),
                     "mail": parameters.get("mail"),
                     "mobilePhone": parameters.get("mobilePhone"),
                     "businessPhones": parameters.get("businessPhones", [])}

        # check for required parameters
        password_profile = parameters.get("passwordProfile", {})
        if (not parameters.get("userPrincipalName") or not parameters.get("displayName") or not
        parameters.get("mailNickname") or parameters.get("accountEnabled") is None or not
        password_profile.get("password") or password_profile.get("password") == "{password}"):
            status_code = 400
            resp_body = {"error": {"code": "Request_BadRequest", "message": "Required property is missing"}}
        # Check that businessPhones is a list
        elif not isinstance(parameters.get("businessPhones", []), list):
            status_code = 400
            resp_body = {"error": {"code": "Request_BadRequest", "message": "businessPhones must be a list"}}
        return status_code, {"Content-Type": "application/json"}, json.dumps(resp_body)

    @responses.activate
    def test_16_add_user_success(self):
        resolver = self.set_up_resolver()

        responses.add_callback(responses.POST, "https://graph.microsoft.com/v1.0/users",
                               callback=self.add_user_callback)

        user_data = {"username": "AdeleV@contoso.com",
                     "givenname": "Adele",
                     "surname": "Vance",
                     "password": "xWwvJ]6NMw+bWH-d",
                     "phone": "01521 123456"}

        uid = resolver.add_user(user_data)
        self.assertEqual("123456789", uid)

    @responses.activate
    def test_17_add_user_fails(self):
        resolver = self.set_up_resolver()

        responses.add_callback(responses.POST, "https://graph.microsoft.com/v1.0/users",
                               callback=self.add_user_callback)

        user_data = {"givenname": "Adele",
                     "surname": "Vance",
                     "password": "xWwvJ]6NMw+bWH-d"}

        # Missing required parameters
        self.assertRaises(ResolverError, resolver.add_user, user_data)
        user_data["userPrincipalName"] = "AdeleV@contoso.com"
        resolver.config[CONFIG_CREATE_USER][REQUEST_MAPPING] = ('{"accountEnabled": true, "displayName": "{givenname} '
                                                                '{surname}", "mailNickname": "{givenname}", '
                                                                '"passwordProfile": {}}')
        self.assertRaises(ResolverError, resolver.add_user, user_data)
        resolver.config[CONFIG_CREATE_USER][REQUEST_MAPPING] = ('{"displayName": "{givenname} {surname}", '
                                                                '"mailNickname": "{givenname}", '
                                                                '"passwordProfile": {"password": "{password}"}}')
        self.assertRaises(ResolverError, resolver.add_user, user_data)
        resolver.config[CONFIG_CREATE_USER][REQUEST_MAPPING] = ('{"accountEnabled": true, '
                                                                '"mailNickname": "{givenname}", '
                                                                '"passwordProfile": {"password": "{password}"}}')
        self.assertRaises(ResolverError, resolver.add_user, user_data)
        resolver.config[CONFIG_CREATE_USER][REQUEST_MAPPING] = ('{"accountEnabled": true, '
                                                                '"displayName": "{givenname} {surname}", '
                                                                '"passwordProfile": {"password": "{password}"}}')
        self.assertRaises(ResolverError, resolver.add_user, user_data)

        # Empty password is also not allowed
        resolver.config[CONFIG_CREATE_USER][REQUEST_MAPPING] = ('{"accountEnabled": true, '
                                                                '"displayName": "{givenname} {surname}", '
                                                                '"mailNickname": "{givenname}", '
                                                                '"passwordProfile": {"password": ""}}')
        self.assertRaises(ResolverError, resolver.add_user, user_data)

        # Unknown error response
        responses.add(responses.POST, "https://graph.microsoft.com/v1.0/users", status=400, body="{}")
        self.assertRaises(ResolverError, resolver.add_user, user_data)

        # Custom error handling
        resolver.config[CONFIG_CREATE_USER][HAS_ERROR_HANDLER] = True
        resolver.config[CONFIG_CREATE_USER][ERROR_RESPONSE] = {"success": False, "message": "User already exists"}
        responses.add(responses.POST, "https://graph.microsoft.com/v1.0/users", status=201,
                      body="""{"success": false, "message": "User already exists"}""")
        self.assertRaises(ResolverError, resolver.add_user, user_data)

    @responses.activate
    def test_18_add_user_no_permission(self):
        resolver = self.set_up_resolver()

        responses.add(responses.POST, "https://graph.microsoft.com/v1.0/users", status=403,
                      body="""{"error": {"code": "Authorization_RequestDenied", 
                               "message": "Insufficient privileges to complete the operation."}}""")

        user_data = {"username": "AdeleV@contoso.com",
                     "givenname": "Adele",
                     "surname": "Vance",
                     "password": "xWwvJ]6NMw+bWH-d"}

        self.assertRaises(ResolverError, resolver.add_user, user_data)

    @responses.activate
    def test_19_update_user_success(self):
        resolver = self.set_up_resolver()
        uid = "87d349ed-44d7-43e1-9a83-5f2406dee5bd"

        def callback(request):
            parameters = json.loads(request.body)
            # Unknown attributes should not be included
            self.assertDictEqual({"surname": "Smith"}, parameters)
            return 204, {}, None

        responses.add_callback(responses.PATCH, f"https://graph.microsoft.com/v1.0/users/{uid}", callback=callback)

        new_params = {"surname": "Smith", "favorite_color": "blue"}
        self.assertTrue(resolver.update_user(uid, new_params))

    @responses.activate
    def test_20_update_user_fails(self):
        resolver = self.set_up_resolver()
        uid = "87d349ed-44d7-43e1-9a83-5f2406dee5bd"
        new_params = {"surname": "Smith"}

        # No permission
        responses.add(responses.PATCH, f"https://graph.microsoft.com/v1.0/users/{uid}", status=403,
                      body="""{"error": {"code": "Authorization_RequestDenied", 
                               "message": "Insufficient privileges to complete the operation."}}""")
        self.assertFalse(resolver.update_user(uid, new_params))

        # User does not exist
        responses.add(responses.PATCH, f"https://graph.microsoft.com/v1.0/users/{uid}", status=404,
                      body="""{"error": {"code": "Request_ResourceNotFound", "message": "Resource not found."}}""")
        self.assertFalse(resolver.update_user(uid, new_params))

        # Error without error message
        responses.add(responses.PATCH, f"https://graph.microsoft.com/v1.0/users/{uid}", status=400, body="{}")
        self.assertFalse(resolver.update_user(uid, new_params))

    @responses.activate
    def test_21_delete_user_success(self):
        resolver = self.set_up_resolver()
        uid = "87d349ed-44d7-43e1-9a83-5f2406dee5bd"

        responses.add(responses.DELETE, f"https://graph.microsoft.com/v1.0/users/{uid}", status=204)

        self.assertTrue(resolver.delete_user(uid))

    @responses.activate
    def test_22_delete_user_fails(self):
        resolver = self.set_up_resolver()
        uid = "87d349ed-44d7-43e1-9a83-5f2406dee5bd"

        # No permission
        responses.add(responses.DELETE, f"https://graph.microsoft.com/v1.0/users/{uid}", status=403,
                      body="""{"error": {"code": "Authorization_RequestDenied", 
                               "message": "Insufficient privileges to complete the operation."}}""")
        self.assertFalse(resolver.delete_user(uid))

        # User does not exist
        responses.add(responses.DELETE, f"https://graph.microsoft.com/v1.0/users/{uid}", status=404,
                      body="""{"error": {"code": "Request_ResourceNotFound", "message": "Resource not found."}}""")
        self.assertFalse(resolver.delete_user(uid))

        # Error with different error message format
        responses.add(responses.DELETE, f"https://graph.microsoft.com/v1.0/users/{uid}", status=400,
                      body="""{"success": false, "description": "User not found"}""")
        self.assertFalse(resolver.delete_user(uid))

    def check_pass_callback(self, request):
        params = {x.split("=")[0]: x.split("=")[1] for x in request.body.split("&")}
        if params.get("username") == "testuser" and params.get("password") == "testpassword" and params.get(
                "client_id") == "1234" and params.get("client_secret") == "secret" and params.get(
            "grant_type") == "password":
            return 200, {}, json.dumps({"token_type": "Bearer", "access_token": "12345"})
        else:
            return 400, {}, json.dumps({"error": "invalid_grant",
                                        "error_description": "Error validating credentials due to invalid username or password."})

    @responses.activate
    def test_23_check_pass_success(self):
        resolver = self.set_up_resolver()

        # Mock user auth
        responses.add_callback(responses.POST, "https://login.microsoftonline.com/organization/oauth2/v2.0/token",
                               callback=self.check_pass_callback)

        self.assertTrue(resolver.checkPass("111-aaa-333", "testpassword", "testuser"))

    @responses.activate
    def test_24_check_pass_fails(self):
        resolver = self.set_up_resolver()

        # Mock user auth
        responses.add_callback(responses.POST, "https://login.microsoftonline.com/organization/oauth2/v2.0/token",
                               callback=self.check_pass_callback)
        self.assertFalse(resolver.checkPass("111-aaa-333", "wrong_password", "testuser"))

        # Error with different format
        responses.add(responses.POST, "https://login.microsoftonline.com/organization/oauth2/v2.0/token",
                      status=400, body="""{"success": false, "description": "Invalid credentials"}""")
        self.assertFalse(resolver.checkPass("111-aaa-333", "wrong_password", "testuser"))

        # Custom error handling
        resolver.config_user_auth[HAS_ERROR_HANDLER] = True
        resolver.config_user_auth[ERROR_RESPONSE] = {"success": False, "description": "Invalid credentials"}
        responses.add(responses.POST, "https://login.microsoftonline.com/organization/oauth2/v2.0/token",
                      status=200, body="""{"success": false, "description": "Invalid credentials"}""")
        self.assertFalse(resolver.checkPass("111-aaa-333", "wrong_password", "testuser"))

        # checkPass is not supported when using certificate as client credential
        resolver = self.set_up_resolver({CLIENT_CREDENTIAL_TYPE: ClientCredentialType.CERTIFICATE.value,
                                         CLIENT_CERTIFICATE: {PRIVATE_KEY_FILE: "tests/testdata/private.pem",
                                                              CERTIFICATE_FINGERPRINT: "123456"}})
        with pytest.raises(ResolverError,
                           match="User authentication with password is not supported when using a certificate for the client"):
            resolver.checkPass("111-aaa-333", "testpassword", "testuser")


class KeycloakResolverTestCase(MyTestCase):

    def set_up_resolver(self):
        resolver = KeycloakResolver()
        config_authorization = copy.deepcopy(resolver.authorization_config)
        config_authorization[ENDPOINT] = "http://localhost:8080/auth/realms/master/protocol/openid-connect/token"
        resolver.loadConfig({CONFIG_AUTHORIZATION: config_authorization, USERNAME: "testuser", PASSWORD: "testpassword",
                             VERIFY_TLS: False, REALM: "master"})

        # Mock response for access token
        def request_callback(request):
            parameters = {x.split("=")[0]: x.split("=")[1] for x in request.body.split("&")}
            if parameters.get("username") == "testuser" and parameters.get("password") == "testpassword":
                status_code = 200
                resp_body = {"access_token": "123456789", "expires_in": 60}
            else:
                status_code = 401
                resp_body = {"error_description": "Invalid user credentials!"}
            return status_code, {}, json.dumps(resp_body)

        responses.add_callback(responses.POST, "http://localhost:8080/auth/realms/master/protocol/openid-connect/token",
                               callback=request_callback)

        return resolver

    def test_01_load_config(self):
        resolver = KeycloakResolver()

        # Check default values
        self.assertEqual({METHOD: "GET", ENDPOINT: "/admin/realms/{realm}/users/{userid}"},
                         resolver.config_get_user_by_id)
        self.assertEqual("", resolver.wildcard)
        self.assertEqual("POST", resolver.authorization_config[METHOD])
        self.assertEqual('{"Content-Type": "application/x-www-form-urlencoded"}',
                         resolver.authorization_config[HEADERS])

        # update config
        config = {CONFIG_AUTHORIZATION: {METHOD: "GET",
                                         HEADERS: '{"Content-Type": "application/json"}'}}
        resolver.loadConfig(config)

        # Load completely replaces the access token config
        self.assertEqual("GET", resolver.authorization_config[METHOD])
        self.assertEqual('{"Content-Type": "application/json"}',
                         resolver.authorization_config[HEADERS])
        self.assertNotIn(REQUEST_MAPPING, resolver.authorization_config.keys())
        # Other configs should not be changed
        self.assertEqual({METHOD: "GET", ENDPOINT: "/admin/realms/{realm}/users/{userid}"},
                         resolver.config_get_user_by_id)
        self.assertEqual("", resolver.wildcard)

    @responses.activate
    def test_02_get_auth_header(self):
        resolver = self.set_up_resolver()

        # success
        auth_header = resolver._get_auth_header()
        self.assertEqual("Bearer 123456789", auth_header["Authorization"])

        # Fails
        resolver.password = "wrong"
        self.assertRaises(ResolverError, resolver._get_auth_header)
        resolver.password = "testpassword"

        # Unexpected error response
        responses.add(responses.POST, "http://localhost:8080/auth/realms/master/protocol/openid-connect/token",
                      status=400, body='{"value": "Bad Request"}')
        self.assertRaises(ResolverError, resolver._get_auth_header)

        # Custom error handling
        resolver.authorization_config[HAS_ERROR_HANDLER] = True
        resolver.authorization_config[ERROR_RESPONSE] = {}
        responses.add(responses.POST, "http://localhost:8080/auth/realms/master/protocol/openid-connect/token",
                      status=200, body='{}')
        self.assertRaises(ResolverError, resolver._get_auth_header)

    @responses.activate
    def test_03_getUserList_success(self):
        resolver = self.set_up_resolver()

        # Mock users API
        responses.add(responses.GET, "http://localhost:8080/admin/realms/master/users", status=200,
                      body="""[{"username": "elizabeth", "firstName": "Elizabeth", "lastName": "Zott", 
                                "id": "6ea91a8d-e32e-41a1-b7bd-d2d185eed0e0"},
                                {"username": "albert", "firstName": "Albert", "lastName": "Einstein",
                                 "id": "4562bcc8-c436-4f95-b7c0-4f8ce89dca5e"}]""")

        user_list = resolver.getUserList()
        self.assertEqual(2, len(user_list))

    @responses.activate
    def test_04_getUserList_fails(self):
        # Could not get access token
        resolver = self.set_up_resolver()
        resolver.password = "wrong"
        self.assertRaises(ResolverError, resolver.getUserList)
        resolver.password = "testpassword"

        # Mock response for invalid access token or missing rights
        responses.add(responses.GET, "http://localhost:8080/admin/realms/master/users", status=403,
                      body='{"error": "Unauthorized", "error_description": "Invalid access token"}')
        self.assertRaises(ResolverError, resolver.getUserList)

        # Mock response for unknown error
        responses.add(responses.GET, "http://localhost:8080/admin/realms/master/users", status=400,
                      body='{"description": "Bad Request"}')
        self.assertRaises(ResolverError, resolver.getUserList)

        # Custom error handling
        resolver.config[CONFIG_GET_USER_LIST][HAS_ERROR_HANDLER] = True
        resolver.config[CONFIG_GET_USER_LIST][ERROR_RESPONSE] = {}
        responses.add(responses.GET, "http://localhost:8080/admin/realms/master/users", status=200,
                      body='{}')
        self.assertRaises(ResolverError, resolver.getUserList)

    @responses.activate
    def test_05_getUserInfo_success(self):
        resolver = self.set_up_resolver()
        user_id = "6ea91a8d-e32e-41a1-b7bd-d2d185eed0e0"

        # Mock users API
        responses.add(responses.GET, f"http://localhost:8080/admin/realms/master/users/{user_id}", status=200,
                      body="""{"username": "elizabeth", "firstName": "Elizabeth", "lastName": "Zott",
                                "id": "6ea91a8d-e32e-41a1-b7bd-d2d185eed0e0"}""")

        user_info = resolver.getUserInfo(user_id)
        self.assertEqual(user_id, user_info["userid"])
        self.assertEqual("elizabeth", user_info["username"])
        self.assertEqual("Elizabeth", user_info["givenname"])
        self.assertEqual("Zott", user_info["surname"])

    @responses.activate
    def test_06_getUserInfo_fails(self):
        resolver = self.set_up_resolver()
        user_id = "6ea91a8d-e32e-41a1-b7bd-d2d185eed0e0"

        # Mock users API: Unknown user ID
        responses.add(responses.GET, f"http://localhost:8080/admin/realms/master/users/{user_id}", status=404,
                      body='{"error": "User not found", "error_description": "User not found"}')
        self.assertDictEqual({}, resolver.getUserInfo(user_id))
        responses.add(responses.GET, f"http://localhost:8080/admin/realms/master/users/{user_id}", status=400,
                      body='{"error": "User not found", "error_description": "User not found"}')
        self.assertDictEqual({}, resolver.getUserInfo(user_id))

        # Unknown error response
        responses.add(responses.GET, f"http://localhost:8080/admin/realms/master/users/{user_id}", status=500,
                      body='{"description": "Internal Server Error"}')
        self.assertDictEqual({}, resolver.getUserInfo(user_id))

        # Custom error handling
        resolver.config[CONFIG_GET_USER_BY_ID][HAS_ERROR_HANDLER] = True
        resolver.config[CONFIG_GET_USER_BY_ID][ERROR_RESPONSE] = {}
        responses.add(responses.GET, f"http://localhost:8080/admin/realms/master/users/{user_id}", status=200,
                      body='{}')
        self.assertDictEqual({}, resolver.getUserInfo(user_id))

    @responses.activate
    def test_07_getUsername(self):
        resolver = self.set_up_resolver()
        user_id = "6ea91a8d-e32e-41a1-b7bd-d2d185eed0e0"

        # Mock users API success
        responses.add(responses.GET, f"http://localhost:8080/admin/realms/master/users/{user_id}", status=200,
                      body="""{"username": "elizabeth", "firstName": "Elizabeth", "lastName": "Zott",
                                "id": "6ea91a8d-e32e-41a1-b7bd-d2d185eed0e0"}""")

        username = resolver.getUsername(user_id)
        self.assertEqual("elizabeth", username)

        # Mock users API: Unknown user ID
        responses.add(responses.GET, f"http://localhost:8080/admin/realms/master/users/{user_id}", status=404,
                      body='{"error": "User not found", "error_description": "User not found"}')
        username = resolver.getUsername(user_id)
        self.assertEqual("", username)

    @responses.activate
    def test_08_getUserId(self):
        resolver = self.set_up_resolver()
        user_name = "elizabeth"

        # Mock users API: found one matching user
        responses.add(responses.GET, "http://localhost:8080/admin/realms/master/users", status=200,
                      body="""[{"username": "elizabeth", "firstName": "Elizabeth", "lastName": "Zott",
                      "id": "6ea91a8d-e32e-41a1-b7bd-d2d185eed0e0"}]""")
        user_id = resolver.getUserId(user_name)
        self.assertEqual("6ea91a8d-e32e-41a1-b7bd-d2d185eed0e0", user_id)

        # Mock users API: found no matching user
        responses.add(responses.GET, f"http://localhost:8080/admin/realms/master/users", status=200, body="[]")
        user_id = resolver.getUserId(user_name)
        self.assertEqual("", user_id)

        # Mock users API: found multiple matching users
        responses.add(responses.GET, "http://localhost:8080/admin/realms/master/users", status=200,
                      body="""[{"username": "elizabeth", "firstName": "Elizabeth", "lastName": "Zott",
                                "id": "6ea91a8d-e32e-41a1-b7bd-d2d185eed0e0"},
                                {"username": "elizabeth", "firstName": "Elizabeth", "lastName": "Smith",
                                 "id": "4562bcc8-c436-4f95-b7c0-4f8ce89dca5e"}]""")
        self.assertRaises(ResolverError, resolver.getUserId, user_name)

    def test_09_getResolverClassDescriptor(self):
        descriptor = KeycloakResolver().getResolverClassDescriptor()

        self.assertIn("keycloakresolver", descriptor)
        self.assertTrue(descriptor["keycloakresolver"]["clazz"].endswith("KeycloakResolver"))

    def test_10_get_config(self):
        resolver = KeycloakResolver()

        # check default config
        default_config = resolver.get_config()
        self.assertDictEqual({}, default_config[HEADERS])
        self.assertFalse(default_config[EDITABLE])
        self.assertTrue(default_config[VERIFY_TLS])
        self.assertTrue(default_config[ADVANCED])
        self.assertEqual("keycloakresolver", default_config["type"])
        self.assertIn(CONFIG_GET_USER_BY_ID, default_config)
        self.assertIn(CONFIG_GET_USER_LIST, default_config)
        self.assertIn(CONFIG_GET_USER_BY_NAME, default_config)
        self.assertIn(ATTRIBUTE_MAPPING, default_config)
        self.assertEqual("http://localhost:8080", default_config[BASE_URL])
        self.assertIn(CONFIG_AUTHORIZATION, default_config)
        self.assertNotIn(USERNAME, default_config)
        self.assertNotIn(PASSWORD, default_config)

        # If we setup a resolver, the new data will be included, but credentials are only returned censored
        resolver = self.set_up_resolver()
        config = resolver.get_config()
        self.assertIn(USERNAME, config)
        self.assertEqual("__CENSORED__", config[PASSWORD])

    # Mock response for access token
    @staticmethod
    def add_user_callback(request):
        parameters = json.loads(request.body)
        status_code = 201
        resp_body = {"id": "6ea91a8d-e32e-41a1-b7bd-d2d185eed0e0",
                     "username": parameters.get("username"),
                     "firstName": parameters.get("firstName"),
                     "lastName": parameters.get("lastName"),
                     "email": parameters.get("email")}

        # check for required parameters
        if not parameters.get("username"):
            status_code = 400
            resp_body = {"errorMessage": "User name is missing"}
        return status_code, {}, json.dumps(resp_body)

    @responses.activate
    def test_11_add_user_success(self):
        resolver = self.set_up_resolver()

        responses.add_callback(responses.POST, "http://localhost:8080/admin/realms/master/users",
                               callback=self.add_user_callback)
        # After creating the user we need to fetch the user id
        responses.add(responses.GET, "http://localhost:8080/admin/realms/master/users", status=200,
                      body="""[{"username": "ezott", "firstName": "Elizabeth", "lastName": "Zott", 
                      "id": "6ea91a8d-e32e-41a1-b7bd-d2d185eed0e0"}]""")

        user_data = {"username": "ezott",
                     "givenname": "Elizabeth",
                     "surname": "Zott"}

        uid = resolver.add_user(user_data)
        self.assertEqual("6ea91a8d-e32e-41a1-b7bd-d2d185eed0e0", uid)

    @responses.activate
    def test_12_add_user_fails(self):
        resolver = self.set_up_resolver()

        responses.add_callback(responses.POST, "http://localhost:8080/admin/realms/master/users",
                               callback=self.add_user_callback)

        user_data = {"givenname": "Elizabeth",
                     "surname": "Zott"}

        # Missing required username
        self.assertRaises(ResolverError, resolver.add_user, user_data)

        # username already exists
        responses.add(responses.POST, "http://localhost:8080/admin/realms/master/users", status=409,
                      body="""{"errorMessage": "User already exists"}""")
        self.assertRaises(ResolverError, resolver.add_user, user_data)

        # No permission
        responses.add(responses.POST, "http://localhost:8080/admin/realms/master/users", status=403,
                      body="""{"errorMessage": "No permission to create user"}""")
        self.assertRaises(ResolverError, resolver.add_user, user_data)

        # Unknown error response
        responses.add(responses.POST, "http://localhost:8080/admin/realms/master/users", status=500,
                      body="""{"description": "Internal Server Error"}""")
        self.assertRaises(ResolverError, resolver.add_user, user_data)

        # Custom error handling
        resolver.config[CONFIG_CREATE_USER][HAS_ERROR_HANDLER] = True
        resolver.config[CONFIG_CREATE_USER][ERROR_RESPONSE] = {"success": False, "message": "User already exists"}
        responses.add(responses.POST, "http://localhost:8080/admin/realms/master/users", status=201,
                      body="""{"success": false, "message": "User already exists"}""")
        self.assertRaises(ResolverError, resolver.add_user, user_data)

    @responses.activate
    def test_13_update_user_success(self):
        resolver = self.set_up_resolver()
        uid = "87d349ed-44d7-43e1-9a83-5f2406dee5bd"

        def callback(request):
            parameters = json.loads(request.body)
            # Unknown attributes should not be included + attributes should be mapped correctly
            self.assertDictEqual({"lastName": "Smith"}, parameters)
            return 204, {}, None

        responses.add_callback(responses.PUT, f"http://localhost:8080/admin/realms/master/users/{uid}",
                               callback=callback)

        new_params = {"surname": "Smith", "favorite_color": "blue"}
        self.assertTrue(resolver.update_user(uid, new_params))

    @responses.activate
    def test_14_update_user_fails(self):
        resolver = self.set_up_resolver()
        uid = "87d349ed-44d7-43e1-9a83-5f2406dee5bd"
        new_params = {"surname": "Smith"}

        # No permission
        responses.add(responses.PUT, f"http://localhost:8080/admin/realms/master/users/{uid}", status=403,
                      body="""{"errorMessage": "No permission to update user"}""")
        self.assertFalse(resolver.update_user(uid, new_params))

        # User does not exist
        responses.add(responses.PUT, f"http://localhost:8080/admin/realms/master/users/{uid}", status=404,
                      body="""{"error": "User not found"}""")
        self.assertFalse(resolver.update_user(uid, new_params))

        # Error without unknown error message
        responses.add(responses.PUT, f"http://localhost:8080/admin/realms/master/users/{uid}", status=500,
                      body="""{"description": "Internal Server Error"}""")
        self.assertFalse(resolver.update_user(uid, new_params))

        # custom error handling
        resolver.config[CONFIG_EDIT_USER][HAS_ERROR_HANDLER] = True
        resolver.config[CONFIG_EDIT_USER][ERROR_RESPONSE] = {"success": False, "message": "User not found"}
        responses.add(responses.PUT, f"http://localhost:8080/admin/realms/master/users/{uid}", status=200,
                      body="""{"success": false, "message": "User not found"}""")
        self.assertFalse(resolver.update_user(uid, new_params))

    @responses.activate
    def test_15_delete_user_success(self):
        resolver = self.set_up_resolver()
        uid = "87d349ed-44d7-43e1-9a83-5f2406dee5bd"

        responses.add(responses.DELETE, f"http://localhost:8080/admin/realms/master/users/{uid}", status=204)

        self.assertTrue(resolver.delete_user(uid))

    @responses.activate
    def test_16_delete_user_fails(self):
        resolver = self.set_up_resolver()
        uid = "87d349ed-44d7-43e1-9a83-5f2406dee5bd"

        # No permission
        responses.add(responses.DELETE, f"http://localhost:8080/admin/realms/master/users/{uid}", status=403,
                      body="""{"errorMessage": "No permission to delete user"}""")
        self.assertFalse(resolver.delete_user(uid))

        # User does not exist
        responses.add(responses.DELETE, f"http://localhost:8080/admin/realms/master/users/{uid}", status=404,
                      body="""{"error": "User not found"}""")
        self.assertFalse(resolver.delete_user(uid))

        # Error with different error message format
        responses.add(responses.DELETE, f"http://localhost:8080/admin/realms/master/users/{uid}", status=400,
                      body="""{"success": false, "description": "User not found"}""")
        self.assertFalse(resolver.delete_user(uid))

        # Custom error handling
        resolver.config[CONFIG_DELETE_USER][HAS_ERROR_HANDLER] = True
        resolver.config[CONFIG_DELETE_USER][ERROR_RESPONSE] = {"success": False, "message": "User not found"}
        responses.add(responses.DELETE, f"http://localhost:8080/admin/realms/master/users/{uid}", status=200,
                      body="""{"success": false, "message": "User not found"}""")

    def check_pass_callback(self, request):
        params = {x.split("=")[0]: x.split("=")[1] for x in request.body.split("&")}
        if params.get("username") == "testuser" and params.get("password") == "testpassword" and params.get(
                "grant_type") == "password" and params.get("client_id") == "admin-cli":
            return 200, {}, json.dumps({"token_type": "Bearer", "access_token": "12345"})
        else:
            return 401, {}, json.dumps({"error": "invalid_grant",
                                        "error_description": "Invalid user credentials"})

    @responses.activate
    def test_17_check_pass_success(self):
        resolver = self.set_up_resolver()

        # Mock user auth
        responses.add_callback(responses.POST, "http://localhost:8080/realms/master/protocol/openid-connect/token",
                               callback=self.check_pass_callback)

        self.assertTrue(resolver.checkPass("111-aaa-333", "testpassword", "testuser"))

    @responses.activate
    def test_18_check_pass_fails(self):
        resolver = self.set_up_resolver()

        # Mock user auth
        responses.add_callback(responses.POST, "http://localhost:8080/realms/master/protocol/openid-connect/token",
                               callback=self.check_pass_callback)
        self.assertFalse(resolver.checkPass("111-aaa-333", "wrongPassword", "testuser"))

        # Error with different format
        responses.add(responses.POST, "http://localhost:8080/realms/master/protocol/openid-connect/token",
                      status=400, body="""{"success": false, "description": "Invalid credentials"}""")
        self.assertFalse(resolver.checkPass("111-aaa-333", "wrongPassword", "testuser"))

        # Custom error handling
        resolver.config_user_auth[HAS_ERROR_HANDLER] = True
        resolver.config_user_auth[ERROR_RESPONSE] = {"success": False, "description": "Invalid credentials"}
        responses.add(responses.POST, "http://localhost:8080/realms/master/protocol/openid-connect/token",
                      status=200, body="""{"success": false, "description": "Invalid credentials"}""")
        self.assertFalse(resolver.checkPass("111-aaa-333", "wrongPassword", "testuser"))

    @responses.activate
    def test_19_testconnection(self):
        params = {USERNAME: "testuser", PASSWORD: "testpassword", VERIFY_TLS: False, REALM: "master", EDITABLE: True}

        # Mock responses
        responses.add(responses.POST, "http://localhost:8080/realms/master/protocol/openid-connect/token", status=200,
                      body="""{"access_token": "123456789", "expires_in": 60}""")
        # Get user by id
        responses.add(responses.GET,
                      "http://localhost:8080/admin/realms/master/users/6ea91a8d-e32e-41a1-b7bd-d2d185eed0e0",
                      status=200, body="""{"username": "elizabeth", "firstName": "Elizabeth", "lastName": "Zott", 
                                            "id": "6ea91a8d-e32e-41a1-b7bd-d2d185eed0e0"}""")

        def user_list_callback(request):
            # This callback is used to mock the response for the user list request
            if "elizabeth" in request.url:
                body = """[{"username": "elizabeth",
                                      "firstName": "Elizabeth",
                                      "lastName": "Zott",
                                      "id": "6ea91a8d-e32e-41a1-b7bd-d2d185eed0e0"}]"""
            else:
                body = """[{"username": "elizabeth",
                            "firstName": "Elizabeth",
                            "lastName": "Zott",
                            "id": "6ea91a8d-e32e-41a1-b7bd-d2d185eed0e0"},
                            {"username": "albert",
                             "firstName": "Albert",
                             "lastName": "Einstein",
                             "id": "4562bcc8-c436-4f95-b7c0-4f8ce89dca5e"}]"""
            return 200, {}, body

        # Get user by name
        responses.add_callback(responses.GET, "http://localhost:8080/admin/realms/master/users",
                               callback=user_list_callback)

        # Success
        params["test_userid"] = "6ea91a8d-e32e-41a1-b7bd-d2d185eed0e0"
        params["test_username"] = "elizabeth"
        success, description = KeycloakResolver.testconnection(params)
        self.assertTrue(success)

        # Invalid delete config
        params[CONFIG_DELETE_USER] = {ENDPOINT: "/users/{userid}"}
        success, description = KeycloakResolver.testconnection(params)
        self.assertFalse(success)
        self.assertIn("Failed to load delete user config", description)
        del params[CONFIG_DELETE_USER]

        # Invalid Edit config
        params[CONFIG_EDIT_USER] = {METHOD: "random", ENDPOINT: "/users/{userid}"}
        success, description = KeycloakResolver.testconnection(params)
        self.assertFalse(success)
        self.assertIn("Failed to load edit user config", description)
        del params[CONFIG_EDIT_USER]

        # Invalid Edit config
        params[CONFIG_CREATE_USER] = {METHOD: "post", ENDPOINT: "/users/", REQUEST_MAPPING: "{'enabled': True}"}
        success, description = KeycloakResolver.testconnection(params)
        self.assertFalse(success)
        self.assertIn("Failed to load create user config", description)
        del params[CONFIG_CREATE_USER]

        # Invalid check user password config
        params[CONFIG_USER_AUTH] = {METHOD: "post"}
        success, description = KeycloakResolver.testconnection(params)
        self.assertFalse(success)
        self.assertIn("Failed to load config to check user password", description)
        del params[CONFIG_USER_AUTH]

        # No user found for username
        responses.add(responses.GET, "http://localhost:8080/admin/realms/master/users", status=200, body="[]")
        success, description = KeycloakResolver.testconnection(params)
        self.assertFalse(success)
        self.assertIn("No user found for username 'elizabeth'", description)

        # Invalid request to get user list
        responses.add(responses.GET, "http://localhost:8080/admin/realms/master/users", status=400,
                      body='{"errorMessage": "Invalid request"}')
        del params["test_username"]
        success, description = KeycloakResolver.testconnection(params)
        self.assertFalse(success)
        self.assertIn("Failed to get user list", description)

        # No user found for id
        responses.add(responses.GET,
                      "http://localhost:8080/admin/realms/master/users/6ea91a8d-e32e-41a1-b7bd-d2d185eed0e0",
                      status=400, body="""{"errorMessage": "Invalid request"}""")
        success, description = KeycloakResolver.testconnection(params)
        self.assertFalse(success)
        self.assertIn("No user found for user ID", description)

        # Invalid credentials to get authorization token
        responses.add(responses.POST, "http://localhost:8080/realms/master/protocol/openid-connect/token",
                      status=400, body="""{"errorMessage": "invalid credentials"}""")
        success, description = KeycloakResolver.testconnection(params)
        self.assertFalse(success)
        self.assertIn("Failed to get authorization header", description)
