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

from .api_container_common import (
    APIContainerTest,
    APIContainerAuthorization,
    SmartphoneRequests,
    UNSPECIFIC_ERROR_MESSAGES,
)


class APIContainerSynchronization(APIContainerTest):

    @classmethod
    def create_smartphone_for_user_and_realm(cls, user: User = None, realm_list: list = None):
        smartphone_serial = init_container({"type": "smartphone"})["container_serial"]
        smartphone = find_container_by_serial(smartphone_serial)
        if user:
            smartphone.add_user(user)
        if realm_list:
            smartphone.set_realms(realm_list, add=True)
        return smartphone

    def register_smartphone_success(self, smartphone_serial=None):
        set_policy("policy", scope=SCOPE.CONTAINER, action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.net/",
                                                            PolicyAction.CONTAINER_REGISTRATION_TTL: 24,
                                                            PolicyAction.CONTAINER_CHALLENGE_TTL: 1,
                                                            PolicyAction.CONTAINER_SSL_VERIFY: "True"}, priority=2)
        if not smartphone_serial:
            smartphone_serial = init_container({"type": "smartphone"})["container_serial"]
        data = {"container_serial": smartphone_serial,
                "passphrase_prompt": "Enter your passphrase",
                "passphrase_response": "top_secret"}

        # Initialize
        result = self.request_assert_success('container/register/initialize',
                                             data,
                                             self.at, 'POST')
        # Check if the response contains the expected values
        init_response_data = result["result"]["value"]
        self.assertIn("container_url", init_response_data)
        self.assertIn("nonce", init_response_data)
        self.assertIn("time_stamp", init_response_data)
        self.assertIn("key_algorithm", init_response_data)
        self.assertIn("hash_algorithm", init_response_data)
        self.assertIn("ssl_verify", init_response_data)
        self.assertIn("ttl", init_response_data)
        self.assertIn("passphrase_prompt", init_response_data)
        self.assertIn("server_url", init_response_data)
        # Check if the url contains all relevant data
        qr_url = init_response_data["container_url"]["value"]
        self.assertIn(f"pia://container/{smartphone_serial}", qr_url)
        self.assertIn("issuer=privacyIDEA", qr_url)
        self.assertIn("ttl=24", qr_url)
        self.assertIn("ssl_verify=True", qr_url)
        self.assertIn("nonce=", qr_url)
        self.assertIn("time=", qr_url)
        self.assertIn("url=https%3A//pi.net/", qr_url)
        self.assertIn(f"serial={smartphone_serial}", qr_url)
        self.assertIn("key_algorithm=", qr_url)
        self.assertIn("hash_algorithm", qr_url)
        self.assertIn("passphrase=Enter%20your%20passphrase", qr_url)

        # check challenge
        challenges = get_challenges(serial=smartphone_serial)
        challenge = challenges[0] if len(challenges) == 1 else None
        self.assertIsNotNone(challenge)
        self.assertEqual(init_response_data["nonce"], challenge.challenge)
        # timestamp: we need to add the timezone for the challenge timestamp
        creation_time = datetime.fromisoformat(init_response_data["time_stamp"])
        self.assertEqual(creation_time, challenge.timestamp.replace(tzinfo=timezone.utc))
        time_delta_challenge = (challenge.expiration - challenge.timestamp).total_seconds()
        self.assertAlmostEqual(24 * 60, time_delta_challenge, 0)
        challenge_data = json.loads(challenge.data)
        self.assertEqual("https://pi.net/container/register/finalize", challenge_data["scope"])

        # Finalize
        mock_smph = MockSmartphone(device_brand="XY", device_model="ABC123")
        params = mock_smph.register_finalize(init_response_data["nonce"], init_response_data["time_stamp"],
                                             "https://pi.net/container/register/finalize", smartphone_serial,
                                             "top_secret")
        result = self.request_assert_success('container/register/finalize',
                                             params,
                                             None, 'POST')

        # Check if the response contains the expected values
        self.assertIn("policies", result["result"]["value"])

        delete_policy("policy")

        return SmartphoneRequests(mock_smph, result)

    def create_offline_token(self, serial, otps):
        # authenticate online initially
        token = get_tokens(serial=serial)[0]
        res = token.check_otp(otps[2])  # count = 2
        self.assertEqual(2, res)
        # check intermediate counter value
        self.assertEqual(3, token.token.count)

        attach_token(serial, "offline", machine_id=0, )

        auth_item = MachineApplication.get_authentication_item("hotp", serial)
        refilltoken = auth_item.get("refilltoken")
        self.assertEqual(len(refilltoken), REFILLTOKEN_LENGTH * 2)
        self.assertTrue(passlib.hash.pbkdf2_sha512.verify(otps[3],  # count = 3
                                                          auth_item.get("response").get(3)))
        self.assertTrue(passlib.hash.pbkdf2_sha512.verify(otps[8],  # count = 8
                                                          auth_item.get("response").get(8)))
        # The token now contains the refill token information:
        self.assertEqual(refilltoken, token.get_tokeninfo("refilltoken"))
        self.assertEqual(103, token.token.count)

    def test_01_register_smartphone_success(self):
        set_policy("client_policy", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER, priority=1)

        result = self.register_smartphone_success()

        # Check if the response contains the expected values
        self.assertIn("policies", result.response["result"]["value"])
        policies = result.response["result"]["value"]["policies"]
        self.assertTrue(policies[PolicyAction.CONTAINER_CLIENT_ROLLOVER])
        self.assertFalse(policies[PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER])
        self.assertFalse(policies[PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER])
        self.assertFalse(policies[PolicyAction.DISABLE_CLIENT_TOKEN_DELETION])

        delete_policy("client_policy")

    def test_02_register_smartphone_of_user(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        set_policy("another_policy", scope=SCOPE.CONTAINER,
                   action={PolicyAction.CONTAINER_SERVER_URL: "https://another-pi.net/",
                           PolicyAction.CONTAINER_REGISTRATION_TTL: 24},
                   realm=self.realm2)
        set_policy("low_prio_policy", scope=SCOPE.CONTAINER,
                   action={PolicyAction.CONTAINER_SERVER_URL: "https://pi-low_prio.net/",
                           PolicyAction.CONTAINER_REGISTRATION_TTL: 24},
                   realm=self.realm1, priority=2)
        set_policy("policy", scope=SCOPE.CONTAINER,
                   action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.net/",
                           PolicyAction.CONTAINER_REGISTRATION_TTL: 24},
                   realm=self.realm1, priority=1)
        smartphone_serial = init_container({"type": "smartphone",
                                            "user": "hans",
                                            "realm": self.realm1})["container_serial"]
        data = {"container_serial": smartphone_serial,
                "passphrase_prompt": "Enter your passphrase",
                "passphrase_response": "top_secret"}

        # Initialize
        result = self.request_assert_success('container/register/initialize',
                                             data,
                                             self.at, 'POST')
        init_response_data = result["result"]["value"]
        # Check if the url contains all relevant data
        qr_url = init_response_data["container_url"]["value"]
        self.assertIn("url=https%3A//pi.net/", qr_url)

        # Finalize
        mock_smph = MockSmartphone(device_brand="XY", device_model="ABC123")
        params = mock_smph.register_finalize(init_response_data["nonce"], init_response_data["time_stamp"],
                                             "https://pi.net/container/register/finalize", smartphone_serial,
                                             "top_secret")

        self.request_assert_success('container/register/finalize',
                                    params,
                                    None, 'POST')

        delete_policy("policy")
        delete_policy("another_policy")
        delete_policy("low_prio_policy")

    def test_03_register_init_fail(self):
        # Policy with server url not defined
        container_serial = init_container({"type": "smartphone"})["container_serial"]
        self.request_assert_error(403, 'container/register/initialize',
                                  {"container_serial": container_serial}, self.at, 'POST',
                                  error_code=303)

        # conflicting server url policies
        self.setUp_user_realms()
        self.setUp_user_realm2()
        set_policy("another_policy", scope=SCOPE.CONTAINER,
                   action={PolicyAction.CONTAINER_SERVER_URL: "https://another-pi.net/",
                           PolicyAction.CONTAINER_REGISTRATION_TTL: 24},
                   realm=self.realm2, priority=1)
        set_policy("policy", scope=SCOPE.CONTAINER,
                   action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.net/",
                           PolicyAction.CONTAINER_REGISTRATION_TTL: 24},
                   realm=self.realm1, priority=1)
        smartphone_serial = init_container({"type": "smartphone"})["container_serial"]
        data = {"container_serial": smartphone_serial,
                "passphrase_prompt": "Enter your passphrase",
                "passphrase_response": "top_secret"}

        self.request_assert_error(403, 'container/register/initialize',
                                  data, self.at, 'POST',
                                  error_code=303)
        delete_policy("another_policy")
        delete_container_by_serial(smartphone_serial)

        # Missing container serial
        self.request_assert_error(400, 'container/register/initialize',
                                  {}, self.at, 'POST',
                                  error_code=905,
                                  error_message="ERR905: Missing parameter: container_serial")

        # Invalid container serial
        self.request_assert_error(404, 'container/register/initialize',
                                  {"container_serial": "invalid_serial"}, self.at, 'POST',
                                  error_code=601)

        delete_policy("policy")

    def test_04_register_finalize_wrong_params(self):
        # Missing container serial
        self.request_assert_error(400, 'container/register/finalize',
                                  {"device_brand": "LG", "device_model": "ABC123"}, None, 'POST',
                                  error_code=905,
                                  error_message="ERR905: Missing parameter: container_serial",
                                  try_unspecific=False)

        # Invalid container serial
        self.request_assert_error(404, 'container/register/finalize',
                                  {"container_serial": "invalid_serial", "device_brand": "LG",
                                   "device_model": "ABC123"},
                                  None, 'POST',
                                  error_code=601,
                                  try_unspecific=True)

    def test_05_register_finalize_invalid_challenge(self):
        # Invalid challenge
        set_policy("policy", scope=SCOPE.CONTAINER, action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.net/",
                                                            PolicyAction.CONTAINER_REGISTRATION_TTL: 24})
        smartphone_serial = init_container({"type": "smartphone"})["container_serial"]
        data = {"container_serial": smartphone_serial,
                "passphrase_prompt": "Enter your passphrase",
                "passphrase_response": "top_secret"}
        # Initialize
        result = self.request_assert_success('container/register/initialize',
                                             data,
                                             self.at, 'POST')
        init_response_data = result["result"]["value"]
        # Finalize with invalid nonce
        mock_smph = MockSmartphone(device_brand="XY", device_model="ABC123")
        params = mock_smph.register_finalize("xxxxx", init_response_data["time_stamp"],
                                             "https://pi.net/container/register/finalize", smartphone_serial,
                                             "top_secret")

        self.request_assert_error(400, 'container/register/finalize', params,
                                  None, 'POST',
                                  error_code=3002,
                                  try_unspecific=True)

    def test_06_register_twice_fails(self):
        # register container successfully
        set_policy("policy", scope=SCOPE.CONTAINER, action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.net/",
                                                            PolicyAction.CONTAINER_REGISTRATION_TTL: 24})
        smartphone_serial = init_container({"type": "smartphone"})["container_serial"]
        data = {"container_serial": smartphone_serial,
                "passphrase_prompt": "Enter your passphrase",
                "passphrase_response": "top_secret"}

        # Initialize
        result = self.request_assert_success('container/register/initialize',
                                             data,
                                             self.at, 'POST')
        init_response_data = result["result"]["value"]

        # Finalize
        mock_smph = MockSmartphone(device_brand="XY", device_model="ABC123")
        params = mock_smph.register_finalize(init_response_data["nonce"], init_response_data["time_stamp"],
                                             "https://pi.net/container/register/finalize", smartphone_serial,
                                             "top_secret")

        self.request_assert_success('container/register/finalize',
                                    params, None, 'POST')

        # try register second time with same data
        self.request_assert_error(400, 'container/register/finalize',
                                  params, None, 'POST',
                                  try_unspecific=True)

        # try to reinit registration
        self.request_assert_error(400, 'container/register/initialize',
                                  data, self.at, 'POST',
                                  error_code=3000)

        delete_policy("policy")

    def test_07_register_terminate_server_success(self):
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        # Terminate
        self.request_assert_success(f'container/register/{mock_smph.container_serial}/terminate',
                                    {},
                                    self.at, 'POST')

    def test_08_register_terminate_fail(self):
        # Invalid container serial
        self.request_assert_error(404, "container/register/invalidSerial/terminate",
                                  {}, self.at, 'POST',
                                  error_code=601)

    def test_09_challenge_success(self):
        set_policy("challenge_ttl", scope="container", action={PolicyAction.CONTAINER_CHALLENGE_TTL: 3}, priority=1)

        # Registration
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph

        # Init
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success('container/challenge',
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             'POST')

        result_entries = result["result"]["value"].keys()
        self.assertIn("nonce", result_entries)
        self.assertIn("time_stamp", result_entries)
        self.assertIn("enc_key_algorithm", result_entries)

        # check challenge
        challenge_list = get_challenges(serial=mock_smph.container_serial)
        self.assertEqual(1, len(challenge_list))
        challenge = challenge_list[0]
        result = result["result"]["value"]
        self.assertEqual(result["nonce"], challenge.challenge)
        # we need to set the timezone since the database can not store it
        challenge_timestamp = challenge.timestamp.replace(tzinfo=timezone.utc)
        self.assertEqual(datetime.fromisoformat(result["time_stamp"]), challenge_timestamp)
        challenge_data = json.loads(challenge.data)
        self.assertEqual(scope, challenge_data["scope"])
        # expiration date: created a few microseconds after the creation date
        expiration_date = datetime.fromisoformat(result["time_stamp"]) + timedelta(seconds=180)
        time_delta = (expiration_date - challenge.expiration.replace(tzinfo=timezone.utc)).total_seconds()
        self.assertLessEqual(abs(time_delta), 1)

        delete_policy("challenge_ttl")

    def test_10_challenge_fail(self):
        # container does not exists
        scope = "https://pi.net/container/synchronize"
        self.request_assert_error(404, "container/challenge",
                                  {"scope": scope, "container_serial": "random"}, None, "POST",
                                  error_code=601,
                                  try_unspecific=True)

        # container is not registered
        smph_serial = init_container({"type": "smartphone"})["container_serial"]
        scope = "container/synchronize"
        self.request_assert_error(400, "container/challenge",
                                  {"scope": scope, "container_serial": smph_serial}, None, "POST",
                                  error_code=3001,
                                  try_unspecific=True)

        # Missing serial
        self.request_assert_error(400, "container/challenge",
                                  {"scope": scope}, None, "POST",
                                  error_code=905,
                                  try_unspecific=False)

    def register_terminate_client_success(self, smartphone_serial=None):
        # Registration
        registration = self.register_smartphone_success(smartphone_serial)
        mock_smph = registration.mock_smph

        # Challenge
        scope = "https://pi.net/container/register/terminate/client"
        result = self.request_assert_success('container/challenge',
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             'POST')

        params = mock_smph.register_terminate(result["result"]["value"], scope)

        # Terminate
        res = self.request_assert_success('container/register/terminate/client',
                                          params,
                                          None, 'POST')
        self.assertTrue(res["result"]["value"]["success"])

    def test_11_register_terminate_client_no_user_success(self):
        # Policy for a specific realm
        self.setUp_user_realms()
        set_policy("client_unregister", scope=SCOPE.CONTAINER, action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   realm=self.realm1)
        self.register_terminate_client_success()
        delete_policy("client_unregister")

        # No disable_client_container_unregister policy set
        self.register_terminate_client_success()

    def test_12_register_terminate_client_realm_and_user_success(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        self.setUp_user_realm3()
        user = User("hans", self.realm1)

        # No policy
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        self.register_terminate_client_success(smartphone.serial)

        # Policy for another realm
        set_policy("client_unregister", scope=SCOPE.CONTAINER, action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   realm=[self.realm3])
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        self.register_terminate_client_success(smartphone.serial)
        delete_policy("client_unregister")

        # Policy for another user in this realm
        set_policy("client_unregister", scope=SCOPE.CONTAINER, action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   realm=[self.realm2], user="hans")
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        self.register_terminate_client_success(smartphone.serial)
        delete_policy("client_unregister")

    def test_13_register_terminate_client_realm_success(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        smartphone = self.create_smartphone_for_user_and_realm(realm_list=[self.realm2])

        # No policy
        self.register_terminate_client_success(smartphone.serial)

        # Policy for another realm
        set_policy("client_unregister", scope=SCOPE.CONTAINER, action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   realm=self.realm1)
        self.register_terminate_client_success(smartphone.serial)
        delete_policy("client_unregister")

        # Policy for a specific user in this realm
        set_policy("client_unregister", scope=SCOPE.CONTAINER, action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   user="hans", realm=self.realm2)
        self.register_terminate_client_success(smartphone.serial)
        delete_policy("client_unregister")
        smartphone.delete()

    def register_terminate_client_denied(self, smartphone_serial=None):
        # Registration
        registration = self.register_smartphone_success(smartphone_serial)
        mock_smph = registration.mock_smph

        # Challenge
        scope = "https://pi.net/container/register/terminate/client"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")

        params = mock_smph.register_terminate(result["result"]["value"], scope)

        # Terminate
        self.request_assert_error(403, "container/register/terminate/client",
                                  params,
                                  None, 'POST',
                                  error_code=303,
                                  try_unspecific=False)

    def test_14_register_terminate_client_no_user_denied(self):
        # Generic policy
        set_policy("client_unregister", scope=SCOPE.CONTAINER, action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER)
        self.register_terminate_client_denied()
        delete_policy("client_unregister")

    def test_15_register_terminate_client_with_user_and_realms_denied(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        user = User("hans", self.realm1)

        # Generic policy
        set_policy("client_unregister", scope=SCOPE.CONTAINER, action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER)
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        self.register_terminate_client_denied(smartphone.serial)
        delete_policy("client_unregister")

        # Policy for the users realm
        set_policy("client_unregister", scope=SCOPE.CONTAINER, action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   realm=self.realm1)
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        self.register_terminate_client_denied(smartphone.serial)
        delete_policy("client_unregister")

        # Policy for the other realm
        set_policy("client_unregister", scope=SCOPE.CONTAINER, action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   realm=self.realm2)
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        self.register_terminate_client_denied(smartphone.serial)
        delete_policy("client_unregister")

        # Policy for the user
        set_policy("client_unregister", scope=SCOPE.CONTAINER, action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   realm=self.realm1, user="hans")
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        self.register_terminate_client_denied(smartphone.serial)
        delete_policy("client_unregister")

    def test_18_register_terminate_client_missing_param(self):
        # Registration
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        result = registration.response

        self.assertFalse(result["result"]["value"]["policies"][PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER])

        # Challenge
        scope = "https://pi.net/container/register/terminate/client"
        self.request_assert_success('container/challenge',
                                    {"scope": scope, "container_serial": mock_smph.container_serial}, None, 'POST')

        # Terminate without signature
        self.request_assert_error(400,
                                  "container/register/terminate/client",
                                  {"container_serial": mock_smph.container_serial}, None, 'POST',
                                  error_code=905,
                                  try_unspecific=True)

        # Terminate without container serial
        self.request_assert_error(400,
                                  "container/register/terminate/client",
                                  {"signature": "123"}, None, 'POST',
                                  error_code=905)

    def test_19_register_terminate_client_invalid_serial(self):
        # container does not exists
        self.request_assert_error(404,
                                  "container/register/terminate/client",
                                  {"container_serial": "random"},
                                  self.at, "POST",
                                  error_code=601,
                                  try_unspecific=True)

        # Missing serial
        self.request_assert_error(400,
                                  "container/register/terminate/client",
                                  {},
                                  self.at, "POST",
                                  error_code=905)

    def test_20_register_terminate_client_invalid_challenge(self):
        # Registration
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph

        # Challenge
        scope = "https://pi.net/container/register/terminate/client"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             'POST')
        # mock with another serial
        correct_serial = mock_smph.container_serial
        mock_smph.container_serial = "random123"
        params = mock_smph.register_terminate(result["result"]["value"], scope)
        params["container_serial"] = correct_serial

        # Terminate
        self.request_assert_error(400, "container/register/terminate/client",
                                  params, self.at, 'POST',
                                  error_code=3002,
                                  try_unspecific=True)

    def test_21_register_terminate_client_not_registered(self):
        # Registration
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph

        # Challenge
        scope = "https://pi.net/container/register/terminate/client"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")

        # server terminates
        self.request_assert_success(f"container/register/{mock_smph.container_serial}/terminate",
                                    {},
                                    self.at, 'POST')

        # client tries to terminate
        params = mock_smph.register_terminate(result["result"]["value"], scope)
        self.request_assert_error(400, "container/register/terminate/client",
                                  params, self.at, "POST",
                                  error_code=3001,
                                  try_unspecific=True)

    def test_22_register_generic_fail(self):
        set_policy("policy", scope=SCOPE.CONTAINER, action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.net/",
                                                            PolicyAction.CONTAINER_REGISTRATION_TTL: 24})
        generic_serial = init_container({"type": "generic"})["container_serial"]
        data = {"container_serial": generic_serial,
                "passphrase_prompt": "Enter your passphrase",
                "passphrase_response": "top_secret"}

        # Initialize
        self.request_assert_error(501, 'container/register/initialize',
                                  data,
                                  self.at, 'POST')

        # Finalize
        data = {"container_serial": generic_serial}
        self.request_assert_error(501, 'container/register/finalize',
                                  data,
                                  None, 'POST',
                                  try_unspecific=True)

        # Terminate
        self.request_assert_error(501, f'container/register/{generic_serial}/terminate',
                                  {}, self.at, 'POST')

        delete_policy('policy')

    def test_23_register_yubikey_fail(self):
        set_policy("policy", scope=SCOPE.CONTAINER, action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.net/",
                                                            PolicyAction.CONTAINER_REGISTRATION_TTL: 24})
        yubi_serial = init_container({"type": "yubikey"})["container_serial"]
        data = {"container_serial": yubi_serial,
                "passphrase_prompt": "Enter your passphrase",
                "passphrase_response": "top_secret"}

        # Initialize
        self.request_assert_error(501, 'container/register/initialize',
                                  data,
                                  self.at, 'POST')

        # Finalize
        data = {"container_serial": yubi_serial}
        self.request_assert_error(501, 'container/register/finalize',
                                  data,
                                  None, 'POST',
                                  try_unspecific=True)

        # Terminate
        self.request_assert_error(501, f'container/register/{yubi_serial}/terminate',
                                  {}, self.at, 'POST')

    def test_24_synchronize_success(self):
        # client rollover and deletable tokens are implicitly set to False
        set_policy("smartphone_config", scope=SCOPE.CONTAINER,
                   action={PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER: True,
                           PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER: True})
        # Registration
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        result = registration.response
        policies = result["result"]["value"]["policies"]
        self.assertTrue(policies[PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER])
        self.assertTrue(policies[PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER])
        self.assertFalse(policies[PolicyAction.DISABLE_CLIENT_TOKEN_DELETION])
        self.assertFalse(policies[PolicyAction.CONTAINER_CLIENT_ROLLOVER])

        # Challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")

        params = mock_smph.synchronize(result["result"]["value"], scope)

        # Sync
        sync_time = datetime.now(timezone.utc)
        result = self.request_assert_success("container/synchronize",
                                             params, None, "POST")
        result_entries = result["result"]["value"].keys()
        self.assertEqual("AES", result["result"]["value"]["encryption_algorithm"])
        self.assertIn("encryption_params", result_entries)
        self.assertIn("public_server_key", result_entries)
        self.assertIn("container_dict_server", result_entries)
        self.assertIn("server_url", result_entries)
        self.assertIn("policies", result_entries)
        policies = result["result"]["value"]["policies"]
        self.assertTrue(policies[PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER])
        self.assertFalse(policies[PolicyAction.CONTAINER_CLIENT_ROLLOVER])
        self.assertTrue(policies[PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER])
        self.assertFalse(policies[PolicyAction.DISABLE_CLIENT_TOKEN_DELETION])

        # check last synchronization timestamp
        smartphone = find_container_by_serial(mock_smph.container_serial)
        last_sync = smartphone.last_synchronization
        time_diff = abs((sync_time - last_sync).total_seconds())
        self.assertLessEqual(time_diff, 1)

        delete_policy("smartphone_config")

    def test_25_synchronize_invalid_params(self):
        smartphone_serial = init_container({"type": "smartphone"})["container_serial"]

        # missing signature
        params = {"public_enc_key_client": "123", "container_serial": smartphone_serial}
        self.request_assert_error(400, "container/synchronize",
                                  params, None, "POST",
                                  error_code=905,
                                  try_unspecific=True)

        # missing serial
        params = {"public_enc_key_client": "123", "signature": "0001"}
        self.request_assert_error(400, "container/synchronize",
                                  params, None, "POST",
                                  error_code=905,
                                  try_unspecific=False)

    def test_26_synchronize_invalid_container(self):
        # container does not exists
        params = {"public_enc_key_client": "123", "signature": "abcd", "container_serial": "random"}
        self.request_assert_error(404, "container/synchronize",
                                  params, None, "POST",
                                  error_code=601,
                                  try_unspecific=True)

    def test_27_synchronize_container_not_registered(self):
        # Registration
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph

        # Challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")

        params = mock_smph.synchronize(result["result"]["value"], scope)

        # Server unregister
        self.request_assert_success(f"container/register/{mock_smph.container_serial}/terminate", {},
                                    self.at, "POST")

        # Sync
        self.request_assert_error(400, "container/synchronize",
                                  params, None, "POST",
                                  error_code=3001,
                                  try_unspecific=True)

    def test_28_synchronize_invalid_challenge(self):
        # invalid challenge
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        # create challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")

        # mock client with invalid scope (wrong serial)
        params = mock_smph.synchronize(result["result"]["value"], "https://pi.net/container/register/initialize")
        self.request_assert_error(400, "container/synchronize",
                                  params, None, 'POST',
                                  error_code=3002,
                                  try_unspecific=True)

    def test_29_synchronize_man_in_the_middle(self):
        # client register successfully
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        # client creates challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             'POST')
        # mock client
        params = mock_smph.synchronize(result["result"]["value"], scope)
        # man in the middle fetches client request and inserts its own public encryption key
        enc_evil = generate_keypair_ecc("x25519")
        params["public_enc_key_client"] = base64.urlsafe_b64encode(enc_evil.public_key.public_bytes_raw()).decode(
            'utf-8')

        # man in the middle sends modified request to the server
        # Fails due to invalid signature (client signed the public encryption key which is now different)
        self.request_assert_error(400, "container/synchronize",
                                  params, None, 'POST',
                                  error_code=3002,
                                  try_unspecific=True)

    def test_30_synchronize_smartphone_with_push_fb(self):
        # Registration
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        smartphone = find_container_by_serial(mock_smph.container_serial)

        # tokens
        push_fb = init_token({"genkey": "1", "type": "push"})
        smartphone.add_token(push_fb)

        # Firebase config
        fb_config = {FirebaseConfig.REGISTRATION_URL: "http://test/ttype/push",
                     FirebaseConfig.JSON_CONFIG: self.FIREBASE_FILE,
                     FirebaseConfig.TTL: 10}
        set_smsgateway("fb1", 'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider', "myFB",
                       fb_config)
        set_policy("push", scope=SCOPE.ENROLL, action={PushAction.FIREBASE_CONFIG: "fb1",
                                                       PushAction.REGISTRATION_URL: "http://test/ttype/push"})

        # Challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial},
                                             None, "POST")

        params = mock_smph.synchronize(result["result"]["value"], scope)

        # Finalize
        result = self.request_assert_success("container/synchronize",
                                             params, None, 'POST')
        result_entries = result["result"]["value"].keys()
        self.assertEqual("AES", result["result"]["value"]["encryption_algorithm"])
        self.assertIn("encryption_params", result_entries)
        self.assertIn("public_server_key", result_entries)
        self.assertIn("container_dict_server", result_entries)
        self.assertIn("server_url", result_entries)

        # check token info
        container_dict_server_enc = result["result"]["value"]["container_dict_server"]
        pub_key_server = X25519PublicKey.from_public_bytes(
            base64.urlsafe_b64decode(result["result"]["value"]["public_server_key"]))
        shared_key = mock_smph.private_key_encr.exchange(pub_key_server)
        container_dict_server = json.loads(decrypt_aes(container_dict_server_enc, shared_key,
                                                       result["result"]["value"]["encryption_params"]).decode("utf-8"))
        tokens_dict = container_dict_server["tokens"]
        self.assertIn("add", tokens_dict)
        self.assertIn("update", tokens_dict)
        tokens = tokens_dict["add"]
        self.assertEqual(1, len(tokens))
        self.assertIn("otpauth://pipush/", tokens[0])

        delete_policy("push")

    def test_31_synchronize_smartphone_with_push_poll_only(self):
        # Registration
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        smartphone = find_container_by_serial(mock_smph.container_serial)

        # tokens
        push_fb = init_token({"genkey": "1", "type": "push"})
        smartphone.add_token(push_fb)

        # policies: push config is spread over multiple policies
        set_policy("push_1", scope=SCOPE.ENROLL, action={PushAction.FIREBASE_CONFIG: "poll only"})
        set_policy("push_2", scope=SCOPE.ENROLL, action={PushAction.REGISTRATION_URL: "http://test/ttype/push"})

        # Challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")

        params = mock_smph.synchronize(result["result"]["value"], scope)

        # Finalize
        result = self.request_assert_success("container/synchronize",
                                             params, None, 'POST')
        result_entries = result["result"]["value"].keys()
        self.assertEqual("AES", result["result"]["value"]["encryption_algorithm"])
        self.assertIn("encryption_params", result_entries)
        self.assertIn("public_server_key", result_entries)
        self.assertIn("container_dict_server", result_entries)
        self.assertIn("server_url", result_entries)

        # check token info
        container_dict_server_enc = result["result"]["value"]["container_dict_server"]
        pub_key_server = X25519PublicKey.from_public_bytes(
            base64.urlsafe_b64decode(result["result"]["value"]["public_server_key"]))
        shared_key = mock_smph.private_key_encr.exchange(pub_key_server)
        container_dict_server = json.loads(decrypt_aes(container_dict_server_enc, shared_key,
                                                       result["result"]["value"]["encryption_params"]).decode("utf-8"))
        tokens_dict = container_dict_server["tokens"]
        self.assertIn("add", tokens_dict)
        self.assertIn("update", tokens_dict)
        tokens = tokens_dict["add"]
        self.assertEqual(1, len(tokens))
        self.assertIn("otpauth://pipush/", tokens[0])

        delete_policy("push_1")
        delete_policy("push_2")

    def test_32_synchronize_smartphone_with_new_tokens(self):
        # Registration
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        smartphone = find_container_by_serial(mock_smph.container_serial)

        # tokens
        hotp = init_token({"genkey": "1", "type": "hotp", "otplen": 8, "hashlib": "sha256"})
        smartphone.add_token(hotp)
        totp = init_token({"genkey": "1", "type": "totp", "otplen": 8, "hashlib": "sha256", "timeStep": 60})
        smartphone.add_token(totp)
        sms = init_token({"type": "sms", "phone": "0123456789"})
        smartphone.add_token(sms)
        daypassword = init_token({"genkey": "1", "type": "daypassword", "hashlib": "sha256", "timeStep": 60})
        smartphone.add_token(daypassword)

        # Challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")

        params = mock_smph.synchronize(result["result"]["value"], scope)

        # Finalize
        result = self.request_assert_success("container/synchronize",
                                             params, None, 'POST')

        # check result
        container_dict_server_enc = result["result"]["value"]["container_dict_server"]
        pub_key_server = X25519PublicKey.from_public_bytes(
            base64.urlsafe_b64decode(result["result"]["value"]["public_server_key"]))
        shared_key = mock_smph.private_key_encr.exchange(pub_key_server)
        container_dict_server = json.loads(decrypt_aes(container_dict_server_enc, shared_key,
                                                       result["result"]["value"]["encryption_params"]).decode("utf-8"))
        tokens_dict = container_dict_server["tokens"]
        self.assertIn("add", tokens_dict)
        self.assertIn("update", tokens_dict)
        tokens = tokens_dict["add"]
        # sms is skipped for synchronization
        self.assertEqual(3, len(tokens))

        # check token properties
        # new tokens are rolled over: enrollment settings need to be the same and not reset to defaults
        hotp_dict = hotp.get_as_dict()
        self.assertEqual(8, hotp_dict["otplen"])
        self.assertEqual("sha256", hotp_dict["info"]["hashlib"])
        totp_dict = totp.get_as_dict()
        self.assertEqual(8, totp_dict["otplen"])
        self.assertEqual("sha256", totp_dict["info"]["hashlib"])
        self.assertEqual("60", totp_dict["info"]["timeStep"])
        sms_dict = sms.get_as_dict()
        self.assertEqual("0123456789", sms_dict["info"]["phone"])
        daypw_dict = daypassword.get_as_dict()
        self.assertEqual("sha256", daypw_dict["info"]["hashlib"])
        self.assertEqual("60", daypw_dict["info"]["timeStep"])

    def test_33_synchronize_smartphone_missing_token_enroll_policies(self):
        # Registration
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        smartphone = find_container_by_serial(mock_smph.container_serial)

        # tokens
        push_fb = init_token({"genkey": "1", "type": "push"})
        smartphone.add_token(push_fb)
        hotp = init_token({"genkey": "1", "type": "hotp"})
        smartphone.add_token(hotp)

        # Challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")

        params = mock_smph.synchronize(result["result"]["value"], scope)

        # Finalize with missing push config
        result = self.request_assert_success("container/synchronize",
                                             params, None, 'POST')
        result_entries = result["result"]["value"].keys()
        self.assertEqual("AES", result["result"]["value"]["encryption_algorithm"])
        self.assertIn("encryption_params", result_entries)
        self.assertIn("public_server_key", result_entries)
        self.assertIn("container_dict_server", result_entries)
        self.assertIn("server_url", result_entries)

        # check token info
        container_dict_server_enc = result["result"]["value"]["container_dict_server"]
        pub_key_server = X25519PublicKey.from_public_bytes(
            base64.urlsafe_b64decode(result["result"]["value"]["public_server_key"]))
        shared_key = mock_smph.private_key_encr.exchange(pub_key_server)
        container_dict_server = json.loads(decrypt_aes(container_dict_server_enc, shared_key,
                                                       result["result"]["value"]["encryption_params"]).decode("utf-8"))
        tokens_dict = container_dict_server["tokens"]
        self.assertIn("add", tokens_dict)
        self.assertIn("update", tokens_dict)
        tokens = tokens_dict["add"]
        # Only hotp token to be added
        self.assertEqual(1, len(tokens))
        self.assertIn("otpauth://hotp/", tokens[0])

    def test_34_synchronize_smartphone_token_policies(self):
        # Registration
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        smartphone = find_container_by_serial(mock_smph.container_serial)

        # Add tokens
        totp = init_token({"genkey": True, "type": "totp"})
        smartphone.add_token(totp)
        daypassword = init_token({"genkey": True, "type": "daypassword"})
        smartphone.add_token(daypassword)
        sms = init_token({"type": "sms", "phone": "0123456789"})
        smartphone.add_token(sms)

        # set label, issuer and require pin policies
        self.setUp_user_realms()
        self.setUp_user_realm2()
        set_policy('token_enroll_realm2', scope=SCOPE.ENROLL,
                   action={PolicyAction.TOKENLABEL: '{user}',
                           PolicyAction.TOKENISSUER: '{realm}',
                           'hotp_' + PolicyAction.FORCE_APP_PIN: True}, realm=self.realm2)
        set_policy('token_enroll_realm1', scope=SCOPE.ENROLL,
                   action={PolicyAction.TOKENLABEL: '{user}',
                           PolicyAction.TOKENISSUER: '{realm}',
                           'hotp_' + PolicyAction.FORCE_APP_PIN: True}, realm=self.realm1)

        # Get initial enroll url
        hotp_params = {"type": "hotp",
                       "genkey": True,
                       "realm": self.realm1,
                       "user": "hans"}
        result = self.request_assert_success("/token/init", hotp_params, self.at, "POST")
        initial_enroll_url = result["detail"]["googleurl"]["value"]
        self.assertIn("pin=True", initial_enroll_url)
        self.assertIn("app_force_unlock=pin", initial_enroll_url)
        self.assertIn(f"issuer={self.realm1}", initial_enroll_url)
        self.assertIn("hans", initial_enroll_url)
        hotp = get_one_token(serial=result["detail"]["serial"])
        smartphone.add_token(hotp)

        # Challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")

        params = mock_smph.synchronize(result["result"]["value"], scope)

        # Finalize
        result = self.request_assert_success("container/synchronize",
                                             params, None, 'POST')
        result_entries = result["result"]["value"].keys()
        self.assertEqual("AES", result["result"]["value"]["encryption_algorithm"])
        self.assertIn("encryption_params", result_entries)
        self.assertIn("public_server_key", result_entries)
        self.assertIn("container_dict_server", result_entries)
        self.assertIn("server_url", result_entries)

        # check token info
        container_dict_server_enc = result["result"]["value"]["container_dict_server"]
        pub_key_server = X25519PublicKey.from_public_bytes(
            base64.urlsafe_b64decode(result["result"]["value"]["public_server_key"]))
        shared_key = mock_smph.private_key_encr.exchange(pub_key_server)
        container_dict_server = json.loads(decrypt_aes(container_dict_server_enc, shared_key,
                                                       result["result"]["value"]["encryption_params"]).decode("utf-8"))
        tokens_dict = container_dict_server["tokens"]
        self.assertIn("add", tokens_dict)
        self.assertIn("update", tokens_dict)
        tokens = tokens_dict["add"]
        # totp, daypassword and hotp token to be added (sms token can not be enrolled in the app)
        self.assertEqual(3, len(tokens))
        # check hotp enroll url
        for token in tokens:
            if "hotp" in token:
                hotp_enroll_url = token
                break
        self.assertNotEqual(initial_enroll_url, hotp_enroll_url)
        self.assertIn("pin=True", hotp_enroll_url)
        self.assertIn("app_force_unlock=pin", hotp_enroll_url)
        self.assertIn(f"issuer={self.realm1}", hotp_enroll_url)
        self.assertIn("hans", hotp_enroll_url)

        delete_policy('token_enroll_realm1')
        delete_policy('token_enroll_realm2')

    def test_35_generic_sync_fail(self):
        generic_serial = init_container({"type": "generic"})["container_serial"]

        # Challenge
        scope = "https://pi.net/container/synchronize"
        self.request_assert_error(400, "container/challenge",
                                  {"scope": scope, "container_serial": generic_serial}, None, 'POST',
                                  error_code=3001,
                                  try_unspecific=True)

    def test_36_yubi_sync_fail(self):
        generic_serial = init_container({"type": "generic"})["container_serial"]

        # Challenge
        scope = "https://pi.net/container/synchronize"
        self.request_assert_error(400, "container/challenge",
                                  {"scope": scope, "container_serial": generic_serial}, None, "POST",
                                  error_code=3001,
                                  try_unspecific=True)

    def setup_rollover(self, smartphone_serial=None):
        # Registration
        registration = self.register_smartphone_success(smartphone_serial)
        mock_smph = registration.mock_smph
        smartphone = find_container_by_serial(mock_smph.container_serial)
        # tokens
        hotp = init_token({"genkey": "1", "type": "hotp"})
        smartphone.add_token(hotp)

        # Challenge for init rollover
        scope = "https://pi.net/container/rollover"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")
        challenge_data = result["result"]["value"]

        # Mock old smartphone
        rollover_scope = "https://pi.net/container/rollover"
        params = mock_smph.register_finalize(challenge_data["nonce"], challenge_data["time_stamp"],
                                             rollover_scope, mock_smph.container_serial)
        params.update({"passphrase_prompt": "Enter your phone number.", "passphrase_response": "123456789"})

        return params

    def client_rollover_success(self, smartphone_serial=None):
        set_policy("register_policy", scope=SCOPE.CONTAINER,
                   action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.net/",
                           PolicyAction.CONTAINER_REGISTRATION_TTL: 24},
                   priority=3)
        # Register, create challenge for rollover and mock smartphone for rollover
        smartphone_params = self.setup_rollover(smartphone_serial)
        smartphone_serial = smartphone_params['container_serial']

        # Init rollover
        result = self.request_assert_success("container/rollover",
                                             smartphone_params, None, 'POST')

        init_response_data = result["result"]["value"]
        self.assertIn("container_url", init_response_data)
        self.assertIn("nonce", init_response_data)
        self.assertIn("time_stamp", init_response_data)
        self.assertIn("key_algorithm", init_response_data)
        self.assertIn("hash_algorithm", init_response_data)
        self.assertIn("ssl_verify", init_response_data)
        self.assertIn("ttl", init_response_data)
        self.assertIn("passphrase_prompt", init_response_data)
        # Check if the url contains all relevant data
        qr_url = init_response_data["container_url"]["value"]
        self.assertIn(f"pia://container/{smartphone_serial}", qr_url)
        self.assertIn("issuer=privacyIDEA", qr_url)
        self.assertIn("ttl=24", qr_url)
        self.assertIn("nonce=", qr_url)
        self.assertIn("time=", qr_url)
        self.assertIn("url=https%3A//pi.net/", qr_url)
        self.assertIn(f"serial={smartphone_serial}", qr_url)
        self.assertIn("key_algorithm=", qr_url)
        self.assertIn("hash_algorithm", qr_url)
        self.assertIn("passphrase=Enter%20your%20phone%20number.", qr_url)
        # New smartphone finalizes rollover
        mock_smph = MockSmartphone(device_brand="XY", device_model="ABC123")
        params = mock_smph.register_finalize(init_response_data["nonce"], init_response_data["time_stamp"],
                                             "https://pi.net/container/register/finalize", smartphone_serial,
                                             smartphone_params["passphrase_response"])

        # Finalize rollover (finalize registration)
        self.request_assert_success('container/register/finalize',
                                    params, None, 'POST')

        delete_policy("register_policy")

    def client_rollover_denied(self, smartphone_serial=None):
        set_policy("register_policy", scope=SCOPE.CONTAINER,
                   action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.net/",
                           PolicyAction.CONTAINER_REGISTRATION_TTL: 24}, priority=1)
        # Register, create challenge for rollover and mock smartphone for rollover
        smartphone_params = self.setup_rollover(smartphone_serial)
        smartphone_serial = smartphone_params['container_serial']

        # Init rollover
        self.request_assert_error(403, "container/rollover", smartphone_params,
                                  None, "POST",
                                  error_code=303,
                                  try_unspecific=False)

        delete_policy("register_policy")

    def test_37_rollover_client_no_user_success(self):
        # Rollover with generic policy
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER)
        self.client_rollover_success()
        delete_policy("policy_rollover")

    def test_38_rollover_client_no_user_denied(self):
        # No rollover right
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER)
        self.client_rollover_denied()
        delete_policy("policy_rollover")

        # Rollover with policy for a specific realm
        self.setUp_user_realms()
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER,
                   realm=self.realm1)
        self.client_rollover_denied()
        delete_policy("policy_rollover")

    def test_39_rollover_client_realm_success(self):
        self.setUp_user_realms()

        # Rollover with generic policy
        smartphone_serial = init_container({"type": "smartphone", "realm": self.realm1})["container_serial"]
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER)
        self.client_rollover_success(smartphone_serial)
        delete_policy("policy_rollover")

        # Rollover with policy for realm
        smartphone_serial = init_container({"type": "smartphone", "realm": self.realm1})["container_serial"]
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER,
                   realm=self.realm1)
        self.client_rollover_success(smartphone_serial)
        delete_policy("policy_rollover")

    def test_40_rollover_client_realm_denied(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()

        # Rollover with policy for a user
        smartphone_serial = init_container({"type": "smartphone", "realm": self.realm1})["container_serial"]
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER,
                   user="hans", realm=self.realm1)
        self.client_rollover_denied(smartphone_serial)
        delete_policy("policy_rollover")

        # Rollover with policy for another realm
        smartphone_serial = init_container({"type": "smartphone", "realm": self.realm1})["container_serial"]
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER,
                   realm=self.realm2)
        self.client_rollover_denied(smartphone_serial)
        delete_policy("policy_rollover")

        # Rollover action not allowed
        smartphone_serial = init_container({"type": "smartphone", "realm": self.realm1})["container_serial"]
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER,
                   realm=self.realm1)
        self.client_rollover_denied(smartphone_serial)
        delete_policy("policy_rollover")

    def test_41_rollover_client_user_success(self):
        self.setUp_user_realms()

        # Rollover with generic policy
        smartphone_serial = init_container({"type": "smartphone",
                                            "user": "hans",
                                            "realm": self.realm1})["container_serial"]
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER)
        self.client_rollover_success(smartphone_serial)
        delete_policy("policy_rollover")

        # Rollover with policy for user realm
        smartphone_serial = init_container({"type": "smartphone",
                                            "user": "hans",
                                            "realm": self.realm1})["container_serial"]
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER,
                   realm=self.realm1)
        self.client_rollover_success(smartphone_serial)
        delete_policy("policy_rollover")

        # Rollover with policy for the user
        smartphone_serial = init_container({"type": "smartphone",
                                            "user": "hans",
                                            "realm": self.realm1})["container_serial"]
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER,
                   realm=self.realm1, user="hans")
        self.client_rollover_success(smartphone_serial)
        delete_policy("policy_rollover")

    def test_42_rollover_client_user_denied(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()

        # Rollover with no rollover rights
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER)
        smartphone_serial = init_container({"type": "smartphone",
                                            "user": "hans",
                                            "realm": self.realm1})["container_serial"]
        self.client_rollover_denied(smartphone_serial)
        delete_policy("policy_rollover")

        # Rollover with policy only for another realm
        smartphone_serial = init_container({"type": "smartphone",
                                            "user": "hans",
                                            "realm": self.realm1})["container_serial"]
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER,
                   realm=self.realm2)
        self.client_rollover_denied(smartphone_serial)
        delete_policy("policy_rollover")

        # Rollover with policy only for another user of the same realm
        smartphone_serial = init_container({"type": "smartphone",
                                            "user": "hans",
                                            "realm": self.realm1})["container_serial"]
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER,
                   realm=self.realm2, user="root")
        self.client_rollover_denied(smartphone_serial)
        delete_policy("policy_rollover")

    def test_43_rollover_client_user_and_realm_success(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        user = User("hans", self.realm1)

        # Rollover with policy for the user realm
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER,
                   realm=self.realm1)
        self.client_rollover_success(smartphone.serial)
        delete_policy("policy_rollover")

        # Rollover with policy for the other realm
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER,
                   realm=self.realm2)
        self.client_rollover_success(smartphone.serial)
        delete_policy("policy_rollover")

        # Rollover with policy for the user
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER,
                   realm=self.realm1, user="hans")
        self.client_rollover_success(smartphone.serial)
        delete_policy("policy_rollover")

    def test_44_rollover_client_user_and_realm_denied(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        self.setUp_user_realm3()
        user = User("hans", self.realm1)

        # Rollover with policy only for another realm
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER,
                   realm=self.realm3)
        self.client_rollover_denied(smartphone.serial)
        delete_policy("policy_rollover")

        # Rollover with policy only for another user
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER,
                   realm=self.realm2, user="hans")
        self.client_rollover_denied(smartphone.serial)
        delete_policy("policy_rollover")

    def test_45_rollover_client_container_not_registered(self):
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER)
        smartphone_serial = init_container({"type": "smartphone"})["container_serial"]
        smartphone = find_container_by_serial(smartphone_serial)
        # tokens
        hotp = init_token({"genkey": "1", "type": "hotp"})
        smartphone.add_token(hotp)

        set_policy("policy", scope=SCOPE.CONTAINER, action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.net/",
                                                            PolicyAction.CONTAINER_REGISTRATION_TTL: 36})

        # Challenge for init rollover
        scope = "https://pi.net/container/rollover"
        self.request_assert_error(400, "container/challenge",
                                  {"scope": scope, "container_serial": smartphone_serial}, None, "POST",
                                  error_code=3001,
                                  try_unspecific=True)

        # Init rollover
        self.request_assert_error(400, "container/rollover",
                                  {"container_serial": smartphone_serial},
                                  None, 'POST',
                                  error_code=3001,
                                  try_unspecific=True)

        delete_policy("policy")
        delete_policy("policy_rollover")

    def test_46_rollover_client_init_invalid_challenge(self):
        # Registration
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER)
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        result = registration.response
        policies = result["result"]["value"]["policies"]
        self.assertFalse(policies[PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER])
        self.assertFalse(policies[PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER])
        self.assertFalse(policies[PolicyAction.DISABLE_CLIENT_TOKEN_DELETION])
        self.assertTrue(policies[PolicyAction.CONTAINER_CLIENT_ROLLOVER])

        smartphone = find_container_by_serial(mock_smph.container_serial)
        # tokens
        hotp = init_token({"genkey": "1", "type": "hotp"})
        smartphone.add_token(hotp)

        set_policy("policy", scope=SCOPE.CONTAINER, action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.net/",
                                                            PolicyAction.CONTAINER_REGISTRATION_TTL: 36})

        # Challenge for init rollover
        scope = "https://pi.net/container/rollover"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")
        challenge_data = result["result"]["value"]

        # Mock smartphone with invalid nonce
        rollover_scope = "https://pi.net/container/rollover"
        params = mock_smph.register_finalize("123456789", challenge_data["time_stamp"],
                                             rollover_scope)

        # Init rollover
        self.request_assert_error(400, "container/rollover",
                                  params,
                                  None, 'POST',
                                  error_code=3002,
                                  try_unspecific=True)

        delete_policy("policy")
        delete_policy("policy_rollover")

    def test_47_rollover_client_finalize_invalid_challenge(self):
        # Registration
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER)
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        result = registration.response
        policies = result["result"]["value"]["policies"]
        self.assertFalse(policies[PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER])
        self.assertFalse(policies[PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER])
        self.assertFalse(policies[PolicyAction.DISABLE_CLIENT_TOKEN_DELETION])
        self.assertTrue(policies[PolicyAction.CONTAINER_CLIENT_ROLLOVER])

        smartphone = find_container_by_serial(mock_smph.container_serial)
        # tokens
        hotp = init_token({"genkey": "1", "type": "hotp"})
        smartphone.add_token(hotp)

        set_policy("policy", scope=SCOPE.CONTAINER, action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.net/",
                                                            PolicyAction.CONTAINER_REGISTRATION_TTL: 36})

        # Challenge for init rollover
        scope = "https://pi.net/container/rollover"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")
        challenge_data = result["result"]["value"]

        # Mock smartphone
        rollover_scope = "https://pi.net/container/rollover"
        params = mock_smph.register_finalize(challenge_data["nonce"], challenge_data["time_stamp"],
                                             rollover_scope)
        passphrase = "top_secret"
        params.update({"passphrase_prompt": "Enter your passphrase", "passphrase_response": passphrase})

        # Init rollover
        result = self.request_assert_success("container/rollover",
                                             params,
                                             None, 'POST')
        rollover_data = result["result"]["value"]

        # Invalid Nonce
        # Mock smartphone
        params = mock_smph.register_finalize("123456789", rollover_data["time_stamp"],
                                             "https://pi.net/container/register/finalize", passphrase=passphrase)

        # Finalize rollover (finalize registration)
        self.request_assert_error(400, 'container/register/finalize',
                                  params,
                                  None, 'POST',
                                  error_code=3002,
                                  try_unspecific=True)

        # Invalid time stamp
        # Mock smartphone
        params = mock_smph.register_finalize(rollover_data["nonce"], "2021-01-01T00:00:00+00:00",
                                             "https://pi.net/container/register/finalize", passphrase=passphrase)

        # Finalize rollover (finalize registration)
        self.request_assert_error(400, 'container/register/finalize',
                                  params,
                                  None, 'POST',
                                  error_code=3002,
                                  try_unspecific=True)

        # Invalid passphrase
        # Mock smartphone
        params = mock_smph.register_finalize(rollover_data["nonce"], rollover_data["time_stamp"],
                                             "https://pi.net/container/register/finalize", passphrase="test1234")

        # Finalize rollover (finalize registration)
        self.request_assert_error(400, 'container/register/finalize',
                                  params,
                                  None, 'POST',
                                  error_code=3002,
                                  try_unspecific=True)

        delete_policy("policy")
        delete_policy("policy_rollover")

    def test_48_rollover_client_missing_serial(self):
        set_policy("policy", scope=SCOPE.CONTAINER, action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.net/",
                                                            PolicyAction.CONTAINER_REGISTRATION_TTL: 36,
                                                            PolicyAction.CONTAINER_CLIENT_ROLLOVER: True})

        self.request_assert_error(400, "container/rollover", {}, None, 'POST',
                                  error_code=905,
                                  try_unspecific=False)

        delete_policy("policy")

    def test_49_client_self_rollover(self):
        # Registration
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        smartphone = find_container_by_serial(mock_smph.container_serial)

        # token
        self.setUp_user_realms()
        hotp_params = {"type": "hotp",
                       "genkey": True,
                       "realm": self.realm1,
                       "user": "hans"}
        result = self.request_assert_success("/token/init", hotp_params, self.at, "POST")
        initial_enroll_url = result["detail"]["googleurl"]["value"]
        hotp = get_one_token(serial=result["detail"]["serial"])
        smartphone.add_token(hotp)

        set_policy("policy", scope=SCOPE.CONTAINER, action={PolicyAction.CONTAINER_SERVER_URL: "https://new-pi.net/",
                                                            PolicyAction.CONTAINER_REGISTRATION_TTL: 36})

        # Challenge for init rollover
        scope = "https://pi.net/container/rollover"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")

        # Rollover init
        data = {"container_serial": mock_smph.container_serial, "rollover": True,
                "passphrase_prompt": "Enter your phone number.", "passphrase_response": "123456789"}
        result = self.request_assert_success("container/register/initialize", data, self.at, 'POST')

        init_response_data = result["result"]["value"]
        self.assertIn("container_url", init_response_data)
        self.assertIn("nonce", init_response_data)
        self.assertIn("time_stamp", init_response_data)
        self.assertIn("key_algorithm", init_response_data)
        self.assertIn("hash_algorithm", init_response_data)
        self.assertIn("ssl_verify", init_response_data)
        self.assertIn("ttl", init_response_data)
        self.assertIn("passphrase_prompt", init_response_data)
        # Check if the url contains all relevant data
        qr_url = init_response_data["container_url"]["value"]
        self.assertIn(f"pia://container/{mock_smph.container_serial}", qr_url)
        self.assertIn("issuer=privacyIDEA", qr_url)
        self.assertIn("ttl=36", qr_url)
        self.assertIn("nonce=", qr_url)
        self.assertIn("time=", qr_url)
        self.assertIn("url=https%3A//new-pi.net/", qr_url)
        self.assertIn(f"serial={mock_smph.container_serial}", qr_url)
        self.assertIn("key_algorithm=", qr_url)
        self.assertIn("hash_algorithm", qr_url)
        self.assertIn("passphrase=Enter%20your%20phone%20number.", qr_url)

        # smartphone finalizes rollover
        params = mock_smph.register_finalize(scope="https://new-pi.net/container/register/finalize",
                                             nonce=init_response_data["nonce"],
                                             registration_time=init_response_data["time_stamp"],
                                             passphrase="123456789")
        self.request_assert_success('container/register/finalize',
                                    params,
                                    None, 'POST')
        self.assertEqual(RegistrationState.ROLLOVER_COMPLETED, smartphone.registration_state)

        # Challenge for Sync
        scope = "https://new-pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")
        mock_smph.container = {"serial": mock_smph.container_serial, "type": "smartphone",
                               "tokens": [{"serial": hotp.get_serial(), "type": "HOTP", "label": hotp.get_serial(),
                                           "issuer": "privacIDEA", "pin": False, "algorithm": "SHA1", "digits": 6}]}
        params = mock_smph.synchronize(result["result"]["value"], scope)

        # Sync
        result = self.request_assert_success("container/synchronize",
                                             params, None, 'POST')
        container_dict_server_enc = result["result"]["value"]["container_dict_server"]
        pub_key_server = X25519PublicKey.from_public_bytes(
            base64.urlsafe_b64decode(result["result"]["value"]["public_server_key"]))
        shared_key = mock_smph.private_key_encr.exchange(pub_key_server)
        container_dict_server = json.loads(decrypt_aes(container_dict_server_enc, shared_key,
                                                       result["result"]["value"]["encryption_params"]).decode("utf-8"))
        token_diff = container_dict_server["tokens"]
        self.assertEqual(1, len(token_diff["add"]))
        self.assertNotEqual(initial_enroll_url, token_diff["add"][0])
        self.assertEqual(0, len(token_diff["update"]))

        # smartphone got new token secrets: rollover completed
        self.assertEqual(RegistrationState.REGISTERED, smartphone.registration_state)

        delete_policy("policy")

    def test_50_sync_with_rollover_challenge_fails(self):
        # Registration
        set_policy("policy_rollover", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER)
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        result = registration.response
        policies = result["result"]["value"]["policies"]
        self.assertFalse(policies[PolicyAction.DISABLE_CLIENT_CONTAINER_UNREGISTER])
        self.assertFalse(policies[PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER])
        self.assertFalse(policies[PolicyAction.DISABLE_CLIENT_TOKEN_DELETION])
        self.assertTrue(policies[PolicyAction.CONTAINER_CLIENT_ROLLOVER])

        smartphone = find_container_by_serial(mock_smph.container_serial)
        # tokens
        hotp = init_token({"genkey": "1", "type": "hotp"})
        smartphone.add_token(hotp)

        set_policy("policy", scope=SCOPE.CONTAINER, action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.net/",
                                                            PolicyAction.CONTAINER_REGISTRATION_TTL: 36})

        # Challenge for init rollover
        scope = "https://pi.net/container/rollover"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")

        # create signature for rollover endpoint
        params = mock_smph.synchronize(result["result"]["value"], scope)

        # Call sync endpoint with rollover signature
        self.request_assert_error(400, "container/synchronize",
                                  params, None, 'POST',
                                  error_code=3002,
                                  try_unspecific=True)

        delete_policy("policy")
        delete_policy("policy_rollover")

    def test_51_rollover_server_success(self):
        # Registration
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        smartphone = find_container_by_serial(mock_smph.container_serial)

        # tokens
        self.setUp_user_realms()

        push = init_token({"genkey": "1", "type": "push", PushAction.FIREBASE_CONFIG: "poll only"})
        self.assertEqual("poll only", push.get_tokeninfo()[PushAction.FIREBASE_CONFIG])
        smartphone.add_token(push)

        hotp_params = {"type": "hotp",
                       "genkey": True,
                       "realm": self.realm1,
                       "user": "hans",
                       "hashlib": "sha256"}
        result = self.request_assert_success("/token/init", hotp_params, self.at, "POST")
        initial_enroll_url = result["detail"]["googleurl"]["value"]
        hotp = get_one_token(serial=result["detail"]["serial"])
        self.assertEqual("sha256", hotp.hashlib)
        smartphone.add_token(hotp)

        totp = init_token({"genkey": True, "type": "totp", "otplen": 8, "hashlib": "sha256", "timeStep": 60})
        self.assertEqual("sha256", totp.hashlib)
        self.assertEqual(60, totp.timestep)
        smartphone.add_token(totp)
        daypassword = init_token({"genkey": True, "type": "daypassword", "hashlib": "sha256", "timeStep": 30})
        self.assertEqual("sha256", daypassword.hashlib)
        self.assertEqual(30, daypassword.timestep)
        smartphone.add_token(daypassword)

        # Offline token
        offline_hotp = init_token({"genkey": "1", "type": "hotp"})
        offline_hotp_otps = offline_hotp.get_multi_otp(100)[2]["otp"]
        smartphone.add_token(offline_hotp)
        self.create_offline_token(offline_hotp.get_serial(), offline_hotp_otps)

        set_policy("policy", scope=SCOPE.CONTAINER, action={PolicyAction.CONTAINER_SERVER_URL: "https://new-pi.net/",
                                                            PolicyAction.CONTAINER_REGISTRATION_TTL: 36})
        # Firebase config
        fb_config = {FirebaseConfig.REGISTRATION_URL: "http://test/ttype/push",
                     FirebaseConfig.JSON_CONFIG: self.FIREBASE_FILE,
                     FirebaseConfig.TTL: 10}
        set_smsgateway("firebase", 'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider', "myFB",
                       fb_config)
        set_policy("push", scope=SCOPE.ENROLL, action={PushAction.FIREBASE_CONFIG: "firebase",
                                                       PushAction.REGISTRATION_URL: "http://test/ttype/push"})

        # Rollover init
        data = {"container_serial": mock_smph.container_serial, "rollover": True,
                "passphrase_prompt": "Enter your phone number.", "passphrase_response": "123456789"}
        result = self.request_assert_success("container/register/initialize", data, self.at, "POST")

        init_response_data = result["result"]["value"]
        self.assertIn("container_url", init_response_data)
        self.assertIn("nonce", init_response_data)
        self.assertIn("time_stamp", init_response_data)
        self.assertIn("key_algorithm", init_response_data)
        self.assertIn("hash_algorithm", init_response_data)
        self.assertIn("ssl_verify", init_response_data)
        self.assertIn("ttl", init_response_data)
        self.assertIn("passphrase_prompt", init_response_data)
        # Check if the url contains all relevant data
        qr_url = init_response_data["container_url"]["value"]
        self.assertIn(f"pia://container/{mock_smph.container_serial}", qr_url)
        self.assertIn("issuer=privacyIDEA", qr_url)
        self.assertIn("ttl=36", qr_url)
        self.assertIn("nonce=", qr_url)
        self.assertIn("time=", qr_url)
        self.assertIn("url=https%3A//new-pi.net/", qr_url)
        self.assertIn(f"serial={mock_smph.container_serial}", qr_url)
        self.assertIn("key_algorithm=", qr_url)
        self.assertIn("hash_algorithm", qr_url)
        self.assertIn("passphrase=Enter%20your%20phone%20number.", qr_url)

        # New smartphone finalizes rollover
        new_mock_smph = MockSmartphone(device_brand="XY", device_model="ABC123")
        params = new_mock_smph.register_finalize(scope="https://new-pi.net/container/register/finalize",
                                                 nonce=init_response_data["nonce"],
                                                 registration_time=init_response_data["time_stamp"],
                                                 passphrase="123456789", serial=mock_smph.container_serial)

        self.request_assert_success('container/register/finalize',
                                    params,
                                    None, 'POST')
        self.assertEqual(RegistrationState.ROLLOVER_COMPLETED, smartphone.registration_state)

        # Try to sync with old smartphone
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")
        params = mock_smph.synchronize(result["result"]["value"], scope)
        self.request_assert_error(400, "container/synchronize",
                                  params, None, 'POST',
                                  error_code=3002,
                                  try_unspecific=True)
        self.assertEqual(RegistrationState.ROLLOVER_COMPLETED, smartphone.registration_state)

        # Sync with new smartphone
        scope = "https://new-pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": new_mock_smph.container_serial}, None,
                                             "POST")

        new_mock_smph.container = {"serial": new_mock_smph.container_serial, "type": "smartphone",
                                   "tokens": [{"serial": hotp.get_serial(), "type": "HOTP", "label": hotp.get_serial(),
                                               "issuer": "privacIDEA", "pin": False, "algorithm": "SHA1", "digits": 6}]}
        params = new_mock_smph.synchronize(result["result"]["value"], scope)
        result = self.request_assert_success("container/synchronize",
                                             params, None, 'POST')
        container_dict_server_enc = result["result"]["value"]["container_dict_server"]
        pub_key_server = X25519PublicKey.from_public_bytes(
            base64.urlsafe_b64decode(result["result"]["value"]["public_server_key"]))
        shared_key = new_mock_smph.private_key_encr.exchange(pub_key_server)
        container_dict_server = json.loads(decrypt_aes(container_dict_server_enc, shared_key,
                                                       result["result"]["value"]["encryption_params"]).decode("utf-8"))
        token_diff = container_dict_server["tokens"]
        # only online hotp token is included, for the push token the config is missing and offline tokens can not be
        # synchronized
        self.assertEqual(4, len(token_diff["add"]))
        new_hotp_enroll_url = [enroll_url for enroll_url in token_diff["add"] if hotp.get_serial() in enroll_url][0]
        self.assertNotEqual(initial_enroll_url, new_hotp_enroll_url)
        self.assertIn(offline_hotp.get_serial(), token_diff["offline"])
        self.assertEqual(103, offline_hotp.token.count)

        # check tokens
        self.assertEqual("sha256", hotp.hashlib)
        self.assertEqual("sha256", totp.hashlib)
        self.assertEqual(60, totp.timestep)
        self.assertEqual("sha256", daypassword.hashlib)
        self.assertEqual(30, daypassword.timestep)
        # due to new policy push token config changed to firebase
        self.assertEqual("firebase", push.get_tokeninfo()[PushAction.FIREBASE_CONFIG])

        # smartphone got new token secrets: rollover completed
        self.assertEqual(RegistrationState.REGISTERED, smartphone.registration_state)

        delete_policy("policy")

    def test_52_rollover_server_not_completed(self):
        # Registration
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        smartphone = find_container_by_serial(mock_smph.container_serial)

        # token
        hotp = init_token({"genkey": "1", "type": "hotp"})
        hotp_secret = hotp.token.get_otpkey().getKey().decode("utf-8")
        smartphone.add_token(hotp)

        set_policy("policy", scope=SCOPE.CONTAINER, action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.net/",
                                                            PolicyAction.CONTAINER_REGISTRATION_TTL: 36})

        # Rollover init
        data = {"container_serial": mock_smph.container_serial, "rollover": True,
                "passphrase_prompt": "Enter your phone number.", "passphrase_response": "123456789"}
        self.request_assert_success("container/register/initialize", data, self.at, "POST")

        # register/finalize missing

        # Sync with old smartphone still working
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")
        mock_smph.container = {"serial": mock_smph.container_serial, "type": "smartphone",
                               "tokens": [{"serial": hotp.get_serial(), "type": "HOTP"}]}
        params = mock_smph.synchronize(result["result"]["value"], scope)

        self.request_assert_success("container/synchronize", params, None, 'POST')
        # check that token is not rolled over
        new_hotp_secret = hotp.token.get_otpkey().getKey().decode("utf-8")
        self.assertEqual(hotp_secret, new_hotp_secret)

        delete_policy("policy")

    def sync_with_initial_token_transfer_allowed(self, smartphone_serial=None):
        registration = self.register_smartphone_success(smartphone_serial)
        mock_smph = registration.mock_smph
        smartphone_serial = mock_smph.container_serial

        # Create Tokens
        hotp_token = init_token({"genkey": True, "type": "hotp"})
        _, _, otp_dict = hotp_token.get_multi_otp(2)
        hotp_otps = list(otp_dict["otp"].values())
        spass_token = init_token({"type": "spass"})
        totp = init_token({"genkey": True, "type": "totp"})
        daypassword = init_token({"genkey": True, "type": "daypassword"})

        # Challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": smartphone_serial}, None, 'POST')

        mock_smph.container = {"serial": smartphone_serial, "type": "smartphone",
                               "tokens": [{"serial": totp.get_serial()}, {"serial": daypassword.get_serial()},
                                          {"otp": hotp_otps, "type": "hotp"}, {"serial": spass_token.get_serial()},
                                          {"serial": "123456"}]}
        params = mock_smph.synchronize(result["result"]["value"], scope)

        # Initial Sync
        sync_time = datetime.now(timezone.utc)
        with mock.patch("privacyidea.lib.containerclass.datetime") as mock_dt:
            mock_dt.now.return_value = sync_time
            result = self.request_assert_success("container/synchronize",
                                                 params, None, 'POST')
        result_entries = result["result"]["value"].keys()
        self.assertEqual("AES", result["result"]["value"]["encryption_algorithm"])
        self.assertIn("encryption_params", result_entries)
        self.assertIn("public_server_key", result_entries)
        self.assertIn("container_dict_server", result_entries)
        self.assertIn("server_url", result_entries)
        self.assertIn("policies", result_entries)
        self.assertTrue(result["result"]["value"]["policies"][PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER])

        # check last synchronization timestamp
        smartphone = find_container_by_serial(smartphone_serial)
        last_sync = smartphone.last_synchronization
        self.assertEqual(last_sync, sync_time)

        # check tokens of container
        smartphone_tokens = smartphone.get_tokens()
        self.assertEqual(3, len(smartphone_tokens))
        token_serials = [token.get_serial() for token in smartphone_tokens]
        self.assertIn(totp.get_serial(), token_serials)
        self.assertIn(daypassword.get_serial(), token_serials)
        self.assertIn(hotp_token.get_serial(), token_serials)

        # Second Sync
        new_hotp = init_token({"genkey": True, "type": "hotp"})

        # Challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": smartphone_serial}, None,
                                             "POST")

        mock_smph.container = {"serial": smartphone_serial, "type": "smartphone",
                               "tokens": [{"serial": totp.get_serial()}, {"serial": daypassword.get_serial()},
                                          {"otp": hotp_otps, "type": "hotp"}, {"serial": spass_token.get_serial()},
                                          {"serial": "123456"}, {"serial": new_hotp.get_serial()}]}
        params = mock_smph.synchronize(result["result"]["value"], scope)

        # Sync
        self.request_assert_success("container/synchronize",
                                    params, None, 'POST')

        # check tokens of container: new hotp shall not be in the container
        smartphone_tokens = smartphone.get_tokens()
        self.assertEqual(3, len(smartphone_tokens))
        token_serials = [token.get_serial() for token in smartphone_tokens]
        self.assertIn(totp.get_serial(), token_serials)
        self.assertIn(daypassword.get_serial(), token_serials)
        self.assertIn(hotp_token.get_serial(), token_serials)
        self.assertNotIn(new_hotp.get_serial(), token_serials)

    def sync_with_initial_token_transfer_denied(self, smartphone_serial=None):
        registration = self.register_smartphone_success(smartphone_serial)
        mock_smph = registration.mock_smph
        smartphone_serial = mock_smph.container_serial

        # Create Tokens
        hotp_token = init_token({"genkey": True, "type": "hotp"})
        _, _, otp_dict = hotp_token.get_multi_otp(2)
        hotp_otps = list(otp_dict["otp"].values())
        spass_token = init_token({"type": "spass"})
        totp = init_token({"genkey": True, "type": "totp"})
        daypassword = init_token({"genkey": True, "type": "daypassword"})

        # Challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": smartphone_serial}, None, "POST")

        mock_smph.container = {"serial": smartphone_serial, "type": "smartphone",
                               "tokens": [{"serial": totp.get_serial()}, {"serial": daypassword.get_serial()},
                                          {"otp": hotp_otps, "type": "hotp"}, {"serial": spass_token.get_serial()},
                                          {"serial": "123456"}]}
        params = mock_smph.synchronize(result["result"]["value"], scope)

        # Initial Sync
        sync_time = datetime.now(timezone.utc)
        result = self.request_assert_success("container/synchronize",
                                             params, None, "POST")
        result_entries = result["result"]["value"].keys()
        self.assertEqual("AES", result["result"]["value"]["encryption_algorithm"])
        self.assertIn("encryption_params", result_entries)
        self.assertIn("public_server_key", result_entries)
        self.assertIn("container_dict_server", result_entries)
        self.assertIn("server_url", result_entries)
        self.assertIn("policies", result_entries)
        self.assertFalse(result["result"]["value"]["policies"][PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER])

        # check last synchronization timestamp
        smartphone = find_container_by_serial(smartphone_serial)
        last_sync = smartphone.last_synchronization
        time_diff = abs((sync_time - last_sync).total_seconds())
        # TODO: Should probably patch datetime.now in TokenContainerClass.update_last_authentication()
        self.assertLessEqual(time_diff, 5)

        # check tokens of container
        smartphone_tokens = smartphone.get_tokens()
        self.assertEqual(0, len(smartphone_tokens))

    def test_53_synchronize_initial_token_transfer_no_user_success(self):
        # Generic policy
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER)
        self.sync_with_initial_token_transfer_allowed()
        delete_policy("transfer_policy")

    def test_54_synchronize_initial_token_transfer_no_user_denied(self):
        # No policy
        self.sync_with_initial_token_transfer_denied()

        # Policy for a specific realm
        self.setUp_user_realms()
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER,
                   realm=self.realm1)
        self.sync_with_initial_token_transfer_denied()
        delete_policy("transfer_policy")

    def test_55_synchronize_initial_token_transfer_user_success(self):
        self.setUp_user_realms()

        # Generic policy
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER)
        smartphone_serial = init_container({"type": "smartphone",
                                            "user": "hans",
                                            "realm": self.realm1})["container_serial"]
        self.sync_with_initial_token_transfer_allowed(smartphone_serial)
        delete_policy("transfer_policy")

        # Policy for the users realm
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER,
                   realm=self.realm1)
        smartphone_serial = init_container({"type": "smartphone",
                                            "user": "hans",
                                            "realm": self.realm1})["container_serial"]
        self.sync_with_initial_token_transfer_allowed(smartphone_serial)
        delete_policy("transfer_policy")

        # Policy for the user
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER,
                   realm=self.realm1, user="hans")
        smartphone_serial = init_container({"type": "smartphone",
                                            "user": "hans",
                                            "realm": self.realm1})["container_serial"]
        self.sync_with_initial_token_transfer_allowed(smartphone_serial)
        delete_policy("transfer_policy")

        # Policy for the resolver
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER,
                   resolver=self.resolvername1)
        smartphone_serial = init_container({"type": "smartphone",
                                            "user": "hans",
                                            "realm": self.realm1})["container_serial"]
        self.sync_with_initial_token_transfer_allowed(smartphone_serial)
        delete_policy("transfer_policy")

    def test_56_synchronize_initial_token_transfer_user_denied(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()

        # No policy
        smartphone_serial = init_container({"type": "smartphone",
                                            "user": "hans",
                                            "realm": self.realm1})["container_serial"]
        self.sync_with_initial_token_transfer_denied(smartphone_serial)

        # Policy for another realm
        smartphone_serial = init_container({"type": "smartphone",
                                            "user": "hans",
                                            "realm": self.realm1})["container_serial"]
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER,
                   realm=self.realm2)
        self.sync_with_initial_token_transfer_denied(smartphone_serial)
        delete_policy("transfer_policy")

        # Policy for another user
        smartphone_serial = init_container({"type": "smartphone",
                                            "user": "hans",
                                            "realm": self.realm1})["container_serial"]
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER,
                   realm=self.realm1, user="root")
        self.sync_with_initial_token_transfer_denied(smartphone_serial)
        delete_policy("transfer_policy")

    def test_57_synchronize_initial_token_transfer_user_realm_success(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        user = User("hans", self.realm1)

        # Policy for the users realm
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER,
                   realm=self.realm1)
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        self.sync_with_initial_token_transfer_allowed(smartphone.serial)
        delete_policy("transfer_policy")

        # Policy for the other realm
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER,
                   realm=self.realm2)
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        self.sync_with_initial_token_transfer_allowed(smartphone.serial)
        delete_policy("transfer_policy")

        # Policy for the user
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER,
                   realm=self.realm1, user="hans")
        smartphone = self.create_smartphone_for_user_and_realm(user, [self.realm2])
        self.sync_with_initial_token_transfer_allowed(smartphone.serial)
        delete_policy("transfer_policy")

    def test_58_synchronize_initial_token_transfer_user_realm_denied(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        self.setUp_user_realm3()
        user = User("hans", self.realm1)

        # Policy for another realm
        smartphone = self.create_smartphone_for_user_and_realm(user, self.realm2)
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER,
                   realm=self.realm3)
        self.sync_with_initial_token_transfer_denied(smartphone.serial)
        delete_policy("transfer_policy")

        # Policy for another user
        smartphone = self.create_smartphone_for_user_and_realm(user, self.realm2)
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER,
                   realm=self.realm2, user="root")
        self.sync_with_initial_token_transfer_denied(smartphone.serial)
        delete_policy("transfer_policy")

    def test_59_synchronize_smartphone_with_offline_tokens(self):
        # Registration
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER)
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        smartphone = find_container_by_serial(mock_smph.container_serial)

        # tokens
        server_token = init_token({"genkey": "1", "type": "hotp", "otplen": 8, "hashlib": "sha256"})
        server_token_otps = server_token.get_multi_otp(100)[2]["otp"]
        client_token_no_serial = init_token({"genkey": "1", "type": "hotp"})
        client_token_no_serial_otps = client_token_no_serial.get_multi_otp(100)[2]["otp"]
        client_token_with_serial = init_token({"genkey": "1", "type": "hotp"})
        client_token_with_serial_otps = client_token_with_serial.get_multi_otp(100)[2]["otp"]
        shared_token = init_token({"genkey": "1", "type": "hotp"})
        shared_token_otps = shared_token.get_multi_otp(100)[2]["otp"]
        shared_token_no_serial = init_token({"genkey": "1", "type": "hotp"})
        shared_token_no_serial_otps = shared_token_no_serial.get_multi_otp(100)[2]["otp"]
        online_token = init_token({"genkey": "1", "type": "hotp"})

        smartphone.add_token(server_token)
        smartphone.add_token(shared_token)
        smartphone.add_token(shared_token_no_serial)
        smartphone.add_token(online_token)

        # Create offline token
        self.create_offline_token(server_token.get_serial(), server_token_otps)
        self.create_offline_token(client_token_no_serial.get_serial(), client_token_no_serial_otps)
        self.create_offline_token(client_token_with_serial.get_serial(), client_token_with_serial_otps)
        self.create_offline_token(shared_token.get_serial(), shared_token_otps)
        self.create_offline_token(shared_token_no_serial.get_serial(), shared_token_no_serial_otps)

        # Challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")

        mock_smph.container = {
            "tokens": [{"tokentype": "HOTP", "otp": list(client_token_no_serial_otps.values())[2:4], "counter": "2"},
                       {"tokentype": "HOTP", "serial": client_token_with_serial.get_serial()},
                       {"tokentype": "HOTP", "serial": shared_token.get_serial()},
                       {"tokentype": "HOTP", "otp": list(shared_token_no_serial_otps.values())[2:4], "counter": "2"},
                       {"tokentype": "HOTP", "serial": online_token.get_serial()}]}
        params = mock_smph.synchronize(result["result"]["value"], scope)

        # Finalize
        result = self.request_assert_success("container/synchronize",
                                             params, None, 'POST')
        result_entries = result["result"]["value"].keys()
        self.assertEqual("AES", result["result"]["value"]["encryption_algorithm"])
        self.assertIn("encryption_params", result_entries)
        self.assertIn("public_server_key", result_entries)
        self.assertIn("container_dict_server", result_entries)
        self.assertIn("server_url", result_entries)

        # check token info
        container_dict_server_enc = result["result"]["value"]["container_dict_server"]
        pub_key_server = X25519PublicKey.from_public_bytes(
            base64.urlsafe_b64decode(result["result"]["value"]["public_server_key"]))
        shared_key = mock_smph.private_key_encr.exchange(pub_key_server)
        container_dict_server = json.loads(decrypt_aes(container_dict_server_enc, shared_key,
                                                       result["result"]["value"]["encryption_params"]).decode("utf-8"))
        tokens_dict = container_dict_server["tokens"]
        self.assertIn("add", tokens_dict)
        self.assertIn("update", tokens_dict)
        # the token only on the server can not be added to the client since the server does not know the offline counter
        add_tokens = tokens_dict["add"]
        self.assertEqual(0, len(add_tokens))
        self.assertEqual(103, server_token.token.count)

        update_tokens = {token["serial"]: token for token in tokens_dict["update"]}
        update_tokens_serials = update_tokens.keys()
        # the token from the client with serial is added to the container with unchanged counter
        self.assertIn(client_token_with_serial.get_serial(), update_tokens_serials)
        self.assertEqual(103, client_token_with_serial.token.count)
        self.assertTrue(update_tokens[client_token_with_serial.get_serial()]["offline"])
        # the shared token stays unchanged (counter = 103)
        self.assertIn(shared_token.get_serial(), update_tokens_serials)
        self.assertEqual(103, shared_token.token.count)
        self.assertTrue(update_tokens[shared_token.get_serial()]["offline"])
        # The token from the client without serial is added to the server and the counter is unchanged
        self.assertIn(client_token_no_serial.get_serial(), update_tokens_serials)
        self.assertEqual(103, client_token_no_serial.token.count)
        self.assertTrue(update_tokens[client_token_no_serial.get_serial()]["offline"])
        # Shared token: otp values could be mapped to serial
        self.assertIn(shared_token_no_serial.get_serial(), update_tokens_serials)
        self.assertEqual(103, shared_token_no_serial.token.count)
        self.assertTrue(update_tokens[shared_token_no_serial.get_serial()]["offline"])
        # Online token
        self.assertIn(online_token.get_serial(), update_tokens_serials)
        self.assertFalse(update_tokens[online_token.get_serial()]["offline"])
        self.assertEqual(5, len(update_tokens_serials))

        delete_policy("transfer_policy")

    def test_60_rollover_and_synchronize_with_offline_tokens(self):
        # Registration
        set_policy("transfer_policy", scope=SCOPE.CONTAINER, action=PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER)
        registration = self.register_smartphone_success()
        mock_smph = registration.mock_smph
        smartphone = find_container_by_serial(mock_smph.container_serial)
        smartphone.update_container_info([TokenContainerInfoData(key=RegistrationState.get_key(),
                                                                 value=RegistrationState.ROLLOVER_COMPLETED.value,
                                                                 info_type=PI_INTERNAL)])

        # tokens
        server_token = init_token({"genkey": "1", "type": "hotp", "otplen": 8, "hashlib": "sha256"})
        server_token_otps = server_token.get_multi_otp(100)[2]["otp"]
        client_token_no_serial = init_token({"genkey": "1", "type": "hotp"})
        client_token_no_serial_otps = client_token_no_serial.get_multi_otp(100)[2]["otp"]
        client_token_with_serial = init_token({"genkey": "1", "type": "hotp"})
        client_token_with_serial_otps = client_token_with_serial.get_multi_otp(100)[2]["otp"]
        shared_token = init_token({"genkey": "1", "type": "hotp"})
        shared_token_otps = shared_token.get_multi_otp(100)[2]["otp"]
        shared_token_no_serial = init_token({"genkey": "1", "type": "hotp"})
        shared_token_no_serial_otps = shared_token_no_serial.get_multi_otp(100)[2]["otp"]
        online_token = init_token({"genkey": "1", "type": "hotp"})

        smartphone.add_token(server_token)
        smartphone.add_token(shared_token)
        smartphone.add_token(shared_token_no_serial)
        smartphone.add_token(online_token)

        # Create offline token
        self.create_offline_token(server_token.get_serial(), server_token_otps)
        self.create_offline_token(client_token_no_serial.get_serial(), client_token_no_serial_otps)
        self.create_offline_token(client_token_with_serial.get_serial(), client_token_with_serial_otps)
        self.create_offline_token(shared_token.get_serial(), shared_token_otps)
        self.create_offline_token(shared_token_no_serial.get_serial(), shared_token_no_serial_otps)

        # Challenge
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")

        mock_smph.container = {
            "tokens": [{"tokentype": "HOTP", "otp": list(client_token_no_serial_otps.values())[2:4], "counter": "2"},
                       {"tokentype": "HOTP", "serial": client_token_with_serial.get_serial()},
                       {"tokentype": "HOTP", "serial": shared_token.get_serial()},
                       {"tokentype": "HOTP", "otp": list(shared_token_no_serial_otps.values())[2:4], "counter": "2"},
                       {"tokentype": "HOTP", "serial": online_token.get_serial()}]}
        params = mock_smph.synchronize(result["result"]["value"], scope)

        # Finalize
        result = self.request_assert_success("container/synchronize",
                                             params, None, 'POST')
        result_entries = result["result"]["value"].keys()
        self.assertEqual("AES", result["result"]["value"]["encryption_algorithm"])
        self.assertIn("encryption_params", result_entries)
        self.assertIn("public_server_key", result_entries)
        self.assertIn("container_dict_server", result_entries)
        self.assertIn("server_url", result_entries)

        # check token info
        container_dict_server_enc = result["result"]["value"]["container_dict_server"]
        pub_key_server = X25519PublicKey.from_public_bytes(
            base64.urlsafe_b64decode(result["result"]["value"]["public_server_key"]))
        shared_key = mock_smph.private_key_encr.exchange(pub_key_server)
        container_dict_server = json.loads(decrypt_aes(container_dict_server_enc, shared_key,
                                                       result["result"]["value"]["encryption_params"]).decode("utf-8"))
        tokens_dict = container_dict_server["tokens"]
        self.assertIn("add", tokens_dict)
        self.assertIn("update", tokens_dict)
        # Only the online token is rolled over and hence in the add list with the new token secret
        add_tokens = tokens_dict["add"]
        self.assertEqual(1, len(add_tokens))
        self.assertIn(online_token.get_serial(), add_tokens[0])

        # the token only on the server can not be added to the client since the server does not know the offline counter
        offline_tokens = tokens_dict["offline"]
        self.assertIn(server_token.get_serial(), offline_tokens)
        self.assertEqual(103, server_token.token.count)

        update_tokens = {token["serial"]: token for token in tokens_dict["update"]}
        update_tokens_serials = update_tokens.keys()
        # the token from the client with serial is added to the container with unchanged counter
        self.assertIn(client_token_with_serial.get_serial(), update_tokens_serials)
        self.assertEqual(103, client_token_with_serial.token.count)
        self.assertTrue(update_tokens[client_token_with_serial.get_serial()]["offline"])
        # the shared token stays unchanged (counter = 103)
        self.assertIn(shared_token.get_serial(), update_tokens_serials)
        self.assertEqual(103, shared_token.token.count)
        self.assertTrue(update_tokens[shared_token.get_serial()]["offline"])
        # The token from the client without serial is added to the server and the counter is unchanged
        self.assertIn(client_token_no_serial.get_serial(), update_tokens_serials)
        self.assertEqual(103, client_token_no_serial.token.count)
        self.assertTrue(update_tokens[client_token_no_serial.get_serial()]["offline"])
        # Shared token: otp values could be mapped to serial
        self.assertIn(shared_token_no_serial.get_serial(), update_tokens_serials)
        self.assertEqual(103, shared_token_no_serial.token.count)
        self.assertTrue(update_tokens[shared_token_no_serial.get_serial()]["offline"])
        self.assertEqual(4, len(update_tokens_serials))

        delete_policy("transfer_policy")
