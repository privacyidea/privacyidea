#  2017-08-11 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add condition for detail->error->message
#  2017-07-19 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add possibility to compare tokeninfo field against fixed time
#             and also {now} with offset.
#  2016-05-04 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Initial writeup
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

import datetime
import logging
import re

from dateutil.tz import tzlocal

from privacyidea.lib import _
from privacyidea.lib.auth import ROLE
from privacyidea.lib.config import get_token_types
from privacyidea.lib.container import (find_container_by_serial, find_container_for_token, get_all_containers,
                                       get_container_classes)
from privacyidea.lib.containerclass import TokenContainerClass
from privacyidea.lib.counter import read as counter_read
from privacyidea.lib.realm import get_realms
from privacyidea.lib.resolver import get_resolver_list
from privacyidea.lib.token import get_token_owner, get_tokens
from privacyidea.lib.user import User
from privacyidea.lib.utils import (compare_condition, compare_generic_condition,
                                   parse_time_offset_from_now, is_true,
                                   check_ip_in_policy, AUTH_RESPONSE)
from privacyidea.lib.tokenclass import DATE_FORMAT
from privacyidea.lib.challenge import get_challenges

log = logging.getLogger(__name__)


class CONDITION(object):
    """
    Possible conditions
    """
    TOKEN_HAS_OWNER = "token_has_owner"  # nosec B105 # condition name
    TOKEN_IS_ORPHANED = "token_is_orphaned"  # nosec B105 # condition name
    TOKEN_VALIDITY_PERIOD = "token_validity_period"  # nosec B105 # condition name
    USER_TOKEN_NUMBER = "user_token_number"  # nosec B105 # condition name
    USER_CONTAINER_NUMBER = "user_container_number"
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
    RESULT_AUTHENTICATION = "result_authentication"
    TOKENREALM = "tokenrealm"
    TOKENRESOLVER = "tokenresolver"
    TOKEN_IS_IN_CONTAINER = "token_is_in_container"
    REALM = "realm"
    RESOLVER = "resolver"
    CLIENT_IP = "client_ip"
    ROLLOUT_STATE = "rollout_state"
    CHALLENGE_SESSION = "challenge_session"
    CHALLENGE_EXPIRED = "challenge_expired"
    CONTAINER_STATE = "container_state"
    CONTAINER_EXACT_STATE = "container_exact_state"
    CONTAINER_HAS_OWNER = "container_has_owner"
    CONTAINER_TYPE = "container_type"
    CONTAINER_HAS_TOKEN = "container_has_token"
    SERIAL = "serial"


class GROUP(object):
    """
    These are the event handler groups. The conditions
    will be grouped in the UI.
    """
    TOKEN = "token"  # nosec B105 # group name
    GENERAL = "general"
    USER = "user"
    COUNTER = "counter"
    CHALLENGE = "challenge"
    CONTAINER = "container"


class BaseEventHandler(object):
    """
    An Eventhandler needs to return a list of actions, which it can handle.

    It also returns a list of allowed action and conditions

    It returns an identifier, which can be used in the event-handling definitions
    """

    identifier = "BaseEventHandler"
    description = "This is the base class of an EventHandler with no " \
                  "functionality"

    def __init__(self):
        pass
        self.run_details = None

    @property
    def allowed_positions(self):
        """
        This returns the allowed positions of the event handler definition.
        This can be "post" or "pre" or both.

        :return: list of allowed positions
        """
        return ["post"]

    @property
    def actions(self):
        """
        This method returns a list of available actions, that are provided
        by this event handler.

        :return: dictionary of actions.
        """
        actions = ["sample_action_1", "sample_action_2"]
        return actions

    @property
    def conditions(self):
        """
        The UserNotification can filter for conditions like
        * type of logged-in user and
        * successful or failed value.success

        allowed types are str, multi, text, regexp

        :return: dict
        """
        realms = get_realms()
        resolvers = get_resolver_list()
        container_states = [{"name": state} for state in TokenContainerClass.get_state_types().keys()]
        cond = {
            CONDITION.CHALLENGE_SESSION:
                {
                    "type": "str",
                    "desc": _("The challenge session matches the string or regular "
                              "expression (like 'challenge_declined' or 'enrollment')"),
                    "group": GROUP.CHALLENGE
                },
            CONDITION.CHALLENGE_EXPIRED:
                {
                    "type": "str",
                    "desc": _("The challenge of a token during the authentication process"
                              " is expired."),
                    "value": ("True", "False"),
                    "group": GROUP.CHALLENGE
                },
            CONDITION.ROLLOUT_STATE:
                {
                    "type": "str",
                    "desc": _("The rollout_state of the token has a certain value like 'clientwait' or 'enrolled'."),
                    "group": GROUP.TOKEN
                },
            CONDITION.REALM:
                {
                    "type": "multi",
                    "desc": _("The realm of the user, for which this event should apply."),
                    "value": [{"name": r} for r in realms],
                    "group": GROUP.USER
                },
            CONDITION.RESOLVER:
                {
                    "type": "multi",
                    "desc": _("The resolver of the user, for which this event should apply."),
                    "value": [{"name": r} for r in resolvers],
                    "group": GROUP.USER
                },
            CONDITION.TOKENREALM:
                {
                    "type": "multi",
                    "desc": _("The realm of the token, for which this event should "
                              "apply."),
                    "value": [{"name": r} for r in realms],
                    "group": GROUP.TOKEN
                },
            CONDITION.TOKENRESOLVER:
                {
                    "type": "multi",
                    "desc": _("The resolver of the token, for which this event should "
                              "apply."),
                    "value": [{"name": r} for r in resolvers],
                    "group": GROUP.TOKEN
                },
            CONDITION.TOKENTYPE:
                {
                    "type": "multi",
                    "desc": _("The type of the token."),
                    "value": [{"name": r} for r in get_token_types()],
                    "group": GROUP.TOKEN
                },
            "logged_in_user":
                {
                    "type": "str",
                    "desc": _("The logged in user is of the following type."),
                    "value": (ROLE.ADMIN, ROLE.USER),
                    "group": GROUP.USER
                },
            CONDITION.RESULT_VALUE:
                {
                    "type": "str",
                    "desc": _("The result.value within the response is "
                              "True or False."),
                    "value": ("True", "False"),
                    "group": GROUP.GENERAL
                },
            CONDITION.RESULT_STATUS:
                {
                    "type": "str",
                    "desc": _("The result.status within the response is "
                              "True or False."),
                    "value": ("True", "False"),
                    "group": GROUP.GENERAL
                },
            CONDITION.RESULT_AUTHENTICATION:
                {
                    "type": "str",
                    "desc": _("The result.authentication within the response is the given value."),
                    "value": (
                        AUTH_RESPONSE.ACCEPT, AUTH_RESPONSE.REJECT, AUTH_RESPONSE.CHALLENGE, AUTH_RESPONSE.DECLINED),
                    "group": GROUP.GENERAL
                },
            "token_locked":
                {
                    "type": "str",
                    "desc": _("Check if the max failcounter of the token is "
                              "reached."),
                    "value": ("True", "False"),
                    "group": GROUP.TOKEN
                },
            CONDITION.TOKEN_HAS_OWNER:
                {
                    "type": "str",
                    "desc": _("The token has a user assigned."),
                    "value": ("True", "False"),
                    "group": GROUP.TOKEN
                },
            CONDITION.TOKEN_IS_ORPHANED:
                {
                    "type": "str",
                    "desc": _("The token has a user assigned, but the user does "
                              "not exist in the userstore anymore."),
                    "value": ("True", "False"),
                    "group": GROUP.TOKEN
                },
            CONDITION.TOKEN_VALIDITY_PERIOD:
                {
                    "type": "str",
                    "desc": _("Check if the token is within its validity period."),
                    "value": ("True", "False"),
                    "group": GROUP.TOKEN
                },
            CONDITION.SERIAL:
                {
                    "type": "regexp",
                    "desc": _("Action is triggered, if the serial matches this "
                              "regular expression."),
                    "group": GROUP.TOKEN
                },
            CONDITION.TOKEN_IS_IN_CONTAINER:
                {
                    "type": "str",
                    "desc": _("The token is in a container."),
                    "value": ("True", "False"),
                    "group": GROUP.TOKEN
                },
            CONDITION.USER_TOKEN_NUMBER:
                {
                    "type": "str",
                    "desc": _("Action is triggered, if the user has this number "
                              "of tokens assigned."),
                    "group": GROUP.USER
                },
            CONDITION.USER_CONTAINER_NUMBER:
                {
                    "type": "str",
                    "desc": _("Action is triggered, if the user has this number "
                              "of containers assigned."),
                    "group": GROUP.USER
                },
            CONDITION.OTP_COUNTER:
                {
                    "type": "str",
                    "desc": _("Action is triggered, if the counter of the token "
                              "equals this setting. Can also be "
                              "'>100' or '<99' for no exact match."),
                    "group": GROUP.COUNTER
                },
            CONDITION.LAST_AUTH:
                {
                    "type": "str",
                    "desc": _("Action is triggered, if the last authentication of "
                              "the token is older than 7h, 10d or 1y."),
                    "group": GROUP.TOKEN
                },
            CONDITION.COUNT_AUTH:
                {
                    "type": "str",
                    "desc": _("This can be '>100', '<99', or '=100', to trigger "
                              "the action, if the tokeninfo field 'count_auth' is "
                              "bigger than 100, less than 99 or exactly 100."),
                    "group": GROUP.COUNTER
                },
            CONDITION.COUNT_AUTH_SUCCESS:
                {
                    "type": "str",
                    "desc": _("This can be '>100', '<99', or '=100', to trigger "
                              "the action, if the tokeninfo field "
                              "'count_auth_success' is "
                              "bigger than 100, less than 99 or exactly 100."),
                    "group": GROUP.COUNTER
                },
            CONDITION.COUNT_AUTH_FAIL:
                {
                    "type": "str",
                    "desc": _("This can be '>100', '<99', or '=100', to trigger "
                              "the action, if the difference between the tokeninfo "
                              "field 'count_auth' and 'count_auth_success is "
                              "bigger than 100, less than 99 or exactly 100."),
                    "group": GROUP.COUNTER
                },
            CONDITION.FAILCOUNTER:
                {
                    "type": "str",
                    "desc": _("This can be '>9', '<9', or '=10', to trigger "
                              "the action, if the failcounter of a token matches this value. "
                              "Note that the failcounter stops increasing, if the max_failcount is "
                              "reached."),
                    "group": GROUP.COUNTER
                },
            CONDITION.TOKENINFO:
                {
                    "type": "str",
                    "desc": _("This condition can check any arbitrary tokeninfo "
                              "field. You need to enter something like "
                              "'<fieldname> == <fieldvalue>', '<fieldname> > "
                              "<fieldvalue>' or '<fieldname> < <fieldvalue>'."),
                    "group": GROUP.TOKEN
                },
            CONDITION.COUNTER:
                {
                    "type": "str",
                    "desc": _("This condition can check the value of an arbitrary event counter and "
                              "compare it like 'myCounter == 1000', 'myCounter > 1000' or "
                              "'myCounter < 1000'."),
                    "group": GROUP.COUNTER
                },
            CONDITION.DETAIL_ERROR_MESSAGE:
                {
                    "type": "str",
                    "desc": _("Here you can enter a regular expression. The "
                              "condition only applies if the regular expression "
                              "matches the detail->error->message in the response."),
                    "group": GROUP.GENERAL
                },
            CONDITION.DETAIL_MESSAGE:
                {
                    "type": "str",
                    "desc": _("Here you can enter a regular expression. The "
                              "condition only applies if the regular expression "
                              "matches the detail->message in the response."),
                    "group": GROUP.GENERAL
                },
            CONDITION.CLIENT_IP:
                {
                    "type": "str",
                    "desc": _("Trigger the action, if the client IP matches."),
                    "group": GROUP.GENERAL
                },
            CONDITION.CONTAINER_STATE:
                {
                    "type": "multi",
                    "desc": _("The container is in the specified states, but can additionally be in other states."),
                    "value": container_states,
                    "group": GROUP.CONTAINER
                },
            CONDITION.CONTAINER_EXACT_STATE:
                {
                    "type": "multi",
                    "desc": _("The container is only in the specified states."),
                    "value": container_states,
                    "group": GROUP.CONTAINER
                },
            CONDITION.CONTAINER_HAS_OWNER:
                {
                    "type": "str",
                    "desc": _("The container has a user assigned."),
                    "value": ("True", "False"),
                    "group": GROUP.CONTAINER
                },
            CONDITION.CONTAINER_HAS_TOKEN:
                {
                    "type": "str",
                    "desc": _("The container has at least one token assigned."),
                    "value": ("True", "False"),
                    "group": GROUP.CONTAINER
                },
            CONDITION.CONTAINER_TYPE:
                {
                    "type": "str",
                    "desc": _("The container is of a certain type."),
                    "value": list(get_container_classes().keys()),
                    "group": GROUP.CONTAINER
                }
        }
        return cond

    @property
    def events(self):
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
            if user is None:
                user = User()
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
    def _get_container_owners(request):
        users = []
        user = User(login='', realm='')
        if hasattr(request, "User"):
            user = request.User
            if user:
                users.append(user)
        serial = request.all_data.get("container_serial")
        if not user and serial:
            # maybe the user is empty, but a serial was passed.
            # Then we determine the user by the serial
            container = find_container_by_serial(serial)
            users = container.get_users()

        return users

    @classmethod
    def _get_users_from_request(cls, request):
        """
        Extracts the user information from the request or searches for the container owners or token owner.
        If no user is found, an empty user is returned.

        :param request: The request object
        :return: List of user objects
        """
        users = cls._get_container_owners(request)
        if len(users) == 0:
            user = cls._get_tokenowner(request)
            if not user.is_empty():
                users.append(user)
        return users

    @classmethod
    def _get_token_serials(cls, request, content, g):
        """
        Extracts the token serials from the request, content or audit object.

        :param request: The request object
        :param content: The content of the response
        :param g: The g object
        :return: Comma separated string of token serials
        """
        # Get single token serial
        serial = request.all_data.get("serial") or \
                 content.get("detail", {}).get("serial") or \
                 g.audit_object.audit_data.get("serial")

        return serial

    @classmethod
    def _get_container_serial(cls, request, content):
        """
        Get the container serial from the request, content or audit object.

        :param request: The request object
        :param content: The content of the response
        :return: The container serial or None if no serial could be found
        """

        # get serial from request
        container_serial = request.all_data.get("container_serial")
        if not cls._serial_is_from_container(container_serial):
            container_serial = None

        if not container_serial:
            # get serial from response
            value = content.get("result", {}).get('value', {})
            if isinstance(value, dict):
                container_serial = value.get("container_serial")
                if not cls._serial_is_from_container(container_serial):
                    container_serial = None

        return container_serial

    @classmethod
    def _get_container_serial_from_token(cls, request, content, g):
        """
        Tries to get a token serial. If a token is found, it tries to get the container serial from this token.

        :param request: The request object
        :param content: The content of the response
        :param g: The g object
        :return: The container serial or None if no serial could be found
        """
        container_serial = None
        serials = cls._get_token_serials(request, content, g)

        if serials:
            serial_list = serials.replace(' ', '').split(',')
            if len(serial_list):
                # Only if one token serial is provided a corresponding container can be found
                serial = serial_list[0]
                container_serial = cls._get_container_serial_from_token_serial(serial)

        return container_serial

    @classmethod
    def _serial_is_from_container(cls, serial):
        """
        Validates whether the given serial is from a container.

        :param serial: The serial to validate
        :return: True if a container with the given serial exists, False otherwise
        """
        container_exists = False

        if serial:
            # Check if a container exists with this serial
            containers = get_all_containers(serial=serial, pagesize=0, page=0)['containers']
            if len(containers) > 0:
                container_exists = True

        return container_exists

    @classmethod
    def _get_container_serial_from_token_serial(cls, token_serial):
        """
        Tries to get the container serial from a token.

        :param token_serial: Serial of a token
        :return: container serial or None if the token is not part of a container or the token does not exist
        """
        container_serial = None
        if token_serial:
            tokens = get_tokens(serial=token_serial)
            if len(tokens) > 0:
                token = tokens[0]
                container = find_container_for_token(token.get_serial())
                if container:
                    container_serial = container.serial

        return container_serial

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
        If the conditions are met, we return "True"

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
        transaction_id = request.all_data.get("transaction_id")
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
            # There is a token involved, so we determine its resolvers and realms
            token_obj = token_obj_list[0]
            tokenrealms = token_obj.get_realms()
            tokentype = token_obj.get_tokentype()

            all_realms = get_realms()
            for tokenrealm in tokenrealms:
                resolvers = all_realms.get(tokenrealm, {}).get("resolver", {})
                tokenresolvers.extend([r.get("name") for r in resolvers])
            tokenresolvers = list(set(tokenresolvers))

        # Get container
        container_serial = self._get_container_serial(request, content)
        container = None
        if container_serial:
            container = find_container_by_serial(container_serial)
        elif serial and token_obj:
            container = find_container_for_token(serial)

        if CONDITION.CLIENT_IP in conditions:
            if g and g.client_ip:
                ip_policy = [ip.strip() for ip in conditions.get(CONDITION.CLIENT_IP).split(",")]
                found, excluded = check_ip_in_policy(g.client_ip, ip_policy)
                if not found or excluded:
                    return False

        if CONDITION.REALM in conditions:
            if user.realm not in conditions.get(CONDITION.REALM).split(","):
                return False

        if CONDITION.RESOLVER in conditions:
            if user.resolver not in conditions.get(CONDITION.RESOLVER).split(","):
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

        if CONDITION.RESULT_AUTHENTICATION in conditions:
            condition_value = conditions.get(CONDITION.RESULT_AUTHENTICATION)
            result_auth = content.get("result", {}).get("authentication")
            if condition_value != result_auth:
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
            if num_tokens != int(conditions.get(CONDITION.USER_TOKEN_NUMBER)):
                return False

        if CONDITION.USER_CONTAINER_NUMBER in conditions and user:
            container_list = get_all_containers(user=user, page=1, pagesize=1)
            num_containers = container_list['count']
            if num_containers != int(conditions.get(CONDITION.USER_CONTAINER_NUMBER)):
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
                if (conditions.get(CONDITION.TOKEN_VALIDITY_PERIOD) in ["True", True]) != valid:
                    return False

            if CONDITION.OTP_COUNTER in conditions:
                cond = conditions.get(CONDITION.OTP_COUNTER)
                if not compare_condition(cond, token_obj.token.count):
                    return False

            if CONDITION.LAST_AUTH in conditions:
                if token_obj.check_last_auth_newer(conditions.get(CONDITION.LAST_AUTH)):
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

            # We also put the challenge condition here. If we do not have a
            # token-obj we can not identify challenges.
            if CONDITION.CHALLENGE_SESSION or CONDITION.CHALLENGE_EXPIRED in conditions:
                chals = get_challenges(serial=token_obj.token.serial, transaction_id=transaction_id)
                if len(chals) == 1:
                    chal = chals[0]
                    if CONDITION.CHALLENGE_SESSION in conditions:
                        cond_match = conditions.get(CONDITION.CHALLENGE_SESSION)
                        if not bool(re.match(cond_match, chal.session)):
                            return False
                    if CONDITION.CHALLENGE_EXPIRED in conditions:
                        condition_value = conditions.get(CONDITION.CHALLENGE_EXPIRED)
                        if is_true(condition_value) == chal.is_valid():
                            return False
                elif len(chals) > 1:
                    # If there is more than one challenge, the conditions seams awkward
                    log.warning("There are more than one challenge for token {0!s} "
                                "and transaction_id {1!s}".format(token_obj.token.serial, transaction_id))
                    return False

            if CONDITION.TOKEN_IS_IN_CONTAINER in conditions:
                cond = conditions.get(CONDITION.TOKEN_IS_IN_CONTAINER)
                container = find_container_for_token(serial)
                token_is_in_container = container is not None
                if token_is_in_container and cond in ["True", True]:
                    res = True
                elif not token_is_in_container and cond in ["False", False]:
                    res = True
                else:
                    log.debug(f"Condition {CONDITION.TOKEN_IS_IN_CONTAINER} for token {token_obj} "
                              "not fulfilled.")
                    return False

        # Container specific conditions
        if container:
            if CONDITION.CONTAINER_STATE in conditions:
                cond = conditions.get(CONDITION.CONTAINER_STATE).split(',')
                container_states = container.get_states()
                for cond_state in cond:
                    if cond_state not in container_states:
                        log.debug(f"Condition container_state {cond_state} for container {container.serial} "
                                  "not fulfilled.")
                        return False

            if CONDITION.CONTAINER_EXACT_STATE in conditions:
                cond = conditions.get(CONDITION.CONTAINER_EXACT_STATE).split(',')
                container_states = container.get_states()
                if len(cond) != len(container_states):
                    log.debug(f"Condition container_single_state {cond} for container {container.serial} "
                              "not fulfilled.")
                    return False

                for cond_state in cond:
                    if cond_state not in container_states:
                        log.debug(f"Condition container_state {cond_state} for container {container.serial} "
                                  "not fulfilled.")
                        return False

            if CONDITION.CONTAINER_HAS_OWNER in conditions:
                has_container_owner = len(container.get_users()) > 0
                cond = conditions.get(CONDITION.CONTAINER_HAS_OWNER)
                if has_container_owner and cond in ["True", True]:
                    res = True
                elif not has_container_owner and cond in ["False", False]:
                    res = True
                else:
                    log.debug(f"Condition container_has_owner for container {container.serial} "
                              "not fulfilled.")
                    return False

            if CONDITION.CONTAINER_TYPE in conditions:
                cond = conditions.get(CONDITION.CONTAINER_TYPE)
                if container.type != cond:
                    log.debug(f"Condition container_type {cond} for container {container.serial} "
                              "not fulfilled.")
                    return False

            if CONDITION.CONTAINER_HAS_TOKEN in conditions:
                tokens = [token.get_serial() for token in container.get_tokens()]
                cond = conditions.get(CONDITION.CONTAINER_HAS_TOKEN)
                if len(tokens) > 0 and cond in ["True", True]:
                    res = True
                elif len(tokens) == 0 and cond in ["False", False]:
                    res = True
                else:
                    log.debug(f"Condition container_has_token for container {container.serial} "
                              "not fulfilled.")
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
