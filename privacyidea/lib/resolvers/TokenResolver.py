#  Mar, 12 2020 Bruno Cascio
#  http://www.privacyidea.org
#
#  product:  PrivacyIDEA
#  module:   httpresolver
#  tool:     HTTPResolver
#  edition:  Comunity Edition
#
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

import yaml
from .UserIdResolver import UserIdResolver
import jwt
import logging
from pydash import get

__name__ = "TOKEN_RESOLVER"

ENCODING = "utf-8"
SYMMETRICAL_ALGORITHMS = ["HS256", "HS384", "HS512"]

log = logging.getLogger(__name__)


class TokenResolver(UserIdResolver):
    def __init__(self):
        super(TokenResolver, self).__init__()
        self.methodAllowed = ""
        self.secret = ""
        self.responseMapping = {}
        self.user_id = ""
        self.username = ""
        self.token_data = {}

    @staticmethod
    def getResolverClassType():
        """
        provide the resolver type for registration
        """
        return 'tokenresolver'

    @staticmethod
    def getResolverType():
        """
        getResolverType - return the type of the resolver

        :return: returns the string 'ldapresolver'
        :rtype:  string
        """
        return TokenResolver.getResolverClassType()

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
        descriptor['clazz'] = "useridresolver.TokenResolver.TokenResolver"
        descriptor['config'] = {
            'methodAllowed': 'string',
            'secret': 'string',
            'responseMapping': 'string',
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
        return TokenResolver.getResolverClassDescriptor()

    def getUserId(self, loginName):
        """
        return the userid for the given user by loginName or the loginName in unicode format

        :return: the userid
        :rtype:  string
        """
        if self.user_id != "":
            return self.user_id
        elif self.token_data and 'userid' in self.token_data:
            return self.token_data['userid']

        log.info("no userid found")
        if isinstance(loginName, str):
            return loginName
        elif isinstance(loginName, bytes):
            return loginName.decode(ENCODING)
        return loginName

    def getUsername(self, userid):
        """
        return the username for the given user by userid

        :return: the username
        :rtype:  string
        """
        if self.username != "":
            return self.username
        elif self.token_data and 'username' in self.token_data:
            return self.token_data['username']
        return str(userid)

    def getUserInfo(self, userid):
        """
        This function returns all user information for a given user object
        identified by UserID.
        :param userid: ID of the user in the resolver
        :type userid: int or string
        :return:  dictionary, if no object is found, the dictionary is empty
        :rtype: dict
        """
        if self.token_data:
            return self.token_data

        return {"userid": self.getUserId(userid), "username": self.getUsername(userid)}

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
        success = False
        try:
            response = self._getUser(password)
            if response.get('userid') == str(uid) or response.get('username') == str(uid):
                self.user_id = response.get('userid')
                self.username = response.get('username')
                success = True
        except Exception as e:
            success = False
            log.error("error validating token with exception: {0!s}".format(e))
        return success

    def loadConfig(self, config):
        """
        Load the configuration from the dict into the Resolver object.
        If attributes are missing, need to set default values.
        If required attributes are missing, this should raise an
        Exception.

        :param config: The configuration values of the resolver
        :type config: dict
        """
        self.methodAllowed = config.get('methodAllowed', "")
        self.secret = config.get('secret', "")
        self.responseMapping = yaml.safe_load(config.get('responseMapping', "{}"))
        return self

    @classmethod
    def testconnection(cls, param):
        """
        This function lets you test if the parameters can be used to create a
        working resolver. Also, you can use it anytime you see if the API is
        running as expected.
        The implementation should try to make a request to the HTTP API and verify
        if user can be retrieved.
        In case of success it should return the raw http response.

        :param param: The parameters that should be saved as the resolver
        :type param: dict
        :return: returns True in case of success and a raw response
        :rtype: tuple
        """
        desc = ""
        success = False
        try:
            cls.loadConfig(cls, param)
            response = cls._getUser(cls, param.get('testToken'), test=True)
            desc = response
            success = True
        except Exception as e:
            success = False
            desc = str(e)
            log.error("error validating token with exception: {0!s}".format(e))
        return success, desc

    #
    #   Private methods
    #
    def _getUser(self, token, test=False):
        decode_key = self.secret
        if self.methodAllowed not in SYMMETRICAL_ALGORITHMS:
            decode_key = bytes(decode_key, 'utf-8')

        options = {}
        if test:
            options = {'verify_exp': test}
        jwt_token = jwt.decode(token, decode_key, algorithms=[self.methodAllowed], options=options)
        token = {key.lower(): value for key, value in jwt_token.items()}

        # Create mapped response with response mapping resolver input
        response = {}
        for pi_user_key, value in self.responseMapping.items():
            if value.startswith('{') and value.endswith('}'):
                response[pi_user_key] = get(token, value[1:-1].lower())
            else:
                response[pi_user_key] = value

        if not test:
            # Only cache token data when not testing
            self.token_data = response
        return response
