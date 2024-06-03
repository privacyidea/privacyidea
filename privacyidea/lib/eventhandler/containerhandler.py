__doc__ = """This is the event handler module for container actions.
"""

from privacyidea.lib.container import get_container_classes, delete_container_by_serial, init_container, \
    find_container_by_serial, find_container_for_token, remove_tokens_from_container, get_all_containers
from privacyidea.lib.containerclass import TokenContainerClass
from privacyidea.lib.eventhandler.base import BaseEventHandler
from privacyidea.lib import _
import logging

from privacyidea.lib.token import get_tokens

log = logging.getLogger(__name__)


class ACTION_TYPE(object):
    """
    Allowed actions
    """
    INIT = "create"
    DELETE = "delete"
    UNASSIGN = "unassign"
    SET_STATES = "set states"
    SET_DESCRIPTION = "set description"
    SET_CONTAINER_INFO = "set container info"
    ADD_CONTAINER_INFO = "add container info"
    DELETE_CONTAINER_INFO = "delete container info"
    REMOVE_TOKENS = "remove all tokens"


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
                 },
            ACTION_TYPE.DELETE: {},
            ACTION_TYPE.UNASSIGN: {},
            ACTION_TYPE.SET_STATES: action_states,
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
            ACTION_TYPE.DELETE_CONTAINER_INFO: {}
        }
        return actions

    def do(self, action, options):
        """
        Executes the defined action in the given event.

        :param action:
        :param options: Contains the flask parameters g, request, response
            and the handler_def configuration
        :type options: dict
        :return:
        """
        ret = True
        g = options.get("g")
        request = options.get("request")
        response = options.get("response")
        content = self._get_response_content(response)
        handler_def = options.get("handler_def")
        handler_options = handler_def.get("options", {})

        # TODO: Differentiate container and token serials in all requests or by the serials themselves
        # serial = request.all_data.get("container_serial") or \
        #          request.all_data.get("serial") or \
        #          content.get("result", {}).get('value', {}).get("serial") or \
        #          g.audit_object.audit_data.get("serial")
        # container_serial = serial_is_from_container(serial)
        container_serial = get_container_serial(request, content, g)

        if container_serial:
            log.info(f"{action} for container {container_serial}")
            if action.lower() == ACTION_TYPE.DELETE:
                delete_container_by_serial(container_serial)

            elif action.lower() == ACTION_TYPE.UNASSIGN:
                users = self._get_users_from_request(request)
                container = find_container_by_serial(container_serial)
                for user in users:
                    if not user.is_empty():
                        container.remove_user(user)

            elif action.lower() == ACTION_TYPE.SET_STATES:
                container_states = list(TokenContainerClass.get_state_types().keys())
                selected_states = []
                for state in container_states:
                    if handler_options.get(state):
                        selected_states.append(state)
                container = find_container_by_serial(container_serial)
                container.set_states(selected_states)

            elif action.lower() == ACTION_TYPE.SET_DESCRIPTION:
                new_description = handler_options.get("description") or ""
                container = find_container_by_serial(container_serial)
                container.description = new_description

            elif action.lower() == ACTION_TYPE.REMOVE_TOKENS:
                container = find_container_by_serial(container_serial)
                tokens = container.get_tokens()
                token_serials = [t.get_serial() for t in tokens]
                remove_tokens_from_container(container_serial, token_serials)

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
                container.delete_containerinfo()

        else:
            log.info(f"Action {action} requires serial number. But no serial "
                     f"number could be found in request {request}.")
            ret = False

        if action.lower() == ACTION_TYPE.INIT:
            params = {
                "type": handler_options.get("type"),
                "description": handler_options.get("description"),
            }
            if handler_options.get("user"):
                users = self._get_users_from_request(request)

                if len(users) > 0 and not users[0].is_empty():
                    params["user"] = users[0].login
                    params["realm"] = users[0].realm
            new_serial = init_container(params)
            # assign remaining users to container
            for user in users[1:]:
                container = find_container_by_serial(new_serial)
                if container and not user.is_empty():
                    container.add_user(user)

        return ret


def get_container_serial(request, content, g):
    """
    Get the container serial from the request, content or audit object.
    It checks if the serial is from a container or a token. In case it is from a token, it trys to get the container
    serial from the token.

    :param request: The request object
    :param content: The content of the response
    :param g: The g object
    :return: The container serial or None if no serial could be found
    """
    # Get serial from request
    serial = request.all_data.get("container_serial")

    if not serial:
        # get serial from request
        serial = request.all_data.get("serial")
        serial = serial_is_from_container(serial)

    if not serial:
        # get serial from response
        serial = content.get("result", {}).get('value', {}).get("serial")
        serial = serial_is_from_container(serial)

    if not serial:
        # get serial from audit object
        serial = g.audit_object.audit_data.get("serial")
        serial = serial_is_from_container(serial)

    return serial


def serial_is_from_container(serial):
    """
    Validates whether the given serial is from a container or a token. If it is from a token, it tries to get the
    container serial from the token.

    :param serial: The serial to validate
    :return: The container serial or None if the serial is not from a container and the token also has no container
    serial
    """
    container_serial = None
    # Check if a container exists with this serial
    containers = get_all_containers(serial=serial, pagesize=0, page=0)['containers']
    if len(containers) > 0:
        container_serial = serial
    else:
        # Check if a token exists with this serial and get the container serial
        tokens = get_tokens(serial=serial)
        if len(tokens) > 0:
            token = tokens[0]
            container = find_container_for_token(token.get_serial())
            if container:
                container_serial = container.serial

    return container_serial
