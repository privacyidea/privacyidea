# -*- coding: utf-8 -*-
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  Jul 07, 2014 add check_machine_policy, Cornelius Kölbel

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
"""
Base function to handle the policy entries in the database.
This module only depends on the db/models.py

The functions of this module are tested in tests/test_lib_policy.py

A policy has the attributes

 * name
 * scope
 * action
 * realm
 * resolver
 * user
 * client
 * active

``name`` is the unique identifier of a policy. ``scope`` is the area,
where this policy is ment for. This can be values like admin, selfservice,
authentication...
``scope`` takes only one value.

``active`` is bool and indicates, whether a policy is active or not.

``action``, ``realm``, ``resolver``, ``user`` and ``client`` can take a comma
seperated list of values.

realm and resolver
------------------
If these are empty '*', this policy matches each requested realm.

user
----
If the user is empty or '*', this policy matches each user.
You can exclude users from matching this policy, by prepending a '-' or a '!'.
``*, -admin`` will match for all users except the admin.

client
------
The client is identified by its IP address. A policy can contain a list of
IP addresses or subnets.
You can exclude clients from subnets by prepending the client with a '-' or
a '!'.
``172.16.0.0/24, -172.16.0.17`` will match each client in the subnet except
the 172.16.0.17.
"""

from .log import log_with
from .error import privacyIDEAError
from configobj import ConfigObj

from netaddr import IPAddress
from netaddr import IPNetwork
from gettext import gettext as _

import logging
from ..models import (Policy,
                       db)
log = logging.getLogger(__name__)


optional = True
required = False


# This dictionary maps the token_types to actions in the scope gettoken,
# that define the maximum allowed otp valies in case of getotp/getmultiotp
MAP_TYPE_GETOTP_ACTION = {"dpw": "max_count_dpw",
                          "hmac": "max_count_hotp",
                          "totp": "max_count_totp"}


class PolicyException(privacyIDEAError):
    def __init__(self, description="unspecified error!", id=410):
        privacyIDEAError.__init__(self, description=description, id=id)


class AuthorizeException(privacyIDEAError):
    def __init__(self, description="unspecified error!", id=510):
        privacyIDEAError.__init__(self, description=description, id=id)


# --------------------------------------------------------------------------
#
#  NEW STUFF
#
#

class PolicyClass(object):
    # TODO: Migration
    pass


@log_with(log)
def set_policy(name=None, scope=None, action=None, realm=None, resolver=None,
               user=None, time=None, client=None, active=True):
    """
    Function to set a policy.
    If the policy with this name already exists, it updates the policy.
    It expects a dict of with the following keys:
    :param name: The name of the policy
    :param scope: The scope of the policy. Something like "admin", "system",
    "authentication"
    :param action: A scope specific action or a comma seperated list of actions
    :type active: basestring
    :param realm: A realm, for which this policy is valid
    :param resolver: A resolver, for which this policy is valid
    :param user: A username or a list of usernames
    :param time: N/A
    :param client: A client IP with optionally a subnet like 172.16.0.0/16
    :param active: If the policy is active or not
    :type active: bool
    :return: The database ID od the the policy
    :rtype: int
    """
    p = Policy(name, action=action, scope=scope, realm=realm,
               user=user, time=time, client=client, active=active,
               resolver=resolver).save()
    return p


@log_with(log)
def delete_policy(name):
    """
    Function to delete one named policy

    :param name: the name of the policy to be deleted
    :return: the count of the deleted policies.
    :rtype: int
    """
    p = Policy.query.filter_by(name=name)
    res = p.delete()
    db.session.commit()
    return res


def _filter_client(policies, client):
    """
    This function defines, how a given client is tried to match the client
    definition in the policy.

    The client definition in the policy may ba a comma seperated list.
    It may start with a "-" or a "!" to exclude the client
    from a subnet.

    Thus a client 10.0.0.2 matches a policy "10.0.0.0/8, -10.0.0.1" but
    the client 10.0.0.1 does not match the policy "10.0.0.0/8, -10.0.0.1".

    An empty client definition in the policy matches all clients.

    :param policies: dictionary of policy definitions
    :type policies: dict
    :param client: client IP
    :type client: basestring
    :return: new policy dictionary, which only contains the client
    """
    ret_policies = {}
    for polkey, pol in policies.iteritems():
        pol_client = pol.get("client", "")
        if pol_client == "":
            # No client in the policy, the policy matches
            ret_policies[pol.get("name")] = pol
        else:
            pol_clients = [c.strip() for c in pol.get("client").split(
                ",")]
            # There are clients in the policy, so we need to check,
            # if the client matches these client definitions
            client_found = False
            client_excluded = False
            for pc in pol_clients:
                if pc:
                    if pc[0] in ['-', '!']:
                        if IPAddress(client) in IPNetwork(pc[1:]):
                            log.debug("the client %s is excluded by %s in "
                                      "policy %s" % (client, pc, pol))
                            client_excluded = True
                    elif IPAddress(client) in IPNetwork(pc):
                        client_found = True
            if client_found and not client_excluded:
                # The client was contained in the defined subnets and was
                #  not excluded
                ret_policies[polkey] = pol
    return ret_policies


def _filter_realm(policies, realm):
    """
    This function defines, how a given realm is tried to match the realm
    definition in the policy.

    An empty policy realm or an '*' as policy realm matches all realms.

    :param policies:
    :param realm:
    :return:
    """
    ret_policies = {}
    for polkey, pol in policies.iteritems():
        pol_realm = pol.get("realm", "")
        if pol_realm == "" or pol_realm == "*":
            ret_policies[polkey] = pol
        else:
            if pol.get("realm") == realm:
                ret_policies[polkey] = pol
    return ret_policies


def _filter_resolver(policies, resolver):
    """
    This function defines, how a given resolver is tried to match the resolver
    definition in the policy.

    An empty policy resolver or an '*' as policy
    resolver matches
    all resolvers.

    :param policies:
    :param resolver:
    :return:
    """
    ret_policies = {}
    for polkey, pol in policies.iteritems():
        pol_resolver = pol.get("resolver", "")
        if pol_resolver == "" or pol_resolver == "*":
            ret_policies[polkey] = pol
        else:
            if pol.get("resolver") == resolver:
                ret_policies[polkey] = pol
    return ret_policies


def _filter_user(policies, user):
    """
    This function defines, how a given username is tried to match the user
    definition in the policy.

    An empty policy user or an '*' as policy user matches all users.

    The users can be a comma seperated list.
    Users may be excluded from the policy by adding "-" or "!" infront of the
    username. Thus you could define a policy, that is valid for all users,
    except the "admin" and "superroor":

       user = "*, -admin, -superroot"

    :param policies: The policies, that are filtered for the given user
    :type policies: dict
    :param user: the user, who should be found in the policies
    :type user: basestring
    :return: the filtered policies, stripped by those policies, that are not
    valid for the given user
    :rtype: dict
    """
    ret_policies = {}
    for polkey, pol in policies.iteritems():
        pol_user = pol.get("user", "")
        if pol_user == "" or pol_user == "*":
            ret_policies[polkey] = pol
        else:
            pol_users = [c.strip() for c in pol.get("user").split(",")]
            user_found = False
            user_excluded = False
            for pu in pol_users:
                if pu:
                    if pu[0] in ['-', '!']:
                        if user == pu[1:]:
                            log.debug("the user %s is excluded by %s in "
                                      "policy %s" % (user, pu, pol))
                            user_excluded = True
                    elif user == pu or "*" == pu:
                        user_found = True
            if user_found and not user_excluded:
                # The user was contained in the user list and was not excluded
                ret_policies[polkey] = pol
    return ret_policies


def _filter_action(policies, action):
    """
    This function defines, how a given action is tried to match the action
    definition in the policy.

    Usually an action should not be empty.
    So if we see an empty action, we ignore this policy!

    action is a comma separated list.
    An action can either be a single word or a word, followed by '='.

    An action like 'enroll' would allow enrollment (boolean).
    An action like 'url=' would define some value for 'url' (string).

    This method just checks, if 'enroll' or 'url' would be contained in a
    policy and does not check for the values after '='.

    Again, you can exclude action like
    ``*, -setpin``
    Allowing all actions in the selfservice portal except setting the pin.

    A policy action '*' matches all (boolean) actions.

    :param policies: The policies, that are filtered for the given user
    :type policies: dict
    :param action: the action, that should be contained in the policy
    :type action: basestring
    :return: the filtered policies, stripped by those policies, that are do
    not contain the requested action.
    :rtype: dict
    """
    ret_policies = {}
    for polkey, pol in policies.iteritems():
        pol_action = pol.get("action", "")
        pol_actions = [c.strip() for c in pol_action.split(",")]
        action_found = False
        action_excluded = False
        for pa in pol_actions:
            if pa:
                # Just for matching purpose split the values from the action
                pa = pa.split("=")[0]
                if pa[0] in ['-', '!']:
                    if action == pa[1:]:
                        log.debug("the action %s is excluded by %s in "
                                  "policy %s" % (action, pa, pol))
                        action_excluded = True
                elif action == pa or "*" == pa:
                    action_found = True
        if action_found and not action_excluded:
            # The action was contained in the action list and was not
            # excluded
            ret_policies[polkey] = pol
    return ret_policies



@log_with(log)
def get_policies(name=None, scope=None, realm=None, active=None,
                 resolver=None, user=None, client=None, action=None):
    """
    read the complete policies from the database and return
    them in a dictionary.
    The parameters apply a filter on the database view.

    The client
    
    :param name: THe name of the policy
    :param scope: The scope of the policy
    :param realm: Only policies with the given realm.
    :param active: Only active (True) or inactive (False) policies. If None,
    all policies are returned.
    :param action: a comma seperated list of actions
    :param resolver: The resolver of a policy
    :param user: The user of a policy
    :param client: The requesting client, ip address
    :type client: basestring
    :return: A dictionary with all policies
    :rtype: dictionary
    """
    policies = {}
    sql_query = Policy.query
    if name is not None:
        sql_query = sql_query.filter(Policy.name == name)
    if scope is not None:
        sql_query = sql_query.filter(Policy.scope == scope)
    if active is not None:
        sql_query = sql_query.filter(Policy.active == active)

    # Fetch the data from the database
    for pol in sql_query.all():
        policies[pol.name] = pol.get()

    # Now we do some more sophisticated filtering
    if resolver is not None:
        policies = _filter_resolver(policies, resolver)
    if realm is not None:
        policies = _filter_realm(policies, realm)
    if user is not None:
        policies = _filter_user(policies, user)
    if client is not None:
        policies = _filter_client(policies, client)
    if action is not None:
        policies = _filter_action(policies, action)

    return policies


@log_with(log)
def export_policies(policies):
    """
    This function takes a policy dictionary and creates an export file from it
    
    :param policies: a policy definition
    :type policies: dictionary
    :return: the contents of the file
    :rtype: string
    """
    file_contents = ""
    if len(policies) > 0:
        for policy in policies:
            file_contents += "[%s]\n" % policy
            for key in policies.get(policy):
                file_contents += "%s = %s\n" % (key,
                                                policies.get(policy).get(key))
            file_contents += "\n"

    return file_contents


@log_with(log)
def import_policies(file_contents):
    """
    This function imports policies from a file.
    The file has a config_object format, i.e. the text file has a header
        [<policy_name>]
        key = value
    and key value pairs.

    :param file_contents: The contents of the file
    :type file_contents: basestring
    :return: number of imported policies
    :rtype: int
    """
    policies = ConfigObj(file_contents.split('\n'), encoding="UTF-8")
    res = 0
    for policy_name in policies.keys():
        ret = set_policy(name=policy_name,
                         action=policies[policy_name].get("action"),
                         scope=policies[policy_name].get("scope"),
                         realm=policies[policy_name].get("realm"),
                         user=policies[policy_name].get("user"),
                         resolver=policies[policy_name].get("resolver"),
                         client=policies[policy_name].get("client"),
                         time=policies[policy_name].get("time")
                         )
        if ret > 0:
            log.debug("import policy %s: %s" % (policy_name, ret))
            res += 1
    return res


@log_with(log)
def get_static_policy_definitions(scope=None):
    """
    These are the static hard coded policy definitions.
    They can be enhanced by token based policy definitions, that can be found
    int lib.token.get_dynamic_policy_definitions.

    :param scope: Optional the scope of the policies
    :type scope: basestring
    :return: allowed scopes with allowed actions, the type of action and a
    description.
    :rtype: dict
    """

    pol = {
        'admin': {
            'enable': {'type': 'bool',
                       'desc' : _('Admin is allowed to enable tokens.')},
            'disable': {'type': 'bool',
                        'desc' : _('Admin is allowed to disable tokens.')},
            'set': {'type': 'bool',
                    'desc' : _('Admin is allowed to set token properties.')},
            'setOTPPIN': {'type': 'bool',
                          'desc' : _('Admin is allowed to set the OTP PIN of tokens.')},
            'setMOTPPIN': {'type': 'bool',
                           'desc' : _('Admin is allowed to set the mOTP PIN of motp tokens.')},
            'setSCPIN': {'type': 'bool',
                         'desc' : _('Admin is allowed to set the smartcard PIN of tokens.')},
            'resync': {'type': 'bool',
                       'desc' : _('Admin is allowed to resync tokens.')},
            'reset': {'type': 'bool',
                      'desc' : _('Admin is allowed to reset the Failcounter of a token.')},
            'assign': {'type': 'bool',
                       'desc' : _('Admin is allowed to assign a token to a user.')},
            'unassign': {'type': 'bool',
                         'desc' : _('Admin is allowed to remove the token from a user, '
                         'i.e. unassign a token.')},
            'import': {'type': 'bool',
                       'desc' : _('Admin is allowed to import token files.')},
            'remove': {'type': 'bool',
                       'desc' : _('Admin is allowed to remove tokens from the database.')},
            'userlist': {'type': 'bool',
                         'desc' : _('Admin is allowed to view the list of the users.')},
            'checkstatus': {'type': 'bool',
                            'desc' : _('Admin is allowed to check the status of a challenge'
                                       ' resonse token.')},
            'manageToken': {'type': 'bool',
                            'desc' : _('Admin is allowed to manage the realms of a token.')},
            'getserial': {'type': 'bool',
                          'desc' : _('Admin is allowed to retrieve a serial for a given OTP value.')},
            'checkserial': {'type': 'bool',
                            'desc': _('Admin is allowed to check if a serial is unique')},
            'copytokenpin': {'type': 'bool',
                             'desc' : _('Admin is allowed to copy the PIN of one token '
                                        'to another token.')},
            'copytokenuser': {'type': 'bool',
                              'desc' : _('Admin is allowed to copy the assigned user to another'
                                         ' token, i.e. assign a user ot another token.')},
            'losttoken': {'type': 'bool',
                          'desc' : _('Admin is allowed to trigger the lost token workflow.')},
            'getotp': {
                'type': 'bool',
                'desc': _('Allow the administrator to retrieve OTP values for tokens.')}
        },
        'gettoken': {
            'max_count_dpw': {'type': 'int',
                              'desc' : _('When OTP values are retrieved for a DPW token, '
                                         'this is the maximum number of retrievable OTP values.')},
            'max_count_hotp': {'type': 'int',
                               'desc' : _('When OTP values are retrieved for a HOTP token, '
                                          'this is the maximum number of retrievable OTP values.')},
            'max_count_totp': {'type': 'int',
                               'desc' : _('When OTP values are retrieved for a TOTP token, '
                                          'this is the maximum number of retrievable OTP values.')},
        },
        'selfservice': {
            'assign': {
                'type': 'bool',
                'desc': _("The user is allowed to assign an existing token"
                          " that is not yet assigned"
                          " using the token serial number.")},
            'disable': {'type': 'bool',
                        'desc': _('The user is allowed to disable his own tokens.')},
            'enable': {'type': 'bool',
                       'desc': _("The user is allowed to enable his own tokens.")},
            'delete': {'type': 'bool',
                       "desc": _("The user is allowed to delete his own tokens.")},
            'unassign': {'type': 'bool',
                         "desc": _("The user is allowed to unassign his own tokens.")},
            'resync': {'type': 'bool',
                       "desc": _("The user is allowed to resyncronize his tokens.")},
            'reset': {
                'type': 'bool',
                'desc': _('The user is allowed to reset the failcounter of his tokens.')},
            'setOTPPIN': {'type': 'bool',
                          "desc": _("The user is allowed to set the OTP PIN of his tokens.")},
            'setMOTPPIN': {'type': 'bool',
                           "desc": _("The user is allowed to set the mOTP PIN of his mOTP tokens.")},
            'getotp': {'type': 'bool',
                       "desc": _("The user is allowed to retrieve OTP values for his own tokens.")},
            'otp_pin_maxlength': {'type': 'int',
                                  'value': range(0, 100),
                                  "desc": _("Set the maximum allowed length of the OTP PIN.")},
            'otp_pin_minlength': {'type': 'int',
                                  'value': range(0, 100),
                                  "desc" : _("Set the minimum required lenght of the OTP PIN.")},
            'otp_pin_contents': {'type': 'str',
                                 "desc" : _("Specifiy the required contents of the OTP PIN. (c)haracters, (n)umeric, (s)pecial, (o)thers. [+/-]!")},
            'activateQR': {'type': 'bool',
                           "desc": _("The user is allowed to enroll a QR token.")},
            'webprovisionOATH': {'type': 'bool',
                                 "desc": _("The user is allowed to enroll an OATH token.")},
            'webprovisionGOOGLE': {'type': 'bool',
                                   "desc": _("The user is allowed to enroll a Google Authenticator event based token.")},
            'webprovisionGOOGLEtime': {'type': 'bool',
                                       "desc": _("The user is allowed to enroll a Google Authenticator time based token.")},
            'max_count_dpw': {'type': 'int',
                              "desc": _("This is the maximum number of OTP values, the user is allowed to retrieve for a DPW token.")},
            'max_count_hotp': {'type': 'int',
                               "desc": _("This is the maximum number of OTP values, the user is allowed to retrieve for a HOTP token.")},
            'max_count_totp': {'type': 'int',
                               "desc": _("This is the maximum number of OTP values, the user is allowed to retrieve for a TOTP token.")},
            'history': {
                'type': 'bool',
                'desc': _('Allow the user to view his own token history.')},
            'getserial': {
                'type': 'bool',
                'desc': _('Allow the user to search an unassigned token by OTP value.')},
            'auth' : {
                'type' : 'str',
                'desc' : _('If set to "otp": Users in this realm need to login with OTP to the selfservice.')}
            },
        'system': {
            'read': {'type': 'bool',
                     "desc" : _("Admin is allowed to read the system configuration.")},
            'write': {'type': 'bool',
                      "desc" : _("Admin is allowed to write and modify the system configuration.")},
            },
        'enrollment': {
            'tokencount': {
                'type': 'int',
                'desc': _('Limit the number of allowed tokens in a realm.')},
            'maxtoken': {
                'type': 'int',
                'desc': _('Limit the number of tokens a user in this realm may '
                        'have assigned.')},
            'otp_pin_random': {
                'type': 'int',
                'value': range(0, 100),
                "desc": _("Set a random OTP PIN with this lenght for a token.")},
            'otp_pin_encrypt': {
                'type': 'int',
                'value': [0, 1],
                "desc": _("If set to 1, the OTP PIN is encrypted. The normal behaviour is the PIN is hashed.")},
            'tokenlabel': {
                'type': 'str',
                'desc': _("Set label for a new enrolled Google Authenticator. "
                          "Possible tags are &lt;u&gt; (user), &lt;r&gt; (realm), &lt;s&gt; (serial).")},
            'autoassignment': {
                'type': 'int',
                'value': [6, 8],
                'desc': _("Users can assign a token just by using the "
                          "unassigned token to authenticate. This is the lenght"
                          " of the OTP value - either 6, 8, 32, 48.")},
            'ignore_autoassignment_pin': {
                'type': 'bool',
                'desc' : _("Do not set password from auto assignment as token pin.")},
            'lostTokenPWLen': {
                'type': 'int',
                'desc': _('The length of the password in case of '
                        'temporary token (lost token).')},
            'lostTokenPWContents': {
                'type': 'str',
                'desc': _('The contents of the temporary password, '
                        'described by the characters C, c, n, s.')},
            'lostTokenValid': {
                'type': 'int',
                'desc': _('The length of the validity for the temporary '
                        'token (in days).')},
            },
        'authentication': {
            'smstext': {
                'type': 'str',
                'desc': _('The text that will be send via SMS for an SMS token. '
                        'Use &lt;otp&gt; and &lt;serial&gt; as parameters.')},
            'otppin': {
                'type': 'int',
                'value': [0, 1, 2],
                'desc': _('Either use the Token PIN (0), use the Userstore '
                        'Password (1) or use no fixed password '
                        'component (2).')},
            'autosms': {
                'type': 'bool',
                'desc': _('If set, a new SMS OTP will be sent after '
                        'successful authentication with one SMS OTP.')},
            'passthru': {
                'type': 'bool',
                'desc': _('If set, the user in this realm will be authenticated '
                        'against the UserIdResolver, if the user has no '
                        'tokens assigned.')
                },
            'passOnNoToken': {
                'type': 'bool',
                'desc': _('If the user has no token, the authentication request '
                        'for this user will always be true.')
                },
            'qrtanurl': {
                'type': 'str',
                'desc': _('The URL for the half automatic mode that should be '
                        'used in a QR Token')
                },
            'challenge_response': {
                'type': 'str',
                'desc': _('A list of tokentypes for which challenge response '
                        'should be used.')
                }
            },
        'authorization': {
            'authorize': {
                'type': 'bool',
                'desc': _('The user/realm will be authorized to login '
                        'to the clients IPs.')},
            'tokentype': {
                'type': 'str',
                'desc': _('The user will only be authenticated with this '
                        'very tokentype.')},
            'serial': {
                'type': 'str',
                'desc': _('The user will only be authenticated if the serial '
                        'number of the token matches this regexp.')},
            'setrealm': {
                'type': 'str',
                'desc': _('The Realm of the user is set to this very realm. '
                        'This is important if the user is not contained in '
                        'the default realm and can not pass his realm.')},
            'detail_on_success': {
                'type': 'bool',
                'desc': _('In case of successful authentication additional '
                        'detail information will be returned.')},
            'detail_on_fail': {
                'type': 'bool',
                'desc': _('In case of failed authentication additional '
                        'detail information will be returned.')}
            },
        'audit': {
            'view': {
                'type': 'bool',
                'desc' : _("Admin is allowed to view the audit log.")}
        },
        'ocra': {
            'request': {
                'type': 'bool',
                'desc': _('Allow to do a ocra/request.')},
            'status': {
                'type': 'bool',
                'desc': _('Allow to check the transaction status.')},
            'activationcode': {
                'type': 'bool',
                'desc': _('Allow to do an ocra/getActivationCode.')},
            'calcOTP': {
                'type': 'bool',
                'desc': _('Allow to do an ocra/calculateOtp.')}
        },
        'machine': {
                    'create': {'type': 'bool',
                               'desc': _("Create a new client "
                                         "machine definition")
                               },
                    'delete': {'type': 'bool',
                               'desc': _("delete a client machine defintion")},
                    'show': {'type': 'bool',
                             'desc': _("list the client machine definitions")},
                    'addtoken': {'type': 'bool',
                                 'desc': _("add a token to a client machine")},
                    'deltoken': {'type': 'bool',
                                 'desc': _("delete a token from "
                                           "a client machine")},
                    'showtoken': {'type': 'bool',
                                  'desc': _("list the tokens and "
                                            "client machines")},
                    'gettokenapps': {'type': 'bool',
                                  'desc': _("get the authentication items "
                                            "for a client machine")}
                    }
    }
    if scope:
        ret = pol.get(scope, {})
    else:
        ret = pol
    return ret
