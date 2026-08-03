# SPDX-FileCopyrightText: 2024 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later

from privacyidea.lib.container import (create_container_template, delete_container_by_serial,
                                       set_container_states, unregister)
from privacyidea.lib.container import (init_container, find_container_by_serial, remove_token_from_container)
from privacyidea.lib.containers.container_info import TokenContainerInfoData, RegistrationState
from privacyidea.lib.containers.container_states import ContainerStates
from privacyidea.lib.policies.actions import PolicyAction
from privacyidea.lib.policies.conditions import ConditionSection, ConditionHandleMissingData
from privacyidea.lib.policy import set_policy, SCOPE, delete_policy
from privacyidea.lib.token import init_token, unassign_token
from privacyidea.lib.user import User
from privacyidea.lib.utils.compare import PrimaryComparators
from tests.test_lib_tokencontainer import MockSmartphone

from .api_container_common import (
    APIContainerAuthorization,
)


class ContainerPolicyConditions(APIContainerAuthorization):
    """
    This class tests that the endpoints work as expected for extended policy conditions.
    It does not cover all possible combinations, but some useful scenarios.
    """

    def test_01_create(self):
        # condition on container fails as the container does not yet exist
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_CREATE,
                   conditions=[(ConditionSection.CONTAINER, "type", PrimaryComparators.EQUALS, "generic", True)])
        self.request_assert_error(403, '/container/init', {"type": "generic"}, self.at, 'POST')
        self.assert_audit_entry('POST /container/init', success=0, info=self.NOT_EMPTY)
        delete_policy("policy")

    def test_02_delete(self):
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_DELETE,
                   conditions=[(ConditionSection.CONTAINER, "type", PrimaryComparators.IN, "generic,smartphone", True)])

        # Delete smartphone is allowed
        container_serial = init_container({"type": "smartphone"})["container_serial"]
        self.request_assert_success(f"/container/{container_serial}", {}, self.at, "DELETE")
        self.assert_audit_entry('DELETE /container/<string:container_serial>', success=1,
                                container_serial=container_serial)

        # Delete yubikey fails
        container_serial = init_container({"type": "yubikey"})["container_serial"]
        self.request_assert_error(403, f"/container/{container_serial}", {}, self.at, "DELETE")
        self.assert_audit_entry('DELETE /container/<string:container_serial>', success=0,
                                container_serial=container_serial, info=self.NOT_EMPTY)
        delete_policy("policy")
        delete_container_by_serial(container_serial)

    def test_03_assign_unassign(self):
        self.setUp_user_realms()
        # Only allowed to assign users with a phone number to smartphone containers and all users to other containers
        set_policy("assign", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ASSIGN_USER,
                   conditions=[(ConditionSection.CONTAINER, "type", PrimaryComparators.NOT_EQUALS, "smartphone", True)])
        set_policy("assign_smph", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ASSIGN_USER,
                   conditions=[(ConditionSection.USERINFO, "phone", PrimaryComparators.MATCHES, ".+", True,
                                ConditionHandleMissingData.IS_FALSE.value),
                               (ConditionSection.CONTAINER, "type", PrimaryComparators.EQUALS, "smartphone", True)])
        # Unassignment only allowed for not registered containers
        set_policy("unassign", scope=SCOPE.ADMIN,
                   action=PolicyAction.CONTAINER_UNASSIGN_USER,
                   conditions=[(ConditionSection.CONTAINER_INFO, "registration_state", PrimaryComparators.NOT_EQUALS,
                                "registered", True, ConditionHandleMissingData.IS_TRUE.value)])

        generic_serial = init_container({"type": "generic"})["container_serial"]
        smph_serial = init_container({"type": "smartphone"})["container_serial"]
        smartphone = find_container_by_serial(smph_serial)

        # Assign user without phone to generic container is allowed
        self.request_assert_success(f"/container/{generic_serial}/assign",
                                    {"user": "selfservice", "realm": self.realm1}, self.at, "POST")
        self.assert_audit_entry('POST /container/<string:container_serial>/assign', success=1,
                                container_serial=generic_serial)

        # Assign user without phone to smartphone container fails
        self.request_assert_error(403, f"/container/{smph_serial}/assign",
                                  {"user": "selfservice", "realm": self.realm1}, self.at, "POST")
        self.assert_audit_entry('POST /container/<string:container_serial>/assign', success=0,
                                container_serial=smph_serial, info=self.NOT_EMPTY)
        # Assign user with phone to smartphone is allowed
        self.request_assert_success(f"/container/{smph_serial}/assign",
                                    {"user": "cornelius", "realm": self.realm1}, self.at, "POST")
        self.assert_audit_entry('POST /container/<string:container_serial>/assign', success=1,
                                container_serial=smph_serial)

        # Simulate registration
        smartphone.set_container_info(
            [TokenContainerInfoData("registration_state", RegistrationState.REGISTERED.value)])

        # Unassign user from (not registered) generic container is allowed
        self.request_assert_success(f"/container/{generic_serial}/unassign",
                                    {"user": "selfservice", "realm": self.realm1}, self.at, "POST")
        self.assert_audit_entry('POST /container/<string:container_serial>/unassign', success=1,
                                container_serial=generic_serial)

        # Unassign user from registered smartphone is not allowed
        self.request_assert_error(403, f"/container/{smph_serial}/unassign",
                                  {"user": "cornelius", "realm": self.realm1}, self.at, "POST")
        self.assert_audit_entry('POST /container/<string:container_serial>/unassign', success=0,
                                container_serial=smph_serial, info=self.NOT_EMPTY)

        delete_policy("assign")
        delete_policy("assign_smph")
        delete_policy("unassign")
        delete_container_by_serial(generic_serial)
        smartphone.delete()

    def test_04_list_containers(self):
        # extended policy conditions do not work for list containers as most often this involves multiple containers
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_LIST,
                   conditions=[(ConditionSection.CONTAINER, "type", PrimaryComparators.EQUALS, "generic", True)])
        container_serial = init_container({"type": "generic"})["container_serial"]
        self.request_assert_error(403, "/container/", {}, self.at, "GET")
        self.assert_audit_entry('GET /container/', success=0, info=self.NOT_EMPTY)
        self.request_assert_error(403, "/container/", {"type": "generic"}, self.at, "GET")
        self.assert_audit_entry('GET /container/', success=0, info=self.NOT_EMPTY)
        self.request_assert_error(403, "/container/", {"container_serial": container_serial}, self.at, "GET")
        self.assert_audit_entry('GET /container/', success=0, info=self.NOT_EMPTY)

        delete_policy("policy")
        delete_container_by_serial(container_serial)

    def test_05_add_token(self):
        # only tokens of a specific type and hashlib can be added to smartphones
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_ADD_TOKEN,
                   conditions=[(ConditionSection.CONTAINER, "type", PrimaryComparators.EQUALS, "smartphone", True),
                               (ConditionSection.TOKEN, "tokentype", PrimaryComparators.IN, "hotp,totp", True),
                               (ConditionSection.TOKENINFO, "hashlib", PrimaryComparators.EQUALS, "sha256", True,
                                ConditionHandleMissingData.IS_FALSE.value)])
        selfservice = User("selfservice", self.realm1)
        hotp_sha1 = init_token({"type": "hotp", "genkey": True, "hashlib": "sha1"}, selfservice)
        hotp_sha256 = init_token({"type": "hotp", "genkey": True, "hashlib": "sha256"}, selfservice)
        totp_sha1 = init_token({"type": "totp", "genkey": True, "hashlib": "sha1"}, selfservice)
        totp_sha256 = init_token({"type": "totp", "genkey": True, "hashlib": "sha256"}, selfservice)
        sms = init_token({"type": "sms", "phone": "12345689"}, selfservice)
        container_serial = init_container({"type": "smartphone", "user": "selfservice", "realm": self.realm1})[
            "container_serial"]

        # ---- Add single tokens ----
        # hotp and totp with sha256 are allowed
        self.request_assert_success(f"/container/{container_serial}/add", {"serial": hotp_sha256.get_serial()},
                                    self.at_user, "POST")
        self.assert_audit_entry('POST /container/<string:container_serial>/add', success=1)
        container = find_container_by_serial(container_serial)
        self.assertSetEqual({hotp_sha256.get_serial()}, {token.get_serial() for token in container.get_tokens()})
        self.request_assert_success(f"/container/{container_serial}/add", {"serial": totp_sha256.get_serial()},
                                    self.at_user, "POST")
        self.assert_audit_entry('POST /container/<string:container_serial>/add', success=1)
        container = find_container_by_serial(container_serial)
        self.assertSetEqual({hotp_sha256.get_serial(), totp_sha256.get_serial()},
                            {token.get_serial() for token in container.get_tokens()})
        # hotp and totp with sha1 are not allowed
        self.request_assert_error(403, f"/container/{container_serial}/add", {"serial": hotp_sha1.get_serial()},
                                  self.at_user, "POST")
        self.assert_audit_entry('POST /container/<string:container_serial>/add', success=0, info=self.NOT_EMPTY)
        container = find_container_by_serial(container_serial)
        self.assertSetEqual({hotp_sha256.get_serial(), totp_sha256.get_serial()},
                            {token.get_serial() for token in container.get_tokens()})
        self.request_assert_error(403, f"/container/{container_serial}/add", {"serial": totp_sha1.get_serial()},
                                  self.at_user, "POST")
        self.assert_audit_entry('POST /container/<string:container_serial>/add', success=0, info=self.NOT_EMPTY)
        container = find_container_by_serial(container_serial)
        self.assertSetEqual({hotp_sha256.get_serial(), totp_sha256.get_serial()},
                            {token.get_serial() for token in container.get_tokens()})
        # sms also not allowed
        self.request_assert_error(403, f"/container/{container_serial}/add", {"serial": sms.get_serial()},
                                  self.at_user, "POST")
        self.assert_audit_entry('POST /container/<string:container_serial>/add', success=0, info=self.NOT_EMPTY)
        container = find_container_by_serial(container_serial)
        self.assertSetEqual({hotp_sha256.get_serial(), totp_sha256.get_serial()},
                            {token.get_serial() for token in container.get_tokens()})

        # ---- Add all tokens ----
        remove_token_from_container(container_serial, hotp_sha256.get_serial())
        remove_token_from_container(container_serial, totp_sha256.get_serial())
        container = find_container_by_serial(container_serial)
        self.assertEqual(0, len(container.get_tokens()))

        result = self.request_assert_success(f"/container/{container_serial}/addall",
                                             {"serial": f"{hotp_sha256.get_serial()},{hotp_sha1.get_serial()},"
                                                        f"{sms.get_serial()},{totp_sha256.get_serial()},"
                                                        f"{totp_sha1.get_serial()}"},
                                             self.at_user, "POST")
        self.assert_audit_entry('POST /container/<string:container_serial>/addall', success=0, info=self.NOT_EMPTY)
        self.assertTrue(result["result"]["value"][hotp_sha256.get_serial()])
        self.assertTrue(result["result"]["value"][totp_sha256.get_serial()])
        self.assertFalse(result["result"]["value"][hotp_sha1.get_serial()])
        self.assertFalse(result["result"]["value"][totp_sha1.get_serial()])
        self.assertFalse(result["result"]["value"][sms.get_serial()])
        container = find_container_by_serial(container_serial)
        self.assertSetEqual({hotp_sha256.get_serial(), totp_sha256.get_serial()},
                            {token.get_serial() for token in container.get_tokens()})

        delete_policy("policy")

        # ---- user info condition ----
        # user condition is applied to the token and container owner
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ADD_TOKEN,
                   conditions=[(ConditionSection.USERINFO, "phone", PrimaryComparators.MATCHES, ".+", True)])

        cornelius = User("cornelius", self.realm1)
        container = find_container_by_serial(container_serial)
        container.remove_user(selfservice)
        container.add_user(cornelius)

        # Add token of a user without phone number to a container with phone number fails
        self.request_assert_error(403, f"/container/{container_serial}/add", {"serial": hotp_sha1.get_serial()},
                                  self.at, "POST")
        self.assert_audit_entry('POST /container/<string:container_serial>/add', success=0, info=self.NOT_EMPTY)
        container = find_container_by_serial(container_serial)
        self.assertSetEqual({hotp_sha256.get_serial(), totp_sha256.get_serial()},
                            {token.get_serial() for token in container.get_tokens()})

        # Both users (same user) have phone number works
        unassign_token(hotp_sha1.get_serial())
        hotp_sha1.add_user(cornelius)
        self.request_assert_success(f"/container/{container_serial}/add", {"serial": hotp_sha1.get_serial()},
                                    self.at, "POST")
        self.assert_audit_entry('POST /container/<string:container_serial>/add', success=1)
        container = find_container_by_serial(container_serial)
        self.assertSetEqual({hotp_sha256.get_serial(), totp_sha256.get_serial(), hotp_sha1.get_serial()},
                            {token.get_serial() for token in container.get_tokens()})

        delete_policy("policy")
        hotp_sha1.delete_token()
        hotp_sha256.delete_token()
        totp_sha1.delete_token()
        totp_sha256.delete_token()
        sms.delete_token()
        delete_container_by_serial(container_serial)

    def test_06_set_realms(self):
        # Only allow to set the realms for disabled containers
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_REALMS,
                   conditions=[(ConditionSection.CONTAINER, "states", PrimaryComparators.CONTAINS,
                                ContainerStates.DISABLED.value, True)])
        container_serial = init_container({"type": "generic"})["container_serial"]

        # set realms for active container fails
        self.request_assert_error(403, f"/container/{container_serial}/realms", {"realms": self.realm1}, self.at,
                                  "POST")
        self.assert_audit_entry('POST /container/<string:container_serial>/realms', success=0, info=self.NOT_EMPTY)

        # Set realms for disabled container is allowed
        set_container_states(container_serial, [ContainerStates.DISABLED.value])
        self.request_assert_success(f"/container/{container_serial}/realms", {"realms": self.realm1}, self.at, "POST")
        self.assert_audit_entry('POST /container/<string:container_serial>/realms', success=1)

        delete_policy("policy")
        delete_container_by_serial(container_serial)

    def test_07_register(self):
        # only allow registration if state != lost/damaged
        set_policy("policy", scope=SCOPE.USER, action=PolicyAction.CONTAINER_REGISTER,
                   conditions=[(ConditionSection.CONTAINER, "states", PrimaryComparators.NOT_CONTAINS,
                                ContainerStates.LOST.value, True),
                               (ConditionSection.CONTAINER, "states", PrimaryComparators.NOT_CONTAINS,
                                ContainerStates.DAMAGED.value, True)
                               ])
        # users should register at different pi servers
        set_policy("registration", scope=SCOPE.CONTAINER, action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.net/"},
                   conditions=[(ConditionSection.USERINFO, "email", PrimaryComparators.MATCHES,
                                ".*@localhost.localdomain", True, ConditionHandleMissingData.IS_FALSE.value)])
        set_policy("registration_external", scope=SCOPE.CONTAINER,
                   action={PolicyAction.CONTAINER_SERVER_URL: "https://pi-external.net/"},
                   conditions=[(ConditionSection.USERINFO, "email", PrimaryComparators.NOT_MATCHES,
                                ".*@localhost.localdomain", True, ConditionHandleMissingData.IS_TRUE.value)])
        container_serial = init_container({"type": "smartphone", "user": "selfservice", "realm": self.realm1})[
            "container_serial"]
        container = find_container_by_serial(container_serial)

        # Registration not allowed
        container.add_states([ContainerStates.LOST.value])
        self.request_assert_error(403, "container/register/initialize", {"container_serial": container_serial},
                                  self.at_user, "POST")
        self.assert_audit_entry('POST /container/register/initialize', success=0, info=self.NOT_EMPTY)

        # Registration allowed
        container.set_states([ContainerStates.ACTIVE.value])
        # external user
        result = self.request_assert_success("container/register/initialize", {"container_serial": container_serial},
                                             self.at_user, "POST")
        self.assert_audit_entry('POST /container/register/initialize', success=1)
        self.assertEqual("https://pi-external.net/", result["result"]["value"]["server_url"])
        # internal user
        unregister(container)
        container.remove_user(User("selfservice", self.realm1))
        container.add_user(User("cornelius", self.realm1))
        result = self.request_assert_success("container/register/initialize", {"container_serial": container_serial},
                                             self.at, "POST")
        self.assert_audit_entry('POST /container/register/initialize', success=1)
        self.assertEqual("https://pi.net/", result["result"]["value"]["server_url"])

        delete_policy("policy")
        delete_policy("registration")
        delete_policy("registration_external")
        container.delete()

    def test_08_server_rollover(self):
        # only allow server rollover if state == lost and user has a phone number
        set_policy("policy", scope=SCOPE.ADMIN, action=PolicyAction.CONTAINER_ROLLOVER,
                   conditions=[
                       (ConditionSection.CONTAINER, "states", PrimaryComparators.CONTAINS, ContainerStates.LOST.value,
                        True),
                       (ConditionSection.USERINFO, "phone", PrimaryComparators.MATCHES, ".+", True,
                        ConditionHandleMissingData.IS_FALSE.value)])
        set_policy("registration", scope=SCOPE.CONTAINER, action=f"{PolicyAction.CONTAINER_SERVER_URL}=https://pi.net/")
        container_serial = init_container({"type": "smartphone", "user": "selfservice", "realm": self.realm1})[
            "container_serial"]
        container = find_container_by_serial(container_serial)

        # Register smartphone
        container.set_container_info([TokenContainerInfoData("registration_state", RegistrationState.REGISTERED.value),
                                      TokenContainerInfoData("server_url", "https://pi.net/")])

        # Rollover fails
        self.request_assert_error(403, "container/register/initialize",
                                  {"container_serial": container_serial, "rollover": True}, self.at, "POST")
        self.assert_audit_entry('POST /container/register/initialize', success=0, info=self.NOT_EMPTY)

        # Change user: Rollover still fails
        container.remove_user(User("selfservice", self.realm1))
        container.add_user(User("cornelius", self.realm1))
        self.request_assert_error(403, "container/register/initialize",
                                  {"container_serial": container_serial, "rollover": True}, self.at, "POST")
        self.assert_audit_entry('POST /container/register/initialize', success=0, info=self.NOT_EMPTY)

        # Rollover success
        container.set_states([ContainerStates.LOST.value])
        data = {"container_serial": container_serial, "rollover": True}
        self.request_assert_success("container/register/initialize", data, self.at, "POST")
        self.assert_audit_entry('POST /container/register/initialize', success=1)

        delete_policy("policy")
        delete_policy("registration")
        container.delete()

    def test_09_register_finalize(self):
        # initially add tokens only allowed if container was not created from a template
        set_policy("registration", scope=SCOPE.CONTAINER, action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.net/"})
        set_policy("initially_add_tokens", scope=SCOPE.CONTAINER, action=PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER,
                   conditions=[(ConditionSection.CONTAINER, "template", PrimaryComparators.NOT_MATCHES, ".+", True)])
        container_serial = init_container({"type": "smartphone", "user": "selfservice", "realm": self.realm1})[
            "container_serial"]
        container = find_container_by_serial(container_serial)

        # --- container without template: initially add tokens allowed ---
        # Register init
        result = self.request_assert_success("container/register/initialize", {"container_serial": container_serial},
                                             self.at, "POST")
        self.assert_audit_entry('POST /container/register/initialize', success=1)
        init_response_data = result["result"]["value"]

        # Finalize
        mock_smph = MockSmartphone()
        params = mock_smph.register_finalize(init_response_data["nonce"], init_response_data["time_stamp"],
                                             "https://pi.net/container/register/finalize", container_serial)
        result = self.request_assert_success("container/register/finalize",
                                             params,
                                             None, 'POST')
        self.assert_audit_entry('POST /container/register/finalize', success=1)
        self.assertTrue(result["result"]["value"]["policies"][PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER])

        # --- container with template: initially add tokens not allowed ---
        unregister(container)
        create_container_template(container.type, "test", {}, False)
        container.template = "test"
        # Register init
        result = self.request_assert_success("container/register/initialize", {"container_serial": container_serial},
                                             self.at, "POST")
        self.assert_audit_entry('POST /container/register/initialize', success=1)
        init_response_data = result["result"]["value"]

        # Finalize
        mock_smph = MockSmartphone()
        params = mock_smph.register_finalize(init_response_data["nonce"], init_response_data["time_stamp"],
                                             "https://pi.net/container/register/finalize", container_serial)
        result = self.request_assert_success("container/register/finalize", params, None, "POST")
        self.assert_audit_entry('POST /container/register/finalize', success=1)
        self.assertFalse(result["result"]["value"]["policies"][PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER])

        delete_policy("registration")
        delete_policy("initially_add_tokens")
        container.delete()

    def test_10_synchronization(self):
        # initially add tokens only allowed for internal users (specific mail domain) + specific client
        set_policy("registration", scope=SCOPE.CONTAINER, action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.net/"})
        set_policy("initially_add_tokens", scope=SCOPE.CONTAINER, action=PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER,
                   conditions=[(ConditionSection.USERINFO, "email", PrimaryComparators.MATCHES,
                                ".+@localhost.localdomain", True, ConditionHandleMissingData.IS_FALSE.value)])
        container_serial = init_container({"type": "smartphone", "user": "selfservice", "realm": self.realm1})[
            "container_serial"]
        container = find_container_by_serial(container_serial)

        # Registration
        result = self.request_assert_success("container/register/initialize", {"container_serial": container_serial},
                                             self.at, "POST")
        self.assert_audit_entry('POST /container/register/initialize', success=1)
        init_response_data = result["result"]["value"]
        # Finalize
        mock_smph = MockSmartphone()
        params = mock_smph.register_finalize(init_response_data["nonce"], init_response_data["time_stamp"],
                                             "https://pi.net/container/register/finalize", container_serial)
        self.request_assert_success("container/register/finalize", params, None, "POST")
        self.assert_audit_entry('POST /container/register/finalize', success=1)

        # Synchronize with external user
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")
        self.assert_audit_entry('POST /container/challenge', success=1)
        params = mock_smph.synchronize(result["result"]["value"], scope)
        result = self.request_assert_success("container/synchronize", params, None, "POST")
        self.assert_audit_entry('POST /container/synchronize', success=1)
        self.assertFalse(result["result"]["value"]["policies"][PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER])

        # Synchronize with internal user
        container.remove_user(User("selfservice", self.realm1))
        container.add_user(User("cornelius", self.realm1))
        scope = "https://pi.net/container/synchronize"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": mock_smph.container_serial}, None,
                                             "POST")
        self.assert_audit_entry('POST /container/challenge', success=1)
        params = mock_smph.synchronize(result["result"]["value"], scope)
        result = self.request_assert_success("container/synchronize", params, None, "POST")
        self.assert_audit_entry('POST /container/synchronize', success=1)
        self.assertTrue(result["result"]["value"]["policies"][PolicyAction.INITIALLY_ADD_TOKENS_TO_CONTAINER])

        delete_policy("registration")
        delete_policy("initially_add_tokens")
        container.delete()

    def test_11_client_rollover(self):
        # Only allowed if state != lost && userinfo
        set_policy("registration", scope=SCOPE.CONTAINER, action={PolicyAction.CONTAINER_SERVER_URL: "https://pi.net/"})
        set_policy("rollover", scope=SCOPE.CONTAINER, action=PolicyAction.CONTAINER_CLIENT_ROLLOVER,
                   conditions=[(ConditionSection.CONTAINER, "states", PrimaryComparators.NOT_CONTAINS,
                                ContainerStates.LOST.value, True),
                               (ConditionSection.USERINFO, "email", PrimaryComparators.MATCHES,
                                ".+@localhost.localdomain",
                                True, ConditionHandleMissingData.IS_FALSE.value)])
        container_serial = init_container({"type": "smartphone", "user": "selfservice", "realm": self.realm1})[
            "container_serial"]
        container = find_container_by_serial(container_serial)

        # Registration
        result = self.request_assert_success("container/register/initialize", {"container_serial": container_serial},
                                             self.at, "POST")
        self.assert_audit_entry('POST /container/register/initialize', success=1)
        init_response_data = result["result"]["value"]
        mock_smph = MockSmartphone()
        params = mock_smph.register_finalize(init_response_data["nonce"], init_response_data["time_stamp"],
                                             "https://pi.net/container/register/finalize", container_serial)
        self.request_assert_success("container/register/finalize", params, None, "POST")
        self.assert_audit_entry('POST /container/register/finalize', success=1)

        container.set_states([ContainerStates.LOST.value])

        # Client rollover: User and state not allowed
        scope = "https://pi.net/container/rollover"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": container_serial}, None,
                                             "POST")
        self.assert_audit_entry('POST /container/challenge', success=1)
        challenge_data = result["result"]["value"]
        rollover_scope = "https://pi.net/container/rollover"
        params = mock_smph.register_finalize(challenge_data["nonce"], challenge_data["time_stamp"],
                                             rollover_scope, mock_smph.container_serial)
        self.request_assert_error(403, "container/rollover", params, None, "POST", try_unspecific=False)
        self.assert_audit_entry('POST /container/rollover', success=0, info=self.NOT_EMPTY)

        # Client rollover: User not allowed
        container.set_states([ContainerStates.ACTIVE.value])
        scope = "https://pi.net/container/rollover"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": container_serial}, None,
                                             "POST")
        self.assert_audit_entry('POST /container/challenge', success=1)
        challenge_data = result["result"]["value"]
        rollover_scope = "https://pi.net/container/rollover"
        params = mock_smph.register_finalize(challenge_data["nonce"], challenge_data["time_stamp"],
                                             rollover_scope, mock_smph.container_serial)
        self.request_assert_error(403, "container/rollover", params, None, "POST",
                                  try_unspecific=False)
        self.assert_audit_entry('POST /container/rollover', success=0, info=self.NOT_EMPTY)

        # Client rollover: State not allowed
        container.remove_user(User("selfservice", self.realm1))
        container.add_user(User("cornelius", self.realm1))
        container.set_states([ContainerStates.LOST.value])
        scope = "https://pi.net/container/rollover"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": container_serial}, None,
                                             "POST")
        self.assert_audit_entry('POST /container/challenge', success=1)
        challenge_data = result["result"]["value"]
        rollover_scope = "https://pi.net/container/rollover"
        params = mock_smph.register_finalize(challenge_data["nonce"], challenge_data["time_stamp"],
                                             rollover_scope, mock_smph.container_serial)
        self.request_assert_error(403, "container/rollover", params, None, "POST",
                                  try_unspecific=False)
        self.assert_audit_entry('POST /container/rollover', success=0, info=self.NOT_EMPTY)

        # Client rollover: Success
        container.set_states([ContainerStates.ACTIVE.value])
        scope = "https://pi.net/container/rollover"
        result = self.request_assert_success("container/challenge",
                                             {"scope": scope, "container_serial": container_serial}, None,
                                             "POST")
        self.assert_audit_entry('POST /container/challenge', success=1)
        challenge_data = result["result"]["value"]
        rollover_scope = "https://pi.net/container/rollover"
        params = mock_smph.register_finalize(challenge_data["nonce"], challenge_data["time_stamp"],
                                             rollover_scope, mock_smph.container_serial)
        self.request_assert_success("container/rollover", params, None, "POST")
        self.assert_audit_entry('POST /container/rollover', success=1)

        delete_policy("registration")
        delete_policy("rollover")
        container.delete()
