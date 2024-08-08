"""
This test file tests the lib.resolvers.py

The lib.resolvers.py only depends on the database model.
"""
import uuid

from privacyidea.models import NodeName
from .base import MyTestCase

from privacyidea.lib.resolver import (save_resolver,
                                      delete_resolver)

from privacyidea.lib.realm import (set_realm,
                                   get_realms,
                                   get_default_realm,
                                   realm_is_defined,
                                   set_default_realm,
                                   delete_realm, export_realms, import_realms)


class ResolverTestCase(MyTestCase):
    """
    Test the token on the database level
    """
    resolvername1 = "resolver1"
    resolvername2 = "Resolver2"
    realm1 = "realm1"
    realm_dot = "realm1.com"

    def test_01_create_realm(self):
        rid = save_resolver({"resolver": self.resolvername1,
                             "type": "passwdresolver",
                             "fileName": "/etc/passwd"})
        self.assertTrue(rid > 0, rid)

        rid = save_resolver({"resolver": self.resolvername2,
                             "type": "passwdresolver",
                             "fileName": "/etc/secrets"})
        self.assertTrue(rid > 0, rid)

        (added, failed) = set_realm(self.realm1,
                                    [{"name": self.resolvername1},
                                     {"name": self.resolvername2}])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 2)

        (added, failed) = set_realm(self.realm_dot,
                                    [{"name": self.resolvername1},
                                     {"name": self.resolvername2}])
        self.assertEqual(0, len(failed))
        self.assertEqual(2, len(added))

        # test the realms
        realms = get_realms()
        self.assertTrue(self.realm1 in realms, realms)
        self.assertTrue(realms.get("realm1").get("default"), realms)
        self.assertTrue(self.realm_dot in realms, realms)
        # check that no node is set
        self.assertEqual("", realms.get("realm1").get("resolver")[0].get("node"), realms)
        self.assertEqual("", realms.get("realm1").get("resolver")[1].get("node"), realms)

        # delete dot realm
        delete_realm(self.realm_dot)

        # try to create realm with invalid name
        self.assertRaises(Exception, set_realm, "#####")

        # update the resolver list:
        (added, failed) = set_realm(self.realm1,
                                    [{'name': self.resolvername1},
                                     {'name': "non exiting"}])
        self.assertTrue(len(failed) == 1)
        self.assertTrue(len(added) == 1)

        self.assertTrue(realm_is_defined(self.realm1))
        self.assertTrue(realm_is_defined("non exist") is False)

    def test_03_get_specific_realm(self):
        realm = get_realms(self.realm1)
        self.assertTrue(self.realm1 in realm, realm)
        self.assertTrue(len(realm) == 1, realm)

    def test_02_set_default_realm(self):
        (added, failed) = set_realm("realm2",
                                    [{'name': self.resolvername2}])
        self.assertTrue(len(added) == 1)
        self.assertTrue(len(failed) == 0)

        realm = get_default_realm()
        self.assertTrue(realm == self.realm1)

        set_default_realm("realm2")
        realm = get_default_realm()
        self.assertTrue(realm == "realm2")

        set_default_realm()
        realm = get_default_realm()
        self.assertTrue(realm is None, realm)

    def test_10_delete_realm(self):
        delete_realm(self.realm1)
        delete_realm("realm2")
        delete_resolver(self.resolvername1)
        delete_resolver(self.resolvername2)
        realms = get_realms()
        self.assertTrue(len(realms) == 0, realms)

    def test_20_realms_with_nodes(self):
        nd1_uuid = "8e4272a9-9037-40df-8aa3-976e4a04b5a9"
        nd2_uuid = "d1d7fde6-330f-4c12-88f3-58a1752594bf"
        NodeName(id=nd1_uuid, name="Node1").save()
        NodeName(id=nd2_uuid, name="Node2").save()

        save_resolver({"resolver": self.resolvername1,
                       "type": "passwdresolver",
                       "fileName": "/etc/passwd"})

        save_resolver({"resolver": self.resolvername2,
                       "type": "passwdresolver",
                       "fileName": "/etc/secrets"})

        (added, failed) = set_realm("realm1",
                                    [
                                        {'name': self.resolvername1,
                                         'node': uuid.UUID(nd1_uuid)}])
        self.assertIn(self.resolvername1, added, added)
        self.assertEqual(len(failed), 0, failed)
        realms_dict = get_realms()
        self.assertIn("realm1", realms_dict, realms_dict)
        resolver_list = realms_dict["realm1"]["resolver"]
        self.assertEqual(len(resolver_list), 1, realms_dict)
        self.assertEqual(resolver_list[0]["node"], nd1_uuid, resolver_list)

        # overwrite/update existing realm with resolvers with different nodes
        (added, failed) = set_realm("realm1",
                                    [
                                        {'name': self.resolvername1,
                                         'node': uuid.UUID(nd1_uuid)},
                                        {'name': self.resolvername1,
                                         'node': uuid.UUID(nd2_uuid)}])
        self.assertIn(self.resolvername1, added, added)
        self.assertEqual(len(failed), 0, failed)
        realms_dict = get_realms()
        self.assertIn("realm1", realms_dict, realms_dict)
        resolver_list = realms_dict["realm1"]["resolver"]
        self.assertEqual(len(resolver_list), 2, realms_dict)
        self.assertIn(nd1_uuid, [x.get('node') for x in resolver_list], resolver_list)
        self.assertIn(nd2_uuid, [x.get('node') for x in resolver_list], resolver_list)

        # different resolvers, one with node, one without
        (added, failed) = set_realm("realm1",
                                    [
                                        {'name': self.resolvername1,
                                         'node': uuid.UUID(nd1_uuid)},
                                        {'name': self.resolvername2}])
        self.assertIn(self.resolvername1, added, added)
        self.assertIn(self.resolvername2, added, added)
        self.assertEqual(len(failed), 0, failed)
        realms_dict = get_realms()
        self.assertIn("realm1", realms_dict, realms_dict)
        resolver_list = realms_dict["realm1"]["resolver"]
        self.assertEqual(len(resolver_list), 2, realms_dict)
        self.assertEqual(
            nd1_uuid,
            next(x.get('node') for x in resolver_list if x.get("name") == self.resolvername1),
            resolver_list)
        self.assertEqual(
            "",
            next(x.get('node') for x in resolver_list if x.get("name") == self.resolvername2),
            resolver_list)

        # different resolvers, different nodes
        (added, failed) = set_realm("realm1",
                                    [
                                        {'name': self.resolvername1,
                                         'node': uuid.UUID(nd1_uuid)},
                                        {'name': self.resolvername2,
                                         'node': uuid.UUID(nd2_uuid)}])
        self.assertIn(self.resolvername1, added, added)
        self.assertIn(self.resolvername2, added, added)
        self.assertEqual(len(failed), 0, failed)
        realms_dict = get_realms()
        self.assertIn("realm1", realms_dict, realms_dict)
        resolver_list = realms_dict["realm1"]["resolver"]
        self.assertEqual(len(resolver_list), 2, realms_dict)
        self.assertEqual(
            nd1_uuid,
            next(x.get('node') for x in resolver_list if x.get("name") == self.resolvername1),
            resolver_list)
        self.assertEqual(
            nd2_uuid,
            next(x.get('node') for x in resolver_list if x.get("name") == self.resolvername2),
            resolver_list)

        delete_realm('realm1')
        NodeName.query.filter_by(id=nd1_uuid).delete()
        NodeName.query.filter_by(id=nd2_uuid).delete()

    def test_30_realm_import_export(self):
        nd1_uuid = "8e4272a9-9037-40df-8aa3-976e4a04b5a9"
        nd2_uuid = "d1d7fde6-330f-4c12-88f3-58a1752594bf"
        NodeName(id=nd1_uuid, name="Node1").save()
        NodeName(id=nd2_uuid, name="Node2").save()

        save_resolver({"resolver": self.resolvername1,
                       "type": "passwdresolver",
                       "fileName": "/etc/passwd"})

        save_resolver({"resolver": self.resolvername2,
                       "type": "passwdresolver",
                       "fileName": "/etc/secrets"})

        set_realm("realm1",
                  [
                      {'name': self.resolvername1,
                       'node': uuid.UUID(nd1_uuid)},
                      {'name': self.resolvername1}])
        realm_exp = export_realms("realm1")
        self.assertIn("realm1", realm_exp, realm_exp)
        self.assertTrue(realm_exp["realm1"]["default"], realm_exp)
        self.assertIn(self.resolvername1, [x["name"] for x in realm_exp["realm1"]["resolver"]], realm_exp)
        self.assertIn(nd1_uuid, [x["node"] for x in realm_exp["realm1"]["resolver"]], realm_exp)

        import_dict = {
            'realm2': {'id': 2, 'option': '', 'default': False, 'resolver': [
                {'priority': None, 'name': 'Resolver2', 'type': 'passwdresolver',
                 'node': nd2_uuid},
                {'priority': None, 'name': 'resolver1', 'type': 'passwdresolver',
                 'node': ''}]}}

        import_realms(import_dict)
        realms_dict = get_realms()
        self.assertEqual(len(realms_dict), 2, realms_dict)
        self.assertIn("realm2", realms_dict, realms_dict)
        resolver_list = realms_dict["realm2"]["resolver"]
        self.assertEqual(len(resolver_list), 2, realms_dict)
        self.assertIn(nd2_uuid, [x.get('node') for x in resolver_list], resolver_list)
        self.assertIn(self.resolvername2, [x.get('name') for x in resolver_list], resolver_list)

        delete_realm('realm1')
        delete_realm('realm2')
        delete_resolver("resolver1")
        delete_resolver("Resolver2")
        NodeName.query.filter_by(id=nd1_uuid).delete()
        NodeName.query.filter_by(id=nd2_uuid).delete()
