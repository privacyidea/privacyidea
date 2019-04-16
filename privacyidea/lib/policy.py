# -*- coding: utf-8 -*-
#
#  2018-09-07 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add App Image URL
#  2018-01-15 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add tokeninfo field policy
#             Add add_resolver_in_result
#  2017-11-14 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add policy action for customization of menu and baseline
#  2017-01-22 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add policy action groups
#  2016-12-19 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add check_all_resolvers logic
#  2016-11-20 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add audit log age functionality
#  2016-08-30 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add registration body
#  2016-06-21 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Change PIN policies
#  2016-05-07 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add realm dropdown
#  2016-04-06 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add time dependency in policy
#  2016-02-22 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add RADIUS passthru policy
#  2016-02-05 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add tokenwizard in scope UI
#  2015-12-30 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add password reset policy
#  2015-12-28 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add registration policy
#  2015-12-16 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add tokenissuer policy
#  2015-11-29 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add getchallenges policy
#  2015-10-31 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add last_auth policy.
#  2015-10-30 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Display user details in token list
#  2015-10-26 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add default token type for enrollment
#  2015-10-14 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add auth_max_success and auth_max_fail actions to
#             scope authorization
#  2015-10-09 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add token_page_size and user_page_size policy
#  2015-09-06 Cornelius Kölbel <cornelius.koelbel@netkngihts.it>
#             Add challenge_response authentication policy
#  2015-06-30 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add the OTP PIN handling
#  2015-06-29 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add the mangle policy
#  2015-04-03 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add WebUI logout time.
#  2015-03-27 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add PIN policies in USER scope
#  2015-02-06 Cornelius Kölbel <cornelius@privacyidea.org>
#             Rewrite for flask migration.
#             Policies are not handled by decorators as
#             1. precondition for API calls
#             2. internal modifications of LIB-functions
#             3. postcondition for API calls
#
#  Jul 07, 2014 add check_machine_policy, Cornelius Kölbel
#  May 08, 2014 Cornelius Kölbel
#
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  privacyIDEA is a fork of LinOTP
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
where this policy is meant for. This can be values like admin, selfservice,
authentication...
``scope`` takes only one value.

``active`` is bool and indicates, whether a policy is active or not.

``action``, ``realm``, ``resolver``, ``user`` and ``client`` can take a comma
separated list of values.

realm and resolver
------------------
If these are empty '*', this policy matches each requested realm.

user
----
If the user is empty or '*', this policy matches each user.
You can exclude users from matching this policy, by prepending a '-' or a '!'.
``*, -admin`` will match for all users except the admin.

You can also use regular expressions to match the user like ``customer_.*``
to match any user, starting with *customer_*.

.. note:: Regular expression will only work for exact machtes.
   *user1234* will not match *user1* but only *user1...*

client
------
The client is identified by its IP address. A policy can contain a list of
IP addresses or subnets.
You can exclude clients from subnets by prepending the client with a '-' or
a '!'.
``172.16.0.0/24, -172.16.0.17`` will match each client in the subnet except
the 172.16.0.17.

time
----
You can specify a time in which the policy should be active.
Time formats are

<dow>-<dow>:<hh>:<mm>-<hh>:<mm>, ...
<dow>:<hh>:<mm>-<hh>:<mm>
<dow>:<hh>-<hh>

and any combination of it. "dow" being day of week Mon, Tue, Wed, Thu, Fri,
Sat, Sun.
"""

from .log import log_with
from configobj import ConfigObj

from operator import itemgetter
import six
import logging
from ..models import (Policy, Config, PRIVACYIDEA_TIMESTAMP, db,
                      save_config_timestamp)
from privacyidea.lib.config import (get_token_classes, get_token_types,
                                    Singleton)
from privacyidea.lib.framework import get_app_config_value
from privacyidea.lib.error import ParameterError, PolicyError, ResourceNotFoundError
from privacyidea.lib.realm import get_realms
from privacyidea.lib.resolver import get_resolver_list
from privacyidea.lib.smtpserver import get_smtpservers
from privacyidea.lib.radiusserver import get_radiusservers
from privacyidea.lib.utils import (check_time_in_range, reload_db,
                                   fetch_one_resource, is_true, check_ip_in_policy)
from privacyidea.lib.user import User
from privacyidea.lib import _
import datetime
import re
import ast
from six import with_metaclass, string_types

log = logging.getLogger(__name__)

optional = True
required = False


class SCOPE(object):
    __doc__ = """This is the list of the allowed scopes that can be used in
    policy definitions.
    """
    AUTHZ = "authorization"
    ADMIN = "admin"
    AUTH = "authentication"
    AUDIT = "audit"
    USER = "user"   # was selfservice
    ENROLL = "enrollment"
    GETTOKEN = "gettoken"
    WEBUI = "webui"
    REGISTER = "register"


class ACTION(object):
    __doc__ = """This is the list of usual actions."""
    ASSIGN = "assign"
    APPIMAGEURL = "appimageurl"
    AUDIT = "auditlog"
    AUDIT_AGE = "auditlog_age"
    AUDIT_DOWNLOAD = "auditlog_download"
    AUTHITEMS = "fetch_authentication_items"
    AUTHMAXSUCCESS = "auth_max_success"
    AUTHMAXFAIL = "auth_max_fail"
    AUTOASSIGN = "autoassignment"
    CACONNECTORREAD = "caconnectorread"
    CACONNECTORWRITE = "caconnectorwrite"
    CACONNECTORDELETE = "caconnectordelete"
    CHALLENGERESPONSE = "challenge_response"
    CHALLENGETEXT = "challenge_text"
    CHALLENGETEXT_HEADER = "challenge_text_header"
    CHALLENGETEXT_FOOTER = "challenge_text_footer"
    GETCHALLENGES = "getchallenges"
    COPYTOKENPIN = "copytokenpin"
    COPYTOKENUSER = "copytokenuser"
    DEFAULT_TOKENTYPE = "default_tokentype"
    DELETE = "delete"
    DISABLE = "disable"
    EMAILCONFIG = "smtpconfig"
    ENABLE = "enable"
    ENCRYPTPIN = "encrypt_pin"
    GETSERIAL = "getserial"
    GETRANDOM = "getrandom"
    IMPORT = "importtokens"
    LASTAUTH = "last_auth"
    LOGINMODE = "login_mode"
    LOGOUTTIME = "logout_time"
    LOSTTOKEN = 'losttoken'
    LOSTTOKENPWLEN = "losttoken_PW_length"
    LOSTTOKENPWCONTENTS = "losttoken_PW_contents"
    LOSTTOKENVALID = "losttoken_valid"
    MACHINERESOLVERWRITE = "mresolverwrite"
    MACHINERESOLVERDELETE = "mresolverdelete"
    MACHINELIST = "machinelist"
    MACHINETOKENS = "manage_machine_tokens"
    MANGLE = "mangle"
    MAXTOKENREALM = "max_token_per_realm"
    MAXTOKENUSER = "max_token_per_user"
    NODETAILSUCCESS = "no_detail_on_success"
    ADDUSERINRESPONSE = "add_user_in_response"
    ADDRESOLVERINRESPONSE = "add_resolver_in_response"
    NODETAILFAIL = "no_detail_on_fail"
    OTPPIN = "otppin"
    OTPPINRANDOM = "otp_pin_random"
    OTPPINMAXLEN = 'otp_pin_maxlength'
    OTPPINMINLEN = 'otp_pin_minlength'
    OTPPINCONTENTS = 'otp_pin_contents'
    PASSNOTOKEN = "passOnNoToken"
    PASSNOUSER = "passOnNoUser"
    PASSTHRU = "passthru"
    PASSWORDRESET = "password_reset"
    PINHANDLING = "pinhandling"
    POLICYDELETE = "policydelete"
    POLICYWRITE = "policywrite"
    POLICYTEMPLATEURL = "policy_template_url"
    REALM = "realm"
    REMOTE_USER = "remote_user"
    REQUIREDEMAIL = "requiredemail"
    RESET = "reset"
    RESOLVERDELETE = "resolverdelete"
    RESOLVERWRITE = "resolverwrite"
    RESOLVER = "resolver"
    RESYNC = "resync"
    REVOKE = "revoke"
    SET = "set"
    SETPIN = "setpin"
    SETREALM = "setrealm"
    SERIAL = "serial"
    SYSTEMDELETE = "configdelete"
    SYSTEMWRITE = "configwrite"
    CONFIGDOCUMENTATION = "system_documentation"
    SETTOKENINFO = "settokeninfo"
    TOKENISSUER = "tokenissuer"
    TOKENLABEL = "tokenlabel"
    TOKENPAGESIZE = "token_page_size"
    TOKENREALMS = "tokenrealms"
    TOKENTYPE = "tokentype"
    TOKENINFO = "tokeninfo"
    TOKENWIZARD = "tokenwizard"
    TOKENWIZARD2ND = "tokenwizard_2nd_token"
    TRIGGERCHALLENGE = "triggerchallenge"
    UNASSIGN = "unassign"
    USERLIST = "userlist"
    USERPAGESIZE = "user_page_size"
    ADDUSER = "adduser"
    DELETEUSER = "deleteuser"
    UPDATEUSER = "updateuser"
    USERDETAILS = "user_details"
    APIKEY = "api_key_required"
    SETHSM = "set_hsm_password"
    SMTPSERVERWRITE = "smtpserver_write"
    RADIUSSERVERWRITE = "radiusserver_write"
    PRIVACYIDEASERVERWRITE = "privacyideaserver_write"
    REALMDROPDOWN = "realm_dropdown"
    EVENTHANDLINGWRITE = "eventhandling_write"
    PERIODICTASKWRITE = "periodictask_write"
    SMSGATEWAYWRITE = "smsgateway_write"
    CHANGE_PIN_FIRST_USE = "change_pin_on_first_use"
    CHANGE_PIN_EVERY = "change_pin_every"
    CLIENTTYPE = "clienttype"
    REGISTERBODY = "registration_body"
    RESETALLTOKENS = "reset_all_user_tokens"
    ENROLLPIN = "enrollpin"
    MANAGESUBSCRIPTION = "managesubscription"
    SEARCH_ON_ENTER = "search_on_enter"
    TIMEOUT_ACTION = "timeout_action"
    AUTH_CACHE = "auth_cache"
    HIDE_BUTTONS = "hide_buttons"
    HIDE_WELCOME = "hide_welcome_info"
    SHOW_SEED = "show_seed"
    CUSTOM_MENU = "custom_menu"
    CUSTOM_BASELINE = "custom_baseline"
    STATISTICSREAD = "statistics_read"
    STATISTICSDELETE = "statistics_delete"
    LOGIN_TEXT = "login_text"


class GROUP(object):
    __doc__ = """These are the allowed policy action groups. The policies
    will be grouped in the UI."""
    TOOLS = "tools"
    SYSTEM = "system"
    TOKEN = "token"
    ENROLLMENT = "enrollment"
    GENERAL = "general"
    MACHINE = "machine"
    USER = "user"
    PIN = "pin"


class MAIN_MENU(object):
    __doc__ = """These are the allowed top level menu items. These are used
    to toggle the visibility of the menu items depending on the rights of the
    user"""
    TOKENS = "tokens"
    USERS = "users"
    MACHINES = "machines"
    CONFIG = "config"
    AUDIT = "audit"
    COMPONENTS = "components"


class LOGINMODE(object):
    __doc__ = """This is the list of possible values for the login mode."""
    USERSTORE = "userstore"
    PRIVACYIDEA = "privacyIDEA"
    DISABLE = "disable"


class REMOTE_USER(object):
    __doc__ = """The list of possible values for the remote_user policy."""
    DISABLE = "disable"
    ACTIVE = "allowed"


class ACTIONVALUE(object):
    __doc__ = """This is a list of usual action values for e.g. policy
    action-values like otppin."""
    TOKENPIN = "tokenpin"
    USERSTORE = "userstore"
    DISABLE = "disable"
    NONE = "none"


class AUTOASSIGNVALUE(object):
    __doc__ = """This is the possible values for autoassign"""
    USERSTORE = "userstore"
    NONE = "any_pin"


class TIMEOUT_ACTION(object):
    __doc__ = """This is a list of actions values for idle users"""
    LOGOUT = "logout"
    LOCKSCREEN = 'lockscreen'


class PolicyClass(with_metaclass(Singleton, object)):

    """
    The Policy_Object will contain all database policy entries for easy
    filtering and mangling.
    It will be created at the beginning of the request and is supposed to stay
    alive unchanged during the request.
    """

    def __init__(self):
        """
        Create the Policy_Object from the database table

        """
        self.policies = []
        self.timestamp = None
        # read the policies from the database and store it in the object
        self.reload_from_db()

    def reload_from_db(self):
        """
        Read the timestamp from the database. If the timestamp is newer than
        the internal timestamp, then read the complete data
        :return:
        """
        check_reload_config = get_app_config_value("PI_CHECK_RELOAD_CONFIG", 0)
        if not self.timestamp or self.timestamp + datetime.timedelta(
                seconds=check_reload_config) < datetime.datetime.now():
            db_ts = Config.query.filter_by(Key=PRIVACYIDEA_TIMESTAMP).first()
            if reload_db(self.timestamp, db_ts):
                self.policies = []
                policies = Policy.query.all()
                for pol in policies:
                    # read each policy
                    self.policies.append(pol.get())
            self.timestamp = datetime.datetime.now()

    @classmethod
    def _search_value(cls, policy_attributes, searchvalue):
        """
        Searches a given value in a policy attribute. The policy_attribute is
        a list like searching the resolver name "resolver1" in the given
        resolvers of a policy:

            policy.get("resolver") = ["resolver1", "resolver2"]

        It returns a tuple of booleans if the searched value is
        contained/found or excluded.

        :param policy_attributes:
        :param searchvalue:
        :return: tuple of value_found and value_excluded
        """
        value_found = False
        value_excluded = False
        for value in policy_attributes:
            if value and value[0] in ["!", "-"] and \
                            searchvalue == value[1:]:
                value_excluded = True
            elif type(searchvalue) == list and value in \
                            searchvalue + ["*"]:
                value_found = True
            elif value in [searchvalue, "*"]:
                value_found = True
            elif type(searchvalue) != list:
                # Do not do this search style for resolvers, which come as a
                # list
                # check regular expression only for exact matches
                # avoid matching user1234 -> user1
                if re.search(u"^{0!s}$".format(value), searchvalue):
                    value_found = True

        return value_found, value_excluded

    @log_with(log)
    def get_policies(self, name=None, scope=None, realm=None, active=None,
                     resolver=None, user=None, client=None, action=None,
                     adminrealm=None, time=None, all_times=False,
                     sort_by_priority=True, audit_data=None):
        """
        Return the policies of the given filter values.

        :param name: The name of the policy
        :param scope: The scope of the policy
        :param realm: The realm in the policy
        :param active: Only active policies
        :param resolver: Only policies with this resolver
        :param user: Only policies with this user
        :type user: basestring
        :param client:
        :param action: Only policies, that contain this very action.
        :param adminrealm: This is the realm of the admin. This is only
            evaluated in the scope admin.
        :param time: The optional time, for which the policies should be
            fetched. The default time is now()
        :type time: datetime
        :param all_times: If True the time restriction of the policies is
            ignored. Policies of all time ranges will be returned.
        :type all_times: bool
        :param sort_by_priority: If true, sort the resulting list by priority, ascending
        by their policy numbers.
        :type sort_by_priority: bool
        :param audit_data: A dictionary with audit data collected during a request. This
            method will add found policies to the dictionary.
        :return: list of policies
        :rtype: list of dicts
        """
        reduced_policies = self.policies

        # filter policy for time. If no time is set or is a time is set and
        # it matches the time_range, then we add this policy
        if not all_times:
            reduced_policies = [policy for policy in reduced_policies if
                                (policy.get("time") and
                                 check_time_in_range(policy.get("time"), time))
                                or not policy.get("time")]
        log.debug("Policies after matching time: {0!s}".format(
            reduced_policies))

        # Do exact matches for "name", "active" and "scope", as these fields
        # can only contain one entry
        p = [("name", name), ("active", active), ("scope", scope)]
        for searchkey, searchvalue in p:
            if searchvalue is not None:
                reduced_policies = [policy for policy in reduced_policies if
                                    policy.get(searchkey) == searchvalue]
                log.debug("Policies after matching {1!s}: {0!s}".format(
                    reduced_policies, searchkey))

        p = [("action", action), ("user", user), ("realm", realm)]
        # If this is an admin-policy, we also do check the adminrealm
        if scope == "admin":
            p.append(("adminrealm", adminrealm))
        for searchkey, searchvalue in p:
            if searchvalue is not None:
                new_policies = []
                # first we find policies, that really match!
                # Either with the real value or with a "*"
                # values can be excluded by a leading "!" or "-"
                for policy in reduced_policies:
                    if not policy.get(searchkey):
                        # We also find the policies with no distinct information
                        # about the request value
                        new_policies.append(policy)
                    else:
                        value_found, value_excluded = self._search_value(
                            policy.get(searchkey), searchvalue)
                        if value_found and not value_excluded:
                            new_policies.append(policy)
                reduced_policies = new_policies
                log.debug("Policies after matching {1!s}: {0!s}".format(
                    reduced_policies, searchkey))

        # We need to act individually on the resolver key word
        # We either match the resolver exactly or we match another resolver (
        # which is not the first resolver) of the user, but only if the
        # check_all_resolvers flag in the policy is set.
        if resolver is not None:
            new_policies = []
            user_resolvers = []
            for policy in reduced_policies:
                if policy.get("check_all_resolvers"):
                    if realm and user:
                        # We have a realm and a user and can get all resolvers
                        # of this user in the realm
                        if not user_resolvers:
                            user_resolvers = User(user,
                                                  realm=realm).get_ordererd_resolvers()
                        for reso in user_resolvers:
                            value_found, _v_ex = self._search_value(
                                policy.get("resolver"), reso)
                            if value_found:
                                new_policies.append(policy)
                                break
                elif not policy.get("resolver"):
                    # We also find the policies with no distinct information
                    # about the request value
                    new_policies.append(policy)
                else:
                    value_found, _v_ex = self._search_value(
                        policy.get("resolver"), resolver)
                    if value_found:
                        new_policies.append(policy)

            reduced_policies = new_policies
            log.debug("Policies after matching resolver: {0!s}".format(
                reduced_policies))

        # Match the client IP.
        # Client IPs may be direct match, may be located in subnets or may
        # be excluded by a leading "-" or "!" sign.
        # The client definition in the policy may ba a comma separated list.
        # It may start with a "-" or a "!" to exclude the client
        # from a subnet.
        # Thus a client 10.0.0.2 matches a policy "10.0.0.0/8, -10.0.0.1" but
        # the client 10.0.0.1 does not match the policy "10.0.0.0/8, -10.0.0.1".
        # An empty client definition in the policy matches all clients.
        if client is not None:
            new_policies = []
            for policy in reduced_policies:
                log.debug(u"checking client ip in policy {0!s}.".format(policy))
                client_found, client_excluded = check_ip_in_policy(client, policy.get("client"))
                if client_found and not client_excluded:
                    # The client was contained in the defined subnets and was
                    #  not excluded
                    new_policies.append(policy)

            # If there is a policy without any client, we also add it to the
            # accepted list.
            for policy in reduced_policies:
                if not policy.get("client"):
                    new_policies.append(policy)
            reduced_policies = new_policies
            log.debug("Policies after matching client".format(
                reduced_policies))

        if sort_by_priority:
            reduced_policies = sorted(reduced_policies, key=itemgetter("priority"))

        if audit_data is not None:
            for p in reduced_policies:
                audit_data.setdefault("policies", []).append(p.get("name"))

        return reduced_policies

    @staticmethod
    def check_for_conflicts(policies, action):
        """
        Given a (not necessarily sorted) list of policy dictionaries and an action name,
        check that there are no action value conflicts.

        This raises a PolicyError if there are multiple policies with the highest
        priority which define different values for **action**.

        Otherwise, the function just returns nothing.

        :param policies: list of dictionaries
        :param action: string
        """
        if len(policies) > 1:
            prioritized_policy = min(policies, key=itemgetter("priority"))
            prioritized_action = prioritized_policy["action"][action]
            highest_priority = prioritized_policy["priority"]
            for other_policy in policies:
                if (other_policy["priority"] == highest_priority
                        and other_policy["action"][action] != prioritized_action):
                    raise PolicyError("Contradicting {!s} policies.".format(action))

    @log_with(log)
    def get_action_values(self, action, scope=SCOPE.AUTHZ, realm=None,
                          resolver=None, user=None, client=None, unique=False,
                          allow_white_space_in_action=False, adminrealm=None,
                          audit_data=None):
        """
        Get the defined action values for a certain action like
            scope: authorization
            action: tokentype
        would return a dictionary of {tokentype: policyname}

            scope: authorization
            action: serial
        would return a dictionary of {serial: policyname}

        :param unique: if set, the function will only consider the policy with the
            highest priority and check for policy conflicts.
        :param allow_white_space_in_action: Some policies like emailtext
            would allow entering text with whitespaces. These whitespaces
            must not be used to separate action values!
        :type allow_white_space_in_action: bool
        :param audit_data: This is a dictionary, that can take audit_data in the g object.
            If set, this dictionary will be filled with the list of triggered policynames in the
            key "policies". This can be useful for policies like ACTION.OTPPIN - where it is clear, that the
            found policy will be used. I could make less sense with an aktion like ACTION.LASTAUTH - where
            the value of the action needs to be evaluated in a more special case.
        :rtype: dict
        """
        policy_values = {}
        policies = self.get_policies(scope=scope, adminrealm=adminrealm,
                                     action=action, active=True,
                                     realm=realm, resolver=resolver, user=user,
                                     client=client, sort_by_priority=True)
        # If unique = True, only consider the policies with the highest priority
        if policies and unique:
            highest_priority = policies[0]['priority']
            policies = [p for p in policies if p['priority'] == highest_priority]
        for pol in policies:
            action_dict = pol.get("action", {})
            action_value = action_dict.get(action, "")
            policy_name = pol.get("name")
            """
            We must distinguish actions like:
                tokentype=totp hotp motp,
            where the string represents a list divided by spaces, and
                smstext='your otp is <otp>'
            where the spaces are part of the string.
            """
            # By saving the policynames in a dict with the values being the key,
            # we achieve unique policy_values.
            # Save the policynames in a list
            if action_value.startswith("'") and action_value.endswith("'"):
                action_key = action_dict.get(action)[1:-1]
                policy_values.setdefault(action_key, []).append(policy_name)
            elif allow_white_space_in_action:
                action_key = action_dict.get(action)
                policy_values.setdefault(action_key, []).append(policy_name)
            else:
                for action_key in action_dict.get(action, "").split():
                    policy_values.setdefault(action_key, []).append(policy_name)

        # Check if the policies with the highest priority agree on the action values
        if unique and len(policy_values) > 1:
            names = [p['name'] for p in policies]
            raise PolicyError(u"There are policies with conflicting actions: {!r}".format(names))

        if audit_data is not None:
            for action_value, policy_names in policy_values.items():
                for p_name in policy_names:
                    audit_data.setdefault("policies", []).append(p_name)

        return policy_values

    @log_with(log)
    def ui_get_main_menus(self, logged_in_user, client=None):
        """
        Get the list of allowed main menus derived from the policies for the
        given user - admin or normal user.
        It fetches all policies for this user and compiles a list of allowed
        menus to display or hide in the UI.

        :param logged_in_user: The logged in user, a dictionary with keys
            "username", "realm" and "role".
        :param client: The IP address of the client
        :return: A list of MENUs to be displayed
        """
        from privacyidea.lib.token import get_dynamic_policy_definitions
        role = logged_in_user.get("role")
        user_rights = self.ui_get_rights(role,
                                         logged_in_user.get("realm"),
                                         logged_in_user.get("username"),
                                         client)
        main_menus = []
        static_rights = get_static_policy_definitions(role)
        enroll_rights = get_dynamic_policy_definitions(role)
        static_rights.update(enroll_rights)
        for r in user_rights:
            menus = static_rights.get(r, {}).get("mainmenu", [])
            main_menus.extend(menus)

        main_menus = list(set(main_menus))
        return main_menus

    @log_with(log)
    def ui_get_rights(self, scope, realm, username, client=None):
        """
        Get the rights derived from the policies for the given realm and user.
        Works for admins and normal users.
        It fetches all policies for this user and compiles a maximum list of
        allowed rights, that can be used to hide certain UI elements.

        :param scope: Can be SCOPE.ADMIN or SCOPE.USER
        :param realm: Is either user users realm or the adminrealm
        :param username: The loginname of the user
        :param client: The HTTP client IP
        :return: A list of actions
        """
        from privacyidea.lib.auth import ROLE
        from privacyidea.lib.token import get_dynamic_policy_definitions
        rights = set()
        userrealm = None
        adminrealm = None
        resolver = None
        logged_in_user = {"username": username,
                          "realm": realm}
        if scope == SCOPE.ADMIN:
            adminrealm = realm
            logged_in_user["role"] = ROLE.ADMIN
        elif scope == SCOPE.USER:
            userrealm = realm
            logged_in_user["role"] = ROLE.USER
            resolver = User(username, userrealm).resolver
        pols = self.get_policies(scope=scope,
                                 adminrealm=adminrealm,
                                 realm=userrealm,
                                 resolver=resolver,
                                 user=username, active=True,
                                 client=client)
        for pol in pols:
            for action, action_value in pol.get("action").items():
                if action_value:
                    rights.add(action)
                    # if the action has an actual non-boolean value, return it
                    if isinstance(action_value, string_types):
                        rights.add(u"{}={}".format(action, action_value))
        # check if we have policies at all:
        pols = self.get_policies(scope=scope, active=True)
        if not pols:
            # We do not have any policies in this scope, so we return all
            # possible actions in this scope.
            log.debug("No policies defined, so we set all rights.")
            rights = get_static_policy_definitions(scope)
            rights.update(get_dynamic_policy_definitions(scope))
        rights = list(rights)
        log.debug("returning the admin rights: {0!s}".format(rights))
        return rights

    @log_with(log)
    def ui_get_enroll_tokentypes(self, client, logged_in_user):
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

        :param client: Client IP address
        :type client: basestring
        :param logged_in_user: The Dict of the logged in user
        :type logged_in_user: dict
        :return: list of token types, the user may enroll
        """
        from privacyidea.lib.auth import ROLE
        enroll_types = {}
        role = logged_in_user.get("role")
        if role == ROLE.ADMIN:
            admin_realm = logged_in_user.get("realm")
            user_realm = None
        else:
            admin_realm = None
            user_realm = logged_in_user.get("realm")
        # check, if we have a policy definition at all.
        pols = self.get_policies(scope=role, active=True)
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
                # determine, if there is a enrollment policy for this very type
                typepols = self.get_policies(scope=role, client=client,
                                             user=logged_in_user.get("username"),
                                             realm=user_realm,
                                             active=True,
                                             action="enroll"+tokentype.upper(),
                                             adminrealm=admin_realm)
                if typepols:
                    # If there is no policy allowing the enrollment of this
                    # tokentype, it is deleted.
                    filtered_enroll_types[tokentype] = enroll_types[tokentype]
            enroll_types = filtered_enroll_types

        return enroll_types

# --------------------------------------------------------------------------
#
#  NEW STUFF
#
#


@log_with(log)
def set_policy(name=None, scope=None, action=None, realm=None, resolver=None,
               user=None, time=None, client=None, active=True,
               adminrealm=None, priority=None, check_all_resolvers=False):
    """
    Function to set a policy.
    If the policy with this name already exists, it updates the policy.
    It expects a dict of with the following keys:
    :param name: The name of the policy
    :param scope: The scope of the policy. Something like "admin" or "authentication"
    :param action: A scope specific action or a comma separated list of actions
    :type active: basestring
    :param realm: A realm, for which this policy is valid
    :param resolver: A resolver, for which this policy is valid
    :param user: A username or a list of usernames
    :param time: N/A    if type()
    :param client: A client IP with optionally a subnet like 172.16.0.0/16
    :param active: If the policy is active or not
    :type active: bool
    :param priority: the priority of the policy (smaller values having higher priority)
    :type priority: int
    :param check_all_resolvers: If all the resolvers of a user should be
        checked with this policy
    :type check_all_resolvers: bool
    :return: The database ID od the the policy
    :rtype: int
    """
    active = is_true(active)
    if isinstance(priority, six.string_types):
        priority = int(priority)
    if priority is not None and priority <= 0:
        raise ParameterError("Priority must be at least 1")
    check_all_resolvers = is_true(check_all_resolvers)
    if type(action) == dict:
        action_list = []
        for k, v in action.items():
            if v is not True:
                # value key
                action_list.append("{0!s}={1!s}".format(k, v))
            else:
                # simple boolean value
                action_list.append(k)
        action = ", ".join(action_list)
    if type(action) == list:
        action = ", ".join(action)
    if type(realm) == list:
        realm = ", ".join(realm)
    if type(adminrealm) == list:
        adminrealm = ", ".join(adminrealm)
    if type(user) == list:
        user = ", ".join(user)
    if type(resolver) == list:
        resolver = ", ".join(resolver)
    if type(client) == list:
        client = ", ".join(client)
    p1 = Policy.query.filter_by(name=name).first()
    if p1:
        # The policy already exist, we need to update
        if action is not None:
            p1.action = action
        if scope is not None:
            p1.scope = scope
        if realm is not None:
            p1.realm = realm
        if adminrealm is not None:
            p1.adminrealm = adminrealm
        if resolver is not None:
            p1.resolver = resolver
        if user is not None:
            p1.user = user
        if client is not None:
            p1.client = client
        if time is not None:
            p1.time = time
        if priority is not None:
            p1.priority = priority
        p1.active = active
        p1.check_all_resolvers = check_all_resolvers
        save_config_timestamp()
        db.session.commit()
        ret = p1.id
    else:
        # Create a new policy
        ret = Policy(name, action=action, scope=scope, realm=realm,
                     user=user, time=time, client=client, active=active,
                     resolver=resolver, adminrealm=adminrealm,
                     priority=priority,
                     check_all_resolvers=check_all_resolvers).save()
    return ret


@log_with(log)
def enable_policy(name, enable=True):
    """
    Enable or disable the policy with the given name
    :param name:
    :return: ID of the policy
    """
    if not Policy.query.filter(Policy.name == name).first():
        raise ResourceNotFoundError(u"The policy with name '{0!s}' does not exist".format(name))

    # Update the policy
    p = set_policy(name=name, active=enable)
    return p


@log_with(log)
def delete_policy(name):
    """
    Function to delete one named policy.
    Raise ResourceNotFoundError if there is no such policy.

    :param name: the name of the policy to be deleted
    :return: the ID of the deleted policy
    :rtype: int
    """
    return fetch_one_resource(Policy, name=name).delete()


@log_with(log)
def delete_all_policies():
    policies = Policy.query.all()
    for p in policies:
        p.delete()


@log_with(log)
def export_policies(policies):
    """
    This function takes a policy list and creates an export file from it

    :param policies: a policy definition
    :type policies: list of policy dictionaries
    :return: the contents of the file
    :rtype: string
    """
    file_contents = ""
    if policies:
        for policy in policies:
            file_contents += "[{0!s}]\n".format(policy.get("name"))
            for key, value in policy.items():
                file_contents += "{0!s} = {1!s}\n".format(key, value)
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
    for policy_name, policy in policies.items():
        ret = set_policy(name=policy_name,
                         action=ast.literal_eval(policy.get("action")),
                         scope=policy.get("scope"),
                         realm=ast.literal_eval(policy.get("realm", "[]")),
                         user=ast.literal_eval(policy.get("user", "[]")),
                         resolver=ast.literal_eval(policy.get("resolver", "[]")),
                         client=ast.literal_eval(policy.get("client", "[]")),
                         time=policy.get("time", ""),
                         priority=policy.get("priority", "1")
                         )
        if ret > 0:
            log.debug("import policy {0!s}: {1!s}".format(policy_name, ret))
            res += 1
    return res


@log_with(log)
def get_static_policy_definitions(scope=None):
    """
    These are the static hard coded policy definitions.
    They can be enhanced by token based policy definitions, that can be found
    in lib.token.get_dynamic_policy_definitions.

    :param scope: Optional the scope of the policies
    :type scope: basestring
    :return: allowed scopes with allowed actions, the type of action and a
    description.
    :rtype: dict
    """
    resolvers = list(get_resolver_list())
    realms = list(get_realms())
    smtpconfigs = [server.config.identifier for server in get_smtpservers()]
    radiusconfigs = [radius.config.identifier for radius in
                     get_radiusservers()]
    radiusconfigs.insert(0, "userstore")
    # "type": allowed values str, bool, int
    # "desc": description of this action
    # "value": list of allowed values of this action, works with int and str. A
    #          dropdown box will be displayed
    # "group": ment to be used for grouping actions for better finding
    # "mainmenu": list of enabled Menus. If this action is set, this menu
    #                 is visible in the WebUI
    pol = {
        SCOPE.REGISTER: {
            ACTION.RESOLVER: {'type': 'str',
                              'value': resolvers,
                              'desc': _('Define in which resolver the user '
                                        'should be registered.')},
            ACTION.REALM: {'type': 'str',
                           'value': realms,
                           'desc': _('Define in which realm the user should '
                                     'be registered.')},
            ACTION.EMAILCONFIG: {'type': 'str',
                                 'value': smtpconfigs,
                                 'desc': _('The SMTP server configuration, '
                                           'that should be used to send the '
                                           'registration email.')},
            ACTION.REQUIREDEMAIL: {'type': 'str',
                                   'desc': _('Only users with this email '
                                             'address are allowed to '
                                             'register. This is a regular '
                                             'expression.')},
            ACTION.REGISTERBODY: {'type': 'text',
                                  'desc': _("The body of the registration "
                                            "email. Use '{regkey}' as tag"
                                            "for the registration key.")}
        },
        SCOPE.ADMIN: {
            ACTION.ENABLE: {'type': 'bool',
                            'desc': _('Admin is allowed to enable tokens.'),
                            'mainmenu': [MAIN_MENU.TOKENS],
                            'group': GROUP.TOKEN},
            ACTION.DISABLE: {'type': 'bool',
                             'desc': _('Admin is allowed to disable tokens.'),
                             'mainmenu': [MAIN_MENU.TOKENS],
                             'group': GROUP.TOKEN},
            ACTION.SET: {'type': 'bool',
                         'desc': _(
                             'Admin is allowed to set token properties.'),
                         'mainmenu': [MAIN_MENU.TOKENS],
                         'group': GROUP.TOKEN},
            ACTION.SETPIN: {'type': 'bool',
                            'desc': _(
                                'Admin is allowed to set the OTP PIN of '
                                'tokens.'),
                            'mainmenu': [MAIN_MENU.TOKENS],
                            'group': GROUP.TOKEN},
            ACTION.SETTOKENINFO: {'type': 'bool',
                               'desc': _('Admin is allowed to manually set and delete token info.'),
                               'mainmenu': [MAIN_MENU.TOKENS],
                               'group': GROUP.TOKEN},
            ACTION.ENROLLPIN: {'type': 'bool',
                               "desc": _("Admin is allowed to set the OTP "
                                         "PIN during enrollment."),
                               'mainmenu': [MAIN_MENU.TOKENS],
                               'group': GROUP.ENROLLMENT},
            ACTION.RESYNC: {'type': 'bool',
                            'desc': _('Admin is allowed to resync tokens.'),
                            'mainmenu': [MAIN_MENU.TOKENS],
                            'group': GROUP.TOKEN},
            ACTION.RESET: {'type': 'bool',
                           'desc': _(
                               'Admin is allowed to reset the Failcounter of '
                               'a token.'),
                           'mainmenu': [MAIN_MENU.TOKENS],
                           'group': GROUP.TOKEN},
            ACTION.REVOKE: {'tpye': 'bool',
                            'desc': _("Admin is allowed to revoke a token"),
                            'mainmenu': [MAIN_MENU.TOKENS],
                            'group': GROUP.TOKEN},
            ACTION.ASSIGN: {'type': 'bool',
                            'desc': _(
                                'Admin is allowed to assign a token to a '
                                'user.'),
                            'mainmenu': [MAIN_MENU.TOKENS, MAIN_MENU.USERS],
                            'group': GROUP.TOKEN},
            ACTION.UNASSIGN: {'type': 'bool',
                              'desc': _(
                                  'Admin is allowed to remove the token from '
                                  'a user, '
                                  'i.e. unassign a token.'),
                              'mainmenu': [MAIN_MENU.TOKENS],
                              'group': GROUP.TOKEN},
            ACTION.IMPORT: {'type': 'bool',
                            'desc': _(
                                'Admin is allowed to import token files.'),
                            'mainmenu': [MAIN_MENU.TOKENS],
                            'group': GROUP.SYSTEM},
            ACTION.DELETE: {'type': 'bool',
                            'desc': _(
                                'Admin is allowed to remove tokens from the '
                                'database.'),
                            'mainmenu': [MAIN_MENU.TOKENS],
                            'group': GROUP.TOKEN},
            ACTION.USERLIST: {'type': 'bool',
                              'desc': _(
                                  'Admin is allowed to view the list of the '
                                  'users.'),
                              'mainmenu': [MAIN_MENU.USERS],
                              'group': GROUP.GENERAL},
            ACTION.MACHINELIST: {'type': 'bool',
                                 'desc': _('The Admin is allowed to list '
                                           'the machines.'),
                                 'mainmenu': [MAIN_MENU.MACHINES],
                                 'group': GROUP.MACHINE},
            ACTION.MACHINETOKENS: {'type': 'bool',
                                   'desc': _('The Admin is allowed to attach '
                                             'and detach tokens to '
                                             'machines.'),
                                   'mainmenu': [MAIN_MENU.TOKENS,
                                                MAIN_MENU.MACHINES],
                                   'group': GROUP.MACHINE},
            ACTION.AUTHITEMS: {'type': 'bool',
                               'desc': _('The Admin is allowed to fetch '
                                         'authentication items of tokens '
                                         'assigned to machines.'),
                               'group': GROUP.GENERAL},
            ACTION.TOKENREALMS: {'type': 'bool',
                                 'desc': _('Admin is allowed to manage the '
                                           'realms of a token.'),
                                 'mainmenu': [MAIN_MENU.TOKENS],
                                 'group': GROUP.TOKEN},
            ACTION.GETSERIAL: {'type': 'bool',
                               'desc': _('Admin is allowed to retrieve a serial'
                                         ' for a given OTP value.'),
                               'mainmenu': [MAIN_MENU.TOKENS],
                               "group": GROUP.TOOLS},
            ACTION.GETRANDOM: {'type': 'bool',
                               'desc': _('Admin is allowed to retrieve '
                                         'random keys from privacyIDEA.'),
                               'group': GROUP.TOOLS},
            ACTION.COPYTOKENPIN: {'type': 'bool',
                                  'desc': _(
                                      'Admin is allowed to copy the PIN of '
                                      'one token '
                                      'to another token.'),
                                  "group": GROUP.TOOLS},
            ACTION.COPYTOKENUSER: {'type': 'bool',
                                   'desc': _(
                                       'Admin is allowed to copy the assigned '
                                       'user to another'
                                       ' token, i.e. assign a user ot '
                                       'another token.'),
                                   "group": GROUP.TOOLS},
            ACTION.LOSTTOKEN: {'type': 'bool',
                               'desc': _('Admin is allowed to trigger the '
                                         'lost token workflow.'),
                               'mainmenu': [MAIN_MENU.TOKENS],
                               'group': GROUP.TOOLS},

            ACTION.SYSTEMWRITE: {'type': 'bool',
                                 "desc": _("Admin is allowed to write and "
                                           "modify the system configuration."),
                                 "group": GROUP.SYSTEM,
                                 'mainmenu': [MAIN_MENU.CONFIG]},
            ACTION.SYSTEMDELETE: {'type': 'bool',
                                  "desc": _("Admin is allowed to delete "
                                            "keys in the system "
                                            "configuration."),
                                  "group": GROUP.SYSTEM,
                                  'mainmenu': [MAIN_MENU.CONFIG]},
            ACTION.CONFIGDOCUMENTATION: {'type': 'bool',
                                         'desc': _('Admin is allowed to '
                                                   'export a documentation '
                                                   'of the complete '
                                                   'configuration including '
                                                   'resolvers and realm.'),
                                         'group': GROUP.SYSTEM,
                                         'mainmenu': [MAIN_MENU.CONFIG]},
            ACTION.POLICYWRITE: {'type': 'bool',
                                 "desc": _("Admin is allowed to write and "
                                           "modify the policies."),
                                 "group": GROUP.SYSTEM,
                                 'mainmenu': [MAIN_MENU.CONFIG]},
            ACTION.POLICYDELETE: {'type': 'bool',
                                  "desc": _("Admin is allowed to delete "
                                            "policies."),
                                  "group": GROUP.SYSTEM,
                                  'mainmenu': [MAIN_MENU.CONFIG]},
            ACTION.RESOLVERWRITE: {'type': 'bool',
                                   "desc": _("Admin is allowed to write and "
                                             "modify the "
                                             "resolver and realm "
                                             "configuration."),
                                   "group": GROUP.SYSTEM,
                                   'mainmenu': [MAIN_MENU.CONFIG]},
            ACTION.RESOLVERDELETE: {'type': 'bool',
                                    "desc": _("Admin is allowed to delete "
                                              "resolvers and realms."),
                                    "group": GROUP.SYSTEM,
                                    'mainmenu': [MAIN_MENU.CONFIG]},
            ACTION.CACONNECTORWRITE: {'type': 'bool',
                                      "desc": _("Admin is allowed to create new"
                                                " CA Connector definitions "
                                                "and modify existing ones."),
                                      "group": GROUP.SYSTEM,
                                      'mainmenu': [MAIN_MENU.CONFIG]},
            ACTION.CACONNECTORDELETE: {'type': 'bool',
                                       "desc": _("Admin is allowed to delete "
                                                 "CA Connector definitions."),
                                       "group": GROUP.SYSTEM,
                                       'mainmenu': [MAIN_MENU.CONFIG]},
            ACTION.MACHINERESOLVERWRITE: {'type': 'bool',
                                          'desc': _("Admin is allowed to "
                                                    "write and modify the "
                                                    "machine resolvers."),
                                          'group': GROUP.SYSTEM,
                                          'mainmenu': [MAIN_MENU.CONFIG]},
            ACTION.MACHINERESOLVERDELETE: {'type': 'bool',
                                           'desc': _("Admin is allowed to "
                                                     "delete "
                                                     "machine resolvers."),
                                           'group': GROUP.SYSTEM,
                                           'mainmenu': [MAIN_MENU.CONFIG]},
            ACTION.OTPPINMAXLEN: {'type': 'int',
                                  'value': list(range(0, 32)),
                                  "desc": _("Set the maximum allowed length "
                                            "of the OTP PIN."),
                                  'group': GROUP.PIN},
            ACTION.OTPPINMINLEN: {'type': 'int',
                                  'value': list(range(0, 32)),
                                  "desc": _("Set the minimum required length "
                                            "of the OTP PIN."),
                                  'group': GROUP.PIN},
            ACTION.OTPPINCONTENTS: {'type': 'str',
                                    "desc": _("Specifiy the required "
                                              "contents of the OTP PIN. "
                                              "(c)haracters, (n)umeric, "
                                              "(s)pecial, (o)thers. [+/-]!"),
                                    'group': GROUP.PIN},
            ACTION.AUDIT: {'type': 'bool',
                           "desc": _("Admin is allowed to view the Audit log."),
                           "group": GROUP.SYSTEM,
                           'mainmenu': [MAIN_MENU.AUDIT]},
            ACTION.AUDIT_AGE: {'type': 'str',
                               "desc": _("The admin will only see audit "
                                         "entries of the last 10d, 3m or 2y."),
                               "group": GROUP.SYSTEM,
                               'mainmenu': [MAIN_MENU.AUDIT]},
            ACTION.AUDIT_DOWNLOAD: {'type': 'bool',
                               "desc": _("The admin is allowed to download "
                                         "the complete auditlog."),
                               "group": GROUP.SYSTEM,
                               'mainmenu': [MAIN_MENU.AUDIT]},
            ACTION.ADDUSER: {'type': 'bool',
                             "desc": _("Admin is allowed to add users in a "
                                       "userstore/UserIdResolver."),
                             "group": GROUP.USER,
                             'mainmenu': [MAIN_MENU.USERS]},
            ACTION.UPDATEUSER: {'type': 'bool',
                                "desc": _("Admin is allowed to update the "
                                          "users data in a userstore."),
                                "group": GROUP.USER,
                                'mainmenu': [MAIN_MENU.USERS]},
            ACTION.DELETEUSER: {'type': 'bool',
                                "desc": _("Admin is allowed to delete a user "
                                          "object in a userstore."),
                                'mainmenu': [MAIN_MENU.USERS],
                                'group': GROUP.USER},
            ACTION.SETHSM: {'type': 'bool',
                            'desc': _("Admin is allowed to set the password "
                                      "of the HSM/Security Module."),
                            'group': GROUP.SYSTEM},
            ACTION.GETCHALLENGES: {'type': 'bool',
                                   'desc': _("Admin is allowed to retrieve "
                                             "the list of active "
                                             "challenges."),
                                   'mainmenu': [MAIN_MENU.TOKENS],
                                   'group': GROUP.GENERAL},
            ACTION.SMTPSERVERWRITE: {'type': 'bool',
                                     'desc': _("Admin is allowed to write new "
                                               "SMTP server definitions."),
                                     'mainmenu': [MAIN_MENU.CONFIG],
                                     'group': GROUP.SYSTEM},
            ACTION.RADIUSSERVERWRITE: {'type': 'bool',
                                       'desc': _("Admin is allowed to write "
                                                 "new RADIUS server "
                                                 "definitions."),
                                       'mainmenu': [MAIN_MENU.CONFIG],
                                       'group': GROUP.SYSTEM},
            ACTION.PRIVACYIDEASERVERWRITE: {'type': 'bool',
                                            'desc': _("Admin is allowed to "
                                                      "write remote "
                                                      "privacyIDEA server "
                                                      "definitions."),
                                            'mainmenu': [MAIN_MENU.CONFIG],
                                            'group': GROUP.SYSTEM},
            ACTION.PERIODICTASKWRITE: {'type': 'bool',
                                       'desc': _("Admin is allowed to write "
                                                 "periodic task definitions."),
                                            'mainmenu': [MAIN_MENU.CONFIG],
                                            'group': GROUP.SYSTEM},
            ACTION.STATISTICSREAD: {'type': 'bool',
                                    'desc': _("Admin is allowed to read statistics data."),
                                    'group': GROUP.SYSTEM},
            ACTION.STATISTICSDELETE: {'type': 'bool',
                                    'desc': _("Admin is allowed to delete statistics data."),
                                    'group': GROUP.SYSTEM},
            ACTION.EVENTHANDLINGWRITE: {'type': 'bool',
                                        'desc': _("Admin is allowed to write "
                                                  "and modify the event "
                                                  "handling configuration."),
                                        'mainmenu': [MAIN_MENU.CONFIG],
                                        'group': GROUP.SYSTEM},
            ACTION.SMSGATEWAYWRITE: {'type': 'bool',
                                     'desc': _("Admin is allowed to write "
                                               "and modify SMS gateway "
                                               "definitions."),
                                     'mainmenu': [MAIN_MENU.CONFIG],
                                     'group': GROUP.SYSTEM},
            ACTION.CLIENTTYPE: {'type': 'bool',
                                'desc': _("Admin is allowed to get the list "
                                          "of authenticated clients and their "
                                          "types."),
                                'mainmenu': [MAIN_MENU.COMPONENTS],
                                'group': GROUP.SYSTEM},
            ACTION.MANAGESUBSCRIPTION: {
                'type': 'bool',
                'desc': _("Admin is allowed to add and delete component "
                          "subscriptions."),
                'mainmenu': [MAIN_MENU.COMPONENTS],
                'group': GROUP.SYSTEM},
            ACTION.TRIGGERCHALLENGE: {
                'type': 'bool',
                'desc': _("The Admin is allowed to trigger a challenge for "
                          "e.g. SMS OTP token."),
                'mainmenu': [],
                'group': GROUP.GENERAL
            }
        },

        SCOPE.USER: {
            ACTION.ASSIGN: {
                'type': 'bool',
                'desc': _("The user is allowed to assign an existing token"
                          " that is not yet assigned"
                          " using the token serial number."),
                'mainmenu': [MAIN_MENU.TOKENS],
                'group': GROUP.TOKEN},
            ACTION.DISABLE: {'type': 'bool',
                             'desc': _(
                                 'The user is allowed to disable his own '
                                 'tokens.'),
                             'mainmenu': [MAIN_MENU.TOKENS],
                             'group': GROUP.TOKEN},
            ACTION.ENABLE: {'type': 'bool',
                            'desc': _(
                                "The user is allowed to enable his own "
                                "tokens."),
                            'mainmenu': [MAIN_MENU.TOKENS],
                            'group': GROUP.TOKEN},
            ACTION.DELETE: {'type': 'bool',
                            "desc": _(
                                "The user is allowed to delete his own "
                                "tokens."),
                            'mainmenu': [MAIN_MENU.TOKENS],
                            'group': GROUP.TOKEN},
            ACTION.UNASSIGN: {'type': 'bool',
                              "desc": _("The user is allowed to unassign his "
                                        "own tokens."),
                              'mainmenu': [MAIN_MENU.TOKENS],
                              'group': GROUP.TOKEN},
            ACTION.RESYNC: {'type': 'bool',
                            "desc": _("The user is allowed to resyncronize his "
                                      "tokens."),
                            'mainmenu': [MAIN_MENU.TOKENS],
                            'group': GROUP.TOKEN},
            ACTION.REVOKE: {'type': 'bool',
                            'desc': _("The user is allowed to revoke a "
                                      "token"),
                            'mainmenu': [MAIN_MENU.TOKENS],
                            'group': GROUP.TOKEN},
            ACTION.RESET: {'type': 'bool',
                           'desc': _('The user is allowed to reset the '
                                     'failcounter of his tokens.'),
                           'mainmenu': [MAIN_MENU.TOKENS],
                           'group': GROUP.TOKEN},
            ACTION.SETPIN: {'type': 'bool',
                            "desc": _("The user is allowed to set the OTP "
                                      "PIN of his tokens."),
                            'mainmenu': [MAIN_MENU.TOKENS],
                            'group': GROUP.PIN},
            ACTION.ENROLLPIN: {'type': 'bool',
                               "desc": _("The user is allowed to set the OTP "
                                         "PIN during enrollment."),
                               'group': GROUP.PIN},
            ACTION.OTPPINMAXLEN: {'type': 'int',
                                  'value': list(range(0, 32)),
                                  "desc": _("Set the maximum allowed length "
                                            "of the OTP PIN."),
                                  'group': GROUP.PIN},
            ACTION.OTPPINMINLEN: {'type': 'int',
                                  'value': list(range(0, 32)),
                                  "desc": _("Set the minimum required length "
                                            "of the OTP PIN."),
                                  'group': GROUP.PIN},
            ACTION.OTPPINCONTENTS: {'type': 'str',
                                    "desc": _("Specifiy the required "
                                              "contents of the OTP PIN. "
                                              "(c)haracters, (n)umeric, "
                                              "(s)pecial, (o)thers. [+/-]!"),
                                    'group': GROUP.PIN},

            ACTION.AUDIT: {
                'type': 'bool',
                'desc': _('Allow the user to view his own token history.'),
                'mainmenu': [MAIN_MENU.AUDIT]},
            ACTION.AUDIT_AGE: {'type': 'str',
                               "desc": _("The user will only see audit "
                                         "entries of the last 10d, 3m or 2y."),
                               'mainmenu': [MAIN_MENU.AUDIT]},
            ACTION.USERLIST: {'type': 'bool',
                              'desc': _("The user is allowed to view his "
                                        "own user information."),
                              'mainmenu': [MAIN_MENU.USERS]},
            ACTION.UPDATEUSER: {'type': 'bool',
                                'desc': _("The user is allowed to update his "
                                          "own user information, like changing "
                                          "his password."),
                                'mainmenu': [MAIN_MENU.USERS]},
            ACTION.PASSWORDRESET: {'type': 'bool',
                                   'desc': _("The user is allowed to do a "
                                             "password reset in an editable "
                                             "UserIdResolver."),
                                   'mainmenu': []}

        },
        SCOPE.ENROLL: {
            ACTION.MAXTOKENREALM: {
                'type': 'int',
                'desc': _('Limit the number of allowed tokens in a realm.'),
                'group': GROUP.TOKEN},
            ACTION.MAXTOKENUSER: {
                'type': 'int',
                'desc': _('Limit the number of tokens a user may have '
                          'assigned.'),
                'group': GROUP.TOKEN},
            ACTION.OTPPINRANDOM: {
                'type': 'int',
                'value': list(range(0, 32)),
                "desc": _("Set a random OTP PIN with this length for a "
                          "token."),
                'group': GROUP.PIN},
            ACTION.PINHANDLING: {
                'type': 'str',
                'desc': _('In case of a random OTP PIN use this python '
                          'module to process the PIN.'),
                'group': GROUP.PIN},
            ACTION.CHANGE_PIN_FIRST_USE: {
                'type': 'bool',
                'desc': _("If the administrator sets the OTP PIN during "
                          "enrollment or later, the user will have to change "
                          "the PIN during first use."),
                'group': GROUP.PIN
            },
            ACTION.CHANGE_PIN_EVERY: {
                'type': 'str',
                'desc': _("The user needs to change his PIN on a regular "
                          "basis. To change the PIN every 180 days, "
                          "enter '180d'."),
                'group': GROUP.PIN
            },
            ACTION.ENCRYPTPIN: {
                'type': 'bool',
                "desc": _("The OTP PIN can be hashed or encrypted. Hashing "
                          "the PIN is the default behaviour."),
                'group': GROUP.PIN},
            ACTION.TOKENLABEL: {
                'type': 'str',
                'desc': _("Set label for a new enrolled Google Authenticator. "
                          "Possible tags are <u> (user), <r> ("
                          "realm), <s> (serial)."),
                'group': GROUP.TOKEN},
            ACTION.TOKENISSUER: {
                'type': 'str',
                'desc': _("This is the issuer label for new enrolled Google "
                          "Authenticators."),
                'group': GROUP.TOKEN
            },
            ACTION.APPIMAGEURL: {
                'type': 'str',
                'desc': _("This is the URL to the token image for smartphone apps "
                          "like FreeOTP."),
                'group': GROUP.TOKEN
            },
            ACTION.AUTOASSIGN: {
                'type': 'str',
                'value': [AUTOASSIGNVALUE.NONE, AUTOASSIGNVALUE.USERSTORE],
                'desc': _("Users can assign a token just by using the "
                          "unassigned token to authenticate."),
                'group': GROUP.TOKEN},
            ACTION.LOSTTOKENPWLEN: {
                'type': 'int',
                'value': list(range(1, 32)),
                'desc': _('The length of the password in case of '
                          'temporary token (lost token).')},
            ACTION.LOSTTOKENPWCONTENTS: {
                'type': 'str',
                'desc': _('The contents of the temporary password, '
                          'described by the characters C, c, n, s, 8.')},
            ACTION.LOSTTOKENVALID: {
                'type': 'int',
                'value': list(range(1, 61)),
                'desc': _('The length of the validity for the temporary '
                          'token (in days).')},
        },
        SCOPE.AUTH: {
            ACTION.OTPPIN: {
                'type': 'str',
                'value': [ACTIONVALUE.TOKENPIN, ACTIONVALUE.USERSTORE,
                          ACTIONVALUE.NONE],
                'desc': _('Either use the Token PIN , use the Userstore '
                          'Password or use no fixed password '
                          'component.')},
            ACTION.CHALLENGERESPONSE: {
                'type': 'str',
                'desc': _('This is a whitespace separated list of tokentypes, '
                          'that can be used with challenge response.')
            },
            ACTION.CHALLENGETEXT: {
                'type': 'str',
                'desc': _('Use an alternate challenge text for telling the '
                          'user to enter an OTP value.')
            },
            ACTION.CHALLENGETEXT_HEADER: {
                'type': 'str',
                'desc': _("If there are several different challenges, this text precedes the list"
                          " of the challenge texts.")
            },
            ACTION.CHALLENGETEXT_FOOTER: {
                'type': 'str',
                'desc': _("If there are several different challenges, this text follows the list"
                          " of the challenge texts.")
            },
            ACTION.PASSTHRU: {
                'type': 'str',
                'value': radiusconfigs,
                'desc': _('If set, the user in this realm will be '
                          'authenticated against the userstore or against the '
                          'given RADIUS config,'
                          ' if the user has no tokens assigned.')
            },
            ACTION.PASSNOTOKEN: {
                'type': 'bool',
                'desc': _('If the user has no token, the authentication '
                          'request for this user will always be true.')
            },
            ACTION.PASSNOUSER: {
                'type': 'bool',
                'desc': _('If the user user does not exist, '
                          'the authentication request for this '
                          'non-existing user will always be true.')
            },
            ACTION.MANGLE: {
                'type': 'str',
                'desc': _('Can be used to modify the parameters pass, '
                          'user and realm in an authentication request. See '
                          'the documentation for an example.')
            },
            ACTION.RESETALLTOKENS: {
                'type': 'bool',
                'desc': _('If a user authenticates successfully reset the '
                          'failcounter of all of his tokens.')
            },
            ACTION.AUTH_CACHE: {
                'type': 'str',
                'desc': _('Cache the password used for authentication and '
                          'allow authentication with the same credentials for a '
                          'certain amount of time. '
                          'Specify timeout like 4h or 4h/5m.')
            }
        },
        SCOPE.AUTHZ: {
            ACTION.AUTHMAXSUCCESS: {
                'type': 'str',
                'desc': _("You can specify how many successful authentication "
                          "requests a user is allowed to do in a given time. "
                          "Specify like 1/5s, 2/10m, 10/1h - s, m, h being "
                          "second, minute and hour.")
            },
            ACTION.AUTHMAXFAIL: {
                'type': 'str',
                'desc': _("You can specify how many failed authentication "
                          "requests a user is allowed to do in a given time. "
                          "Specify like 1/5s, 2/10m, 10/1h - s, m, h being "
                          "second, minute and hour.")
            },
            ACTION.LASTAUTH: {
                'type': 'str',
                'desc': _("You can specify in which time frame the user needs "
                          "to authenticate again with this token. If the user "
                          "authenticates later, authentication will fail. "
                          "Specify like 30h, 7d or 1y.")
            },
            ACTION.TOKENTYPE: {
                'type': 'str',
                'desc': _('The user will only be authenticated with this '
                          'very tokentype.')},
            ACTION.SERIAL: {
                'type': 'str',
                'desc': _('The user will only be authenticated if the serial '
                          'number of the token matches this regexp.')},
            ACTION.TOKENINFO: {
                'type': 'str',
                'desc': _("The user will only be authenticated if the tokeninfo "
                          "field matches the regexp. key/<regexp>/")},
            ACTION.SETREALM: {
                'type': 'str',
                'value': realms,
                'desc': _('The Realm of the user is set to this very realm. '
                          'This is important if the user is not contained in '
                          'the default realm and can not pass his realm.')},
            ACTION.NODETAILSUCCESS: {
                'type': 'bool',
                'desc': _('In case of successful authentication additional '
                          'no detail information will be returned.')},
            ACTION.NODETAILFAIL: {
                'type': 'bool',
                'desc': _('In case of failed authentication additional '
                          'no detail information will be returned.')},
            ACTION.ADDUSERINRESPONSE: {
                'type': 'bool',
                'desc': _('In case of successful authentication user data '
                          'will be added in the detail branch of the '
                          'authentication response.')},
            ACTION.ADDRESOLVERINRESPONSE: {
                'type': 'bool',
                'desc': _('In case of successful authentication the user resolver and '
                          'realm will be added in the detail branch of the '
                          'authentication response.')},
            ACTION.APIKEY: {
                'type': 'bool',
                'desc': _('The sending of an API Auth Key is required during'
                          'authentication. This avoids rogue authenticate '
                          'requests against the /validate/check interface.')
            }
        },

        SCOPE.WEBUI: {
            ACTION.LOGINMODE: {
                'type': 'str',
                'desc': _(
                    'If set to "privacyIDEA" the users and admins need to '
                    'authenticate against privacyIDEA when they log in '
                    'to the Web UI. Defaults to "userstore"'),
                'value': [LOGINMODE.USERSTORE, LOGINMODE.PRIVACYIDEA,
                          LOGINMODE.DISABLE],
            },
            ACTION.LOGIN_TEXT: {
                'type': 'str',
                'desc': _('An alternative text to display on the WebUI login dialog instead of "Please sign in".')
            },
            ACTION.SEARCH_ON_ENTER: {
                'type': 'bool',
                'desc': _('When searching in the user list, the search will '
                          'only performed when pressing enter.')
            },
            ACTION.TIMEOUT_ACTION: {
                'type': 'str',
                'desc': _('The action taken when a user is idle '
                          'beyond the logout_time limit. '
                          'Defaults to "lockscreen".'),
                'value': [TIMEOUT_ACTION.LOGOUT, TIMEOUT_ACTION.LOCKSCREEN],
            },
            ACTION.REMOTE_USER: {
                'type': 'str',
                'value': [REMOTE_USER.ACTIVE, REMOTE_USER.DISABLE],
                'desc': _('The REMOTE_USER set by the webserver can be used '
                          'to login to privacyIDEA or it will be ignored. '
                          'Defaults to "disable".')
            },
            ACTION.LOGOUTTIME: {
                'type': 'int',
                'desc': _("Set the time in seconds after which the user will "
                          "be logged out from the WebUI. Default: 120")
            },
            ACTION.TOKENPAGESIZE: {
                'type': 'int',
                'desc': _("Set how many tokens should be displayed in the "
                          "token view on one page.")
            },
            ACTION.USERPAGESIZE: {
                'type': 'int',
                'desc': _("Set how many users should be displayed in the user "
                          "view on one page.")
            },
            ACTION.CUSTOM_MENU: {
                'type': 'str',
                'desc': _("Use your own html template for the web UI menu.")
            },
            ACTION.CUSTOM_BASELINE: {
                'type': 'str',
                'desc': _("Use your own html template for the web UI baseline/footer.")
            },
            ACTION.USERDETAILS: {
                'type': 'bool',
                'desc': _("Whether the user ID and the resolver should be "
                          "displayed in the token list.")
            },
            ACTION.POLICYTEMPLATEURL: {
                'type': 'str',
                'desc': _("The URL of a repository, where the policy "
                          "templates can be found.  (Default "
                          "https: //raw.githubusercontent.com/ privacyidea/"
                          "policy-templates /master/templates/)")
            },
            ACTION.TOKENWIZARD: {
                'type': 'bool',
                'desc': _("As long as a user has no token, he will only see"
                          " a token wizard in the UI.")
            },
            ACTION.TOKENWIZARD2ND: {
                'type': 'bool',
                'desc': _("The tokenwizard will be displayed in the token "
                          "menu, even if the user already has a token.")
            },
            ACTION.DEFAULT_TOKENTYPE: {
                'type': 'str',
                'desc': _("This is the default token type in the token "
                          "enrollment dialog."),
                'value': get_token_types()
            },
            ACTION.REALMDROPDOWN: {
                'type': 'str',
                'desc': _("A list of realm names, which are "
                          "displayed in a drop down menu in the WebUI login "
                          "screen. Realms are separated by white spaces.")
            },
            ACTION.HIDE_WELCOME: {
                'type': 'bool',
                'desc': _("If this checked, the administrator will not see "
                          "the welcome dialog anymore.")
            },
            ACTION.HIDE_BUTTONS: {
                'type': 'bool',
                'desc': _("Per default disabled actions result in disabled buttons. When"
                          " checking this action, buttons of disabled actions are hidden.")
            },
            ACTION.SHOW_SEED: {
                'type': 'bool',
                'desc': _("If this is checked, the seed "
                          "will be displayed as text during enrollment.")
            }
        }


    }
    if scope:
        ret = pol.get(scope, {})
    else:
        ret = pol
    return ret


def get_action_values_from_options(scope, action, options):
    """
    This function is used in the library level to fetch policy action values
    from a given option dictionary.

    :return: A scalar, string or None
    """
    value = None
    g = options.get("g")
    if g:
        user_object = options.get("user")
        username = None
        realm = None
        if user_object:
            username = user_object.login
            realm = user_object.realm

        clientip = options.get("clientip")
        policy_object = g.policy_object
        value = policy_object. \
            get_action_values(action=action,
                              scope=scope,
                              realm=realm,
                              user=username,
                              client=clientip,
                              unique=True,
                              allow_white_space_in_action=True)
        if len(value) >= 1:
            return list(value)[0]
        else:
            return None

    return value
