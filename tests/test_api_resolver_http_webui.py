# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
An HTTP resolver keeps working when it is saved with request configurations that name no endpoint, as a form posts
the requests the administrator left empty.
"""
import responses

from privacyidea.lib.realm import set_realm, delete_realm
from privacyidea.lib.resolver import save_resolver, delete_resolver, get_resolver_object, get_resolver_config
from privacyidea.lib.token import init_token, get_tokens, remove_token
from privacyidea.lib.user import User
from .base import MyApiTestCase

USER_STORE_URL = "https://userstore.example/users"
ALICE = {"username": "alice", "userid": "alice", "email": "alice@example.com", "givenname": "Alice"}

BASIC_CONFIG = {
    "endpoint": USER_STORE_URL + "/{userid}",
    "method": "GET",
    "headers": '{"Content-Type": "application/json"}',
    "requestMapping": '{"id": "{userid}"}',
    "responseMapping": '{"username": "{username}", "userid": "{userid}", "email": "{email}", '
                       '"givenname": "{givenname}"}',
}

ADVANCED_CONFIG = {
    "base_url": "https://userstore.example",
    "attribute_mapping": {"username": "username", "userid": "userid", "email": "email", "givenname": "givenname"},
    "config_get_user_by_id": {"method": "GET", "endpoint": "/users/{userid}"},
    "config_get_user_by_name": {"method": "GET", "endpoint": "/users/{username}"},
}

EMPTY_REQUEST_CONFIG = {"method": "GET", "endpoint": "", "headers": "", "requestMapping": "", "responseMapping": "",
                        "hasSpecialErrorHandler": False, "errorResponse": ""}
REQUEST_CONFIG_KEYS = ["config_authorization", "config_user_auth", "config_get_user_list", "config_get_user_by_id",
                       "config_get_user_by_name", "config_create_user", "config_edit_user", "config_delete_user"]


def payload_with_empty_requests(stored: dict) -> dict:
    """
    The stored data with every request configuration, the ones the administrator left empty posted with an empty
    endpoint, and the default attribute mapping of the form.
    """
    payload = {"type": "httpresolver", **stored,
               "attribute_mapping": stored.get("attribute_mapping") or {"userid": "userid", "givenname": "givenname"}}
    for key in REQUEST_CONFIG_KEYS:
        payload[key] = dict(EMPTY_REQUEST_CONFIG, **stored.get(key, {}))
    return payload


def basic_form_payload(stored: dict) -> dict:
    """
    What the WebUI posts for a basic resolver: the basic fields, and an empty object for every request configuration
    and the attribute mapping, which removes them.
    """
    payload = {"type": "httpresolver", **stored, **{key: stored[key] for key in BASIC_CONFIG},
               "hasSpecialErrorHandler": False, "errorResponse": "", "Editable": False, "attribute_mapping": {}}
    for key in REQUEST_CONFIG_KEYS:
        payload[key] = {}
    return payload


class HTTPResolverEmptyRequestsTestCase(MyApiTestCase):

    def tearDown(self) -> None:
        for token in get_tokens(realm="wrealm"):
            remove_token(token.token.serial)
        delete_realm("wrealm")
        delete_resolver("whttp")
        super().tearDown()

    def _create_resolver(self, config: dict) -> None:
        save_resolver({"resolver": "whttp", "type": "httpresolver", **config})
        set_realm("wrealm", resolvers=[{"name": "whttp"}])
        init_token({"type": "spass", "pin": "alicepin"}, user=User("alice", "wrealm"))

    def _save(self, payload: dict) -> None:
        with self.app.test_request_context("/resolver/whttp", method="POST", json=payload,
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
        self.assertEqual(200, res.status_code, res.json)
        # The next request starts with a fresh request-local store and loads the resolver again
        self.reset_flask_g()

    def _assert_login_works(self) -> None:
        with self.app.test_request_context("/validate/check", method="POST",
                                           data={"user": "alice", "realm": "wrealm", "pass": "alicepin"}):
            res = self.app.full_dispatch_request()
        self.assertEqual(200, res.status_code, res.json)
        self.assertTrue(res.json["result"]["value"], res.json)

    @responses.activate
    def test_01_basic_resolver_with_empty_requests_resolves_users(self):
        responses.add(responses.GET, USER_STORE_URL + "/alice", json=ALICE)
        self._create_resolver(BASIC_CONFIG)
        self._save(payload_with_empty_requests(get_resolver_config("whttp")))

        resolver = get_resolver_object("whttp")
        self.assertEqual("alice", resolver.getUserId("alice"))
        self.assertEqual(ALICE, resolver.get_user_info("alice"))
        self._assert_login_works()

    @responses.activate
    def test_02_advanced_resolver_skips_requests_without_endpoint(self):
        responses.add(responses.GET, USER_STORE_URL + "/alice", json=ALICE)
        self._create_resolver(ADVANCED_CONFIG)
        self._save(payload_with_empty_requests(get_resolver_config("whttp")))

        resolver = get_resolver_object("whttp")
        self.assertEqual(ALICE, resolver.get_user_info("alice"))
        # No user list request configured: an empty list, as for a resolver without this request
        self.assertEqual([], resolver.getUserList({"username": "*"}))
        self._assert_login_works()

    @responses.activate
    def test_03_basic_form_payload_removes_empty_requests(self):
        responses.add(responses.GET, USER_STORE_URL + "/alice", json=ALICE)
        self._create_resolver(BASIC_CONFIG)
        self._save(payload_with_empty_requests(get_resolver_config("whttp")))
        self._save(basic_form_payload(get_resolver_config("whttp")))

        stored = get_resolver_config("whttp")
        self.assertEqual([], [key for key in REQUEST_CONFIG_KEYS if key in stored])
        self.assertNotIn("attribute_mapping", stored)
        self.assertEqual(ALICE, get_resolver_object("whttp").get_user_info("alice"))
        self._assert_login_works()
