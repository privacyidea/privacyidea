from privacyidea.lib.container import delete_container_by_id, find_container_by_id, \
    find_container_by_serial, init_container, get_all_containers
from privacyidea.lib.container import get_container_classes
from privacyidea.lib.error import ResourceNotFoundError, ParameterError, EnrollmentError
from privacyidea.lib.realm import set_realm
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.token import init_token
from privacyidea.lib.user import User
from privacyidea.models import TokenContainer
from .base import MyTestCase


class TokenContainerManagementTestCase(MyTestCase):

    def test_01_create_empty_container(self):
        serial = init_container({"type": "Generic", "description": "test container"})
        container = find_container_by_serial(serial)
        self.assertEqual("test container", container.description)
        self.assertIsNotNone(container.serial)
        self.assertTrue(len(container.tokens) == 0)
        rid = container.delete()
        self.assertTrue(rid > 0)

        # Init container with realm
        self.setUp_user_realms()
        serial = init_container({"type": "Generic", "description": "test container", "realm": self.realm1})
        container = find_container_by_serial(serial)
        self.assertEqual(self.realm1, container.realms[0].name)

    def test_02_fails(self):
        self.assertRaises(ParameterError, delete_container_by_id, None)
        self.assertRaises(ResourceNotFoundError, delete_container_by_id, 11)
        self.assertRaises(ResourceNotFoundError, find_container_by_id, 11)
        self.assertRaises(ResourceNotFoundError, find_container_by_serial, "thisdoesnotexist")
        # Unknown container type raises exception
        self.assertRaises(EnrollmentError, init_container, {"type": "doesnotexist"})

    def test_03_container_with_tokens_users(self):
        # Create users and tokens first
        self.setUp_user_realms()

        # Create a container with tokens and user
        serial = init_container({"type": "generic", "description": "test container"})
        container = find_container_by_serial(serial)
        user_hans = User(login="hans", realm=self.realm1, resolver=self.resolvername1)
        container.add_user(user_hans)
        tokens = []
        params = {"genkey": "1"}
        for i in range(5):
            t = init_token(params, user=user_hans)
            tokens.append(t)
            container.add_token(t)
        all_serials = [t.get_serial() for t in tokens]

        self.assertEqual(5, len(container.get_tokens()))
        self.assertEqual("test container", container.description)
        self.assertEqual(1, len(container.get_users()))

        # Manipulate the tokens
        to_remove = [t for t in tokens[0:2]]
        to_remove_serials = [t.get_serial() for t in to_remove]
        self.assertEqual(2, len(to_remove_serials))
        for serial in to_remove_serials:
            container.remove_token(serial)
        self.assertEqual(3, len(container.tokens))
        for token in to_remove:
            container.add_token(token)
        self.assertEqual(5, len(container.tokens))
        for serial in [t.get_serial() for t in container.tokens]:
            self.assertTrue(serial in all_serials)

        # Manipulate the user
        cusers = container.get_users()
        for u in cusers:
            self.assertTrue(container.remove_user(u) > 0)
        self.assertEqual(0, len(container.get_users()))
        container.add_user(user_hans)
        self.assertEqual(1, len(container.get_users()))

    def test_04_get_all_containers_paginate(self):
        TokenContainer.query.delete()
        types = ["Smartphone", "generic", "Yubikey", "Smartphone", "generic", "Yubikey"]
        container_serials = []
        for t in types:
            serial = init_container({"type": t, "description": "test container"})
            container_serials.append(serial)

        # Filter for container serial
        containerdata = get_all_containers(serial=container_serials[3], pagesize=15)
        self.assertEqual(1, containerdata["count"])
        self.assertEqual(containerdata["containers"][0].serial, container_serials[3])

        # filter for type
        containerdata = get_all_containers(ctype="generic", pagesize=15)
        for container in containerdata["containers"]:
            self.assertEqual(container.type, "generic")
        self.assertEqual(2, containerdata["count"])

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
        containerdata = get_all_containers(token_serial=token_serials[1], pagesize=15)
        for container in containerdata["containers"]:
            self.assertTrue(container.serial in container_serials[2:4])
        self.assertEqual(2, containerdata["count"])

    def test_05_set_realms(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        container_serial = init_container({"type": "generic", "description": "test container"})
        container = find_container_by_serial(container_serial)

        # Set existing realms
        container.set_realms([self.realm1, self.realm2])
        container_realms = [realm.name for realm in container.realms]
        self.assertIn(self.realm1, container_realms)
        self.assertIn(self.realm2, container_realms)

        # Set one non-existing realm
        result = container.set_realms(["nonexisting", self.realm2])
        self.assertTrue(result['deleted'])
        self.assertFalse(result['nonexisting'])
        self.assertTrue(result[self.realm2])
        container_realms = [realm.name for realm in container.realms]
        self.assertNotIn("nonexisting", container_realms)
        self.assertIn(self.realm2, container_realms)

        # Set empty realm
        result = container.set_realms([""])
        self.assertTrue(result['deleted'])
        container_realms = [realm.name for realm in container.realms]
        self.assertEqual(0, len(container_realms))

        # Clean up
        container.delete()

    def test_06_add_realms(self):
        self.setUp_user_realms()
        self.setUp_user_realm2()
        container_serial = init_container({"type": "generic", "description": "test container"})
        container = find_container_by_serial(container_serial)

        # Add existing realm
        result = container.set_realms([self.realm1], add=True)
        self.assertFalse(result['deleted'])
        container_realms = [realm.name for realm in container.realms]
        self.assertIn(self.realm1, container_realms)

        # Add same realm
        result = container.set_realms([self.realm1], add=True)
        self.assertFalse(result[self.realm1])

        # Add one non-existing realm
        result = container.set_realms(["nonexisting", self.realm2], add=True)
        self.assertFalse(result['deleted'])
        self.assertFalse(result['nonexisting'])
        self.assertTrue(result[self.realm2])
        container_realms = [realm.name for realm in container.realms]
        self.assertNotIn("nonexisting", container_realms)
        self.assertIn(self.realm2, container_realms)
        self.assertIn(self.realm1, container_realms)

        # Add empty realm
        result = container.set_realms([""], add=True)
        self.assertFalse(result['deleted'])
        container_realms = [realm.name for realm in container.realms]
        self.assertEqual(2, len(container_realms))

        # Clean up
        container.delete()

    def test_99_container_classes(self):
        classes = get_container_classes()
        policies = {}
        for k, v in classes.items():
            policies[k] = v.get_container_policy_info()
