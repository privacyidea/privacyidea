"""
This test file tests the lib.resolvers.py

The lib.resolvers.py only depends on the database model.
"""
import json
from .base import MyTestCase

from privacyidea.lib.resolver import (save_resolver,
                                      delete_resolver)

from privacyidea.lib.realm import (set_realm,
                                   get_realms,
                                   get_default_realm,
                                   realm_is_defined,
                                   set_default_realm,
                                   delete_realm)


class ResolverTestCase(MyTestCase):
    '''
    Test the token on the database level
    '''
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
                                    [self.resolvername1,
                                     self.resolvername2])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 2)

        (added, failed) = set_realm(self.realm_dot,
                                    [self.resolvername1,
                                     self.resolvername2])
        self.assertTrue(len(failed) == 0)
        self.assertTrue(len(added) == 2)

        # test the realms
        realms = get_realms()
        self.assertTrue(self.realm1 in realms, realms)
        self.assertTrue(realms.get("realm1").get("default"), realms)
        self.assertTrue(self.realm_dot in realms, realms)

        # delete dot realm
        delete_realm(self.realm_dot)
        
        # try to create realm with invalid name
        self.assertRaises(Exception, set_realm, "#####")
        
        # update the resolver list:
        (added, failed) = set_realm(self.realm1,
                                    [self.resolvername1,
                                     "non exiting"])
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
                                    [self.resolvername2])
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
