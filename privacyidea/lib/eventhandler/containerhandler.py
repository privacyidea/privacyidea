# (c) NetKnights GmbH 2024,  https://netknights.it
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-FileCopyrightText: 2024 Jelina Unger <jelina.unger@netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
#
__doc__ = """This is the event handler module for container actions.
"""

from privacyidea.lib.container import get_container_classes, delete_container_by_serial, init_container, \
    find_container_by_serial, set_container_states, \
    add_container_states, set_container_description, add_container_info, delete_container_info, assign_user, \
    unassign_user, set_container_info, remove_multiple_tokens_from_container, add_multiple_tokens_to_container
from privacyidea.lib.containerclass import TokenContainerClass
from privacyidea.lib.eventhandler.base import BaseEventHandler
from privacyidea.lib import _
import logging

from privacyidea.lib.token import enable_token
from privacyidea.lib.user import User

log = logging.getLogger(__name__)


class ACTION_TYPE(object):
    """
    Allowed actions
    """
    INIT = "create"
    DELETE = "delete"
    UNASSIGN = "unassign"
    ASSIGN = "assign"
    SET_STATES = "set states"
    ADD_STATES = "add states"
    SET_DESCRIPTION = "set description"
    SET_CONTAINER_INFO = "set container info"
    ADD_CONTAINER_INFO = "add container info"
    DELETE_CONTAINER_INFO = "delete container info"
    REMOVE_TOKENS = "remove all tokens"
    DISABLE_TOKENS = "disable all tokens"
    ENABLE_TOKENS = "enable all tokens"


class ContainerEventHandler(BaseEventHandler):
    """
    This is the event handler for container actions.
    """

    identifier = "Container"
    description = "This event handler can trigger new actions on containers."

    @property
    def allowed_positions(cls):
        """
        This returns the allowed positions of the event handler definition.
        This can be "post" or "pre" or both.
        :return: list of allowed positions
        """
        return ["pre", "post"]

    @property
    def actions(cls):
        """
        This method returns a list of available actions, that are provided
        by this event handler.
        :return: dictionary of actions.
        """
        container_types = list(get_container_classes().keys())
        container_states = list(TokenContainerClass.get_state_types().keys())
        action_states = {}
        for state in container_states:
            action_states[state] = {"type": "bool",
                                    "required": False,
                                    "description": _(f"Set the state {state}")}

        actions = {
            ACTION_TYPE.INIT:
                {"type":
                     {"type": "str",
                      "required": True,
                      "description": _("Container type to create"),
                      "value": container_types
                      },
                 "description":
                     {"type": "str",
                      "required": False,
                      "description": _("Description of the container")
                      },
                 "user":
                     {"type": "bool",
                      "required": False,
                      "description": _("Assign container to user in request or to token/container owner")
                      },
                 "token":
                     {"type": "bool",
                      "required": False,
                      "description": _("Add token from request to container")
                      }
                 },
            ACTION_TYPE.DELETE: {},
            ACTION_TYPE.UNASSIGN: {},
            ACTION_TYPE.ASSIGN: {},
            ACTION_TYPE.SET_STATES: action_states,
            ACTION_TYPE.ADD_STATES: action_states,
            ACTION_TYPE.SET_DESCRIPTION:
                {"description":
                     {"type": "str",
                      "required": True,
                      "description": _("Description of the container")
                      }
                 },
            ACTION_TYPE.REMOVE_TOKENS: {},
            ACTION_TYPE.SET_CONTAINER_INFO:
                {"key":
                     {"type": "str",
                      "required": True,
                      "description": _("Set this container info key (deletes all existing keys).")
                      },
                 "value":
                     {"type": "str",
                      "description": _("Set the value for the key above.")}
                 },
            ACTION_TYPE.ADD_CONTAINER_INFO:
                {"key":
                     {"type": "str",
                      "required": True,
                      "description": _("Add this key to the container info.")
                      },
                 "value":
                     {"type": "str",
                      "description": _("Set the value for the key above.")}
                 },
            ACTION_TYPE.DELETE_CONTAINER_INFO: {},
            ACTION_TYPE.DISABLE_TOKENS: {},
            ACTION_TYPE.ENABLE_TOKENS: {}
        }
        return actions

    def do(self, action, options):
        """
        Executes the defined action in the given event.

        :param action:
        :param options: Contains the flask parameters g, request, response
            and the handler_def configuration
        :type options: dict
        :return: True if the action was successful, False otherwise (missing information, e.g. serial, user)
        """
        ret = True
        g = options.get("g")
        request = options.get("request")
        response = options.get("response")
        content = self._get_response_content(response)
        handler_def = options.get("handler_def")
        handler_options = handler_def.get("options", {})
        user = User(login=g.logged_in_user.get("login"), realm=g.logged_in_user.get("realm"))
        user_role = g.logged_in_user.get("role")

        container_serial = self._get_container_serial(request, content)
        if not container_serial:
            container_serial = self._get_container_serial_from_token(request, content, g)

        if action.lower() in [ACTION_TYPE.DELETE,
                              ACTION_TYPE.UNASSIGN,
                              ACTION_TYPE.ASSIGN,
                              ACTION_TYPE.SET_STATES,
                              ACTION_TYPE.ADD_STATES,
                              ACTION_TYPE.SET_DESCRIPTION,
                              ACTION_TYPE.REMOVE_TOKENS,
                              ACTION_TYPE.SET_CONTAINER_INFO,
                              ACTION_TYPE.ADD_CONTAINER_INFO,
                              ACTION_TYPE.DELETE_CONTAINER_INFO,
                              ACTION_TYPE.DISABLE_TOKENS,
                              ACTION_TYPE.ENABLE_TOKENS]:
            if container_serial:
                log.info(f"{action} for container {container_serial}")
                if action.lower() == ACTION_TYPE.DELETE:
                    delete_container_by_serial(container_serial, user, user_role)

                elif action.lower() == ACTION_TYPE.UNASSIGN:
                    container = find_container_by_serial(container_serial)
                    container_owners = container.get_users()
                    if len(container_owners) == 0:
                        ret = False
                        log.debug(f"No user found to unassign from container {container_serial}")
                    for c_user in container_owners:
                        unassign_user(container_serial, c_user, user, user_role)

                elif action.lower() == ACTION_TYPE.ASSIGN:
                    users = self._get_users_from_request(request)
                    if len(users) == 0:
                        ret = False
                        log.debug(f"No user found to assign to container {container_serial}")
                    for c_user in users:
                        assign_user(container_serial, c_user, user, user_role)

                elif action.lower() == ACTION_TYPE.SET_STATES:
                    container_states = list(TokenContainerClass.get_state_types().keys())
                    selected_states = []
                    for state in container_states:
                        if handler_options.get(state):
                            selected_states.append(state)
                    if len(selected_states) > 0:
                        set_container_states(container_serial, selected_states, user, user_role)
                    else:
                        ret = False
                        log.debug(
                            f"No valid state found in the handler options {handler_options} "
                            f"to set in container {container_serial}")

                elif action.lower() == ACTION_TYPE.ADD_STATES:
                    container_states = list(TokenContainerClass.get_state_types().keys())
                    selected_states = []
                    for state in container_states:
                        if handler_options.get(state):
                            selected_states.append(state)
                    if len(selected_states) > 0:
                        add_container_states(container_serial, selected_states, user, user_role)
                    else:
                        ret = False
                        log.debug(f"No states found to add to container {container_serial}")

                elif action.lower() == ACTION_TYPE.SET_DESCRIPTION:
                    new_description = handler_options.get("description")
                    if new_description:
                        set_container_description(container_serial, new_description, user, user_role)
                    else:
                        ret = False
                        log.debug(f"No description found to set in container {container_serial}")

                elif action.lower() == ACTION_TYPE.REMOVE_TOKENS:
                    container = find_container_by_serial(container_serial)
                    tokens = container.get_tokens()
                    token_serials = [t.get_serial() for t in tokens]
                    if len(token_serials) > 0:
                        remove_multiple_tokens_from_container(container_serial, token_serials, user, user_role)
                    else:
                        log.debug(f"No tokens found to remove from container {container_serial}")

                elif action.lower() == ACTION_TYPE.SET_CONTAINER_INFO:
                    key = handler_options.get("key")
                    value = handler_options.get("value") or ""
                    info = {key: value}
                    set_container_info(container_serial, info, user, user_role)

                elif action.lower() == ACTION_TYPE.ADD_CONTAINER_INFO:
                    key = handler_options.get("key")
                    value = handler_options.get("value") or ""
                    add_container_info(container_serial, key, value, user, user_role)

                elif action.lower() == ACTION_TYPE.DELETE_CONTAINER_INFO:
                    delete_container_info(container_serial, ikey=None, user=user, user_role=user_role)

                elif action.lower() == ACTION_TYPE.DISABLE_TOKENS:
                    container = find_container_by_serial(container_serial)
                    tokens = container.get_tokens()
                    for token in tokens:
                        enable_token(token.get_serial(), enable=False, user=user)

                    if len(tokens) == 0:
                        log.debug(f"No tokens found to disable in container {container_serial}")

                elif action.lower() == ACTION_TYPE.ENABLE_TOKENS:
                    container = find_container_by_serial(container_serial)
                    tokens = container.get_tokens()
                    for token in tokens:
                        enable_token(token.get_serial(), enable=True, user=user)

                    if len(tokens) == 0:
                        log.debug(f"No tokens found to enable in container {container_serial}")

            else:
                log.debug(f"Action {action} requires serial number. But no valid serial "
                          f"number could be found in request {request}.")
                ret = False

        if action.lower() == ACTION_TYPE.INIT:
            if handler_options.get("type"):
                params = {
                    "type": handler_options.get("type"),
                    "description": handler_options.get("description"),
                }
                users = []
                if handler_options.get("user"):
                    users = self._get_users_from_request(request)

                    if len(users) > 0 and not users[0].is_empty():
                        params["user"] = users[0].login
                        params["realm"] = users[0].realm
                    else:
                        log.debug(f"No user found to assign to container {container_serial}")

                new_serial = init_container(params)
                # assign remaining users to container
                for user in users[1:]:
                    container = find_container_by_serial(new_serial)
                    if container and not user.is_empty():
                        container.add_user(user)

                if handler_options.get("token"):
                    token_serial = request.all_data.get("serial") or \
                                   content.get("detail", {}).get("serial") or \
                                   g.audit_object.audit_data.get("serial")
                    if token_serial:
                        user = request.User
                        user_role = g.logged_in_user.get("role")
                        add_multiple_tokens_to_container(new_serial, [token_serial], user=user, user_role=user_role)
                    else:
                        log.debug(f"No token found to add to container {new_serial}")

            else:
                ret = False
                log.debug(f"Action {action} requires container type. But no type "
                          f"could be found in the handler options {handler_options}.")

        return ret
