# -*- coding: utf-8 -*-
#  2017-08-11 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add condition for detail->error->message
#  2017-07-19 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add possibility to compare tokeninfo field against fixed time
#             and also {now} with offset.
#  2016-05-04 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Initial writup
#
# License:  AGPLv3
# (c) 2016. Cornelius Kölbel
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
#
__doc__ = """This is the base class for an event handler module.
The event handler module is bound to an event together with

* a condition and
* an action
* optional options ;-)
"""
from privacyidea.lib import _
from privacyidea.lib.config import get_token_types
from privacyidea.lib.realm import get_realms
from privacyidea.lib.resolver import get_resolver_list
from privacyidea.lib.auth import ROLE
from privacyidea.lib.token import get_token_owner, get_tokens
from privacyidea.lib.user import User, UserError
from privacyidea.lib.counter import read as counter_read
from privacyidea.lib.utils import (compare_condition, compare_value_value,
                                   compare_generic_condition,
                                   parse_time_offset_from_now, is_true,
                                   check_ip_in_policy)
import datetime
from dateutil.tz import tzlocal
import re
import logging
from privacyidea.lib.tokenclass import DATE_FORMAT

log = logging.getLogger(__name__)


class CONDITION(object):
    """
    Possible conditions
    """
    TOKEN_HAS_OWNER = "token_has_owner"  # nosec B105 # condition name
    TOKEN_IS_ORPHANED = "token_is_orphaned"  # nosec B105 # condition name
    TOKEN_VALIDITY_PERIOD = "token_validity_period"  # nosec B105 # condition name
    USER_TOKEN_NUMBER = "user_token_number"  # nosec B105 # condition name
    OTP_COUNTER = "otp_counter"
    TOKENTYPE = "tokentype"
    LAST_AUTH = "last_auth"
    COUNT_AUTH = "count_auth"
    COUNT_AUTH_SUCCESS = "count_auth_success"
    COUNT_AUTH_FAIL = "count_auth_fail"
    COUNTER = "counter"
    FAILCOUNTER = 'failcounter'
    TOKENINFO = "tokeninfo"
    DETAIL_ERROR_MESSAGE = "detail_error_message"
    DETAIL_MESSAGE = "detail_message"
    RESULT_VALUE = "result_value"
    RESULT_STATUS = "result_status"
    TOKENREALM = "tokenrealm"
    TOKENRESOLVER = "tokenresolver"
    REALM = "realm"
    RESOLVER = "resolver"
    CLIENT_IP = "client_ip"
    ROLLOUT_STATE = "rollout_state"


class GROUP(object):
    """
    These are the event handler groups. The conditions
    will be grouped in the UI.
    """
    TOKEN = "token"  # nosec B105 # group name
    GENERAL = "general"
    USER = "user"
    COUNTER = "counter"


class BaseEventHandler(object):
    """
    An Eventhandler needs to return a list of actions, which it can handle.

    It also returns a list of allowed action and conditions

    It returns an identifier, which can be used in the eventhandlig definitions
    """

    identifier = "BaseEventHandler"
    description = "This is the base class of an EventHandler with no " \
                  "functionality"

    def __init__(self):
        pass

    @property
    def allowed_positions(cls):
        """
        This returns the allowed positions of the event handler definition.
        This can be "post" or "pre" or both.
        :return: list of allowed positions
        """
        return ["post"]

    @property
    def actions(cls):
        """
        This method returns a list of available actions, that are provided
        by this event handler.
        :return: dictionary of actions.
        """
        actions = ["sample_action_1", "sample_action_2"]
        return actions

    @property
    def conditions(cls):
        """
        The UserNotification can filter for conditions like
        * type of logged in user and
        * successful or failed value.success

        allowed types are str, multi, text, regexp

        :return: dict
        """
        realms = get_realms()
        resolvers = get_resolver_list()
        cond = {
            CONDITION.ROLLOUT_STATE: {
                "type": "str",
                "desc": _("The rollout_state of the token has a certain value like 'clientwait' or 'enrolled'."),
                "group": GROUP.TOKEN
            },
            CONDITION.REALM: {
                "type": "str",
                "desc": _("The realm of the user, for which this event should apply."),
                "value": list(realms),
                "group": GROUP.USER
            },
            CONDITION.RESOLVER: {
                "type": "str",
                "desc": _("The resolver of the user, for which this event should apply."),
                "value": list(resolvers),
                "group": GROUP.USER
            },
            CONDITION.TOKENREALM: {
                "type": "multi",
                "desc": _("The realm of the token, for which this event should "
                          "apply."),
                "value": [{"name": r} for r in realms],
                "group": GROUP.TOKEN
            },
            CONDITION.TOKENRESOLVER: {
                "type": "multi",
                "desc": _("The resolver of the token, for which this event should "
                          "apply."),
                "value": [{"name": r} for r in resolvers],
                "group": GROUP.TOKEN
            },
            CONDITION.TOKENTYPE: {
                "type": "multi",
                "desc": _("The type of the token."),
                "value": [{"name": r} for r in get_token_types()],
                "group": GROUP.TOKEN
            },
            "logged_in_user": {
                "type": "str",
                "desc": _("The logged in user is of the following type."),
                "value": (ROLE.ADMIN, ROLE.USER),
                "group": GROUP.USER
            },
            CONDITION.RESULT_VALUE: {
                "type": "str",
                "desc": _("The result.value within the response is "
                          "True or False."),
                "value": ("True", "False"),
                "group": GROUP.GENERAL
            },
            CONDITION.RESULT_STATUS: {
                "type": "str",
                "desc": _("The result.status within the response is "
                          "True or False."),
                "value": ("True", "False"),
                "group": GROUP.GENERAL
            },
            "token_locked": {
                "type": "str",
                "desc": _("Check if the max failcounter of the token is "
                          "reached."),
                "value": ("True", "False"),
                "group": GROUP.TOKEN
            },
            CONDITION.TOKEN_HAS_OWNER: {
                "type": "str",
                "desc": _("The token has a user assigned."),
                "value": ("True", "False"),
                "group": GROUP.TOKEN
            },
            CONDITION.TOKEN_IS_ORPHANED: {
                "type": "str",
                "desc": _("The token has a user assigned, but the user does "
                          "not exist in the userstore anymore."),
                "value": ("True", "False"),
                "group": GROUP.TOKEN
            },
            CONDITION.TOKEN_VALIDITY_PERIOD: {
                "type": "str",
                "desc": _("Check if the token is within its validity period."),
                "value": ("True", "False"),
                "group": GROUP.TOKEN
            },
            "serial": {
                "type": "regexp",
                "desc": _("Action is triggered, if the serial matches this "
                          "regular expression."),
                "group": GROUP.TOKEN
            },
            CONDITION.USER_TOKEN_NUMBER: {
                "type": "str",
                "desc": _("Action is triggered, if the user has this number "
                          "of tokens assigned."),
                "group": GROUP.USER
            },
            CONDITION.OTP_COUNTER: {
                "type": "str",
                "desc": _("Action is triggered, if the counter of the token "
                          "equals this setting. Can also be "
                          "'>100' or '<99' for no exact match."),
                "group": GROUP.COUNTER
            },
            CONDITION.LAST_AUTH: {
                "type": "str",
                "desc": _("Action is triggered, if the last authentication of "
                          "the token is older than 7h, 10d or 1y."),
                "group": GROUP.TOKEN
            },
            CONDITION.COUNT_AUTH: {
                "type": "str",
                "desc": _("This can be '>100', '<99', or '=100', to trigger "
                          "the action, if the tokeninfo field 'count_auth' is "
                          "bigger than 100, less than 99 or exactly 100."),
                "group": GROUP.COUNTER
            },
            CONDITION.COUNT_AUTH_SUCCESS: {
                "type": "str",
                "desc": _("This can be '>100', '<99', or '=100', to trigger "
                          "the action, if the tokeninfo field "
                          "'count_auth_success' is "
                          "bigger than 100, less than 99 or exactly 100."),
                "group": GROUP.COUNTER
            },
            CONDITION.COUNT_AUTH_FAIL: {
                "type": "str",
                "desc": _("This can be '>100', '<99', or '=100', to trigger "
                          "the action, if the difference between the tokeninfo "
                          "field 'count_auth' and 'count_auth_success is "
                          "bigger than 100, less than 99 or exactly 100."),
                "group": GROUP.COUNTER
            },
            CONDITION.FAILCOUNTER: {
                "type": "str",
                "desc": _("This can be '>9', '<9', or '=10', to trigger "
                          "the action, if the failcounter of a token matches this value. "
                          "Note that the failcounter stops increasing, if the max_failcount is "
                          "reached."),
                "group": GROUP.COUNTER
            },
            CONDITION.TOKENINFO: {
                "type": "str",
                "desc": _("This condition can check any arbitrary tokeninfo "
                          "field. You need to enter something like "
                          "'<fieldname> == <fieldvalue>', '<fieldname> > "
                          "<fieldvalue>' or '<fieldname> < <fieldvalue>'."),
                "group": GROUP.TOKEN
            },
            CONDITION.COUNTER: {
                "type": "str",
                "desc": _("This condition can check the value of an arbitrary event counter and "
                          "compare it like 'myCounter == 1000', 'myCounter > 1000' or "
                          "'myCounter < 1000'."),
                "group": GROUP.COUNTER
            },
            CONDITION.DETAIL_ERROR_MESSAGE: {
                "type": "str",
                "desc": _("Here you can enter a regular expression. The "
                          "condition only applies if the regular expression "
                          "matches the detail->error->message in the response."),
                "group": GROUP.GENERAL
            },
            CONDITION.DETAIL_MESSAGE: {
                "type": "str",
                "desc": _("Here you can enter a regular expression. The "
                          "condition only applies if the regular expression "
                          "matches the detail->message in the response."),
                "group": GROUP.GENERAL
            },
            CONDITION.CLIENT_IP: {
                "type": "str",
                "desc": _("Trigger the action, if the client IP matches."),
                "group": GROUP.GENERAL
            }
        }
        return cond

    @property
    def events(cls):
        """
        This method returns a list allowed events, that this event handler
        can be bound to and which it can handle with the corresponding actions.

        An eventhandler may return an asterisk ["*"] indicating, that it can
        be used in all events.
        :return: list of events
        """
        events = ["*"]
        return events

    @staticmethod
    def _get_tokenowner(request):
        user = User()
        if hasattr(request, "User"):
            user = request.User
            serial = request.all_data.get("serial")
            if user.is_empty() and serial:
                # maybe the user is empty, but a serial was passed.
                # Then we determine the user by the serial
                try:
                    user = get_token_owner(serial) or User()
                except Exception as exx:
                    user = User()
                    # This can happen for orphaned tokens.
                    log.info("Could not determine tokenowner for {0!s}. Maybe the "
                             "user does not exist anymore.".format(serial))
                    log.debug(exx)
            # If the user does not exist, we set an empty user
            if not user.exist():
                user = User()

        return user

    @staticmethod
    def _get_response_content(response):
        content = {}
        if response:
            if response.is_json:
                content = response.json
        return content

    def check_condition(self, options):
        """
        Check if all conditions are met and if the action should be executed.
        The the conditions are met, we return "True"
        :return: True
        """
        g = options.get("g")
        request = options.get("request")
        response = options.get("response")
        e_handler_def = options.get("handler_def")
        if not e_handler_def:
            # options is the handler definition
            return True
        # conditions can be corresponding to the property conditions
        conditions = e_handler_def.get("conditions")
        content = self._get_response_content(response)
        user = self._get_tokenowner(request)

        serial = request.all_data.get("serial") or content.get("detail", {}).get("serial")
        tokenrealms = []
        tokenresolvers = []
        tokentype = None
        token_obj = None
        if serial:
            # We have determined the serial number from the request.
            token_obj_list = get_tokens(serial=serial)
        elif user:
            # We have to determine the token via the user object. But only if
            #  the user has only one token
            token_obj_list = get_tokens(user=user)
        else:
            token_obj_list = []

        if len(token_obj_list) == 1:
            # There is a token involved, so we determine it's resolvers and realms
            token_obj = token_obj_list[0]
            tokenrealms = token_obj.get_realms()
            tokentype = token_obj.get_tokentype()

            all_realms = get_realms()
            for tokenrealm in tokenrealms:
                resolvers = all_realms.get(tokenrealm, {}).get("resolver", {})
                tokenresolvers.extend([r.get("name") for r in resolvers])
            tokenresolvers = list(set(tokenresolvers))

        if CONDITION.CLIENT_IP in conditions:
            if g and g.client_ip:
                ip_policy = [ip.strip() for ip in conditions.get(CONDITION.CLIENT_IP).split(",")]
                found, excluded = check_ip_in_policy(g.client_ip, ip_policy)
                if not found or excluded:
                    return False

        if CONDITION.REALM in conditions:
            if user.realm != conditions.get(CONDITION.REALM):
                return False

        if CONDITION.RESOLVER in conditions:
            if user.resolver != conditions.get(CONDITION.RESOLVER):
                return False

        if "logged_in_user" in conditions:
            # Determine the role of the user
            try:
                logged_in_user = g.logged_in_user
                user_role = logged_in_user.get("role")
            except Exception:
                # A non-logged-in-user is a User, not an admin
                user_role = ROLE.USER
            if user_role != conditions.get("logged_in_user"):
                return False

        if CONDITION.RESULT_VALUE in conditions:
            condition_value = conditions.get(CONDITION.RESULT_VALUE)
            result_value = content.get("result", {}).get("value")
            if is_true(condition_value) != is_true(result_value):
                return False

        if CONDITION.RESULT_STATUS in conditions:
            condition_value = conditions.get(CONDITION.RESULT_STATUS)
            result_status = content.get("result", {}).get("status")
            if is_true(condition_value) != is_true(result_status):
                return False

        # checking of max-failcounter state of the token
        if "token_locked" in conditions:
            if token_obj:
                locked = token_obj.get_failcount() >= \
                         token_obj.get_max_failcount()
                if (conditions.get("token_locked") in ["True", True]) != \
                      locked:
                    return False
            else:
                # check all tokens of the user, if any token is maxfail
                token_objects = get_tokens(user=user, maxfail=True)
                if not ','.join([tok.get_serial() for tok in token_objects]):
                    return False

        if CONDITION.TOKENREALM in conditions and tokenrealms:
            res = False
            for trealm in tokenrealms:
                if trealm in conditions.get(CONDITION.TOKENREALM).split(","):
                    res = True
                    break
            if not res:
                return False

        if CONDITION.TOKENRESOLVER in conditions and tokenresolvers:
            res = False
            for tres in tokenresolvers:
                if tres in conditions.get(CONDITION.TOKENRESOLVER).split(","):
                    res = True
                    break
            if not res:
                return False

        if "serial" in conditions and serial:
            serial_match = conditions.get("serial")
            if not bool(re.match(serial_match, serial)):
                return False

        if CONDITION.USER_TOKEN_NUMBER in conditions and user:
            num_tokens = get_tokens(user=user, count=True)
            if num_tokens != int(conditions.get(
                    CONDITION.USER_TOKEN_NUMBER)):
                return False

        if CONDITION.DETAIL_ERROR_MESSAGE in conditions:
            message = content.get("detail", {}).get("error", {}).get("message", "")
            search_exp = conditions.get(CONDITION.DETAIL_ERROR_MESSAGE)
            m = re.search(search_exp, message)
            if not bool(m):
                return False

        if CONDITION.DETAIL_MESSAGE in conditions:
            message = content.get("detail", {}).get("message", "")
            search_exp = conditions.get(CONDITION.DETAIL_MESSAGE)
            m = re.search(search_exp, message)
            if not bool(m):
                return False

        if CONDITION.COUNTER in conditions:
            # Can be counter==1000
            if not compare_generic_condition(conditions.get(CONDITION.COUNTER),
                                             lambda x: counter_read(x) or 0,
                                             "Misconfiguration in your counter "
                                             "condition: {0!s}"
                                             ):
                return False

        # Token specific conditions
        if token_obj:
            if CONDITION.TOKENTYPE in conditions:
                if tokentype not in conditions.get(CONDITION.TOKENTYPE).split(
                        ","):
                    return False

            if CONDITION.TOKEN_HAS_OWNER in conditions:
                uid = token_obj.get_user_id()
                check = conditions.get(CONDITION.TOKEN_HAS_OWNER)
                if uid and check in ["True", True]:
                    res = True
                elif not uid and check in ["False", False]:
                    res = True
                else:
                    log.debug("Condition token_has_owner for token {0!r} "
                              "not fulfilled.".format(token_obj))
                    return False

            if CONDITION.TOKEN_IS_ORPHANED in conditions:
                orphaned = token_obj.is_orphaned()
                check = conditions.get(CONDITION.TOKEN_IS_ORPHANED)
                if orphaned and check in ["True", True]:
                    res = True
                elif not orphaned and check in ["False", False]:
                    res = True
                else:
                    log.debug("Condition token_is_orphaned for token {0!r} not "
                              "fulfilled.".format(token_obj))
                    return False

            if CONDITION.TOKEN_VALIDITY_PERIOD in conditions:
                valid = token_obj.check_validity_period()
                if (conditions.get(CONDITION.TOKEN_VALIDITY_PERIOD)
                       in ["True", True]) != valid:
                    return False

            if CONDITION.OTP_COUNTER in conditions:
                cond = conditions.get(CONDITION.OTP_COUNTER)
                if not compare_condition(cond, token_obj.token.count):
                    return False

            if CONDITION.LAST_AUTH in conditions:
                if token_obj.check_last_auth_newer(conditions.get(
                    CONDITION.LAST_AUTH)):
                    return False

            if CONDITION.COUNT_AUTH in conditions:
                count = token_obj.get_count_auth()
                cond = conditions.get(CONDITION.COUNT_AUTH)
                if not compare_condition(cond, count):
                    return False

            if CONDITION.COUNT_AUTH_SUCCESS in conditions:
                count = token_obj.get_count_auth_success()
                cond = conditions.get(CONDITION.COUNT_AUTH_SUCCESS)
                if not compare_condition(cond, count):
                    return False

            if CONDITION.COUNT_AUTH_FAIL in conditions:
                count = token_obj.get_count_auth()
                c_success = token_obj.get_count_auth_success()
                c_fail = count - c_success
                cond = conditions.get(CONDITION.COUNT_AUTH_FAIL)
                if not compare_condition(cond, c_fail):
                    return False

            if CONDITION.FAILCOUNTER in conditions:
                failcount = token_obj.get_failcount()
                cond = conditions.get(CONDITION.FAILCOUNTER)
                if not compare_condition(cond, failcount):
                    return False

            if CONDITION.TOKENINFO in conditions:
                cond = conditions.get(CONDITION.TOKENINFO)
                # replace {now} in condition
                cond, td = parse_time_offset_from_now(cond)
                s_now = (datetime.datetime.now(tzlocal()) + td).strftime(
                    DATE_FORMAT)
                cond = cond.format(now=s_now)
                if not compare_generic_condition(cond,
                                                 token_obj.get_tokeninfo,
                                                 "Misconfiguration in your tokeninfo "
                                                 "condition: {0!s}"):
                    return False

            if CONDITION.ROLLOUT_STATE in conditions:
                cond = conditions.get(CONDITION.ROLLOUT_STATE)
                if not cond == token_obj.token.rollout_state:
                    return False

        return True

    def do(self, action, options=None):
        """
        This method executes the defined action in the given event.

        :param action:
        :param options: Contains the flask parameters g and request and the
            handler_def configuration
        :type options: dict
        :return:
        """
        log.info("In fact we are doing nothing, be we presume we are doing"
                 "{0!s}".format(action))
        return True
