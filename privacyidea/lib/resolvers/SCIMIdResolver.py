# -*- coding: utf-8 -*-
#
#  product:  privacyIDEA is a fork of LinOTP
#  module:   resolver library
#    
#  May 08, 2014 Cornelius Kölbel
#  contact:  http://www.privacyidea.org
#            
#  product:  LinOTP2
#  module:   useridresolver
#  tool:     SCIMIdResolver
#  edition:  Comunity Edition
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
  Description:  This file is part of the privacyidea service
                This module implements the communication interface
                for resolving user information from a SCIM service

  Dependencies: -
'''

import logging
log = logging.getLogger(__name__)

from UserIdResolver import UserIdResolver
from UserIdResolver import getResolverClass
import json
import base64
import httplib2
from urllib import urlencode

# logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class IdResolver (UserIdResolver):

    @classmethod
    def setup(cls, config=None, cache_dir=None):
        '''
        this setup hook is triggered, when the server
        starts to serve the first request

        :param config: the privacyidea config
        :type  config: the privacyidea config dict
        '''
        log.info("Setting up the SCIMResolver")
        return

    def close(self):
        return
    
    def __init__(self):
        self.name = "scim-default"
        self.auth_server = ''
        self.resource_server = ''
        self.auth_client = 'localhost'
        self.auth_secret = ''        
        self.access_token = None

    @classmethod
    def get_access_token(self, server=None, client=None, secret=None):
        h = httplib2.Http()
        auth = base64.encodestring( client + ':' + secret )

        resp, content = h.request(
                                  "%s/oauth/token?grant_type=client_credentials" % server,
                                  'GET',
                                  headers = { 'Authorization' : 'Basic ' + auth }
                                  )
        if resp.get("status") != "200":
            raise Exception("Could not get access token: %s" % resp.get("status"))
        access_token = json.loads(content).get('access_token')
        return access_token

    def create_scim_object(self):
        self.access_token = self.get_access_token(self.auth_server, self.auth_client, self.auth_secret)


    def checkPass(self, uid, password):
        """
        This function checks the password for a given uid.
        - returns true in case of success
        -         false if password does not match

        TODO
        """
        return False

    def getUserInfo(self, userId):
        '''
        returns the user information for a given uid.
        '''
        ret = {}
        #res = self._search_with_get_on_users(self.resource_server,
        #                                     self.access_token,
        #                                     {"filter" : '%s eq "%s"' % (self.mapping.get("userid"),
        #
        #
        # The SCIM ID is always /Users/ID
        # Alas, we can not map the ID to any other attribute                                                              userId) })
        res = self._get_user(self.resource_server,
                             self.access_token,
                             userId)
        user = res
        #user = res.get("Resources", [{}])[0]

        ret['username'] = user.get(self.mapping.get("username"))
        ret['givenname'] = user.get(self.mapping.get("givenname"), "")
        ret['surname'] = user.get(self.mapping.get("surname"), "")
        ret['phone'] = user.get(self.mapping.get("phone"), "")
        ret['mobile'] = user.get(self.mapping.get("mobile"), "")
        ret['email'] = user.get(self.mapping.get("email"), "")

        return ret

    def getUsername(self, userId):
        '''
        returns the loginname for a given userId
        '''
        user = self.getUserInfo(userId)
        return user.get("username")


    def getUserId(self, LoginName):
        """
        returns the uid for a given loginname/username
        """
        res = {}
        if self.access_token:
            res = self._search_with_get_on_users(self.resource_server,
                                                 self.access_token,
                                                 {'filter' :  '%s eq "%s"' % (self.mapping.get("username"),
                                                           LoginName) })
        return res.get("Resources", [{}])[0].get(self.mapping.get("userid"))

    def getUserList(self, searchDict):
        '''
        Return the list of users
        '''
        ret = []

        '''
        TODO: search dict
        '''
        res = {}
        if self.access_token:
            res = self._search_with_get_on_users(self.resource_server,
                                                 self.access_token,
                                                 "")

        for user in res.get("Resources"):
            ret_user = {}
            ret_user['username'] = user.get(self.mapping.get("username"))
            ret_user['userid'] = user.get(self.mapping.get("userid"))
            ret_user['surname'] = user.get(self.mapping.get("surname"), "")
            ret_user['givenname'] = user.get(self.mapping.get("givenname"), "")
            ret_user['email'] = user.get(self.mapping.get("email"), "")
            ret_user['phone'] = user.get(self.mapping.get("phone"), "")
            ret_user['mobile'] = user.get(self.mapping.get("mobile"), "")

            ret.append(ret_user)

        return ret



#############################################################
# server inf methods
#############################################################
    def getResolverId(self):
        """ getResolverId(LoginName)
            - returns the resolver identifier string
            - empty string if not exist
        """
        return self.name

    def getResolverType(self):
        return IdResolver.getResolverClassType()

    @classmethod
    def getResolverClassType(cls):
        return 'scimresolver'

    @classmethod
    def getResolverClassDescriptor(cls):
        '''
        return the descriptor of the resolver, which is
        - the class name and
        - the config description

        :return: resolver description dict
        :rtype:  dict
        '''
        descriptor = {}
        typ = cls.getResolverClassType()
        descriptor['clazz'] = "useridresolver.SCIMIdResolver.IdResolver"
        descriptor['config'] = {'authserver' : 'string',
                                'resourceserver' : 'string',
                                'authclient' : 'string',
                                'authsecret' : 'string',
                                'mapping' : 'string' }
        return {typ : descriptor}

    def getResolverDescriptor(self):
        return IdResolver.getResolverClassDescriptor()

    def getConfigEntry(self, config, key, conf, required=True):
        ckey = key
        cval = ""
        if conf != "" or None:
            ckey = ckey + "." + conf
            if ckey in config:
                cval = config[ckey]
        if cval == "":
            if key in config:
                cval = config[key]
        if cval == "" and required == True:
            raise Exception("missing config entry: " + key)
        return cval

    def loadConfig(self, config, conf):
        """ loadConfig(configDict)
            The UserIdResolver could be configured
            from the pylon app config
        """
        self.name = conf
        self.auth_server = self.getConfigEntry(config, 'privacyidea.scimresolver.authserver', conf)
        self.resource_server = self.getConfigEntry(config, 'privacyidea.scimresolver.resourceserver', conf)
        self.auth_client = self.getConfigEntry(config, 'privacyidea.scimresolver.client', conf)
        self.auth_secret = self.getConfigEntry(config, 'privacyidea.scimresolver.secret', conf)
        self.mapping = json.loads(self.getConfigEntry(config, 'privacyidea.scimresolver.mapping', conf))
        self.create_scim_object()

        return


    @classmethod
    def testconnection(self, param):
        '''
        This function lets you test the to be saved SCIM connection.
              
        :param param: A dictionary with all necessary parameter to test the connection.
        :type param: dict
        
        :return: Tuple of success and a description
        :rtype: (bool, string)  
        
        Parameters are: Authserver, Resourceserver, Client, Secret, Map
            
        '''
        desc=None
        num = -1
               
        try:        
            access_token = self.get_access_token(str(param.get("Authserver")),
                                                 param.get("Client"),
                                                 param.get("Secret"))
            content = self._search_with_get_on_users(param.get("Resourceserver"), access_token, "")
            num = content.get("totalResults", -1)
        except Exception as exx:
            desc = "failed to retrieve users: %s" % exx
            
        return (num, desc)

    @classmethod
    def _search_with_get_on_users(self, resource_server, access_token, params=None):
        '''
        :param params: Additional http parameters added to the URL
        :type params: dictionary
        '''
        if params == None:
            params = {}
        headers = {'Authorization': "Bearer {0}".format(access_token),
                    'content-type': 'application/json'}
        h = httplib2.Http()
        url = '{0}/Users?{1}'.format(resource_server, urlencode(params))
        resp, content = h.request(url, 
                                  'GET',
                                  headers=headers)
        if resp.get("status") != "200":
            print "We were calling the URL ", url
            raise Exception("Could not get user list token: %s" % resp.get("status"))
        j_content = json.loads(content)
        return j_content
    
    @classmethod
    def _get_user(self, resource_server, access_token, userid):
        '''
        '''
        headers = {'Authorization': "Bearer {0}".format(access_token),
                    'content-type': 'application/json'}
        h = httplib2.Http()
        url = '{0}/Users/{1}'.format(resource_server, userid)
        resp, content = h.request(url, 
                                  'GET',
                                  headers=headers)
        if resp.get("status") != "200":
            print "We were calling the URL ", url
            raise Exception("Could not get user list token: %s" % resp.get("status"))
        j_content = json.loads(content)
        return j_content



if __name__ == "__main__":

    CLIENT = "schnuck"
    SECRET = "d81c31e4-9f65-4805-b5ba-6edf0761f954"
    AUTHSERVER = "http://localhost:8080/osiam-auth-server"
    RESOURCESERVER = "http://localhost:8080/osiam-resource-server"
    print " SCIMIdResolver - IdResolver class test "


    y = getResolverClass("SCIMIdResolver", "IdResolver")()
    
    print "======== testconnection ==========="
    print "getting token for %s, %s" % (CLIENT, SECRET)
    ret = y.testconnection({"Authserver": AUTHSERVER,
                      "Resourceserver" : RESOURCESERVER,
                      "Client" :CLIENT,
                      "Secret" : SECRET})
    print ret

    

    y.loadConfig({ 'privacyidea.scimresolver.authserver' : AUTHSERVER,
                  'privacyidea.scimresolver.resourceserver' : RESOURCESERVER,
                   'privacyidea.scimresolver.secret' : SECRET,
                   'privacyidea.scimresolver.client' : CLIENT,
                   'privacyidea.scimresolver.mapping' : '{ "username" : "userName" , "userid" : "id"}'}, "")

    print "==== the complete userlist ======="
    print y.getUserList({})
    print "=================================="

    user = "marissa"
    loginId = y.getUserId(user)

    print " %s -  %s" % (user , loginId)
    print " reId - " + y.getResolverId()

    ret = y.getUserInfo(loginId)
    print ret
    
    print "======== testconnection ==========="
    print "getting token for %s, %s" % (CLIENT, SECRET)
    ret = y.testconnection({"Authserver": AUTHSERVER,
                      "Resourceserver" : RESOURCESERVER,
                      "Client" :CLIENT,
                      "Secret" : SECRET})
    print ret

