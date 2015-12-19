# -*- coding: utf-8 -*-
#
# 2015-06-05   Cornelius Kölbel <cornelius@privacyidea.org>
#              Add interface to edit and add users
# Dec 01, 2014 Cornelius Kölbel <cornelius@privacyidea.org>
#               Migration to flask
#               Adapt methods for tests
#               Improve comments
#               100% test code coverage
# 2014-10-03 fix getUsername function
#            Cornelius Kölbel <cornelius@privcyidea.org>
#  May, 08 2014 Cornelius Kölbel
#  http://www.privacyidea.org
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
This module implements the communication interface
for resolving user info to the user base

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
    id = "baseid"
    updateable = False

    def close(self):
        """
        Hook to close down the resolver after one request
        """
        return

    @staticmethod
    def getResolverClassType():
        """
        provide the resolver type for registration
        """
        return 'UserIdResolver'

    @staticmethod
    def getResolverType():
        """
        getResolverType - return the type of the resolver

        :return: returns the string 'ldapresolver'
        :rtype:  string
        """
        return 'UserIdResolver'

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
        descriptor['clazz'] = "useridresolver.UserIdResolver"
        descriptor['config'] = {}
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

        It needs to return an emptry string, if the user does
        not exist.

        :param loginName: The login name of the user
        :type loginName: sting
        :return: The ID of the user
        :rtype: string or int
        """
        return "dummy_user_id"

    def getUsername(self, userid):
        """
        Returns the username/loginname for a given userid
        :param userid: The userid in this resolver
        :type userid: string
        :return: username
        :rtype: string
        """
        return "dummy_user_name"

    def getUserInfo(self, userid):
        """
        This function returns all user information for a given user object
        identified by UserID.
        :param userid: ID of the user in the resolver
        :type userid: int or string
        :return:  dictionary, if no object is found, the dictionary is empty
        :rtype: dict
        """
        return {}

    def getUserList(self, searchDict=None):
        """
        This function finds the user objects,
        that have the term 'value' in the user object field 'key'

        :param searchDict:  dict with key values of user attributes -
                    the key may be something like 'loginname' or 'email'
                    the value is a regular expression.
        :type searchDict: dict

        :return: list of dictionaries (each dictionary contains a
                 user object) or an empty string if no object is found.
        :rtype: list of dicts
        """
        searchDict = searchDict or {}
        return [{}]

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
        Add a new user in the useridresolver.
        This is only possible, if the UserIdResolver supports this and if
        we have write access to the user store.

        :param username: The login name of the user
        :type username: basestring
        :param attributes: Attributes according to the attribute mapping
        :return: The new UID of the user. The UserIdResolver needs to
        determine the way how to create the UID.
        """
        attributes = attributes or {}
        return None

    def delete_user(self, uid):
        """
        Delete a user from the useridresolver.
        The user is referenced by the user id.
        :param uid: The uid of the user object, that should be deleted.
        :type uid: basestring
        :return: Returns True in case of success
        :rtype: bool
        """
        return None

    def update_user(self, uid, attributes=None):
        """
        Update an existing user.
        This function is also used to update the password. Since the
        attribute mapping know, which field contains the password,
        this function can also take care for password changing.

        Attributes that are not contained in the dict attributes are not
        modified.

        :param uid: The uid of the user object in the resolver.
        :type uid: basestring
        :param attributes: Attributes to be updated.
        :type attributes: dict
        :return: True in case of success
        """
        attributes = attributes or {}
        return None

    @staticmethod
    def testconnection(param):
        """
        This function lets you test if the parameters can be used to create a
        working resolver.
        The implementation should try to connect to the user store and verify
        if users can be retrieved.
        In case of success it should return a text like
        "Resolver config seems OK. 123 Users found."

        param param: The parameters that should be saved as the resolver
        type param: dict
        return: returns True in case of success and a descriptive text
        rtype: tuple
        """
        success = False
        desc = "Not implemented"
        return success, desc
