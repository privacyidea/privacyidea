# -*- coding: utf-8 -*-
#  Copyright (C) 2014 Cornelius Kölbel
#  contact:  corny@cornelinux.de#
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


import logging
import ldap
import yaml

from UserIdResolver import UserIdResolver
from UserIdResolver import getResolverClass
from privacyidea.lib.log import log_with
from gettext import gettext as _

log = logging.getLogger(__name__)
ENCODING = "utf-8"
       
'''
TODO:
  * Encoding
  * redundancy
  * Timeout
  * Referral
'''       
       
class IdResolver (UserIdResolver):


    @classmethod
    def setup(cls, config=None, cache_dir=None):
        '''
        this setup hook is triggered, when the server 
        starts to serve the first request

        :param config: the privacyidea config
        :type  config: the privacyidea config dict
        '''
        log.info("Setting up the LDAPResolver")
        return    
    
    def __init__(self):
        self.i_am_bound = False
        return

    def checkPass(self, uid, password):
        """
        This function checks the password for a given uid.
        - returns true in case of success
        -         false if password does not match
        
        """
        DN = self._getDN(uid)
        
        l = ldap.initialize(self.uri)
        try:
            l.bind_s(DN, password)
            l.unbind()
        except Exception, e:
            log.warning("failed to check password for %r/%r: %r" % (uid, DN, e))
            return False
        
        return True
        
    def _getDN(self, userId):
        '''
        This function returns the DN of a userId.
        Therefor it evaluates the self.uidtype.
        
        :param userId: The userid of a user
        :type userId: string
        
        :return: The DN of the object. 
        '''
        DN = ""
        if self.uidtype == "dn":
            DN = userId
        else:
            # get the DN for the Object
            self._bind()
            _filter = "(&%s(%s=%s))" % (self.searchfilter, self.uidtype, userId )
            r = self.l.search_s(self.basedn,
                                ldap.SCOPE_SUBTREE,
                                _filter,
                                self.userinfo.values())
                
        if len(r) > 1:
            raise Exception("Found more than one object for uid %r" % userId)

        for dn, entry in r:
            DN = dn
        
        return DN
        
    def _bind(self):
        if not self.i_am_bound:
            self.l = ldap.initialize(self.uri)
            self.l.bind_s(self.binddn, self.bindpw)
            self.i_am_bound = True

        
    def _unbind(self):
        self.l.unbind_s()
    
    def getUserInfo(self,userId):
        '''
        This function returns all user info for a given userid/object.
        
        :param userId: The userid of the object
        :type userId: string
        :return: A dictionary with the keys defined in self.userinfo
        :rtype: dict
        '''
        ret = {}
        self._bind()      
        
        if self.uidtype.lower() == "dn":
            r = self.l.search_s(userId,
                                ldap.SCOPE_SUBTREE,
                                "(&" + self.searchfilter + ")",
                                attrlist=self.userinfo.values())
        else: 
            _filter = "(&%s(%s=%s))" % (self.searchfilter, self.uidtype, userId )
            r = self.l.search_s(self.basedn,
                                ldap.SCOPE_SUBTREE,
                                _filter,
                                self.userinfo.values())
                
        if len(r) > 1:
            raise Exception("Found more than one object for uid %r" % userId)

        for dn,entry in r:
            for k, v in entry.items():
                key = self.reverse_map[k]
                ret[key] = v[0]  
        
        return ret  
    

    def getUsername(self,userId):
        '''
        returns true, if a user id exists
        '''
        info = self.getUserInfo(userId)
        return info.has_key('username')
   
    
    def getUserId(self, LoginName):
        ''' 
        resolve the loginname to the userid. 
        
        :param LoginName: The login name from the credentials
        :type LoginName: string
        :return: UserId as found for the LoginName
        '''
        userid = ""
        self._bind()
        _filter = "(&%s(%s=%s))" % (self.searchfilter, self.loginname_attribute, LoginName)
        
        attributes = self.userinfo.values()
        if self.uidtype.lower() != "dn":
            attributes.append(str(self.uidtype))
            
        r = self.l.search_s(self.basedn,
                       ldap.SCOPE_SUBTREE,
                       _filter,
                       attributes)
        
        if len(r) > 1:
            raise Exception("Found more than one object for Loginname %r" % LoginName)
        
        for dn, entry in r:
            if self.uidtype.lower() == "dn":
                userid = dn
            else:
                userid = entry.get(self.uidtype)[0]
        
        return userid

    def getUserList(self, searchDict):
        '''
        :param searchDict: A dictionary with search parameters
        :type searchDict: dict
        :return: list of users, where each user is a dictionary
        '''
        ret = []
        self._bind()
        attributes = self.userinfo.values()
        if self.uidtype.lower() != "dn":
            attributes.append(str(self.uidtype))
            
        # do the filter depending on the searchDict
        _filter = "(&" + self.searchfilter
        for search_key in searchDict.keys():
            _filter += "(%s=%s)" % (self.userinfo[search_key], searchDict[search_key])
        _filter += ")"
            
        r = self.l.search_s(self.basedn,
                       ldap.SCOPE_SUBTREE,
                       _filter,
                       attributes)
        
        for dn,entry in r:
            user = {}
            if self.uidtype == "dn":
                user['userid'] = dn
            else:
                user['userid'] = entry.get(self.uidtype)[0]
                del(entry[self.uidtype])
            for k, v in entry.items():
                key = self.reverse_map[k]
                user[key] = v[0]
            ret.append(user)        
        
        return ret

    
    def getResolverId(self):
        '''
        Returns the resolver Id
        This should be an Identifier of the resolver, preferable the type and the name of the resolver.
        '''
        return "ldapresolver." + self.resolverId

    @classmethod
    def getResolverClassType(cls):
        return 'ldapresolver'

    def getResolverType(self):
        return IdResolver.getResolverClassType()    
    
    def loadConfig(self, config, conf):
        '''
        Load the config from conf.
        
        :param config: The configuration from the Config Table
        :type config: dict
        :param conf: the instance of the configuration
        :type conf: string 
        
        The information which config entries we need to load is taken from
            manage.js: function save_ldap_config
            
                    '#ldap_uri': 'LDAPURI',
                    '#ldap_basedn': 'LDAPBASE',
                    '#ldap_binddn': 'BINDDN',
                    '#ldap_password': 'BINDPW',
                    '#ldap_timeout': 'TIMEOUT',
                    '#ldap_sizelimit': 'SIZELIMIT',
                    '#ldap_loginattr': 'LOGINNAMEATTRIBUTE',
                    '#ldap_searchfilter': 'LDAPSEARCHFILTER',
                    '#ldap_userfilter': 'LDAPFILTER',
                    '#ldap_mapping': 'USERINFO',
                    '#ldap_uidtype': 'UIDTYPE',
                    '#ldap_noreferrals' : 'NOREFERRALS',
                    '#ldap_certificate': 'CACERTIFICATE',
                    
        '''
        self.resolverId = conf
        
        self.uri = self.getConfigEntry(config, 'privacyidea.ldapresolver.LDAPURI', conf)
        self.basedn = self.getConfigEntry(config, 'privacyidea.ldapresolver.LDAPBASE', conf)
        self.binddn = self.getConfigEntry(config, 'privacyidea.ldapresolver.BINDDN', conf, required=False)
        self.bindpw = self.getConfigEntry(config, 'privacyidea.ldapresolver.BINDPW', conf, required=False)
        self.timeout = self.getConfigEntry(config, 'privacyidea.ldapresolver.TIMEOUT', conf, required=False, default=5000)
        self.sizelimit = self.getConfigEntry(config, 'privacyidea.ldapresolver.SIZELIMIT', conf, required=False, default=500)
        self.loginname_attribute = self.getConfigEntry(config, 'privacyidea.ldapresolver.LOGINNAMEATTRIBUTE', conf)
        self.searchfilter = self.getConfigEntry(config, 'privacyidea.ldapresolver.LDAPSEARCHFILTER', conf)
        self.reversefilter = self.getConfigEntry(config, 'privacyidea.ldapresolver.LDAPFILTER', conf)
        userinfo = self.getConfigEntry(config, 'privacyidea.ldapresolver.USERINFO', conf)
        self.userinfo = yaml.load(userinfo)
        self.reverse_map = dict([[v,k] for k,v in self.userinfo.items()])
        self.uidtype = self.getConfigEntry(config, 'privacyidea.ldapresolver.UIDTYPE', conf, required=False)
        self.noreferrals = self.getConfigEntry(config, 'privacyidea.ldapresolver.NOREFERRALS', conf, required=False, default=False)
        self.certificate = self.getConfigEntry(config, 'privacyidea.ldapresolver.CACERTIFICATE', conf, required=False)
        
        return self
    
    


    def getResolverDescriptor(self):
        descriptor = {}
        typ = self.getResolverType()
        descriptor['clazz'] = "useridresolver.LDAPIdResolver.IdResolver" 
        descriptor['config'] = {'LDAPURI' : 'string',
                                'LDAPBASE' : 'string',
                                'BINDDN' : 'string',
                                'BINDPW' : 'string',
                                'TIMEOUT' : 'int',
                                'SIZELIMIT' : 'int',
                                'LOGINNAMEATTRIBUTE' : 'string',
                                'LDAPSEARCHFILTER' : 'string',
                                'LDAPFILTER' : 'string',
                                'USERINFO' : 'string',
                                'UIDTYPE' : 'string',
                                'NOREFERRALS' : 'bool',
                                'CACERTIFICATE' : 'string'}
        return {typ : descriptor}


    def getConfigEntry(self, config, key, conf, required=True, default=None):
        ckey = key
        cval = "" 
        if conf != "" or None:
            ckey = ckey + "." + conf
            if config.has_key(ckey):
                cval = config[ckey]
        if cval == "":
            if config.has_key(key):
                cval = config[key]
        if cval == "" and required == True:
            raise Exception("missing config entry: " + key)
        if cval == "" and default:
            cval = default
        return cval

            
    @classmethod
    @log_with(log)
    def testconnection(self, param):
        '''
        This function lets you test the to be saved LDAP connection.
        
        This is taken from controllers/admin.py
        
        :param param: A dictionary with all necessary parameter to test the connection.
        :type param: dict
        
        :return: Tuple of success and a description
        :rtype: (bool, string)  
        
        Parameters are:
            BINDDN, BINDPW, LDAPURI, TIMEOUT, LDAPBASE, LOGINNAMEATTRIBUTE, LDAPSEARCHFILTER,
            LDAPFILTER, USERINFO, SIZELIMIT, NOREFERRALS, CACERTIFICATE
        '''
        
        success=False
        desc=None
        try:
            l = ldap.initialize(param["LDAPURI"])
            l.bind_s(param["BINDDN"], param["BINDPW"])
            # search for users...
            r = l.search_s(param["LDAPBASE"],
                       ldap.SCOPE_SUBTREE,
                       "(&" + param["LDAPSEARCHFILTER"] + ")",
                       yaml.load(param["USERINFO"]).values())
        
            count = len(r)
            desc = _("Your LDAP config seems to be OK, %i user objects found.") % count
            
            l.unbind()
            success = True
            
        except Exception, e:
            desc = "%r" % e
        
        return (success, desc)
    
    

if __name__ == "__main__":

    print " LDAPIdResolver - IdResolver class test "
        
    y = getResolverClass("LDAPIdResolver", "IdResolver")()
    
    print y
    

    y.loadConfig({ 'privacyidea.ldapresolver.LDAPURI' : 'ldap://localhost:1389',
              'privacyidea.ldapresolver.LDAPBASE' : 'ou=users,dc=az,dc=local',
              'privacyidea.ldapresolver.BINDDN' : 'cn=admin,dc=az,dc=local',
              'privacyidea.ldapresolver.BINDPW' : 'LDpw.',
              'privacyidea.ldapresolver.LOGINNAMEATTRIBUTE': 'uid',
              'privacyidea.ldapresolver.LDAPSEARCHFILTER' : '(uid=*)(objectClass=inetOrgPerson)',
              'privacyidea.ldapresolver.LDAPFILTER' : '(&(uid=%s)(objectClass=inetOrgPerson))',
              'privacyidea.ldapresolver.USERINFO' : '{ "username": "uid", \
                      "phone" : "telephoneNumber", \
                      "mobile" : "mobile", \
                      "email" : "mail", \
                      "surname" : "sn", \
                      "givenname" : "givenName" }',
              'privacyidea.ldapresolver.UIDTYPE' : 'DN',                      
              }, "")

    print "Config loaded"
    
    
    print "====== getUserList =========="
    result = y.getUserList({'username' : '*'})
    for entry in result:
        print entry
    print "============================="
        
    user = "koelbel"
    loginId = y.getUserId(user)

    print " %s -  %s" % ( user , loginId )
    print " reId - " + y.getResolverId()
    print "============================="

    ret = y.getUserInfo(loginId)  
    print "Userinfo for %r" % loginId
    print ret
    print "============================="
    
    ret = y.getSearchFields()
    #ret["username"]="^bea*"
    search = { 
               "userid":" between 1000, 1005",
#              "username":"^bea*",
              #"description":"*Audio*",
#              "descriptio":"*Winkler*",
#              "userid":" <=1003",
              }
    #
    
    ret = y.getUserList(search)
    
    print ret
