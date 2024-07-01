from privacyidea.lib.config import set_privacyidea_config
from privacyidea.lib.container import delete_container_by_id, find_container_by_id, \
    find_container_by_serial, init_container, get_all_containers, _gen_serial, find_container_for_token, \
    get_container_policy_info, remove_tokens_from_container, add_tokens_to_container, delete_container_by_serial, \
    get_container_classes_descriptions, get_container_token_types, add_container_info
from privacyidea.lib.container import get_container_classes
from privacyidea.lib.error import ResourceNotFoundError, ParameterError, EnrollmentError, UserError
from privacyidea.lib.token import init_token, remove_token
from privacyidea.lib.user import User
from privacyidea.models import TokenContainer, Token
from .base import MyTestCase


class TokenContainerManagementTestCase(MyTestCase):
    """
    Note: The tests are not independent. Always run all tests of the class.
    """
    empty_container_serial = "CONT000001"
    smartphone_serial = "SMPH000001"
    generic_serial = "CONT000002"
    yubikey_serial = "YUBI000001"
    hotp_serial_gen = "HOTP000001"
    hotp_serial_yubi = "HOTP000002"
    totp_serial_gen = "TOTP000001"
    totp_serial_smph = "TOTP000002"
    spass_serial_gen = "SPASS000001"

    def get_container_with_user(self):
        self.setUp_user_realms()
        container_serial = init_container({"type": "generic", "user": "hans", "realm": self.realm1})
        container = find_container_by_serial(container_serial)

    def test_01_create_empty_container(self):
        serial = init_container(
            {"type": "generic", "container_serial": self.empty_container_serial, "description": "test container"})
        empty_container = find_container_by_serial(self.empty_container_serial)
        self.assertEqual("test container", empty_container.description)
        self.assertIsNotNone(empty_container.serial)
        self.assertEqual(self.empty_container_serial, serial)
        self.assertTrue(len(empty_container.tokens) == 0)

        # Init container with user and realm
        self.setUp_user_realms()
        serial = init_container({"type": "generic",
                                 "container_serial": self.generic_serial,
                                 "user": "hans",
                                 "realm": self.realm1})
        container = find_container_by_serial(serial)
        self.assertEqual(self.realm1, container.realms[0].name)
        self.assertEqual("hans", container.get_users()[0].login)

        # Init smartphone container with realm
        serial = init_container(
            {"type": "smartphone", "container_serial": self.smartphone_serial, "realm": self.realm1})
        smartphone = find_container_by_serial(serial)
        self.assertEqual(self.realm1, smartphone.realms[0].name)
        self.assertEqual("smartphone", smartphone.type)

        # Init yubikey container
        self.yubikey_serial = init_container({"type": "yubikey", "container_serial": self.yubikey_serial})
        self.assertIsNotNone(self.yubikey_serial)
        self.assertNotEqual("", self.yubikey_serial)

    def test_02_create_container_fails(self):
        # Unknown container type raises exception
        self.assertRaises(EnrollmentError, init_container, {"type": "doesnotexist"})
        # Empty container type raises exception
        self.assertRaises(EnrollmentError, init_container, {})

    def test_03_create_container_wrong_parameters(self):
        # Init container with user: User shall not be assigned (realm required)
        serial = init_container({"type": "Generic", "user": "hans"})
        container = find_container_by_serial(serial)
        self.assertEqual(0, len(container.realms))
        self.assertEqual(0, len(container.get_users()))

        # Init with non-existing user
        serial = init_container({"type": "Generic", "user": "random", "realm": "random"})
        container = find_container_by_serial(serial)
        self.assertEqual(0, len(container.realms))
        self.assertEqual(0, len(container.get_users()))

    def test_04_add_tokens_to_container(self):
        # create tokens
        hotp_token_gen = init_token({"type": "hotp", "genkey": "1", "serial": self.hotp_serial_gen})
        hotp_token_yubi = init_token({"type": "hotp", "genkey": "1", "serial": self.hotp_serial_yubi})
        totp_token_gen = init_token({"type": "totp", "otpkey": "1", "serial": self.totp_serial_gen})
        totp_token_smph = init_token({"type": "totp", "otpkey": "1", "serial": self.totp_serial_smph})
        spass_token = init_token({"type": "spass", "serial": self.spass_serial_gen})

        # Generic container
        gen_token_serials = [self.hotp_serial_gen, self.totp_serial_gen, self.spass_serial_gen]
        res = add_tokens_to_container(self.generic_serial, gen_token_serials, user=User(), user_role="admin")
        self.assertTrue(res)
        # Check tokens
        container = find_container_by_serial(self.generic_serial)
        tokens = [token.get_serial() for token in container.get_tokens()]
        for t_serial in gen_token_serials:
            self.assertIn(t_serial, tokens)
        self.assertEqual(3, len(tokens))

        # Smartphone
        res = add_tokens_to_container(self.smartphone_serial, [self.totp_serial_smph],
                                      user=User(), user_role="admin")
        self.assertTrue(res)
        # Check if token is added to container
        smartphone = find_container_by_serial(self.smartphone_serial)
        tokens = smartphone.get_tokens()
        self.assertEqual(1, len(tokens))
        self.assertIn(self.totp_serial_smph, tokens[0].get_serial())

        # Yubikey
        res = add_tokens_to_container(self.yubikey_serial, [self.hotp_serial_yubi],
                                      user=User(), user_role="admin")
        self.assertTrue(res)
        # Check if token is added to container
        yubikey = find_container_by_serial(self.yubikey_serial)
        tokens = yubikey.get_tokens()
        self.assertEqual(1, len(tokens))
        self.assertIn(self.hotp_serial_yubi, tokens[0].get_serial())

    def test_05_add_token_to_another_container(self):
        res = add_tokens_to_container(self.smartphone_serial, [self.hotp_serial_gen],
                                      user=User(), user_role="admin")
        self.assertTrue(res[self.hotp_serial_gen])
        # Check containers of the token
        db_result = TokenContainer.query.join(Token.container).filter(Token.serial == self.hotp_serial_gen)
        container_serials = [row.serial for row in db_result]
        self.assertEqual(1, len(container_serials))
        self.assertEqual(self.smartphone_serial, container_serials[0])

    def test_06_add_wrong_token_types_to_container(self):
        # Smartphone
        spass_token = init_token({"type": "spass"})
        result = add_tokens_to_container(self.smartphone_serial, [spass_token.get_serial()],
                                         user=User(), user_role="admin")
        self.assertFalse(result[spass_token.get_serial()])

        # Yubikey
        totp_token = init_token({"type": "totp", "otpkey": "1"})
        result = add_tokens_to_container(self.yubikey_serial, [totp_token.get_serial()],
                                         user=User(), user_role="admin")
        self.assertFalse(result[totp_token.get_serial()])

    def test_07_add_tokens_to_container_fails(self):
        # Add token which is already in the container
        result = add_tokens_to_container(self.smartphone_serial,
                                         [self.totp_serial_smph, self.hotp_serial_yubi],
                                         user=User(), user_role="admin")
        self.assertFalse(result[self.totp_serial_smph])
        self.assertTrue(result[self.hotp_serial_yubi])

        # Add non-existing token to container
        result = add_tokens_to_container(self.smartphone_serial, ["non_existing_token"],
                                         user=User(), user_role="admin")
        self.assertNotIn("non_existing_token", result.keys())

    def test_08_remove_tokens_from_container_success(self):
        generic_token_serials = [self.totp_serial_gen, self.spass_serial_gen]
        result = remove_tokens_from_container(self.generic_serial, generic_token_serials)
        self.assertTrue(result[self.totp_serial_gen])
        self.assertTrue(result[self.spass_serial_gen])

    def test_09_remove_tokens_from_container_fails(self):
        # Remove non-existing token from container
        result = remove_tokens_from_container(self.smartphone_serial, ["non_existing_token"])
        self.assertFalse(result["non_existing_token"])

        # Remove tokens that are not in the container
        result = remove_tokens_from_container(self.generic_serial, [self.hotp_serial_yubi])
        self.assertFalse(result[self.hotp_serial_yubi])

        # Pass empty token serial list
        result = remove_tokens_from_container(self.generic_serial, [])
        self.assertFalse(result)

        # Pass non-existing container serial
        self.assertRaises(ResourceNotFoundError, remove_tokens_from_container,
                          container_serial="non_existing_container",
                          token_serials=[self.hotp_serial_gen])

    def test_10_delete_token_remove_from_container(self):
        result = remove_token(self.totp_serial_smph)
        self.assertTrue(result)
        container = find_container_by_serial(self.smartphone_serial)
        self.assertNotIn(self.totp_serial_smph, container.get_tokens())

    def test_11_find_container_for_token(self):
        # Token without container
        token = init_token({"type": "hotp", "genkey": "1"})
        container_result = find_container_for_token(token.get_serial())
        self.assertIsNone(container_result)

        # Token with container
        container_serial = init_container({"type": "generic"})
        add_tokens_to_container(container_serial, [token.get_serial()], user=User(), user_role="admin")
        container_result = find_container_for_token(token.get_serial())
        self.assertEqual(container_serial, container_result.serial)

        # Call with non-existing token serial
        self.assertRaises(ResourceNotFoundError, find_container_for_token, "non_existing_token")

    def test_12_delete_container_by_id(self):
        # Fail
        self.assertRaises(ParameterError, delete_container_by_id, None)
        self.assertRaises(ResourceNotFoundError, delete_container_by_id, 11)

        # Success
        container = find_container_by_serial(self.yubikey_serial)
        container_id = container._db_container.id
        result = delete_container_by_id(container_id)
        self.assertEqual(container_id, result)

    def test_13_delete_container_by_serial(self):
        # Fail
        self.assertRaises(ParameterError, delete_container_by_serial, None)
        self.assertRaises(ResourceNotFoundError, delete_container_by_serial, "non_existing_serial")

        # Success
        container_id = delete_container_by_serial(self.generic_serial)
        self.assertGreater(container_id, 0)
        container_id = delete_container_by_serial(self.smartphone_serial)
        self.assertGreater(container_id, 0)

    def test_14_find_container_fails(self):
        # Find by ID
        self.assertRaises(ResourceNotFoundError, find_container_by_id, 11)
        self.assertRaises(ResourceNotFoundError, find_container_by_id, None)
        # Find by serial
        self.assertRaises(ResourceNotFoundError, find_container_by_serial, "non_existing_serial")
        self.assertRaises(ResourceNotFoundError, find_container_by_serial, None)

    def test_15_find_container_success(self):
        # Find by serial
        serial = init_container({"type": "generic", "description": "find container"})
        container = find_container_by_serial(serial)
        self.assertEqual(serial, container.serial)

        # Find by ID
        container = find_container_by_id(container._db_container.id)
        self.assertEqual(serial, container.serial)

    def test_16_set_realms(self):
        # Arrange
        self.setUp_user_realms()
        self.setUp_user_realm2()
        container_serial = init_container({"type": "generic", "description": "Set Realm Container"})
        container = find_container_by_serial(container_serial)

        # Set existing realms
        result = container.set_realms([self.realm1, self.realm2])
        # Check return value
        self.assertTrue(result['deleted'])
        self.assertTrue(result[self.realm1])
        self.assertTrue(result[self.realm2])
        # Check realms
        container_realms = [realm.name for realm in container.realms]
        self.assertIn(self.realm1, container_realms)
        self.assertIn(self.realm2, container_realms)

        # Set one non-existing realm
        result = container.set_realms(["nonexisting", self.realm2])
        # Check return value
        self.assertTrue(result['deleted'])
        self.assertFalse(result['nonexisting'])
        self.assertTrue(result[self.realm2])
        # Check realms
        container_realms = [realm.name for realm in container.realms]
        self.assertNotIn("nonexisting", container_realms)
        self.assertIn(self.realm2, container_realms)

        # Set empty realm
        result = container.set_realms([""])
        self.assertTrue(result['deleted'])
        container_realms = [realm.name for realm in container.realms]
        self.assertEqual(0, len(container_realms))

    def test_17_add_realms(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        container_serial = init_container({"type": "generic", "description": "test container"})
        container = find_container_by_serial(container_serial)

        # Add existing realm
        result = container.set_realms([self.realm1], add=True)
        # Check return value
        self.assertFalse(result['deleted'])
        self.assertTrue(result[self.realm1])
        # Check realms
        container_realms = [realm.name for realm in container.realms]
        self.assertIn(self.realm1, container_realms)

        # Add same realm
        result = container.set_realms([self.realm1], add=True)
        self.assertFalse(result[self.realm1])

        # Add one non-existing realm
        result = container.set_realms(["nonexisting", self.realm2], add=True)
        # Check return value
        self.assertFalse(result['deleted'])
        self.assertFalse(result['nonexisting'])
        self.assertTrue(result[self.realm2])
        # Check realms
        container_realms = [realm.name for realm in container.realms]
        self.assertNotIn("nonexisting", container_realms)
        self.assertIn(self.realm2, container_realms)
        self.assertIn(self.realm1, container_realms)

        # Add empty realm
        result = container.set_realms([""], add=True)
        self.assertFalse(result['deleted'])
        container_realms = [realm.name for realm in container.realms]
        self.assertEqual(2, len(container_realms))

        # Add none realm
        result = container.set_realms(None, add=True)
        self.assertFalse(result['deleted'])
        container_realms = [realm.name for realm in container.realms]
        self.assertEqual(2, len(container_realms))

    def test_18_assign_user(self):
        # Arrange
        self.setUp_user_realms()
        container_serial = init_container({"type": "generic", "description": "assign user"})
        container = find_container_by_serial(container_serial)
        user_hans = User(login="hans", realm=self.realm1, resolver=self.resolvername1)
        user_root = User(login="root", realm=self.realm1, resolver=self.resolvername1)
        invalid_user = User(login="invalid", realm="invalid")

        # Assign user
        result = container.add_user(user_hans)
        users = container.get_users()
        self.assertTrue(result)
        self.assertEqual(1, len(users))
        self.assertEqual("hans", users[0].login)
        self.assertEqual(self.realm1, container.realms[0].name)

        # Assign another user fails
        result = container.add_user(user_root)
        users = container.get_users()
        self.assertFalse(result)
        self.assertEqual(1, len(users))
        self.assertEqual("hans", users[0].login)
        self.assertEqual(self.realm1, container.realms[0].name)

        # Assign an invalid user raises exception
        self.assertRaises(UserError, container.add_user, invalid_user)

    def test_19_add_container_info(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "add container info"})
        container = find_container_by_serial(container_serial)

        # Add container info
        add_container_info(container_serial, "key1", "value1")
        container_info = {container_info.key: container_info.value for container_info in container.get_container_info()}
        self.assertEqual("value1", container_info["key1"])

        # Add second info does not overwrite first info
        add_container_info(container_serial, "key2", "value2")
        container_info = {container_info.key: container_info.value for container_info in container.get_container_info()}
        self.assertEqual("value1", container_info["key1"])
        self.assertEqual("value2", container_info["key2"])

        # Pass no key changes nothing
        add_container_info(container_serial, "key2", "value2")
        container_info = {container_info.key: container_info.value for container_info in container.get_container_info()}
        self.assertEqual("value1", container_info["key1"])
        self.assertEqual("value2", container_info["key2"])

        # Pass no value sets empty value
        add_container_info(container_serial, "key", None)
        container_info = {container_info.key: container_info.value for container_info in container.get_container_info()}
        self.assertEqual("", container_info["key"])

    def test_20_set_container_info(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "add container info"})
        container = find_container_by_serial(container_serial)

        # Set container info
        container.set_container_info({"key1": "value1"})
        container_info = {container_info.key: container_info.value for container_info in container.get_container_info()}
        self.assertEqual("value1", container_info["key1"])

        # Set second info overwrites first info
        container.set_container_info({"key2": "value2"})
        container_info = {container_info.key: container_info.value for container_info in container.get_container_info()}
        self.assertEqual("value2", container_info["key2"])
        self.assertNotIn("key1", container_info.keys())

        # Pass no info only deletes old entries
        container.set_container_info(None)
        container_info = container.get_container_info()
        self.assertEqual(0, len(container_info))

        # Pass no value
        container.set_container_info({"key": None})
        container_info = {container_info.key: container_info.value for container_info in container.get_container_info()}
        self.assertEqual("", container_info["key"])

        # Pass no key only deletes old entries
        container.set_container_info({None: "value"})
        container_info = container.get_container_info()
        self.assertEqual(0, len(container_info))

    def test_21_delete_container_info(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "delete container info"})
        container = find_container_by_serial(container_serial)
        container.set_container_info({"key1": "value1", "key2": "value2", "key3": "value3"})

        # Delete non-existing key
        container.delete_container_info("non_existing_key")
        container_info = {container_info.key: container_info.value for container_info in container.get_container_info()}
        self.assertEqual(3, len(container_info))

        # Delete existing key
        container.delete_container_info("key1")
        container_info = {container_info.key: container_info.value for container_info in container.get_container_info()}
        self.assertEqual(2, len(container_info))
        self.assertNotIn("key1", container_info.keys())

        # Delete all keys
        container.delete_container_info()
        container_info = {container_info.key: container_info.value for container_info in container.get_container_info()}
        self.assertEqual(0, len(container_info))

    def test_22_set_description(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "Initial description"})
        container = find_container_by_serial(container_serial)

        # Set empty description
        container.description = ""
        self.assertEqual("", container.description)

        # Set description
        container.description = "new description"
        self.assertEqual("new description", container.description)

        # Set None description
        container.description = None
        self.assertEqual("", container.description)

    def test_23_set_states(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "Set states"})
        container = find_container_by_serial(container_serial)

        # check initial state
        states = container.get_states()
        self.assertEqual(1, len(states))
        self.assertIn("active", states)

        # Set state overwrites previous state
        container.set_states(["disabled", "lost"])
        states = container.get_states()
        self.assertEqual(2, len(states))
        self.assertIn("disabled", states)
        self.assertIn("lost", states)

        # Set empty state list: Shall delete all states
        container.set_states([])
        states = container.get_states()
        self.assertEqual(0, len(states))

        # Set unknown state
        container.set_states(["unknown_state", "active"])
        states = container.get_states()
        self.assertEqual(1, len(states))
        self.assertIn("active", states)

        # Set none
        container.set_states(None)
        states = container.get_states()
        self.assertEqual(0, len(states))

        # Set excluded states
        # TODO: Shall that be possible? And if not what would be expected?
        container.set_states(["active", "disabled"])
        states = container.get_states()
        self.assertEqual(2, len(states))
        self.assertIn("disabled", states)
        self.assertIn("active", states)

    def test_23_add_states(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "Set states"})
        container = find_container_by_serial(container_serial)

        # check initial state
        states = container.get_states()
        self.assertEqual(1, len(states))
        self.assertIn("active", states)

        # Add state
        container.add_states(["lost"])
        states = container.get_states()
        self.assertEqual(2, len(states))
        self.assertIn("active", states)
        self.assertIn("lost", states)

        # Add empty state list: Changes nothing
        container.add_states([])
        states = container.get_states()
        self.assertEqual(2, len(states))

        # Add none: Changes nothing
        container.add_states(None)
        states = container.get_states()
        self.assertEqual(2, len(states))

        # Add unknown state
        container.add_states(["unknown_state"])
        states = container.get_states()
        self.assertEqual(2, len(states))
        self.assertIn("active", states)
        self.assertIn("lost", states)

        # Add excluding state: removes excluded state
        container.add_states(["disabled"])
        states = container.get_states()
        self.assertEqual(2, len(states))
        self.assertIn("disabled", states)
        self.assertIn("lost", states)

    def test_24_get_all_containers_paginate(self):
        # Removes all previously initialized containers
        TokenContainer.query.delete()
        # Arrange
        types = ["Smartphone", "generic", "Yubikey", "Smartphone", "generic", "Yubikey"]
        container_serials = []
        for t in types:
            serial = init_container({"type": t, "description": "test container"})
            container_serials.append(serial)

        # Filter for container serial
        container_data = get_all_containers(serial=container_serials[3], pagesize=15)
        self.assertEqual(1, container_data["count"])
        self.assertEqual(container_data["containers"][0].serial, container_serials[3])

        # Filter for non-existing serial
        container_data = get_all_containers(serial="non_existing_serial")
        self.assertEqual(0, len(container_data["containers"]))

        # filter for type
        container_data = get_all_containers(ctype="generic", pagesize=15)
        for container in container_data["containers"]:
            self.assertEqual(container.type, "generic")
        self.assertEqual(2, container_data["count"])

        # filter for non-existing type
        container_data = get_all_containers(ctype="random_type")
        self.assertEqual(0, len(container_data["containers"]))

        # Assign token
        tokens = []
        params = {"genkey": "1"}
        for i in range(3):
            t = init_token(params)
            tokens.append(t)
        token_serials = [t.get_serial() for t in tokens]

        for serial in container_serials[2:4]:
            container = find_container_by_serial(serial)
            for token in tokens:
                container.add_token(token)

        # Filter for token serial
        container_data = get_all_containers(token_serial=token_serials[1], pagesize=15)
        for container in container_data["containers"]:
            self.assertTrue(container.serial in container_serials[2:4])
        self.assertEqual(2, container_data["count"])

        # Filter for non-existing token serial: returns all containers
        container_data = get_all_containers(token_serial="non_existing_token", pagesize=15)
        self.assertEqual(6, len(container_data["containers"]))

        # Test pagination
        container_data = get_all_containers(page=2, pagesize=2)
        self.assertEqual(1, container_data["prev"])
        self.assertEqual(2, container_data["current"])
        self.assertEqual(3, container_data["next"])
        self.assertEqual(6, container_data["count"])
        self.assertEqual(2, len(container_data["containers"]))

        # Do not use pagination
        container_data = get_all_containers()
        self.assertNotIn("prev", container_data)
        self.assertNotIn("current", container_data)
        self.assertEqual(6, len(container_data["containers"]))

        # sort by type ascending
        container_data = get_all_containers(sortby="type", sortdir="asc")
        self.assertEqual("generic", container_data["containers"][0].type)
        self.assertEqual("yubikey", container_data["containers"][-1].type)

        # sort by serial descending
        container_data = get_all_containers(sortby="serial", sortdir="desc")
        self.assertEqual("YUBI", container_data["containers"][0].serial[:4])
        self.assertEqual("CONT", container_data["containers"][-1].serial[:4])

        # sort for non-existing column: uses serial instead
        container_data = get_all_containers(sortby="random_column", sortdir="asc")
        self.assertEqual("CONT", container_data["containers"][0].serial[:4])
        self.assertEqual("YUBI", container_data["containers"][-1].serial[:4])

        # non-existing sort direction: uses asc instead
        container_data = get_all_containers(sortby="type", sortdir="wrong_dir")
        self.assertEqual("generic", container_data["containers"][0].type)
        self.assertEqual("yubikey", container_data["containers"][-1].type)

    def test_25_gen_serial(self):
        # Test class prefix
        serial = _gen_serial(container_type="non_existing_type")
        self.assertEqual("CONT", serial[:4])

        serial = _gen_serial(container_type="generic")
        self.assertEqual("CONT", serial[:4])

        serial = _gen_serial(container_type="smartphone")
        self.assertEqual("SMPH", serial[:4])

        serial = _gen_serial(container_type="yubikey")
        self.assertEqual("YUBI", serial[:4])

        # test length
        self.assertEqual(8 + len("YUBI"), len(serial))

        set_privacyidea_config("SerialLength", 12)
        serial = _gen_serial(container_type="generic")
        self.assertEqual(12 + len("CONT"), len(serial))

        set_privacyidea_config("SerialLength", -1)
        serial = _gen_serial(container_type="generic")
        self.assertEqual(8, len(serial))

        set_privacyidea_config("SerialLength", 8)

    def test_26_container_token_types(self):
        supported_token_types = get_container_token_types()
        container_types = supported_token_types.keys()
        # All classes are included
        self.assertIn("generic", container_types)
        self.assertIn("smartphone", container_types)
        self.assertIn("yubikey", container_types)
        self.assertEqual(3, len(container_types))

    def test_27_get_container_classes(self):
        container_classes = get_container_classes()
        container_types = container_classes.keys()
        # All classes are included
        self.assertIn("generic", container_types)
        self.assertIn("smartphone", container_types)
        self.assertIn("yubikey", container_types)
        self.assertEqual(3, len(container_types))

    def test_28_get_container_classes_description(self):
        container_classes = get_container_classes_descriptions()
        container_types = container_classes.keys()
        # All classes are included
        self.assertIn("generic", container_types)
        self.assertIn("smartphone", container_types)
        self.assertIn("yubikey", container_types)
        self.assertEqual(3, len(container_types))

    def test_29_get_container_policy_info(self):
        # Test for generic
        policy_info = get_container_policy_info(container_type="generic")
        self.assertTrue(policy_info)

        # Test for non-existing type
        self.assertRaises(ResourceNotFoundError, get_container_policy_info, container_type="wrong_type")

        # Get policy info for all container types
        policy_info = get_container_policy_info()
        self.assertIn("yubikey", policy_info.keys())

    def test_30_container_classes(self):
        classes = get_container_classes()
        policies = {}
        for k, v in classes.items():
            policies[k] = v.get_container_policy_info()
            self.assertTrue(policies[k])
