"""
This test file tests the lib.config

The lib.config only depends on the database model.
"""
from .base import MyTestCase
from privacyidea.lib.config import (get_resolver_list,
                                    get_resolver_classes,
                                    get_resolver_class_dict,
                                    get_resolver_types,
                                    get_resolver_module_list,
                                    get_from_config,
                                    get_privacyidea_config,
                                    set_privacyidea_config,
                                    delete_privacyidea_config,
                                    get_token_list,
                                    get_token_module_list,
                                    get_token_class_dict,
                                    get_token_types,
                                    get_token_classes, get_token_prefix,
                                    get_machine_resolver_class_dict,
                                    get_privacyidea_node, get_privacyidea_nodes,
                                    this, get_config_object, update_config_object)
from privacyidea.lib.resolvers.PasswdIdResolver import IdResolver as PWResolver
from privacyidea.lib.tokens.hotptoken import HotpTokenClass
from privacyidea.lib.tokens.totptoken import TotpTokenClass
from flask import current_app
import importlib


class ConfigTestCase(MyTestCase):
    """
    Test the config on the database level
    """
    def test_00_get_config(self):
        # set the config
        set_privacyidea_config(key="Hallo", value="What?", typ="string",
                               desc="Some dumb value")

        # get the complete config
        conf = get_from_config()
        self.assertTrue("Hallo" in conf, conf)

        conf = get_from_config("Hallo")
        self.assertTrue(conf == "What?", conf)

        conf = get_from_config("Hello", "Does not exist")
        self.assertTrue(conf == "Does not exist", conf)

        conf = get_privacyidea_config()
        self.assertTrue("Hallo" in conf, conf)

        # delete privacyidea config
        delete_privacyidea_config("Hallo")
        conf = get_from_config("Hallo")
        self.assertFalse(conf == "What?", conf)

        # set more values to create a timestamp and overwrite
        set_privacyidea_config(key="k1", value="v1")
        set_privacyidea_config(key="k2", value="v2")
        set_privacyidea_config(key="k3", value="v3")
        conf = get_from_config("k3")
        self.assertTrue(conf == "v3", conf)
        set_privacyidea_config(key="k3", value="new", typ="string", desc="n")
        conf = get_from_config("k3")
        self.assertTrue(conf == "new", conf)

    def test_01_resolver(self):
        r = get_resolver_list()
        self.assertTrue("privacyidea.lib.resolvers.PasswdIdResolver" in r, r)
        self.assertTrue("privacyidea.lib.resolvers.LDAPIdResolver" in r, r)
        self.assertTrue("privacyidea.lib.resolvers.SCIMIdResolver" in r, r)
        self.assertTrue("privacyidea.lib.resolvers.SQLIdResolver" in r, r)

        # check modules
        mlist = get_resolver_module_list()
        mod_name = "privacyidea.lib.resolvers.PasswdIdResolver"
        module = importlib.import_module(mod_name)

        self.assertTrue(module in mlist, mlist)

        r = get_resolver_classes()
        self.assertTrue(PWResolver in r, r)
        # resolver classes must be available here
        self.assertTrue("pi_resolver_classes" in this.config, this.config)
        self.assertTrue("pi_resolver_types" in this.config, this.config)

        # Class dict
        (classes, types) = get_resolver_class_dict()
        self.assertTrue('privacyidea.lib.resolvers.PasswdIdResolver'
                        '.IdResolver' in classes, classes)
        self.assertTrue(classes.get(
            'privacyidea.lib.resolvers.PasswdIdResolver.IdResolver') ==
                        PWResolver, classes)
        self.assertTrue('privacyidea.lib.resolvers.PasswdIdResolver'
                        '.IdResolver' in types, types)
        self.assertTrue(types.get('privacyidea.lib.resolvers.PasswdIdResolver'
                        '.IdResolver') == "passwdresolver", types)

        # With calling 'get_resolver_classes()' the resolver types will also be cached
        self.assertTrue("pi_resolver_types" in this.config, this.config)
        # When the resolvers are determined, they are stored
        types = get_resolver_types()
        self.assertTrue("passwdresolver" in types, types)

    def test_02_token(self):
        r = get_token_list()
        self.assertTrue("privacyidea.lib.tokens.totptoken" in r, r)
        self.assertTrue("privacyidea.lib.tokens.hotptoken" in r, r)

        # check modules
        mlist = get_token_module_list()
        mod_name = "privacyidea.lib.tokens.totptoken"
        module = importlib.import_module(mod_name)
        self.assertTrue(module in mlist, mlist)

#        r = get_resolver_classes()
#        self.assertTrue(UserResolver in r, r)
#        self.assertTrue(PWResolver in r, r)

        # get_token_class_dict
        (classes, types) = get_token_class_dict()
        self.assertTrue('privacyidea.lib.tokens.hotptoken.HotpTokenClass'
                        in classes, classes)
        self.assertTrue(classes.get(
            'privacyidea.lib.tokens.hotptoken.HotpTokenClass') ==
                        HotpTokenClass, classes)
        self.assertTrue('privacyidea.lib.tokens.totptoken.TotpTokenClass'
                        in classes, classes)
        self.assertTrue(classes.get(
            'privacyidea.lib.tokens.totptoken.TotpTokenClass') ==
                        TotpTokenClass, classes)

        self.assertTrue('privacyidea.lib.tokens.hotptoken.HotpTokenClass'
                        in types, types)
        self.assertTrue('privacyidea.lib.tokens.totptoken.TotpTokenClass'
                        in types, types)
        self.assertTrue(types.get('privacyidea.lib.tokens.hotptoken'
                                  '.HotpTokenClass') == "hotp", types)
        self.assertTrue(types.get('privacyidea.lib.tokens.totptoken'
                                  '.TotpTokenClass') == "totp", types)

        types = get_token_types()
        self.assertTrue("totp" in types, types)
        self.assertTrue("hotp" in types, types)

        # token classes are cached with calling 'get_token_types()'
        self.assertTrue("pi_token_classes" in this.config, this.config)
        self.assertTrue("pi_token_types" in this.config, this.config)
        r = get_token_classes()
        self.assertTrue(TotpTokenClass in r, r)
        self.assertTrue(HotpTokenClass in r, r)

    def test_03_token_prefix(self):
        prefix = get_token_prefix("totp")
        self.assertTrue(prefix == "TOTP", prefix)

        prefix = get_token_prefix("X_Y_Z", "does not exist")
        self.assertTrue(prefix == "does not exist", prefix)

        prefix = get_token_prefix()
        self.assertTrue(prefix.get("totp") == "TOTP", prefix)
        self.assertTrue(prefix.get("hotp") == "OATH", prefix)

    def test_04_store_encrypted_values(self):
        r = set_privacyidea_config("mySecretData", "soho",
                                   typ="password", desc="Very important")
        self.assertTrue(r == "insert", r)

        r = get_from_config("mySecretData")
        self.assertTrue(r == "soho", r)

        r = get_from_config()
        self.assertTrue(r.get("mySecretData") == "soho",
                        r.get("mySecretData"))

    def test_05_machine_resolvers(self):
        (classes, types) = get_machine_resolver_class_dict()
        self.assertTrue("hosts" in types.values(), list(types.values()))
        self.assertTrue("privacyidea.lib.machines.hosts.HostsMachineResolver"
                        in classes, classes)

    def test_06_public_and_admin(self):
        # This tests the new public available config
        set_privacyidea_config("publicInfo1", "info1", typ="public")
        set_privacyidea_config("publicInfo2", "info2", typ="public")
        set_privacyidea_config("secretInfo1", "info1")

        # Get administrators info
        a = get_from_config()
        self.assertTrue("secretInfo1" in a)
        self.assertTrue("publicInfo1" in a)
        a = get_from_config("publicInfo1")
        self.assertEqual(a, "info1")
        a = get_from_config("secretInfo1")
        self.assertEqual(a, "info1")

        # Get public info as user
        a = get_from_config()
        self.assertTrue("publicInfo1" in a)
        a = get_from_config("publicInfo1")
        self.assertEqual(a, "info1")

        # Not able to get private info as user
        a = get_from_config(role="public")
        self.assertTrue("secretInfo1" not in a)
        a = get_from_config("secretInfo1", role="public")
        self.assertEqual(a, None)

    def test_07_node_names(self):
        node = get_privacyidea_node()
        self.assertEqual(node, "Node1")
        nodes = get_privacyidea_nodes()
        self.assertTrue("Node1" in nodes)
        self.assertTrue("Node2" in nodes)

    def test_08_config_object(self):
        set_privacyidea_config(key="k1", value="v1")
        self.assertEqual(get_config_object().get_config("k1"), "v1")
        set_privacyidea_config(key="k1", value="v2")
        # not updated yet
        self.assertEqual(get_config_object().get_config("k1"), "v1")
        # updated now
        self.assertEqual(update_config_object().get_config("k1"), "v2")
