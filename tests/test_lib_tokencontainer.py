import base64
import json
from datetime import datetime, timezone

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey

from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.config import set_privacyidea_config
from privacyidea.lib.container import (delete_container_by_id, find_container_by_id, find_container_by_serial,
                                       init_container, get_all_containers, _gen_serial, find_container_for_token,
                                       delete_container_by_serial, get_container_classes_descriptions,
                                       get_container_token_types, add_container_info,
                                       _check_user_access_on_container, assign_user, set_container_realms,
                                       add_container_realms, get_container_info_dict,
                                       set_container_info, delete_container_info, set_container_description,
                                       set_container_states, add_container_states,
                                       remove_multiple_tokens_from_container, remove_token_from_container,
                                       add_multiple_tokens_to_container,
                                       add_token_to_container, create_endpoint_url)
from privacyidea.lib.container import get_container_classes
from privacyidea.lib.crypto import geturandom, generate_keypair_ecc, ecc_key_pair_to_b64url_str, sign_ecc, decrypt_ecc, \
    b64url_str_key_pair_to_ecc_obj, ecdh_key_exchange
from privacyidea.lib.error import (ResourceNotFoundError, ParameterError, EnrollmentError, UserError, PolicyError,
                                   TokenAdminError, privacyIDEAError)
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

    def register_smartphone_initialize_success(self, registration_url, passphrase_params=None):
        smartphone_serial = init_container({"type": "smartphone"})
        smartphone = find_container_by_serial(smartphone_serial)
        params = {"container_registration_url": registration_url}

        # passphrase
        if passphrase_params:
            params.update(passphrase_params)

        # Prepare
        result = smartphone.init_registration(params)

        result_entries = result.keys()
        self.assertIn("nonce", result_entries)
        self.assertIn("container_url", result_entries)
        self.assertIn("time_stamp", result_entries)
        self.assertIn("key_algorithm", result_entries)

        return smartphone_serial, result

    def mock_smartphone_register_params(self, nonce, registration_time, registration_url, serial, passphrase=None):
        message = f"{nonce}|{registration_time}|{registration_url}|{serial}"
        if passphrase:
            message += f"|{passphrase}"

        public_key_smph, private_key_smph = generate_keypair_ecc("secp384r1")
        pub_key_smph_str, _ = ecc_key_pair_to_b64url_str(public_key=public_key_smph)

        signature, hash_algorithm = sign_ecc(message.encode("utf-8"), private_key_smph, "sha256")

        params = {"signature": base64.b64encode(signature), "public_client_key": pub_key_smph_str}

        return params, private_key_smph

    def test_34_register_smartphone_init_fails(self):
        smartphone_serial = init_container({"type": "smartphone"})
        smartphone = find_container_by_serial(smartphone_serial)

        # Prepare with missing registration URL
        self.assertRaises(ParameterError, smartphone.init_registration, {})

    def test_35_register_smartphone_finalize_unauthorized(self):
        # Mock smartphone with guessed params (no prepare)
        smartphone_serial = init_container({"type": "smartphone"})
        smartphone = find_container_by_serial(smartphone_serial)
        registration_url = "http://test/container/register/finalize"
        nonce = geturandom(20, hex=True)
        time_stamp = datetime.now(timezone.utc)
        params, _ = self.mock_smartphone_register_params(nonce, time_stamp,
                                                         registration_url, smartphone_serial)

        # Try finalize registration
        self.assertRaises(privacyIDEAError, smartphone.finalize_registration, params)

        # Valid prepare
        registration_url = "http://test/container/register/finalize"
        passphrase_params = {"passphrase_ad": False, "passphrase_prompt": "Enter passphrase",
                             "passphrase_response": "top_secret"}
        smartphone_serial, init_results = self.register_smartphone_initialize_success(registration_url,
                                                                                      passphrase_params)
        smartphone = find_container_by_serial(smartphone_serial)

        # Mock smartphone with wrong nonce
        invalid_nonce = geturandom(20, hex=True)
        params, _ = self.mock_smartphone_register_params(invalid_nonce, init_results["time_stamp"],
                                                         registration_url, smartphone_serial)
        params.update({"container_registration_url": registration_url})

        # Try to finalize registration
        self.assertRaises(privacyIDEAError, smartphone.finalize_registration, params)

        # Mock smartphone with invalid public key
        params, _ = self.mock_smartphone_register_params(init_results["nonce"], init_results["time_stamp"],
                                                         registration_url, smartphone_serial)
        params.update({"container_registration_url": registration_url})
        public_key_smph, private_key_smph = generate_keypair_ecc("secp384r1")
        params["public_key"], _ = ecc_key_pair_to_b64url_str(public_key=public_key_smph)

        # Try finalize registration
        self.assertRaises(privacyIDEAError, smartphone.finalize_registration, params)

        # Mock smartphone with invalid passphrase
        params, _ = self.mock_smartphone_register_params(init_results["nonce"], init_results["time_stamp"],
                                                         registration_url, smartphone_serial,
                                                         "different_secret")
        params.update({"container_registration_url": registration_url})

        # Try to finalize registration
        self.assertRaises(privacyIDEAError, smartphone.finalize_registration, params)

    def test_36_register_smartphone_terminate(self):
        # container is not registered
        smartphone_serial = init_container({"type": "smartphone"})
        smartphone = find_container_by_serial(smartphone_serial)
        smartphone.terminate_registration()

        # check container_info is empty
        container_info = smartphone.get_container_info_dict()
        self.assertEqual(4, len(container_info))
        self.assertIn("key_algorithm", container_info.keys())
        self.assertIn("hash_algorithm", container_info.keys())
        self.assertIn("encrypt_algorithm", container_info.keys())
        self.assertIn("encrypt_algorithm", container_info.keys())

    def test_37_register_smartphone_success(self):
        # Prepare
        registration_url = "http://test/container/register/finalize"
        smartphone_serial, init_result = self.register_smartphone_initialize_success(registration_url)
        smartphone = find_container_by_serial(smartphone_serial)

        # Mock smartphone
        params, priv_sig_key_smph = self.mock_smartphone_register_params(init_result["nonce"],
                                                                         init_result["time_stamp"],
                                                                         registration_url, smartphone_serial)
        params.update({"container_registration_url": registration_url})

        # Finalize registration
        res = smartphone.finalize_registration(params)
        self.assertIn("public_server_key", res.keys())

        # Check if container info is set correctly
        container_info = smartphone.get_container_info_dict()
        container_info_keys = container_info.keys()
        self.assertIn("public_key_container", container_info_keys)
        self.assertIn("public_key_server", container_info_keys)
        self.assertIn("private_key_server", container_info_keys)
        self.assertNotEqual("", container_info["public_key_container"], container_info["public_key_server"])

        return smartphone_serial, priv_sig_key_smph

    def test_38_register_terminate_smartphone_success(self):
        smartphone_serial, _ = self.test_37_register_smartphone_success()
        smartphone = find_container_by_serial(smartphone_serial)

        # Terminate registration
        smartphone.terminate_registration()
        # Check that the container info is deleted
        container_info = smartphone.get_container_info_dict()
        container_info_keys = container_info.keys()
        self.assertNotIn("public_key_container", container_info_keys)
        self.assertNotIn("public_key_server", container_info_keys)
        self.assertNotIn("private_key_server", container_info_keys)

    def test_39_register_smartphone_passphrase_success(self):
        # Prepare
        registration_url = "http://test/container/register/finalize"
        passphrase_params = {"passphrase_ad": False, "passphrase_prompt": "Enter passphrase",
                             "passphrase_response": "top_secret"}
        smartphone_serial, init_result = self.register_smartphone_initialize_success(registration_url,
                                                                                     passphrase_params)
        smartphone = find_container_by_serial(smartphone_serial)

        # Check that passphrase is included in the challenge
        challenge = get_challenges(serial=smartphone_serial)[0]
        challenge_data = json.loads(challenge.data)
        self.assertEqual(passphrase_params["passphrase_response"], challenge_data["passphrase_response"])

        # Mock smartphone
        params, _ = self.mock_smartphone_register_params(init_result["nonce"], init_result["time_stamp"],
                                                         registration_url, smartphone_serial,
                                                         passphrase_params["passphrase_response"])
        params.update({"container_registration_url": registration_url})

        # Finalize registration
        res = smartphone.finalize_registration(params)
        self.assertIn("public_server_key", res.keys())

        # Check if container info is set correctly
        container_info = smartphone.get_container_info_dict()
        container_info_keys = container_info.keys()
        self.assertIn("public_key_container", container_info_keys)
        self.assertIn("public_key_server", container_info_keys)
        self.assertIn("private_key_server", container_info_keys)

    def test_40_reinit_registration_invalidates_old_challenge(self):
        # First init
        registration_url = "http://test/container/register/finalize"
        smartphone_serial, init_result_old = self.register_smartphone_initialize_success(registration_url)
        smartphone = find_container_by_serial(smartphone_serial)

        # second init
        init_result_new = smartphone.init_registration(
            {"container_serial": smartphone_serial, "container_registration_url": registration_url})

        # Finalize with old init data
        params, _ = self.mock_smartphone_register_params(init_result_old["nonce"], init_result_old["time_stamp"],
                                                         registration_url, smartphone_serial)
        params.update({"container_registration_url": registration_url})
        self.assertRaises(privacyIDEAError, smartphone.finalize_registration, params)

        # Finalize with new init data
        params, _ = self.mock_smartphone_register_params(init_result_new["nonce"], init_result_new["time_stamp"],
                                                         registration_url, smartphone_serial)
        params.update({"container_registration_url": registration_url})

        # Finalize registration
        res = smartphone.finalize_registration(params)
        self.assertIn("public_server_key", res.keys())

    def test_41_create_container_challenge(self):
        container_serial = init_container({"type": "smartphone"})
        container = find_container_by_serial(container_serial)

        res = container.create_challenge({})
        self.assertIn("nonce", res.keys())
        self.assertIn("time_stamp", res.keys())

        # check challenge
        challenge = get_challenges(serial=container_serial)[0]
        self.assertEqual(res["nonce"], challenge.challenge)
        self.assertEqual(res["time_stamp"], challenge.timestamp.replace(tzinfo=timezone.utc).isoformat())

    def test_42_create_endpoint_url(self):
        correct_url = "https://pi/test/endpoint"
        # simple concat
        endpoint = create_endpoint_url("https://pi/", "test/endpoint")
        self.assertEqual(correct_url, endpoint)

        # base url without /
        endpoint = create_endpoint_url("https://pi", "test/endpoint")
        self.assertEqual(correct_url, endpoint)

        # endpoint already included in base url
        endpoint = create_endpoint_url("https://pi/test/endpoint", "test/endpoint")
        self.assertEqual(correct_url, endpoint)

    def mock_smartphone_sync(self, params, serial, private_key_sig_smph, client_container=None):
        nonce = params["nonce"]
        time_stamp = params["time_stamp"]
        scope = params["container_sync_url"]

        public_key_enc_smph, private_enc_key_smph = generate_keypair_ecc("x25519")
        pub_key_enc_smph_str = base64.urlsafe_b64encode(public_key_enc_smph.public_bytes_raw()).decode('utf-8')

        message = f"{nonce}|{time_stamp}|{serial}|{scope}|{pub_key_enc_smph_str}"
        if client_container:
            message += f"|{json.dumps(client_container)}"
        signature, hash_algorithm = sign_ecc(message.encode("utf-8"), private_key_sig_smph, "sha256")

        params = {"signature": base64.b64encode(signature), "public_enc_key_client": pub_key_enc_smph_str}
        if client_container:
            params.update({"container_dict_client": json.dumps(client_container)})
        return params, private_enc_key_smph

    def test_43_init_synchronize_smartphone_success(self):
        smartphone_serial = init_container({"type": "smartphone"})
        smartphone = find_container_by_serial(smartphone_serial)

        params = {"scope": "container/synchronize/finalize"}
        result = smartphone.init_sync(params)
        result_entries = result.keys()
        self.assertIn("nonce", result_entries)
        self.assertIn("time_stamp", result_entries)
        self.assertIn("key_algorithm", result_entries)

        # check challenge
        challenge = get_challenges(serial=smartphone_serial)[0]
        self.assertEqual(result["nonce"], challenge.challenge)
        self.assertEqual(result["time_stamp"], challenge.timestamp.replace(tzinfo=timezone.utc).isoformat())
        data = json.loads(challenge.data)
        self.assertEqual(params["scope"], data["scope"])

    def test_44_init_synchronize_smartphone_fail(self):
        smartphone_serial = init_container({"type": "smartphone"})
        smartphone = find_container_by_serial(smartphone_serial)

        self.assertRaises(ParameterError, smartphone.init_sync, {})

    def test_45_finalize_synchronize_smartphone_success(self):
        # Registration
        smartphone_serial, priv_sig_key_smph = self.test_37_register_smartphone_success()
        smartphone = find_container_by_serial(smartphone_serial)

        # Init sync
        params = {"scope": f"container/sync/{smartphone_serial}/finalize"}
        init_result = smartphone.init_sync(params)
        result_entries = init_result.keys()
        self.assertIn("nonce", result_entries)
        self.assertIn("time_stamp", result_entries)
        self.assertIn("key_algorithm", result_entries)

        # Mock smartphone
        init_result.update({'container_sync_url': params["scope"]})
        smph_params, _ = self.mock_smartphone_sync(init_result, smartphone_serial, priv_sig_key_smph)

        # Finalize sync
        smph_params.update({'scope': params["scope"]})
        res = smartphone.finalize_sync(smph_params)
        self.assertEqual("AES", res["encryption_algorithm"])
        self.assertIn("encryption_params", res.keys())
        self.assertIn("public_server_key", res.keys())
        self.assertIn("container_dict_server", res.keys())

    def test_46_finalize_synchronize_smartphone_with_tokens(self):
        # Registration
        smartphone_serial, priv_sig_key_smph = self.test_37_register_smartphone_success()
        smartphone = find_container_by_serial(smartphone_serial)

        # tokens
        hotp_server_token = init_token({"genkey": "1", "type": "hotp", "otplen": 8, "hashlib": "sha256"})
        hotp_token = init_token({"genkey": "1", "type": "hotp"})
        _, _, otp_dict = hotp_token.get_multi_otp(2)
        hotp_otps = list(otp_dict["otp"].values())
        totp_token = init_token({"genkey": "1", "type": "totp"})
        # the function uses the local time, hence we have to pass the utc time
        time_now = datetime.now(timezone.utc)
        _, _, otp_dict = totp_token.get_multi_otp(2, curTime=time_now)
        totp_otps = [otp["otpval"] for otp in list(otp_dict["otp"].values())]

        smartphone.add_token(hotp_server_token)
        smartphone.add_token(totp_token)

        # Init sync
        params = {"scope": f"container/sync/{smartphone_serial}/finalize"}
        init_result = smartphone.init_sync(params)
        result_entries = init_result.keys()
        self.assertIn("nonce", result_entries)
        self.assertIn("time_stamp", result_entries)
        self.assertIn("key_algorithm", result_entries)

        # Mock smartphone
        init_result.update({'container_sync_url': params["scope"]})
        # In the first step the smph does not know the container. hence it only sends the token infos
        random_otp = "123456"
        client_container = {"tokens": [{"type": "hotp", "otp": hotp_otps}, {"type": "totp", "otp": totp_otps},
                                       {"type": "hotp", "otp": [random_otp]}]}
        smph_params, priv_enc_key_smph = self.mock_smartphone_sync(init_result, smartphone_serial, priv_sig_key_smph,
                                                                   client_container)

        # Finalize sync
        smph_params.update({'scope': params["scope"]})
        res = smartphone.finalize_sync(smph_params)
        self.assertEqual("AES", res["encryption_algorithm"])
        self.assertIn("encryption_params", res.keys())
        self.assertIn("public_server_key", res.keys())
        self.assertIn("container_dict_server", res.keys())

        # check container dict results
        container_dict_enc = res["container_dict_server"]
        # decrypt container info
        pub_key_server = X25519PublicKey.from_public_bytes(base64.urlsafe_b64decode(res["public_server_key"]))
        session_key = ecdh_key_exchange(priv_enc_key_smph, pub_key_server)
        container_dict_enc = decrypt_ecc(container_dict_enc, session_key, "", res["encryption_params"])
        container_dict = json.loads(container_dict_enc)

        # check entries
        container_details = container_dict["container"]
        self.assertIn("active", container_details["states"])
        # tokens
        token_details = container_dict["tokens"]
        add_tokens = token_details["add"]
        self.assertEqual(1, len(add_tokens))
        self.assertIn(hotp_server_token.get_serial(), add_tokens[0])
        update_tokens = token_details["update"]
        self.assertEqual(1, len(update_tokens))
        self.assertEqual(totp_token.get_serial(), update_tokens[0]["serial"])
        self.assertTrue(update_tokens[0]["active"])

    def test_47_synchronize_without_registration(self):
        smartphone_serial = init_container({"type": "smartphone"})
        smartphone = find_container_by_serial(smartphone_serial)

        # Init sync
        params = {"scope": f"container/sync/{smartphone_serial}/finalize"}
        init_result = smartphone.init_sync(params)

        # Mock smartphone
        init_result.update({'container_sync_url': params["scope"]})
        _, priv_sig_key_smph = generate_keypair_ecc("secp384r1")
        smph_params, _ = self.mock_smartphone_sync(init_result, smartphone_serial, priv_sig_key_smph)

        # Finalize sync
        smph_params.update({'scope': params["scope"]})
        self.assertRaises(privacyIDEAError, smartphone.finalize_sync, smph_params)

    def test_48_synchronize_with_invalid_signature(self):
        # Registration
        smartphone_serial, priv_sig_key_smph = self.test_37_register_smartphone_success()
        smartphone = find_container_by_serial(smartphone_serial)

        # Init sync
        params = {"scope": f"container/sync/{smartphone_serial}/finalize"}
        init_result = smartphone.init_sync(params)
        result_entries = init_result.keys()
        self.assertIn("nonce", result_entries)
        self.assertIn("time_stamp", result_entries)
        self.assertIn("key_algorithm", result_entries)

        # Mock smartphone with another serial
        init_result.update({'container_sync_url': params["scope"]})
        smph_params, _ = self.mock_smartphone_sync(init_result, "SMPH9999", priv_sig_key_smph)

        # Finalize sync
        smph_params.update({'scope': params["scope"]})
        self.assertRaises(privacyIDEAError, smartphone.finalize_sync, smph_params)

    def test_49_synchronize_container_details(self):
        # Arrange
        smartphone_serial = init_container({"type": "smartphone"})
        smartphone = find_container_by_serial(smartphone_serial)
        hotp_token = init_token({"genkey": True, "type": "hotp"})
        _, _, otp_dict = hotp_token.get_multi_otp(2)
        hotp_otps = list(otp_dict["otp"].values())
        totp_token = init_token({"genkey": True, "type": "totp"})

        smartphone.add_token(hotp_token)
        smartphone.add_token(totp_token)

        # clients tokens with different properties
        client_container = {"container": {"states": ["active"]},
                            "tokens": [{"serial": totp_token.get_serial(), "active": True}, {"otp": hotp_otps}]}

        # manipulate container and tokens in the meantime
        smartphone.set_states(["lost"])
        totp_token.enable(False)

        # synchronize details
        synced_container_details = smartphone.synchronize_container_details(client_container)

        # check container details
        self.assertEqual("lost", synced_container_details["container"]["states"][0])
        # check tokens
        add_tokens = synced_container_details["tokens"]["add"]
        self.assertEqual(0, len(add_tokens))
        updated_tokens = synced_container_details["tokens"]["update"]
        for token in updated_tokens:
            self.assertIn(token["serial"], [hotp_token.get_serial(), totp_token.get_serial()])
            if token["serial"] == hotp_token.get_serial():
                self.assertTrue(token["active"])
            elif token["serial"] == totp_token.get_serial():
                self.assertFalse(token["active"])

        # Pass empty client container
        synced_container_details = smartphone.synchronize_container_details({})
        # check tokens
        add_tokens = synced_container_details["tokens"]["add"]
        self.assertEqual(2, len(add_tokens))
