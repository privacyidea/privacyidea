# -*- coding: utf-8 -*-
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
  Description:  functional tests
                
  Dependencies: -

'''

import logging
import random
from datetime import datetime
from datetime import timedelta

import json


from sqlalchemy.engine import create_engine
import sqlalchemy

from privacyidea.tests import TestController, url

log = logging.getLogger(__name__)


class SQLData(object):

    def __init__(self, connect='sqlite:///:memory:'):
        self.userTable = 'Config'

        self.connection = None
        try:
            self.engine = create_engine(connect)
            connection = self.engine.connect()
        except Exception as e:
            print "%r" % e
        self.connection = connection
        return

    def addData(self, key, value, typ, description):
        iStr = """
            INSERT INTO "%s"( "Key", "Value", "Type", "Description")
            VALUES (:key, :value, :typ, :description);
            """ % (self.userTable)

        if "mysql" in self.engine.driver:
            iStr = """
            INSERT INTO %s (%s.Key, Value, Type, Description)
            VALUES (:key, :value, :typ, :description);
            """ % (self.userTable, self.userTable)


        intoStr = iStr

        t = sqlalchemy.sql.expression.text(intoStr)

        self.connection.execute(t, key=key, value=value, typ=typ, description=description)
        return

    def updateData(self, key, value):
        uStr = 'UPDATE "%s"  SET "Value"=:value WHERE "Key" = :key;'
        if "mysql" in self.engine.driver:
            uStr = 'UPDATE %s  SET Value=:value WHERE Config.Key = :key;'

        updateStr = uStr % (self.userTable)

        t = sqlalchemy.sql.expression.text(updateStr)
        self.connection.execute(t, key=key, value=value)
        return

    def query(self):
        selectStr = "select * from %s" % (self.userTable)
        result = self.connection.execute(selectStr)
        rows = []
        for row in result:
            rows.append(row)
            print unicode(row)
        return

    def delData(self, key):
        dStr = 'DELETE FROM "%s" WHERE "Key"=:key;' % (self.userTable)
        if "mysql" in self.engine.driver:
            dStr = ('DELETE FROM %s WHERE %s.Key=:key;' %
                    (self.userTable, self.userTable))

        delStr = dStr
        t = sqlalchemy.sql.expression.text(delStr)
        self.connection.execute(t, key=key)
        return


    def close(self):
        self.connection.close()


    def __del__(self):
        self.connection.close()






class TestReplication(TestController):

    def setUp(self):

        #self.appconf = self.app.app.app.apps[1].application.app.application.app.app.app.config
        self.sqlconnect = self.appconf.get('sqlalchemy.url')
        sqlData = SQLData(connect=self.sqlconnect)
        log.debug(sqlData)

        return

    def tearDown(self):
        ''' Overwrite parent tear down, which removes all realms '''
        return

    def addData(self, key, value, description):

        sqlData = SQLData(connect=self.sqlconnect)
        typ = type(value).__name__
        sqlData.addData(key, value, typ, description)
        sec = random.randrange(1, 9)
        sqlData.updateData("privacyidea.Config", str(datetime.now()
                                               + timedelta(milliseconds=sec)))
        sqlData.close()

        return


    def delData(self, key):

        sqlData = SQLData(connect=self.sqlconnect)
        sqlData.delData(key)

        sec = random.randrange(1, 9)
        sqlData.updateData("privacyidea.Config", str(datetime.now()
                                               + timedelta(milliseconds=sec)))
        sqlData.close()

        return

    def addToken(self, user):

        param = { 'user': user, 'pin':user, 'serial': 's' + user, 'type':'spass' }
        response = self.app.get(url(controller='admin', action='init'), params=param)
        assert '"status": true,' in response

        return

    def authToken(self, user):

        param = { 'user': user, 'pass':user}
        response = self.app.get(url(controller='validate', action='check'), params=param)
        return response

    def showTokens(self):

        param = None
        response = self.app.get(url(controller='admin', action='show'), params=param)
        assert '"status": true,' in response
        return response


    def test_replication(self):
        '''
            test replication of an simple config entry

            Description:
            - put privacyIDEA in replication aware mode
            - add a new entry in the Config Data vi SQL + update the timestamp
            - query the Config (system/getConfig, which should show the entry

            - del a entry in the Config Data vi SQL + update the timestamp
            - query the Config (system/getConfig, which should show the entry no more

        '''
        ''' 0. '''
        parameters = {'enableReplication' : 'true' }
        resp = self.app.get(url(controller='system', action='setConfig'), params=parameters)
        assert('"setConfig enableReplication:true": true' in resp)

        ''' 1. '''
        self.addData('replication', 'test1', 'test data')

        ''' 2. '''
        resp = self.app.get(url(controller='system', action='getConfig'))
        assert('"replication": "test1"' in resp)


        ''' 3. '''
        self.delData('replication')

        ''' 4. '''
        resp = self.app.get(url(controller='system', action='getConfig'))
        res = ('"replication": "test1"' in resp)
        assert (res == False)

        ''' 5 - cleanup'''
        parameters = {'key':'enableReplication' }
        resp = self.app.get(url(controller='system', action='delConfig'), params=parameters)
        assert('"delConfig enableReplication": true' in resp)

        return



    def test_replication_2(self):
        '''
            test 'no' replication, when 'enableReplication' entry is not set

            Description:
            - put privacyIDEA in replication aware mode
            - add a new entry in the Config Data vi SQL + update the timestamp
            - query the Config (system/getConfig, which should show the entry

            - del a entry in the Config Data vi SQL + update the timestamp
            - query the Config (system/getConfig, which should show the entry no more

        '''
        ''' 0. '''
        self.addData('replication', 'test1', 'test data')

        ''' 1. '''
        resp = self.app.get(url(controller='system', action='getConfig'))
        res = ('"replication": "test1"' in resp)
        assert (res == False)

        ''' 2. '''
        parameters = {'enableReplication' : 'true' }
        resp = self.app.get(url(controller='system', action='setConfig'), params=parameters)
        assert('"setConfig enableReplication:true": true' in resp)


        ''' 3. '''
        self.delData('replication')

        ''' 3. '''
        resp = self.app.get(url(controller='system', action='getConfig'))
        res = ('"replication": "test1"' in resp)
        assert (res == False)


        self.addData('replication', 'test1', 'test data')

        ''' 4. '''
        resp = self.app.get(url(controller='system', action='getConfig'))
        res = ('"replication": "test1"' in resp)
        assert (res == True)


        ''' 3. '''
        self.delData('replication')

        ''' 3. '''
        resp = self.app.get(url(controller='system', action='getConfig'))
        res = ('"replication": "test1"' in resp)
        assert (res == False)


        ''' 5 - cleanup'''
        parameters = {'key':'enableReplication' }
        resp = self.app.get(url(controller='system', action='delConfig'), params=parameters)
        assert('"delConfig enableReplication": true' in resp)

        return


    def test_updateResolver(self):
        '''
            test replication with resolver update

        '''
        #FIXME missing SQLresolver
        return
        umap = { "userid" : "id",
                "username": "user",
                "phone" : "telephoneNumber",
                "mobile" : "mobile",
                "email" : "mail",
                "surname" : "sn",
                "givenname" : "givenName",
                "password" : "password",
                "salt" : "salt" }

        sqlResolver = {
            "sqlresolver.conParams.mySQL": None,
            "sqlresolver.Where.mySQL": None,
            "sqlresolver.Limit.mySQL": "20",
            "sqlresolver.User.mySQL": "user",
            "sqlresolver.Database.mySQL": "yourUserDB",
            "sqlresolver.Password.mySQL": "157455c27f605ad309d6059e1d936a4" +
                                        "e:7a812ba9e613fb931386f5f4fb025890",
            "sqlresolver.Table.mySQL": "usertable",
            "sqlresolver.Server.mySQL": "127.0.0.1",
            "sqlresolver.Driver.mySQL": "mysql",
            "sqlresolver.Encoding.mySQL": None,
            "sqlresolver.Port.mySQL": "3306",
            "sqlresolver.Map.mySQL": json.dumps(umap)

            }
        for k in sqlResolver:
            self.delData(k)

        ''' 0. '''
        parameters = {'enableReplication' : 'true' }
        resp = self.app.get(url(controller='system', action='setConfig'),
                            params=parameters)
        assert('"setConfig enableReplication:true": true' in resp)

        for k in sqlResolver:
            self.addData(k, sqlResolver.get(k), '')

        param = {'resolver':'mySQL'}
        resp = self.app.get(url(controller='system', action='getResolver'),
                            params=param)
        assert('"Database": "yourUserDB"' in resp)

        for k in sqlResolver:
            self.delData(k)

        param = {'resolver':'mySQL'}
        resp = self.app.get(url(controller='system', action='getResolver'),
                            params=param)
        assert('"data": {}' in resp)


        ''' 5 - cleanup'''
        parameters = {'key':'enableReplication' }
        resp = self.app.get(url(controller='system', action='delConfig'),
                            params=parameters)
        assert('"delConfig enableReplication": true' in resp)



        return

    def test_updateRealm(self):
        '''
            test replication with realm and resolver update
        '''
        realmDef = {
            "useridresolver.group.realm":
                    "privacyidea.lib.resolvers.PasswdIdResolver.IdResolver.resolverTest",
            "passwdresolver.fileName.resolverTest": "/etc/passwd",
            "DefaultRealm": "realm",
            }

        for k in realmDef:
            self.delData(k)

        parameters = {'enableReplication' : 'true' }
        resp = self.app.get(url(controller='system', action='setConfig'),
                            params=parameters)
        assert('"setConfig enableReplication:true": true' in resp)


        resp = self.app.get(url(controller='system', action='getRealms'))
        res = '"realmname": "realm"' in resp
        assert res == False


        for k in realmDef:
            self.addData(k, realmDef.get(k), '')

        resp = self.app.get(url(controller='system', action='getRealms'))
        res = '"realmname": "realm"' in resp
        assert res == True


        ''' 5 - cleanup'''
        for k in realmDef:
            self.delData(k)

        resp = self.app.get(url(controller='system', action='getRealms'))
        res = '"realmname": "realm"' in resp
        assert res == False


        parameters = {'key':'enableReplication' }
        resp = self.app.get(url(controller='system', action='delConfig'),
                            params=parameters)
        assert('"delConfig enableReplication": true' in resp)



        return

    def test_auth_updateRealm(self):
        '''
          test resolver and realm update with authentication

          0. delete all related data
          1. enable replication
          2. write sql data
          3. lookup for the realm definition
          4. enroll token and auth for user root
          5. cleanup: remove realm definition + replication flag

        '''
        realmDef = {
            "useridresolver.group.realm":
                    "privacyidea.lib.resolvers.PasswdIdResolver.IdResolver.resolverTest",
            "passwdresolver.fileName.resolverTest": "/etc/passwd",
            "DefaultRealm": "realm",
            }

        ''' 0. delete all related data'''
        for k in realmDef:
            self.delData(k)

        ''' 1. switch on replication '''
        parameters = {'enableReplication' : 'true' }
        resp = self.app.get(url(controller='system', action='setConfig'),
                            params=parameters)
        assert('"setConfig enableReplication:true": true' in resp)


        ''' 1.b check that realm is not defined '''
        resp = self.app.get(url(controller='system', action='getRealms'))
        res = '"realmname": "realm"' in resp
        assert res == False


        ''' 2  write sql data '''
        for k in realmDef:
            self.addData(k, realmDef.get(k), '')

        ''' 3. lookup for the realm definition'''
        resp = self.app.get(url(controller='system', action='getRealms'))
        res = '"realmname": "realm"' in resp
        assert res == True

        ''' 4. enroll token and auth for user root '''
        self.addToken('root')
        res = self.authToken('root')
        assert ('"value": true' in res)


        ''' 5 - cleanup'''
        for k in realmDef:
            self.delData(k)

        ''' 5b. lookup for the realm definition'''
        resp = self.app.get(url(controller='system', action='getRealms'))
        res = '"realmname": "realm"' in resp
        assert res == False

        parameters = {'key':'enableReplication' }
        resp = self.app.get(url(controller='system', action='delConfig'),
                            params=parameters)
        assert('"delConfig enableReplication": true' in resp)


        return


    def test_0000_policy(self):
        '''
            test the replication of policies
        '''

        policyDef = {
            "Policy.enrollPolicy.action": "maxtoken=3,",
            "Policy.enrollPolicy.scope": "enrollment",
            "Policy.enrollPolicy.client": None,
            "Policy.enrollPolicy.time": None,
            "Policy.enrollPolicy.realm": "*",
            "Policy.enrollPolicy.user": "*",
            }

        ''' 0 - cleanup'''
        parameters = {'key':'enableReplication' }
        resp = self.app.get(url(controller='system', action='delConfig'),
                            params=parameters)
        assert('"delConfig enableReplication": true' in resp)

        for k in policyDef:
            self.delData(k)


        ''' 1. switch on replication '''
        parameters = {'enableReplication' : 'true' }
        resp = self.app.get(url(controller='system', action='setConfig'),
                            params=parameters)
        assert('"setConfig enableReplication:true": true' in resp)

        ''' 2  write sql data '''
        for k in policyDef:
            self.addData(k, policyDef.get(k), '')

        ''' 3. getPolicy '''
        parameters = {'name' : 'enrollPolicy' }
        resp = self.app.get(url(controller='system', action='getPolicy'),
                            params=parameters)
        assert('"action": "maxtoken=3' in resp)

        ''' 5 - cleanup'''
        for k in policyDef:
            self.delData(k)

        ''' 5b. lookup for the policy definition'''
        parameters = {'name' : 'enrollPolicy' }
        resp = self.app.get(url(controller='system', action='getPolicy'),
                            params=parameters)
        res = ('"action": "maxtoken=3' in resp)
        assert res == False

        ''' 5c. reset replication '''
        parameters = {'key':'enableReplication' }
        resp = self.app.get(url(controller='system', action='delConfig'),
                            params=parameters)
        assert('"delConfig enableReplication": true' in resp)


        return

##eof##########################################################################

