import base64
import json
from datetime import datetime, timezone, timedelta

import mock

from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.config import set_privacyidea_config
from privacyidea.lib.container import (delete_container_by_id, find_container_by_id, find_container_by_serial,
                                       init_container, get_all_containers, _gen_serial, find_container_for_token,
                                       delete_container_by_serial, get_container_classes_descriptions,
                                       get_container_token_types, add_container_info,
                                       assign_user, set_container_realms,
                                       add_container_realms, get_container_info_dict,
                                       set_container_info, delete_container_info, set_container_description,
                                       set_container_states, add_container_states,
                                       remove_multiple_tokens_from_container, remove_token_from_container,
                                       add_multiple_tokens_to_container,
                                       add_token_to_container, create_endpoint_url, create_container_template,
                                       get_templates_by_query, get_template_obj,
                                       create_container_template_from_db_object, compare_template_dicts,
                                       set_default_template, compare_template_with_container,
                                       finalize_registration, finalize_container_rollover, init_container_rollover,
                                       unassign_user)
from privacyidea.lib.container import get_container_classes, unregister
from privacyidea.lib.containerclass import TokenContainerClass
from privacyidea.lib.containers.container_info import TokenContainerInfoData, PI_INTERNAL, RegistrationState
from privacyidea.lib.containers.smartphone import SmartphoneOptions, SmartphoneContainer
from privacyidea.lib.containers.yubikey import YubikeyContainer
from privacyidea.lib.containertemplate.containertemplatebase import ContainerTemplateBase
from privacyidea.lib.containertemplate.smartphonetemplate import SmartphoneContainerTemplate
from privacyidea.lib.containertemplate.yubikeytemplate import YubikeyContainerTemplate
from privacyidea.lib.crypto import (geturandom, generate_keypair_ecc, ecc_key_pair_to_b64url_str, sign_ecc,
                                    decryptPassword, KeyPair)
from privacyidea.lib.error import (ResourceNotFoundError, ParameterError, EnrollmentError, UserError,
                                   TokenAdminError, ContainerInvalidChallenge, ContainerNotRegistered, PolicyError)
from privacyidea.lib.token import init_token, remove_token
from privacyidea.lib.user import User
from privacyidea.models import TokenContainer, Token, TokenContainerTemplate
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
        serial = init_container({"type": "generic",
                                 "container_serial": self.empty_container_serial,
                                 "description": "test container"})["container_serial"]
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
                                 "realm": self.realm1})["container_serial"]
        container = find_container_by_serial(serial)
        self.assertEqual(self.realm1, container.realms[0].name)
        self.assertEqual("hans", container.get_users()[0].login)
        self.assertIn("creation_date", container.get_container_info_dict().keys())

        # Init smartphone container with realm
        serial = init_container({"type": "smartphone",
                                 "container_serial": self.smartphone_serial,
                                 "realm": self.realm1})["container_serial"]
        smartphone = find_container_by_serial(serial)
        self.assertEqual(self.realm1, smartphone.realms[0].name)
        self.assertEqual("smartphone", smartphone.type)
        self.assertIn("creation_date", smartphone.get_container_info_dict().keys())

        # Init yubikey container
        serial = init_container({"type": "yubikey", "container_serial": self.yubikey_serial})["container_serial"]
        yubikey = find_container_by_serial(serial)
        self.assertEqual(self.yubikey_serial, serial)
        self.assertIn("creation_date", yubikey.get_container_info_dict().keys())

        # Check creation Date
        create_now = datetime.now(tz=timezone.utc)
        with mock.patch("privacyidea.lib.container.datetime", wraps=datetime) as mock_datetime:
            mock_datetime.now.return_value = create_now
            container_serial = init_container({"type": "generic"})["container_serial"]
        container = find_container_by_serial(container_serial)
        self.assertEqual(create_now.isoformat(timespec="seconds"),
                         container.get_container_info_dict().get("creation_date"))

    def test_02_create_container_fails(self):
        # Unknown container type raises exception
        self.assertRaises(EnrollmentError, init_container, {"type": "doesnotexist"})
        # Empty container type raises exception
        self.assertRaises(EnrollmentError, init_container, {})

        # create container with existing serial
        serial = init_container({"type": "generic"})["container_serial"]
        self.assertRaises(EnrollmentError, init_container, {"type": "generic", "container_serial": serial})

    def test_03_create_container_wrong_user_parameters(self):
        # Init container with user: User shall not be assigned (realm required)
        serial = init_container({"type": "Generic", "user": "hans"})["container_serial"]
        container = find_container_by_serial(serial)
        self.assertEqual(0, len(container.realms))
        self.assertEqual(0, len(container.get_users()))

        # Init with non-existing user
        serial = init_container({"type": "Generic", "user": "random", "realm": "random"})["container_serial"]
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
        res = add_multiple_tokens_to_container(self.generic_serial, gen_token_serials)
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
        res = add_token_to_container(self.smartphone_serial, self.totp_serial_smph)
        self.assertTrue(res)
        # Check if token is added to container
        smartphone = find_container_by_serial(self.smartphone_serial)
        tokens = smartphone.get_tokens()
        self.assertEqual(1, len(tokens))
        self.assertIn(self.totp_serial_smph, tokens[0].get_serial())

        # Try to add the same token again to the container
        res = add_token_to_container(self.smartphone_serial, self.totp_serial_smph)
        self.assertFalse(res)
        tokens = smartphone.get_tokens()
        self.assertEqual(1, len(tokens))
        self.assertIn(self.totp_serial_smph, tokens[0].get_serial())

        # Yubikey
        init_token({"type": "hotp", "genkey": "1", "serial": self.hotp_serial_yubi})
        res = add_token_to_container(self.yubikey_serial, self.hotp_serial_yubi)
        self.assertTrue(res)
        # Check if token is added to container
        yubikey = find_container_by_serial(self.yubikey_serial)
        tokens = yubikey.get_tokens()
        self.assertEqual(1, len(tokens))
        self.assertIn(self.hotp_serial_yubi, tokens[0].get_serial())

    def test_06_add_token_to_another_container(self):
        # Add HOTP token from the generic container to the smartphone
        res = add_token_to_container(self.smartphone_serial, self.hotp_serial_gen)
        self.assertTrue(res)
        # Check containers: Token is only in smartphone container
        db_result = TokenContainer.query.join(Token.container).filter(Token.serial == self.hotp_serial_gen)
        container_serials = [row.serial for row in db_result]
        self.assertEqual(1, len(container_serials))
        self.assertEqual(self.smartphone_serial, container_serials[0])

    def test_07_add_wrong_token_types_to_container(self):
        # Smartphone
        spass_token = init_token({"type": "spass"})
        self.assertRaises(ParameterError, add_token_to_container, self.smartphone_serial, spass_token.get_serial())

        # Yubikey
        totp_token = init_token({"type": "totp", "otpkey": "1"})
        self.assertRaises(ParameterError, add_token_to_container, self.yubikey_serial, totp_token.get_serial())

        # Add multiple tokens does not raise exception
        spass_token = init_token({"type": "spass"})
        hotp_token = init_token({"type": "hotp", "genkey": "1"})
        res = add_multiple_tokens_to_container(self.smartphone_serial,
                                               [spass_token.get_serial(), hotp_token.get_serial()])
        self.assertFalse(res[spass_token.get_serial()])
        self.assertTrue(res[hotp_token.get_serial()])

    def test_08_add_token_to_container_fails(self):
        # Single non-existing token
        self.assertRaises(ResourceNotFoundError, add_token_to_container, self.smartphone_serial, "non_existing_token")

        # Add multiple tokens with non-existing token to container
        token = init_token({"type": "hotp", "genkey": "1"})
        result = add_multiple_tokens_to_container(self.smartphone_serial, ["non_existing_token", token.get_serial()])
        self.assertFalse(result["non_existing_token"])
        self.assertTrue(result[token.get_serial()])

        # Add single token which is already in the container
        result = add_token_to_container(self.smartphone_serial, self.totp_serial_smph)
        self.assertFalse(result)

        # Add multiple tokens with one token that is already in the container
        result = add_multiple_tokens_to_container(self.smartphone_serial,
                                                  [self.totp_serial_smph, self.hotp_serial_yubi])
        self.assertFalse(result[self.totp_serial_smph])
        self.assertTrue(result[self.hotp_serial_yubi])

    def test_09_remove_multiple_tokens_from_container_success(self):
        generic_token_serials = [self.totp_serial_gen, self.spass_serial_gen]
        result = remove_multiple_tokens_from_container(self.generic_serial, generic_token_serials)
        self.assertTrue(result[self.totp_serial_gen])
        self.assertTrue(result[self.spass_serial_gen])
        # Check tokens of container
        container = find_container_by_serial(self.generic_serial)
        generic_tokens = [token.get_serial() for token in container.get_tokens()]
        self.assertNotIn(self.totp_serial_gen, generic_tokens)
        self.assertNotIn(self.spass_serial_gen, generic_tokens)

    def test_10_remove_token_from_container_success(self):
        result = remove_token_from_container(self.smartphone_serial, self.totp_serial_smph)
        self.assertTrue(result)
        container = find_container_by_serial(self.smartphone_serial)
        smartphone_tokens = [token.get_serial() for token in container.get_tokens()]
        self.assertNotIn(self.totp_serial_smph, smartphone_tokens)

    def test_11_remove_token_from_container_fails(self):
        # Remove non-existing token from container
        self.assertRaises(ResourceNotFoundError, remove_token_from_container, self.smartphone_serial,
                          "non_existing_token")

        # Remove token that is not in the container
        result = remove_token_from_container(self.generic_serial, self.hotp_serial_yubi)
        self.assertFalse(result)

        # Pass no token serial
        self.assertRaises(ResourceNotFoundError, remove_token_from_container, self.smartphone_serial, None)

        # Pass non-existing container serial
        self.assertRaises(ResourceNotFoundError, remove_token_from_container,
                          container_serial="non_existing_container",
                          token_serial=self.hotp_serial_gen)

    def test_12_remove_multiple_tokens_from_container_fails(self):
        # Remove non-existing tokens from container
        result = remove_multiple_tokens_from_container(self.generic_serial, ["non_existing_token", "random"])
        self.assertFalse(result["non_existing_token"])
        self.assertFalse(result["random"])

        # Remove token that is not in the container
        result = remove_multiple_tokens_from_container(self.generic_serial,
                                                       [self.hotp_serial_yubi, self.totp_serial_smph])
        self.assertFalse(result[self.hotp_serial_yubi])
        self.assertFalse(result[self.totp_serial_smph])

        # Pass empty token serial list
        result = remove_multiple_tokens_from_container(self.generic_serial, [])
        self.assertEqual(0, len(result))

        # Pass non-existing container serial
        self.assertRaises(ResourceNotFoundError, remove_multiple_tokens_from_container,
                          container_serial="non_existing_container",
                          token_serials=[self.hotp_serial_gen])

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
        container_serial = init_container({"type": "generic"})["container_serial"]
        add_token_to_container(container_serial, token.get_serial())
        container_result = find_container_for_token(token.get_serial())
        self.assertEqual(container_serial, container_result.serial)

        # Call with non-existing token serial
        self.assertRaises(ResourceNotFoundError, find_container_for_token, "non_existing_token")

    def test_15_delete_container_by_id(self):
        # Fail
        self.assertRaises(ParameterError, delete_container_by_id, None)
        self.assertRaises(ResourceNotFoundError, delete_container_by_id, 11)

        # Success
        container = find_container_by_serial(self.yubikey_serial)
        container_id = container._db_container.id
        result = delete_container_by_id(container_id)
        self.assertEqual(container_id, result)

    def test_16_delete_container_by_serial(self):
        # Fail
        self.assertRaises(ParameterError, delete_container_by_serial, None)
        self.assertRaises(ResourceNotFoundError, delete_container_by_serial, "non_existing_serial")

        # Success
        container_id = delete_container_by_serial(self.generic_serial)
        self.assertGreater(container_id, 0)
        self.assertRaises(ResourceNotFoundError, find_container_by_serial, self.generic_serial)
        container_id = delete_container_by_serial(self.smartphone_serial)
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
        serial = "CONT0001"
        init_container({"type": "generic", "container_serial": serial})
        # Find by serial exact
        container = find_container_by_serial("CONT0001")
        self.assertEqual(serial, container.serial)

        # find by serial in lower cases
        container = find_container_by_serial("cont0001")
        self.assertEqual(serial, container.serial)

        # Find by ID
        container = find_container_by_id(container._db_container.id)
        self.assertEqual(serial, container.serial)

    def test_19_set_realms(self):
        # Arrange
        self.setUp_user_realms()
        self.setUp_user_realm2()
        container_serial = init_container({"type": "generic", "description": "Set Realm Container"})["container_serial"]
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
        container_serial = init_container({"type": "generic", "description": "test container"})["container_serial"]
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

    def test_21_assign_unassign_user(self):
        # Arrange
        self.setUp_user_realms()
        container_serial = init_container({"type": "generic", "description": "assign user"})["container_serial"]
        container = find_container_by_serial(container_serial)
        user_hans = User(login="hans", realm=self.realm1, resolver=self.resolvername1)
        user_root = User(login="root", realm=self.realm1, resolver=self.resolvername1)
        invalid_user = User(login="invalid", realm="invalid")

        # Assign user
        result = assign_user(container_serial, user_hans)
        users = container.get_users()
        self.assertTrue(result)
        self.assertEqual(1, len(users))
        self.assertEqual("hans", users[0].login)
        self.assertEqual(self.realm1, container.realms[0].name)

        # Assigning another user fails
        self.assertRaises(TokenAdminError, assign_user, container_serial, user_root)

        # Unassign user
        success = unassign_user(container_serial, user_hans)
        self.assertTrue(success)

        # Assigning an invalid user raises exception
        self.assertRaises(UserError, assign_user, container_serial, invalid_user)

        # Unassigning an invalid user with the user id and resolver should work
        invalid_user = User(login="invalid", uid="123", realm=self.realm1, resolver=self.resolvername1)
        assign_user(container_serial, invalid_user)
        success = unassign_user(container_serial, invalid_user)
        self.assertTrue(success)

        # Unassign an invalid user without providing the user id and without resolver raises an Exception
        assign_user(container_serial, invalid_user)
        invalid_user = User(login="invalid", realm=self.realm1)
        self.assertRaises(UserError, unassign_user, container_serial, invalid_user)

        container.delete()

    def test_22_add_container_info(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "add container info"})["container_serial"]

        # Add container info
        add_container_info(container_serial, "key1", "value1")
        container_info = get_container_info_dict(container_serial)
        self.assertEqual("value1", container_info["key1"])

        # Add second info does not overwrite first info
        add_container_info(container_serial, "key2", "value2")
        container_info = get_container_info_dict(container_serial)
        self.assertEqual("value1", container_info["key1"])
        self.assertEqual("value2", container_info["key2"])

        # Pass no key changes nothing
        add_container_info(container_serial, "key2", "value2")
        container_info = get_container_info_dict(container_serial)
        self.assertEqual("value1", container_info["key1"])
        self.assertEqual("value2", container_info["key2"])

        # Pass no value sets empty value
        add_container_info(container_serial, "key", None)
        container_info = get_container_info_dict(container_serial)
        self.assertEqual("", container_info["key"])

        # Try to modify internal info raises exception
        container = find_container_by_serial(container_serial)
        container.update_container_info(
            [TokenContainerInfoData(key="public_server_key", value="123456789", info_type=PI_INTERNAL)])
        self.assertRaises(PolicyError, add_container_info, container_serial, "public_server_key", "000000000")

    def test_23_set_container_info(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "add container info"})["container_serial"]

        # Set container info
        res = set_container_info(container_serial, {"key1": "value1"})
        self.assertTrue(res["key1"])
        container_info = get_container_info_dict(container_serial)
        self.assertEqual("value1", container_info["key1"])
        container_info = get_container_info_dict(container_serial, ikey="key1")
        self.assertEqual("value1", container_info["key1"])

        # Set second info overwrites first info
        res = set_container_info(container_serial, {"key2": "value2"})
        self.assertTrue(res["key2"])
        container_info = get_container_info_dict(container_serial)
        self.assertEqual("value2", container_info["key2"])
        self.assertNotIn("key1", container_info.keys())
        container_info = get_container_info_dict(container_serial, ikey="key1")
        self.assertIsNone(container_info["key1"])

        # Pass no info only deletes old entries, but not internal entries
        res = set_container_info(container_serial, {})
        self.assertDictEqual({}, res)
        container_info = get_container_info_dict(container_serial)
        self.assertEqual(1, len(container_info))
        self.assertIn("creation_date", container_info.keys())

        # Pass no value
        res = set_container_info(container_serial, {"key": None})
        self.assertTrue(res["key"])
        container_info = get_container_info_dict(container_serial)
        self.assertEqual("", container_info["key"])

        # Try to set internal info
        container = find_container_by_serial(container_serial)
        container.update_container_info(
            [TokenContainerInfoData(key="public_server_key", value="123456", info_type=PI_INTERNAL)])
        res = set_container_info(container_serial, {"public_server_key": "0000", "key": "value"})
        self.assertFalse(res["public_server_key"])
        self.assertTrue(res["key"])
        container_info = get_container_info_dict(container_serial)
        self.assertEqual("123456", container_info["public_server_key"])
        self.assertEqual("value", container_info["key"])

    def test_24_delete_container_info(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "delete container info"})[
            "container_serial"]
        container = find_container_by_serial(container_serial)
        info = {"key1": "value1", "key2": "value2", "key3": "value3"}
        set_container_info(container_serial, info)

        # Delete non-existing key
        res = delete_container_info(container_serial, "non_existing_key")
        self.assertFalse(res["non_existing_key"])
        container_info = get_container_info_dict(container_serial)
        self.assertEqual(4, len(container_info))

        # Delete existing key
        res = delete_container_info(container_serial, "key1")
        self.assertTrue(res["key1"])
        container_info = get_container_info_dict(container_serial)
        self.assertEqual(3, len(container_info))
        self.assertNotIn("key1", container_info.keys())

        # Delete all keys
        res = delete_container_info(container_serial)
        self.assertTrue(res["key2"])
        self.assertTrue(res["key3"])
        container_info = get_container_info_dict(container_serial)
        self.assertEqual(1, len(container_info))
        self.assertIn("creation_date", container_info)

        # Try to delete internal info key
        container.update_container_info(
            [TokenContainerInfoData(key="public_server_key", value="123456789", info_type=PI_INTERNAL)])
        res = delete_container_info(container_serial, "public_server_key")
        self.assertDictEqual({"public_server_key": False}, res)
        res = delete_container_info(container_serial)
        self.assertDictEqual({"public_server_key": False, "creation_date": False}, res)

    def test_25_set_description(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "Initial description"})["container_serial"]
        container = find_container_by_serial(container_serial)

        # Set empty description
        set_container_description(container_serial, description="")
        self.assertEqual("", container.description)

        # Set description
        set_container_description(container_serial, description="new description")
        self.assertEqual("new description", container.description)

        # Set None description
        set_container_description(container_serial, description=None)
        self.assertEqual("", container.description)

    def test_26_set_states(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "Set states"})["container_serial"]
        container = find_container_by_serial(container_serial)

        # check initial state
        states = container.get_states()
        self.assertEqual(1, len(states))
        self.assertIn("active", states)

        # Set state overwrites previous state
        res = set_container_states(container_serial, ["disabled", "lost"])
        self.assertTrue(res["disabled"])
        self.assertTrue(res["lost"])
        states = container.get_states()
        self.assertEqual(2, len(states))
        self.assertIn("disabled", states)
        self.assertIn("lost", states)

        # Set empty state list: Shall delete all states
        res = set_container_states(container_serial, [])
        self.assertEqual(0, len(res))
        states = container.get_states()
        self.assertEqual(0, len(states))

        # Set unknown state
        res = set_container_states(container_serial, ["unknown_state", "active"])
        self.assertFalse(res["unknown_state"])
        self.assertTrue(res["active"])
        states = container.get_states()
        self.assertEqual(1, len(states))
        self.assertIn("active", states)

        # Set none is handled as empty list
        res = set_container_states(container_serial, None)
        self.assertEqual(0, len(res))
        states = container.get_states()
        self.assertEqual(0, len(states))

        # Set excluded states
        self.assertRaises(ParameterError, set_container_states, container_serial, ["active", "disabled"])

    def test_27_add_states(self):
        # Arrange
        container_serial = init_container({"type": "generic", "description": "Set states"})["container_serial"]
        container = find_container_by_serial(container_serial)

        # Check initial state
        states = container.get_states()
        self.assertEqual(1, len(states))
        self.assertIn("active", states)

        # Add state
        res = add_container_states(container_serial, ["lost"])
        self.assertTrue(res["lost"])
        states = container.get_states()
        self.assertEqual(2, len(states))
        self.assertIn("active", states)
        self.assertIn("lost", states)

        # Add empty state list: Changes nothing
        res = add_container_states(container_serial, [])
        self.assertEqual(0, len(res))
        states = container.get_states()
        self.assertEqual(2, len(states))

        # Add None: Changes nothing
        container.add_states(None)
        states = container.get_states()
        self.assertEqual(2, len(states))

        # Add unknown state
        res = add_container_states(container_serial, ["unknown_state"])
        self.assertFalse(res["unknown_state"])
        states = container.get_states()
        self.assertEqual(2, len(states))
        self.assertIn("active", states)
        self.assertIn("lost", states)

        # Add state that excludes old state: removes the old state
        res = add_container_states(container_serial, ["disabled"])
        self.assertTrue(res["disabled"])
        states = container.get_states()
        self.assertEqual(2, len(states))
        self.assertIn("disabled", states)
        self.assertIn("lost", states)

        # Add two states that excludes each other: raises parameter error
        self.assertRaises(ParameterError, add_container_states, container_serial, ["active", "disabled"])

    def test_28_get_all_containers_paginate(self):
        # Removes all previously initialized containers
        old_test_containers = TokenContainer.query.all()
        for container in old_test_containers:
            container.delete()

        # Arrange
        types = ["generic", "Yubikey", "Smartphone", "generic", "Yubikey"]
        self.setUp_user_realms()
        self.setUp_user_realm2()
        realms = ["realm2", "realm1", "realm2", "realm1", "realm1"]
        container_serials = ["SMPH0001"]
        init_container(
            {"type": "smartphone", "description": "test container", "realm": "realm1", "container_serial": "SMPH0001"})
        for t, r, serial in zip(types, realms, container_serials):
            serial = init_container({"type": t, "description": "test container", "realm": r})["container_serial"]
            container_serials.append(serial)

        # ---- container serial ----
        # Filter for exact container serial
        container_data = get_all_containers(serial=container_serials[0], pagesize=15)
        self.assertEqual(1, container_data["count"])
        self.assertEqual(container_serials[0], container_data["containers"][0].serial)

        # Filter for container serial in lower cases
        container_data = get_all_containers(serial="smph0001", pagesize=15)
        self.assertEqual(1, container_data["count"])
        self.assertEqual("SMPH0001", container_data["containers"][0].serial)

        # Filter for container serial stored as lower cases in db
        init_container(
            {"type": "generic", "description": "test container", "realm": "realm2", "container_serial": "cont0001"})
        container_data = get_all_containers(serial="CONT0001", pagesize=15)
        self.assertEqual(1, container_data["count"])
        self.assertEqual("cont0001", container_data["containers"][0].serial)
        find_container_by_serial("cont0001").delete()

        # Filter for non-existing serial
        container_data = get_all_containers(serial="non_existing_serial")
        self.assertEqual(0, len(container_data["containers"]))

        # Filter for container serials starting with "SMPH"
        container_data = get_all_containers(serial="SMPH*", pagesize=15)
        self.assertEqual(2, container_data["count"])
        self.assertSetEqual(set(container_serials[i] for i in [0, 3]),
                            {container.serial for container in container_data["containers"]})

        # Filter for any container serial
        container_data = get_all_containers(serial="*", pagesize=15)
        self.assertEqual(6, container_data["count"])

        # Filter for container serial containing "ont"
        container_data = get_all_containers(serial="*ont*", pagesize=15)
        self.assertEqual(2, container_data["count"])

        # ---- Type ----
        # Filter for type
        container_data = get_all_containers(ctype="generic", pagesize=15)
        for container in container_data["containers"]:
            self.assertEqual(container.type, "generic")
        self.assertEqual(2, container_data["count"])

        # Filter for type using wildcards
        container_data = get_all_containers(ctype="*ne*", pagesize=15)
        self.assertEqual(4, container_data["count"])
        for container in container_data["containers"]:
            self.assertIn(container.type, ["generic", "smartphone"])

        # Filter for non-existing type
        container_data = get_all_containers(ctype="random_type")
        self.assertEqual(0, len(container_data["containers"]))

        # ---- token serial ----
        # Add token
        tokens = []
        params = {"type": "hotp", "genkey": "1"}
        container = find_container_by_serial(container_serials[2])
        for i in range(3):
            t = init_token(params)
            tokens.append(t)
            container.add_token(t)
        token_serials = [t.get_serial() for t in tokens]

        token = init_token(params)
        container = find_container_by_serial(container_serials[3])
        container.add_token(token)

        # Filter for token serial
        container_data = get_all_containers(token_serial=token_serials[1], pagesize=15)
        for container in container_data["containers"]:
            self.assertTrue(container.serial in container_serials[2])
        self.assertEqual(1, container_data["count"])

        # filter for token serial containing wildcard
        container_data = get_all_containers(token_serial="OATH*", pagesize=15)
        for container in container_data["containers"]:
            self.assertTrue(container.serial in container_serials[2:4])
        self.assertEqual(2, container_data["count"])

        # filter for non-matching token serial containing wildcard
        container_data = get_all_containers(token_serial="xyz1234*", pagesize=15)
        self.assertEqual(0, container_data["count"])

        # Filter for non-existing token serial
        container_data = get_all_containers(token_serial="non_existing_token", pagesize=15)
        self.assertEqual(0, len(container_data["containers"]))

        # ---- Realm ----
        # Filter by realm
        container_data = get_all_containers(realm="realm1", pagesize=15)
        self.assertEqual(4, len(container_data["containers"]))
        for container in container_data["containers"]:
            self.assertEqual("realm1", container.realms[0].name)

        # Filter by realm including wildcards
        container_data = get_all_containers(realm="*1", pagesize=15)
        self.assertEqual(4, len(container_data["containers"]))
        for container in container_data["containers"]:
            self.assertIn("1", container.realms[0].name)

        # Filter by realms case-insensitive
        container_data = get_all_containers(realm="rEalM2", pagesize=15)
        self.assertEqual(2, len(container_data["containers"]))
        for container in container_data["containers"]:
            self.assertEqual("realm2", container.realms[0].name)

        # Filter for non-existing realm
        container_data = get_all_containers(realm="non_existing_realm", pagesize=15)
        self.assertEqual(0, len(container_data["containers"]))

        # ---- user ----
        # Filter by user (same username and resolver, but different realms)
        user_cornelius_1 = User(login="cornelius", realm=self.realm1)
        assign_user(container_serials[1], user_cornelius_1)
        user_cornelius_2 = User(login="cornelius", realm=self.realm2)
        assign_user(container_serials[2], user_cornelius_2)
        container_data = get_all_containers(user=user_cornelius_1, pagesize=15)
        self.assertEqual(1, len(container_data["containers"]))
        self.assertEqual(container_serials[1], container_data["containers"][0].serial)
        self.assertEqual(1, len(container_data["containers"][0].get_users()))
        container1_owner = container_data["containers"][0].get_users()[0]
        self.assertEqual(user_cornelius_1, container1_owner)

        # Filter for non-existing user
        user_invalid = User(login="invalid", realm="random")
        container_data = get_all_containers(user=user_invalid, pagesize=15)
        self.assertEqual(0, len(container_data["containers"]))

        # ---- assigned ----
        container_data = get_all_containers(assigned=True, pagesize=15)
        self.assertEqual(2, len(container_data["containers"]))
        self.assertSetEqual(set(container_serials[1:3]),
                            {container.serial for container in container_data["containers"]})

        # not assigned
        container_data = get_all_containers(assigned=False, pagesize=15)
        self.assertEqual(4, len(container_data["containers"]))
        not_assigned_serials = [container.serial for container in container_data["containers"]]
        self.assertNotIn(container_serials[1], not_assigned_serials)
        self.assertNotIn(container_serials[2], not_assigned_serials)

        # ---- resolver ----
        # unassign one user
        unassign_user(container_serials[2], user_cornelius_2)
        # exact match
        container_data = get_all_containers(resolver=self.resolvername1, pagesize=15)
        self.assertEqual(1, len(container_data["containers"]))
        self.assertEqual(1, len(container_data["containers"][0].get_users()))
        self.assertEqual(self.resolvername1, container_data["containers"][0].get_users()[0].resolver)

        # wildcard
        container_data = get_all_containers(resolver="reso*", pagesize=15)
        self.assertEqual(1, len(container_data["containers"]))
        self.assertEqual(1, len(container_data["containers"][0].get_users()))
        self.assertEqual(self.resolvername1, container_data["containers"][0].get_users()[0].resolver)

        # non-existing resolver
        container_data = get_all_containers(resolver="random*", pagesize=15)
        self.assertEqual(0, len(container_data["containers"]))

        # ---- info ----
        # Add info
        container_3 = find_container_by_serial(container_serials[3])
        container_3.set_container_info({"key1": "value1", "key2": "value2"})
        container_4 = find_container_by_serial(container_serials[4])
        container_4.set_container_info({"key1": "value1", "test": "1234", "test.type": "number"})
        # exact
        container_data = get_all_containers(info={"key1": "value1"}, pagesize=15)
        self.assertEqual(2, len(container_data["containers"]))
        self.assertSetEqual(set(container_serials[3:5]),
                            {container.serial for container in container_data["containers"]})

        # wildcard
        container_data = get_all_containers(info={"key*": "*2*"}, pagesize=15)
        self.assertEqual(1, len(container_data["containers"]))
        self.assertEqual(container_serials[3], container_data["containers"][0].serial)

        # no match
        container_data = get_all_containers(info={"test": "*value*"}, pagesize=15)
        self.assertEqual(0, len(container_data["containers"]))

        # Get container info type
        container_data = get_all_containers(info={"test": "*"})
        self.assertEqual(1, len(container_data["containers"]))
        self.assertEqual(container_serials[4], container_data["containers"][0].serial)
        container_info = container_data["containers"][0].get_container_info()
        self.assertGreaterEqual(len(container_info), 2, container_info)
        test_info = [x for x in container_info if x.key == "test"][0]
        self.assertEqual("number", test_info.type, test_info)

        # ---- description ----
        # filter by description
        find_container_by_serial(container_serials[0]).description = "test description"
        find_container_by_serial(container_serials[2]).description = "this is an awesome description"

        # exact match
        container_data = get_all_containers(description="test description")
        self.assertEqual(1, len(container_data["containers"]))
        self.assertEqual(container_serials[0], container_data["containers"][0].serial)

        # wildcard
        container_data = get_all_containers(description="*description*")
        self.assertEqual(2, len(container_data["containers"]))

        # ---- template ----
        # Create container with template
        template_params = {"name": "test",
                           "container_type": "smartphone",
                           "template_options": {"tokens": [{"type": "hotp", "genkey": True}]}}
        create_container_template(container_type=template_params["container_type"],
                                  template_name=template_params["name"],
                                  options=template_params["template_options"])
        container_serial = init_container({"type": "smartphone", "template": template_params})["container_serial"]

        # check filter by template
        container_data = get_all_containers(template="test")
        self.assertEqual(1, len(container_data["containers"]))
        self.assertEqual("test", container_data["containers"][0].template.name)

        # filter template with wildcards
        container_data = get_all_containers(template="te*")
        self.assertEqual(1, len(container_data["containers"]))
        self.assertEqual("test", container_data["containers"][0].template.name)

        # check filter by non-existing template
        container_data = get_all_containers(template="random")
        self.assertEqual(0, len(container_data["containers"]))

        # ---- last_auth ----
        # Add last_auth
        container_3 = find_container_by_serial(container_serials[3])
        container_3._db_container.last_seen = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=2)
        container_4 = find_container_by_serial(container_serials[4])
        container_4._db_container.last_seen = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=300)

        # within last hour
        container_data = get_all_containers(last_auth_delta="1h", pagesize=15)
        self.assertEqual(0, len(container_data["containers"]))

        # within last 7 days
        container_3._db_container.last_seen = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=2)
        container_data = get_all_containers(last_auth_delta="7d", pagesize=15)
        self.assertEqual(1, len(container_data["containers"]))
        self.assertEqual(container_serials[3], container_data["containers"][0].serial)

        # within last year
        container_data = get_all_containers(last_auth_delta="1y", pagesize=15)
        self.assertEqual(2, len(container_data["containers"]))
        self.assertSetEqual({container_serials[3], container_serials[4]},
                            {container.serial for container in container_data["containers"]})

        # within last minute
        container_3._db_container.last_seen = datetime.now(timezone.utc).replace(tzinfo=None)
        container_data = get_all_containers(last_auth_delta="1m", pagesize=15)
        self.assertEqual(1, len(container_data["containers"]))
        self.assertEqual(container_serials[3], container_data["containers"][0].serial)

        # ---- last_sync ----
        # Add last_sync
        container_3._db_container.last_updated = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=5)
        container_4._db_container.last_updated = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=300)

        # within last minute
        container_data = get_all_containers(last_sync_delta="1m", pagesize=15)
        self.assertEqual(0, len(container_data["containers"]))

        # within last hour
        container_data = get_all_containers(last_sync_delta="1h", pagesize=15)
        self.assertEqual(1, len(container_data["containers"]))
        self.assertEqual(container_serials[3], container_data["containers"][0].serial)

        # within last year
        container_data = get_all_containers(last_sync_delta="1y", pagesize=15)
        self.assertEqual(2, len(container_data["containers"]))
        self.assertSetEqual({container_serials[3], container_serials[4]},
                            {container.serial for container in container_data["containers"]})

        # ---- state ----
        # Add states
        container_3.add_states(["disabled", "lost"])
        container_4.add_states(["disabled"])

        # exact
        container_data = get_all_containers(state="disabled", pagesize=15)
        self.assertEqual(2, len(container_data["containers"]))
        self.assertSetEqual({container_serials[3], container_serials[4]},
                            {container.serial for container in container_data["containers"]})

        # wildcard
        container_data = get_all_containers(state="*s*", pagesize=15)
        self.assertEqual(2, len(container_data["containers"]))
        self.assertSetEqual({container_serials[3], container_serials[4]},
                            {container.serial for container in container_data["containers"]})

        # wildcard
        container_data = get_all_containers(state="los*", pagesize=15)
        self.assertEqual(1, len(container_data["containers"]))
        self.assertEqual(container_serials[3], container_data["containers"][0].serial)

        # non-existing state
        container_data = get_all_containers(state="non_existing_state", pagesize=15)
        self.assertEqual(0, len(container_data["containers"]))

        # ---- combined search ----
        container = find_container_by_serial(container_serial)
        container.add_user(User(login="hans", realm=self.realm1))
        container.set_realms([self.realm1, self.realm2])
        container.add_token(init_token({"type": "hotp", "genkey": True}))
        # correct search
        container_data = get_all_containers(user=User("hans", self.realm1), serial="SMPH*", ctype="smartphone",
                                            realm="realm2", token_serial="OATH*", template="test", pagesize=15)
        self.assertEqual(1, container_data["count"])
        # no container fits all search params
        container_data = get_all_containers(user=User("hans", self.realm1), serial="SMPH*", ctype="smartphone",
                                            realm="realm3", token_serial="OATH*", template="test", pagesize=15)
        self.assertEqual(0, container_data["count"])

        # ---- Test pagination ----
        container_data = get_all_containers(page=2, pagesize=2)
        self.assertEqual(1, container_data["prev"])
        self.assertEqual(2, container_data["current"])
        self.assertEqual(3, container_data["next"])
        self.assertEqual(7, container_data["count"])
        self.assertEqual(2, len(container_data["containers"]))

        # Do not use pagination
        container_data = get_all_containers()
        self.assertNotIn("prev", container_data)
        self.assertNotIn("current", container_data)
        self.assertEqual(7, len(container_data["containers"]))

        # ---- Sorting ----
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

        template = get_template_obj(template_params["name"])
        template.delete()

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

    def test_34_get_as_dict(self):
        # Arrange
        container_serial = init_container({"type": "generic"})["container_serial"]
        container = find_container_by_serial(container_serial)
        # Tokens
        hotp = init_token({"genkey": True, "type": "hotp"})
        container.add_token(hotp)
        totp = init_token({"genkey": True, "type": "totp"})
        container.add_token(totp)
        # User
        self.setUp_user_realms()
        user = User(login="hans", realm=self.realm1)
        container.add_user(user)
        # Template
        create_container_template(container_type="generic", template_name="test", options={})
        container.template = "test"

        # Act
        container_dict = container.get_as_dict()

        # Assert
        self.assertEqual("generic", container_dict["type"])
        self.assertEqual(container_serial, container_dict["serial"])
        self.assertEqual("", container_dict["description"])
        self.assertIsNone(container_dict["last_authentication"])
        self.assertIsNone(container_dict["last_synchronization"])
        self.assertListEqual(["active"], container_dict["states"])
        self.assertEqual("test", container_dict["template"])
        self.assertEqual(1, len(container_dict["info"]))
        self.assertIn("creation_date", container_dict["info"])
        self.assertListEqual([self.realm1], container_dict["realms"])
        self.assertEqual("hans", container_dict["users"][0]["user_name"])
        self.assertEqual(self.realm1, container_dict["users"][0]["user_realm"])
        self.assertEqual(self.resolvername1, container_dict["users"][0]["user_resolver"])
        self.assertListEqual([hotp.get_serial(), totp.get_serial()], container_dict["tokens"])

        template = get_template_obj("test")
        template.delete()

    def test_35_get_as_dict_no_tokens_no_user(self):
        # Arrange
        container_serial = init_container({"type": "generic"})["container_serial"]
        container = find_container_by_serial(container_serial)

        # Act
        container_dict = container.get_as_dict()

        # Assert
        self.assertEqual("generic", container_dict["type"])
        self.assertEqual(container_serial, container_dict["serial"])
        self.assertEqual("", container_dict["description"])
        self.assertIsNone(container_dict["last_authentication"])
        self.assertIsNone(container_dict["last_synchronization"])
        self.assertListEqual(["active"], container_dict["states"])
        self.assertEqual("", container_dict["template"])
        self.assertEqual(1, len(container_dict["info"]))
        self.assertIn("creation_date", container_dict["info"])
        self.assertListEqual([], container_dict["realms"])
        self.assertListEqual([], container_dict["users"])
        self.assertListEqual([], container_dict["tokens"])

    def test_36_set_default_options(self):
        smph_serial = init_container({"type": "smartphone"})["container_serial"]
        smartphone = find_container_by_serial(smph_serial)

        # Invalid key
        value = smartphone.set_default_option("random_key")
        self.assertIsNone(value)

        # valid key
        value = smartphone.set_default_option(SmartphoneOptions.KEY_ALGORITHM)
        self.assertEqual("secp384r1", value)

        # change key
        smartphone.set_container_info({SmartphoneOptions.KEY_ALGORITHM: "secp256r1"})
        # set default value keeps the defined value
        value = smartphone.set_default_option(SmartphoneOptions.KEY_ALGORITHM)
        self.assertEqual("secp256r1", value)

    def test_37_set_template(self):
        create_container_template(container_type="smartphone",
                                  template_name="test",
                                  options={"tokens": [{"type": "hotp"}]})
        smartphone_serial = init_container({"type": "smartphone"})["container_serial"]
        smartphone = find_container_by_serial(smartphone_serial)
        smartphone.template = "test"
        self.assertEqual("test", smartphone.template.name)

        yubi_serial = init_container({"type": "yubikey"})["container_serial"]
        yubikey = find_container_by_serial(yubi_serial)
        yubikey.template = "test"
        self.assertIsNone(yubikey.template)

    def test_38_update_container_info(self):
        container_serial = init_container({"type": "generic"})["container_serial"]
        container = find_container_by_serial(container_serial)

        # Set initial info fields
        info = [TokenContainerInfoData(key="key1", value="abc"), TokenContainerInfoData(key="key2", value="123")]
        container.update_container_info(info)
        container_info = get_container_info_dict(container_serial)
        self.assertEqual("abc", container_info["key1"])
        self.assertEqual("123", container_info["key2"])
        self.assertIn("creation_date", container_info)
        self.assertEqual(3, len(container_info))

        # Update info fields
        info = [TokenContainerInfoData(key="key2", value="456"), TokenContainerInfoData(key="key3", value="xyz")]
        container.update_container_info(info)
        container_info = get_container_info_dict(container_serial)
        self.assertEqual("abc", container_info["key1"])
        self.assertEqual("456", container_info["key2"])
        self.assertEqual("xyz", container_info["key3"])
        self.assertIn("creation_date", container_info)
        self.assertEqual(4, len(container_info))

        # Pass empty list
        container.update_container_info([])
        container_info = get_container_info_dict(container_serial)
        self.assertEqual(4, len(container_info))

        # Clean up
        container.delete()

    def test_39_get_tokens_for_synchronization(self):
        # Arrange
        container_serial = init_container({"type": "smartphone"})["container_serial"]
        container = find_container_by_serial(container_serial)
        hotp = init_token({"genkey": True, "type": "hotp"})
        container.add_token(hotp)
        totp = init_token({"genkey": True, "type": "totp"})
        container.add_token(totp)
        sms = init_token({"type": "sms", "phone": "+123456789", "genkey": True})
        container.add_token(sms)
        push = init_token({"type": "push", "genkey": True})
        container.add_token(push)

        # Act
        tokens = container.get_tokens_for_synchronization()

        # Assert
        token_types = [token.get_tokentype() for token in tokens]
        self.assertSetEqual({"hotp", "totp", "push"}, set(token_types))
        self.assertNotIn("sms", token_types)


class MockSmartphone:

    def __init__(self, device_brand=None, device_model=None):
        self.container_serial = None
        self.public_key_encr = None
        self.private_key_encr = None
        self.public_key_sign = None
        self.private_key_sign = None
        self.device_brand = device_brand
        self.device_model = device_model
        self.container = {}

    @property
    def private_key_sign(self):
        return self._private_key_sign

    @private_key_sign.setter
    def private_key_sign(self, value):
        self._private_key_sign = value

    @property
    def public_key_sign(self):
        return self._public_key_sign

    @public_key_sign.setter
    def public_key_sign(self, value):
        self._public_key_sign = value

    def set_sign_keys(self, keys: KeyPair):
        self.private_key_sign = keys.private_key
        self.public_key_sign = keys.public_key

    def get_sign_keys(self):
        return KeyPair(private_key=self.private_key_sign, public_key=self.public_key_sign)

    @property
    def private_key_encr(self):
        return self._private_key_encr

    @private_key_encr.setter
    def private_key_encr(self, value):
        self._private_key_encr = value

    @property
    def public_key_encr(self):
        return self._public_key_encr

    @public_key_encr.setter
    def public_key_encr(self, value):
        self._public_key_encr = value

    def set_encr_keys(self, keys: KeyPair):
        self.private_key_encr = keys.private_key
        self.public_key_encr = keys.public_key

    @property
    def container(self):
        return self._container

    @container.setter
    def container(self, value):
        self._container = value

    @property
    def device_brand(self):
        return self._device_brand

    @device_brand.setter
    def device_brand(self, value):
        self._device_brand = value

    @property
    def device_model(self):
        return self._device_model

    @device_model.setter
    def device_model(self, value):
        self._device_model = value

    @property
    def container_serial(self):
        return self._container_serial

    @container_serial.setter
    def container_serial(self, value):
        self._container_serial = value

    def register_finalize(self, nonce, registration_time, scope, serial=None, passphrase=None, private_key_smph=None,
                          passphrase_user=False):
        if serial:
            self.container_serial = serial

        message = f"{nonce}|{registration_time}|{self.container_serial}|{scope}"
        if self.device_brand:
            message += f"|{self.device_brand}"
        if self.device_model:
            message += f"|{self.device_model}"
        if passphrase:
            message += f"|{passphrase}"

        if private_key_smph:
            key_pair_smph = KeyPair(private_key=private_key_smph)
            key_pair_smph.public_key = private_key_smph.public_key()
        elif not self.private_key_sign:
            key_pair_smph = generate_keypair_ecc("secp384r1")
        else:
            key_pair_smph = self.get_sign_keys()
        self.set_sign_keys(key_pair_smph)
        key_pair_str = ecc_key_pair_to_b64url_str(public_key=key_pair_smph.public_key)

        sign_res = sign_ecc(message.encode("utf-8"), key_pair_smph.private_key, "sha256")

        params = {"signature": base64.b64encode(sign_res["signature"]), "public_client_key": key_pair_str.public_key,
                  "device_brand": self.device_brand, "device_model": self.device_model, "scope": scope,
                  "container_serial": self.container_serial}
        if passphrase_user:
            params.update({"passphrase": passphrase})
        return params

    def synchronize(self, challenge_params, scope):
        nonce = challenge_params["nonce"]
        time_stamp = challenge_params["time_stamp"]

        enc_keys = generate_keypair_ecc("x25519")
        self.set_encr_keys(enc_keys)
        pub_key_enc_smph_str = base64.urlsafe_b64encode(enc_keys.public_key.public_bytes_raw()).decode('utf-8')

        message = f"{nonce}|{time_stamp}|{self.container_serial}|{scope}|{pub_key_enc_smph_str}"
        if self.container:
            message += f"|{json.dumps(self.container)}"
        sign_res = sign_ecc(message.encode("utf-8"), self.private_key_sign, "sha256")

        params = {"signature": base64.b64encode(sign_res["signature"]), "public_enc_key_client": pub_key_enc_smph_str,
                  "scope": scope, "container_serial": self.container_serial}
        if self.container:
            params.update({"container_dict_client": json.dumps(self.container)})
        return params

    def register_terminate(self, params, scope):
        nonce = params["nonce"]
        time_stamp = params["time_stamp"]

        message = f"{nonce}|{time_stamp}|{self.container_serial}|{scope}"
        sign_res = sign_ecc(message.encode("utf-8"), self.private_key_sign, "sha256")

        params = {"signature": base64.b64encode(sign_res["signature"]), "container_serial": self.container_serial}
        return params


class TokenContainerSynchronization(MyTestCase):

    def register_smartphone_initialize_success(self, server_url, passphrase_params=None,
                                               smartphone_serial: str = None):
        if not smartphone_serial:
            smartphone_serial = init_container({"type": "smartphone"})["container_serial"]
        smartphone = find_container_by_serial(smartphone_serial)
        scope = create_endpoint_url(server_url, "container/register/finalize")

        # passphrase
        params = {}
        if passphrase_params:
            params.update(passphrase_params)

        # Prepare
        result = smartphone.init_registration(server_url, scope, registration_ttl=100, ssl_verify=True, params=params)
        smartphone.update_container_info(
            [TokenContainerInfoData(key="server_url", value=server_url, info_type=PI_INTERNAL)])

        # Check result entries
        result_entries = result.keys()
        self.assertIn("nonce", result_entries)
        self.assertIn("time_stamp", result_entries)
        self.assertIn("key_algorithm", result_entries)
        self.assertIn("hash_algorithm", result_entries)
        self.assertTrue(result["ssl_verify"])
        self.assertEqual(100, result["ttl"])
        self.assertIn("container_url", result_entries)

        # Check url
        url = result["container_url"]["value"]
        self.assertIn(smartphone_serial, url)
        self.assertIn("issuer=privacyIDEA", url)
        self.assertIn("key_algorithm=secp384r1", url)
        self.assertIn("hash_algorithm=SHA256", url)
        self.assertIn("ssl_verify=True", url)
        self.assertIn("ttl=100", url)

        # check container info is set
        container_info = smartphone.get_container_info_dict()
        self.assertEqual("secp384r1", container_info[SmartphoneOptions.KEY_ALGORITHM])
        self.assertEqual("SHA256", container_info[SmartphoneOptions.HASH_ALGORITHM])
        self.assertEqual("AES", container_info[SmartphoneOptions.ENCRYPT_ALGORITHM])
        self.assertEqual("x25519", container_info[SmartphoneOptions.ENCRYPT_KEY_ALGORITHM])
        self.assertEqual("GCM", container_info[SmartphoneOptions.ENCRYPT_MODE])

        return smartphone_serial, result

    def test_01_register_smartphone_finalize_invalid_challenge(self):
        scope = "https://pi.net/container/register/finalize"
        mock_smph = MockSmartphone(device_brand="XY", device_model="ABS123")
        smartphone_serial = init_container({"type": "smartphone"})["container_serial"]
        smartphone = find_container_by_serial(smartphone_serial)

        # Mock smartphone with guessed params (no prepare)
        nonce = geturandom(20, hex=True)
        time_stamp = datetime.now(timezone.utc)
        params = mock_smph.register_finalize(nonce, time_stamp, scope, smartphone_serial)

        # Try to finalize registration with invalid params
        self.assertRaises(ContainerInvalidChallenge, smartphone.finalize_registration, params)

        # Valid prepare
        passphrase_params = {"passphrase_prompt": "Enter passphrase",
                             "passphrase_response": "top_secret"}
        smartphone_serial, init_results = self.register_smartphone_initialize_success(scope,
                                                                                      passphrase_params)
        smartphone = find_container_by_serial(smartphone_serial)

        # Mock smartphone with wrong nonce
        invalid_nonce = geturandom(20, hex=True)
        params = mock_smph.register_finalize(invalid_nonce, init_results["time_stamp"], scope, smartphone_serial,
                                             "top_secret")

        # Try to finalize registration
        self.assertRaises(ContainerInvalidChallenge, smartphone.finalize_registration, params)

        # Mock smartphone with invalid public key
        params = mock_smph.register_finalize(init_results["nonce"], init_results["time_stamp"], scope,
                                             smartphone_serial, "top_secret")
        smph_keys = generate_keypair_ecc("secp384r1")
        params["public_client_key"] = ecc_key_pair_to_b64url_str(public_key=smph_keys.public_key).public_key
        # Try finalize registration
        self.assertRaises(ContainerInvalidChallenge, smartphone.finalize_registration, params)

        # Mock smartphone with invalid passphrase
        params = mock_smph.register_finalize(init_results["nonce"], init_results["time_stamp"], scope,
                                             smartphone_serial, "different_secret")

        # Try to finalize registration
        self.assertRaises(ContainerInvalidChallenge, smartphone.finalize_registration, params)

        # Mock smartphone with wrong scope
        params = mock_smph.register_finalize(init_results["nonce"], init_results["time_stamp"],
                                             "https://pi.net/container/register/terminate",
                                             smartphone_serial, "top_secret")

        # Try to finalize registration
        self.assertRaises(ContainerInvalidChallenge, smartphone.finalize_registration, params)

    def test_02_register_smartphone_terminate(self):
        # container is not registered
        smartphone_serial = init_container({"type": "smartphone"})["container_serial"]
        smartphone = find_container_by_serial(smartphone_serial)
        smartphone.terminate_registration()

        # check container_info is empty except for creation date
        container_info = smartphone.get_container_info_dict()
        self.assertEqual(1, len(container_info))
        self.assertIn("creation_date", container_info.keys())

    def test_03_register_smartphone_success(self, smartphone_serial=None):
        # Prepare
        server_url = "https://pi.net/"
        smartphone_serial, init_result = self.register_smartphone_initialize_success(server_url,
                                                                                     smartphone_serial=smartphone_serial)
        smartphone = find_container_by_serial(smartphone_serial)

        # Mock smartphone
        mock_smph = MockSmartphone(device_brand="XY", device_model="ABC123")
        scope = create_endpoint_url(server_url, "container/register/finalize")
        params = mock_smph.register_finalize(init_result["nonce"], init_result["time_stamp"], scope, smartphone_serial)

        # Finalize registration
        smartphone.finalize_registration(params)

        # Check if container info is set correctly
        container_info = smartphone.get_container_info_dict()
        container_info_keys = container_info.keys()
        self.assertIn("public_key_client", container_info_keys)
        self.assertEqual(f"{mock_smph.device_brand} {mock_smph.device_model}", container_info["device"])
        self.assertEqual(RegistrationState.REGISTERED, smartphone.registration_state)

        return mock_smph

    def test_04_register_terminate_smartphone_success(self):
        mock_smph = self.test_03_register_smartphone_success()
        smartphone = find_container_by_serial(mock_smph.container_serial)

        # create challenges
        params = {"scope": "https://pi.net/container/synchronize"}
        smartphone.create_challenge(params)
        smartphone.create_challenge(params)
        smartphone.create_challenge(params)
        challenges = get_challenges(serial=mock_smph.container_serial)
        self.assertEqual(3, len(challenges))

        # Terminate registration
        unregister(smartphone)
        # Check that the container info is deleted
        container_info = smartphone.get_container_info_dict()
        container_info_keys = container_info.keys()
        self.assertNotIn("public_key_client", container_info_keys)
        self.assertNotIn("device", container_info_keys)
        self.assertNotIn(RegistrationState.get_key(), container_info_keys)
        self.assertNotIn("server_url", container_info_keys)

        # check challenge
        challenges = get_challenges(serial=mock_smph.container_serial)
        self.assertEqual(0, len(challenges))

    def test_05a_register_smartphone_passphrase_success(self):
        # Prepare
        scope = "https://pi.net/container/register/finalize"
        passphrase_params = {"passphrase_prompt": "Enter passphrase",
                             "passphrase_response": "top_secret"}
        smartphone_serial, init_result = self.register_smartphone_initialize_success(scope,
                                                                                     passphrase_params)
        smartphone = find_container_by_serial(smartphone_serial)

        # Check that passphrase is included in the challenge
        challenge = get_challenges(serial=smartphone_serial)[0]
        challenge_data = json.loads(challenge.data)
        self.assertEqual(passphrase_params["passphrase_response"],
                         decryptPassword(challenge_data["passphrase_response"]))

        # Mock smartphone
        mock_smph = MockSmartphone(device_brand="XY", device_model="ABC123")
        params = mock_smph.register_finalize(init_result["nonce"], init_result["time_stamp"], scope, smartphone_serial,
                                             passphrase_params["passphrase_response"])

        # Finalize registration
        smartphone.finalize_registration(params)

        # Check if container info is set correctly
        container_info = smartphone.get_container_info_dict()
        container_info_keys = container_info.keys()
        self.assertIn("public_key_client", container_info_keys)

    def test_05b_register_smartphone_passphrase_user_success(self):
        """
        Test a successful registration when securing the registration with the passphrase from the user store
        """
        self.setUp_user_realms()
        # Prepare
        server_url = "https://pi.net/"
        passphrase_params = {"passphrase_user": True, "passphrase_prompt": "Enter AD passphrase"}
        smartphone_serial = init_container({"type": "smartphone", "user": "cornelius", "realm": self.realm1})[
            "container_serial"]
        smartphone_serial, init_result = self.register_smartphone_initialize_success(server_url,
                                                                                     smartphone_serial=smartphone_serial,
                                                                                     passphrase_params=passphrase_params)
        # check register init result
        self.assertTrue(init_result["send_passphrase"])
        self.assertEqual("Enter AD passphrase", init_result["passphrase_prompt"])
        url = init_result["container_url"]["value"]
        self.assertIn("send_passphrase=True", url)
        self.assertIn("passphrase=Enter%20AD%20passphrase", url)

        # check challenge data
        challenge = get_challenges(serial=smartphone_serial)[0]
        challenge_data = json.loads(challenge.data)
        self.assertTrue(challenge_data["passphrase_user"])
        self.assertEqual("", challenge_data["passphrase_response"])

        # Mock smartphone
        mock_smph = MockSmartphone(device_brand="XY", device_model="ABC123")
        scope = create_endpoint_url(server_url, "container/register/finalize")
        params = mock_smph.register_finalize(init_result["nonce"], init_result["time_stamp"], scope, smartphone_serial,
                                             passphrase="test", passphrase_user=True)

        # Finalize registration
        smartphone = find_container_by_serial(smartphone_serial)
        smartphone.finalize_registration(params)

        # Check if container info is set correctly
        container_info = smartphone.get_container_info_dict()
        container_info_keys = container_info.keys()
        self.assertIn("public_key_client", container_info_keys)
        self.assertEqual(f"{mock_smph.device_brand} {mock_smph.device_model}", container_info["device"])
        self.assertEqual(RegistrationState.REGISTERED, smartphone.registration_state)

    def test_05c_register_smartphone_passphrase_user_fails(self):
        """
        Test failed registrations when securing the registration with the passphrase from the user store
        """
        self.setUp_user_realms()

        # ---- Invalid passphrase parameter combination ----
        server_url = "https://pi.net/"
        passphrase_params = {"passphrase_user": True, "passphrase_prompt": "Enter AD passphrase",
                             "passphrase_response": "test1234"}
        smartphone_serial = init_container({"type": "smartphone", "user": "cornelius", "realm": self.realm1})[
            "container_serial"]
        smartphone = find_container_by_serial(smartphone_serial)
        scope = create_endpoint_url(server_url, "container/register/finalize")

        # Register init fails: passphrase_user and passphrase_response are both passed
        self.assertRaises(ParameterError, smartphone.init_registration, server_url, scope, registration_ttl=100,
                          ssl_verify=True, params=passphrase_params)

        # ---- Invalid passphrase ----
        server_url = "https://pi.net/"
        passphrase_params = {"passphrase_user": True, "passphrase_prompt": "Enter AD passphrase"}
        smartphone_serial = init_container({"type": "smartphone", "user": "cornelius", "realm": self.realm1})[
            "container_serial"]
        smartphone_serial, init_result = self.register_smartphone_initialize_success(server_url,
                                                                                     smartphone_serial=smartphone_serial,
                                                                                     passphrase_params=passphrase_params)
        # check register init result
        self.assertTrue(init_result["send_passphrase"])
        self.assertEqual("Enter AD passphrase", init_result["passphrase_prompt"])
        url = init_result["container_url"]["value"]
        self.assertIn("send_passphrase=True", url)
        self.assertIn("passphrase=Enter%20AD%20passphrase", url)

        # check challenge data
        challenge = get_challenges(serial=smartphone_serial)[0]
        challenge_data = json.loads(challenge.data)
        self.assertTrue(challenge_data["passphrase_user"])
        self.assertEqual("", challenge_data["passphrase_response"])

        # Mock smartphone
        mock_smph = MockSmartphone(device_brand="XY", device_model="ABC123")
        scope = create_endpoint_url(server_url, "container/register/finalize")
        params = mock_smph.register_finalize(init_result["nonce"], init_result["time_stamp"], scope, smartphone_serial,
                                             passphrase="invalid", passphrase_user=True)

        # Finalize registration
        smartphone = find_container_by_serial(smartphone_serial)
        self.assertRaises(ContainerInvalidChallenge, smartphone.finalize_registration, params)

        # ---- Do not pass passphrase on finalize ----
        # Mock smartphone
        mock_smph = MockSmartphone()
        scope = create_endpoint_url(server_url, "container/register/finalize")
        params = mock_smph.register_finalize(init_result["nonce"], init_result["time_stamp"], scope, smartphone_serial)

        # Finalize registration
        self.assertRaises(ContainerInvalidChallenge, smartphone.finalize_registration, params)

    def test_06_create_container_challenge(self):
        container_serial = init_container({"type": "smartphone"})["container_serial"]
        container = find_container_by_serial(container_serial)
        scope = "https://pi.net/container/synchronize"

        res = container.create_challenge(scope)
        self.assertIn("nonce", res.keys())
        self.assertIn("time_stamp", res.keys())
        self.assertIn("enc_key_algorithm", res.keys())

        # check challenge
        challenge = get_challenges(serial=container_serial)[0]
        self.assertEqual(res["nonce"], challenge.challenge)
        self.assertEqual(res["time_stamp"], challenge.timestamp.replace(tzinfo=timezone.utc).isoformat())
        self.assertEqual(scope, json.loads(challenge.data)["scope"])

    def test_07_create_endpoint_url(self):
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

    def test_08_challenge_sync_smartphone_success(self):
        smartphone_serial = init_container({"type": "smartphone"})["container_serial"]
        smartphone = find_container_by_serial(smartphone_serial)

        # Create challenge for synchronization
        scope = "https://pi.net/container/synchronize"
        result = smartphone.create_challenge(scope)
        result_entries = result.keys()
        self.assertIn("nonce", result_entries)
        self.assertIn("time_stamp", result_entries)
        self.assertIn("enc_key_algorithm", result_entries)

        # check challenge
        challenge = get_challenges(serial=smartphone_serial)[0]
        self.assertEqual(result["nonce"], challenge.challenge)
        self.assertEqual(result["time_stamp"], challenge.timestamp.replace(tzinfo=timezone.utc).isoformat())
        data = json.loads(challenge.data)
        self.assertEqual(scope, data["scope"])

    def test_09_check_challenge_response_smartphone_success(self):
        # Registration
        mock_smph = self.test_03_register_smartphone_success()
        smartphone = find_container_by_serial(mock_smph.container_serial)

        # Init sync
        scope = "https://pi.net/container/synchronize"
        challenge_params = smartphone.create_challenge(scope)
        result_entries = challenge_params.keys()
        self.assertIn("nonce", result_entries)
        self.assertIn("time_stamp", result_entries)
        self.assertIn("enc_key_algorithm", result_entries)

        # Mock smartphone
        smph_params = mock_smph.synchronize(challenge_params, scope)

        # Finalize sync
        allowed = smartphone.check_challenge_response(smph_params)
        self.assertTrue(allowed)

    def test_10_check_challenge_response_smartphone_invalid_signature(self):
        # Registration
        mock_smph = self.test_03_register_smartphone_success()
        smartphone = find_container_by_serial(mock_smph.container_serial)

        # Init sync
        scope = "https://pi.net/container/synchronize"
        challenge_params = smartphone.create_challenge(scope)

        # Wrong nonce
        challenge_params["nonce"] = geturandom(20, hex=True)
        smph_params = mock_smph.synchronize(challenge_params, scope)
        self.assertRaises(ContainerInvalidChallenge, smartphone.check_challenge_response, smph_params)

        # Wrong time stamp
        challenge_params["time_stamp"] = "2021-01-01T00:00:00.0000+00:00"
        smph_params = mock_smph.synchronize(challenge_params, scope)
        self.assertRaises(ContainerInvalidChallenge, smartphone.check_challenge_response, smph_params)

        # Another scope
        wrong_scope = "https://pi.net/container/register/terminate/client"
        smph_params = mock_smph.synchronize(challenge_params, wrong_scope)
        self.assertRaises(ContainerInvalidChallenge, smartphone.check_challenge_response, smph_params)

        # Wrong serial
        mock_smph.container_serial = "SMPH000123"
        smph_params = mock_smph.synchronize(challenge_params, scope)
        self.assertRaises(ContainerInvalidChallenge, smartphone.check_challenge_response, smph_params)

    def test_11_check_challenge_response_smartphone_expired_challenge(self):
        # Registration
        mock_smph = self.test_03_register_smartphone_success()
        smartphone = find_container_by_serial(mock_smph.container_serial)

        # Init sync
        scope = "https://pi.net/container/synchronize"
        challenge_params = smartphone.create_challenge(scope, 0)

        smph_params = mock_smph.synchronize(challenge_params, scope)
        self.assertRaises(ContainerInvalidChallenge, smartphone.check_challenge_response, smph_params)

    def test_12_validate_challenge_smartphone_invalid_params(self):
        # Registration
        mock_smph = self.test_03_register_smartphone_success()
        smartphone = find_container_by_serial(mock_smph.container_serial)

        # Init sync
        scope = "https://pi.net/container/synchronize"
        challenge_params = smartphone.create_challenge(scope)

        # pass no public key
        smph_params = mock_smph.synchronize(challenge_params, scope)
        smph_params["public_enc_key_client"] = None
        valid = smartphone.validate_challenge(smph_params["signature"], None,
                                              smph_params["scope"], key=smph_params["public_enc_key_client"])
        self.assertFalse(valid)

    def test_13_synchronize_smartphone_with_tokens(self):
        # Registration
        mock_smph = self.test_03_register_smartphone_success()
        smartphone = find_container_by_serial(mock_smph.container_serial)

        # tokens
        hotp_server_token = init_token({"genkey": "1", "type": "hotp", "otplen": 8, "hashlib": "sha256"})
        hotp_token = init_token({"genkey": "1", "type": "hotp"})
        _, _, otp_dict = hotp_token.get_multi_otp(3)
        hotp_otps = list(otp_dict["otp"].values())[1:]
        totp_token = init_token({"genkey": "1", "type": "totp"})
        # the function uses the local time, hence we have to pass the utc time
        time_now = datetime.now(timezone.utc)
        _, _, otp_dict = totp_token.get_multi_otp(2, curTime=time_now)
        totp_otps = [otp["otpval"] for otp in list(otp_dict["otp"].values())]

        smartphone.add_token(hotp_server_token)
        smartphone.add_token(totp_token)

        # Init sync
        scope = "https://pi.net/container/synchronize"
        challenge_params = smartphone.create_challenge(scope)
        result_entries = challenge_params.keys()
        self.assertIn("nonce", result_entries)
        self.assertIn("time_stamp", result_entries)
        self.assertIn("enc_key_algorithm", result_entries)

        # Mock smartphone
        # In the first step the smph does not know the container. hence it only sends the token infos
        random_otp = "123456"
        mock_smph.container = {
            "tokens": [{"tokentype": "HOTP", "otp": hotp_otps, "issuer": "privacyIDEA", "label": "123", "pin": "False",
                        "algorithm": "SHA1", "digits": "6", "counter": "1"},
                       {"tokentype": "TOTP", "otp": totp_otps},
                       {"tokentype": "HOTP", "otp": [random_otp]}]}
        smph_params = mock_smph.synchronize(challenge_params, scope)

        # Finalize sync
        allowed = smartphone.check_challenge_response(smph_params)
        self.assertTrue(allowed)
        container_dict = smartphone.synchronize_container_details(mock_smph.container)

        # check entries
        container_details = container_dict["container"]
        self.assertIn(smartphone.serial, container_details["serial"])
        # tokens
        token_details = container_dict["tokens"]
        add_tokens = token_details["add"]
        self.assertEqual(1, len(add_tokens))
        self.assertIn(hotp_server_token.get_serial(), add_tokens[0])
        update_tokens = token_details["update"]
        self.assertEqual(1, len(update_tokens))
        self.assertEqual(totp_token.get_serial(), update_tokens[0]["serial"])

        # Encrypt container dict
        res = smartphone.encrypt_dict(container_dict, smph_params)
        self.assertIn("encryption_algorithm", res.keys())
        self.assertIn("encryption_params", res.keys())
        self.assertIn("container_dict_server", res.keys())

    def test_14_synchronize_without_registration(self):
        smartphone_serial = init_container({"type": "smartphone"})["container_serial"]
        smartphone = find_container_by_serial(smartphone_serial)

        # Init sync
        scope = "https://pi.net/container/synchronize"
        challenge_params = smartphone.create_challenge(scope)

        # Mock smartphone
        mock_smph = MockSmartphone()
        mock_smph.set_sign_keys(generate_keypair_ecc("secp384r1"))
        smph_params = mock_smph.synchronize(challenge_params, scope)

        # Finalize sync
        self.assertRaises(ContainerNotRegistered, smartphone.check_challenge_response, smph_params)

    def test_15_synchronize_with_invalid_signature(self):
        # Registration
        mock_smph = self.test_03_register_smartphone_success()
        smartphone = find_container_by_serial(mock_smph.container_serial)

        # Init sync
        scope = "https://pi.net/container/synchronize"
        challenge_params = smartphone.create_challenge(scope)
        result_entries = challenge_params.keys()
        self.assertIn("nonce", result_entries)
        self.assertIn("time_stamp", result_entries)
        self.assertIn("enc_key_algorithm", result_entries)

        # Mock smartphone with another serial
        mock_smph.container_serial = "SMPH9999"
        smph_params = mock_smph.synchronize(challenge_params, scope)

        # Finalize sync
        self.assertRaises(ContainerInvalidChallenge, smartphone.check_challenge_response, smph_params)

    def test_16_synchronize_container_details(self):
        # Arrange
        smartphone_serial = init_container({"type": "smartphone"})["container_serial"]
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
        self.assertEqual(smartphone.serial, synced_container_details["container"]["serial"])
        # check tokens
        add_tokens = synced_container_details["tokens"]["add"]
        self.assertEqual(0, len(add_tokens))
        updated_tokens = synced_container_details["tokens"]["update"]
        for token in updated_tokens:
            self.assertIn(token["serial"], [hotp_token.get_serial(), totp_token.get_serial()])

        # Pass empty client container
        synced_container_details = smartphone.synchronize_container_details({})
        # check tokens
        add_tokens = synced_container_details["tokens"]["add"]
        self.assertEqual(2, len(add_tokens))

    def test_17_finalize_container_rollover(self):
        # create smartphone container with all possible token types
        smartphone_serial = init_container({"type": "smartphone"})["container_serial"]
        smartphone = find_container_by_serial(smartphone_serial)
        hotp_token = init_token({"genkey": True, "type": "hotp"})
        hotp_secret = hotp_token.token.get_otpkey().getKey().decode("utf-8")
        smartphone.add_token(hotp_token)
        totp_token = init_token({"genkey": True, "type": "totp"})
        totp_secret = totp_token.token.get_otpkey().getKey().decode("utf-8")
        smartphone.add_token(totp_token)
        push_token = init_token({"genkey": True, "type": "push"})
        push_secret = push_token.token.get_otpkey().getKey().decode("utf-8")
        smartphone.add_token(push_token)
        daypassword = init_token({"genkey": True, "type": "daypassword"})
        daypassword_secret = daypassword.token.get_otpkey().getKey().decode("utf-8")
        smartphone.add_token(daypassword)

        # rollover
        finalize_container_rollover(smartphone)

        # check token secrets
        new_hotp_secret = hotp_token.token.get_otpkey().getKey().decode("utf-8")
        self.assertNotEqual(hotp_secret, new_hotp_secret)
        new_totp_secret = totp_token.token.get_otpkey().getKey().decode("utf-8")
        self.assertNotEqual(totp_secret, new_totp_secret)
        new_push_secret = push_token.token.get_otpkey().getKey().decode("utf-8")
        self.assertNotEqual(push_secret, new_push_secret)
        new_daypassword_secret = daypassword.token.get_otpkey().getKey().decode("utf-8")
        self.assertNotEqual(daypassword_secret, new_daypassword_secret)

    def test_18_container_rollover(self):
        mock_smph = self.test_03_register_smartphone_success()
        smartphone = find_container_by_serial(mock_smph.container_serial)

        # Create Challenge for rollover
        scope = "https://pi.net/container/rollover"
        challenge_data = smartphone.create_challenge(scope)

        # Mock smartphone
        params = mock_smph.register_finalize(challenge_data["nonce"], challenge_data["time_stamp"], scope,
                                             smartphone.serial)

        # Rollover init
        init_result = init_container_rollover(smartphone, "https://pi.net/", 20, 10,
                                              "True", params)

        # Mock new smartphone
        scope = "https://pi.net/container/register/finalize"
        mock_smph_new = MockSmartphone(device_brand="AB", device_model="99")
        params = mock_smph_new.register_finalize(init_result["nonce"], init_result["time_stamp"], scope,
                                                 smartphone.serial)

        # Finalize registration
        finalize_registration(mock_smph_new.container_serial, params)

        # Check if container info is set correctly
        container_info = smartphone.get_container_info_dict()
        container_info_keys = container_info.keys()
        self.assertIn("public_key_client", container_info_keys)
        self.assertEqual(f"{mock_smph_new.device_brand} {mock_smph_new.device_model}", container_info["device"])
        self.assertEqual(RegistrationState.ROLLOVER_COMPLETED, smartphone.registration_state)
        self.assertEqual("https://pi.net/", container_info["server_url"])
        self.assertEqual("20", container_info["challenge_ttl"])

        # rollover entries removed
        self.assertNotIn("rollover_server_url", container_info_keys)
        self.assertNotIn("rollover_challenge_ttl", container_info_keys)

    def test_19_container_rollover_with_tokens(self):
        mock_smph = self.test_03_register_smartphone_success()
        smartphone = find_container_by_serial(mock_smph.container_serial)

        # Add tokens
        hotp = init_token({"genkey": "1", "type": "hotp", "otplen": 8, "hashlib": "sha256"})
        hotp_secret = hotp.token.get_otpkey().getKey().decode("utf-8")
        smartphone.add_token(hotp)
        totp = init_token({"genkey": "1", "type": "totp", "otplen": 8, "hashlib": "sha256", "timeStep": 60})
        totp_secret = totp.token.get_otpkey().getKey().decode("utf-8")
        smartphone.add_token(totp)
        sms = init_token({"type": "sms", "phone": "0123456789"})
        sms_secret = sms.token.get_otpkey().getKey().decode("utf-8")
        smartphone.add_token(sms)
        daypassword = init_token({"genkey": "1", "type": "daypassword", "hashlib": "sha256", "timeStep": 60})
        daypw_secret = daypassword.token.get_otpkey().getKey().decode("utf-8")
        smartphone.add_token(daypassword)

        # Create Challenge for rollover
        scope = "https://pi.net/container/rollover"
        challenge_data = smartphone.create_challenge(scope)

        # Mock smartphone
        params = mock_smph.register_finalize(challenge_data["nonce"], challenge_data["time_stamp"], scope,
                                             smartphone.serial)

        # Rollover init
        init_result = init_container_rollover(smartphone, "https://pi.net/", 20, 10,
                                              "True", params)

        # Mock new smartphone
        scope = "https://pi.net/container/register/finalize"
        mock_smph_new = MockSmartphone(device_brand="AB", device_model="99")
        params = mock_smph_new.register_finalize(init_result["nonce"], init_result["time_stamp"], scope,
                                                 smartphone.serial)

        # Finalize registration
        finalize_registration(mock_smph_new.container_serial, params)

        # Check token details
        # new tokens are rolled over: enrollment settings need to be the same and not reset to defaults
        hotp_dict = hotp.get_as_dict()
        self.assertEqual(8, hotp_dict["otplen"])
        self.assertEqual("sha256", hotp_dict["info"]["hashlib"])
        new_hotp_secret = hotp.token.get_otpkey().getKey().decode("utf-8")
        self.assertNotEqual(hotp_secret, new_hotp_secret)
        totp_dict = totp.get_as_dict()
        self.assertEqual(8, totp_dict["otplen"])
        self.assertEqual("sha256", totp_dict["info"]["hashlib"])
        self.assertEqual("60", totp_dict["info"]["timeStep"])
        new_totp_secret = totp.token.get_otpkey().getKey().decode("utf-8")
        self.assertNotEqual(totp_secret, new_totp_secret)
        sms_dict = sms.get_as_dict()
        self.assertEqual("0123456789", sms_dict["info"]["phone"])
        new_sms_secret = sms.token.get_otpkey().getKey().decode("utf-8")
        self.assertNotEqual(sms_secret, new_sms_secret)
        daypw_dict = daypassword.get_as_dict()
        self.assertEqual("sha256", daypw_dict["info"]["hashlib"])
        self.assertEqual("60", daypw_dict["info"]["timeStep"])
        new_daypw_secret = daypassword.token.get_otpkey().getKey().decode("utf-8")
        self.assertNotEqual(daypw_secret, new_daypw_secret)

    def test_20_container_rollover_aborted(self):
        mock_smph = self.test_03_register_smartphone_success()
        smartphone = find_container_by_serial(mock_smph.container_serial)

        # Add tokens
        hotp = init_token({"genkey": "1", "type": "hotp", "otplen": 8, "hashlib": "sha256"})
        smartphone.add_token(hotp)
        totp = init_token({"genkey": "1", "type": "totp", "otplen": 8, "hashlib": "sha256", "timeStep": 60})
        smartphone.add_token(totp)

        # Create Challenge for rollover
        scope = "https://pi.net/container/rollover"
        challenge_data = smartphone.create_challenge(scope)

        # Mock smartphone
        params = mock_smph.register_finalize(challenge_data["nonce"], challenge_data["time_stamp"], scope,
                                             smartphone.serial)

        # Rollover init
        init_container_rollover(smartphone, "https://pi.net/", 20, 10, "True", params)

        # Rollover is not completed by the new device. The old device is still active
        # Synchronize with old device
        client_container = {"serial": smartphone.serial, "type": "smartphone",
                            "tokens": [{"serial": hotp.get_serial(), "type": "hotp"},
                                       {"serial": totp.get_serial(), "type": "totp"}]}
        synced_container_details = smartphone.synchronize_container_details(client_container)
        self.assertEqual(0, len(synced_container_details["tokens"]["add"]))
        self.assertEqual(2, len(synced_container_details["tokens"]["update"]))

    def test_21_initial_synchronize_smartphone(self):
        # setup container
        smartphone_serial = init_container({"type": "smartphone"})["container_serial"]
        smartphone = find_container_by_serial(smartphone_serial)

        # Registration
        mock_smph = self.test_03_register_smartphone_success(smartphone_serial)
        smartphone.update_container_info(
            [TokenContainerInfoData(key="initially_synchronized", value="False", info_type=PI_INTERNAL)])

        # tokens
        hotp_token = init_token({"genkey": "1", "type": "hotp"})
        _, _, otp_dict = hotp_token.get_multi_otp(2)
        hotp_otps = list(otp_dict["otp"].values())
        totp_token = init_token({"genkey": "1", "type": "totp"})
        spass_token = init_token({"type": "spass"})

        # Init sync
        scope = "https://pi.net/container/synchronize"
        challenge_params = smartphone.create_challenge(scope)
        result_entries = challenge_params.keys()
        self.assertIn("nonce", result_entries)
        self.assertIn("time_stamp", result_entries)
        self.assertIn("enc_key_algorithm", result_entries)

        # Mock smartphone with known and unknown tokens for the server
        mock_smph.container = {"tokens": [{"type": "hotp", "otp": hotp_otps},  # known by the server
                                          {"type": "totp", "serial": totp_token.get_serial()},  # known by the server
                                          {"type": "hotp", "serial": "123456"},  # unknown to the server
                                          {"type": "spass", "serial": spass_token.get_serial()}]}  # invalid type
        smph_params = mock_smph.synchronize(challenge_params, scope)

        # Finalize sync
        smph_params.update({'scope': scope})
        allowed = smartphone.check_challenge_response(smph_params)
        self.assertTrue(allowed)
        smartphone.synchronize_container_details(mock_smph.container, True)

        # check tokens of the container on the server
        server_tokens = smartphone.get_tokens()
        self.assertEqual(2, len(server_tokens))
        server_serials = [token.get_serial() for token in server_tokens]
        self.assertIn(hotp_token.get_serial(), server_serials)
        self.assertIn(totp_token.get_serial(), server_serials)


class TokenContainerTemplateTestCase(MyTestCase):
    def test_01_create_delete_template_success(self):
        template_name = "test"
        template_id = create_container_template(container_type="generic",
                                                template_name=template_name,
                                                options={"tokens": [{"type": "hotp"}]})
        self.assertGreater(template_id, 0)

        template = get_template_obj(template_name)
        template.delete()

        self.assertRaises(ResourceNotFoundError, get_template_obj, template_name)

    def test_02_create_template_fail(self):
        template_name = "test"

        # wrong options type input
        self.assertRaises(ParameterError, create_container_template, container_type="smartphone",
                          template_name=template_name,
                          options="random")
        self.assertRaises(ResourceNotFoundError, get_template_obj, template_name)

        # wrong container type
        self.assertRaises(EnrollmentError, create_container_template, container_type="random",
                          template_name=template_name,
                          options={"tokens": [{"type": "hotp"}]})
        self.assertRaises(ResourceNotFoundError, get_template_obj, template_name)

        # wrong default type
        self.assertRaises(ParameterError, create_container_template, container_type="smartphone",
                          template_name=template_name,
                          default="random",
                          options={"tokens": [{"type": "hotp"}]})
        self.assertRaises(ResourceNotFoundError, get_template_obj, template_name)

    def test_03_get_class_type(self):
        # smartphone
        create_container_template(container_type="smartphone",
                                  template_name="smph",
                                  options={"tokens": [{"type": "hotp"}]})
        smph = get_template_obj("smph")
        self.assertEqual("smartphone", smph.get_class_type())
        smph.delete()

        # generic
        create_container_template(container_type="generic",
                                  template_name="generic",
                                  options={"tokens": [{"type": "hotp"}]})
        generic = get_template_obj("generic")
        self.assertEqual("generic", generic.get_class_type())
        generic.delete()

        # yubikey
        create_container_template(container_type="yubikey",
                                  template_name="yubikey",
                                  options={"tokens": [{"type": "hotp"}]})
        yubikey = get_template_obj("yubikey")
        self.assertEqual("yubikey", yubikey.get_class_type())
        yubikey.delete()

    def test_04_get_name(self):
        initial_name = "test"
        create_container_template(container_type="generic",
                                  template_name=initial_name,
                                  options={"tokens": [{"type": "hotp"}]})
        template = get_template_obj("test")
        # Check initial name
        self.assertEqual(initial_name, template.name)

        template.delete()

    def test_05_get_supported_token_types(self):
        # Check that the template token types are all supported by the corresponding container
        # Generic
        generic_token_types = TokenContainerClass.get_supported_token_types()
        template_generic_tokens = ContainerTemplateBase.get_supported_token_types()
        self.assertGreater(len(template_generic_tokens), 0)
        self.assertTrue(set(template_generic_tokens).issubset(set(generic_token_types)))

        # Smartphone
        smph_token_types = SmartphoneContainer.get_supported_token_types()
        template_smph_tokens = SmartphoneContainerTemplate.get_supported_token_types()
        self.assertGreater(len(template_smph_tokens), 0)
        self.assertTrue(set(template_smph_tokens).issubset(set(smph_token_types)))
        # All smartphone tokens must be a subset of the generic tokens
        self.assertTrue(set(smph_token_types).issubset(set(generic_token_types)))

        # Yubikey
        yubi_token_types = YubikeyContainer.get_supported_token_types()
        template_yubi_tokens = YubikeyContainerTemplate.get_supported_token_types()
        self.assertGreater(len(template_yubi_tokens), 0)
        self.assertTrue(set(template_yubi_tokens).issubset(set(yubi_token_types)))
        # All yubikey tokens must be a subset of the generic tokens
        self.assertTrue(set(yubi_token_types).issubset(set(generic_token_types)))

    def test_06_template_options_success(self):
        initial_options = {"tokens": [{"type": "hotp", "genkey": True}]}
        create_container_template(container_type="smartphone", template_name="test", options=initial_options)
        template = get_template_obj("test")

        # get options
        options = template.template_options
        self.assertIsInstance(options, str)
        self.assertEqual(json.dumps(initial_options), options)
        options_dict = template.get_template_options_as_dict()
        self.assertIsInstance(options_dict, dict)
        self.assertDictEqual(initial_options, options_dict)

        # set options
        new_options = {"tokens": [{"type": "hotp", "genkey": True},
                                  {"type": "totp", "genkey": True, "hashlib": "sha256"}]}
        template.template_options = new_options
        options = template.template_options
        self.assertEqual(json.dumps(new_options), options)
        options_dict = template.get_template_options_as_dict()
        self.assertIsInstance(options_dict, dict)
        self.assertDictEqual(new_options, options_dict)

        # Clean up
        template.delete()

    def test_07_template_options_fail(self):
        # smartphone
        initial_options = {"tokens": [{"type": "hotp", "genkey": True}]}
        create_container_template(container_type="smartphone", template_name="test", options=initial_options)
        template = get_template_obj("test")

        # set options as string
        new_options = {"tokens": [{"type": "hotp", "genkey": True},
                                  {"type": "totp", "genkey": True, "hashlib": "sha256"}],
                       "options": {}}
        self.assertRaises(ParameterError, setattr, template, "template_options", json.dumps(new_options))

        # set invalid token type
        invalid_options = {"tokens": [{"type": "spass"}]}
        self.assertRaises(ParameterError, setattr, template, "template_options", invalid_options)

        # Yubikey
        create_container_template(container_type="yubikey",
                                  template_name="yubi",
                                  options=initial_options)
        template_yubi = get_template_obj("yubi")

        # wrong token type
        template_options = {"tokens": [{"type": "totp", "genkey": True}, {"type": "spass"}]}
        self.assertRaises(ParameterError, setattr, template_yubi, "template_options", template_options)
        self.assertEqual(json.dumps(initial_options), template.template_options)

        # Clean up
        template.delete()
        template_yubi.delete()

    def test_08_template_default_success(self):
        template_name = "test"
        create_container_template(container_type="smartphone",
                                  template_name=template_name,
                                  default=True,
                                  options={})

        template = get_template_obj(template_name)
        self.assertTrue(template.default)

        # set default
        template.default = False
        self.assertFalse(template.default)

        template.delete()

    def test_09_template_default_fail(self):
        template_name = "test"
        create_container_template(container_type="smartphone",
                                  template_name=template_name,
                                  default=True,
                                  options={})
        template = get_template_obj(template_name)

        # set wrong type to default
        self.assertRaises(ParameterError, setattr, template, "default", "False")

        template.delete()

    def test_10_containers(self):
        create_container_template(container_type="smartphone",
                                  template_name="test",
                                  options={})
        template = get_template_obj("test")
        # create container with a template
        template_params = {"name": "test", "container_type": "smartphone", "template_options": {}}
        smph1 = init_container({"type": "smartphone", "template": template_params})["container_serial"]
        smph2 = init_container({"type": "smartphone", "template": template_params})["container_serial"]

        containers = template.containers
        self.assertEqual(2, len(containers))
        self.assertIn(containers[0].serial, [smph1, smph2])
        self.assertIn(containers[1].serial, [smph1, smph2])

        # clean up
        template.delete()

    def test_11_create_container_template_from_db_object_success(self):
        # Generic
        template_db = TokenContainerTemplate(name="test", container_type="generic", options="")
        template_db.save()
        template = create_container_template_from_db_object(template_db)
        self.assertIsInstance(template, ContainerTemplateBase)
        template.delete()

        # Smartphone
        template_db = TokenContainerTemplate(name="test", container_type="smartphone", options="")
        template_db.save()
        template = create_container_template_from_db_object(template_db)
        self.assertIsInstance(template, SmartphoneContainerTemplate)
        template.delete()

        # Yubikey
        template_db = TokenContainerTemplate(name="test", container_type="yubikey", options="")
        template_db.save()
        template = create_container_template_from_db_object(template_db)
        self.assertIsInstance(template, YubikeyContainerTemplate)
        template.delete()

    def test_12_create_container_template_from_db_object_fails(self):
        # Invalid type
        template_db = TokenContainerTemplate(name="test", container_type="random", options="")
        template_db.save()
        template = create_container_template_from_db_object(template_db)
        self.assertIsNone(template)
        template_db.delete()

    def test_13_get_template_obj_success(self):
        template_name = "test"
        create_container_template(container_type="smartphone",
                                  template_name=template_name,
                                  options={"tokens": [{"type": "hotp"}]})

        template = get_template_obj(template_name)
        self.assertIsInstance(template, SmartphoneContainerTemplate)
        self.assertEqual(template_name, template.name)

        template.delete()

    def test_14_get_template_obj_fail(self):
        # Pass non-existing template name
        self.assertRaises(ResourceNotFoundError, get_template_obj, "non-existing")

    def test_15_get_template_by_query(self):
        create_container_template(container_type="smartphone",
                                  template_name="smph",
                                  default=True,
                                  options={"tokens": [{"type": "totp"}]})
        create_container_template(container_type="generic",
                                  template_name="generic",
                                  options={"tokens": [{"type": "spass"}]})
        create_container_template(container_type="yubikey",
                                  template_name="yubi",
                                  options={})

        # Get all templates
        templates_res = get_templates_by_query(sortdir="asc", sortby="name")
        self.assertIn("templates", templates_res.keys())
        self.assertEqual(3, len(templates_res["templates"]))
        self.assertEqual("generic", templates_res["templates"][0]["name"])
        self.assertEqual("smph", templates_res["templates"][1]["name"])
        self.assertEqual("yubi", templates_res["templates"][2]["name"])

        # Sort descending
        templates_res = get_templates_by_query(sortdir="desc", sortby="name")
        self.assertIn("templates", templates_res.keys())
        self.assertEqual(3, len(templates_res["templates"]))
        self.assertEqual("yubi", templates_res["templates"][0]["name"])
        self.assertEqual("smph", templates_res["templates"][1]["name"])
        self.assertEqual("generic", templates_res["templates"][2]["name"])

        # Sort by type
        templates_res = get_templates_by_query(sortdir="asc", sortby="container_type")
        self.assertIn("templates", templates_res.keys())
        self.assertEqual(3, len(templates_res["templates"]))
        self.assertEqual("generic", templates_res["templates"][0]["name"])
        self.assertEqual("smph", templates_res["templates"][1]["name"])
        self.assertEqual("yubi", templates_res["templates"][2]["name"])

        # Sort by unknown column: use name instead
        templates_res = get_templates_by_query(sortdir="asc", sortby="random")
        self.assertIn("templates", templates_res.keys())
        self.assertEqual(3, len(templates_res["templates"]))
        self.assertEqual("generic", templates_res["templates"][0]["name"])
        self.assertEqual("smph", templates_res["templates"][1]["name"])
        self.assertEqual("yubi", templates_res["templates"][2]["name"])

        # Get smartphone templates
        templates_res = get_templates_by_query(container_type="smartphone")
        self.assertIn("templates", templates_res.keys())
        self.assertEqual(1, len(templates_res["templates"]))
        self.assertEqual("smph", templates_res["templates"][0]["name"])

        # Filter by name
        templates_res = get_templates_by_query(name="generic")
        self.assertIn("templates", templates_res.keys())
        self.assertEqual(1, len(templates_res["templates"]))
        self.assertEqual("generic", templates_res["templates"][0]["name"])

        # Filter by non-existing name
        templates_res = get_templates_by_query(name="random")
        self.assertIn("templates", templates_res.keys())
        self.assertEqual(0, len(templates_res["templates"]))

        # Filter by default
        templates_res = get_templates_by_query(default=True)
        self.assertIn("templates", templates_res.keys())
        self.assertEqual(1, len(templates_res["templates"]))
        self.assertEqual("smph", templates_res["templates"][0]["name"])

        # Clean up
        templates_res = get_templates_by_query()
        for template in templates_res["templates"]:
            template_obj = get_template_obj(template["name"])
            template_obj.delete()

    def test_16_get_templates_by_query_pagination(self):
        # Create templates
        for i in range(20):
            create_container_template(container_type="smartphone",
                                      template_name=f"smph{i}",
                                      options={"tokens": [{"type": "totp"}]})

        # Get all templates
        templates_res = get_templates_by_query(page=0, pagesize=10)
        self.assertEqual(20, templates_res["count"])
        self.assertEqual(10, len(templates_res["templates"]))
        self.assertEqual(2, templates_res["next"])
        self.assertIsNone(templates_res["prev"])
        self.assertEqual(1, templates_res["current"])

        # Clean up
        templates_res = get_templates_by_query()
        for template in templates_res["templates"]:
            template_obj = get_template_obj(template["name"])
            template_obj.delete()

    def test_17_compare_templates(self):
        # same templates but different order of entries
        template_a = {"template_options": {"tokens": [{"type": "hotp", "genkey": True, "hashlib": "sha1"},
                                                      {"type": "totp", "genkey": True, "hashlib": "sha256"}]}}
        template_b = {"template_options": {"tokens": [{"type": "totp", "hashlib": "sha256", "genkey": True},
                                                      {"genkey": True, "type": "hotp", "hashlib": "sha1"}]}}

        equal = compare_template_dicts(template_a, template_b)
        self.assertTrue(equal)

        # different templates
        template_a = {"template_options": {"tokens": [{"type": "totp", "genkey": True, "hashlib": "sha256"},
                                                      {"type": "totp", "genkey": True, "hashlib": "sha256"}]}}
        template_b = {"template_options": {"tokens": [{"type": "totp", "hashlib": "sha256", "genkey": True},
                                                      {"genkey": True, "type": "hotp", "hashlib": "sha1"}]}}

        equal = compare_template_dicts(template_a, template_b)
        self.assertFalse(equal)

        equal = compare_template_dicts(template_b, template_a)
        self.assertFalse(equal)

        # template is None
        equal = compare_template_dicts(template_a, None)
        self.assertFalse(equal)

        equal = compare_template_dicts(None, template_a)
        self.assertFalse(equal)

        # templates of different length
        template_b = {"template_options": {"tokens": [{"type": "totp", "genkey": True, "hashlib": "sha256"}]}}

        equal = compare_template_dicts(template_a, template_b)
        self.assertFalse(equal)

        equal = compare_template_dicts(template_b, template_a)
        self.assertFalse(equal)

    def test_18_set_default_template(self):
        # Set default template
        template1_name = "test"
        create_container_template(container_type="smartphone",
                                  template_name=template1_name,
                                  options={"tokens": [{"type": "hotp"}]})
        template1 = get_template_obj(template1_name)

        set_default_template(template1_name)
        # Check if default template is set
        self.assertTrue(template1.default)

        # Set another template from the same type as default
        template2_name = "test2"
        create_container_template(container_type="smartphone",
                                  template_name=template2_name,
                                  options={"tokens": [{"type": "hotp"}]})
        template2 = get_template_obj(template2_name)

        set_default_template(template2_name)
        # Check if default template is set
        self.assertTrue(template2.default)
        self.assertFalse(template1.default)

        # Set default template for another type
        template3_name = "test3"
        create_container_template(container_type="generic",
                                  template_name=template3_name,
                                  options={"tokens": [{"type": "hotp"}]})
        template3 = get_template_obj(template3_name)

        set_default_template(template3_name)
        # Check if default template is set
        self.assertTrue(template2.default)
        self.assertFalse(template1.default)
        self.assertTrue(template3.default)

        # Clean up
        template1.delete()
        template2.delete()
        template3.delete()

    def test_19_create_container_with_template_success(self):
        # Create template
        template_options = {"tokens": [{"type": "hotp", "genkey": True}, {"type": "totp", "genkey": True}]}
        create_container_template(container_type="smartphone",
                                  template_name="test",
                                  options=template_options)

        # Create container with template
        container_params = {"type": "smartphone", "template": {"name": "test", "container_type": "smartphone",
                                                               "template_options": template_options}}
        init_res = init_container(container_params)
        container_serial = init_res["container_serial"]
        template_tokens = init_res["template_tokens"]
        self.assertEqual(template_options["tokens"], template_tokens)
        container = find_container_by_serial(container_serial)

        # Delete template
        template = get_template_obj("test")
        template.delete()
        self.assertIsNone(container.template)

        # Clean up
        container.delete()

    def test_20_create_container_with_template_fail(self):
        # template and container type differ: container is created but not with template options
        template_options = {"tokens": [{"type": "hotp", "genkey": True}, {"type": "totp", "genkey": True}]}
        create_container_template(container_type="generic",
                                  template_name="test",
                                  options=template_options)

        container_params = {"type": "smartphone", "template": {"name": "test", "container_type": "generic",
                                                               "template_options": template_options}}
        init_res = init_container(container_params)
        container_serial = init_res["container_serial"]
        template_tokens = init_res["template_tokens"]
        container = find_container_by_serial(container_serial)
        self.assertEqual([], template_tokens)
        self.assertIsNone(container.template)

        # Clean up
        container.delete()
        get_template_obj("test").delete()

    def test_21_compare_container_with_template(self):
        # create template
        template_options = {"tokens": [{"type": "hotp", "genkey": True}, {"type": "totp", "genkey": True}]}
        create_container_template(container_type="generic",
                                  template_name="test",
                                  options=template_options)
        template = get_template_obj("test")

        # create container with tokens
        container_params = {"type": "generic", "template": {"name": "test", "container_type": "generic",
                                                            "template_options": template_options}}
        container_serial = init_container(container_params)["container_serial"]

        container = find_container_by_serial(container_serial)
        for token_details in [{"type": "hotp", "genkey": True}, {"type": "spass"}, {"type": "spass"}]:
            token = init_token(token_details)
            container.add_token(token)
        container.set_container_info({"hash_algorithm": "SHA1", "encrypt_algorithm": "AES"})

        # compare template and container: equal
        result = compare_template_with_container(template, container)
        token_result = result["tokens"]
        self.assertEqual(["totp"], token_result["missing"])
        self.assertEqual(['spass', 'spass'], token_result["additional"])

        template.delete()

    def test_22_get_template_options_as_dict(self):
        # create template
        template_options = {"tokens": [{"type": "hotp", "genkey": True}, {"type": "totp", "genkey": True}]}
        create_container_template(container_type="generic",
                                  template_name="test",
                                  options=template_options)
        template = get_template_obj("test")

        options_dict = template.get_template_options_as_dict()
        self.assertDictEqual(template_options, options_dict)

        template.template_options = {}
        options_dict = template.get_template_options_as_dict()
        self.assertDictEqual({'tokens': []}, options_dict)

        template.delete()

    def test_23_get_template_class_options(self):
        # generic template
        class_options = ContainerTemplateBase.get_template_class_options()
        self.assertDictEqual({}, class_options)

        # smartphone template
        class_options = SmartphoneContainerTemplate.get_template_class_options()
        smartphone_options = {SmartphoneOptions.KEY_ALGORITHM, SmartphoneOptions.ENCRYPT_KEY_ALGORITHM,
                              SmartphoneOptions.ENCRYPT_ALGORITHM, SmartphoneOptions.ENCRYPT_MODE,
                              SmartphoneOptions.HASH_ALGORITHM}
        self.assertSetEqual(smartphone_options, set(class_options.keys()))

        # yubikey template
        class_options = YubikeyContainerTemplate.get_template_class_options()
        self.assertDictEqual({}, class_options)
