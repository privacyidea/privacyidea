"""Shared bases for split test_api_container_*.py files."""
# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
import base64
import json
import mock
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

from typing import Optional

import passlib
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey

from privacyidea.lib.applications.offline import MachineApplication, REFILLTOKEN_LENGTH
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.container import (create_container_template, get_template_obj, delete_container_by_serial,
                                       get_container_realms, set_container_states, unregister)
from privacyidea.lib.container import (init_container, find_container_by_serial, add_token_to_container, assign_user,
                                       add_container_realms, remove_token_from_container)
from privacyidea.lib.containers.container_info import PI_INTERNAL, TokenContainerInfoData, RegistrationState
from privacyidea.lib.containers.container_states import ContainerStates
from privacyidea.lib.containers.smartphone import SmartphoneOptions
from privacyidea.lib.crypto import generate_keypair_ecc, decrypt_aes
from privacyidea.lib.error import Error
from privacyidea.lib.machine import attach_token
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policies.conditions import ConditionSection, ConditionHandleMissingData
from privacyidea.lib.policy import set_policy, SCOPE, delete_policy
from privacyidea.lib.privacyideaserver import add_privacyideaserver
from privacyidea.lib.realm import set_realm, set_default_realm
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.serviceid import set_serviceid
from privacyidea.lib.smsprovider.FirebaseProvider import FirebaseConfig
from privacyidea.lib.smsprovider.SMSProvider import set_smsgateway
from privacyidea.lib.token import (get_one_token, get_tokens_from_serial_or_user,
                                   get_tokeninfo, get_tokens)
from privacyidea.lib.token import init_token, get_tokens_paginate, unassign_token
from privacyidea.lib.tokens.papertoken import PAPERACTION
from privacyidea.lib.tokens.pushtoken import PushAction
from privacyidea.lib.tokens.tantoken import TANAction
from privacyidea.lib.user import User
from privacyidea.lib.utils.compare import PrimaryComparators
from privacyidea.models import Realm
from tests.base import MyApiTestCase
from tests.test_lib_tokencontainer import MockSmartphone

UNSPECIFIC_ERROR_MESSAGES: dict[str, str] = {
    "container/rollover": "Failed container rollover",
    "container/synchronize": "Failed container synchronization",
    "container/challenge": "Failed creating container challenge",
    "container/register/finalize": "Failed finalizing container registration",
    "container/register/terminate/client": "Failed terminating container registration",
}


class APIContainerTest(MyApiTestCase):
    FIREBASE_FILE = "tests/testdata/firebase-test.json"
    CLIENT_FILE = "tests/testdata/google-services.json"

    def clear_flask_g(self):
        if self.app_context.g:
            keys = [key for key in iter(self.app_context.g)]
            [self.app_context.g.pop(key) for key in keys]

    def request_assert_success(self, url, data: dict, auth_token, method='POST'):
        with self.app.test_request_context(url,
                                           method=method,
                                           data=data if method == 'POST' else None,
                                           query_string=data if method == 'GET' else None,
                                           headers={'Authorization': auth_token} if auth_token else None):
            res = self.app.full_dispatch_request()
            self.assertEqual(200, res.status_code, res.json)
            self.assertTrue(res.json["result"]["status"])
        self.clear_flask_g()
        return res.json

    def request_assert_error(self, status_code, url, data: dict, auth_token, method='POST',
                             error_code: Optional[int] = None,
                             error_message: Optional[str] = None,
                             try_unspecific: bool = False):
        with self.app.test_request_context(url,
                                           method=method,
                                           data=data if method == 'POST' else None,
                                           query_string=data if method == 'GET' else None,
                                           headers={'Authorization': auth_token} if auth_token else None):
            res = self.app.full_dispatch_request()
            self.assertEqual(status_code, res.status_code, res.json)
            self.assertFalse(res.json["result"]["status"])
            if error_code is not None:
                self.assertEqual(res.json["result"]["error"]["code"], error_code)
            if error_message is not None:
                self.assertEqual(res.json["result"]["error"]["message"], error_message)
        self.clear_flask_g()

        if try_unspecific:
            set_policy(name="hide_specific_error_message", scope=SCOPE.CONTAINER,
                       action=f"{PolicyAction.HIDE_SPECIFIC_ERROR_MESSAGE}=true")
            try:
                return self.request_assert_error(status_code, url, data, auth_token,
                                                 method=method, error_code=Error.CONTAINER,
                                                 error_message=UNSPECIFIC_ERROR_MESSAGES[url])
            finally:
                delete_policy("hide_specific_error_message")

        return res.json

    def request_assert_405(self, url, data: dict, auth_token, method='POST'):
        with self.app.test_request_context(url,
                                           method=method,
                                           data=data if method == 'POST' else None,
                                           query_string=data if method == 'GET' else None,
                                           headers={'Authorization': auth_token} if auth_token else None):
            res = self.app.full_dispatch_request()
            self.assertEqual(405, res.status_code, res.json)
        self.clear_flask_g()
        return res.json

    def request_assert_404_no_result(self, url, data: dict, auth_token, method='POST'):
        with self.app.test_request_context(url,
                                           method=method,
                                           data=data if method == 'POST' else None,
                                           query_string=data if method == 'GET' else None,
                                           headers={'Authorization': auth_token} if auth_token else None):
            res = self.app.full_dispatch_request()
            self.assertEqual(404, res.status_code, res.json)
        self.clear_flask_g()



class APIContainerAuthorization(APIContainerTest):
    def setUp(self):
        rid = save_resolver({"resolver": self.resolvername1,
                             "type": "passwdresolver",
                             "fileName": "tests/testdata/passwords"})
        self.assertGreater(rid, 0)

        (added, failed) = set_realm(self.realm1, [{'name': self.resolvername1}])
        self.assertEqual(0, len(failed))
        self.assertEqual(1, len(added))

        user = User(login="root",
                    realm=self.realm1,
                    resolver=self.resolvername1)

        user_str = "{0!s}".format(user)
        self.assertEqual("<root.resolver1@realm1>", user_str)

        self.assertFalse(user.is_empty())
        self.assertTrue(User().is_empty())

        user_repr = "{0!r}".format(user)
        expected = "User(login='root', realm='realm1', resolver='resolver1')"
        self.assertEqual(expected, user_repr)
        self.authenticate_selfservice_user()

    def request_denied_assert_403(self, url, data: dict, auth_token, method='POST',
                                  error_message: Optional[str] = None):
        with self.app.test_request_context(url,
                                           method=method,
                                           data=data if method == 'POST' else None,
                                           query_string=data if method == 'GET' else None,
                                           headers={'Authorization': auth_token} if auth_token else None):
            res = self.app.full_dispatch_request()
            self.assertEqual(403, res.status_code, res.json)
            self.assertEqual(res.json["result"]["error"]["code"], 303)
            if error_message is not None:
                self.assertEqual(res.json["result"]["error"]["message"], error_message)
        self.clear_flask_g()
        return res.json

    def create_container_for_user(self, ctype="generic"):
        set_policy("user_container_create", scope=SCOPE.USER, action=PolicyAction.CONTAINER_CREATE)
        with self.app.test_request_context('/container/init',
                                           method='POST',
                                           data={"type": ctype},
                                           headers={'Authorization': self.at_user}):
            res = self.app.full_dispatch_request()
            self.assertEqual(res.status_code, 200)
        container_serial = res.json["result"]["value"]["container_serial"]
        self.assertGreater(len(container_serial), 0)
        delete_policy("user_container_create")
        return container_serial



@dataclass
class SmartphoneRequests:
    mock_smph: MockSmartphone = MockSmartphone()
    response: dict = None
