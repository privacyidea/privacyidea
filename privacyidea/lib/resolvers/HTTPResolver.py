# -*- coding: utf-8 -*-
#
#  May, 08 2014 Cornelius Kölbel
#  http://www.privacyidea.org
#
#  product:  LinOTP2
#  module:   httpresolver
#  tool:     HTTPResolver
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

from .UserIdResolver import UserIdResolver
import requests
import logging
import json
from urllib.parse import urlencode
from pydash import get

ENCODING = "utf-8"

log = logging.getLogger(__name__)

class HTTPResolver(UserIdResolver):

    fields = {
        "endpoint": 1, 
        "method": 1,
        "requestMapping": 1,
        "responseMapping": 1,
        "hasSpecialErrorHandler": 0,
        "errorResponseMapping": 0
    }

    @staticmethod
    def getResolverClassType():
        """
        provide the resolver type for registration
        """
        return 'httpresolver'

    @staticmethod
    def getResolverType():
        """
        getResolverType - return the type of the resolver

        :return: returns the string 'ldapresolver'
        :rtype:  string
        """
        return HTTPResolver.getResolverClassType()

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
        descriptor['clazz'] = "useridresolver.HTTPResolver.HTTPResolver"
        descriptor['config'] = {
            'endpoint': 'string',
            'method': 'string',
            'headers': 'string',
            'requestMapping': 'string',
            'responseMapping': 'string',
            'hasSpecialErrorHandler': 'bool',
            'errorResponseMapping': 'string',
        }
        return {typ: descriptor}

    @staticmethod
    def getResolverDescriptor():
        """
        return the descriptor of the resolver, which is
        - the class name and
        - the config description

        :return: resolver description dict
        :rtype:  dict
        """
        return UserIdResolver.getResolverClassDescriptor()

    def getUserId(self, loginName):
        """
        The loginname is resolved to a user_id.
        Depending on the resolver type the user_id can
        be an ID (like in /etc/passwd) or a string (like
        the DN in LDAP)

        It needs to return an empty string, if the user does
        not exist.

        :param loginName: The login name of the user
        :type loginName: sting
        :return: The ID of the user
        :rtype: str
        """
        return loginName if loginName else ''

    def getUsername(self, userid):
        """
        Returns the username/loginname for a given userid
        :param userid: The userid in this resolver
        :type userid: string
        :return: username
        :rtype: string
        """
        return userid

    def getUserInfo(self, userid):
        """
        This function returns all user information for a given user object
        identified by UserID.
        :param userid: ID of the user in the resolver
        :type userid: int or string
        :return:  dictionary, if no object is found, the dictionary is empty
        :rtype: dict
        """
        return HTTPResolver._getUser(self.config, userid)
        
    def getUserList(self, searchDict=None):
        """
        Since it is an HTTP resolver, 
        users are not stored in the database
        """
        return []

    def getResolverId(self):
        """
        get resolver specific information
        :return: the resolver identifier string - empty string if not exist
        """
        return self.id

    def loadConfig(self, config):
        """
        Load the configuration from the dict into the Resolver object.
        If attributes are missing, need to set default values.
        If required attributes are missing, this should raise an
        Exception.

        :param config: The configuration values of the resolver
        :type config: dict
        """
        self.config = config
        return self

    def checkPass(self, uid, password):
        """
        This function checks the password for a given uid.
        returns true in case of success
        false if password does not match

        :param uid: The uid in the resolver
        :type uid: string or int
        :param password: the password to check. Usually in cleartext
        :type password: string
        :return: True or False
        :rtype: bool
        """
        return False

    def add_user(self, attributes=None):
        """
        Adding new users is not support for this kind of resolver
        """
        return None

    def delete_user(self, uid):
        """
        Delete a user is not supported for this kind of resolver
        """
        return None

    def update_user(self, uid, attributes=None):
        """
        Update an existing user is not supported for this kind of resolver
        """
        return None

    @classmethod
    def testconnection(cls, param):
        """
        This function lets you test if the parameters can be used to create a
        working resolver.
        The implementation should try to connect to the user store and verify
        if users can be retrieved.
        In case of success it should return a text like
        "Resolver config seems OK. 123 Users found."

        :param param: The parameters that should be saved as the resolver
        :type param: dict
        :return: returns True in case of success and a descriptive text
        :rtype: tuple
        """
        desc = ""
        success = False
        try:
            response = cls._getUser(param, param.get('testEmail'))
            desc = response
            success = True
        except Exception as e:
            success = False
            desc = "failed: {0!s}".format(e)
        return success, desc

    #
    #   Private methods
    #
    @classmethod
    def _getUser(self, param, userid):
        method = param.get('method').lower()
        endpoint = param.get('endpoint')
        requestMappingJSON = json.loads(param.get('requestMapping').replace("{userid}", userid))
        responseMapping = json.loads(param.get('responseMapping'))
        headers = json.loads(param.get('headers', '{}'))
        hasSpecialErrorHandler = bool(param.get('hasSpecialErrorHandler'))
        errorResponseMapping = json.loads(param.get('errorResponseMapping', '{}'))

        if method not in ('post', 'get'):
            raise Exception('Method have to be "GET" or "POST"')

        if method == "post":
            httpResponse = requests.post(endpoint, json=requestMappingJSON, headers=headers)
        else:
            httpResponse = requests.get(endpoint, urlencode(requestMappingJSON), headers=headers)

        if httpResponse.status_code >= 400:
            raise Exception(httpResponse.status_code, httpResponse.text)

        jsonHTTPResponse = httpResponse.json()

        if hasSpecialErrorHandler:
            # verify if error response mapping is a subset of the json http response
            if errorResponseMapping.items() <= jsonHTTPResponse.items():
                raise Exception(jsonHTTPResponse)

        # Create mapped response with response mapping resolver input
        response = {}
        for pi_user_key, value in responseMapping.items():
            if value.startswith('{') and value.endswith('}'):
                response[pi_user_key] = get(jsonHTTPResponse, value[1:-1])
            else:
                response[pi_user_key] = value

        return response
