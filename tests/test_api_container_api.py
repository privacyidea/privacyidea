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


class APIContainer(APIContainerTest):

    def test_00_init_delete_container_success(self):
        # Init container
        payload = {"type": "Smartphone", "description": "test description!!"}
        res = self.request_assert_success('/container/init', payload, self.at, 'POST')
        cserial = res["result"]["value"]["container_serial"]
        self.assertTrue(len(cserial) > 1)

        # Check creation date is set
        container = find_container_by_serial(cserial)
        self.assertIn("creation_date", list(container.get_container_info_dict().keys()))

        # Delete the container
        result = self.request_assert_success(f"container/{cserial}", {}, self.at, 'DELETE')
        self.assertTrue(result["result"]["value"])

    def test_01_init_container_fail(self):
        # Init with non-existing type
        payload = {"type": "wrongType", "description": "test description!!"}
        self.request_assert_error(400, '/container/init', payload, self.at, 'POST',
                                  error_code=404,
                                  error_message="ERR404: Type 'wrongType' is not a valid type!")

        # Init without type
        self.request_assert_error(400, '/container/init', {}, self.at, 'POST',
                                  error_code=404,
                                  error_message="ERR404: Type parameter is required!")

        # Init without auth token
        payload = {"type": "Smartphone", "description": "test description!!"}
        self.request_assert_error(401, '/container/init',
                                  payload, None, 'POST',
                                  error_code=4033,
                                  error_message="Authentication failure. Missing Authorization header.")

    def test_02_delete_container_fail(self):
        # Delete non-existing container
        self.request_assert_error(404, '/container/wrong_serial',
                                  {}, self.at, 'DELETE',
                                  error_code=601,
                                  error_message="Unable to find container with serial wrong_serial.")

        # Call without serial
        self.request_assert_405('/container/', {}, self.at, 'DELETE')

    def test_03_assign_user_fail(self):
        # Arrange
        container_serial = init_container({"type": "generic"})["container_serial"]

        # Assign without realm
        payload = {"user": "hans"}
        self.request_assert_error(400, f'/container/{container_serial}/assign',
                                  payload, self.at, 'POST',
                                  error_code=904,
                                  error_message="ERR904: The user can not be found in any resolver in this realm!")

        # Assign user with non-existing realm
        payload = {"user": "hans", "realm": "non_existing"}
        self.request_assert_error(400, f'/container/{container_serial}/assign',
                                  payload, self.at, 'POST',
                                  error_code=904,
                                  error_message="ERR904: The user can not be found in any resolver in this realm!")

        # Assign without user
        self.setUp_user_realm2()
        payload = {"realm": self.realm2}
        self.request_assert_error(400, f'/container/{container_serial}/assign',
                                  payload, self.at, 'POST',
                                  error_code=905,
                                  error_message="ERR905: Missing parameter: user")

        delete_container_by_serial(container_serial)

    def test_04_assign_multiple_users_fails(self):
        # Arrange
        container_serial = init_container({"type": "generic"})["container_serial"]
        self.setUp_user_realms()
        payload = {"user": "hans", "realm": self.realm1}

        # Assign with user and realm
        result = self.request_assert_success(f'/container/{container_serial}/assign', payload, self.at, 'POST')
        self.assertTrue(result["result"]["value"])

        # Assign another user fails
        payload = {"user": "cornelius", "realm": self.realm1}
        self.request_assert_error(400, f'/container/{container_serial}/assign',
                                  payload, self.at, 'POST',
                                  error_code=301,
                                  error_message="ERR301: This container is already assigned to another user.")

        delete_container_by_serial(container_serial)

    def test_05_assign_unassign_user_success(self):
        # Arrange
        container_serial = init_container({"type": "generic"})["container_serial"]
        self.setUp_user_realms()
        payload = {"user": "hans", "realm": self.realm1}

        # Assign with user and realm
        result = self.request_assert_success(f'/container/{container_serial}/assign', payload, self.at, 'POST')
        self.assertTrue(result["result"]["value"])

        # Unassign
        result = self.request_assert_success(f'/container/{container_serial}/unassign',
                                             payload, self.at, 'POST')
        self.assertTrue(result["result"]["value"])

        delete_container_by_serial(container_serial)

    def test_06_assign_without_realm(self):
        # If no realm is passed the default realm is set in before_request
        # Arrange
        container_serial = init_container({"type": "generic"})["container_serial"]
        self.setUp_user_realm2()
        self.setUp_user_realm3()
        payload = {"user": "hans"}

        # Assign
        result = self.request_assert_success(f'/container/{container_serial}/assign',
                                             payload, self.at, 'POST')
        self.assertTrue(result["result"]["value"])
        # Used default realm is correct
        container = find_container_by_serial(container_serial)
        owner = container.get_users()[0]
        self.assertTrue(owner.login == "hans")
        self.assertTrue(owner.realm == self.realm2)

        # Assign without realm where default realm is not correct
        container_serial = init_container({"type": "generic"})["container_serial"]
        payload = {"user": "root"}
        self.request_assert_error(400, f'/container/{container_serial}/assign',
                                  payload, self.at, 'POST',
                                  error_code=904,
                                  error_message="ERR904: The user can not be found in any resolver in this realm!")

        container.delete()

    def test_07a_unassign_success(self):
        # Arrange
        self.setUp_user_realms()
        self.setUp_user_realm3()
        set_default_realm(self.realm1)
        user = User("hans", self.realm1)
        container_serial = init_container({"type": "generic", "user": user.login, "realm": user.realm})[
            "container_serial"]
        container = find_container_by_serial(container_serial)

        # Unassign only with username works if user is in default realm
        payload = {"user": "hans"}
        result = self.request_assert_success(f'/container/{container_serial}/unassign', payload, self.at, 'POST')
        self.assertTrue(result["result"].get("value"))
        self.assertEqual(0, len(container.get_users()))

        # username + realm
        container.add_user(user)
        payload = {"user": user.login, "realm": user.realm}
        result = self.request_assert_success(f'/container/{container_serial}/unassign', payload, self.at, 'POST')
        self.assertTrue(result["result"].get("value"))
        self.assertEqual(0, len(container.get_users()))

        # username + resolver
        container.add_user(user)
        payload = {"user": user.login, "resolver": user.resolver}
        result = self.request_assert_success(f'/container/{container_serial}/unassign', payload, self.at, 'POST')
        self.assertTrue(result["result"].get("value"))
        self.assertEqual(0, len(container.get_users()))

        # uid
        container.add_user(user)
        payload = {"user_id": user.uid}
        result = self.request_assert_success(f'/container/{container_serial}/unassign', payload, self.at, 'POST')
        self.assertTrue(result["result"].get("value"))
        self.assertEqual(0, len(container.get_users()))

        # uid + realm + resolver
        container.add_user(user)
        payload = {"user_id": user.uid, "realm": user.realm, "resolver": user.resolver}
        result = self.request_assert_success(f'/container/{container_serial}/unassign', payload, self.at, 'POST')
        self.assertTrue(result["result"].get("value"))
        self.assertEqual(0, len(container.get_users()))

        container.delete()

    def test_07b_unassign_fail(self):
        # Arrange
        self.setUp_user_realms()
        self.setUp_user_realm3()
        set_default_realm(self.realm1)
        user = User("corny", self.realm3)
        container_serial = init_container({"type": "generic", "user": user.login, "realm": user.realm})[
            "container_serial"]

        # Missing input parameters
        # No parameters
        self.request_assert_error(400, f'/container/{container_serial}/unassign', {}, self.at, 'POST',
                                  error_code=905,
                                  error_message="ERR905: Missing one of the following parameters: ['user', 'user_id']")

        # Only username, realm / resolver / uid missing (if user is not in defrealm)
        payload = {"user": user.login}
        self.request_assert_error(400, f'/container/{container_serial}/unassign',
                                  payload, self.at, 'POST',
                                  error_code=904,
                                  error_message="ERR904: The user can not be found in any resolver in this realm!")
        # If no default realm exists, another error is raised
        set_default_realm()
        self.request_assert_error(400, f'/container/{container_serial}/unassign',
                                  payload, self.at, 'POST',
                                  error_code=905,
                                  error_message="ERR905: Missing parameter 'realm', 'resolver', and/or 'user_id'")

        # Only realm: user / user_id missing
        payload = {"realm": self.realm3}
        self.request_assert_error(400, f'/container/{container_serial}/unassign',
                                  payload, self.at, 'POST',
                                  error_code=905,
                                  error_message="ERR905: Missing one of the following parameters: ['user', 'user_id']")

        # Unassign user with non-existing realm
        payload = {"user": user.login, "realm": "non_existing"}
        self.request_assert_error(400, f'/container/{container_serial}/unassign',
                                  payload, self.at, 'POST',
                                  error_code=904,
                                  error_message="ERR904: The user can not be found in any resolver in this realm!")

        # Unassign not assigned user
        payload = {"user": "hans", "realm": self.realm1}
        result = self.request_assert_success(f'/container/{container_serial}/unassign',
                                             payload, self.at, 'POST')
        self.assertFalse(result["result"]["value"])

        delete_container_by_serial(container_serial)

    def test_07c_unassign_non_existing_user(self):
        # Arrange
        self.setUp_user_realms()
        self.setUp_user_realm3()
        set_default_realm(self.realm1)
        invalid_user = User("invalid", self.realm1, self.resolvername1, "123")
        container_serial = init_container({"type": "generic"})["container_serial"]
        container = find_container_by_serial(container_serial)
        container.add_user(invalid_user)
        self.assertEqual(1, len(container.get_users()))

        # --- Fail ---
        # Only with username and realm
        payload = {"user": "invalid", "realm": self.realm1}
        self.request_assert_error(400, f'/container/{container_serial}/unassign',
                                  payload, self.at, 'POST',
                                  error_code=904,
                                  error_message="ERR904: The user can not be found in any resolver in this realm!")

        # Remove non-existing not assigned user
        payload = {"user": "another_invalid", "realm": self.realm1, "user_id": "987"}
        self.request_assert_error(400, f'/container/{container_serial}/unassign',
                                  payload, self.at, 'POST',
                                  error_code=904,
                                  error_message="ERR904: The user can not be found in any resolver in this realm!")

        # --- Success ---
        # Only with user_id should work as long as the container can only have one user
        payload = {"user_id": invalid_user.uid}
        result = self.request_assert_success(f'/container/{container_serial}/unassign',
                                             payload, self.at, 'POST')
        self.assertTrue(result["result"].get("value"))
        self.assertEqual(0, len(container.get_users()))

        # With user_id and resolver success
        container.add_user(invalid_user)
        payload = {"user_id": invalid_user.uid, "resolver": invalid_user.resolver}
        result = self.request_assert_success(f'/container/{container_serial}/unassign',
                                             payload, self.at, 'POST')
        self.assertTrue(result["result"].get("value"))
        self.assertEqual(0, len(container.get_users()))

        # Provide realm and user_id should work
        container.add_user(invalid_user)
        payload = {"realm": invalid_user.realm, "user_id": invalid_user.uid}
        result = self.request_assert_success(f'/container/{container_serial}/unassign',
                                             payload, self.at, 'POST')
        self.assertTrue(result["result"].get("value"))
        self.assertEqual(0, len(container.get_users()))

        # Provide everything
        container.add_user(invalid_user)
        payload = {"user": invalid_user.login, "realm": invalid_user.realm, "resolver": invalid_user.resolver,
                   "user_id": invalid_user.uid}
        result = self.request_assert_success(f'/container/{container_serial}/unassign',
                                             payload, self.at, 'POST')
        self.assertTrue(result["result"].get("value"))
        self.assertEqual(0, len(container.get_users()))

        # ---- Invalid realm ---
        user = User("corny", self.realm3)
        container.add_user(user)
        Realm.query.filter_by(name=self.realm3).first().delete()
        # Success if providing everything (realm does not exist, hence realm_id is not set)
        payload = {"user": "corny", "realm": self.realm3, "user_id": user.uid, "resolver": user.resolver}
        result = self.request_assert_success(f'/container/{container_serial}/unassign', payload, self.at, 'POST')
        self.assertTrue(result["result"].get("value"))
        self.assertEqual(0, len(container.get_users()))
        self.setUp_user_realm3()
        user = User("corny", self.realm3)
        container.add_user(user)
        Realm.query.filter_by(name=self.realm3).first().delete()
        # Also fails if not providing realm (sets default realm)
        payload = {"user": "corny", "user_id": user.uid, "resolver": user.resolver}
        self.request_assert_error(400, f'/container/{container_serial}/unassign',
                                  payload, self.at, 'POST',
                                  error_code=904,
                                  error_message="ERR904: The user can not be found in any resolver in this realm!")
        # Success when providing only user_id and resolver, even if realm does not exist
        payload = {"user_id": user.uid, "resolver": user.resolver}
        result = self.request_assert_success(f'/container/{container_serial}/unassign', payload, self.at, 'POST')
        self.assertTrue(result["result"].get("value"))
        self.assertEqual(0, len(container.get_users()))

        container.delete()

    def test_08_set_realms_success(self):
        # Arrange
        self.setUp_user_realms()
        self.setUp_user_realm2()
        container_serial = init_container({"type": "generic"})["container_serial"]

        # Set existing realms
        payload = {"realms": self.realm1 + "," + self.realm2}
        result = self.request_assert_success(f'/container/{container_serial}/realms', payload, self.at, 'POST')
        result = result["result"]
        self.assertTrue(result["value"])
        self.assertFalse(result["value"]["deleted"])
        self.assertTrue(result["value"][self.realm1])
        self.assertTrue(result["value"][self.realm2])

        # Set no realm shall remove all realms for the container
        payload = {"realms": ""}
        result = self.request_assert_success(f'/container/{container_serial}/realms', payload, self.at, 'POST')
        result = result["result"]
        self.assertTrue(result["value"])
        self.assertTrue(result["value"]["deleted"])
        self.assertNotIn(self.realm1, result["value"].keys())
        self.assertNotIn(self.realm2, result["value"].keys())

        delete_container_by_serial(container_serial)

        # Automatically add the user realms
        container_serial = init_container({"type": "generic", "user": "hans", "realm": self.realm1})["container_serial"]
        payload = {"realms": self.realm2}
        result = self.request_assert_success(f'/container/{container_serial}/realms', payload, self.at, 'POST')
        # TODO: Should we also add the result for the users realm even if they are not in the requested realms?
        # self.assertTrue(result["result"]["value"][self.realm1])
        self.assertTrue(result["result"]["value"][self.realm2])

        delete_container_by_serial(container_serial)

    def test_09_set_realms_fail(self):
        # Arrange
        self.setUp_user_realms()
        self.setUp_user_realm2()
        container_serial = init_container({"type": "generic"})["container_serial"]

        # Missing realm parameter
        self.request_assert_error(400, f'/container/{container_serial}/realms',
                                  {}, self.at, 'POST',
                                  error_code=905,
                                  error_message="ERR905: Missing parameter: realms")

        # Set non-existing realm
        payload = {"realms": "nonexistingrealm"}
        result = self.request_assert_success(f'/container/{container_serial}/realms', payload, self.at, 'POST')
        result = result.get("result")
        self.assertFalse(result["value"]["nonexistingrealm"])

        # Missing container serial
        self.request_assert_405('/container/realms', {"realms": [self.realm1]}, self.at, 'POST')

        delete_container_by_serial(container_serial)

    def test_10_set_description_success(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "test container"})["container_serial"]

        # Set description
        payload = {"description": "new description"}
        result = self.request_assert_success(f'/container/{container_serial}/description',
                                             payload, self.at, 'POST')
        self.assertTrue(result["result"]["value"])

        # Set empty description
        payload = {"description": ""}
        result = self.request_assert_success(f'/container/{container_serial}/description',
                                             payload, self.at, 'POST')
        self.assertTrue(result["result"]["value"])

        delete_container_by_serial(container_serial)

    def test_11_set_description_fail(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "test container"})["container_serial"]

        # Missing description parameter
        self.request_assert_error(400, f'/container/{container_serial}/description',
                                  {}, self.at, 'POST',
                                  error_code=905,
                                  error_message="ERR905: Missing parameter: description")

        # Description parameter is None
        self.request_assert_error(400, f'/container/{container_serial}/description',
                                  {"description": None}, self.at, 'POST',
                                  error_code=905,
                                  error_message="ERR905: Missing parameter: description")

        # Missing container serial
        self.request_assert_405('/container/description', {"description": "new description"},
                                self.at, 'POST')

        delete_container_by_serial(container_serial)

    def test_12_set_states_success(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "test container"})["container_serial"]

        # Set states
        payload = {"states": "active,damaged,lost"}
        result = self.request_assert_success(f'/container/{container_serial}/states',
                                             payload, self.at, 'POST')
        self.assertTrue(result["result"]["value"])
        self.assertTrue(result["result"]["value"]["active"])
        self.assertTrue(result["result"]["value"]["damaged"])
        self.assertTrue(result["result"]["value"]["lost"])

        delete_container_by_serial(container_serial)

    def test_13_set_states_fail(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "test container"})["container_serial"]

        # Missing states parameter
        self.request_assert_error(400, f'/container/{container_serial}/states',
                                  {}, self.at, 'POST',
                                  error_code=905,
                                  error_message="ERR905: Missing parameter: states")

        # Missing container serial
        self.request_assert_405('/container/states', {"states": "active,damaged,lost"},
                                self.at, 'POST')

        # Set exclusive states
        payload = {"states": "active,disabled"}
        self.request_assert_error(400, f'/container/{container_serial}/states',
                                  payload, self.at, 'POST',
                                  error_code=905,
                                  error_message="ERR905: The state list ['active', 'disabled'] contains exclusive states!")

        delete_container_by_serial(container_serial)

    def test_14_set_container_info_success(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "test container"})["container_serial"]

        # Set info
        self.request_assert_success(f'/container/{container_serial}/info/key1',
                                    {"value": "value1"}, self.at, 'POST')

        delete_container_by_serial(container_serial)

    def test_15_set_container_info_fail(self):
        # Arrange
        container_serial = init_container({"type": "generic"})["container_serial"]

        # Missing value parameter
        self.request_assert_error(400, f'/container/{container_serial}/info/key1',
                                  {}, self.at, 'POST',
                                  error_code=905,
                                  error_message="ERR905: Missing parameter: value")

        # Missing container serial
        self.request_assert_404_no_result('/container/info/key1', {"value": "value1"}, self.at, 'POST')

        # Missing key
        self.request_assert_404_no_result(f'/container/{container_serial}/info/',
                                          {"value": "value1"}, self.at, 'POST')

        delete_container_by_serial(container_serial)

    def test_16_add_remove_token_success(self):
        # Arrange
        container_serial = init_container({"type": "generic"})["container_serial"]
        hotp_01 = init_token({"genkey": "1"})
        hotp_01_serial = hotp_01.get_serial()
        hotp_02 = init_token({"genkey": "1"})
        hotp_02_serial = hotp_02.get_serial()
        hotp_03 = init_token({"genkey": "1"})
        hotp_03_serial = hotp_03.get_serial()

        # Add single token
        result = self.request_assert_success(f'/container/{container_serial}/add',
                                             {"serial": hotp_01_serial}, self.at, 'POST')
        self.assertTrue(result["result"]["value"])

        # Remove single token
        result = self.request_assert_success(f'/container/{container_serial}/remove',
                                             {"serial": hotp_01_serial}, self.at, 'POST')
        self.assertTrue(result["result"]["value"])

        # Add multiple tokens
        result = self.request_assert_success(f'/container/{container_serial}/addall',
                                             {"serial": f"{hotp_01_serial},{hotp_02_serial},{hotp_03_serial}"},
                                             self.at, 'POST')
        self.assertTrue(result["result"]["value"][hotp_01_serial])
        self.assertTrue(result["result"]["value"][hotp_02_serial])
        self.assertTrue(result["result"]["value"][hotp_03_serial])

        # Remove multiple tokens with spaces in list
        result = self.request_assert_success(f'/container/{container_serial}/removeall',
                                             {"serial": f"{hotp_01_serial}, {hotp_02_serial}, {hotp_03_serial}"},
                                             self.at, 'POST')
        self.assertTrue(result["result"]["value"][hotp_01_serial])
        self.assertTrue(result["result"]["value"][hotp_02_serial])
        self.assertTrue(result["result"]["value"][hotp_03_serial])

        # Add multiple tokens with spaces in list
        result = self.request_assert_success(f'/container/{container_serial}/addall',
                                             {"serial": f"{hotp_01_serial}, {hotp_02_serial}, {hotp_03_serial}"},
                                             self.at, 'POST')
        self.assertTrue(result["result"]["value"][hotp_01_serial])
        self.assertTrue(result["result"]["value"][hotp_02_serial])
        self.assertTrue(result["result"]["value"][hotp_03_serial])

        # Remove multiple tokens
        result = self.request_assert_success(f'/container/{container_serial}/removeall',
                                             {"serial": f"{hotp_01_serial},{hotp_02_serial},{hotp_03_serial}"},
                                             self.at, 'POST')
        self.assertTrue(result["result"]["value"][hotp_01_serial])
        self.assertTrue(result["result"]["value"][hotp_02_serial])
        self.assertTrue(result["result"]["value"][hotp_03_serial])

        delete_container_by_serial(container_serial)

    def test_17_add_token_fail(self):
        # Arrange
        container_serial = init_container({"type": "generic"})["container_serial"]
        hotp_01 = init_token({"genkey": "1"})
        hotp_01_serial = hotp_01.get_serial()

        # Add token without serial
        self.request_assert_error(400, f'/container/{container_serial}/add',
                                  {}, self.at, 'POST',
                                  error_code=905,
                                  error_message="ERR905: Missing parameter: 'serial' or 'serials'")

        # Add token without container serial
        self.request_assert_405('/container/add', {"serial": hotp_01_serial}, self.at, 'POST')

        delete_container_by_serial(container_serial)

    def test_18_remove_token_fail(self):
        # Arrange
        container_serial = init_container({"type": "generic"})["container_serial"]
        hotp_01 = init_token({"genkey": "1"})
        hotp_01_serial = hotp_01.get_serial()
        add_token_to_container(container_serial, hotp_01_serial)

        # Remove token without serial
        self.request_assert_error(400, f'/container/{container_serial}/remove',
                                  {}, self.at, 'POST',
                                  error_code=905,
                                  error_message="ERR905: Missing parameter: 'serial' or 'serials'")

        # Remove token without container serial
        self.request_assert_405('/container/remove', {"serial": hotp_01_serial}, self.at, 'POST')

        delete_container_by_serial(container_serial)

    def test_19_get_state_types(self):
        result = self.request_assert_success('/container/statetypes', {}, self.at, 'GET')
        self.assertTrue(result["result"]["value"])
        self.assertIn("active", result["result"]["value"].keys())
        self.assertIn("disabled", result["result"]["value"]["active"])
        self.assertIn("lost", result["result"]["value"].keys())

    def test_20_get_types(self):
        result = self.request_assert_success('/container/types', {}, self.at, 'GET')
        self.assertTrue(result["result"]["value"])
        # Check that all container types are included
        self.assertIn("smartphone", result["result"]["value"])
        self.assertIn("generic", result["result"]["value"])
        self.assertIn("yubikey", result["result"]["value"])
        # Check that all properties are set
        self.assertIn("description", result["result"]["value"]["generic"])
        self.assertIn("token_types", result["result"]["value"]["generic"])

    def test_21_get_all_containers_paginate(self):
        # Arrange
        self.setUp_user_realms()
        # Create containers
        types = ["Smartphone", "generic", "Yubikey", "Smartphone", "generic", "Yubikey"]
        container_serials = []
        for t in types:
            serial = init_container({"type": t, "description": "test container"})["container_serial"]
            container_serials.append(serial)
        # Add token to container 1
        container = find_container_by_serial(container_serials[1])
        token = init_token({"genkey": "1"}, user=User("shadow", self.realm1))
        token_serial = token.get_serial()
        add_token_to_container(container_serials[1], token_serial)
        # Assign user to container 1
        user_hans = User(login="hans", realm=self.realm1)
        container.add_user(user_hans)
        # Add second realm
        self.setUp_user_realm2()
        container.set_realms([self.realm2], add=True)
        # Add info
        container.update_container_info([TokenContainerInfoData(key="key1", value="value1")])

        # Filter for type
        result = self.request_assert_success('/container/',
                                             {"type": "generic", "pagesize": 15},
                                             self.at, 'GET')
        for container in result["result"]["value"]["containers"]:
            self.assertEqual(container["type"], "generic")

        # Filter for assigned containers
        result = self.request_assert_success('/container/',
                                             {"assigned": True, "pagesize": 15},
                                             self.at, 'GET')
        self.assertEqual(1, result["result"]["value"]["count"])

        # filter for realm the admin is not allowed to manage (only get the container that is also in realm 1)
        container_serial = init_container({"type": "generic", "realm": self.realm2})["container_serial"]
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_LIST, realm=self.realm1)
        result = self.request_assert_success('/container/',
                                             {"container_realm": self.realm2, "pagesize": 15},
                                             self.at, 'GET')
        self.assertEqual(1, result["result"]["value"]["count"])
        self.assertEqual(container_serials[1], result["result"]["value"]["containers"][0]["serial"])
        delete_policy("policy")
        delete_container_by_serial(container_serial)

        # Filter for token serial
        result = self.request_assert_success('/container/',
                                             {"token_serial": token_serial, "pagesize": 15},
                                             self.at, 'GET')
        self.assertTrue(container_serials[1], result["result"]["value"]["containers"][0]["serial"])
        self.assertEqual(result["result"]["value"]["count"], 1)

        # Set hide_container_info_policy
        set_policy("hide_info", scope=SCOPE.ADMIN,
                   action=f"{PolicyAction.HIDE_CONTAINER_INFO}=encrypt_algorithm device,{PolicyAction.CONTAINER_LIST}")
        container3 = find_container_by_serial(container_serials[3])
        container3.set_container_info([TokenContainerInfoData(key="encrypt_algorithm", value="AES"),
                                       TokenContainerInfoData(key="encrypt_mode", value="GCM"),
                                       TokenContainerInfoData(key="device", value="ABC1234"),
                                       TokenContainerInfoData(key=RegistrationState.get_key(),
                                                              value=RegistrationState.REGISTERED.value)])
        # Filter for container serial
        result = self.request_assert_success('/container/',
                                             {"container_serial": container_serials[3], "pagesize": 15},
                                             self.at, 'GET')
        result_container = result["result"]["value"]["containers"][0]
        self.assertTrue(container_serials[3], result_container["serial"])
        self.assertSetEqual({"encrypt_mode", RegistrationState.get_key(), "creation_date"},
                            set(result_container["info"].keys()))
        # Get all containers
        result = self.request_assert_success('/container/', {"pagesize": 15}, self.at, 'GET')
        result_containers = result["result"]["value"]["containers"]
        for container in result_containers:
            info_keys = container["info"].keys()
            self.assertNotIn("encrypt_algorithm", info_keys)
            self.assertNotIn("device", info_keys)
        delete_policy("hide_info")

        # Test output
        result = self.request_assert_success('/container/',
                                             {"container_serial": container_serials[1], "pagesize": 15, "page": 1},
                                             self.at, 'GET')
        containerdata = result["result"]["value"]
        # Pagination
        self.assertEqual(1, containerdata["count"])
        self.assertIn("prev", containerdata.keys())
        self.assertIn("next", containerdata.keys())
        self.assertIn("current", containerdata.keys())
        self.assertEqual(1, len(containerdata["containers"]))
        # Container data
        res_container = containerdata["containers"][0]
        self.assertEqual("generic", res_container["type"])
        self.assertEqual(container_serials[1], res_container["serial"])
        self.assertEqual("test container", res_container["description"])
        self.assertIn("last_authentication", res_container.keys())
        self.assertIn("last_synchronization", res_container.keys())
        self.assertIn("active", res_container["states"])
        # Tokens
        self.assertEqual(1, len(res_container["tokens"]))
        # User
        self.assertEqual(1, len(res_container["users"]))
        self.assertEqual(user_hans.login, res_container["users"][0]["user_name"])
        self.assertEqual(user_hans.realm, res_container["users"][0]["user_realm"])
        self.assertEqual(user_hans.resolver, res_container["users"][0]["user_resolver"])
        self.assertEqual(user_hans.uid, res_container["users"][0]["user_id"])
        # Realms
        self.assertIn(self.realm1, res_container["realms"])
        self.assertIn(self.realm2, res_container["realms"])
        # Info
        self.assertIn("key1", res_container["info"].keys())
        self.assertEqual("value1", res_container["info"]["key1"])

    def test_22_get_all_containers_paginate_invalid_params(self):
        init_container({"type": "generic", "description": "test container"})

        # Filter for non-existing type
        result = self.request_assert_success('/container/',
                                             {"type": "non-existing", "pagesize": 15},
                                             self.at, 'GET')
        self.assertEqual(0, result["result"]["value"]["count"])

        # Filter for non existing token serial
        result = self.request_assert_success('/container/',
                                             {"token_serial": "non-existing", "pagesize": 15},
                                             self.at, 'GET')
        self.assertEqual(result["result"]["value"]["count"], 0)

    def test_23_delete_container_info_success(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "test container"})["container_serial"]
        container = find_container_by_serial(container_serial)
        container.update_container_info([TokenContainerInfoData(key="test", value="1234")])

        # Delete info
        self.request_assert_success(f"/container/{container_serial}/info/delete/test",
                                    {}, self.at, "DELETE")

    def test_24_delete_container_info_fail(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "test container"})["container_serial"]
        container = find_container_by_serial(container_serial)
        container.update_container_info([TokenContainerInfoData(key="test", value="1234"),
                                         TokenContainerInfoData(key="internal_test", value="abcd",
                                                                info_type=PI_INTERNAL)])

        # Try to delete internal key
        result = self.request_assert_success(f"/container/{container_serial}/info/delete/internal_test",
                                             {}, self.at, "DELETE")
        self.assertFalse(result["result"]["value"])

    def test_25_broken_user_resolver(self):
        # Arrange
        self.setUp_user_realms()
        container_serial = init_container({"type": "generic",
                                           "description": "test container",
                                           "user": "hans",
                                           "realm": self.realm1})["container_serial"]
        # Get all containers with assigned user
        result = self.request_assert_success('/container/', {}, self.at, 'GET')
        # Get the current container
        container = [x for x in result["result"]["value"]["containers"] if x["serial"] == container_serial][0]
        self.assertEqual(container["users"][0]["user_name"], "hans", result["result"])
        # Break the resolver
        save_resolver({"resolver": self.resolvername1,
                       "type": "passwdresolver",
                       "fileName": "/unknown/file"})
        # And check the container again
        result = self.request_assert_success('/container/', {}, self.at, 'GET')
        container = [x for x in result["result"]["value"]["containers"] if x["serial"] == container_serial][0]
        self.assertEqual(container["users"][0]["user_name"], "**resolver error**", result["result"])
