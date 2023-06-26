# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#
#  2015-04-15 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Migrate SCIM Resolver to work with privacyidea 2 (Flask)
#
#  May 08, 2014 Cornelius Kölbel
#  contact:  http://www.privacyidea.org
#
#  product:  LinOTP2
#  module:   useridresolver
#  tool:     SCIMIdResolver
#  edition:  Community Edition
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
__doc__ = """This is the resolver to find users in a SCIM service.

The file is tested in tests/test_lib_resolver.py
"""

import logging
import traceback

from .UserIdResolver import UserIdResolver
import yaml
import requests
import base64
from urllib.parse import urlencode
from privacyidea.lib.utils import to_bytes, to_unicode, convert_column_to_unicode

log = logging.getLogger(__name__)


class IdResolver (UserIdResolver):

    def __init__(self):
        self.auth_server = ''
        self.resource_server = ''
        self.auth_client = 'localhost'
        self.auth_secret = ''  # nosec B105 # default parameter
        self.access_token = None

    def checkPass(self, uid, password):
        """
        This function checks the password for a given uid.
        - returns true in case of success
        -         false if password does not match

        """
        # TODO: Implement password checking with SCIM
        return False

    def getUserInfo(self, userid):
        """
        returns the user information for a given uid.
        """
        ret = {}
        # The SCIM ID is always /Users/ID
        # Alas, we can not map the ID to any other attribute
        res = self._get_user(self.resource_server,
                             self.access_token,
                             userid)
        user = res
        ret = self._fill_user_schema_1_0(user)

        return ret

    @staticmethod
    def _fill_user_schema_1_0(user):
        # We assume the schema:
        # "schemas": ["urn:scim:schemas:core:1.0"]

        #ret['username'] = user.get(self.mapping.get("username"))
        #ret['givenname'] = user.get(self.mapping.get("givenname"), "")
        #ret['surname'] = user.get(self.mapping.get("surname"), "")
        #ret['phone'] = user.get(self.mapping.get("phone"), "")
        #ret['mobile'] = user.get(self.mapping.get("mobile"), "")
        #ret['email'] = user.get(self.mapping.get("email"), "")

        ret = {"phone": "",
               "email": "",
               "mobile": ""}
        ret['username'] = user.get("userName", {})
        ret['givenname'] = user.get("name", {}).get("givenName", "")
        ret['surname'] = user.get("name", {}).get("familyName", "")
        if user.get("phoneNumbers", {}):
            ret['phone'] = user.get("phoneNumbers")[0].get("value")
        if user.get("emails", {}):
            ret['email'] = user.get("emails")[0].get("value")
        return ret

    def getUsername(self, userid):
        """
        Returns the username/loginname for a given userid
        :param userid: The userid in this resolver
        :type userid: string
        :return: username
        :rtype: string
        """
        #user = self.getUserInfo(userid)
        #return user.get("username", "")
        # It seems that the userName is the UserId
        return userid

    def getUserId(self, loginName):
        """
        returns the uid for a given loginname/username
        :rtype: str
        """
        #res = {}
        #if self.access_token:
        #    res = self._search_users(self.resource_server,
        #                                         self.access_token,
        #                                         {'filter': '%s eq "%s"' %
        #                                          ("userName", loginName)})
        #return res.get("Resources", [{}])[0].get("externalId")
        # It seems that the userName is the userId
        return convert_column_to_unicode(loginName)

    def getUserList(self, searchDict=None):
        """
        Return the list of users
        """
        ret = []

        # TODO: search dict is not used at the moment
        res = {}
        if self.access_token:
            res = self._search_users(self.resource_server,
                                                 self.access_token,
                                                 "")

        for user in res.get("Resources"):
            ret_user = self._fill_user_schema_1_0(user)

            ret.append(ret_user)

        return ret

    def getResolverId(self):
        """
        :return: the resolver identifier string, empty string if not exist
        """
        return self.auth_server

    @staticmethod
    def getResolverClassType():
        return 'scimresolver'

    @staticmethod
    def getResolverDescriptor():
        return IdResolver.getResolverClassDescriptor()

    @staticmethod
    def getResolverType():
        return IdResolver.getResolverClassType()

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
        typ = cls.getResolverClassType()
        descriptor['clazz'] = "useridresolver.SCIMIdResolver.IdResolver"
        descriptor['config'] = {'authserver': 'string',
                                'resourceserver': 'string',
                                'authclient': 'string',
                                'authsecret': 'string',
                                'mapping': 'string'}
        return {typ: descriptor}

    def loadConfig(self, config):
        """load the configuration to the Resolver instance

        Keys in the dict are
         * Authserver
         * Resouceserver
         * Client
         * Secret
         * Mapping

        :param config: the configuration dictionary
        :type config: dict
        :return: the resolver instance
        """
        self.auth_server = config.get('Authserver')
        self.resource_server = config.get('Resourceserver')
        self.auth_client = config.get('Client')
        self.auth_secret = config.get('Secret')
        self.mapping = yaml.safe_load(config.get('Mapping'))
        self.create_scim_object()
        return self

    @classmethod
    def testconnection(cls, param):
        """
        This function lets you test the to be saved SCIM connection.
              
        :param param: A dictionary with all necessary parameter to test the
                        connection.
        :type param: dict
        :return: Tuple of success and a description
        :rtype: (bool, string)
        
        Parameters are: Authserver, Resourceserver, Client, Secret, Mapping
        """
        desc = None
        success = False
               
        try:
            access_token = cls.get_access_token(str(param.get("Authserver")),
                                                param.get("Client"),
                                                param.get("Secret"))
            content = cls._search_users(param.get("Resourceserver"),
                                                    access_token, "")
            num = content.get("totalResults", -1)
            desc = "Found {0!s} users".format(num)
            success = True
        except Exception as exx:
            log.error("Failed to retrieve users: {0!s}".format(exx))
            log.debug("{0!s}".format(traceback.format_exc()))
            desc = "failed to retrieve users: {0!s}".format(exx)
            
        return success, desc

    @staticmethod
    def _search_users(resource_server, access_token, params=None):
        """
        :param params: Additional http parameters added to the URL
        :type params: dictionary
        """
        params = params or {}
        headers = {'Authorization': "Bearer {0}".format(access_token),
                   'content-type': 'application/json'}
        url = '{0}/Users?{1}'.format(resource_server, urlencode(params))
        resp = requests.get(url, headers=headers, timeout=60)
        if resp.status_code != 200:
            info = "Could not get user list: {0!s}".format(resp.status_code)
            log.error(info)
            raise Exception(info)
        j_content = yaml.safe_load(resp.content)

        return j_content
    
    @staticmethod
    def _get_user(resource_server, access_token, userid):
        """
        Get a User from the SCIM service

        :param resource_server: The Resource Server
        :type resource_server: basestring / URI
        :param access_token: Access Token
        :type access_token: basestring
        :param userid: The userid to fetch
        :type userid: basestring
        :return: Dictionary of User object.
        """
        headers = {'Authorization': "Bearer {0}".format(access_token),
                   'content-type': 'application/json'}
        url = '{0}/Users/{1}'.format(resource_server, userid)
        resp = requests.get(url, headers=headers, timeout=60)

        if resp.status_code != 200:
            info = "Could not get user: {0!s}".format(resp.status_code)
            log.error(info)
            raise Exception(info)
        j_content = yaml.safe_load(resp.content)

        return j_content

    @staticmethod
    def get_access_token(server=None, client=None, secret=None):

        auth = to_unicode(base64.b64encode(to_bytes(client + ':' + secret)))

        url = "{0!s}/oauth/token?grant_type=client_credentials".format(server)
        resp = requests.get(url,
                            headers={'Authorization': 'Basic ' + auth},
                            timeout=60)

        if resp.status_code != 200:
            info = "Could not get access token: {0!s}".format(resp.status_code)
            log.error(info)
            raise Exception(info)

        access_token = yaml.safe_load(resp.content).get('access_token')
        return access_token

    def create_scim_object(self):
        self.access_token = self.get_access_token(self.auth_server,
                                                  self.auth_client,
                                                  self.auth_secret)
