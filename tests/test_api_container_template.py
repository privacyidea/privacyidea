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
from privacyidea.lib.tokenrolloutstate import RolloutState
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


class APIContainerTemplate(APIContainerTest):

    def test_01_create_delete_template_success(self):
        template_name = "test"
        # Create template without tokens
        data = json.dumps({"template_options": {"tokens": []}, "default": True})
        result = self.request_assert_success(f'/container/smartphone/template/{template_name}',
                                             data, self.at, 'POST')
        self.assertGreater(result["result"]["value"]["template_id"], 0)

        # Delete template
        result = self.request_assert_success(f'/container/template/{template_name}',
                                             {}, self.at, 'DELETE')
        self.assertTrue(result["result"]["value"])

    def test_02_create_template_fail(self):
        # Create template without name
        self.request_assert_404_no_result('/container/smartphone/template',
                                          {}, self.at, 'POST')

    def test_03_delete_template_fail(self):
        # Delete non existing template
        template_name = "random"
        self.request_assert_405(f'container/template/{template_name}',
                                {}, None, 'POST')

    def test_04_update_template_options_success(self):
        # Create a template
        template_name = "test"
        template_id = create_container_template(container_type="generic",
                                                template_name=template_name,
                                                options={"tokens": [{"type": "hotp"}]})

        # Update options
        params = json.dumps({"template_options": {
            "tokens": [{"type": "hotp", "genkey": True}, {"type": "totp", "genkey": True, "hashlib": "sha256"}]}})

        result = self.request_assert_success(f'/container/generic/template/{template_name}',
                                             params, self.at, 'POST')
        self.assertEqual(template_id, result["result"]["value"]["template_id"])

        template = get_template_obj(template_name)
        template.delete()

    def test_05_update_template_options_fail(self):
        # Create a template
        template_name = "test"
        create_container_template(container_type="generic",
                                  template_name=template_name,
                                  options={"tokens": [{"type": "hotp"}]})

        # Update with wrong options type
        params = json.dumps({"template_options": json.dumps({
            "tokens": [{"type": "hotp", "genkey": True}, {"type": "totp", "genkey": True, "hashlib": "sha256"}]})})

        self.request_assert_error(400, f'/container/generic/template/{template_name}',
                                  params, self.at, 'POST',
                                  error_code=905)

        template = get_template_obj(template_name)
        template.delete()

    def test_06_create_container_with_template_success(self):
        # Create a template
        template_params = {"name": "test",
                           "container_type": "smartphone",
                           "template_options": {"tokens": [{"type": "hotp", "genkey": True}]}}
        create_container_template(container_type=template_params["container_type"],
                                  template_name=template_params["name"],
                                  options=template_params["template_options"])

        def check_result(result):
            container_serial = result["result"]["value"]["container_serial"]
            container = find_container_by_serial(container_serial)
            tokens = container.get_tokens()
            self.assertEqual(1, len(tokens))
            self.assertEqual("hotp", tokens[0].get_type())
            # result contains enroll info for one token
            self.assertEqual(1, len(result["result"]["value"]["tokens"]))
            container_template = container.template
            self.assertEqual(template_params["name"], container_template.name)

        # create container by passing the complete template dictionary
        request_params = json.dumps({"type": "smartphone", "template": template_params})
        result = self.request_assert_success('/container/init', request_params, self.at, 'POST')
        check_result(result)

        # create container by passing only the template name
        result = self.request_assert_success('/container/init',
                                             {"type": "smartphone", "template_name": template_params["name"]},
                                             self.at, 'POST')
        check_result(result)

        template = get_template_obj(template_params["name"])
        template.delete()

    def test_07_create_container_with_template_no_tokens(self):
        # Create a template with no tokens
        template_params = {"name": "test",
                           "container_type": "smartphone",
                           "template_options": {}}
        create_container_template(container_type=template_params["container_type"],
                                  template_name=template_params["name"],
                                  options=template_params["template_options"])

        def check_result(result):
            container_serial = result["result"]["value"]["container_serial"]
            container = find_container_by_serial(container_serial)
            tokens = container.get_tokens()
            self.assertEqual(0, len(tokens))
            self.assertIsNone(result["result"]["value"].get("tokens"))
            self.assertEqual(template_params["name"], container.template.name)

        # with template dict
        request_params = json.dumps({"type": "smartphone", "template": template_params})
        result = self.request_assert_success("/container/init", request_params, self.at, "POST")
        check_result(result)

        # with template from db
        request_params = json.dumps({"type": "smartphone", "template": template_params})
        result = self.request_assert_success("/container/init",
                                             {"type": "smartphone", "template_name": template_params["name"]},
                                             self.at, "POST")
        check_result(result)

        template = get_template_obj(template_params["name"])
        template.delete()

        # Create a template without template options
        template_params = {"name": "test",
                           "container_type": "smartphone"}

        request_params = json.dumps({"type": "smartphone", "template": template_params})
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertEqual(0, len(tokens))

    def test_08_create_container_with_template_missing_policies(self):
        # Create a template with hotp and push
        template_params = {"name": "test",
                           "container_type": "smartphone",
                           "template_options": {
                               "tokens": [{"type": "hotp", "genkey": True}, {"type": "push", "genkey": True}]}}
        create_container_template(container_type=template_params["container_type"],
                                  template_name=template_params["name"],
                                  options=template_params["template_options"])

        def check_result(result):
            # only hotp token is created, push require policy that is not set
            container_serial = result["result"]["value"]["container_serial"]
            container = find_container_by_serial(container_serial)
            tokens = container.get_tokens()
            self.assertEqual(1, len(tokens))

        # Create a container from the template dict
        request_params = json.dumps({"type": "smartphone", "template": template_params})
        result = self.request_assert_success('/container/init', request_params, self.at, 'POST')
        check_result(result)

        # Create a container from the db template
        result = self.request_assert_success("/container/init",
                                             {"type": "smartphone", "template_name": template_params["name"]}, self.at,
                                             "POST")
        check_result(result)

        template = get_template_obj(template_params["name"])
        template.delete()

    def test_09_create_container_with_template_all_tokens_success(self):
        self.setUp_user_realm3()
        # Policies
        set_policy("push", scope=SCOPE.ENROLL, action={PushAction.FIREBASE_CONFIG: "poll only",
                                                       PushAction.REGISTRATION_URL: "http://test/ttype/push",
                                                       PolicyAction.TOKENISSUER: "{realm}",
                                                       PolicyAction.TOKENLABEL: "serial_{serial}"})
        set_policy("admin", SCOPE.ADMIN, action={PolicyAction.CONTAINER_CREATE: True,
                                                 "enrollHOTP": True, "enrollREMOTE": True, "enrollDAYPASSWORD": True,
                                                 "enrollSPASS": True, "enrollTOTP": True, "enroll4EYES": True,
                                                 "enrollPAPER": True, "enrollTAN": True, "enrollPUSH": True,
                                                 "enrollINDEXEDSECRET": True,
                                                 "enrollAPPLSPEC": True, "enrollREGISTRATION": True, "enrollSMS": True,
                                                 "enrollEMAIL": True, "enrollTIQR": True,
                                                 "indexedsecret_force_attribute": "username",
                                                 "hotp_hashlib": "sha256"})
        set_policy("pw_length", scope=SCOPE.ENROLL, action={PolicyAction.REGISTRATIONCODE_LENGTH: 12})

        # privacyIDEA server for the remote token
        pi_server_id = add_privacyideaserver(identifier="myserver",
                                             url="https://pi/pi",
                                             description="Hallo")
        # service id for applspec
        service_id = set_serviceid("test", "This is an awesome test service id")

        # Create a template with all token types allowed for the generic container template
        tokens_dict = [
            {"type": "hotp", "genkey": True, "user": True},
            {"type": "remote", "remote.server_id": pi_server_id, "remote.serial": "1234"},
            {"type": "daypassword", "genkey": True}, {"type": "spass"},
            {"type": "totp", "genkey": True},
            {"type": "4eyes", "4eyes": {self.realm3: {"count": 2, "selected": True}}},
            {"type": "paper"}, {"type": "tan"}, {"type": "push", "genkey": True, "user": True},
            {"type": "indexedsecret", "user": True},
            {"type": "applspec", "genkey": True, "service_id": service_id},
            {"type": "registration"}, {"type": "sms", "dynamic_phone": True, "genkey": True, "user": True},
            {"type": "email", "dynamic_email": True, "genkey": True, "user": True}, {"type": "tiqr", "user": True}
        ]
        template_params = {"name": "test",
                           "container_type": "generic",
                           "template_options": {"tokens": tokens_dict}}
        create_container_template(container_type=template_params["container_type"],
                                  template_name=template_params["name"],
                                  options=template_params["template_options"])

        def check_result(result):
            # check tokens that were created
            container_serial = result["result"]["value"]["container_serial"]
            container = find_container_by_serial(container_serial)
            tokens = container.get_tokens()
            self.assertEqual(15, len(tokens))
            self.assertEqual(15, len(result["result"]["value"]["tokens"]))

            # check tokens and init details
            owner = User(login="cornelius", realm=self.realm3)
            init_details = result["result"]["value"]["tokens"]
            for token in tokens:
                token_type = token.get_type()

                # check user assignment
                if token_type in ["hotp", "indexedsecret", "push", "sms", "email", "tiqr"]:
                    self.assertEqual(owner, token.user)
                    if token_type == "hotp":
                        # check default hashlib
                        self.assertEqual("sha256", token.hashlib)
                else:
                    self.assertIsNone(token.user)

                # check init details
                if token_type in ["hotp", "totp", "daypassword"]:
                    self.assertTrue(isinstance(init_details[token.get_serial()].get("googleurl"), dict))
                elif token_type in ["paper", "tan"]:
                    self.assertTrue(isinstance(init_details[token.get_serial()].get("otps"), dict))
                elif token_type == "push":
                    serial = token.get_serial()
                    push_url = init_details[serial].get("pushurl")
                    self.assertTrue(isinstance(push_url, dict))
                    self.assertIn(f"issuer={self.realm3}", push_url["value"])
                    self.assertIn(f"serial_{serial}", push_url["value"])
                elif token_type == "applspec":
                    self.assertTrue(isinstance(init_details[token.get_serial()].get("password"), str))
                elif token_type == "registration":
                    self.assertEqual(12, len(init_details[token.get_serial()]["registrationcode"]))
                elif token_type == "tiqr":
                    self.assertTrue(isinstance(init_details[token.get_serial()].get("tiqrenroll"), dict))

            [token.delete_token() for token in tokens]
            container.delete()

        # Create a container from the template dict
        request_params = json.dumps(
            {"type": "generic", "template": template_params, "user": "cornelius", "realm": self.realm3})
        result = self.request_assert_success("/container/init", request_params, self.at, "POST")
        check_result(result)

        # Create a container from the template name
        result = self.request_assert_success("/container/init",
                                             {"type": "generic", "template_name": template_params["name"],
                                              "user": "cornelius", "realm": self.realm3}, self.at, "POST")
        check_result(result)

        template = get_template_obj(template_params["name"])
        template.delete()

        delete_policy("push")
        delete_policy("admin")
        delete_policy("pw_length")

    def test_10_create_container_with_template_some_tokens_fail(self):
        # tokens that require policies fail: push
        # tokens that require user fail: tiqr
        # Policies
        set_policy("admin", SCOPE.ADMIN, action={PolicyAction.CONTAINER_CREATE: True,
                                                 "enrollHOTP": True, "enrollREMOTE": True, "enrollDAYPASSWORD": True,
                                                 "enrollSPASS": True, "enrollTOTP": True, "enroll4EYES": True,
                                                 "enrollPAPER": True, "enrollTAN": True, "enrollPUSH": True,
                                                 "enrollINDEXEDSECRET": True,
                                                 "enrollAPPLSPEC": True, "enrollREGISTRATION": True, "enrollSMS": True,
                                                 "enrollEMAIL": True, "enrollTIQR": True,
                                                 "indexedsecret_force_attribute": "username",
                                                 "hotp_hashlib": "sha256"})
        set_policy("pw_length", scope=SCOPE.ENROLL, action={PolicyAction.REGISTRATIONCODE_LENGTH: 12})

        # privacyIDEA server for the remote token
        pi_server_id = add_privacyideaserver(identifier="myserver",
                                             url="https://pi/pi",
                                             description="Hallo")
        # service id for applspec
        service_id = set_serviceid("test", "This is an awesome test service id")

        # Create a template with all token types allowed for the generic container template
        tokens_dict = [
            {"type": "hotp", "genkey": True, "user": True},
            {"type": "remote", "remote.server_id": pi_server_id, "remote.serial": "1234"},
            {"type": "daypassword", "genkey": True}, {"type": "spass"},
            {"type": "totp", "genkey": True},
            {"type": "4eyes", "4eyes": {self.realm3: {"count": 2, "selected": True}}},
            {"type": "paper"}, {"type": "tan"}, {"type": "push", "genkey": True, "user": True},
            {"type": "indexedsecret", "user": True},
            {"type": "applspec", "genkey": True, "service_id": service_id},
            {"type": "registration"}, {"type": "sms", "dynamic_phone": True, "genkey": True, "user": True},
            {"type": "email", "dynamic_email": True, "genkey": True, "user": True}, {"type": "tiqr", "user": True}
        ]
        template_params = {"name": "test",
                           "container_type": "generic",
                           "template_options": {"tokens": tokens_dict}}
        create_container_template(container_type=template_params["container_type"],
                                  template_name=template_params["name"],
                                  options=template_params["template_options"])

        def check_result(result):
            # check tokens that were created
            container_serial = result["result"]["value"]["container_serial"]
            container = find_container_by_serial(container_serial)
            tokens = container.get_tokens()
            all_token_types = [token.get_type() for token in tokens]
            self.assertNotIn("push", all_token_types)
            self.assertNotIn("tiqr", all_token_types)
            self.assertEqual(13, len(tokens))
            self.assertEqual(13, len(result["result"]["value"]["tokens"]))

            # check tokens and init details
            init_details = result["result"]["value"]["tokens"]
            for token in tokens:
                token_type = token.get_type()

                # check user assignment
                self.assertIsNone(token.user)

                if token_type == "hotp":
                    # check default hashlib
                    self.assertEqual("sha256", token.hashlib)

                # check init details
                if token_type in ["hotp", "totp", "daypassword"]:
                    self.assertTrue(isinstance(init_details[token.get_serial()].get("googleurl"), dict))
                elif token_type in ["paper", "tan"]:
                    self.assertTrue(isinstance(init_details[token.get_serial()].get("otps"), dict))
                elif token_type == "applspec":
                    self.assertTrue(isinstance(init_details[token.get_serial()].get("password"), str))
                elif token_type == "registration":
                    self.assertEqual(12, len(init_details[token.get_serial()]["registrationcode"]))
                elif token_type == "tiqr":
                    self.assertTrue(isinstance(init_details[token.get_serial()].get("tiqrenroll"), dict))

            [token.delete_token() for token in tokens]
            container.delete()

        # Create a container from the template dict
        self.setUp_user_realm3()
        request_params = json.dumps(
            {"type": "generic", "template": template_params})
        result = self.request_assert_success("/container/init", request_params, self.at, "POST")
        check_result(result)

        # Create container from the db template
        result = self.request_assert_success("/container/init",
                                             {"type": "generic", "template_name": template_params["name"]}, self.at,
                                             "POST")
        check_result(result)

        template = get_template_obj(template_params["name"])
        template.delete()

        delete_policy("admin")
        delete_policy("pw_length")

    def test_11_create_container_with_template_max_token_policies(self):
        # Limit number of tokens per user and type
        set_policy("max_token", scope=SCOPE.ENROLL, action={PolicyAction.MAXTOKENUSER: 6,
                                                            TANAction.TANTOKEN_COUNT: 2,
                                                            PAPERACTION.PAPERTOKEN_COUNT: 2,
                                                            PolicyAction.MAXTOKENREALM: 7})
        self.setUp_user_realms()
        hans = User(login="hans", realm=self.realm1)

        # Create tokens for hans
        init_token({"type": "paper"}, user=hans)
        init_token({"type": "tan"}, user=hans)

        template_params = {"name": "test",
                           "container_type": "generic",
                           "template_options": {
                               "tokens": [{"type": "hotp", "genkey": True, "user": True},
                                          {"type": "paper", "user": True},
                                          {"type": "tan", "user": True}]}}
        request_params = json.dumps({"type": "generic", "user": "hans", "realm": self.realm1,
                                     "template": template_params})

        # second paper and tan tokens for hans can be created with the template
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertEqual(3, len(tokens))
        token_types = [token.get_type() for token in tokens]
        self.assertEqual(set(["hotp", "paper", "tan"]), set(token_types))

        # third paper and tan tokens for hans can NOT be created
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container1 = find_container_by_serial(container_serial)
        tokens = container1.get_tokens()
        self.assertEqual(1, len(tokens))
        self.assertEqual("hotp", tokens[0].get_type())

        # Can not create any type of token: hans already has 6 tokens
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container2 = find_container_by_serial(container_serial)
        tokens = container2.get_tokens()
        self.assertEqual(0, len(tokens))

        # create tokens for another user in this realm: only one token created
        request_params = json.dumps({"type": "generic", "user": "selfservice", "realm": self.realm1,
                                     "template": template_params})

        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertEqual(1, len(tokens))

        delete_policy("max_token")
        container1.delete()
        container2.delete()
        user_tokens = get_tokens_from_serial_or_user(serial=None, user=hans)
        [token.delete_token() for token in user_tokens]

    def test_12_create_container_with_template_otp_pin(self):
        # Set otp pin policy
        set_policy("otp_pin", scope=SCOPE.ADMIN, action={PolicyAction.OTPPINMAXLEN: 6, PolicyAction.OTPPINMINLEN: 2})
        set_policy("encrypt", scope=SCOPE.ENROLL, action=PolicyAction.ENCRYPTPIN)
        # Set admin policies
        set_policy("admin", scope=SCOPE.ADMIN,
                   action={PolicyAction.CONTAINER_CREATE: True, "enrollHOTP": True})
        set_policy("enrollPIN", SCOPE.ADMIN, action=PolicyAction.ENROLLPIN)
        set_policy("change_pin", SCOPE.ENROLL, action={PolicyAction.CHANGE_PIN_FIRST_USE: True})

        # correct pin
        template_params = {"name": "test",
                           "container_type": "smartphone",
                           "template_options": {"tokens": [{"type": "hotp", "genkey": True, "pin": "1234"}]}}
        request_params = json.dumps({"type": "smartphone", "user": "hans", "realm": self.realm1,
                                     "template": template_params})
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertEqual(1, len(tokens))
        self.assertNotEqual(-1, tokens[0].token.get_pin())
        self.assertIsNotNone(get_tokeninfo(tokens[0].get_serial(), "next_pin_change"))
        delete_policy("change_pin")

        # pin too short
        template_params = {"name": "test",
                           "container_type": "smartphone",
                           "template_options": {"tokens": [{"type": "hotp", "genkey": True, "pin": "1"}]}}
        request_params = json.dumps({"type": "smartphone", "user": "hans", "realm": self.realm1,
                                     "template": template_params})
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertEqual(0, len(tokens))

        # Not allowed to set the PIN. This will cause the token to not be enrolled at all
        delete_policy("otp_pin")
        delete_policy("enrollPIN")
        template_params = {"name": "test",
                           "container_type": "smartphone",
                           "template_options": {"tokens": [{"type": "hotp", "genkey": True, "pin": "1234"}]}}
        request_params = json.dumps({"type": "smartphone", "user": "hans", "realm": self.realm1,
                                     "template": template_params})
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertEqual(0, len(tokens))

        # random pin
        set_policy("random_pin", scope=SCOPE.ENROLL, action={PolicyAction.OTPPINRANDOM: 8})
        template_params = {"name": "test",
                           "container_type": "smartphone",
                           "template_options": {"tokens": [{"type": "hotp", "genkey": True}]}}
        request_params = json.dumps({"type": "smartphone", "user": "hans", "realm": self.realm1,
                                     "template": template_params})
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertEqual(1, len(tokens))
        self.assertNotEqual(-1, tokens[0].token.get_pin())

        delete_policy("random_pin")
        delete_policy("encrypt")
        delete_policy("admin")

    def test_13_create_container_with_template_verify_enrollment(self):
        # Policies
        set_policy("enrollment", scope=SCOPE.ENROLL,
                   action={PolicyAction.VERIFY_ENROLLMENT: "hotp totp paper tan indexedsecret"})

        # tokens
        tokens_dict = [
            {"type": "hotp", "genkey": True}, {"type": "totp", "genkey": True},
            {"type": "paper"}, {"type": "tan"}, {"type": "indexedsecret"},
        ]
        template_params = {"name": "test",
                           "container_type": "generic",
                           "template_options": {"tokens": tokens_dict}}
        request_params = json.dumps({"type": "generic", "user": "hans", "realm": self.realm1,
                                     "template": template_params})
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertEqual(5, len(tokens))
        token_results = result["result"]["value"]["tokens"]
        for token in tokens:
            self.assertTrue(RolloutState.VERIFY_PENDING, token.rollout_state)
            self.assertEqual(RolloutState.VERIFY_PENDING, token_results[token.get_serial()]["rollout_state"])
            self.assertTrue(isinstance(token_results[token.get_serial()]["verify"], dict))

        # cleanup
        [token.delete_token() for token in tokens]
        delete_policy("enrollment")

    def test_14_create_container_with_template_2_step_enrollment(self):
        # Policies
        set_policy("enrollment", scope=SCOPE.ADMIN,
                   action={"hotp_2step": "allow", PolicyAction.CONTAINER_CREATE: True, "enrollHOTP": True,
                           "enrollTOTP": True})

        # tokens
        hotp_serial = "OATH0001"
        totp_serial = "TOTP0001"
        tokens_dict = [{"type": "hotp", "genkey": True, "2stepinit": True, "serial": hotp_serial},
                       {"type": "totp", "genkey": True, "serial": totp_serial}]
        template_params = {"name": "test",
                           "container_type": "generic",
                           "template_options": {"tokens": tokens_dict}}
        request_params = json.dumps({"type": "generic", "user": "hans", "realm": self.realm1,
                                     "template": template_params})
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')

        # check result
        token_result = result["result"]["value"]["tokens"]
        hotp_result_keys = list(token_result[hotp_serial].keys())
        self.assertIn("2step_salt", hotp_result_keys)
        self.assertIn("2step_output", hotp_result_keys)
        self.assertIn("2step_difficulty", hotp_result_keys)
        totp_result_keys = list(token_result[totp_serial].keys())
        self.assertNotIn("2step_salt", totp_result_keys)
        self.assertNotIn("2step_output", totp_result_keys)
        self.assertNotIn("2step_difficulty", totp_result_keys)

        # check tokens
        container_serial = result["result"]["value"]["container_serial"]
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        for token in tokens:
            if token.get_type() == "hotp":
                self.assertEqual(RolloutState.CLIENTWAIT, token.rollout_state)
            else:
                self.assertEqual(RolloutState.ENROLLED, token.rollout_state)

        # cleanup
        [token.delete_token() for token in tokens]
        delete_policy("enrollment")

    def test_15_get_template(self):
        create_container_template(container_type="smartphone",
                                  template_name="test1",
                                  options={})
        create_container_template(container_type="generic",
                                  template_name="test2",
                                  options={})
        create_container_template(container_type="smartphone",
                                  template_name="test3",
                                  options={})

        query_params = {"container_type": "smartphone", "pagesize": 15, "page": 1}
        result = self.request_assert_success('/container/templates', query_params, self.at, 'GET')
        self.assertEqual(2, result["result"]["value"]["count"])
        self.assertEqual(1, result["result"]["value"]["current"])
        self.assertEqual(2, len(result["result"]["value"]["templates"]))

    def test_16_compare_template_with_containers(self):
        template_options = {"options": {SmartphoneOptions.KEY_ALGORITHM: "secp384r1"},
                            "tokens": [{"type": "hotp", "genkey": True}, {"type": "daypassword", "genkey": True}]}
        create_container_template(container_type="smartphone", template_name="test", options=template_options)

        # create container with template
        request_params = json.dumps({"type": "smartphone",
                                     "template": {"name": "test", "container_type": "smartphone",
                                                  "template_options": template_options}})
        result = self.request_assert_success('/container/init', request_params, self.at, 'POST')
        equal_cserial = result["result"]["value"]["container_serial"]

        # Create container with tokens and link with template
        cserial = init_container({"type": "smartphone"})["container_serial"]
        container = find_container_by_serial(cserial)
        container.template = "test"

        hotp = init_token({"type": "hotp", "genkey": True})
        totp1 = init_token({"type": "totp", "genkey": True})
        totp2 = init_token({"type": "totp", "genkey": True})
        container.add_token(hotp)
        container.add_token(totp1)
        container.add_token(totp2)

        # Compare template with all containers
        result = self.request_assert_success("/container/template/test/compare", {}, self.at, "GET")
        # Check result for equal container
        container_diff = result["result"]["value"][equal_cserial]
        token_diff = container_diff["tokens"]
        self.assertEqual(0, len(token_diff["missing"]))
        self.assertEqual(0, len(token_diff["additional"]))
        self.assertTrue(token_diff["equal"])
        # Check result for unequal container
        container_diff = result["result"]["value"][cserial]
        token_diff = container_diff["tokens"]
        self.assertSetEqual({"daypassword"}, set(token_diff["missing"]))
        self.assertSetEqual({"totp", "totp"}, set(token_diff["additional"]))
        self.assertFalse(token_diff["equal"])

        # Compare template with specific container
        result = self.request_assert_success("/container/template/test/compare", {"container_serial": cserial},
                                             self.at, "GET")
        # Check result for unequal container
        container_diff = result["result"]["value"][cserial]
        token_diff = container_diff["tokens"]
        self.assertSetEqual({"daypassword"}, set(token_diff["missing"]))
        self.assertSetEqual({"totp", "totp"}, set(token_diff["additional"]))
        self.assertFalse(token_diff["equal"])
        self.assertNotIn(equal_cserial, result["result"]["value"].keys())

        # Clean up
        container.delete()
        hotp.delete_token()
        totp1.delete_token()
        totp2.delete_token()
        get_template_obj("test").delete()

    def test_17_get_template_token_types(self):
        result = self.request_assert_success('/container/template/tokentypes', {}, self.at, 'GET')
        self.assertEqual(3, len(result["result"]["value"]))
        template_token_types = result["result"]["value"]
        template_container_types = template_token_types.keys()

        self.assertIn("generic", template_container_types)
        self.assertIn("smartphone", template_container_types)
        self.assertIn("yubikey", template_container_types)

        self.assertTrue(isinstance(template_token_types["generic"]["description"], str))
        self.assertTrue(isinstance(template_token_types["generic"]["token_types"], list))
