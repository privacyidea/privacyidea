from privacyidea.lib.container import delete_container_by_id, find_container_by_id, \
    find_container_by_serial, init_container
from privacyidea.lib.container import get_container_classes
from privacyidea.lib.error import ResourceNotFoundError, ParameterError, EnrollmentError
from privacyidea.lib.realm import set_realm
from privacyidea.lib.resolver import save_resolver
from privacyidea.lib.token import init_token
from privacyidea.lib.user import User
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

    def test_02_fails(self):
        self.assertRaises(ParameterError, delete_container_by_id, None)
        self.assertRaises(ResourceNotFoundError, delete_container_by_id, 11)
        self.assertRaises(ResourceNotFoundError, find_container_by_id, 11)
        self.assertRaises(ResourceNotFoundError, find_container_by_serial, "thisdoesnotexist")
        # Unknown container type raises exception
        self.assertRaises(EnrollmentError, init_container, {"type": "doesnotexist"})

    def test_03_container_with_tokens_users(self):
        # Create users and tokens first
        rid = save_resolver({"resolver": self.resolvername1,
                             "type": "passwdresolver",
                             "fileName": "tests/testdata/passwd"})
        self.assertTrue(rid > 0, rid)

        (added, failed) = set_realm(self.realm1, [{'name': self.resolvername1}])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 1)

        # Create a container with tokens and users
        serial = init_container({"type": "generic", "description": "test container"})
        container = find_container_by_serial(serial)
        user_root = User(login="root", realm=self.realm1, resolver=self.resolvername1)
        user_statd = User(login="statd", realm=self.realm1, resolver=self.resolvername1)
        users = [user_root, user_statd]
        for u in users:
            container.add_user(u)
        tokens = []
        params = {"genkey": "1"}
        for i in range(5):
            t = init_token(params, user=user_root)
            tokens.append(t)
            container.add_token(t)
        all_serials = [t.get_serial() for t in tokens]

        self.assertEqual(5, len(container.get_tokens()))
        self.assertEqual("test container", container.description)
        self.assertEqual(2, len(container.get_users()))

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

        # Manipulate the users
        cusers = container.get_users()
        for u in cusers:
            self.assertTrue(container.remove_user(u) > 0)
        self.assertEqual(0, len(container.get_users()))
        for u in users:
            container.add_user(u)
        self.assertEqual(2, len(container.get_users()))

    def test_99_container_classes(self):
        classes = get_container_classes()
        policies = {}
        for k, v in classes.items():
            policies[k] = v.get_container_policy_info()
