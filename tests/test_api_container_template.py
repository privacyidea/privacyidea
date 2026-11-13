# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
import base64
import binascii
import copy
import json
import string
from unittest import mock

from flask import g, request

from privacyidea.lib.container import (create_container_template, get_template_obj,
                                       create_container_tokens_from_template, get_templates_by_query,
                                       get_all_containers)
from privacyidea.lib.container import (init_container, find_container_by_serial)
from privacyidea.lib.error import ResolverError, UserError
from privacyidea.lib.containers.smartphone import SmartphoneOptions
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policies.conditions import ConditionSection
from privacyidea.lib.policy import set_policy, SCOPE, delete_policy, PolicyClass, get_policies
from privacyidea.lib.privacyideaserver import add_privacyideaserver
from privacyidea.lib.serviceid import delete_serviceid, set_serviceid
from privacyidea.lib.token import (get_tokens, get_tokens_from_serial_or_user,
                                   get_tokeninfo)
from privacyidea.lib.token import init_token, get_one_token
from privacyidea.lib.tokenrolloutstate import RolloutState
from privacyidea.lib.tokens.applicationspecificpasswordtoken import ApplicationSpecificPasswordTokenClass
from privacyidea.lib.tokens.papertoken import PAPERACTION
from privacyidea.lib.tokens.pushtoken import PushAction
from privacyidea.lib.tokens.tantoken import TANAction
from privacyidea.lib.user import User
from privacyidea.lib.utils.compare import PrimaryComparators
from .api_container_common import (
    APIContainerTest,
)


class APIContainerTemplate(APIContainerTest):

    def test_01_create_delete_template_success(self):
        template_name = "test"
        # Create template without tokens
        data = json.dumps({"template_options": {"tokens": []}, "default": True})
        result = self.request_assert_success(f'/container/smartphone/template/{template_name}',
                                             data, self.at, 'POST')
        self.assert_audit_entry('POST /container/<string:container_type>/template/<string:template_name>', success=1,
                                action_detail=self.contains(f"template_name={template_name}"))
        self.assertGreater(result["result"]["value"]["template_id"], 0)

        # Delete template
        result = self.request_assert_success(f'/container/template/{template_name}',
                                             {}, self.at, 'DELETE')
        self.assert_audit_entry('DELETE /container/template/<string:template_name>', success=1)
        self.assertTrue(result["result"]["value"])

    def test_02_create_template_fail(self):
        # Create template without name
        self.request_assert_404_no_result('/container/smartphone/template',
                                          {}, self.at, 'POST')
        self.assert_audit_log_empty()

    def test_03_delete_template_fail(self):
        # Delete non existing template
        template_name = "random"
        self.request_assert_405(f'container/template/{template_name}',
                                {}, None, 'POST')
        self.assert_audit_log_empty()

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
        self.assert_audit_entry('POST /container/<string:container_type>/template/<string:template_name>', success=1)
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
        self.assert_audit_entry('POST /container/<string:container_type>/template/<string:template_name>', success=0,
                                info=self.contains('ERR905'))

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
        self.assert_audit_entry('POST /container/init', success=1,
                                container_serial=result["result"]["value"]["container_serial"])
        check_result(result)

        # create container by passing only the template name
        result = self.request_assert_success('/container/init',
                                             {"type": "smartphone", "template_name": template_params["name"]},
                                             self.at, 'POST')
        self.assert_audit_entry('POST /container/init', success=1,
                                container_serial=result["result"]["value"]["container_serial"])
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
        self.assert_audit_entry('POST /container/init', success=1)
        check_result(result)

        # with template from db
        request_params = json.dumps({"type": "smartphone", "template": template_params})
        result = self.request_assert_success("/container/init",
                                             {"type": "smartphone", "template_name": template_params["name"]},
                                             self.at, "POST")
        self.assert_audit_entry('POST /container/init', success=1)
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
        self.assert_audit_entry('POST /container/init', success=1)
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
        self.assert_audit_entry('POST /container/init', success=1)
        check_result(result)

        # Create a container from the db template
        result = self.request_assert_success("/container/init",
                                             {"type": "smartphone", "template_name": template_params["name"]}, self.at,
                                             "POST")
        self.assert_audit_entry('POST /container/init', success=1)
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
        service_id = "test"
        set_serviceid(service_id, "This is an awesome test service id")

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
        self.assert_audit_entry('POST /container/init', success=1)
        check_result(result)

        # Create a container from the template name
        result = self.request_assert_success("/container/init",
                                             {"type": "generic", "template_name": template_params["name"],
                                              "user": "cornelius", "realm": self.realm3}, self.at, "POST")
        self.assert_audit_entry('POST /container/init', success=1)
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
        service_id = "test"
        set_serviceid(service_id, "This is an awesome test service id")

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
        self.assert_audit_entry('POST /container/init', success=1)
        check_result(result)

        # Create container from the db template
        result = self.request_assert_success("/container/init",
                                             {"type": "generic", "template_name": template_params["name"]}, self.at,
                                             "POST")
        self.assert_audit_entry('POST /container/init', success=1)
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
        self.assert_audit_entry('POST /container/init', success=1)
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
        self.assert_audit_entry('POST /container/init', success=1)
        container_serial = result["result"]["value"]["container_serial"]
        container1 = find_container_by_serial(container_serial)
        tokens = container1.get_tokens()
        self.assertEqual(1, len(tokens))
        self.assertEqual("hotp", tokens[0].get_type())

        # Can not create any type of token: hans already has 6 tokens
        result = self.request_assert_success('/container/init',
                                             request_params,
                                             self.at, 'POST')
        self.assert_audit_entry('POST /container/init', success=1)
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
        self.assert_audit_entry('POST /container/init', success=1)
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
        self.assert_audit_entry('POST /container/init', success=1)
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
        self.assert_audit_entry('POST /container/init', success=1)
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
        self.assert_audit_entry('POST /container/init', success=1)
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
        self.assert_audit_entry('POST /container/init', success=1)
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
        self.assert_audit_entry('POST /container/init', success=1)
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
        self.assert_audit_entry('POST /container/init', success=1)

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
        self.assert_audit_entry('GET /container/templates', success=1)
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
        self.assert_audit_entry('POST /container/init', success=1)
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
        self.assert_audit_entry('GET /container/template/<string:template_name>/compare', success=1)
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
        self.assert_audit_entry('GET /container/template/<string:template_name>/compare', success=1)
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
        self.assert_audit_entry('GET /container/template/tokentypes', success=1)
        self.assertEqual(3, len(result["result"]["value"]))
        template_token_types = result["result"]["value"]
        template_container_types = template_token_types.keys()

        self.assertIn("generic", template_container_types)
        self.assertIn("smartphone", template_container_types)
        self.assertIn("yubikey", template_container_types)

        self.assertTrue(isinstance(template_token_types["generic"]["description"], str))
        self.assertTrue(isinstance(template_token_types["generic"]["token_types"], list))

    def test_18_create_container_with_template_change_pin_container_condition(self):
        set_policy("admin", scope=SCOPE.ADMIN, action={PolicyAction.CONTAINER_CREATE: True, "enrollHOTP": True})
        set_policy("change_pin", SCOPE.ENROLL, action={PolicyAction.CHANGE_PIN_FIRST_USE: True},
                   conditions=[(ConditionSection.CONTAINER, "type", PrimaryComparators.EQUALS, "smartphone", True)])

        def create_container(container_type):
            template_params = {"name": "test",
                               "container_type": container_type,
                               "template_options": {"tokens": [{"type": "hotp", "genkey": True, "user": True}]}}
            request_params = json.dumps({"type": container_type, "user": "hans", "realm": self.realm1,
                                         "template": template_params})
            result = self.request_assert_success('/container/init', request_params, self.at, 'POST')
            container = find_container_by_serial(result["result"]["value"]["container_serial"])
            tokens = container.get_tokens()
            self.assertEqual(1, len(tokens))
            return container, tokens[0]

        # Policy applies to tokens in a smartphone
        smartphone, smartphone_token = create_container("smartphone")
        self.assertIsNotNone(get_tokeninfo(smartphone_token.get_serial(), "next_pin_change"))

        # Policy does not apply to tokens in other container types
        generic, generic_token = create_container("generic")
        self.assertIsNone(get_tokeninfo(generic_token.get_serial(), "next_pin_change"))

        delete_policy("change_pin")
        delete_policy("admin")
        smartphone.delete()
        generic.delete()
        smartphone_token.delete_token()
        generic_token.delete_token()

    def test_19_create_container_with_template_request_data_condition(self):
        set_policy("change_pin", SCOPE.ENROLL, action={PolicyAction.CHANGE_PIN_FIRST_USE: True},
                   conditions=[(ConditionSection.REQUEST_DATA, "type", PrimaryComparators.EQUALS, "hotp", True)])
        template_params = {"name": "test",
                           "container_type": "generic",
                           "template_options": {"tokens": [{"type": "hotp", "genkey": True},
                                                           {"type": "totp", "genkey": True}]}}
        request_params = json.dumps({"type": "generic", "user": "hans", "realm": self.realm1,
                                     "template": template_params})

        result = self.request_assert_success('/container/init', request_params, self.at, 'POST')

        container = find_container_by_serial(result["result"]["value"]["container_serial"])
        tokens = {token.get_tokentype(): token for token in container.get_tokens()}
        self.assertSetEqual({"hotp", "totp"}, set(tokens))
        # The condition is evaluated against the parameters of each template token
        self.assertIsNotNone(get_tokeninfo(tokens["hotp"].get_serial(), "next_pin_change"))
        self.assertIsNone(get_tokeninfo(tokens["totp"].get_serial(), "next_pin_change"))

        delete_policy("change_pin")
        container.delete()
        [token.delete_token() for token in tokens.values()]

    def test_20_create_container_with_template_policies_match_token_owner(self):
        self.setUp_user_realms()
        set_policy("enrollment", scope=SCOPE.ENROLL, action={PolicyAction.VERIFY_ENROLLMENT: "hotp"},
                   realm=self.realm1)
        template_params = {"name": "test",
                           "container_type": "generic",
                           "template_options": {"tokens": [{"type": "hotp", "genkey": True, "user": True},
                                                           {"type": "hotp", "genkey": True}]}}
        request_params = json.dumps({"type": "generic", "user": "hans", "realm": self.realm1,
                                     "template": template_params})

        result = self.request_assert_success('/container/init', request_params, self.at, 'POST')

        container = find_container_by_serial(result["result"]["value"]["container_serial"])
        tokens = container.get_tokens()
        self.assertEqual(2, len(tokens))
        owned_token = next(token for token in tokens if token.user)
        unowned_token = next(token for token in tokens if not token.user)
        # The policies are matched against the token owner and not against the container owner
        self.assertEqual(RolloutState.VERIFY_PENDING, owned_token.rollout_state)
        self.assertNotEqual(RolloutState.VERIFY_PENDING, unowned_token.rollout_state)

        delete_policy("enrollment")
        container.delete()
        [token.delete_token() for token in tokens]

    def test_21_create_container_with_template_policies_match_container_realm(self):
        self.setUp_user_realms()
        set_policy("enrollment", scope=SCOPE.ENROLL, action={PolicyAction.VERIFY_ENROLLMENT: "hotp"},
                   realm=self.realm1)
        template_params = {"name": "test",
                           "container_type": "generic",
                           "template_options": {"tokens": [{"type": "hotp", "genkey": True, "user": True}]}}
        request_params = json.dumps({"type": "generic", "realm": self.realm1, "template": template_params})

        result = self.request_assert_success('/container/init', request_params, self.at, 'POST')

        container = find_container_by_serial(result["result"]["value"]["container_serial"])
        tokens = container.get_tokens()
        self.assertEqual(1, len(tokens))
        token = tokens[0]
        # The container has no owner: the token only gets the container realm and the policies are matched against it
        self.assertIsNone(token.user)
        self.assertListEqual([self.realm1], token.get_realms())
        self.assertEqual(RolloutState.VERIFY_PENDING, token.rollout_state)

        delete_policy("enrollment")
        container.delete()
        token.delete_token()

    def test_22_create_container_tokens_from_template_restores_request_on_error(self):
        self.setUp_user_realms()
        hans = User("hans", self.realm1)
        container_serial = init_container({"type": "generic", "user": "hans", "realm": self.realm1})["container_serial"]
        request_data = {"type": "generic", "user": "hans", "realm": self.realm1}

        with self.app.test_request_context("/container/init", method="POST"):
            request.all_data = copy.deepcopy(request_data)
            request.User = hans
            g.request_data = copy.deepcopy(request_data)
            g.policies = {"container_policy": "value"}
            g.logged_in_user = {"role": "admin", "username": "admin", "realm": ""}
            with mock.patch("privacyidea.lib.container.User", side_effect=UserError("unavailable")):
                with self.assertRaises(UserError):
                    create_container_tokens_from_template(container_serial, [{"type": "hotp", "genkey": True,
                                                                              "user": True}], request, "admin")

            self.assertDictEqual(request_data, request.all_data)
            self.assertDictEqual(request_data, g.request_data)
            self.assertEqual(hans, request.User)
            self.assertDictEqual({"container_policy": "value"}, g.policies)

        find_container_by_serial(container_serial).delete()

    def test_23_create_container_with_template_user_store_not_available(self):
        self.setUp_user_realms()
        hans = User("hans", self.realm1)
        template_params = {"name": "test",
                           "container_type": "generic",
                           "template_options": {"tokens": [{"type": "hotp", "genkey": True, "user": True},
                                                           {"type": "totp", "genkey": True, "user": True}]}}
        request_params = json.dumps({"type": "generic", "user": "hans", "realm": self.realm1,
                                     "template": template_params})
        user_store_lookup = User._get_user_from_userstore

        def lookup_user(user_object: User) -> None:
            # The user store fails while the first template token is enrolled
            if getattr(request, "all_data", {}).get("type") == "hotp":
                raise ResolverError("The user store is not available")
            user_store_lookup(user_object)

        with mock.patch.object(User, "_get_user_from_userstore", autospec=True, side_effect=lookup_user):
            result = self.request_assert_success('/container/init', request_params, self.at, 'POST')

        # The error is only logged for the first token and the remaining token is created for the container owner
        self.assertEqual(1, len(result["result"]["value"]["tokens"]))
        container = find_container_by_serial(result["result"]["value"]["container_serial"])
        tokens = container.get_tokens()
        self.assertEqual(1, len(tokens))
        self.assertEqual("totp", tokens[0].get_tokentype())
        self.assertEqual(hans, tokens[0].user)

        container.delete()
        [token.delete_token() for token in tokens]

    def test_24_create_container_tokens_from_template_for_user_without_container_owner(self):
        self.setUp_user_realms()
        hans = User("hans", self.realm1)
        container_serial = init_container({"type": "generic", "realm": self.realm1})["container_serial"]
        template_tokens = [{"type": "hotp", "genkey": True, "user": True}, {"type": "totp", "genkey": True}]
        self._create_container_tokens_from_template_as_user(container_serial, template_tokens, hans)

        # All tokens of a user are assigned to the user, also if the container has no owner and independent of the
        # user flag
        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertSetEqual({"hotp", "totp"}, {token.get_tokentype() for token in tokens})
        for token in tokens:
            self.assertEqual(hans, token.user)

        container.delete()
        [token.delete_token() for token in tokens]

    def test_25_create_container_with_template_change_pin_on_first_use(self):
        template_params = {"name": "test",
                           "container_type": "generic",
                           "template_options": {"tokens": [{"type": "hotp", "genkey": True,
                                                            "change_pin_on_first_use": True},
                                                           {"type": "totp", "genkey": True}]}}
        request_params = json.dumps({"type": "generic", "user": "hans", "realm": self.realm1,
                                     "template": template_params})

        result = self.request_assert_success('/container/init', request_params, self.at, 'POST')

        container = find_container_by_serial(result["result"]["value"]["container_serial"])
        tokens = {token.get_tokentype(): token for token in container.get_tokens()}
        self.assertSetEqual({"hotp", "totp"}, set(tokens))
        # Without the policy change_pin_on_first_use, only the token with the option gets the PIN change
        self.assertTrue(tokens["hotp"].is_pin_change())
        self.assertIsNone(get_tokeninfo(tokens["totp"].get_serial(), "next_pin_change"))
        for serial, token_result in result["result"]["value"]["tokens"].items():
            self.assertNotIn("change_pin_on_first_use", token_result["init_params"])
            self.assertIsNone(get_tokeninfo(serial, "change_pin_on_first_use"))

        container.delete()
        [token.delete_token() for token in tokens.values()]

    def test_26_create_container_tokens_from_template_change_pin_on_first_use_for_user(self):
        self.setUp_user_realms()
        hans = User("hans", self.realm1)
        set_policy("user", scope=SCOPE.USER,
                   action={PolicyAction.ENROLLPIN: True, "enrollHOTP": True, "enrollTOTP": True})
        set_policy("change_pin", SCOPE.ENROLL, action={PolicyAction.CHANGE_PIN_EVERY: "30d"})
        container_serial = init_container({"type": "generic", "user": "hans", "realm": self.realm1})["container_serial"]
        template_tokens = [{"type": "hotp", "genkey": True, "pin": "1234", "change_pin_on_first_use": True},
                           {"type": "totp", "genkey": True, "pin": "1234"}]

        self._create_container_tokens_from_template_as_user(container_serial, template_tokens, hans)

        container = find_container_by_serial(container_serial)
        tokens = {token.get_tokentype(): token for token in container.get_tokens()}
        self.assertSetEqual({"hotp", "totp"}, set(tokens))
        # The flag wins over the PIN the user sets and over change_pin_every
        self.assertTrue(tokens["hotp"].is_pin_change())
        self.assertIsNotNone(get_tokeninfo(tokens["totp"].get_serial(), "next_pin_change"))
        self.assertFalse(tokens["totp"].is_pin_change())

        delete_policy("change_pin")
        delete_policy("user")
        container.delete()
        [token.delete_token() for token in tokens.values()]

    def test_27_save_template_change_pin_on_first_use_must_be_boolean(self):
        url = "/container/generic/template/test"
        audit_action = "POST /container/<string:container_type>/template/<string:template_name>"
        invalid_options = {"tokens": [{"type": "hotp", "change_pin_on_first_use": "true"}]}

        # Create
        self.request_assert_error(400, url, json.dumps({"template_options": invalid_options}), self.at, "POST",
                                  error_code=905)
        self.assert_audit_entry(audit_action, success=0, info=self.contains("ERR905"))
        self.assertListEqual([], get_templates_by_query(name="test")["templates"])

        # Update
        valid_options = {"tokens": [{"type": "hotp", "change_pin_on_first_use": True}, {"type": "totp"}]}
        self.request_assert_success(url, json.dumps({"template_options": valid_options}), self.at, "POST")
        self.request_assert_error(400, url, json.dumps({"template_options": invalid_options}), self.at, "POST",
                                  error_code=905)
        self.assertDictEqual(valid_options, get_template_obj("test").get_template_options_as_dict())

        get_template_obj("test").delete()

    def test_28_create_container_with_template_name_policy_change_pin_on_first_use(self):
        set_policy("change_pin", SCOPE.ENROLL, action={PolicyAction.CHANGE_PIN_FIRST_USE: True})
        create_container_template(container_type="generic", template_name="test",
                                  options={"tokens": [{"type": "hotp", "genkey": True},
                                                      {"type": "totp", "genkey": True,
                                                       "change_pin_on_first_use": False}]})
        request_params = json.dumps({"type": "generic", "user": "hans", "realm": self.realm1, "template_name": "test"})

        result = self.request_assert_success("/container/init", request_params, self.at, "POST")

        container = find_container_by_serial(result["result"]["value"]["container_serial"])
        tokens = {token.get_tokentype(): token for token in container.get_tokens()}
        self.assertSetEqual({"hotp", "totp"}, set(tokens))
        self.assertEqual("test", container.template.name)
        # The policy sets the PIN change for an admin, also if the option of the template token is missing or false
        self.assertTrue(tokens["hotp"].is_pin_change())
        self.assertTrue(tokens["totp"].is_pin_change())

        delete_policy("change_pin")
        container.delete()
        [token.delete_token() for token in tokens.values()]
        get_template_obj("test").delete()

    def test_29_create_container_with_template_change_pin_on_first_use_must_be_boolean(self):
        template_params = {"name": "test",
                           "container_type": "generic",
                           "template_options": {"tokens": [{"type": "hotp", "genkey": True,
                                                            "change_pin_on_first_use": "false"}]}}
        request_params = json.dumps({"type": "generic", "template": template_params})
        containers_before = len(get_all_containers(ctype="generic")["containers"])

        self.request_assert_error(400, "/container/init", request_params, self.at, "POST", error_code=905)

        self.assertEqual(containers_before, len(get_all_containers(ctype="generic")["containers"]))

    def test_30_create_container_with_unused_or_empty_template(self):
        templates = {
            # A template of another container type is not used, so its tokens are not checked
            "other container type": {"name": "test", "container_type": "smartphone",
                                     "template_options": {"tokens": [{"type": "hotp",
                                                                      "change_pin_on_first_use": "yes"}]}},
            "no template options": {"name": "test", "container_type": "smartphone", "template_options": None},
            "no tokens": {"name": "test", "container_type": "generic", "template_options": {"tokens": None}},
        }
        for description, template_params in templates.items():
            with self.subTest(description):
                request_params = json.dumps({"type": "generic", "template": template_params})

                result = self.request_assert_success("/container/init", request_params, self.at, "POST")

                self.assertNotIn("tokens", result["result"]["value"])
                container = find_container_by_serial(result["result"]["value"]["container_serial"])
                self.assertListEqual([], container.get_tokens())
                container.delete()

    def test_31_create_container_tokens_from_template_change_pin_on_first_use_not_true(self):
        self.setUp_user_realms()
        hans = User("hans", self.realm1)
        container_serial = init_container({"type": "generic", "user": "hans", "realm": self.realm1})["container_serial"]
        # A stored template is not validated again when it is used
        template_tokens = [{"type": "hotp", "genkey": True, "change_pin_on_first_use": "false"}]

        self._create_container_tokens_from_template_as_user(container_serial, template_tokens, hans)

        container = find_container_by_serial(container_serial)
        tokens = container.get_tokens()
        self.assertEqual(1, len(tokens))
        # Only the boolean True sets the PIN change
        self.assertIsNone(get_tokeninfo(tokens[0].get_serial(), "next_pin_change"))

        container.delete()
        tokens[0].delete_token()

    def _create_container_tokens_from_template_as_user(self, container_serial: str, template_tokens: list[dict],
                                                       user: User) -> dict[str, dict]:
        request_data = {"user": user.login, "realm": user.realm}
        with self.app.test_request_context("/container/init", method="POST"):
            request.all_data = copy.deepcopy(request_data)
            request.User = user
            g.request_data = copy.deepcopy(request_data)
            g.policies = {}
            g.client_ip = "127.0.0.1"
            g.serial = None
            g.audit_object = self.audit_object
            g.policy_object = PolicyClass()
            g.logged_in_user = {"role": "user", "username": user.login, "realm": user.realm,
                                "resolver": user.resolver}
            return create_container_tokens_from_template(container_serial, template_tokens, request, "user")

    def test_32_create_container_with_template_applspec_password_follows_policies(self):
        # The token parameters of a template can not define the generated password of an application specific
        # password token: the length and contents are taken from the policies or the defaults of the token class.
        set_serviceid("mail", "the service of the token below")
        template_params = {"name": "applspec",
                           "container_type": "generic",
                           "template_options": {"tokens": [{"type": "applspec", "genkey": True,
                                                            "service_id": "mail",
                                                            "applspec.length": 4,
                                                            "applspec.contents": "[0]"}]}}
        containers = []

        def get_password():
            request_params = json.dumps({"type": "generic", "template": template_params})
            result = self.request_assert_success("/container/init", request_params, self.at, "POST")
            container = find_container_by_serial(result["result"]["value"]["container_serial"])
            containers.append(container)
            tokens = container.get_tokens()
            self.assertEqual(1, len(tokens))
            return result["result"]["value"]["tokens"][tokens[0].get_serial()]["password"]

        try:
            # Without a policy the default length is used
            password = get_password()
            self.assertEqual(ApplicationSpecificPasswordTokenClass.default_length, len(password), password)
            self.assertTrue(set(password) - {"0"}, password)

            set_policy("applspec_password", scope=SCOPE.ENROLL, action="applspec.length=16, applspec.contents=-s")
            password = get_password()
            self.assertEqual(16, len(password), password)
            self.assertTrue(set(password) <= set(string.ascii_letters + string.digits), password)
        finally:
            for container in containers:
                for token in container.get_tokens():
                    token.delete_token()
                container.delete()
            if get_policies(name="applspec_password"):
                delete_policy("applspec_password")
            delete_serviceid("mail")

    def _init_generic_container_with_template(self, tokens: list) -> dict:
        template_params = {"name": "tmpl_postpolicies",
                           "container_type": "generic",
                           "template_options": {"tokens": tokens}}
        request_params = json.dumps({"type": "generic", "user": "hans", "realm": self.realm1,
                                     "template": template_params})
        return self.request_assert_success('/container/init', request_params, self.at, 'POST')

    @staticmethod
    def _cleanup_container_and_tokens(container_serial: str | None, serials: list[str]):
        if container_serial:
            find_container_by_serial(container_serial).delete()
        for serial in serials:
            for token in get_tokens(serial=serial):
                token.delete_token()

    def test_33_create_container_with_template_reports_token_failing_postpolicies(self):
        self.setUp_user_realms()
        hotp_serial = "TMPLREPORT26A"
        totp_serial = "TMPLREPORT26B"
        hotp_key = "9f8e7d6c5b4a39281706f5e4d3c2b1a098765432"
        hotp_key_base32 = base64.b32encode(binascii.unhexlify(hotp_key)).decode().strip("=")
        # The hotp token has no description, so the condition raises an error for it
        set_policy("verify_hotp_report", scope=SCOPE.ENROLL, action={PolicyAction.VERIFY_ENROLLMENT: "hotp"},
                   conditions=[(ConditionSection.REQUEST_DATA, "description", PrimaryComparators.EQUALS, "x", True,
                                "raise_error")])
        container_serial = None

        try:
            result = self._init_generic_container_with_template([
                {"type": "hotp", "otpkey": hotp_key, "serial": hotp_serial},
                {"type": "totp", "genkey": True, "serial": totp_serial, "description": "kept"}])
            value = result["result"]["value"]
            container_serial = value["container_serial"]

            # Only the created token is in the tokens of the response
            self.assertEqual([totp_serial], list(value["tokens"].keys()))
            # The token that was not created is reported with its type, serial and the error
            not_created = value["tokens_not_created"]
            self.assertEqual(1, len(not_created), not_created)
            self.assertEqual("hotp", not_created[0]["type"])
            self.assertEqual(hotp_serial, not_created[0]["serial"])
            self.assertIsInstance(not_created[0]["error"], str)
            self.assertTrue(not_created[0]["error"])
            self.assertNotIn("googleurl", not_created[0])
            self.assertNotIn("otpkey", not_created[0])
            # No enrollment data of the token that was not created is anywhere in the response
            response_text = json.dumps(result)
            self.assertNotIn(hotp_key, response_text.lower())
            self.assertNotIn(hotp_key_base32, response_text)
            self.assertNotIn("otpauth://hotp", response_text)
            self.assertEqual(0, len(get_tokens(serial=hotp_serial)))
            # The container contains only the token that was created
            container = find_container_by_serial(container_serial)
            self.assertEqual([totp_serial], [token.get_serial() for token in container.get_tokens()])
        finally:
            delete_policy("verify_hotp_report")
            self._cleanup_container_and_tokens(container_serial, [hotp_serial, totp_serial])

    def test_34_create_container_with_template_reports_token_failing_prepolicies_or_init(self):
        self.setUp_user_realms()
        hotp_serial = "TMPLREPORT27A"
        tiqr_serial = "TMPLREPORT27B"
        totp_serial = "TMPLREPORT27C"
        # The pre-policy fails for the hotp token without a description, the tiqr token fails in init_token as it
        # requires a user
        set_policy("require_desc_hotp", scope=SCOPE.ENROLL, action=f"{PolicyAction.REQUIRE_DESCRIPTION}=hotp")
        container_serial = None

        try:
            result = self._init_generic_container_with_template([
                {"type": "hotp", "genkey": True, "serial": hotp_serial},
                {"type": "tiqr", "serial": tiqr_serial},
                {"type": "totp", "genkey": True, "serial": totp_serial}])
            value = result["result"]["value"]
            container_serial = value["container_serial"]

            self.assertEqual([totp_serial], list(value["tokens"].keys()))
            not_created = value["tokens_not_created"]
            self.assertEqual(["hotp", "tiqr"], sorted(entry["type"] for entry in not_created), not_created)
            for entry in not_created:
                self.assertIsInstance(entry["error"], str)
                self.assertTrue(entry["error"], entry)
        finally:
            delete_policy("require_desc_hotp")
            self._cleanup_container_and_tokens(container_serial, [hotp_serial, tiqr_serial, totp_serial])

    def test_35_create_container_with_template_without_errors_omits_tokens_not_created(self):
        self.setUp_user_realms()
        hotp_serial = "TMPLREPORT28A"
        totp_serial = "TMPLREPORT28B"
        set_policy("verify_hotp_ok", scope=SCOPE.ENROLL, action={PolicyAction.VERIFY_ENROLLMENT: "hotp"})
        set_policy("pin_first_use_ok", scope=SCOPE.ENROLL, action=PolicyAction.CHANGE_PIN_FIRST_USE)
        container_serial = None

        try:
            result = self._init_generic_container_with_template([
                {"type": "hotp", "genkey": True, "serial": hotp_serial},
                {"type": "totp", "genkey": True, "serial": totp_serial}])
            value = result["result"]["value"]
            container_serial = value["container_serial"]

            # The response is unchanged if all tokens are created
            self.assertNotIn("tokens_not_created", value)
            self.assertSetEqual({hotp_serial, totp_serial}, set(value["tokens"].keys()))
            self.assertIsInstance(value["tokens"][hotp_serial]["verify"], dict)
            self.assertEqual(RolloutState.VERIFY_PENDING, value["tokens"][hotp_serial]["rollout_state"])
            self.assertNotIn("verify", value["tokens"][totp_serial])
            self.assertIsNotNone(get_tokeninfo(hotp_serial, "next_pin_change"))
            self.assertIsNotNone(get_tokeninfo(totp_serial, "next_pin_change"))
        finally:
            delete_policy("verify_hotp_ok")
            delete_policy("pin_first_use_ok")
            self._cleanup_container_and_tokens(container_serial, [hotp_serial, totp_serial])

    def test_36_create_container_with_template_removes_token_failing_pin_change_policy(self):
        self.setUp_user_realms()
        hotp_serial = "TMPLREPORT29A"
        totp_serial = "TMPLREPORT29B"
        # verify_enrollment succeeds, only change_pin_on_first_use fails for the hotp token without a description
        set_policy("verify_hotp_plain", scope=SCOPE.ENROLL, action={PolicyAction.VERIFY_ENROLLMENT: "hotp"})
        set_policy("pin_first_use_failing", scope=SCOPE.ENROLL, action=PolicyAction.CHANGE_PIN_FIRST_USE,
                   conditions=[(ConditionSection.REQUEST_DATA, "description", PrimaryComparators.EQUALS, "y", True,
                                "raise_error")])
        container_serial = None

        try:
            result = self._init_generic_container_with_template([
                {"type": "hotp", "genkey": True, "serial": hotp_serial},
                {"type": "totp", "genkey": True, "serial": totp_serial, "description": "kept"}])
            value = result["result"]["value"]
            container_serial = value["container_serial"]
            container = find_container_by_serial(container_serial)

            # The token is neither in the database, nor in the container, nor in the tokens of the response
            self.assertEqual(0, len(get_tokens(serial=hotp_serial)))
            self.assertEqual([totp_serial], [token.get_serial() for token in container.get_tokens()])
            self.assertEqual([totp_serial], list(value["tokens"].keys()))
            self.assertEqual([hotp_serial], [entry.get("serial") for entry in value["tokens_not_created"]])
        finally:
            delete_policy("verify_hotp_plain")
            delete_policy("pin_first_use_failing")
            self._cleanup_container_and_tokens(container_serial, [hotp_serial, totp_serial])

    def test_37_create_container_with_template_existing_serial_is_disabled_on_postpolicy_error(self):
        self.setUp_user_realms()
        existing_serial = "TMPLEXIST30A"
        totp_serial = "TMPLEXIST30B"
        init_token({"type": "hotp", "genkey": True, "serial": existing_serial})
        set_policy("verify_hotp_exist", scope=SCOPE.ENROLL, action={PolicyAction.VERIFY_ENROLLMENT: "hotp"},
                   conditions=[(ConditionSection.REQUEST_DATA, "description", PrimaryComparators.EQUALS, "x", True,
                                "raise_error")])
        container_serial = None

        try:
            result = self._init_generic_container_with_template([
                {"type": "hotp", "genkey": True, "serial": existing_serial},
                {"type": "totp", "genkey": True, "serial": totp_serial, "description": "kept"}])
            value = result["result"]["value"]
            container_serial = value["container_serial"]
            container = find_container_by_serial(container_serial)

            # The token existed before and must not be deleted, but it was rolled over (new key nobody has),
            # so it is disabled and not part of the new container
            self.assertEqual(1, len(get_tokens(serial=existing_serial)))
            self.assertFalse(get_one_token(serial=existing_serial).token.active)
            self.assertEqual([totp_serial], [token.get_serial() for token in container.get_tokens()])
            self.assertEqual([existing_serial], [entry.get("serial") for entry in value["tokens_not_created"]])
        finally:
            delete_policy("verify_hotp_exist")
            self._cleanup_container_and_tokens(container_serial, [existing_serial, totp_serial])

    def test_38_create_container_with_template_hides_internal_error_details(self):
        self.setUp_user_realms()
        hotp_serial = "TMPLINTERNAL31"
        container_serial = None

        try:
            with mock.patch("privacyidea.lib.container.init_token", side_effect=RuntimeError("internal detail xyz")):
                result = self._init_generic_container_with_template([
                    {"type": "hotp", "genkey": True, "serial": hotp_serial}])
            value = result["result"]["value"]
            container_serial = value["container_serial"]

            not_created = value["tokens_not_created"]
            self.assertEqual(1, len(not_created), not_created)
            self.assertIsInstance(not_created[0]["error"], str)
            self.assertTrue(not_created[0]["error"])
            self.assertNotIn("internal detail xyz", not_created[0]["error"])
            self.assertNotIn("internal detail xyz", json.dumps(result))
        finally:
            self._cleanup_container_and_tokens(container_serial, [hotp_serial])
