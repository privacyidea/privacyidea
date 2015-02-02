import unittest
import json
from privacyidea.app import create_app
from privacyidea.models import (Resolver,
                                ResolverConfig,
                                Realm,
                                db)
from .base import MyTestCase


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
        self.assertTrue(r1.rtype=="passwdresolver", r1.rtype)


class APIResolverTestCase(MyTestCase):
    '''
    Test the resolver on the API level
    '''
       
    def test_00_create_resolver(self):
        
        with self.app.test_request_context('/resolver/r1',
                                           data={u"type": u"passwdresolver",
                                                 u"fileName": u"/etc/passwd"},
                                           method='POST',
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue('"status": true' in res.data, res.data)
            self.assertTrue('"value": 1' in res.data, res.data)
                    
        # check if the resolver was created
        with self.app.test_request_context('/resolver/',
                                           method='GET',
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            self.assertTrue('"fileName": "/etc/passwd"' in res.data, res.data)
            self.assertTrue('"resolvername": "r1"' in res.data, res.data)
            
    def test_01_create_realm(self):
        realm = u"realm1"
        resolvers = u"r1, r2"
        with self.app.test_request_context('/realm/%s' % realm,
                                           data={u"resolvers": resolvers},
                                           method='POST',
                                           headers={"Authorization": self.at}):
            res = self.app.full_dispatch_request()
            self.assertTrue(res.status_code == 200, res)
            result = json.loads(res.data)
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
