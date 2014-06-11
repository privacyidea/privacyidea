# -*- coding: utf-8 -*-
#
#  product:  privacyIDEA is a fork of LinOTP
#  module:   resolver library
#    
#  May, 08 2014 Cornelius Kölbel
#  http://www.privacyidea.org
#            
#  
#  product:  LinOTP2
#  module:   useridresolver
#  tool:     UserIdResolver
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
"""
  Description:  This module implements the communication interface
                for resolvin user info to the user base

  Dependencies: -

UserIdResolver Interface class.

Defines the rough interface for a UserId Resolver
== a UserId Resolver is required to resolve the
   Login Name to an unique User Identifier

- for /etc/passwd this will be the uid
- for ldap this might be the DN
- for SQL the unique index ( what's the right name here (tm))

"""


class UserIdResolver(object):

    fields = {"username": 1, "userid": 1,
              "description": 0,
              "phone": 0, "mobile": 0, "email": 0,
              "givenname": 0, "surname": 0, "gender": 0
              }
    name = ""
    id = ""

    def __init(self):
        """
        init - usual bootstrap hook
        """
        self.name = "UserIdResolver"

    def close(self):
        """
        Hook to close down the resolver after one request
        """
        return

    @classmethod
    def getResolverClassType(cls):
        """
        provide the resolver type for registration
        """
        return 'UserIdResolver'

    def getResolverType(self):
        '''
        getResolverType - return the type of the resolver

        :return: returns the string 'ldapresolver'
        :rtype:  string
        '''
        return 'UserIdResolver'

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
        descriptor['clazz'] = "useridresolver.UserIdResolver"
        descriptor['config'] = {}
        return {typ: descriptor}

    def getResolverDescriptor(self):
        '''
        return the descriptor of the resolver, which is
        - the class name and
        - the config description

        :return: resolver description dict
        :rtype:  dict
        '''
        return UserIdResolver.getResolverClassDescriptor()

    def getUserId(self, loginName):
        """ getUserId(LoginName)
          - returns the identifier string
          - empty string if not exist

        """
        return self.id

    def getUsername(self, userid):
        """
        getUsername(LoginId)
          - returns the loginname string
          - empty string if not exist

        """

        return self.name

    def getUserInfo(self, userid):
        """
        getUserInfo(UserID)
            This function returns all user information for a given user object
            identified by UserID.
        :return:  dictionary, if no object is found, the dictionary is empty
        """
        return ""

    def getUserList(self, serachDict):
        """
        This function finds the user objects,
        that have the term 'value' in the user object field 'key'

        :param searchDict:  dict with key values of user attributes -
                    the key may be something like 'loginname' or 'email'
                    the value is a regular expression.

        :return: list of dictionaries (each dictionary contains a
                 user object) or an empty string if no object is found.
        """
        return [{}]

    def getResolverId(self):
        """
        get resolver specific information
        :return: the resolver identifier string - empty string if not exist
        """
        return self.name

    def loadConfig(self, config, conf):
        return self

    def checkPass(self, uid, password):
        '''
        This function checks the password for a given uid.
        - returns true in case of success
        -         false if password does not match
        '''
        return False


def getResolverClass(packageName, className):
    """
    helper method to load the UserIdResolver class from a given
    package in literal. Checks, if the getUserId method exists,
    if not an error is thrown

    example:

        getResolverClass("PasswdIdResolver", "IdResolver")()

    :param packageName: the name package + module
    :param className: the name of the class, which should be loaded

    :return: the class object
    """
    mod = __import__(packageName, globals(), locals(), [className])
    klass = getattr(mod, className)
    ret = ""
    attribute = ""
    try:
        attrs = ["getUserId", "getUsername", "getUserInfo", "getUserList",
                 "checkPass", "loadConfig",
                 "getResolverId", "getResolverType", "getResolverDescriptor"
                ]

        for att in attrs:
            attribute = att
            getattr(klass, att)
        ret = klass
    except:
        raise NameError("IdResolver AttributeError: " + packageName + "." + \
              className + " instance has no attribute '" + attribute + "'")

    return ret
