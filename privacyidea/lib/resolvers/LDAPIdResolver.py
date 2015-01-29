# -*- coding: utf-8 -*-
#  Copyright (C) 2014 Cornelius Kölbel
#  contact:  corny@cornelinux.de
#
#  2014-12-25 Cornelius Kölbel <cornelius@privacyidea.org>
#             Rewrite for flask migration
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
__doc__ = """This is the resolver to find users in LDAP directories like
OpenLDAP and Active Directory.

The file is tested in tests/test_lib_resolver.py
"""

import logging
import ldap
import yaml
import traceback

from UserIdResolver import UserIdResolver
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
        """
        this setup hook is triggered, when the server
        starts to serve the first request

        :param config: the privacyidea config
        :type  config: the privacyidea config dict
        """
        log.info("Setting up the LDAPResolver")
        return
    
    def __init__(self):
        self.i_am_bound = False
        self.uri = ""
        self.basedn = ""
        self.binddn = ""
        self.bindpw = ""
        self.timeout = 5000
        self.sizelimit = 500
        self.loginname_attribute = ""
        self.searchfilter = ""
        self.reversefilter = ""
        self.userinfo = {}
        self.reverse_map = {}
        self.uidtype = ""
        self.noreferrals = False
        self.certificate = ""
        self.resolverId = self.uri

    def checkPass(self, uid, password):
        """
        This function checks the password for a given uid.
        - returns true in case of success
        -         false if password does not match
        
        """
        DN = self._getDN(uid)
        
        l = ldap.initialize(self.uri)
        try:
            l.simple_bind_s(DN, password)
            l.unbind()
        except Exception, e:
            log.warning("failed to check password for %r/%r: %r"
                        % (uid, DN, e))
            return False
        
        return True

    def _get_uid(self, entry):
        uid = None
        if type(entry.get(self.uidtype)) == list:
            uid = entry.get(self.uidtype)[0]
        else:
            uid = entry.get(self.uidtype)
        return uid
        
    def _getDN(self, userId):
        """
        This function returns the DN of a userId.
        Therefor it evaluates the self.uidtype.
        
        :param userId: The userid of a user
        :type userId: string
        
        :return: The DN of the object.
        """
        dn = ""
        if self.uidtype.lower() == "dn":
            dn = userId
        else:
            # get the DN for the Object
            self._bind()
            filter = "(&%s(%s=%s))" % \
                (self.searchfilter, self.uidtype, userId)
            r = self.l.search_s(self.basedn,
                                ldap.SCOPE_SUBTREE,
                                filter,
                                self.userinfo.values())
                
            if len(r) > 1:  # pragma nocover
                raise Exception("Found more than one object for uid %r"
                                % userId)

            for dn, _entry in r:
                pass
        
        return dn
        
    def _bind(self):
        if not self.i_am_bound:
            self.l = ldap.initialize(self.uri)
            self.l.simple_bind_s(self.binddn, self.bindpw)
            self.i_am_bound = True

    def getUserInfo(self, userId):
        """
        This function returns all user info for a given userid/object.
        
        :param userId: The userid of the object
        :type userId: string
        :return: A dictionary with the keys defined in self.userinfo
        :rtype: dict
        """
        ret = {}
        self._bind()
        
        if self.uidtype.lower() == "dn":
            r = self.l.search_s(userId,
                                ldap.SCOPE_SUBTREE,
                                "(&" + self.searchfilter + ")",
                                attrlist=self.userinfo.values())
        else:
            filter = "(&%s(%s=%s))" %\
                (self.searchfilter, self.uidtype, userId)
            r = self.l.search_s(self.basedn,
                                ldap.SCOPE_SUBTREE,
                                filter,
                                self.userinfo.values())
                
        if len(r) > 1:  # pragma nocover
            raise Exception("Found more than one object for uid %r" % userId)

        for _dn, entry in r:
            for k, v in entry.items():
                key = self.reverse_map[k]
                if type(v) == list:
                    ret[key] = v[0]
                else:
                    ret[key] = v
        
        return ret
    
    def getUsername(self, user_id):
        """
        Returns the username/loginname for a given user_id
        :param user_id: The user_id in this resolver
        :type user_id: string
        :return: username
        :rtype: string
        """
        info = self.getUserInfo(user_id)
        return info.get('username', "")
   
    def getUserId(self, LoginName):
        """
        resolve the loginname to the userid.
        
        :param LoginName: The login name from the credentials
        :type LoginName: string
        :return: UserId as found for the LoginName
        """
        userid = ""
        self._bind()
        filter = "(&%s(%s=%s))" % \
            (self.searchfilter, self.loginname_attribute, LoginName)
        
        attributes = self.userinfo.values()
        if self.uidtype.lower() != "dn":
            attributes.append(str(self.uidtype))
            
        r = self.l.search_s(self.basedn,
                            ldap.SCOPE_SUBTREE,
                            filter,
                            attributes)
        
        if len(r) > 1:  # pragma nocover
            raise Exception("Found more than one object for Loginname %r" %
                            LoginName)
        
        for dn, entry in r:
            if self.uidtype.lower() == "dn":
                userid = dn
            else:
                userid = self._get_uid(entry)
        
        return userid

    def getUserList(self, searchDict):
        """
        :param searchDict: A dictionary with search parameters
        :type searchDict: dict
        :return: list of users, where each user is a dictionary
        """
        ret = []
        self._bind()
        attributes = self.userinfo.values()
        if self.uidtype.lower() != "dn":
            attributes.append(str(self.uidtype))
            
        # do the filter depending on the searchDict
        filter = "(&" + self.searchfilter
        for search_key in searchDict.keys():
            filter += "(%s=%s)" % \
                (self.userinfo[search_key], searchDict[search_key])
        filter += ")"
            
        r = self.l.search_s(self.basedn,
                            ldap.SCOPE_SUBTREE,
                            filter,
                            attributes)
        
        for dn, entry in r:
            try:
                user = {}
                if self.uidtype.lower() == "dn":
                    user['userid'] = dn
                else:
                    user['userid'] = self._get_uid(entry)
                    del(entry[self.uidtype])
                for k, v in entry.items():
                    key = self.reverse_map[k]
                    if type(v) == list:
                        user[key] = v[0]
                    else:
                        user[key] = v
                ret.append(user)
            except Exception as exx:  # pragma nocover
                log.error("Error during fetching LDAP objects: %r" % exx)
                log.error("%r" % traceback.format_exc())
        
        return ret
    
    def getResolverId(self):
        """
        Returns the resolver Id
        This should be an Identifier of the resolver, preferable the type
        and the name of the resolver.
        """
        return self.uri

    @classmethod
    def getResolverClassType(cls):
        return 'ldapresolver'

    @classmethod
    def getResolverType(cls):
        return IdResolver.getResolverClassType()
    
    def loadConfig(self, config):
        """
        Load the config from conf.
        
        :param config: The configuration from the Config Table
        :type config: dict

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
                    
        """
        self.uri = config.get("LDAPURI")
        self.basedn = config.get("LDAPBASE")
        self.binddn = config.get("BINDDN")
        self.bindpw = config.get("BINDPW")
        self.timeout = config.get("TIMEOUT", 5000)
        self.sizelimit = config.get("SIZELIMIT", 500)
        self.loginname_attribute = config.get("LOGINNAMEATTRIBUTE")
        self.searchfilter = config.get("LDAPSEARCHFILTER")
        self.reversefilter = config.get("LDAPFILTER")
        userinfo = config.get("USERINFO", "{}")
        self.userinfo = yaml.load(userinfo)
        self.reverse_map = dict([[v, k] for k, v in self.userinfo.items()])
        self.uidtype = config.get("UIDTYPE", "DN")
        self.noreferrals = config.get("NOREFERRALS", False)
        self.certificate = config.get("CACERTIFICATE")
        self.resolverId = self.uri
        
        return self

    @classmethod
    def getResolverClassDescriptor(cls):
        """
        return the descriptor of the resolver, which is
        - the class name and
        - the config description

        :return: resolver description dict
        :rtype:  dict
        """
        descriptor = {}
        typ = cls.getResolverType()
        descriptor['clazz'] = "useridresolver.LDAPIdResolver.IdResolver"
        descriptor['config'] = {'LDAPURI': 'string',
                                'LDAPBASE': 'string',
                                'BINDDN': 'string',
                                'BINDPW': 'password',
                                'TIMEOUT': 'int',
                                'SIZELIMIT': 'int',
                                'LOGINNAMEATTRIBUTE': 'string',
                                'LDAPSEARCHFILTER': 'string',
                                'LDAPFILTER': 'string',
                                'USERINFO': 'string',
                                'UIDTYPE': 'string',
                                'NOREFERRALS': 'bool',
                                'CACERTIFICATE': 'string'}
        return {typ: descriptor}

    def getResolverDescriptor(self):
        return IdResolver.getResolverClassDescriptor()

    @classmethod
    def testconnection(self, param):
        """
        This function lets you test the to be saved LDAP connection.
        
        This is taken from controllers/admin.py
        
        :param param: A dictionary with all necessary parameter to test
                        the connection.
        :type param: dict
        
        :return: Tuple of success and a description
        :rtype: (bool, string)
        
        Parameters are:
            BINDDN, BINDPW, LDAPURI, TIMEOUT, LDAPBASE, LOGINNAMEATTRIBUTE,
            LDAPSEARCHFILTER,
            LDAPFILTER, USERINFO, SIZELIMIT, NOREFERRALS, CACERTIFICATE
        """
        success = False
        try:
            l = ldap.initialize(param["LDAPURI"])
            l.simple_bind_s(param["BINDDN"], param["BINDPW"])
            # search for users...
            r = l.search_s(param["LDAPBASE"],
                           ldap.SCOPE_SUBTREE,
                           "(&" + param["LDAPSEARCHFILTER"] + ")",
                           yaml.load(param["USERINFO"]).values())
        
            count = len(r)
            desc = _("Your LDAP config seems to be OK, %i user objects found.")\
                % count
            
            l.unbind()
            success = True
            
        except Exception, e:
            desc = "%r" % e
        
        return success, desc
