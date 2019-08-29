# -*- coding: utf-8 -*-
#
#  2019-09-26 Friedrich Weber <friedrich.weber@netknights.it>
#             Move UI helper methods to a separate module
#
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
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
This module contains helper functions for building the UI correctly depending
on the user rights and defined policies.

It is tested in test_api_lib_ui.py
"""

import logging
from six import string_types

from privacyidea.lib.error import PolicyError
from privacyidea.lib.token import get_dynamic_policy_definitions
from privacyidea.lib.auth import ROLE
from privacyidea.lib.config import get_token_classes
from privacyidea.lib.policy import SCOPE, get_static_policy_definitions, Match
from privacyidea.lib.user import User


log = logging.getLogger(__name__)


def get_enroll_tokentypes(g):
    """
    Return a dictionary of the allowed tokentypes for the logged in user.
    This used for the token enrollment UI.

    It looks like this:

       {"hotp": "HOTP: event based One Time Passwords",
        "totp": "TOTP: time based One Time Passwords",
        "spass": "SPass: Simple Pass token. Static passwords",
        "motp": "mOTP: classical mobile One Time Passwords",
        "sshkey": "SSH Public Key: The public SSH key",
        "yubikey": "Yubikey AES mode: One Time Passwords with Yubikey",
        "remote": "Remote Token: Forward authentication request to another server",
        "yubico": "Yubikey Cloud mode: Forward authentication request to YubiCloud",
        "radius": "RADIUS: Forward authentication request to a RADIUS server",
        "email": "EMail: Send a One Time Passwort to the users email address",
        "sms": "SMS: Send a One Time Password to the users mobile phone",
        "certificate": "Certificate: Enroll an x509 Certificate Token."}

    :param g: Context object, see ``Match`` documentation
    :return: list of token types, the user may enroll
    """
    enroll_types = {}
    role = g.logged_in_user["role"]
    if role == ROLE.USER:
        user_object = User(g.logged_in_user["username"], g.logged_in_user["realm"])
    else:
        user_object = None
    # check, if we have a policy definition at all.
    pols = g.policy_object.list_policies(scope=role, active=True)
    tokenclasses = get_token_classes()
    for tokenclass in tokenclasses:
        # Check if the tokenclass is ui enrollable for "user" or "admin"
        if role in tokenclass.get_class_info("ui_enroll"):
            enroll_types[tokenclass.get_class_type()] = \
                tokenclass.get_class_info("description")
    if pols:
        # admin policies or user policies are set, so we need to
        # test, which tokens are allowed to be enrolled for this user
        filtered_enroll_types = {}
        for tokentype in enroll_types.keys():
            enroll_action = "enroll" + tokentype.upper()
            # determine, if there is a enrollment policy for this very type
            if role == ROLE.ADMIN:
                policy_match = Match.admin(g, action=enroll_action, realm=None)
            else:
                policy_match = Match.user(g, scope=SCOPE.USER, action=enroll_action, user_object=user_object)
            if policy_match.any():
                # If there is no policy allowing the enrollment of this
                # tokentype, it is deleted.
                filtered_enroll_types[tokentype] = enroll_types[tokentype]
        enroll_types = filtered_enroll_types
    return enroll_types


def get_rights(g):
    """
    Get the rights derived from the policies for the given realm and user.
    Works for admins and normal users.
    It fetches all policies for this user and compiles a maximum list of
    allowed rights, that can be used to hide certain UI elements.

    :param g: Context object, see ``Match`` documentation
    :return: A list of actions
    """
    role = g.logged_in_user["role"]
    if role == ROLE.ADMIN:
        policy_match = Match.admin(g, action=None, realm=None)
        scope = SCOPE.ADMIN
    elif role == ROLE.USER:
        user_object = User(g.logged_in_user["username"], g.logged_in_user["realm"])
        scope = SCOPE.USER
        policy_match = Match.user(g, scope=SCOPE.USER, action=None, user_object=user_object)
    else:
        raise PolicyError(u"Unknown role: {}".format(role))
    rights = set()
    pols = policy_match.policies(write_to_audit_log=False)
    for pol in pols:
        for action, action_value in pol.get("action").items():
            if action_value:
                rights.add(action)
                # if the action has an actual non-boolean value, return it
                if isinstance(action_value, string_types):
                    rights.add(u"{}={}".format(action, action_value))
    # check if we have policies at all:
    policies_at_all = g.policy_object.list_policies(scope=scope, active=True)
    if not policies_at_all:
        # We do not have any policies in this scope, so we return all
        # possible actions in this scope.
        log.debug("No policies defined, so we set all rights.")
        rights = get_static_policy_definitions(scope)
        rights.update(get_dynamic_policy_definitions(scope))
    rights = list(rights)
    log.debug("returning the admin rights: {0!s}".format(rights))
    return rights


def get_main_menus(g):
    """
    Get the list of allowed main menus derived from the policies for the
    given user - admin or normal user.
    It fetches all policies for this user and compiles a list of allowed
    menus to display or hide in the UI.

    :param g: Context object, see ``Match`` documentation
    :return: A list of MENUs to be displayed
    """
    role = g.logged_in_user["role"]
    user_rights = get_rights(g)
    main_menus = []
    static_rights = get_static_policy_definitions(role)
    enroll_rights = get_dynamic_policy_definitions(role)
    static_rights.update(enroll_rights)
    for r in user_rights:
        menus = static_rights.get(r, {}).get("mainmenu", [])
        main_menus.extend(menus)

    main_menus = list(set(main_menus))
    return main_menus
