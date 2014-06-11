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
import sys
import ConfigParser
import logging
from privacyidea.tests import TestController, url
import copy

import json

import traceback
import hashlib
import base64

from socket import gethostname


log = logging.getLogger(__name__)

import ldap



class LDAP(object):

    def __init__(self, ldapurl=None):

        self.lobj = None
        self.binddn = None
        self.bindpw = None
        self.ldapserverip = None
        self.ldapuri = None
        self.base = None

        if ldapurl is not None:
            self.ldapurl = ldapurl

            (part, _split, hostname) = self.ldapurl.partition('@')
            if part.startswith('ldap://'):
                offstring = 'ldap://'
                self.ldapuri = 'ldap://'
            if part.startswith('ldaps://'):
                offstring = 'ldaps://'
                self.ldapuri = 'ldaps://'

            userpass = part[len(offstring):]
            posCol = userpass.index(':')

            self.binddn = userpass[:posCol]
            self.bindpw = userpass[posCol + 1:]
            self.ldapserverip = hostname
            self.ldapuri = self.ldapuri + hostname

            baseIndex = self.binddn.index('dc')
            self.base = self.binddn[baseIndex:]

        return


    def loadConfig(self, config, conf="", bindpw=None, binddn=None):
        '''
            loadConfig - load the config for the resolver
        '''

        self.conf = conf
        if conf is not None:
            conf = '.' + conf

        if binddn is not None:
            self.binddn = binddn
        else:
            self.binddn = config.get("ldapresolver.BINDDN" + conf)

        if bindpw is not None:
            self.bindpw = bindpw
        else:
            self.bindpw = config.get("ldapresolver.BINDPW" + conf)


        self.filter = config.get("ldapresolver.LDAPFILTER" + conf, '')
        self.searchfilter = config.get("ldapresolver.LDAPSEARCHFILTER" + conf)
        self.ldapuri = config.get("ldapresolver.LDAPURI" + conf)
        self.base = config.get("ldapresolver.LDAPBASE" + conf)

        self.loginnameattribute = config.get("ldapresolver.LOGINNAMEATTRIBUTE" + conf)
        #userinfo           = config.get("ldapresolver.USERINFO"+conf)
        #timeout            = config.get("ldapresolver.TIMEOUT"+conf)

        self.uidType = config.get("ldapresolver.UIDTYPE" + conf)
        if self.uidType is None or self.uidType.strip() == "":
            self.uidType = "DN"

        sizelimit = config.get("ldapresolver.SIZELIMIT" + conf)
        try:
            self.sizelimit = int(sizelimit)
        except ValueError:
            self.sizelimit = 50
        except TypeError:
            self.sizelimit = 50


        return self


    def bind(self, binddn=None, bindpw=None):
        """ bind()  - this function starts an ldap conncetion
        """
        uri = ''
        #i   = 0


        if binddn is None:
            binddn = self.binddn

        if bindpw is None:
            bindpw = self.bindpw


        urilist = self.ldapuri.split(',')

        if self.lobj is None:
            for uri in urilist:
                try:
                    log.debug("[bind] LDAP: Try to bind to %s", uri)
                    l_obj = ldap.initialize(uri, trace_level=0)
                    l_obj.simple_bind_s(binddn, bindpw)
                    self.lobj = l_obj
                    break
                except ldap.LDAPError as e:
                    log.error("[bind] LDAP error: %r" % e)
                    log.error("[bind] LDAPURI   : %r" % uri)
                    log.error("[bind] %s" % traceback.format_exc())
                    raise Exception(e)

        return self.lobj


    def unbind(self):
        """ unbind() - this function frees the ldap connection
        """
        try:
            if self.lobj is not None:
                self.lobj.unbind_s()

        except ldap.LDAPError as e:
            log.error("[unbind] LDAP error: %r" % e)

        self.lobj = None
        return ""

    def addModlist(self, obj):
        '''
            transform dict to tuple
            -ldap requires the data as tuples
        '''
        record = []
        for k in obj:
            data = obj.get(k)
            record.append((k, data))

        return record

    def addUser(self, dn=None,
                objectclass=None, cn=None, uid=None,
                mail=None, givenName=None, sn=None,
                postalAddress=None, postalCode=None, l=None,
                homePhone=None, mobile=None,
                userPassword=None):
        '''
            # The dn of our new entry/object
            dn="cn=Sigmund Freud,ou=Lab,ou=people,dc=crypton,dc=info"

            """
            dn: cn=Werner Braun,ou=Lab,dc=crypton,dc=info
            # which schema to use
            objectClass: top
            objectClass: person
            objectClass: organizationalPerson
            objectClass: inetOrgPerson
            """

            """
    '''


        attrs = {}
        if dn is None:
            raise Exception('missing requred dn')

        if objectclass is None:
            attrs['objectclass'] = ['top', 'person', 'organizationalPerson', 'inetOrgPerson', 'uidObject']
        else:
            attrs['objectclass'] = objectclass.split(',')

        if cn is not None:
            attrs['cn'] = cn
        if givenName is not None:
            attrs['givenName'] = givenName
        if uid is not None:
            attrs['uid'] = uid
        elif cn is not None:
            attrs['uid'] = cn

        if sn is not None:
            attrs['sn'] = sn
        if postalAddress is not None:
            attrs['postalAddress'] = postalAddress
        if mail is not None:
            attrs['mail'] = mail
        if postalCode is not None:
            attrs['postalCode'] = postalCode
        if l is not None:
            attrs['l'] = l
        if homePhone is not None:
            attrs['homePhone'] = homePhone
        if mobile is not None:
            attrs['mobile'] = mobile

        if userPassword is not None:
            attrs['userPassword'] = userPassword


        self.lobj = self.bind()
        if self.lobj is None:
            raise Exception('LDAP Bind failed!')

        ldif = self.addModlist(attrs)
        self.lobj.add_s(dn, ldif)


        log.debug('userAdded done!')

        return

    def delete(self, dn):

        self.lobj = self.bind()
        if self.lobj is None:
            raise Exception('LDAP Bind failed!')

        self.lobj.delete_s(dn)

        log.debug('delete done!')

        return


    def addOu(self, dn, ou):
        attrs = {}
        attrs['objectclass'] = ['top', 'organizationalUnit']
        attrs['ou'] = ou

        self.lobj = self.bind()
        if self.lobj is None:
            raise Exception('LDAP Bind failed!')

        ldif = self.addModlist(attrs)
        self.lobj.add_s(dn, ldif)

        return

class TestLDAP(TestController):

    users = [
        {'dn'       : 'cn=Werner Braun,',
        'cn'        : 'Werner Braun',
        'givenName' : 'Werner',
        'uid'       : 'wärner',
        'sn'        : 'Braun',
        'mail'      : 'w.Braun@lsexperts.de',
        'postalAddress': 'My Way 5',
        'postalCode': '64297',
        'l'         : 'Darmstadt',
        'homePhone' : '06151 /123 456 789',
        'mobile'    : '0179 / 123 123 123', },

        {'dn'       : 'cn=Jörg Preuße,',
        'cn'        : 'Jörg Preuße',
        'givenName' : 'Preußer',
        'uid'       : 'jörgi',
        'sn'        : 'Jörg Preuße',
        'mail'      : 'Joerg.Preusse@lsexperts.de',
        'postalAddress': 'Lindenstraße 13',
        'postalCode': '24297',
        'l'         : 'Am Hintersee',
        'homePhone' : '06151 /123 456 789',
        'mobile'    : '0179 / 123 123 123', },

    ]





    def setupLDAPResolver(self, name='ldapUsers', ip='serverIp', base='ou=users,dc=crypton,dc=info', uidType='entryUUID', bindpw='test123!', binddn='cn=admin,dc=crypton,dc=info'):
        '''
            'LDAPBASE'              : 'ou=users,dc=crypton,dc=info',
            'LDAPBASE'              : 'ou=users,dc=crypton,dc=info',
        '''


        ldapDef = {
            'name'                  : name,
            'type'                  : 'ldapresolver',
            'LDAPURI'               : 'ldap://' + ip,
            'LDAPBASE'              : base,
            'BINDDN'                : binddn,
            'BINDPW'                : bindpw,
            'TIMEOUT'               : '5',
            'SIZELIMIT'             : '500',
            'LOGINNAMEATTRIBUTE'    : 'uid',
            'LDAPSEARCHFILTER'      : '(uid=*)(objectClass=inetOrgPerson)',
            'LDAPFILTER'            : '(&(uid=%s)(objectClass=inetOrgPerson))',
            'USERINFO'              : '{ "username": "uid", "phone" : "telephoneNumber", "mobile" : "mobile", "email" : "mail", "surname" : "sn", "givenname" : "givenName" }',
            'UIDTYPE'               : uidType,
            'NOREFERRALS'           : 'False'
        }
        response = self.app.get(url(controller='system', action='setResolver'), params=ldapDef)
        assert '"status": true,' in response

        ldapConf = self.getConfig(name, bindpw=bindpw, binddn=binddn)
        return ldapConf

    def getUserList4Resolver(self, resolver, username=None):

        param = {'username' : '*', 'resConf': resolver}
        if username is not None:
            param['username'] = username

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

    def getUserList4Realm(self, realm, username=None):

        param = {'username' : '*', 'realm': realm}
        if username is not None:
            param['username'] = username

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

    def check_ip(self, ip):
        ret = False

        return ret

    def getConfig(self, conf, bindpw=None, binddn=None):

        ret = {}

        response = self.app.get(url(controller='system', action='getConfig'))

        resp = json.loads(response.body)
        config = resp.get('result').get('value')

        for k in config:
            if k.startswith('ldapresolver.') and k.endswith(u'' + conf):
                    ret[k] = config.get(k)

        ''' finally fix the pw and dn in the config '''
        if bindpw is not None and len(ret) > 0:
            ret['ldapresolver.BINDPW.' + conf] = bindpw

        if binddn is not None and len(ret) > 0:
            ret['ldapresolver.BINDDN.' + conf] = binddn

        return ret

    def addToken(self, user, pin=None, serial=None, typ=None):

        if serial is None:
            serial = 's' + user
        if pin is None:
            pin = user
        if typ is None:
            typ = 'spass'
        param = { 'user': user, 'pin':pin, 'serial': serial, 'type':typ }
        response = self.app.get(url(controller='admin', action='init'), params=param)
        assert '"status": true,' in response

        return serial

    def authToken(self, user, passw=None):

        if passw is None:
            passw = user
        param = { 'user': user, 'pass':passw}
        response = self.app.get(url(controller='validate', action='check'), params=param)
        return response


    def showTokens(self, serial=None):

        param = {}
        if serial is not None:
            param['serial'] = serial
        response = self.app.get(url(controller='admin', action='show'), params=param)
        return response

    def delTokens(self, serial=None):

        param = {}
        if serial is not None:
            param['serial'] = serial
        response = self.app.get(url(controller='admin', action='remove'), params=param)
        return response


    def getLDAPUrl(self):

        self.ldapurl = None
        self.binddn = None
        self.bindpw = None
        self.ldapserverip = None

        #self.appconf = self.app.app.app.apps[1].application.app.application.app.app.app.config
        hostname = gethostname()

        if self.appconf.has_key('privacyidea.ldapTestServerIp.' + hostname):
            self.ldapurl = self.appconf.get('privacyidea.ldapTestServerIp.' + hostname)
        elif self.appconf.has_key('<include>') == True:
            try:
                filename = self.appconf.get('<include>')
                cfgParse = ConfigParser.ConfigParser()
                cfgParse.readfp(open(filename))
                incDict = cfgParse.defaults()
                self.ldapurl = incDict.get('privacyidea.ldapTestServerIp.'.lower() + hostname, None)
            except Exception as e:
                log.error('Error parsing include file: %r' % e)
        else:
                log.warning('no ldap Test server specified in the ini file!!')


        if self.ldapurl is not None:

            (part, _split, hostname) = self.ldapurl.partition('@')
            if part.startswith('ldap://'):  offstring = 'ldap://'
            if part.startswith('ldaps://'): offstring = 'ldaps://'

            userpass = part[len(offstring):]
            posCol = userpass.index(':')

            self.binddn = userpass[:posCol]
            self.bindpw = userpass[posCol + 1:]
            self.ldapserverip = hostname

        return (self.ldapurl, self.ldapserverip, self.binddn, self.bindpw)

    def setOtpPinPolicy(self, name='ldapOtpPin', realm='ldap_realm'):
        parameters = {
                         'name'     : name,
                         'user'     : '*',
                         'action'   : 'otppin=1, ',
                         'scope'    : 'authentication',
                         'realm'    : realm,
                         'time'     : '',
                         'client'   : '',
                         }
        response = self.app.get(url(controller='system', action='setPolicy'), params=parameters)
        log.error(response)

    def delOtpPinPolicy(self, name='ldapOtpPin'):
        parameters = { 'name' : name,
                      'selftest_admin' : 'superadmin' }
        response = self.app.get(url(controller='system', action='delPolicy'), params=parameters)
        log.debug(response)

    def test_one(self):
        '''
            LDAP test - test against a test LDAP server

        '''
        # get test server on a per test server host base
        (ldapurl, serverIp, binddn, bindpw) = self.getLDAPUrl()

        # Skip test if no config found
        if ldapurl is None or serverIp is None:
            skip_reason = "No ldap server test url like: ldap://cn=admin,dc=example,dc=com:test123!@192.168.0.2: defined in the *.ini file"
            if sys.version_info[0:2] >= (2, 7):
                # skipTest() has the advantage that it is shown in the test summary
                # but it is only available in Python 2.7
                self.skipTest(skip_reason)
            else:
                log.error("Skipping test 'test_one': " + skip_reason)
                return

        parameters = {'enableReplication' : 'true' }
        resp = self.app.get(url(controller='system', action='setConfig'), params=parameters)
        assert('"setConfig enableReplication:true": true' in resp)

        resolvers = []
        ldapObjects = []

        ldapServ = None

        ldapServerConnected = True

        ldapResolvers = [
            {'name' : 'ldapUsers', 'base': 'ou=users,dc=crypton,dc=info', 'uidType':'entryUUID' },
            {'name' : 'ldapPeople', 'base': 'ou=people,dc=crypton,dc=info', 'uidType':'entryUUID' },
        ]

        ''' add ldap server info to resolverdefinition '''
        for resolver in ldapResolvers:
            resolver['ip'] = serverIp
            resolver['bindpw'] = bindpw
            resolver['binddn'] = binddn

        thePassword = 'jörgi'
        try:
            ldapServ = LDAP(ldapurl)


            for entry in ldapResolvers:
                self.setupLDAPResolver(**entry)
                resolver = entry.get('name')
                resolvers.append(resolver)

                try:
                    base = entry.get('base')
                    path = base.split(',')
                    ou = path[0]
                    ou = ou[len('ou='):]
                    ldapServ.addOu(base, ou)
                    ldapObjects.append(base)

                except Exception as e:
                    if 'Already exists' not in unicode(e):
                        raise Exception(e)

                for user in self.users:
                    nuser = copy.deepcopy(user)
                    nuser['dn'] = user.get('dn') + entry.get('base')
                    nuser['uid'] = "%s-%s" % (user.get('uid'), resolver)
                    passw = hashlib.sha1(thePassword).digest()
                    passw = base64.encodestring(passw)
                    nuser['userPassword'] = '{SHA}%s' % (unicode(passw))

                    try:
                        ldapServ.addUser(**nuser)
                        ldapObjects.append(nuser.get('dn'))
                    except Exception as e:
                        if 'Already exists' not in unicode(e):
                            raise Exception(e)


        except Exception as e:
            log.error("%r" % e)
            log.error("%s" % traceback.format_exc())

            msg = unicode(e)
            if "Can't contact LDAP server" in msg:
                ldapServerConnected = False

        if ldapServerConnected == False:
            self.fail("No LDAP connection")


        realmresolvers = []
        tokenSerials = []
        try:
            for res in resolvers:
                realmresolvers.append('privacyidea.lib.resolvers.LDAPIdResolver.IdResolver.%s' % res)


            ''' next create a realm '''
            realmName = 'ldap_realm'
            parameters = {
                'realm'     : realmName,
                'resolvers' : u'%s' % (unicode(','.join(realmresolvers)))
            }
            resp = self.app.get(url(controller='system', action='setRealm'), params=parameters)
            assert('"value": true' in resp)

            resp = self.app.get(url(controller='system', action='getRealms'))
            assert('"default": "true"' in resp)

            ''' lookup for the user1 in realm '''
            userlist = self.getUserList4Realm(realmName, username='jörgi-*')
            assert len(userlist) == 2



            ''' now create and assign a token and validate '''
            for resolver in resolvers:
                userlist = self.getUserList4Resolver(resolver, username='jörgi-' + resolver)
                assert len(userlist) == 1
                user = 'jörgi-%s@%s' % (resolver, realmName)
                serial = self.addToken(user, pin='jörgi')
                ''' preserve the serials, so we can delete them later '''
                tokenSerials.append(serial)
                resp = self.authToken(user, passw='jörgi')
                assert '"value": true' in resp



            ''' change the ldap uidType from entryUid to DN'''
            for entry in ldapResolvers:
                entry['uidType'] = 'DN'
                self.setupLDAPResolver(**entry)

            ''' check that token is now an orphand one '''
            for serial in tokenSerials:
                resp = self.showTokens(serial=serial)
                assert '"User.username": "/:no user info:/"' in resp


            ''' token should be marked as orphand '''
            for resolver in resolvers:
                userlist = self.getUserList4Resolver(resolver, username='jörgi-' + resolver)
                assert len(userlist) == 1
                user = 'jörgi-%s@%s' % (resolver, realmName)

                resp = self.authToken(user, passw='jörgi')
                assert '"value": false' in resp

                ''' re-assing the token to the DN User1 '''
                self.addToken(user, pin='jörgi')
                resp = self.authToken(user, passw='jörgi')
                assert '"value": true' in resp

            '''set policy otppin=1 ant test checkPass with Umlaut'''
            self.setOtpPinPolicy(realm=realmName)
            for resolver in resolvers:
                user = 'jörgi-%s@%s' % (resolver, realmName)
                passw = thePassword
                resp = self.authToken(user, passw=passw)
                assert '"value": true' in resp


            ''' @todo: policy: passthrough '''


        except Exception as e:
            log.error(e)
            log.error("%s" % traceback.format_exc())
            raise Exception(e)

        finally:

            ''' cleanup : undefine realm and resolvers '''
            parameters = {"realm":realmName}
            resp = self.app.get(url(controller='system', action='delRealm'), params=parameters)
            assert('"result": true' in resp)

            for resolver in resolvers:
                parameters = {"resolver" : resolver}
                resp = self.app.get(url(controller='system', action='delResolver'), params=parameters)
                assert('"status": true' in resp)

            ''' check that token is now an orphand one '''
            for serial in tokenSerials:
                resp = self.showTokens(serial=serial)
                assert '"User.username": "/:no user info:/"' in resp
                resp = self.delTokens(serial=serial)


            if len(ldapObjects) > 0:
                ldapObjects.reverse()

            for ldapObject in ldapObjects:
                try:
                    ldapServ.delete(ldapObject)
                except Exception as e:
                    if 'No such object' not in unicode(e):
                        raise Exception(e)

            ldapServ.unbind()

            ''' 5 - cleanup'''
            parameters = {'key':'enableReplication' }
            resp = self.app.get(url(controller='system', action='delConfig'), params=parameters)
            assert('"delConfig enableReplication": true' in resp)

            self.delOtpPinPolicy()
        return




