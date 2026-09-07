# SPDX-FileCopyrightText: (C) 2023 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Info: https://privacyidea.org
#
# This code is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License
# as published by the Free Software Foundation, either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program. If not, see <http://www.gnu.org/licenses/>.

__doc__ = """This is the event handler module for custom user attributes.
You can set or delete your custom attributes

"""

from privacyidea.lib.eventhandler.base import BaseEventHandler
from privacyidea.lib import _
import logging

from privacyidea.lib.user import User
from privacyidea.lib.utils import create_tag_dict, parse_time_offset_from_now

log = logging.getLogger(__name__)


class ACTION_TYPE:
    """
    Allowed actions
    """
    SET_CUSTOM_USER_ATTRIBUTES = "set_custom_user_attributes"
    DELETE_CUSTOM_USER_ATTRIBUTES = "delete_custom_user_attributes"


class USER_TYPE:
    """
    Allowed user types
    """
    TOKENOWNER = "tokenowner"
    LOGGED_IN_USER = "logged_in_user"


class CustomUserAttributesHandler(BaseEventHandler):
    """
    The CustomUserAttributesHandler is an EventHandler which can set/change/delete custom User-Attributes.
    """

    identifier = "CustomUserAttributes"
    description = "This eventhandler can set and delete custom_user_attributes"

    @property
    def allowed_positions(cls):
        """
        This returns the allowed positions of the event handler definition.

        :return: list of allowed positions
        """
        return ["post", "pre"]

    @property
    def actions(cls):
        """
        This method returns a dictionary of allowed actions and possible
        options in this handler module.

        :return: dict with actions
        """
        actions = {
            ACTION_TYPE.SET_CUSTOM_USER_ATTRIBUTES: {
                "user": {
                    'type': 'str',
                    'required': True,
                    'description': _('The user for whom the custom attribute should be set.'),
                    "value": [
                        USER_TYPE.TOKENOWNER,
                        USER_TYPE.LOGGED_IN_USER,
                    ]},
                "attrkey": {
                    'type': 'str',
                    'description': _('The key of the custom user attribute that should be set.')},
                "attrvalue": {
                    'type': 'str',
                    'description': _('The value of the custom user attribute. '
                                     'It may contain tags like {now} (with offsets '
                                     'such as {now}+2h), {client_ip}, {ua_browser}, '
                                     '{ua_string}, {serial}, {username}, {userrealm} '
                                     'and {tokentype}. {current_time} is a deprecated '
                                     'alias for {now}.')}
            },
            ACTION_TYPE.DELETE_CUSTOM_USER_ATTRIBUTES: {
                "user": {
                    'type': 'str',
                    'required': True,
                    'description': _('The user from which the custom attribute should be deleted.'),
                    "value": [
                        USER_TYPE.TOKENOWNER,
                        USER_TYPE.LOGGED_IN_USER,
                    ]},
                "attrkey": {
                    'type': 'str',
                    'description': _('The key of the custom user attribute that should be deleted.')}
            }}
        return actions

    def do(self, action, options=None):
        """
        This method executes the defined action in the given event.

        :param action: The action to perform
        :type action: str
        :param options: Contains the flask parameters g,  attrkey and attrvalue
        :type options: dict
        :return:
        """
        g = options.get("g")
        request = options.get("request")
        handler_def = options.get("handler_def")
        handler_options = handler_def.get("options", {})
        user_type = handler_options.get("user", USER_TYPE.TOKENOWNER)
        tokenowner = self._get_tokenowner(request)
        if user_type == USER_TYPE.TOKENOWNER and not tokenowner.is_empty():
            user = tokenowner
        elif user_type == USER_TYPE.LOGGED_IN_USER and hasattr(g, 'logged_in_user'):
            user = User(login=g.logged_in_user.get('username'),
                        realm=g.logged_in_user.get('realm'))
        else:
            log.warning("Unable to determine the user for handling the custom "
                        f"attribute! action: {action!s}, handler: {handler_def!s}")
            return False

        attrkey = handler_options.get("attrkey")
        attrvalue = handler_options.get("attrvalue")
        if action.lower() == "set_custom_user_attributes":
            attrvalue = self._render_attrvalue(attrvalue, options, request, g, tokenowner)
            ret = user.set_attribute(attrkey, attrvalue)
        elif action.lower() == "delete_custom_user_attributes":
            ret = user.delete_attribute(attrkey)
        else:
            log.warning(f'Unknown action value: {action!s}')
            ret = False

        return ret

    @staticmethod
    def _render_attrvalue(attrvalue, options, request, g, tokenowner):
        """
        Substitute the supported tags in the attribute value.

        Besides the tags provided by :func:`create_tag_dict` (like ``{client_ip}``,
        ``{ua_browser}``, ``{ua_string}``, ``{serial}``, ``{username}`` ...) the
        placeholders ``{now}`` and ``{current_time}`` are supported, including
        offsets such as ``{now}+2h``.

        :param attrvalue: The raw attribute value (may contain tags)
        :return: The attribute value with all tags replaced
        """
        if not attrvalue or "{" not in attrvalue:
            return attrvalue

        # Resolve a possible time offset like {now}+2h and strip it from the string.
        # The offset is passed to create_tag_dict, which renders {now}/{current_time}.
        attrvalue, time_delta = parse_time_offset_from_now(attrvalue)

        owner = tokenowner if tokenowner and not tokenowner.is_empty() else None
        serial = request.all_data.get("serial") if hasattr(request, "all_data") else None
        serial, tokentype, tokendescription = BaseEventHandler._get_token_data(serial, owner)
        logged_in_user = g.logged_in_user if hasattr(g, "logged_in_user") else None

        tags = create_tag_dict(logged_in_user=logged_in_user,
                               request=request,
                               client_ip=getattr(g, "client_ip", None),
                               serial=serial,
                               tokenowner=owner,
                               tokentype=tokentype,
                               tokendescription=tokendescription,
                               time_offset=time_delta)

        try:
            attrvalue = attrvalue.format(**tags)
        except Exception as e:
            # An attribute value that can not be formatted (unknown tag, unbalanced
            # brace, ...) must not fail the event handling. Keep the raw value.
            log.warning(f"Could not format the custom user attribute value: {e!r}. "
                        f"Using the unformatted value.")
        return attrvalue

