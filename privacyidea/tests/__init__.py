# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  AGPLv3
#  contact:  http://www.linotp.org
#            http://www.lsexperts.de
#            linotp@lsexperts.de
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
'''
  Description:  Pylons application test package

This package assumes the Pylons environment is already loaded, such as
when this script is imported from the `nosetests --with-pylons=test.ini`
command.

This module initializes the application via ``websetup`` (`paster
setup-app`) and provides the base testing objects.

  Dependencies: -

'''
import json

import pylons.test
import os
import logging

from unittest import TestCase

from paste.deploy import appconfig
from paste.deploy import loadapp
from paste.script.appinstall import SetupCommand

from pylons import config, url
from pylons.configuration import config as env
from routes.util import URLGenerator
from webtest import TestApp

from privacyidea.config.environment import load_environment

import warnings
warnings.filterwarnings(action='ignore', category=DeprecationWarning)


def fxn():
    warnings.warn("deprecated", DeprecationWarning)

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    fxn()

from privacyidea.websetup import setup_app

LOG = logging.getLogger(__name__)

__all__ = ['environ', 'url', 'TestController']
SetupCommand('setup-app').run([config['__file__']])

environ = {}

def setUpPackage():
    '''
    setUpPackage is called before each test package / class

    this hook is used to re-initialize the database
    '''
    SetupCommand('setup-app').run([config['__file__']])
    return

def tearDownPackage():
    '''
    tearDownPackage is called when a test package is finished
    '''
    return

class TestController(TestCase):
    '''
    the TestController, which loads the privacyidea app upfront
    '''
    def __init__(self, *args, **kwargs):
        '''
        initialize the test class
        '''
        TestCase.__init__(self, *args, **kwargs)

        LOG.error("ConfigFile: %s " % config['__file__'])

        conffile = config['__file__']

        if pylons.test.pylonsapp:
            wsgiapp = pylons.test.pylonsapp
        else:
            wsgiapp = loadapp('config: %s' % config['__file__'])

        self.app = TestApp(wsgiapp)

        conf = None
        if conffile.startswith('/'):
            conf = appconfig('config:%s' % config['__file__'], relative_to=None)
        else:
            raise Exception('dont know how to load the application relatively')
        #conf = appconfig('config: %s' % config['__file__'], relative_to=rel)

        load_environment(conf.global_conf, conf.local_conf)
        self.appconf = conf

        url._push_object(URLGenerator(config['routes.map'], environ))

        self.isSelfTest = False
        if env.has_key("privacyidea.selfTest"):
            self.isSelfTest = True

        self.license = 'CE'
        return

    @classmethod
    def setup_class(cls):
        '''setup - create clean execution context by resetting database '''
        LOG.info("######## setup_class: %r" % cls)
        SetupCommand('setup-app').run([config['__file__']])
        return

    @classmethod
    def teardown_class(cls):
        '''teardown - cleanup of test class execution result'''
        LOG.info("######## teardown_class: %r" % cls)
        return


    def setUp(self):
        ''' here we do the system test init per test method '''
        self.__deleteAllRealms__()
        self.__deleteAllResolvers__()
        self.__createResolvers__()
        self.__createRealms__()

        return

    def tearDown(self):
        self.__deleteAllRealms__()
        self.__deleteAllResolvers__()
        return

    def __deleteAllRealms__(self):
        ''' get al realms and delete them '''

        response = self.app.get(url(controller='system', action='getRealms'))
        jresponse = json.loads(response.body)
        result = jresponse.get("result")
        values = result.get("value", {})
        for realmId in values:
            print realmId
            realm_desc = values.get(realmId)
            realm_name = realm_desc.get("realmname")
            parameters = {"realm":realm_name}
            resp = self.app.get(url(controller='system', action='delRealm'),
                                params=parameters)
            assert('"result": true' in resp)


    def __deleteAllResolvers__(self):
        ''' get all resolvers and delete them '''

        response = self.app.get(url(controller='system', action='getResolvers'))
        jresponse = json.loads(response.body)
        result = jresponse.get("result")
        values = result.get("value", {})
        for realmId in values:
            print realmId
            resolv_desc = values.get(realmId)
            resolv_name = resolv_desc.get("resolvername")
            parameters = {"resolver" : resolv_name}
            resp = self.app.get(url(controller='system', action='delResolver'),
                                params=parameters)
            assert('"status": true' in resp)

    def deleteAllPolicies(self):
        '''
        '''
        response = self.app.get(url(controller='system', action='getPolicy'),)
        self.assertTrue('"status": true' in response, response)

        body = json.loads(response.body)
        policies = body.get('result', {}).get('value', {}).keys()

        for policy in policies:
            self.delPolicy(policy)

        return

    def delPolicy(self, name='otpPin', remoteurl=None):

        parameters = {'name': name,
                      'selftest_admin': 'superadmin'
                      }
        r_url = url(controller='system', action='delPolicy')

        if remoteurl is not None:
            r_url = "%s/%s" % (remoteurl, "system/delPolicy")
            response = do_http(r_url, params=parameters)
        else:
            response = self.app.get(r_url, params=parameters)


        return response

    def deleteAllTokens(self):
        ''' get all tokens and delete them '''

        serials = []

        response = self.app.get(url(controller='admin', action='show'),
                                )
        self.assertTrue('"status": true' in response, response)

        body = json.loads(response.body)
        tokens = body.get('result', {}).get('value', {}).get('data', {})
        for token in tokens:
            serial = token.get("privacyIDEA.TokenSerialnumber")
            serials.append(serial)

        for serial in serials:
            self.removeTokenBySerial(serial)

        return

    def removeTokenBySerial(self, serial):
        ''' delete a token by its serial number '''

        parameters = {"serial": serial}

        response = self.app.get(url(controller='admin', action='remove'),
                                params=parameters)
        return response

    def __createResolvers__(self):
        '''
        create all base test resolvers
        '''
        parameters = {
            'name'      : 'myDefRes',
            'fileName'  : '%(here)s/tests/testdata/def-passwd',
            'type'      : 'passwdresolver'
            }
        resp = self.app.get(url(controller='system', action='setResolver'),
                                                            params=parameters)
        assert('"value": true' in resp)

        parameters = {
            'name'      : 'myOtherRes',
            'fileName'  : '%(here)s/tests/testdata/myDom-passwd',
            'type'      : 'passwdresolver'
            }
        resp = self.app.get(url(controller='system', action='setResolver'),
                                                            params=parameters)
        assert('"value": true' in resp)

    def __createRealms__(self):
        '''
            Idea: build out of two resolvers
                3 realms
                - 1 per resolver
                - 1 which contains both
            Question:
                search in the mix for the user root must find 2 users
        '''

        parameters = {
            'realm'     :'myDefRealm',
            'resolvers' :'privacyidea.lib.resolvers.PasswdIdResolver.IdResolver.myDefRes'
        }
        resp = self.app.get(url(controller='system', action='setRealm'),
                                                            params=parameters)
        assert('"value": true' in resp)

        resp = self.app.get(url(controller='system', action='getRealms'))
        assert('"default": "true"' in resp)

        parameters = {
            'realm'     :'myOtherRealm',
            'resolvers' :'privacyidea.lib.resolvers.PasswdIdResolver.IdResolver.myOtherRes'
        }
        resp = self.app.get(url(controller='system', action='setRealm'),
                                                             params=parameters)
        assert('"value": true' in resp)

        parameters = {
            'realm'     :'myMixRealm',
            'resolvers' :'privacyidea.lib.resolvers.PasswdIdResolver.IdResolver.' +
                         'myOtherRes,privacyidea.lib.resolvers.PasswdIdResolver.' +
                         'IdResolver.myDefRes'
        }
        resp = self.app.get(url(controller='system', action='setRealm'),
                            params=parameters)
        assert('"value": true' in resp)


        resp = self.app.get(url(controller='system', action='getRealms'))
        #assert('"default": "true"' in resp)

        resp = self.app.get(url(controller='system', action='getDefaultRealm'))
        #assert('"default": "true"' in resp)

        resp = self.app.get(url(controller='system', action='getConfig'))
        #assert('"default": "true"' in resp)




###eof#########################################################################

