
from privacyidea.lib.resolvers.EntraIDResolver import AUTHORITY
from privacyidea.lib.resolvers.HTTPResolver import (ATTRIBUTE_MAPPING, CONFIG_GET_USER_LIST, CONFIG_GET_USER_BY_ID,
                                                    CONFIG_GET_USER_BY_NAME, EDITABLE, HEADERS, ADVANCED,
                                                    CONFIG_AUTHORIZATION)
from privacyidea.models import (Resolver,
                                ResolverConfig,
                                db)
from .base import MyTestCase, MyApiTestCase


class ResolverModelTestCase(MyTestCase):
    '''
    Test the resolver on the database level
    '''

    def test_create_resolver(self):
        r = Resolver("r1", "passwdresolver")
        db.session.add(r)
        db.session.commit()
        self.assertTrue(r.name is not None, r.name)
        self.assertTrue(r.rtype is not None, r.rtype)
        # Add configuration to the resolver
        conf = ResolverConfig(r.id, "fileName", "somevalue")
        db.session.add(conf)
        db.session.commit()

        # Read Resolver
        r1 = Resolver.query.filter_by(name="r1").first()
        self.assertTrue(r1.rtype == "passwdresolver", r1.rtype)


class APIResolverTestCase(MyApiTestCase):
    '''
    Test the resolver on the API level
    '''

    def test_00_create_resolver(self):
        with self.app.test_request_context('/resolver/r1',
                                           data={"type": "passwdresolver",
                                                 "fileName": "/etc/passwd"},
                                           method='POST',
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(res.json['result']['status'], res.json)
            self.assertEqual(res.json['result']['value'], 1, res.json)

        # check if the resolver was created
        with self.app.test_request_context('/resolver/',
                                           method='GET',
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(b'"fileName": "/etc/passwd"' in res.data, res.data)
            self.assertTrue(b'"resolvername": "r1"' in res.data, res.data)

    def test_01_get_default_resolver_config(self):
        # HTTP
        with self.app.test_request_context('/resolver/httpresolver/default',
                                           method="GET",
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(res.json['result']['status'], res.json)
            # Test that the config fits for generic HTTP resolvers
            config = res.json['result']['value']
            self.assertFalse(config[EDITABLE])
            self.assertIn(HEADERS, config)

        # EntraID
        with self.app.test_request_context('/resolver/entraidresolver/default',
                                           method="GET",
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(res.json['result']['status'], res.json)
            # Test that the config fits for EntraID
            config = res.json['result']['value']
            self.assertFalse(config[EDITABLE])
            self.assertIn(ATTRIBUTE_MAPPING, config)
            self.assertTrue(config[ADVANCED])
            self.assertIn(CONFIG_GET_USER_LIST, config)
            self.assertIn(CONFIG_GET_USER_BY_ID, config)
            self.assertIn(CONFIG_GET_USER_BY_NAME, config)
            self.assertIn(AUTHORITY, config)

        # Keycloak
        with self.app.test_request_context('/resolver/keycloakresolver/default',
                                           method="GET",
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue(res.json['result']['status'], res.json)
            # Test that the config fits for Keycloak
            config = res.json['result']['value']
            self.assertFalse(config[EDITABLE])
            self.assertIn(ATTRIBUTE_MAPPING, config)
            self.assertEqual("username", config[ATTRIBUTE_MAPPING]["username"])
            self.assertTrue(config[ADVANCED])
            self.assertIn(CONFIG_GET_USER_LIST, config)
            self.assertIn(CONFIG_GET_USER_BY_ID, config)
            self.assertIn(CONFIG_GET_USER_BY_NAME, config)
            self.assertIn(CONFIG_AUTHORIZATION, config)
            self.assertNotIn(AUTHORITY, config)  # Keycloak does not use AUTHORITY

    def test_02_create_realm(self):
        realm = "realm1"
        resolvers = "r1, r2"
        with self.app.test_request_context('/realm/{0!s}'.format(realm),
                                           data={"resolvers": resolvers},
                                           method='POST',
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = res.json
            value = result.get("result").get("value")
            self.assertTrue('r1' in value["added"], res.data)
            self.assertTrue('r2' in value["failed"], res.data)


'''
        with self.app.test_request_context(
                '/api/1.0/comments/' + str(c.id),
                method='PUT',
                data=json.dumps({'bad': 123}),
                headers={'Content-Type': 'application/json'}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 401)
        '''
