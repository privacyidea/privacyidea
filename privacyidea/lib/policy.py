# -*- coding: utf-8 -*-
#
#  2021-09-06 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add extended condition for HTTP environment
#  2021-02-01 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add custom user attributes
#  2020-06-05 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add privacyIDEA nodes
#  2019-09-26 Friedrich Weber <friedrich.weber@netknights.it>
#             Add a high-level API for policy matching
#  2019-07-01 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add admin read policies
#  2019-06-19 Friedrich Weber <friedrich.weber@netknights.it>
#             Add handling of policy conditions
#  2019-05-25 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add max_active_token_per_user
#  2019-05-23 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add passthru_assign policy
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

.. note:: Regular expression will only work for exact matches.
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
Time formats are::

<dow>-<dow>:<hh>:<mm>-<hh>:<mm>, ...
<dow>:<hh>:<mm>-<hh>:<mm>
<dow>:<hh>-<hh>

and any combination of it. ``dow`` being day of week Mon, Tue, Wed, Thu, Fri,
Sat, Sun.
"""
from .log import log_with
from configobj import ConfigObj

from operator import itemgetter
import logging
from ..models import (Policy, db, save_config_timestamp, Token)
from privacyidea.lib.config import (get_token_classes, get_token_types,
                                    get_config_object, get_privacyidea_node,
                                    get_multichallenge_enrollable_tokentypes)
from privacyidea.lib.error import ParameterError, PolicyError, ResourceNotFoundError, ServerError
from privacyidea.lib.realm import get_realms
from privacyidea.lib.resolver import get_resolver_list
from privacyidea.lib.smtpserver import get_smtpservers
from privacyidea.lib.radiusserver import get_radiusservers
from privacyidea.lib.utils import (check_time_in_range, check_pin_contents,
                                   fetch_one_resource, is_true, check_ip_in_policy,
                                   determine_logged_in_userparams, parse_string_to_dict)
from privacyidea.lib.utils.compare import compare_values, COMPARATOR_DESCRIPTIONS
from privacyidea.lib.utils.export import (register_import, register_export)
from privacyidea.lib.user import User
from privacyidea.lib import _
from netaddr import AddrFormatError
from privacyidea.lib.error import privacyIDEAError
import datetime
import re
import ast
import traceback

log = logging.getLogger(__name__)

optional = True
required = False

DEFAULT_ANDROID_APP_URL = "https://play.google.com/store/apps/details?id=it.netknights.piauthenticator"
DEFAULT_IOS_APP_URL = "https://apps.apple.com/us/app/privacyidea-authenticator/id1445401301"
DEFAULT_PREFERRED_CLIENT_MODE_LIST = ['interactive', 'webauthn', 'poll', 'u2f']


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
    WEBUI = "webui"
    REGISTER = "register"


class ACTION(object):
    __doc__ = """This is the list of usual actions."""
    ADMIN_DASHBOARD = "admin_dashboard"
    ASSIGN = "assign"
    APPIMAGEURL = "appimageurl"
    APPLICATION_TOKENTYPE = "application_tokentype"
    AUDIT = "auditlog"
    AUDIT_AGE = "auditlog_age"
    AUDIT_DOWNLOAD = "auditlog_download"
    AUDITPAGESIZE = "audit_page_size"
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
    FORCE_APP_PIN = "force_app_pin"
    GETSERIAL = "getserial"
    GETRANDOM = "getrandom"
    HIDE_AUDIT_COLUMNS = "hide_audit_columns"
    IMPORT = "importtokens"
    LASTAUTH = "last_auth"
    LOGINMODE = "login_mode"
    LOGOUT_REDIRECT = "logout_redirect"
    LOGOUTTIME = "logout_time"
    LOSTTOKEN = 'losttoken'
    LOSTTOKENPWLEN = "losttoken_PW_length"
    LOSTTOKENPWCONTENTS = "losttoken_PW_contents"
    LOSTTOKENVALID = "losttoken_valid"
    MACHINERESOLVERWRITE = "mresolverwrite"
    MACHINERESOLVERDELETE = "mresolverdelete"
    MACHINERESOLVERREAD = "mresolverread"
    MACHINELIST = "machinelist"
    MACHINETOKENS = "manage_machine_tokens"
    MANGLE = "mangle"
    MAXTOKENREALM = "max_token_per_realm"
    MAXTOKENUSER = "max_token_per_user"
    MAXACTIVETOKENUSER = "max_active_token_per_user"
    NODETAILSUCCESS = "no_detail_on_success"
    ADDUSERINRESPONSE = "add_user_in_response"
    ADDRESOLVERINRESPONSE = "add_resolver_in_response"
    NODETAILFAIL = "no_detail_on_fail"
    OTPPIN = "otppin"
    OTPPINRANDOM = "otp_pin_random"
    OTPPINSETRANDOM = "otp_pin_set_random"
    OTPPINMAXLEN = 'otp_pin_maxlength'
    OTPPINMINLEN = 'otp_pin_minlength'
    OTPPINCONTENTS = 'otp_pin_contents'
    PASSNOTOKEN = "passOnNoToken"
    PASSNOUSER = "passOnNoUser"
    PASSTHRU = "passthru"
    PASSTHRU_ASSIGN = "passthru_assign"
    PASSWORDRESET = "password_reset"
    PINHANDLING = "pinhandling"
    POLICYDELETE = "policydelete"
    POLICYWRITE = "policywrite"
    POLICYREAD = "policyread"
    POLICYTEMPLATEURL = "policy_template_url"
    REALM = "realm"
    REGISTRATIONCODE_LENGTH = "registration.length"
    REGISTRATIONCODE_CONTENTS = "registration.contents"
    PASSWORD_LENGTH = "pw.length"  # nosec B105 # policy name
    PASSWORD_CONTENTS = "pw.contents"  # nosec B105 # policy name
    REMOTE_USER = "remote_user"
    REQUIREDEMAIL = "requiredemail"
    RESET = "reset"
    RESOLVERDELETE = "resolverdelete"
    RESOLVERWRITE = "resolverwrite"
    RESOLVERREAD = "resolverread"
    RESOLVER = "resolver"
    RESYNC = "resync"
    REVOKE = "revoke"
    SET = "set"
    SETDESCRIPTION = "setdescription"
    SETPIN = "setpin"
    SETRANDOMPIN = "setrandompin"
    SETREALM = "setrealm"
    SERIAL = "serial"
    SYSTEMDELETE = "configdelete"
    SYSTEMWRITE = "configwrite"
    SYSTEMREAD = "configread"
    CONFIGDOCUMENTATION = "system_documentation"
    SETTOKENINFO = "settokeninfo"
    TOKENISSUER = "tokenissuer"
    TOKENLABEL = "tokenlabel"
    TOKENLIST = "tokenlist"
    TOKENPAGESIZE = "token_page_size"
    TOKENREALMS = "tokenrealms"
    TOKENTYPE = "tokentype"
    TOKENINFO = "tokeninfo"
    HIDE_TOKENINFO = "hide_tokeninfo"
    TOKENWIZARD = "tokenwizard"
    TOKENWIZARD2ND = "tokenwizard_2nd_token"
    TOKENROLLOVER = "token_rollover"
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
    SMTPSERVERREAD = "smtpserver_read"
    RADIUSSERVERWRITE = "radiusserver_write"
    RADIUSSERVERREAD = "radiusserver_read"
    PRIVACYIDEASERVERWRITE = "privacyideaserver_write"
    PRIVACYIDEASERVERREAD = "privacyideaserver_read"
    REALMDROPDOWN = "realm_dropdown"
    EVENTHANDLINGWRITE = "eventhandling_write"
    EVENTHANDLINGREAD = "eventhandling_read"
    PERIODICTASKWRITE = "periodictask_write"
    PERIODICTASKREAD = "periodictask_read"
    SMSGATEWAYWRITE = "smsgateway_write"
    SMSGATEWAYREAD = "smsgateway_read"
    CHANGE_PIN_FIRST_USE = "change_pin_on_first_use"
    CHANGE_PIN_EVERY = "change_pin_every"
    CHANGE_PIN_VIA_VALIDATE = "change_pin_via_validate"
    RESYNC_VIA_MULTICHALLENGE = "resync_via_multichallenge"
    ENROLL_VIA_MULTICHALLENGE = "enroll_via_multichallenge"
    CLIENTTYPE = "clienttype"
    REGISTERBODY = "registration_body"
    RESETALLTOKENS = "reset_all_user_tokens"
    INCREASE_FAILCOUNTER_ON_CHALLENGE = "increase_failcounter_on_challenge"
    ENROLLPIN = "enrollpin"
    MANAGESUBSCRIPTION = "managesubscription"
    SEARCH_ON_ENTER = "search_on_enter"
    TIMEOUT_ACTION = "timeout_action"
    AUTH_CACHE = "auth_cache"
    DELETION_CONFIRMATION = "deletion_confirmation"
    HIDE_BUTTONS = "hide_buttons"
    HIDE_WELCOME = "hide_welcome_info"
    SHOW_SEED = "show_seed"
    CUSTOM_MENU = "custom_menu"
    CUSTOM_BASELINE = "custom_baseline"
    GDPR_LINK = "privacy_statement_link"
    STATISTICSREAD = "statistics_read"
    STATISTICSDELETE = "statistics_delete"
    LOGIN_TEXT = "login_text"
    DIALOG_NO_TOKEN = "dialog_no_token"  # nosec B105 # policy name
    SHOW_ANDROID_AUTHENTICATOR = "show_android_privacyidea_authenticator"
    SHOW_IOS_AUTHENTICATOR = "show_ios_privacyidea_authenticator"
    SHOW_CUSTOM_AUTHENTICATOR = "show_custom_authenticator"
    AUTHORIZED = "authorized"
    SHOW_NODE = "show_node"
    SET_USER_ATTRIBUTES = "set_custom_user_attributes"
    DELETE_USER_ATTRIBUTES = "delete_custom_user_attributes"
    VERIFY_ENROLLMENT = "verify_enrollment"
    TOKENGROUPS = "tokengroups"
    TOKENGROUP_LIST = "tokengroup_list"
    TOKENGROUP_ADD = "tokengroup_add"
    TOKENGROUP_DELETE = "tokengroup_delete"
    SERVICEID_LIST = "serviceid_list"
    SERVICEID_ADD = "serviceid_add"
    SERVICEID_DELETE = "serviceid_delete"
    PREFERREDCLIENTMODE = "preferred_client_mode"
    REQUIRE_DESCRIPTION = "require_description"


class TYPE(object):
    INT = "int"
    STRING = "str"
    BOOL = "bool"


class AUTHORIZED(object):
    ALLOW = "grant_access"
    DENY = "deny_access"


class GROUP(object):
    __doc__ = """These are the allowed policy action groups. The policies
    will be grouped in the UI."""
    TOOLS = "tools"
    SYSTEM = "system"
    TOKEN = "token"  # nosec B105 # group name
    ENROLLMENT = "enrollment"
    GENERAL = "general"
    MACHINE = "machine"
    USER = "user"
    PIN = "pin"
    MODIFYING_RESPONSE = "modifying response"
    CONDITIONS = "conditions"
    SETTING_ACTIONS = "setting actions"
    TOKENGROUP = "tokengroup"
    SERVICEID = "service ID"


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
    FORCE = "force"


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


class CONDITION_SECTION(object):
    __doc__ = """This is a list of available sections for conditions of policies """
    USERINFO = "userinfo"
    TOKENINFO = "tokeninfo"
    TOKEN = "token"  # nosec B105 # section name
    HTTP_REQUEST_HEADER = "HTTP Request header"
    HTTP_ENVIRONMENT = "HTTP Environment"


class CONDITION_CHECK(object):
    __doc__ = """The available check methods for extended conditions"""
    DO_NOT_CHECK_AT_ALL = 1
    ONLY_CHECK_USERINFO = [CONDITION_SECTION.USERINFO]
    CHECK_AND_RAISE_EXCEPTION_ON_MISSING = None


class PolicyClass(object):
    """
    A policy object can be used to query the current set of policies.
    The policy object itself does not store any policies.
    Instead, every query uses ``get_config_object`` to retrieve the request-local
    config object which contains the current set of policies.

    Hence, reloading the request-local config object also reloads the set of policies.
    """
    def __init__(self):
        pass

    @property
    def policies(self):
        """
        Shorthand to retrieve the set of policies of the request-local config object
        """
        return get_config_object().policies

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
                if re.search("^{0!s}$".format(value), searchvalue):
                    value_found = True

        return value_found, value_excluded

    @log_with(log)
    def list_policies(self, name=None, scope=None, realm=None, active=None,
                      resolver=None, user=None, client=None, action=None, pinode=None,
                      adminrealm=None, adminuser=None, sort_by_priority=True):
        """
        Return the policies, filtered by the given values.

        The following rule holds for all filter arguments:

        If ``None`` is passed as a value, policies are not filtered according to the
        argument at all. As an example, if ``realm=None`` is passed,
        policies are matched regardless of their ``realm`` attribute.
        If any value is passed (even the empty string), policies are filtered
        according to the given value. As an example, if ``realm=''`` is passed,
        only policies that have a matching (or empty) realm attribute are returned.

        The only exception is the ``client`` parameter, which does not accept the empty string,
        and throws a ParameterError if the empty string is passed.

        :param name: The name of the policy
        :param scope: The scope of the policy
        :param realm: The realm in the policy
        :param active: One of None, True, False: All policies, only active or only inactive policies
        :param resolver: Only policies with this resolver
        :param pinode: Only policies with this privacyIDEA node
        :param user: Only policies with this user
        :type user: basestring
        :param client:
        :param action: Only policies, that contain this very action.
        :param adminrealm: This is the realm of the admin. This is only
            evaluated in the scope admin.
        :param adminuser: This is the username of the admin. This in only
            evaluated in the scope admin.
        :param sort_by_priority: If true, sort the resulting list by priority, ascending
            by their policy numbers.
        :type sort_by_priority: bool
        :return: list of policies
        :rtype: list of dicts
        """
        reduced_policies = self.policies

        # Do exact matches for "name", "active" and "scope", as these fields
        # can only contain one entry
        p = [("name", name), ("active", active), ("scope", scope)]
        for searchkey, searchvalue in p:
            if searchvalue is not None:
                reduced_policies = [policy for policy in reduced_policies if
                                    policy.get(searchkey) == searchvalue]
                log.debug("Policies after matching {1!s}={2!s}: {0!s}".format(
                    reduced_policies, searchkey, searchvalue))

        p = [("action", action), ("user", user), ("realm", realm)]
        # If this is an admin-policy, we also do check the adminrealm
        if scope == SCOPE.ADMIN:
            p.append(("adminrealm", adminrealm))
            p.append(("adminuser", adminuser))
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
                log.debug("Policies after matching {1!s}={2!s}: {0!s}".format(
                    reduced_policies, searchkey, searchvalue))

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
            log.debug("Policies after matching resolver={1!s}: {0!s}".format(
                reduced_policies, resolver))

        # Match the privacyIDEA node
        if pinode is not None:
            new_policies = []
            for policy in reduced_policies:
                # The policy either matches if it has no pinode defined or if the pinode is contained in the list
                if not policy.get("pinode") or pinode in policy.get("pinode"):
                    new_policies.append(policy)

            reduced_policies = new_policies
            log.debug("Policies after matching pinode={1!s}: {0!s}".format(reduced_policies, pinode))

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
            if not client:
                raise ParameterError("client argument must be a non-empty string")

            new_policies = []
            for policy in reduced_policies:
                log.debug("checking client ip in policy {0!s}.".format(policy))
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
            log.debug("Policies after matching client={1!s}: {0!s}".format(
                reduced_policies, client))

        if sort_by_priority:
            reduced_policies = sorted(reduced_policies, key=itemgetter("priority"))

        return reduced_policies

    @log_with(log)
    def match_policies(self, name=None, scope=None, realm=None, active=None,
                       resolver=None, user=None, user_object=None, pinode=None,
                       client=None, action=None, adminrealm=None, adminuser=None, time=None,
                       sort_by_priority=True, audit_data=None, request_headers=None, serial=None,
                       extended_condition_check=None):
        """
        Return all policies matching the given context.
        Optionally, write the matching policies to the audit log.

        In order to retrieve policies matching the current user,
        callers can *either* pass a user(name), resolver and realm,
        *or* pass a user object from which login name, resolver and realm will be read.
        In case of conflicting parameters, a ParameterError will be raised.

        This function takes all parameters taken by ``list_policies``, plus
        some additional parameters.

        :param name: see ``list_policies``
        :param scope: see ``list_policies``
        :param realm: see ``list_policies``
        :param active: see ``list_policies``
        :param resolver: see ``list_policies``
        :param user: see ``list_policies``
        :param client: see ``list_policies``
        :param action: see ``list_policies``
        :param adminrealm: see ``list_policies``
        :param adminuser: see ``list_policies``
        :param pinode: see ``list_policies``
        :param sort_by_priority:
        :param user_object: the currently active user, or None
        :type user_object: User or None
        :param time: return only policies that are valid at the specified time.
            Defaults to the current time.
        :type time: datetime or None
        :param audit_data: A dictionary with audit data collected during a request. This
            method will add found policies to the dictionary.
        :type audit_data: dict or None
        :param request_headers: A dict with HTTP headers
        :return: a list of policy dictionaries
        """
        if user_object is not None:
            # if a user_object is passed, we check, if it differs from potentially passed user, resolver, realm:
            if (user and user.lower() not in {user_object.login.lower(), user_object.used_login.lower()}) \
                    or (resolver and resolver.lower() != user_object.resolver.lower()) \
                    or (realm and realm.lower() != user_object.realm):
                tb_str = ''.join(traceback.format_stack())
                log.warning("Cannot pass user_object as well as user, resolver, realm "
                            "in policy {0!s}. "
                            "{1!s} - {2!s}@{3!s} in resolver {4!s}".format((name, scope, action),
                                                                           user_object, user, realm, resolver))
                log.warning("Possible programming error: {0!s}".format(tb_str))
                raise ParameterError("Cannot pass user_object ({1!s}) as well as user ({2!s}),"
                                     " resolver ({3!s}), realm ({4!s})"
                                     "in policy {0!s}".format((name, scope, action), user_object,
                                                              user, resolver, realm))
            user = user_object.login
            realm = user_object.realm
            resolver = user_object.resolver

        reduced_policies = self.list_policies(name=name, scope=scope, realm=realm, active=active,
                                              resolver=resolver, user=user, client=client, action=action,
                                              adminrealm=adminrealm, adminuser=adminuser, pinode=pinode,
                                              sort_by_priority=sort_by_priority)

        # filter policy for time. If no time is set or is a time is set and
        # it matches the time_range, then we add this policy
        reduced_policies = [policy for policy in reduced_policies if
                            (policy.get("time") and
                             check_time_in_range(policy.get("time"), time))
                            or not policy.get("time")]
        log.debug("Policies after matching time: {0!s}".format([p.get("name") for p in reduced_policies]))

        # filter policies by the policy conditions
        if extended_condition_check != CONDITION_CHECK.DO_NOT_CHECK_AT_ALL:
            reduced_policies = self.filter_policies_by_conditions(reduced_policies, user_object, request_headers,
                                                                  serial, extended_condition_check)
            log.debug("Policies after matching conditions".format([p.get("name") for p in reduced_policies]))

        if audit_data is not None:
            for p in reduced_policies:
                audit_data.setdefault("policies", []).append(p.get("name"))

        return reduced_policies

    def filter_policies_by_conditions(self, policies, user_object=None, request_headers=None, serial=None,
                                      extended_condition_check=None):
        """
        Given a list of policy dictionaries and a current user object (if any),
        return a list of all policies whose conditions match the given user object.
        Raises a PolicyError if a condition references an unknown section.
        :param policies: a list of policy dictionaries
        :param user_object: a User object, or None if there is no current user
        :param request_headers: The HTTP headers
        :type request_headers: Request object
        :param extended_condition_check: A list of sections to check or None.
        :return: generates a list of policy dictionaries
        """
        reduced_policies = []
        # If we have several token specific conditions, we only create the db_token (query token DB) once.
        dbtoken = None
        for policy in policies:
            include_policy = True
            for section, key, comparator, value, active in policy['conditions']:
                if (extended_condition_check is CONDITION_CHECK.CHECK_AND_RAISE_EXCEPTION_ON_MISSING
                        or section in extended_condition_check):
                    # We check conditions, either if we are supposed to check everything or if
                    # the section is contained in the extended condition check
                    if active:
                        if section == CONDITION_SECTION.USERINFO:
                            if not self._policy_matches_info_condition(policy, key, comparator, value,
                                                                       CONDITION_SECTION.USERINFO,
                                                                       user_object=user_object):
                                include_policy = False
                                break
                        elif section == CONDITION_SECTION.TOKENINFO:
                            dbtoken = dbtoken or Token.query.filter(Token.serial == serial).first() if serial else None
                            if not self._policy_matches_info_condition(policy, key, comparator, value,
                                                                       CONDITION_SECTION.TOKENINFO,
                                                                       dbtoken=dbtoken):
                                include_policy = False
                                break
                        elif section == CONDITION_SECTION.TOKEN:
                            dbtoken = dbtoken or Token.query.filter(Token.serial == serial).first() if serial else None
                            if not self._policy_matches_token_condition(policy, key, comparator, value, dbtoken):
                                include_policy = False
                                break
                        elif section == CONDITION_SECTION.HTTP_REQUEST_HEADER:
                            if not self._policy_matches_request_header_condition(policy, key, comparator, value,
                                                                                 request_headers):
                                include_policy = False
                                break
                        elif section == CONDITION_SECTION.HTTP_ENVIRONMENT:
                            if not self._policy_matches_request_environ_condition(policy, key, comparator, value,
                                                                                 request_headers):
                                include_policy = False
                                break
                        else:
                            log.warning("Policy {!r} has condition with unknown section: {!r}".format(
                                policy['name'], section
                            ))
                            raise PolicyError("Policy {!r} has condition with unknown section".format(policy['name']))
            if include_policy:
                reduced_policies.append(policy)
        return reduced_policies

    @staticmethod
    def _policy_matches_request_environ_condition(policy, key, comparator, value, request_headers):
        """
        :param request_headers: Request Header object
        :type request_headers: Can be accessed using .get()
        """
        # Now we check the HTTP request headers
        if request_headers is not None:
            request_environ = request_headers.environ
            if request_environ.get(key):
                try:
                    environ_value = request_environ.get(key)
                    return compare_values(environ_value, comparator, value)
                except Exception as exx:
                    log.warning("Error during handling the condition on HTTP environment {!r} "
                                "of policy {!r}: {!r}".format(key, policy['name'], exx))
                    raise PolicyError(
                        "Invalid comparison in the HTTP environment conditions of policy {!r}".format(policy['name']))
            else:
                log.warning("Unknown HTTP environment key referenced in condition of policy "
                            "{!r}: {!r}".format(policy["name"], key))
                log.warning("Available HTTP environment: {!r}".format(request_environ))
                raise PolicyError("Unknown HTTP environment key referenced in condition of policy "
                                  "{!r}: {!r}".format(policy["name"], key))
        else:  # pragma: no cover
            log.error("Policy {!r} has conditions on HTTP environment, but HTTP environment"
                      " is not available. This should not happen - possible "
                      "programming error {!s}.".format(policy["name"],
                                                        ''.join(traceback.format_stack())))
            raise PolicyError("Policy {!r} has conditions on environment {!r}, but HTTP environment"
                              " is not available".format(policy["name"], key))

    @staticmethod
    def _policy_matches_request_header_condition(policy, key, comparator, value, request_headers):
        """
        :param request_headers: Request Header object
        :type request_headers: Can be accessed using .get()
        """
        # Now we check the HTTP request headers
        if request_headers is not None:
            if request_headers.get(key):
                try:
                    header_value = request_headers.get(key)
                    return compare_values(header_value, comparator, value)
                except Exception as exx:
                    log.warning("Error during handling the condition on HTTP header {!r} of policy {!r}: {!r}".format(
                        key, policy['name'], exx
                    ))
                    raise PolicyError(
                        "Invalid comparison in the HTTP header conditions of policy {!r}".format(policy['name']))
            else:
                log.warning("Unknown HTTP header key referenced in condition of policy "
                            "{!r}: {!r}".format(policy["name"], key))
                log.warning("Available HTTP headers: {!r}".format(request_headers))
                raise PolicyError("Unknown HTTP header key referenced in condition of policy "
                                  "{!r}: {!r}".format(policy["name"], key))
        else:  # pragma: no cover
            log.error("Policy {!r} has conditions on HTTP headers, but HTTP header"
                      " is not available. This should not happen - possible "
                      "programming error {!s}.".format(policy["name"],
                                                        ''.join(traceback.format_stack())))
            raise PolicyError("Policy {!r} has conditions on headers {!r}, but HTTP header"
                              " is not available".format(policy["name"], key))

    @staticmethod
    def _policy_matches_token_condition(policy, key, comparator, value, db_token):
        """
        This extended policy checks for token attributes, which are existing columns in
        the token DB table.

        :param policy: a policy dictionary, the policy in question
        :param key: the column name of the token
        :param comparator: a value comparator: one of "equal", "contains"
        :param value: a value against which the token value will be compared
        :param db_token: a dbtoken object
        :return: bool
        """
        if db_token:
            if key in db_token.get():
                try:
                    return compare_values(db_token.get(key), comparator, value)
                except Exception as exx:
                    log.warning("Error during handling the condition on token {!r} "
                                "of policy {!r}: {!r}".format(key, policy['name'], exx))
                    raise PolicyError("Invalid comparison in the 'token' "
                                      "conditions of policy {!r}".format(policy['name']))
            else:
                log.warning("Unknown token column referenced in a "
                            "condition of policy {!r}: {!r}".format(policy['name'], key))
                # If we do have token object but the referenced key is not an attribute of the token,
                # we have a misconfiguration and raise an error.
                raise PolicyError("Unknown key in the token conditions of policy {!r}".format(policy['name']))
        else:  # pragma: no cover
            log.error("Policy {!r} has conditions on tokens, but a token object"
                      " is not available. This should not happen - possible programming "
                      "error: {!s}.".format(policy["name"], ''.join(traceback.format_stack())))
            raise PolicyError("Policy {!r} has conditions on tokens, but a token object"
                              " is not available".format(policy["name"]))

    @staticmethod
    def _policy_matches_info_condition(policy, key, comparator, value, type, user_object=None, dbtoken=None):
        """
        Check if the given policy matches a certain userinfo or tokeninfo condition depending
        on the specified ``type``.
        For the userinfo, if ``user_object`` is None or the requested ``key`` is not contained,
        a PolicyError is raised.
        In case of a tokeninfo, no exception is raised if ``dbtoken`` is malformed. Instead, the
        condition is effectively set to True and the policy may apply.
        :param policy: a policy dictionary, the policy in question
        :param key: a tokeninfo or userinfo key
        :param comparator: a value comparator: one of "equal", "contains"
        :param value: a value against which the tokeninfo or userinfo value will be compared
        :param type: the info type to match, "userinfo" or "tokeninfo"
        :param user_object: a User object, if any, or None
        :param dbtoken: a dbtoken object, if any, or None
        :return: a Boolean
        """
        if user_object is not None or dbtoken is not None:
            info = user_object.info if user_object is not None else dbtoken.get_info()

            if key in info:
                try:
                    return compare_values(info[key], comparator, value)
                except Exception as exx:
                    log.warning("Error during handling the condition on {!s} {!r} of policy {!r}: {!r}".format(
                        type, key, policy['name'], exx
                    ))
                    raise PolicyError(
                        "Invalid comparison in the {!s} conditions of policy {!r}".format(type, policy['name']))
            else:
                log.warning("Unknown {!s} key referenced in a condition of policy {!r}: {!r}".format(
                    type, policy['name'], key
                ))
                # If we do have an user or token object, but the conditions of policies reference
                # an unknown userinfo or tokeninfo key, we have a misconfiguration and raise an error.
                raise PolicyError("Unknown key in the {!s} conditions of policy {!r}".format(
                    type, policy['name']
                ))
        else:
            log.error("Policy {!r} has condition on {!s}, but the according object"
                      " is not available - possible programming error "
                      "{!s}.".format(policy['name'], type, ''.join(traceback.format_stack())))
            # If the policy specifies a userinfo or tokeninfo condition, but no object is available,
            # the policy is misconfigured. We have to raise a PolicyError to ensure that
            # the privacyIDEA server does not silently misbehave.
            raise PolicyError(
                "Policy {!r} has condition on {!s}, but an according object is not available".format(
                    policy['name'], type
                ))

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

    @staticmethod
    def extract_action_values(policies, action, unique=False, allow_white_space_in_action=False):
        """
        Given an action, extract all values the given policies specify for that action.

        :param policies: a list of policy dictionaries
        :type policies: list
        :param action: a policy action
        :type action: action
        :param unique: if True, only consider the policy with the highest priority
                       and check for policy conflicts (in this case, raise a PolicyError).
        :type unique: bool
        :param allow_white_space_in_action: Some policies like emailtext
            would allow entering text with whitespaces. These whitespaces
            must not be used to separate action values!
        :return: a dictionary mapping action values to lists of matching policies.
        """
        policy_values = {}
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
            raise PolicyError("There are policies with conflicting actions: {!r}".format(names))
        return policy_values

    @log_with(log)
    def get_action_values(self, action, scope=SCOPE.AUTHZ, realm=None,
                          resolver=None, user=None, client=None, unique=False,
                          allow_white_space_in_action=False, adminrealm=None, adminuser=None,
                          user_object=None, audit_data=None):
        """
        Get the defined action values for a certain actions.

        Calling the function with parameters like::

            scope: authorization
            action: tokentype

        would return a dictionary of ``{tokentype: policyname}``.

        A call with the parameters::

            scope: authorization
            action: serial

        would return a dictionary of ``{serial: policyname}``

        All parameters not described below are covered in the documentation of ``match_policies``.

        :param unique: if set, the function will only consider the policy with the
            highest priority and check for policy conflicts.
        :param allow_white_space_in_action: Some policies like emailtext
            would allow entering text with whitespaces. These whitespaces
            must not be used to separate action values!
        :type allow_white_space_in_action: bool
        :param audit_data: This is a dictionary, that can take audit_data in the g object.
            If set, this dictionary will be filled with the list of triggered policynames in the
            key "policies". This can be useful for policies like ACTION.OTPPIN - where it is clear, that the
            found policy will be used. It could make less sense with an action like ACTION.LASTAUTH - where
            the value of the action needs to be evaluated in a more special case.
        :rtype: dict
        """
        policies = self.match_policies(scope=scope, adminrealm=adminrealm, adminuser=adminuser,
                                       action=action, active=True,
                                       realm=realm, resolver=resolver, user=user, user_object=user_object,
                                       client=client, sort_by_priority=True)
        policy_values = self.extract_action_values(policies, action,
                                                   unique=unique,
                                                   allow_white_space_in_action=allow_white_space_in_action)

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
        from privacyidea.lib.token import get_dynamic_policy_definitions
        rights = set()
        if scope == SCOPE.ADMIN:
            # If the logged-in user is an admin, we match for username/adminrealm only
            admin_user = username
            admin_realm = realm
            user_object = None
            # During login of the admin there is no token, no tokeninfo and no user info available.
            # Also, the http header is only passed down to the policy Match-class, but not in the get_rights method.
            # Thus we can not check any extended conditions for admins at this point.
            extended_condition_check = CONDITION_CHECK.DO_NOT_CHECK_AT_ALL
        elif scope == SCOPE.USER:
            admin_user = None
            admin_realm = None
            # If the logged-in user is a user, we pass a user object to allow matching for userinfo attributes
            user_object = User(username, realm)
            # During login of the admin there is no token and no tokeninfo available.
            # Also, the http header is only passed down to the policy Match-class, but not in the get_rights method.
            # Thus we can only check the extended condition "userinfo" for users at this point.
            extended_condition_check = CONDITION_CHECK.ONLY_CHECK_USERINFO
        else:
            raise PolicyError("Unknown scope: {}".format(scope))
        pols = self.match_policies(scope=scope,
                                   user_object=user_object,
                                   adminrealm=admin_realm,
                                   adminuser=admin_user,
                                   active=True,
                                   client=client,
                                   extended_condition_check=extended_condition_check)
        for pol in pols:
            for action, action_value in pol.get("action").items():
                if action_value:
                    rights.add(action)
                    # if the action has an actual non-boolean value, return it
                    if isinstance(action_value, str):
                        rights.add("{}={}".format(action, action_value))
        # check if we have policies at all:
        pols = self.list_policies(scope=scope, active=True)
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
        enroll_types = {}
        # In this case we do not distinguish the userobject as for whom an administrator would enroll a token
        # We simply want to know, which tokentypes a user or an admin in generally allowed to enroll. This is
        # why we pass an empty params.
        (role, username, userrealm, adminuser, adminrealm) = determine_logged_in_userparams(logged_in_user, {})
        user_object = None
        if username and userrealm:
            # We need a user_object to do user-attribute specific policy matching
            user_object = User(username, userrealm)
        # check, if we have a policy definition at all.
        pols = self.list_policies(scope=role, active=True)
        tokenclasses = get_token_classes()
        for tokenclass in tokenclasses:
            # Check if the tokenclass is ui enrollable for "user" or "admin"
            if role in tokenclass.get_class_info("ui_enroll"):
                enroll_types[tokenclass.get_class_type()] = \
                    tokenclass.get_class_info("description")

        if role == SCOPE.ADMIN:
            extended_condition_check = CONDITION_CHECK.DO_NOT_CHECK_AT_ALL
        else:
            extended_condition_check = CONDITION_CHECK.ONLY_CHECK_USERINFO
        if pols:
            # admin policies or user policies are set, so we need to
            # test, which tokens are allowed to be enrolled for this user
            filtered_enroll_types = {}
            for tokentype in enroll_types.keys():
                # determine, if there is a enrollment policy for this very type
                typepols = self.match_policies(scope=role, client=client,
                                               user=username,
                                               realm=userrealm,
                                               user_object=user_object,
                                               active=True,
                                               action="enroll"+tokentype.upper(),
                                               adminrealm=adminrealm,
                                               adminuser=adminuser,
                                               extended_condition_check=extended_condition_check)
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
               adminrealm=None, adminuser=None, priority=None, check_all_resolvers=False,
               conditions=None, pinode=None):
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
    :param adminrealm: The name of the realm of administrators
    :type adminrealm: str
    :param adminuser: A comma separated list of administrators
    :type adminuser: str
    :param priority: the priority of the policy (smaller values having higher priority)
    :type priority: int
    :param check_all_resolvers: If all the resolvers of a user should be
        checked with this policy
    :type check_all_resolvers: bool
    :param conditions: A list of 5-tuples (section, key, comparator, value, active) of policy conditions
    :param pinode: A privacyIDEA node or a list of privacyIDEA nodes.
    :return: The database ID od the the policy
    :rtype: int
    """
    active = is_true(active)
    if isinstance(priority, str):
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
    if type(adminuser) == list:
        adminuser = ", ".join(adminuser)
    if type(resolver) == list:
        resolver = ", ".join(resolver)
    if type(client) == list:
        client = ", ".join(client)
    if client is not None:
        try:
            check_ip_in_policy("127.0.0.1", [c.strip() for c in client.split(",")])
        except AddrFormatError:
            raise privacyIDEAError(_("Invalid client definition!"), id=302)
    if type(pinode) == list:
        pinode = ", ".join(pinode)
    # validate conditions parameter
    if conditions is not None:
        for condition in conditions:
            if len(condition) != 5:
                raise ParameterError("Conditions must be 5-tuples: {!r}".format(condition))
            if not (isinstance(condition[0], str)
                    and isinstance(condition[1], str)
                    and isinstance(condition[2], str)
                    and isinstance(condition[3], str)
                    and isinstance(condition[4], bool)):
                raise ParameterError("Conditions must be 5-tuples of four strings and one boolean: {!r}".format(
                    condition))
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
        if adminuser is not None:
            p1.adminuser = adminuser
        if client is not None:
            p1.client = client
        if time is not None:
            p1.time = time
        if priority is not None:
            p1.priority = priority
        if pinode is not None:
            p1.pinode = pinode
        p1.active = active
        p1.check_all_resolvers = check_all_resolvers
        if conditions is not None:
            p1.set_conditions(conditions)
        save_config_timestamp()
        db.session.commit()
        ret = p1.id
    else:
        # Create a new policy
        ret = Policy(name, action=action, scope=scope, realm=realm,
                     user=user, time=time, client=client, active=active,
                     resolver=resolver, adminrealm=adminrealm,
                     adminuser=adminuser, priority=priority,
                     check_all_resolvers=check_all_resolvers,
                     conditions=conditions, pinode=pinode).save()
    return ret


@log_with(log)
def enable_policy(name, enable=True):
    """
    Enable or disable the policy with the given name
    :param name:
    :return: ID of the policy
    """
    if not Policy.query.filter(Policy.name == name).first():
        raise ResourceNotFoundError("The policy with name '{0!s}' does not exist".format(name))

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

    The file has a ``config_object`` format, i.e. the text file has a header::

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
                         pinode=ast.literal_eval(policy.get("pinode", "[]")),
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
                                            "email. Use '{regkey}' as tag "
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
            ACTION.SETDESCRIPTION: {'type': 'bool',
                                    'desc': _('The admin is allowed to set the token description.'),
                                    'mainmenu': [MAIN_MENU.TOKENS],
                                    'group': GROUP.TOKEN},
            ACTION.SETPIN: {'type': 'bool',
                            'desc': _(
                                'Admin is allowed to set the OTP PIN of '
                                'tokens.'),
                            'mainmenu': [MAIN_MENU.TOKENS],
                            'group': GROUP.TOKEN},
            ACTION.SETRANDOMPIN: {'type': 'bool',
                                  'desc': _('Admin is allowed to set a random OTP PIN of tokens.'),
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
            ACTION.REVOKE: {'type': 'bool',
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
                                  'a user, i.e. unassign a token.'),
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
            ACTION.TOKENLIST: {'type': 'bool',
                               'desc': _('Admin is allowed to list tokens.'),
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
                                      'one token to another token.'),
                                  "group": GROUP.TOOLS},
            ACTION.COPYTOKENUSER: {'type': 'bool',
                                   'desc': _(
                                       'Admin is allowed to copy the assigned '
                                       'user to another token, i.e. assign a user to '
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
            ACTION.SYSTEMREAD: {'type': 'bool',
                                "desc": _("Admin is allowed to read "
                                          "basic system configuration."),
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
            ACTION.POLICYREAD: {'type': 'bool',
                                'desc': _("Admin is allowed to read policies."),
                                'group': GROUP.SYSTEM,
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
            ACTION.RESOLVERREAD: {'type': 'bool',
                                   'desc': _("Admin is allowed to read resolvers."),
                                   'group': GROUP.SYSTEM,
                                '   mainmenu': [MAIN_MENU.CONFIG]},
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
            ACTION.CACONNECTORREAD: {'type': 'bool',
                                     "desc": _("Admin is allowed to read CA Connector "
                                               "definitions."),
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
            ACTION.MACHINERESOLVERREAD: {'type': 'bool',
                                         'desc': _("Admin is allowed to "
                                                   "read "
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
                                              "(s)pecial. Use modifiers +/- or a list "
                                              "of allowed characters [1234567890]"),
                                    'group': GROUP.PIN},
            ACTION.OTPPINSETRANDOM: {
                'type': 'int',
                'value': list(range(1, 32)),
                'desc': _("The length of a random PIN set by the administrator."),
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
            ACTION.HIDE_AUDIT_COLUMNS: {'type': 'str',
                                        "desc": _("The admin will not see the specified columns "
                                                  "in the audit."),
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
            ACTION.SMTPSERVERREAD: {'type': 'bool',
                                    'desc': _("Admin is allowed to read "
                                              "SMTP server definitions."),
                                    'mainmenu': [MAIN_MENU.CONFIG],
                                    'group': GROUP.SYSTEM},
            ACTION.RADIUSSERVERWRITE: {'type': 'bool',
                                       'desc': _("Admin is allowed to write "
                                                 "new RADIUS server "
                                                 "definitions."),
                                       'mainmenu': [MAIN_MENU.CONFIG],
                                       'group': GROUP.SYSTEM},
            ACTION.RADIUSSERVERREAD: {'type': 'bool',
                                      'desc': _("Admin is allowed to read "
                                                "RADIUS server definitions."),
                                      'mainmenu': [MAIN_MENU.CONFIG],
                                      'group': GROUP.SYSTEM},
            ACTION.PRIVACYIDEASERVERWRITE: {'type': 'bool',
                                            'desc': _("Admin is allowed to "
                                                      "write remote "
                                                      "privacyIDEA server "
                                                      "definitions."),
                                            'mainmenu': [MAIN_MENU.CONFIG],
                                            'group': GROUP.SYSTEM},
            ACTION.PRIVACYIDEASERVERREAD: {'type': 'bool',
                                           'desc': _("Admin is allowed to "
                                                     "read remote "
                                                     "privacyIDEA server "
                                                     "definitions."),
                                           'mainmenu': [MAIN_MENU.CONFIG],
                                           'group': GROUP.SYSTEM},
            ACTION.PERIODICTASKWRITE: {'type': 'bool',
                                       'desc': _("Admin is allowed to write "
                                                 "periodic task definitions."),
                                            'mainmenu': [MAIN_MENU.CONFIG],
                                            'group': GROUP.SYSTEM},
            ACTION.PERIODICTASKREAD: {'type': 'bool',
                                      'desc': _("Admin is allowed to read "
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
            ACTION.EVENTHANDLINGREAD: {'type': 'bool',
                                       'desc': _("Admin is allowed to read event "
                                                 "handling configuration."),
                                       'mainmenu': [MAIN_MENU.CONFIG],
                                       'group': GROUP.SYSTEM},
            ACTION.SMSGATEWAYWRITE: {'type': 'bool',
                                     'desc': _("Admin is allowed to write "
                                               "and modify SMS gateway "
                                               "definitions."),
                                     'mainmenu': [MAIN_MENU.CONFIG],
                                     'group': GROUP.SYSTEM},
            ACTION.SMSGATEWAYREAD: {'type': 'bool',
                                    'desc': _("Admin is allowed to read "
                                              "SMS gateway definitions."),
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
                'group': GROUP.GENERAL},
            ACTION.SET_USER_ATTRIBUTES: {
                'type': TYPE.STRING,
                'desc': _("The Admin is allowed to set certain custom user "
                          "attributes. If the Admin should be allowed to set any "
                          "attribute, set this to '*:*'. For more details, check "
                          "the documentation."),
                'mainmenu': [],
                'group': GROUP.USER},
            ACTION.DELETE_USER_ATTRIBUTES: {
                'type': TYPE.STRING,
                'desc': _("The Admin is allowed to delete certain custom user "
                          "attributes. If the Admin should be allowed to delete any "
                          "attribute, set this to '*'. For more details, check "
                          "the documentation."),
                'mainmenu': [],
                'group': GROUP.USER},
            ACTION.HIDE_TOKENINFO: {
                'type': TYPE.STRING,
                'desc': _('A whitespace-separated list of tokeninfo fields '
                          'which are not displayed to the admin.'),
                'group': GROUP.TOKEN},
            ACTION.TOKENGROUP_LIST: {
                'type': 'bool',
                'desc': _("The Admin is allowed list the available tokengroups."),
                'mainmenu': [MAIN_MENU.CONFIG],
                'group': GROUP.TOKENGROUP},
            ACTION.TOKENGROUP_ADD: {
                'type': 'bool',
                'desc': _("The Admin is allowed to add a new tokengroup."),
                'mainmenu': [MAIN_MENU.CONFIG],
                'group': GROUP.TOKENGROUP},
            ACTION.TOKENGROUP_DELETE: {
                'type': 'bool',
                'desc': _("The Admin is allowed delete a tokengroup."),
                'mainmenu': [MAIN_MENU.CONFIG],
                'group': GROUP.TOKENGROUP},
            ACTION.SERVICEID_LIST: {
                'type': 'bool',
                'desc': _("The Admin is allowed list the available service ID definitions."),
                'mainmenu': [MAIN_MENU.CONFIG],
                'group': GROUP.SERVICEID},
            ACTION.SERVICEID_ADD: {
                'type': 'bool',
                'desc': _("The Admin is allowed to add a new service ID definition."),
                'mainmenu': [MAIN_MENU.CONFIG],
                'group': GROUP.SERVICEID},
            ACTION.SERVICEID_DELETE: {
                'type': 'bool',
                'desc': _("The Admin is allowed delete a service ID definition."),
                'mainmenu': [MAIN_MENU.CONFIG],
                'group': GROUP.SERVICEID},
            ACTION.TOKENGROUPS: {
                'type': 'bool',
                'desc': _("The Admin is allowed to manage the tokengroups of a token."),
                'group': GROUP.TOKEN},
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
            ACTION.SETRANDOMPIN: {'type': 'bool',
                                  'desc': _('The user is allowed to set a random OTP PIN of his tokens.'),
                                  'mainmenu': [MAIN_MENU.TOKENS],
                                  'group': GROUP.PIN},
            ACTION.OTPPINSETRANDOM: {'type': 'int',
                                     'value': list(range(1, 32)),
                                     'desc': _("The length of a random PIN set by the user."),
                                     'group': GROUP.PIN},
            ACTION.SETDESCRIPTION: {'type': 'bool',
                                    'desc': _('The user is allowed to set the token description.'),
                                    'mainmenu': [MAIN_MENU.TOKENS],
                                    'group': GROUP.TOKEN},
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
                                              "(s)pecial. Use modifiers +/- or a list "
                                              "of allowed characters [1234567890]"),
                                    'group': GROUP.PIN},

            ACTION.AUDIT: {
                'type': 'bool',
                'desc': _('Allow the user to view his own token history.'),
                'mainmenu': [MAIN_MENU.AUDIT]},
            ACTION.AUDIT_AGE: {'type': 'str',
                               "desc": _("The user will only see audit "
                                         "entries of the last 10d, 3m or 2y."),
                               'mainmenu': [MAIN_MENU.AUDIT]},
            ACTION.HIDE_AUDIT_COLUMNS: {'type': 'str',
                                        "desc": _("The user will not see the specified columns "
                                                  "in the audit."),
                                        "group": GROUP.SYSTEM,
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
                                   'mainmenu': []},
            ACTION.SET_USER_ATTRIBUTES: {
                'type': TYPE.STRING,
                'desc': _("The user is allowed to set certain custom user "
                          "attributes. If the user should be allowed to set any "
                          "attribute, set this to '*:*'. Use '*' with CAUTION! "
                          "For more details, check the documentation."),
                'mainmenu': [],
                'group': GROUP.USER},
            ACTION.DELETE_USER_ATTRIBUTES: {
                'type': TYPE.STRING,
                'desc': _("The user is allowed to delete certain custom user "
                          "attributes. If the user should be allowed to delete any "
                          "attribute, set this to '*'. Use '*' with CAUTION! "
                          "For more details, check the documentation."),
                'mainmenu': [],
                'group': GROUP.USER},
            ACTION.HIDE_TOKENINFO: {
                'type': TYPE.STRING,
                'desc': _('A whitespace-separated list of tokeninfo fields '
                          'which are not displayed to the user.'),
                'group': GROUP.TOKEN
            }
        },
        SCOPE.ENROLL: {
            ACTION.MAXTOKENREALM: {
                'type': 'int',
                'desc': _('Limit the number of allowed tokens in a realm.'),
                'group': GROUP.TOKEN},
            ACTION.REQUIRE_DESCRIPTION: {
                'type': 'str',
                'desc': _('During the rollout process, this policy makes the '
                          'description required for all selected tokentypes.'),
                'group': GROUP.ENROLLMENT,
                'multiple': True,
                'value': get_token_types()},

            ACTION.MAXTOKENUSER: {
                'type': 'int',
                'desc': _('Limit the number of tokens a user may have '
                          'assigned.'),
                'group': GROUP.TOKEN},
            ACTION.MAXACTIVETOKENUSER: {
                'type': 'int',
                'desc': _('Limit the number of active tokens a user may have assigned.'),
                'group': GROUP.TOKEN},
            ACTION.OTPPINRANDOM: {
                'type': 'int',
                'value': list(range(1, 32)),
                "desc": _("Set a random OTP PIN with this length for a "
                          "token during the enrollment process."),
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
                'desc': _("The label for a new enrolled Smartphone token. "
                          "Possible tags are <code>{user}</code>, <code>{realm}</code>, "
                          "<code>{serial}</code>, <code>{givenname}</code> and <code>{surname}</code>."),
                'group': GROUP.TOKEN},
            ACTION.TOKENISSUER: {
                'type': 'str',
                'desc': _("The issuer label for new enrolled Smartphone token."
                          "Possible tags are <code>{user}</code>, <code>{realm}</code>, "
                          "<code>{serial}</code>, <code>{givenname}</code> and <code>{surname}</code>."),
                'group': GROUP.TOKEN
            },
            ACTION.APPIMAGEURL: {
                'type': 'str',
                'desc': _("This is the URL to the token image for the privacyIDEA Authenticator "
                          "and some other apps like FreeOTP (supported file formats: PNG, JPG and GIF)."),
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
            ACTION.REGISTRATIONCODE_LENGTH: {
                'type': 'int',
                'value': list(range(1, 32)),
                "desc": _("Set the length of registration codes."),
                'group': GROUP.TOKEN},
            ACTION.REGISTRATIONCODE_CONTENTS: {
                'type': 'str',
                "desc": _("Specify the required "
                          "contents of the registration code. "
                          "(c)haracters, (n)umeric, "
                          "(s)pecial. Use modifiers +/- or a list "
                          "of allowed characters [1234567890]"),
                'group': GROUP.TOKEN},
            ACTION.PASSWORD_LENGTH: {
                'type': 'int',
                'value': list(range(1, 32)),
                "desc": _("Set the length of the password of generated password tokens."),
                'group': GROUP.TOKEN},
            ACTION.PASSWORD_CONTENTS: {
                'type': 'str',
                "desc": _("Specify the required "
                          "contents of the password of a password token. "
                          "(c)haracters, (n)umeric, "
                          "(s)pecial. Use modifiers +/- or a list "
                          "of allowed characters [1234567890]"),
                'group': GROUP.TOKEN},
            ACTION.VERIFY_ENROLLMENT: {
                'type': 'str',
                'desc': _("Specify a white space separated list of token types, "
                          "that should be verified during enrollment."),
                'group': GROUP.TOKEN}
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
                          'that can be used with challenge response.'),
                'multiple': True,
                'value': [token_obj.get_class_type() for token_obj in get_token_classes() if "challenge" in token_obj.mode and len(token_obj.mode) > 1]
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
            ACTION.CHANGE_PIN_VIA_VALIDATE: {
                'type': 'bool',
                'desc': _("If the PIN of a token is to be changed, this will allow the user to change the "
                          "PIN during a validate/check request via challenge / response."),
            },
            ACTION.RESYNC_VIA_MULTICHALLENGE: {
                'type': 'bool',
                'desc': _("The autoresync of a token can be done via a challenge response message."
                          "You need to activate 'Automatic resync' in the general settings!"),
            },
            ACTION.ENROLL_VIA_MULTICHALLENGE: {
                'type': 'str',
                'desc': _("In case of a successful authentication the following tokentype is enrolled. The "
                          "maximum number of tokens for a user is checked."),
                'value': [t.upper() for t in get_multichallenge_enrollable_tokentypes()]
            },
            ACTION.PASSTHRU: {
                'type': 'str',
                'value': radiusconfigs,
                'desc': _('If set, the user in this realm will be '
                          'authenticated against the userstore or against the '
                          'given RADIUS config,'
                          ' if the user has no tokens assigned.')
            },
            ACTION.PASSTHRU_ASSIGN: {
                'type': 'str',
                'desc': _('This allows to automatically assign a Token within privacyIDEA, if the '
                          'user was authenticated via passthru against a RADIUS server. The OTP value '
                          'is used to find the unassigned token in privacyIDEA. Enter the length of the OTP value '
                          'and where the PIN is set like 8:pin or pin:6.')
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
            ACTION.INCREASE_FAILCOUNTER_ON_CHALLENGE: {
                'type': 'bool',
                'desc': _('Increase the failcounter for all the tokens, for which a challenge has been triggered.')
            },
            ACTION.AUTH_CACHE: {
                'type': 'str',
                'desc': _('Cache the password used for authentication and '
                          'allow authentication with the same credentials for a '
                          'certain amount of time. '
                          'Specify timeout like 4h or 4h/5m.')
            },
            ACTION.PREFERREDCLIENTMODE: {
                'type': 'str',
                'desc': _('You can set the client modes in the order that you prefer. '
                          'For example: "interactive webauthn poll u2f". Accepted '
                          'values are: <code>interactive webauthn poll u2f</code>')
            }
        },
        SCOPE.AUTHZ: {
            ACTION.AUTHORIZED: {
                'type': 'str',
                'desc': _("Allow the user to authenticate (default). If set to '{0!s}', "
                          "the authentication of the user will be denied.").format(AUTHORIZED.DENY),
                'value': [AUTHORIZED.ALLOW, AUTHORIZED.DENY],
                'group': GROUP.MODIFYING_RESPONSE,
            },
            ACTION.APPLICATION_TOKENTYPE: {
                'type': 'bool',
                'desc': _("Allow the application to choose which token types should be used "
                          "for authentication. Application may set the parameter 'type' in "
                          "the request. Works with validate/check, validate/samlcheck and "
                          "validate/triggerchallenge.")
            },
            ACTION.AUTHMAXSUCCESS: {
                'type': 'str',
                'desc': _("You can specify how many successful authentication "
                          "requests a user is allowed to do in a given time. "
                          "Specify like 1/5s, 2/10m, 10/1h - s, m, h being "
                          "second, minute and hour."),
                'group': GROUP.CONDITIONS,
            },
            ACTION.AUTHMAXFAIL: {
                'type': 'str',
                'desc': _("You can specify how many failed authentication "
                          "requests a user is allowed to do in a given time. "
                          "Specify like 1/5s, 2/10m, 10/1h - s, m, h being "
                          "second, minute and hour."),
                'group': GROUP.CONDITIONS,
            },
            ACTION.LASTAUTH: {
                'type': 'str',
                'desc': _("You can specify in which time frame the user needs "
                          "to authenticate again with this token. If the user "
                          "authenticates later, authentication will fail. "
                          "Specify like 30h, 7d or 1y."),
                'group': GROUP.CONDITIONS,
            },
            ACTION.TOKENTYPE: {
                'type': 'str',
                'desc': _('The user will only be authenticated with this '
                          'very tokentype.'),
                'group': GROUP.CONDITIONS,
            },

            ACTION.SERIAL: {
                'type': 'str',
                'desc': _('The user will only be authenticated if the serial '
                          'number of the token matches this regexp.'),
                'group': GROUP.CONDITIONS,
            },
            ACTION.TOKENINFO: {
                'type': 'str',
                'desc': _("The user will only be authenticated if the tokeninfo "
                          "field matches the regexp (key/&lt;regexp&gt;/)."),
                'group': GROUP.CONDITIONS,
            },
            ACTION.SETREALM: {
                'type': 'str',
                'value': realms,
                'desc': _('The Realm of the user is set to this very realm. '
                          'This is important if the user is not contained in '
                          'the default realm and can not pass his realm.'),
                'group': GROUP.SETTING_ACTIONS,
            },
            ACTION.NODETAILSUCCESS: {
                'type': 'bool',
                'desc': _('In case of successful authentication additional '
                          'no detail information will be returned.'),
                'group': GROUP.SETTING_ACTIONS,
            },
            ACTION.NODETAILFAIL: {
                'type': 'bool',
                'desc': _('In case of failed authentication additional '
                          'no detail information will be returned.'),
                'group': GROUP.SETTING_ACTIONS,
            },
            ACTION.ADDUSERINRESPONSE: {
                'type': 'bool',
                'desc': _('In case of successful authentication user data '
                          'will be added in the detail branch of the '
                          'authentication response.'),
                'group': GROUP.SETTING_ACTIONS,
            },
            ACTION.ADDRESOLVERINRESPONSE: {
                'type': 'bool',
                'desc': _('In case of successful authentication the user resolver and '
                          'realm will be added in the detail branch of the '
                          'authentication response.'),
                'group': GROUP.SETTING_ACTIONS,
            },
            ACTION.APIKEY: {
                'type': 'bool',
                'desc': _('The sending of an API Auth Key is required during'
                          'authentication. This avoids rogue authenticate '
                          'requests against the /validate/check interface.'),
                'group': GROUP.SETTING_ACTIONS,
            }
        },

        SCOPE.WEBUI: {
            ACTION.ADMIN_DASHBOARD: {
                'type': 'bool',
                'desc': _('If set, administrators will see a dashboard as start screen '
                          'when logging in to privacyIDEA WebUI.')
            },
            ACTION.LOGINMODE: {
                'type': 'str',
                'desc': _(
                    'If set to "privacyIDEA" the users and admins need to '
                    'authenticate against privacyIDEA when they log in '
                    'to the Web UI. Defaults to "userstore".'),
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
                'value': [REMOTE_USER.ACTIVE, REMOTE_USER.DISABLE, REMOTE_USER.FORCE],
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
            ACTION.AUDITPAGESIZE: {
                'type': 'int',
                'desc': _("Set how many audit entries should be displayed in the audit "
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
            ACTION.GDPR_LINK: {
                'type': 'str',
                'desc': _("Link your privacy statement to be displayed in the baseline/footer.")
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
            ACTION.LOGOUT_REDIRECT: {
              'type': 'str',
              'desc': _("The URL of an SSO provider for redirect at logout."
                        "(The URL must start with http:// or https://)")
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
            ACTION.TOKENROLLOVER: {
                'type': 'str',
                'desc': _('This is a whitespace separated list of tokentypes, '
                          'for which a rollover button is displayed in the token '
                          'details.'),
                'group': GROUP.TOKEN
            },
            ACTION.DIALOG_NO_TOKEN: {
                'type': 'bool',
                'desc': _("The welcome dialog will be displayed if the user has no tokens assigned.")
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
            ACTION.DELETION_CONFIRMATION: {
                'type': 'bool',
                'desc': _("If this is checked, there will be a confirmation prompt when "
                          "deleting policies, events, mresolver, resolver or periodic tasks!")
            },
            ACTION.SHOW_SEED: {
                'type': 'bool',
                'desc': _("If this is checked, the seed "
                          "will be displayed as text during enrollment.")
            },
            ACTION.SHOW_NODE: {
                'type': 'bool',
                'desc': _("If this is checked, the privacyIDEA Node name will be displayed "
                          "in the menu bar.")
            },
            ACTION.SHOW_ANDROID_AUTHENTICATOR: {
                'type': 'bool',
                'desc': _("If this is checked, the enrollment page for HOTP, "
                          "TOTP and Push tokens will contain a QR code that leads "
                          "to the privacyIDEA Authenticator in the Google Play Store."),
                'group': 'QR Codes'
            },
            ACTION.SHOW_IOS_AUTHENTICATOR: {
                'type': 'bool',
                'desc': _("If this is checked, the enrollment page for HOTP, "
                          "TOTP and Push tokens will contain a QR code that leads "
                          "to the privacyIDEA Authenticator in the iOS App Store."),
                'group': 'QR Codes'
            },
            ACTION.SHOW_CUSTOM_AUTHENTICATOR: {
                'type': 'str',
                'desc': _("This action adds a QR code in the enrollment page for "
                          "HOTP, TOTP and Push tokens, that lead to this given URL."),
                'group': 'QR Codes'
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

    The matched policies are *not* written to the audit log.

    :return: A scalar, string or None
    """
    value = None
    g = options.get("g")
    if g:
        user_object = options.get("user")
        value = Match.user(g, scope=scope, action=action, user_object=user_object)\
            .action_values(unique=True, allow_white_space_in_action=True, write_to_audit_log=False)
        if len(value) >= 1:
            return list(value)[0]
        else:
            return None

    return value


def get_policy_condition_sections():
    """
    :return: a dictionary mapping condition sections to dictionaries with the following keys:
      * ``"description"``, a human-readable description of the section
    """
    return {
        CONDITION_SECTION.USERINFO: {
            "description": _("The policy only matches if certain conditions on the user info are fulfilled.")
        },
        CONDITION_SECTION.TOKEN: {
            "description": _("The policy only matches if certain conditions of the token attributes are fulfilled.")
        },
        CONDITION_SECTION.TOKENINFO: {
            "description": _("The policy only matches if certain conditions on the token info are fulfilled.")
        },
        CONDITION_SECTION.HTTP_REQUEST_HEADER: {
            "description": _("The policy only matches if certain conditions on the HTTP Request header are fulfilled.")
        },
        CONDITION_SECTION.HTTP_ENVIRONMENT: {
            "description": _("The policy only matches if certain conditions on the HTTP Environment are fulfilled.")
        }
    }


def get_policy_condition_comparators():
    """
    :return: a dictionary mapping comparators to dictionaries with the following keys:
     * ``"description"``, a human-readable description of the comparator
    """
    return {comparator: {"description": description}
            for comparator, description in COMPARATOR_DESCRIPTIONS.items()}


class MatchingError(ServerError):
    pass


class Match(object):
    """
    This class provides a high-level API for policy matching.

    It should not be instantiated directly. Instead, code should use one of the
    provided classmethods to construct a ``Match`` object. See the respective
    classmethods for details.

    A ``Match`` object encapsulates a policy matching operation, i.e. a call to
    :py:func:`privacyidea.lib.policy.PolicyClass.match_policies`.
    In order to retrieve the matching policies, one should use one of
    ``policies()``, ``action_values()`` and ``any()``.
    By default, these functions write the matched policies to the audit log.
    This behavior can be explicitly disabled.

    Every classmethod expects a so-called "context object" as its first argument.
    The context object implements the following attributes:

     * ``audit_object``: an ``Audit`` object which is used to write the used
                         policies to the audit log. In case False is passed for
                         ``write_to_audit_log``, the audit object may be None.
     * ``policy_object``: a ``PolicyClass`` object that is used to retrieve the
                          matching policies.
     * ``client_ip``: the IP of the current client, as a string
     * ``logged_in_user``: a dictionary with keys "username", "realm", "role"
                           that describes the currently logged-in (managing) user

    In our case, this context object is usually the ``flask.g`` object.
    """
    def __init__(self, g, **kwargs):
        self._g = g
        self._match_kwargs = kwargs
        self.pinode = get_privacyidea_node()

    def policies(self, write_to_audit_log=True):
        """
        Return a list of policies.
        The list is sorted by priority, which means that prioritized policies
        appear first.

        :param write_to_audit_log: If True, write the list of matching policies
            to the audit log
        :return: a list of policy dictionaries
        :rtype: list
        """
        if write_to_audit_log:
            audit_data = self._g.audit_object.audit_data
        else:
            audit_data = None
        if hasattr(self._g, "request_headers"):
            request_headers = self._g.request_headers
        else:
            request_headers = None
        return self._g.policy_object.match_policies(audit_data=audit_data, request_headers=request_headers,
                                                    pinode=self.pinode, **self._match_kwargs)

    def any(self, write_to_audit_log=True):
        """
        Return True if at least one policy matches.

        :param write_to_audit_log: If True, write the list of matching policies
            to the audit log
        :return: True or False
        """
        return bool(self.policies(write_to_audit_log=write_to_audit_log))

    def action_values(self, unique, allow_white_space_in_action=False, write_to_audit_log=True):
        """
        Return a dictionary of action values extracted from the matching policies.

        The dictionary maps each action value to a list of policies which define
        this action value.

        :param unique: If True, return only the prioritized action value.
            See :py:func:`privacyidea.lib.policy.PolicyClass.get_action_values` for details.
        :param allow_white_space_in_action: If True, allow whitespace in action values.
            See :py:func:`privacyidea.lib.policy.PolicyClass.get_action_values` for details.
        :param write_to_audit_log: If True, augment the audit log with the names of all
                       policies whose action values are returned
        :rtype: dict
        """
        policies = self.policies(write_to_audit_log=False)
        action_values = self._g.policy_object.extract_action_values(policies,
                                                                    self._match_kwargs['action'],
                                                                    unique=unique,
                                                                    allow_white_space_in_action=
                                                                    allow_white_space_in_action)
        if write_to_audit_log:
            for action_value, policy_names in action_values.items():
                for p_name in policy_names:
                    self._g.audit_object.audit_data.setdefault("policies", []).append(p_name)
        return action_values

    def allowed(self, write_to_audit_log=True):
        """
        Determine if the matched action is allowed in the scope ``admin`` or ``user``.

        This is the case
         * *either* if there are no active policies defined in the matched scope
         * *or* the action is explicitly allowed by a policy in the matched scope

        Example usage::

            is_allowed = Match.user(g, scope=SCOPE.USER, action=ACTION.ENROLLPIN, user=user_object).allowed()
            # is_allowed is now true
            #  either if there is no active policy defined with scope=SCOPE.USER at all
            #  or if there is a policy matching the given scope, action, user and client IP.

        :param write_to_audit_log: If True, write the list of matching policies to the audit log
        :return: True or False
        """
        policies_defined = self.any(write_to_audit_log=write_to_audit_log)
        policies_at_all = self._g.policy_object.list_policies(scope=self._match_kwargs["scope"], active=True)
        # The action is *allowed* if a matched policy explicitly mentions it (``policies_defined`` is non-empty)
        # or if no policies are defined in the given scope (``policies_at_all`` is empty)
        if policies_defined or not policies_at_all:
            return True
        else:
            return False

    @classmethod
    def action_only(cls, g, scope, action):
        """
        Match active policies solely based on a scope and an action, which may also be None.
        The client IP is matched implicitly.

        :param g: context object
        :param scope: the policy scope. SCOPE.ADMIN cannot be passed, ``admin``
            must be used instead.
        :param action: the policy action, or None
        :rtype: ``Match``
        """
        if scope == SCOPE.ADMIN:
            raise MatchingError("Match.action_only cannot be used for policies with scope ADMIN")
        return cls(g, name=None, scope=scope, realm=None, active=True,
                   resolver=None, user=None, user_object=None,
                   client=g.client_ip, action=action, adminrealm=None, time=None,
                   sort_by_priority=True)

    @classmethod
    def realm(cls, g, scope, action, realm):
        """
        Match active policies with a scope, an action and a user realm.
        The client IP is matched implicitly.

        :param g: context object
        :param scope: the policy scope. SCOPE.ADMIN cannot be passed, ``admin``
            must be used instead.
        :param action: the policy action
        :param realm: the realm to match
        :rtype: ``Match``
        """
        if scope == SCOPE.ADMIN:
            raise MatchingError("Match.realm cannot be used for policies with scope ADMIN")
        return cls(g, name=None, scope=scope, realm=realm, active=True,
                   resolver=None, user=None, user_object=None,
                   client=g.client_ip, action=action, adminrealm=None, time=None,
                   sort_by_priority=True, serial=g.serial)

    @classmethod
    def user(cls, g, scope, action, user_object):
        """
        Match active policies with a scope, an action and a user object (which may be None).
        The client IP is matched implicitly.

        :param g: context object
        :param scope: the policy scope. SCOPE.ADMIN cannot be passed, ``admin``
            must be used instead.
        :param action: the policy action
        :param user_object: the user object to match. Might also be None, which
            means that the policy attributes ``user``, ``realm`` and
            ``resolver`` are ignored.
        :type user_object: User or None
        :rtype: ``Match``
        """
        if scope == SCOPE.ADMIN:
            raise MatchingError("Match.user cannot be used for policies with scope ADMIN")
        if not (user_object is None or isinstance(user_object, User)):
            raise MatchingError("Invalid user")
        # Username, realm and resolver will be extracted from the user_object parameter
        return cls(g, name=None, scope=scope, realm=None, active=True,
                   resolver=None, user=None, user_object=user_object,
                   client=g.client_ip, action=action, adminrealm=None, time=None,
                   sort_by_priority=True, serial=g.serial)

    @classmethod
    def token(cls, g, scope, action, token_obj):
        """
        Match active policies with a scope, an action and a token object.
        The client IP is matched implicitly.
        From the token object we try to determine the user as the owner.
        If the token has no owner, we try to determine the tokenrealm.
        We fallback to realm=None

        :param g: context object
        :param scope: the policy scope. SCOPE.ADMIN cannot be passed, ``admin``
            must be used instead.
        :param action: the policy action
        :param token_obj: The token where the user object or the realm should match.
        :rtype: ``Match``
        """
        if token_obj.user:
            return cls.user(g, scope, action, token_obj.user)
        else:
            realms = token_obj.get_realms()
            if len(realms) == 0:
                return cls.action_only(g, scope, action)
            elif len(realms) == 1:
                # We have one distinct token realm
                log.debug("Matching policies with tokenrealm {0!s}.".format(realms[0]))
                return cls.realm(g, scope, action, realms[0])
            else:
                log.warning("The token has more than one tokenrealm. Probably not able to match correctly.")
                return cls.action_only(g, scope, action)

    @classmethod
    def admin(cls, g, action, user_obj=None):
        """
        Match admin policies with an action and, optionally, a realm.
        Assumes that the currently logged-in user is an admin, and throws an error otherwise.
        Policies will be matched against the admin's username and adminrealm,
        and optionally also the provided user_obj on which the admin is acting
        The client IP is matched implicitly.

        :param g: context object
        :param action: the policy action
        :param user_obj: the user against which policies should be matched. Can be None.
        :type user_obj: User or None
        :rtype: ``Match``
        """
        adminuser = g.logged_in_user["username"]
        adminrealm = g.logged_in_user["realm"]
        from privacyidea.lib.auth import ROLE
        if g.logged_in_user["role"] != ROLE.ADMIN:
            raise MatchingError("Policies with scope ADMIN can only be retrieved by admins")
        return cls(g, name=None, scope=SCOPE.ADMIN, user_object=user_obj, active=True,
                   resolver=None, client=g.client_ip, action=action,
                   adminuser=adminuser, adminrealm=adminrealm, time=None,
                   sort_by_priority=True, serial=g.serial)

    @classmethod
    def admin_or_user(cls, g, action, user_obj):
        """
        Depending on the role of the currently logged-in user, match either scope=ADMIN or scope=USER policies.
        If the currently logged-in user is an admin, match policies against the username, adminrealm
        and the given user_obj on which the admin is acting.
        If the currently logged-in user is a user, match policies against the username and the given realm.
        The client IP is matched implicitly.

        :param g: context object
        :param action: the policy action
        :param user_obj: the user_obj on which the administrator is acting
        :rtype: ``Match``
        """
        from privacyidea.lib.auth import ROLE
        adminrealm = adminuser = username = userrealm = None
        scope = g.logged_in_user["role"]
        if scope == ROLE.ADMIN:
            adminuser = g.logged_in_user["username"]
            adminrealm = g.logged_in_user["realm"]
        elif scope == ROLE.USER:
            if not user_obj:
                # If we have a user object (including resolver) in a request, we use this on.
                # Otherwise we take the user from the logged in user.
                username = g.logged_in_user["username"]
                userrealm = g.logged_in_user["realm"]
        else:
            raise MatchingError("Unknown role")
        return cls(g, name=None, scope=scope, realm=userrealm, active=True,
                   resolver=None, user=username, user_object=user_obj,
                   client=g.client_ip, action=action, adminrealm=adminrealm, adminuser=adminuser,
                   time=None, sort_by_priority=True, serial=g.serial)

    @classmethod
    def generic(cls, g, scope=None, realm=None, resolver=None, user=None, user_object=None,
                client=None, action=None, adminrealm=None, adminuser=None, time=None,
                active=True, sort_by_priority=True, serial=None, extended_condition_check=None):
        """
        Low-level legacy policy matching interface: Search for active policies and return
        them sorted by priority. All parameters that should be used for matching have to
        be passed explicitly.
        The client IP has to be passed explicitly.
        See :py:func:`privacyidea.lib.policy.PolicyClass.match_policies` for details.

        :rtype: ``Match``
        """
        if client is None:
            client = g.client_ip if hasattr(g, "client_ip") else None
        if serial is None:
            serial = g.serial if hasattr(g, "serial") else None
        return cls(g, name=None, scope=scope, realm=realm, active=active,
                   resolver=resolver, user=user, user_object=user_object,
                   client=client, action=action, adminrealm=adminrealm,
                   adminuser=adminuser, time=time, serial=serial,
                   sort_by_priority=sort_by_priority, extended_condition_check=extended_condition_check)


def get_allowed_custom_attributes(g, user_obj):
    """
    Return the list off allowed custom user attributes that can be set
    and deleted.
    Returns a dictionary with the two keys "delete" and "set.

    :param g:
    :param user_obj: The User object to check the allowed attributes for
    :return: dict
    """
    deleteables = []
    setables = {}
    del_pol_dict = Match.admin_or_user(g, action=ACTION.DELETE_USER_ATTRIBUTES,
                                       user_obj=user_obj).action_values(unique=False,
                                                                        allow_white_space_in_action=True)
    for keys in del_pol_dict:
        deleteables.extend([k.strip() for k in keys.strip().split()])
    deleteables = list(set(deleteables))
    set_pol_dict = Match.admin_or_user(g, action=ACTION.SET_USER_ATTRIBUTES,
                                       user_obj=user_obj).action_values(unique=False,
                                                                        allow_white_space_in_action=True)
    for keys in set_pol_dict:
        # parse through each policy
        d = parse_string_to_dict(keys)
        for k, vals in d.items():
            setables.setdefault(k, []).extend(vals)
            # If there are double entries in vals, we reduce them to one
            setables[k] = list(set(setables[k]))

    return {"delete": deleteables, "set": setables}


def check_pin(g, pin, tokentype, user_obj):
    """
    get the policies for minimum length, maximum length and PIN contents
    first try to get a token specific policy - otherwise fall back to
    default policy.

    Raises an exception, if the PIN does not comply to the policies.

    :param g:
    :param pin:
    :param tokentype:
    :param user_obj:
    """
    pol_minlen = Match.admin_or_user(g, action="{0!s}_{1!s}".format(tokentype, ACTION.OTPPINMINLEN),
                                     user_obj=user_obj).action_values(unique=True)
    if not pol_minlen:
        pol_minlen = Match.admin_or_user(g, action=ACTION.OTPPINMINLEN,
                                         user_obj=user_obj).action_values(unique=True)
    pol_maxlen = Match.admin_or_user(g, action="{0!s}_{1!s}".format(tokentype, ACTION.OTPPINMAXLEN),
                                     user_obj=user_obj).action_values(unique=True)
    if not pol_maxlen:
        pol_maxlen = Match.admin_or_user(g, action=ACTION.OTPPINMAXLEN,
                                         user_obj=user_obj).action_values(unique=True)
    pol_contents = Match.admin_or_user(g, action="{0!s}_{1!s}".format(tokentype, ACTION.OTPPINCONTENTS),
                                       user_obj=user_obj).action_values(unique=True)
    if not pol_contents:
        pol_contents = Match.admin_or_user(g, action=ACTION.OTPPINCONTENTS,
                                           user_obj=user_obj).action_values(unique=True)

    if len(pol_minlen) == 1 and len(pin) < int(list(pol_minlen)[0]):
        # check the minimum length requirement
        raise PolicyError("The minimum OTP PIN length is {0!s}".format(
            list(pol_minlen)[0]))

    if len(pol_maxlen) == 1 and len(pin) > int(list(pol_maxlen)[0]):
        # check the maximum length requirement
        raise PolicyError("The maximum OTP PIN length is {0!s}".format(
            list(pol_maxlen)[0]))

    if len(pol_contents) == 1:
        # check the contents requirement
        r, comment = check_pin_contents(pin, list(pol_contents)[0])
        if r is False:
            raise PolicyError(comment)


@register_export('policy')
def export_policy(name=None):
    """ Export given or all policy configuration """
    pol_cls = PolicyClass()
    return pol_cls.list_policies(name=name)


@register_import('policy')
def import_policy(data, name=None):
    """Import policy configuration"""
    log.debug('Import policy config: {0!s}'.format(data))
    for res_data in data:
        if name and name != res_data.get('name'):
            continue
        rid = set_policy(**res_data)
        # TODO: we have no information if a new policy was created or an
        #  existing policy updated. We would need to enhance "set_policy()"
        #  to either force overwriting or not and also return if the policy
        #  existed before.
        log.info('Import of policy "{0!s}" finished,'
                 ' id: {1!s}'.format(res_data['name'], rid))
