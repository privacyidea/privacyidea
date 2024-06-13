__doc__ = """This is the event handler module for container actions.
"""

from privacyidea.lib.container import get_container_classes, delete_container_by_serial, init_container, \
    find_container_by_serial, find_container_for_token, remove_tokens_from_container, get_all_containers, \
    add_tokens_to_container
from privacyidea.lib.containerclass import TokenContainerClass
from privacyidea.lib.eventhandler.base import BaseEventHandler
from privacyidea.lib import _
import logging

from privacyidea.lib.token import get_tokens, enable_token

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
                    delete_container_by_serial(container_serial)

                elif action.lower() == ACTION_TYPE.UNASSIGN:
                    users = self._get_users_from_request(request)
                    container = find_container_by_serial(container_serial)
                    ret = False
                    for user in users:
                        if not user.is_empty():
                            container.remove_user(user)
                            ret = True
                    if not ret:
                        log.debug(f"No user found to unassign from container {container_serial}")

                elif action.lower() == ACTION_TYPE.ASSIGN:
                    users = self._get_users_from_request(request)
                    container = find_container_by_serial(container_serial)
                    ret = False
                    for user in users:
                        if not user.is_empty():
                            container.add_user(user)
                            ret = True
                    if not ret:
                        log.debug(f"No user found to assign to container {container_serial}")

                elif action.lower() == ACTION_TYPE.SET_STATES:
                    container_states = list(TokenContainerClass.get_state_types().keys())
                    selected_states = []
                    for state in container_states:
                        if handler_options.get(state):
                            selected_states.append(state)
                    container = find_container_by_serial(container_serial)
                    if len(selected_states) > 0:
                        container.set_states(selected_states)
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
                    container = find_container_by_serial(container_serial)
                    if len(selected_states) > 0:
                        container.add_states(selected_states)
                    else:
                        ret = False
                        log.debug(f"No states found to add to container {container_serial}")

                elif action.lower() == ACTION_TYPE.SET_DESCRIPTION:
                    new_description = handler_options.get("description")
                    if new_description:
                        container = find_container_by_serial(container_serial)
                        container.description = new_description
                    else:
                        ret = False
                        log.debug(f"No description found to set in container {container_serial}")

                elif action.lower() == ACTION_TYPE.REMOVE_TOKENS:
                    container = find_container_by_serial(container_serial)
                    tokens = container.get_tokens()
                    token_serials = [t.get_serial() for t in tokens]
                    if len(token_serials) > 0:
                        remove_tokens_from_container(container_serial, token_serials)
                    else:
                        log.debug(f"No tokens found to remove from container {container_serial}")

                elif action.lower() == ACTION_TYPE.SET_CONTAINER_INFO:
                    key = handler_options.get("key")
                    value = handler_options.get("value") or ""
                    container = find_container_by_serial(container_serial)
                    info = {key: value}
                    container.set_containerinfo(info)

                elif action.lower() == ACTION_TYPE.ADD_CONTAINER_INFO:
                    key = handler_options.get("key")
                    value = handler_options.get("value") or ""
                    container = find_container_by_serial(container_serial)
                    container.add_containerinfo(key, value)

                elif action.lower() == ACTION_TYPE.DELETE_CONTAINER_INFO:
                    container = find_container_by_serial(container_serial)
                    container.delete_container_info()

                elif action.lower() == ACTION_TYPE.DISABLE_TOKENS:
                    container = find_container_by_serial(container_serial)
                    tokens = container.get_tokens()
                    for token in tokens:
                        token.enable(False)
                        token.save()

                    if len(tokens) == 0:
                        log.debug(f"No tokens found to disable in container {container_serial}")

                elif action.lower() == ACTION_TYPE.ENABLE_TOKENS:
                    container = find_container_by_serial(container_serial)
                    tokens = container.get_tokens()
                    for token in tokens:
                        token.enable(True)
                        token.save()

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
                        add_tokens_to_container(new_serial, [token_serial])
                    else:
                        log.debug(f"No token found to add to container {new_serial}")

            else:
                ret = False
                log.debug(f"Action {action} requires container type. But no type "
                          f"could be found in the handler options {handler_options}.")

        return ret
