#  2019-09-06 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Initial writup
#
# License:  AGPLv3
# (c) 2019. Cornelius Kölbel
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
__doc__ = """This is the event handler module modifying request parameters.
"""

import logging
import re

from privacyidea.lib import _
from privacyidea.lib.eventhandler.base import BaseEventHandler
from privacyidea.lib.user import User, get_user_from_param
from privacyidea.lib.utils import is_true

log = logging.getLogger(__name__)

#: The parameters naming the user of a request, for which ``reset_user`` determines the user again.
USER_PARAMETERS = ("realm", "username", "user")


class ACTION_TYPE:
    """
    Allowed actions
    """
    SET = "set"
    DELETE = "delete"


class RequestManglerEventHandler(BaseEventHandler):
    """
    An Eventhandler needs to return a list of actions, which it can handle.

    It also returns a list of allowed action and conditions

    It returns an identifier, which can be used in the event-handling definitions
    """

    identifier = "RequestMangler"
    description = "This event handler can modify the parameters in the request."

    @property
    def allowed_positions(self):
        """
        This returns the allowed positions of the event handler definition.
        :return: list of allowed positions
        """
        """
        Usually we would only modify the parameters in the PRE location, so that
        the request is handled with the modified parameters.

        But we could also modify the parameters in the POST location, so that the request
        is handled with the original parameters, but *after* the request is handled,
        some parameters can be changed to that an event handler, that is called *After*
        the RequestMangler gets other input parameters.

        At the time of writing I can not make up a scenario, but technically it could
        make sense.
        """
        return ["post", "pre"]

    @property
    def actions(self):
        """
        This method returns a dictionary of allowed actions and possible
        options in this handler module.

        :return: dict with actions
        """
        actions = {ACTION_TYPE.DELETE:
                       {"parameter":
                            {"type": "str",
                             "required": True,
                             "description": _("The parameter that should be deleted.")}
                        },
                   ACTION_TYPE.SET:
                       {"parameter":
                            {"type": "str",
                             "required": True,
                             "description": _("The parameter that should be added or modified.")
                             },
                        "value":
                            {"type": "str",
                             "required": True,
                             "description": _("The new value of the parameter. Can contain tags like {0}, {1} for "
                                              "the matched sub strings.")
                             },
                        "match_parameter":
                            {"type": "str",
                             "description": _("The parameter, that should match some values.")
                             },
                        "match_pattern":
                            {"type": "str",
                             "description": _("The value of the match_parameter. It can contain a regular "
                                              "expression and '()' to transfer values to the new parameter.")
                             },
                        "reset_user":
                            {"type": "bool",
                             "description": _("If the parameter is 'username', 'user' or 'realm', the user will be"
                                              " reset. This can have an effect on any further actions on the user!")}
                        }
                   }
        return actions

    def do(self, action, options=None):
        """
        This method executes the defined action in the given event.

        :param action:
        :param options: Contains the flask parameters g, request, response
            and the handler_def configuration
        :type options: dict
        :return:
        """
        ret = True
        request = options.get("request")
        handler_def = options.get("handler_def")
        handler_options = handler_def.get("options", {})
        parameter = handler_options.get("parameter")

        if parameter:
            if action.lower() == ACTION_TYPE.DELETE:
                if parameter in request.all_data:
                    del (request.all_data[parameter])
            elif action.lower() == ACTION_TYPE.SET:
                value = handler_options.get("value")
                match_parameter = handler_options.get("match_parameter")
                match_pattern = handler_options.get("match_pattern")

                if value is not None:
                    # We only take action, if we have a value, even an empty string "".
                    new_value = None
                    if not match_parameter:
                        # simple setting a parameter
                        new_value = value
                    elif match_pattern and match_parameter in request.all_data:
                        # setting a parameter depending on another value,
                        # but only set it, if match_parameter exists
                        """
                        Note: Beware user supplied format-string like "match_pattern", can
                        be dangerous: http://lucumr.pocoo.org/2016/12/29/careful-with-str-format/
                        but in our case it is fine because no objects are involved, as m.groups()
                        always returns a tuple of strings
                        """
                        m = re.match("^" + match_pattern + "$", request.all_data.get(match_parameter))
                        if m:
                            # Now we set the new value with the matching tuple
                            try:
                                new_value = value.format(*m.groups())
                            except IndexError:
                                log.warning(f"The number of found tags ({m.groups()!r}) "
                                            f"do not match the required number ({value!r}).")
                    if new_value is not None:
                        request.all_data[parameter] = new_value
                        # Optionally reset the user if a param of the user was mangled
                        # TODO this should be a UserMangler to explicitly change the user
                        # TODO then remove any user info from all_data...
                        if parameter in USER_PARAMETERS and is_true(handler_options.get("reset_user")):
                            request.User = _user_from_parameters(request.all_data)

        return ret


def _user_from_parameters(parameters: dict) -> User:
    """
    The user the request parameters name, read like any other request that names a user
    (:func:`~privacyidea.lib.user.get_user_from_param`): a ``user@realm`` login name is split as the Split@Sign
    setting says, the ``realm`` parameter takes precedence over the split realm, no realm at all means the default
    realm, and the ``resolver`` parameter is kept. ``/auth`` names the user in ``username`` rather than ``user``, so
    that one is read first.

    :param parameters: the request parameters, after the mangling
    :return: the user of the request
    """
    # Only what names the user is passed on, so no other request parameter, such as the password, reaches its debug log.
    user_parameters = {key: parameters[key] for key in ("realm", "resolver") if key in parameters}
    user_parameters["user"] = parameters.get("username") or parameters.get("user")
    return get_user_from_param(user_parameters)
