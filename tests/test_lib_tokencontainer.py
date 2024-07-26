from privacyidea.lib.config import set_privacyidea_config
from privacyidea.lib.container import delete_container_by_id, find_container_by_id, find_container_by_serial, \
    init_container, get_all_containers, _gen_serial, find_container_for_token, get_container_policy_info, \
    delete_container_by_serial, get_container_classes_descriptions, get_container_token_types, add_container_info, \
    _check_user_access_on_container, assign_user, set_container_realms, add_container_realms, get_container_info_dict, \
    set_container_info, delete_container_info, set_container_description, set_container_states, add_container_states, \
    remove_multiple_tokens_from_container, remove_token_from_container, add_multiple_tokens_to_container, \
    add_token_to_container
from privacyidea.lib.container import get_container_classes
from privacyidea.lib.error import ResourceNotFoundError, ParameterError, EnrollmentError, UserError, PolicyError, \
    TokenAdminError
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

    def test_03_create_container_wrong_user_parameters(self):
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

    def test_04_add_multiple_tokens_to_container_success(self):
        # Create tokens
        init_token({"type": "hotp", "genkey": "1", "serial": self.hotp_serial_gen})
        init_token({"type": "totp", "otpkey": "1", "serial": self.totp_serial_gen})
        init_token({"type": "spass", "serial": self.spass_serial_gen})
        gen_token_serials = [self.hotp_serial_gen, self.totp_serial_gen, self.spass_serial_gen]

        # Add tokens to generic container
        res = add_multiple_tokens_to_container(self.generic_serial, gen_token_serials, user=User(), user_role="admin",
                                               allowed_realms=None)
        self.assertTrue(res)
        # Check tokens
        container = find_container_by_serial(self.generic_serial)
        tokens = [token.get_serial() for token in container.get_tokens()]
        for t_serial in gen_token_serials:
            self.assertIn(t_serial, tokens)
        self.assertEqual(3, len(tokens))

    def test_05_add_token_to_container_success(self):
        # Smartphone
        init_token({"type": "totp", "otpkey": "1", "serial": self.totp_serial_smph})
        res = add_token_to_container(self.smartphone_serial, self.totp_serial_smph, user_role="admin")
        self.assertTrue(res)
        # Check if token is added to container
        smartphone = find_container_by_serial(self.smartphone_serial)
        tokens = smartphone.get_tokens()
        self.assertEqual(1, len(tokens))
        self.assertIn(self.totp_serial_smph, tokens[0].get_serial())

        # Yubikey
        init_token({"type": "hotp", "genkey": "1", "serial": self.hotp_serial_yubi})
        res = add_token_to_container(self.yubikey_serial, self.hotp_serial_yubi, user_role="admin")
        self.assertTrue(res)
        # Check if token is added to container
        yubikey = find_container_by_serial(self.yubikey_serial)
        tokens = yubikey.get_tokens()
        self.assertEqual(1, len(tokens))
        self.assertIn(self.hotp_serial_yubi, tokens[0].get_serial())

    def test_06_add_token_to_another_container(self):
        # Add HOTP token from the generic container to the smartphone
        res = add_token_to_container(self.smartphone_serial, self.hotp_serial_gen, user_role="admin")
        self.assertTrue(res)
        # Check containers: Token is only in smartphone container
        db_result = TokenContainer.query.join(Token.container).filter(Token.serial == self.hotp_serial_gen)
        container_serials = [row.serial for row in db_result]
        self.assertEqual(1, len(container_serials))
        self.assertEqual(self.smartphone_serial, container_serials[0])

    def test_07_add_wrong_token_types_to_container(self):
        # Smartphone
        spass_token = init_token({"type": "spass"})
        self.assertRaises(ParameterError, add_token_to_container, self.smartphone_serial, spass_token.get_serial(),
                          user_role="admin")

        # Yubikey
        totp_token = init_token({"type": "totp", "otpkey": "1"})
        self.assertRaises(ParameterError, add_token_to_container, self.yubikey_serial, totp_token.get_serial(),
                          user_role="admin")

        # Add multiple tokens does not raise exception
        spass_token = init_token({"type": "spass"})
        hotp_token = init_token({"type": "hotp", "genkey": "1"})
        res = add_multiple_tokens_to_container(self.smartphone_serial,
                                               [spass_token.get_serial(), hotp_token.get_serial()],
                                               user_role="admin", allowed_realms=None)
        self.assertFalse(res[spass_token.get_serial()])
        self.assertTrue(res[hotp_token.get_serial()])

    def test_08_add_token_to_container_fails(self):
        # Single non-existing token
        self.assertRaises(ResourceNotFoundError, add_token_to_container, self.smartphone_serial, "non_existing_token",
                          user_role="admin")

        # Add multiple tokens with non-existing token to container
        token = init_token({"type": "hotp", "genkey": "1"})
        result = add_multiple_tokens_to_container(self.smartphone_serial, ["non_existing_token", token.get_serial()],
                                                  user=User(), user_role="admin", allowed_realms=None)
        self.assertFalse(result["non_existing_token"])
        self.assertTrue(result[token.get_serial()])

        # Add single token which is already in the container
        result = add_token_to_container(self.smartphone_serial, self.totp_serial_smph, user_role="admin")
        self.assertFalse(result)

        # Add multiple tokens with one token that is already in the container
        result = add_multiple_tokens_to_container(self.smartphone_serial,
                                                  [self.totp_serial_smph, self.hotp_serial_yubi],
                                                  user=User(), user_role="admin", allowed_realms=None)
        self.assertTrue(result[self.totp_serial_smph])
        self.assertTrue(result[self.hotp_serial_yubi])

    def test_09_remove_multiple_tokens_from_container_success(self):
        generic_token_serials = [self.totp_serial_gen, self.spass_serial_gen]
        result = remove_multiple_tokens_from_container(self.generic_serial, generic_token_serials, User(), "admin",
                                                       allowed_realms=None)
        self.assertTrue(result[self.totp_serial_gen])
        self.assertTrue(result[self.spass_serial_gen])
        # Check tokens of container
        container = find_container_by_serial(self.generic_serial)
        generic_tokens = [token.get_serial() for token in container.get_tokens()]
        self.assertNotIn(self.totp_serial_gen, generic_tokens)
        self.assertNotIn(self.spass_serial_gen, generic_tokens)

    def test_10_remove_token_from_container_success(self):
        result = remove_token_from_container(self.smartphone_serial, self.totp_serial_smph, User(), "admin")
        self.assertTrue(result)
        container = find_container_by_serial(self.smartphone_serial)
        smartphone_tokens = [token.get_serial() for token in container.get_tokens()]
        self.assertNotIn(self.totp_serial_smph, smartphone_tokens)

    def test_11_remove_token_from_container_fails(self):
        # Remove non-existing token from container
        self.assertRaises(ResourceNotFoundError, remove_token_from_container, self.smartphone_serial,
                          "non_existing_token", User(), "admin")

        # Remove token that is not in the container
        result = remove_token_from_container(self.generic_serial, self.hotp_serial_yubi, User(), "admin")
        self.assertFalse(result)

        # Pass no token serial
        self.assertRaises(ParameterError, remove_token_from_container, self.smartphone_serial, None, user_role="admin")

        # Pass non-existing container serial
        self.assertRaises(ResourceNotFoundError, remove_token_from_container,
                          container_serial="non_existing_container",
                          token_serial=self.hotp_serial_gen, user=User(), user_role="admin")

    def test_12_remove_multiple_tokens_from_container_fails(self):
        # Remove non-existing tokens from container
        result = remove_multiple_tokens_from_container(self.generic_serial, ["non_existing_token", "random"],
                                                       user_role="admin", allowed_realms=None)
        self.assertFalse(result["non_existing_token"])
        self.assertFalse(result["random"])

        # Remove token that is not in the container
        result = remove_multiple_tokens_from_container(self.generic_serial,
                                                       [self.hotp_serial_yubi, self.totp_serial_smph],
                                                       user_role="admin", allowed_realms=None)
        self.assertFalse(result[self.hotp_serial_yubi])
        self.assertFalse(result[self.totp_serial_smph])

        # Pass empty token serial list
        result = remove_multiple_tokens_from_container(self.generic_serial, [], User(), "admin",
                                                       allowed_realms=None)
        self.assertEqual(0, len(result))

        # Pass non-existing container serial
        self.assertRaises(ResourceNotFoundError, remove_multiple_tokens_from_container,
                          container_serial="non_existing_container",
                          token_serials=[self.hotp_serial_gen], user=User(), user_role="admin", allowed_realms=None)

    def test_13_delete_token_remove_from_container(self):
        result = remove_token(self.totp_serial_smph)
        self.assertTrue(result)
        container = find_container_by_serial(self.smartphone_serial)
        token_serials = [token.get_serial() for token in container.get_tokens()]
        self.assertNotIn(self.totp_serial_smph, token_serials)

    def test_14_find_container_for_token(self):
        # Token without container
        token = init_token({"type": "hotp", "genkey": "1"})
        container_result = find_container_for_token(token.get_serial())
        self.assertIsNone(container_result)

        # Token with container
        container_serial = init_container({"type": "generic"})
        add_token_to_container(container_serial, token.get_serial(), user_role="admin")
        container_result = find_container_for_token(token.get_serial())
        self.assertEqual(container_serial, container_result.serial)

        # Call with non-existing token serial
        self.assertRaises(ResourceNotFoundError, find_container_for_token, "non_existing_token")

    def test_15_delete_container_by_id(self):
        # Fail
        self.assertRaises(ParameterError, delete_container_by_id, None, User(), "admin")
        self.assertRaises(ResourceNotFoundError, delete_container_by_id, 11, User(), "admin")

        # Success
        container = find_container_by_serial(self.yubikey_serial)
        container_id = container._db_container.id
        result = delete_container_by_id(container_id, User(), "admin")
        self.assertEqual(container_id, result)

    def test_16_delete_container_by_serial(self):
        # Fail
        self.assertRaises(ParameterError, delete_container_by_serial, None, User, "admin")
        self.assertRaises(ResourceNotFoundError, delete_container_by_serial, "non_existing_serial", User, "admin")

        # Success
        container_id = delete_container_by_serial(self.generic_serial, User, "admin")
        self.assertGreater(container_id, 0)
        self.assertRaises(ResourceNotFoundError, find_container_by_serial, self.generic_serial)
        container_id = delete_container_by_serial(self.smartphone_serial, User, "admin")
        self.assertGreater(container_id, 0)
        self.assertRaises(ResourceNotFoundError, find_container_by_serial, self.smartphone_serial)

    def test_17_find_container_fails(self):
        # Find by ID
        self.assertRaises(ResourceNotFoundError, find_container_by_id, 100)
        self.assertRaises(ResourceNotFoundError, find_container_by_id, None)
        # Find by serial
        self.assertRaises(ResourceNotFoundError, find_container_by_serial, "non_existing_serial")
        self.assertRaises(ResourceNotFoundError, find_container_by_serial, None)

    def test_18_find_container_success(self):
        # Find by serial
        serial = init_container({"type": "generic", "description": "find container"})
        container = find_container_by_serial(serial)
        self.assertEqual(serial, container.serial)

        # Find by ID
        container = find_container_by_id(container._db_container.id)
        self.assertEqual(serial, container.serial)

    def test_19_set_realms(self):
        # Arrange
        self.setUp_user_realms()
        self.setUp_user_realm2()
        container_serial = init_container({"type": "generic", "description": "Set Realm Container"})
        container = find_container_by_serial(container_serial)

        # Set existing realms
        result = set_container_realms(container_serial, [self.realm1, self.realm2], None)
        # Check return value
        self.assertTrue(result['deleted'])
        self.assertTrue(result[self.realm1])
        self.assertTrue(result[self.realm2])
        # Check realms
        container_realms = [realm.name for realm in container.realms]
        self.assertIn(self.realm1, container_realms)
        self.assertIn(self.realm2, container_realms)

        # Set one non-existing realm
        result = set_container_realms(container_serial, ["nonexisting", self.realm2], None)
        # Check return value
        self.assertTrue(result['deleted'])
        self.assertFalse(result['nonexisting'])
        self.assertTrue(result[self.realm2])
        # Check realms
        container_realms = [realm.name for realm in container.realms]
        self.assertNotIn("nonexisting", container_realms)
        self.assertIn(self.realm2, container_realms)

        # Set empty realm
        result = set_container_realms(container_serial, [""], None)
        self.assertTrue(result['deleted'])
        container_realms = [realm.name for realm in container.realms]
        self.assertEqual(0, len(container_realms))

    def test_20_add_realms(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        container_serial = init_container({"type": "generic", "description": "test container"})
        container = find_container_by_serial(container_serial)

        # Add existing realm
        result = add_container_realms(container_serial, [self.realm1], None)
        # Check return value
        self.assertFalse(result['deleted'])
        self.assertTrue(result[self.realm1])
        # Check realms
        container_realms = [realm.name for realm in container.realms]
        self.assertIn(self.realm1, container_realms)

        # Add same realm
        result = add_container_realms(container_serial, [self.realm1], None)
        self.assertFalse(result[self.realm1])

        # Add one non-existing realm
        result = add_container_realms(container_serial, ["nonexisting", self.realm2], None)
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
        result = add_container_realms(container_serial, [""], None)
        self.assertFalse(result['deleted'])
        container_realms = [realm.name for realm in container.realms]
        self.assertEqual(2, len(container_realms))

        # Add none realm
        result = add_container_realms(container_serial, None, None)
        self.assertFalse(result['deleted'])
        container_realms = [realm.name for realm in container.realms]
        self.assertEqual(2, len(container_realms))

    def test_21_assign_user(self):
        # Arrange
        self.setUp_user_realms()
        container_serial = init_container({"type": "generic", "description": "assign user"})
        container = find_container_by_serial(container_serial)
        user_hans = User(login="hans", realm=self.realm1, resolver=self.resolvername1)
        user_root = User(login="root", realm=self.realm1, resolver=self.resolvername1)
        invalid_user = User(login="invalid", realm="invalid")

        # Assign user
        result = assign_user(container_serial, user_hans, None, "admin")
        users = container.get_users()
        self.assertTrue(result)
        self.assertEqual(1, len(users))
        self.assertEqual("hans", users[0].login)
        self.assertEqual(self.realm1, container.realms[0].name)

        # Assigning another user fails
        self.assertRaises(TokenAdminError, assign_user, container_serial, user_root, None, "admin")

        # Assigning an invalid user raises exception
        self.assertRaises(UserError, assign_user, container_serial, invalid_user, None, "admin")

    def test_22_add_container_info(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "add container info"})

        # Add container info
        add_container_info(container_serial, "key1", "value1", None, "admin")
        container_info = get_container_info_dict(container_serial, user_role="admin")
        self.assertEqual("value1", container_info["key1"])

        # Add second info does not overwrite first info
        add_container_info(container_serial, "key2", "value2", None, "admin")
        container_info = get_container_info_dict(container_serial, user_role="admin")
        self.assertEqual("value1", container_info["key1"])
        self.assertEqual("value2", container_info["key2"])

        # Pass no key changes nothing
        add_container_info(container_serial, "key2", "value2", None, "admin")
        container_info = get_container_info_dict(container_serial, user_role="admin")
        self.assertEqual("value1", container_info["key1"])
        self.assertEqual("value2", container_info["key2"])

        # Pass no value sets empty value
        add_container_info(container_serial, "key", None, None, "admin")
        container_info = get_container_info_dict(container_serial, user_role="admin")
        self.assertEqual("", container_info["key"])

    def test_23_set_container_info(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "add container info"})

        # Set container info
        res = set_container_info(container_serial, {"key1": "value1"}, None, "admin")
        self.assertTrue(res)
        container_info = get_container_info_dict(container_serial, user_role="admin")
        self.assertEqual("value1", container_info["key1"])
        container_info = get_container_info_dict(container_serial, ikey="key1", user_role="admin")
        self.assertEqual("value1", container_info["key1"])

        # Set second info overwrites first info
        res = set_container_info(container_serial, {"key2": "value2"}, None, "admin")
        self.assertTrue(res)
        container_info = get_container_info_dict(container_serial, user_role="admin")
        self.assertEqual("value2", container_info["key2"])
        self.assertNotIn("key1", container_info.keys())
        container_info = get_container_info_dict(container_serial, ikey="key1", user_role="admin")
        self.assertIsNone(container_info["key1"])

        # Pass no info only deletes old entries
        res = set_container_info(container_serial, None, None, "admin")
        self.assertTrue(res)
        container_info = get_container_info_dict(container_serial, user_role="admin")
        self.assertEqual(0, len(container_info))

        # Pass no value
        res = set_container_info(container_serial, {"key": None}, None, "admin")
        self.assertTrue(res)
        container_info = get_container_info_dict(container_serial, user_role="admin")
        self.assertEqual("", container_info["key"])

        # Pass no key only deletes old entries
        res = set_container_info(container_serial, {None: "value"}, None, "admin")
        self.assertTrue(res)
        container_info = get_container_info_dict(container_serial, user_role="admin")
        self.assertEqual(0, len(container_info))

    def test_24_delete_container_info(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "delete container info"})
        container = find_container_by_serial(container_serial)
        info = {"key1": "value1", "key2": "value2", "key3": "value3"}
        set_container_info(container_serial, info, None, "admin")

        # Delete non-existing key
        res = delete_container_info(container_serial, "non_existing_key", None, "admin")
        self.assertEqual(0, len(res))
        container_info = get_container_info_dict(container_serial, user_role="admin")
        self.assertEqual(3, len(container_info))

        # Delete existing key
        res = delete_container_info(container_serial, "key1", None, "admin")
        self.assertTrue(res["key1"])
        container_info = get_container_info_dict(container_serial, user_role="admin")
        self.assertEqual(2, len(container_info))
        self.assertNotIn("key1", container_info.keys())

        # Delete all keys
        res = delete_container_info(container_serial, user_role="admin")
        self.assertTrue(res["key2"])
        self.assertTrue(res["key3"])
        container_info = get_container_info_dict(container_serial, user_role="admin")
        self.assertEqual(0, len(container_info))

    def test_25_set_description(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "Initial description"})
        container = find_container_by_serial(container_serial)

        # Set empty description
        set_container_description(container_serial, description="", user_role="admin")
        self.assertEqual("", container.description)

        # Set description
        set_container_description(container_serial, description="new description", user_role="admin")
        self.assertEqual("new description", container.description)

        # Set None description
        set_container_description(container_serial, description=None, user_role="admin")
        self.assertEqual("", container.description)

    def test_26_set_states(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "Set states"})
        container = find_container_by_serial(container_serial)

        # check initial state
        states = container.get_states()
        self.assertEqual(1, len(states))
        self.assertIn("active", states)

        # Set state overwrites previous state
        res = set_container_states(container_serial, ["disabled", "lost"], user_role="admin")
        self.assertTrue(res["disabled"])
        self.assertTrue(res["lost"])
        states = container.get_states()
        self.assertEqual(2, len(states))
        self.assertIn("disabled", states)
        self.assertIn("lost", states)

        # Set empty state list: Shall delete all states
        res = set_container_states(container_serial, [], user_role="admin")
        self.assertEqual(0, len(res))
        states = container.get_states()
        self.assertEqual(0, len(states))

        # Set unknown state
        res = set_container_states(container_serial, ["unknown_state", "active"], user_role="admin")
        self.assertFalse(res["unknown_state"])
        self.assertTrue(res["active"])
        states = container.get_states()
        self.assertEqual(1, len(states))
        self.assertIn("active", states)

        # Set none is handled as empty list
        res = set_container_states(container_serial, None, user_role="admin")
        self.assertEqual(0, len(res))
        states = container.get_states()
        self.assertEqual(0, len(states))

        # Set excluded states
        self.assertRaises(ParameterError, set_container_states, container_serial, ["active", "disabled"],
                          user_role="admin")

    def test_27_add_states(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "Set states"})
        container = find_container_by_serial(container_serial)

        # Check initial state
        states = container.get_states()
        self.assertEqual(1, len(states))
        self.assertIn("active", states)

        # Add state
        res = add_container_states(container_serial, ["lost"], user_role="admin")
        self.assertTrue(res["lost"])
        states = container.get_states()
        self.assertEqual(2, len(states))
        self.assertIn("active", states)
        self.assertIn("lost", states)

        # Add empty state list: Changes nothing
        res = add_container_states(container_serial, [], user_role="admin")
        self.assertEqual(0, len(res))
        states = container.get_states()
        self.assertEqual(2, len(states))

        # Add None: Changes nothing
        container.add_states(None)
        states = container.get_states()
        self.assertEqual(2, len(states))

        # Add unknown state
        res = add_container_states(container_serial, ["unknown_state"], user_role="admin")
        self.assertFalse(res["unknown_state"])
        states = container.get_states()
        self.assertEqual(2, len(states))
        self.assertIn("active", states)
        self.assertIn("lost", states)

        # Add state that excludes old state: removes the old state
        res = add_container_states(container_serial, ["disabled"], user_role="admin")
        self.assertTrue(res["disabled"])
        states = container.get_states()
        self.assertEqual(2, len(states))
        self.assertIn("disabled", states)
        self.assertIn("lost", states)

        # Add two states that excludes each other: raises parameter error
        self.assertRaises(ParameterError, add_container_states, container_serial, ["active", "disabled"],
                          user_role="admin")

    def test_28_get_all_containers_paginate(self):
        # Removes all previously initialized containers
        old_test_containers = TokenContainer.query.all()
        for container in old_test_containers:
            container.delete()

        # Arrange
        types = ["Smartphone", "generic", "Yubikey", "Smartphone", "generic", "Yubikey"]
        self.setUp_user_realms()
        self.setUp_user_realm2()
        realms = ["realm1", "realm2", "realm1", "realm2", "realm1", "realm1"]
        container_serials = []
        for t, r in zip(types, realms):
            serial = init_container({"type": t, "description": "test container", "realm": r})
            container_serials.append(serial)

        # Filter for container serial
        container_data = get_all_containers(serial=container_serials[3], pagesize=15)
        self.assertEqual(1, container_data["count"])
        self.assertEqual(container_data["containers"][0].serial, container_serials[3])

        # Filter for non-existing serial
        container_data = get_all_containers(serial="non_existing_serial")
        self.assertEqual(0, len(container_data["containers"]))

        # Filter for type
        container_data = get_all_containers(ctype="generic", pagesize=15)
        for container in container_data["containers"]:
            self.assertEqual(container.type, "generic")
        self.assertEqual(2, container_data["count"])

        # Filter for non-existing type
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

        # Filter by realms
        container_data = get_all_containers(realms=["realm1"], pagesize=15)
        self.assertEqual(4, len(container_data["containers"]))
        for container in container_data["containers"]:
            self.assertEqual("realm1", container.realms[0].name)

        # Filter by user
        user_hans = User(login="hans", realm=self.realm1)
        assign_user(container_serials[1], user_hans, None, "admin")
        container_data = get_all_containers(user=user_hans, pagesize=15)
        self.assertEqual(1, len(container_data["containers"]))
        self.assertEqual(1, len(container_data["containers"][0].get_users()))
        self.assertEqual("hans", container_data["containers"][0].get_users()[0].login)

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

        # Sort by type ascending
        container_data = get_all_containers(sortby="type", sortdir="asc")
        self.assertEqual("generic", container_data["containers"][0].type)
        self.assertEqual("yubikey", container_data["containers"][-1].type)

        # Sort by serial descending
        container_data = get_all_containers(sortby="serial", sortdir="desc")
        self.assertEqual("YUBI", container_data["containers"][0].serial[:4])
        self.assertEqual("CONT", container_data["containers"][-1].serial[:4])

        # Sort for non-existing column: uses serial instead
        container_data = get_all_containers(sortby="random_column", sortdir="asc")
        self.assertEqual("CONT", container_data["containers"][0].serial[:4])
        self.assertEqual("YUBI", container_data["containers"][-1].serial[:4])

        # Non-existing sort direction: uses asc instead
        container_data = get_all_containers(sortby="type", sortdir="wrong_dir")
        self.assertEqual("generic", container_data["containers"][0].type)
        self.assertEqual("yubikey", container_data["containers"][-1].type)

    def test_29_gen_serial(self):
        # Test class prefix
        serial = _gen_serial(container_type="non_existing_type")
        self.assertEqual("CONT", serial[:4])

        serial = _gen_serial(container_type="generic")
        self.assertEqual("CONT", serial[:4])

        serial = _gen_serial(container_type="smartphone")
        self.assertEqual("SMPH", serial[:4])

        serial = _gen_serial(container_type="yubikey")
        self.assertEqual("YUBI", serial[:4])

        # Test length
        self.assertEqual(8 + len("YUBI"), len(serial))

        set_privacyidea_config("SerialLength", 12)
        serial = _gen_serial(container_type="generic")
        self.assertEqual(12 + len("CONT"), len(serial))

        set_privacyidea_config("SerialLength", -1)
        serial = _gen_serial(container_type="generic")
        self.assertEqual(8, len(serial))

        set_privacyidea_config("SerialLength", 8)

    def test_30_container_token_types(self):
        supported_token_types = get_container_token_types()
        container_types = supported_token_types.keys()
        # All classes are included
        self.assertIn("generic", container_types)
        self.assertIn("smartphone", container_types)
        self.assertIn("yubikey", container_types)
        self.assertEqual(3, len(container_types))

    def test_31_get_container_classes(self):
        container_classes = get_container_classes()
        container_types = container_classes.keys()
        # All classes are included
        self.assertIn("generic", container_types)
        self.assertIn("smartphone", container_types)
        self.assertIn("yubikey", container_types)
        self.assertEqual(3, len(container_types))

    def test_32_get_container_classes_description(self):
        container_classes = get_container_classes_descriptions()
        container_types = container_classes.keys()
        # All classes are included
        self.assertIn("generic", container_types)
        self.assertIn("smartphone", container_types)
        self.assertIn("yubikey", container_types)
        self.assertEqual(3, len(container_types))

    def test_33_check_user_access_on_container(self):
        self.setUp_user_realms()
        user = User(login="hans", realm=self.realm1)
        container_serial = init_container({"type": "generic", "user": user.login, "realm": user.realm})
        container = find_container_by_serial(container_serial)

        # Admin has access on container of users
        res = _check_user_access_on_container(container, User(), user_role="admin")
        self.assertTrue(res)

        # User has access on own container
        res = _check_user_access_on_container(container, user, user_role="user")
        self.assertTrue(res)

        # User has not access on another container
        another_container_serial = init_container({"type": "generic", "user": "root", "realm": self.realm1})
        another_container = find_container_by_serial(another_container_serial)
        self.assertRaises(PolicyError, _check_user_access_on_container, another_container, user, "user")

        # Pass empty user
        self.assertRaises(PolicyError, _check_user_access_on_container, container, None, "user")
        res = _check_user_access_on_container(container, None, user_role="admin")
        self.assertTrue(res)

        # Pass undefined user role raises Parameter error
        self.assertRaises(ParameterError, _check_user_access_on_container, container, user, "random")
