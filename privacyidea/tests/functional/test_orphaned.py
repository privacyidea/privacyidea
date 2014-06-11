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
from privacyidea.tests import TestController, url
import copy

import json

log = logging.getLogger(__name__)

from sqlalchemy.engine import create_engine
import sqlalchemy
q = '"'

class SQLUser(object):

    def __init__(self, connect='sqlite:///:memory:'):
        self.tableName = 'User2'
        self.usercol = '"user"'
        self.userTable = '"%s"' % (self.tableName)

        self.connection = None
        try:
            self.engine = create_engine(connect)
            connection = self.engine.connect()
            self.sqlurl = self.engine.url
            if self.sqlurl.drivername == 'mysql':
                self.userTable = "%s.%s" % (self.sqlurl.database, self.tableName)
                self.usercol = 'user'



        except Exception as e:
            print "%r" % e
        self.connection = connection

        umap = { "userid"   : "id",
                "username"  : "user",
                "phone"     : "telephoneNumber",
                "mobile"    : "mobile",
                "email"     : "mail",
                "surname"   : "sn",
                "givenname" : "givenName" ,
                "password"  : "password",
                "salt"      : "salt" }

        #connect = '''postgres://otpd:privacyidead@localhost/otpdb ''


        self.resolverDef = {
            'Table'     : self.tableName,
            'Connect'   : connect,
            'Map'       : json.dumps(umap),
         }

        return


    def getResolverDefinition(self):
        return self.resolverDef

    def creatTable(self):

        createStr = """
            CREATE TABLE %s
            (
              %s text,
              telephoneNumber text,
              mobile text,
              sn text,
              givenName text,
              password text,
              salt text,
              id text,
              mail text
            )
            """ % (self.userTable, self.usercol)
        t = sqlalchemy.sql.expression.text(createStr)
        self.connection.execute(t)
        return

    def dropTable(self):
        dropStr = "DROP TABLE %s;" % (self.userTable)
        t = sqlalchemy.sql.expression.text(dropStr)
        self.connection.execute(t)


    def addUser(self, user, telephoneNumber, mobile, sn, givenName, password, salt, id, mail):
        intoStr = """
            INSERT INTO %s( %s, telephoneNumber, mobile,
            sn, givenName, password, salt, id, mail)
            VALUES (:user, :telephoneNumber, :mobile, :sn, :givenName, :password, :salt, :id, :mail);
            """ % (self.userTable, self.usercol)
        t = sqlalchemy.sql.expression.text(intoStr)

        self.connection.execute(t, user=user, telephoneNumber=telephoneNumber, mobile=mobile, sn=sn,
                                givenName=givenName, password=password, salt=salt, id=id, mail=mail)

        #execute(sqlalchemy.sql.expression.text("""SELECT COUNT(*) FROM Config WHERE Config.Key = :key"""), key=REPLICATION_CONFIG_KEY)

    def query(self):
        selectStr = "select * from %s" % (self.userTable)
        result = self.connection.execute(selectStr)
        res = []
        for row in result:
            res.append(row)

        return res

    def delUsers(self, id=None, username=None):

        if username is not None:
            delStr = 'DELETE FROM %s  WHERE user=:user;' % (self.userTable)
            t = sqlalchemy.sql.expression.text(delStr)
            self.connection.execute(t, user=username)

        elif type(id) in (str, u''):
            delStr = 'DELETE FROM %s  WHERE id=:id;' % (self.userTable)
            t = sqlalchemy.sql.expression.text(delStr)
            self.connection.execute(t, id=id)

        elif id is None:
            delStr = 'DELETE FROM %s ;' % (self.userTable)
            t = sqlalchemy.sql.expression.text(delStr)
            self.connection.execute(t)





    def close(self):
        self.connection.close()


    def __del__(self):
        self.connection.close()






class TestOrphandTokens(TestController):

    def setUp(self):
        TestController.setUp(self)
        self.setUpSQL()

    def setUpSQL(self):

        self.sqlconnect = self.appconf.get('sqlalchemy.url')
        sqlUser = SQLUser(connect=self.sqlconnect)
        self.sqlResolverDef = sqlUser.getResolverDefinition()

        return

    def addUsers(self, usercount=10):

        userAdd = SQLUser(connect=self.sqlconnect)

        try:
            userAdd.creatTable()
        except Exception as e:
            userAdd.dropTable()
            userAdd.creatTable()
            log.error(" create user table error: %r " % e)
            userAdd.delUsers()


        for i in range(1, usercount):
            user = 'hey%d' % i
            telephoneNumber = '012345-678-%d' % i
            mobile = '00123-456-%d' % i
            sn = 'yak%d' % i
            givenName = 'kayak%d' % i
            password = 'safr2r32'
            salt = 't123'
            id = '__%d' % i
            mail = sn + '.' + givenName + "@example.com"

            userAdd.addUser(user, telephoneNumber, mobile, sn, givenName, password, salt, id, mail)

        u_dict = [{
            'user' : 'kn_t',
            'telephoneNumber' : '012345-678-99999',
            'mobile' : '00123-456-99999',
            'sn' : 'kn_t',
            'givenName' : 'knöt',
            'password' : 'safr2r32',
            'salt' : 't123',
            'id' : '__9999',
            },
            {'user' : 'knöt',
            'telephoneNumber' : '012345-678-99998',
            'mobile' : '00123-456-99998',
            'sn' : 'knöt',
            'givenName' : 'knöt',
            'password' : 'safr2r32',
            'salt' : 't123',
            'id' : '__9998',
            },
            {'user' : 'kn%t',
            'telephoneNumber' : '012345-678-99997',
            'mobile' : '00123-456-99997',
            'sn' : 'kn%t',
            'givenName' : 'kn%t',
            'password' : 'safr2r32',
            'salt' : 't123',
            'id' : '__9997',
            },
            ]
        for user in u_dict:
            user['mail'] = user['sn'] + '.' + user['givenName'] + "@example.com"
            userAdd.addUser(**user)

        resolverDefinition = userAdd.getResolverDefinition()
        userAdd.close()

        return resolverDefinition


    def delUsers(self, id=None, username=None):

        userAdd = SQLUser(connect=self.sqlconnect)
        userAdd.delUsers(id=id, username=username)
        userAdd.close()

    def addSqlResolver(self, name):

        parameters = copy.deepcopy(self.sqlResolverDef)

        parameters['name'] = name
        parameters['type'] = 'sqlresolver'
        parameters['Limit'] = '20'


        resp = self.app.get(url(controller='system', action='setResolver'), params=parameters)
        assert('"value": true' in resp)

        resp = self.app.get(url(controller='system', action='getResolvers'))
        assert('"resolvername": "%s"' % (name) in resp)

        param2 = {'resolver': name
                  }
        resp = self.app.get(url(controller='system', action='getResolver'), params=param2)
        assert('"Table": "User2"' in resp)

        return

    def delSqlResolver(self, name):
        parameters = {
            'resolver'     : name,
        }
        resp = self.app.get(url(controller='system', action='delResolver'), params=parameters)
        assert('"value": true' in resp)

        return resp


    def addSqlRealm(self, realmName, resolverName, defaultRealm=False):
        parameters = {
            'realm'     : realmName,
            'resolvers' :'privacyidea.lib.resolvers.SQLIdResolver.IdResolver.%s' % (resolverName)
        }
        resp = self.app.get(url(controller='system', action='setRealm'), params=parameters)
        assert('"value": true' in resp)

        resp = self.app.get(url(controller='system', action='getRealms'))
        assert('"default": "true"' in resp)
        return

    def delSqlRealm(self, realmName):
        parameters = {
            'realm'     : realmName,
        }
        resp = self.app.get(url(controller='system', action='delRealm'), params=parameters)
        assert('"result": true' in resp)

        return resp


    def getUserList(self, resolver):

        param = {'username' : '*', 'resConf': resolver}
        response = self.app.get(url(controller='admin', action='userlist'), params=param)
        if ("error") in response:
            body = json.loads(response.body)
            result = body.get('result')
            error = result.get('error')
            raise Exception(error.get('message'))
        else:
            assert ('"status": true,' in response)

        body = json.loads(response.body)
        result = body.get('result')
        userList = result.get('value')

        return userList

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


    def __deleteAllRealms__(self):
        ## get al realms
        response = self.app.get(url(controller='system', action='getRealms'))
        jResponse = json.loads(response.body)
        result = jResponse.get("result")
        values = result.get("value", {})
        for realmId in values:
            print realmId
            realmDesc = values.get(realmId)
            realmName = realmDesc.get("realmname")
            parameters = {"realm":realmName}
            resp = self.app.get(url(controller='system', action='delRealm'), params=parameters)
            assert('"result": true' in resp)

        return

    def __deleteAllResolvers__(self):
        ##http://127.0.0.1:5001/system/getResolvers
        response = self.app.get(url(controller='system', action='getResolvers'))
        jResponse = json.loads(response.body)
        result = jResponse.get("result")
        values = result.get("value", {})
        for realmId in values:
            print realmId
            resolvDesc = values.get(realmId)
            resolvName = resolvDesc.get("resolvername")
            parameters = {"resolver" : resolvName}
            resp = self.app.get(url(controller='system', action='delResolver'), params=parameters)
            assert('"status": true' in resp)

        return

    def test_orphandTokens_byUser(self):
        '''
            test an orphand token - where the user is removed in the sql database

            Description:
            - create a SQL User Database with a certain number of users
            - create a SQLResolver, who refers to this user database
            - create a realm for this sql resolver
            - create a token for one of the SQL users
            - admin/show should show the token user
            - run authentication for this user
            - remove users from the SQL database
            - admin/show should show the /:no user info:/
            - authentication should fail

        '''
        #FIXME EE SQL
        return
        self.setUpSQL()

        self.__deleteAllRealms__()
        self.__deleteAllResolvers__()


        resolverName = 'MySQLResolver'
        realmName = 'sqlrealm'.lower()

        self.addUsers()
        self.addSqlResolver(resolverName)
        self.addSqlRealm(realmName, resolverName, defaultRealm=True)

        users = self.getUserList(resolverName)
        user = users[0].get('username')

        self.addToken(user)
        ret = self.authToken(user)
        assert '"value": true' in ret

        self.delUsers()
        users = self.getUserList(resolverName)
        assert len(users) == 0

        res = self.showTokens()
        assert "/:no user info:/" in res

        ret = self.authToken(user)
        assert '"value": false' in ret

        self.delSqlRealm(realmName)
        self.delSqlResolver(resolverName)

        return

    def test_orphandTokens_byResolver(self):
        '''
            test an orphaned token by resolver - where the user is not retrievable by the resolver any more

            Description:
            - create a SQL User Database with a certain number of users
            - create a SQLResolver, who refers to this user database
            - create a realm for this sql resolver
            - create a token for one of the SQL users
            - admin/show should show the token user
            - run authentication for this user

            - remove the SQLResolver

            - admin/show should show the /:no user info:/
            - authentication should fail

        '''
        #FIXME EE SQL
        return
        self.setUpSQL()

        self.__deleteAllRealms__()
        self.__deleteAllResolvers__()


        resolverName = 'MySQLResolver'
        realmName = 'sqlrealm'.lower()

        self.addUsers()
        self.addSqlResolver(resolverName)
        self.addSqlRealm(realmName, resolverName, defaultRealm=True)


        users = self.getUserList(resolverName)
        assert len(users) > 0

        user = users[0].get('username')

        self.addToken(user)
        ret = self.authToken(user)
        assert '"value": true' in ret


        self.delSqlRealm(realmName)
        self.delSqlResolver(resolverName)

        message = ''
        try:
            empty_user_list = self.getUserList(resolverName)
        except Exception as e:
            message = "%r" % e
            log.error(message)
        assert len(empty_user_list) == 0
        #assert "invalid resolver class specification" in message

        ret = self.authToken(user)
        assert '"value": false' in ret

        res = self.showTokens()
        assert "/:no user info:/" in res



        return

    def test_again(self):
        #FIXME EE SQL
        return
        for i in range(1, 10):
            self.test_orphandTokens_byResolver()
            self.test_orphandTokens_byUser()

        return

    def test_0000_umlaut_search(self):
        """
        Escaping SQL Resolver: support for wildcards (s. #12135)
        """
        #FIXME EE SQL
        return
        self.setUpSQL()

        self.__deleteAllRealms__()
        self.__deleteAllResolvers__()

        resolverName = 'MySQLResolver'
        realmName = 'sqlrealm'.lower()

        self.addUsers()
        self.addSqlResolver(resolverName)
        self.addSqlRealm(realmName, resolverName, defaultRealm=True)

        parameters = {'username':'knöt'}
        response = self.app.get(url(controller='admin', action='userlist'),
                                                            params=parameters)
        self.assertTrue('"userid": "__9998"' in response, response)
        self.assertTrue('"userid": "__9997"' not in response, response)
        self.assertTrue('"userid": "__9999"' not in response, response)

        ## ignore SQL wildcards
        parameters = {'username':'kn%t'}
        response = self.app.get(url(controller='admin', action='userlist'),
                                                            params=parameters)

        self.assertTrue('"userid": "__9998"' not in response, response)
        self.assertTrue('"userid": "__9997"' in response, response)
        self.assertTrue('"userid": "__9999"' not in response, response)

        ## ignore SQL wildcards
        parameters = {'username':'kn_t'}
        response = self.app.get(url(controller='admin', action='userlist'),
                                                            params=parameters)

        self.assertTrue('"userid": "__9998"' not in response, response)
        self.assertTrue('"userid": "__9997"' not in response, response)
        self.assertTrue('"userid": "__9999"' in response, response)

        ## support privacyIDEA wildcards
        parameters = {'username':'kn*t'}
        response = self.app.get(url(controller='admin', action='userlist'),
                                                            params=parameters)

        self.assertTrue('"userid": "__9998"' in response, response)
        self.assertTrue('"userid": "__9997"' in response, response)
        self.assertTrue('"userid": "__9999"' in response, response)

        ## support privacyIDEA wildcards
        parameters = {'username':'kn.t'}
        response = self.app.get(url(controller='admin', action='userlist'),
                                                            params=parameters)

        self.assertTrue('"userid": "__9998"' in response, response)
        self.assertTrue('"userid": "__9997"' in response, response)
        self.assertTrue('"userid": "__9999"' in response, response)

        ## support privacyIDEA wildcards for other fields
        parameters = {'userid':'*9*'}
        response = self.app.get(url(controller='admin', action='userlist'),
                                                            params=parameters)

        self.assertTrue('"userid": "__9"' in response, response)
        self.assertTrue('"userid": "__9998"' in response, response)
        self.assertTrue('"userid": "__9997"' in response, response)
        self.assertTrue('"userid": "__9999"' in response, response)

        return

###eof#########################################################################
