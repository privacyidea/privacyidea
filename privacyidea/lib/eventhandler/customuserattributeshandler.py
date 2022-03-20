__doc__ = """This is the event handler module for custom user attributes.
You can set or delete custom your attributes

"""

from privacyidea.lib.eventhandler.base import BaseEventHandler
from privacyidea.lib import _
import logging

from privacyidea.lib.user import User

log = logging.getLogger(__name__)


class ACTION_TYPE(object):
    """
    Allowed actions
    """
    SET_CUSTOM_USER_ATTRIBUTES = "set_custom_user_attributes"
    DELETE_CUSTOM_USER_ATTRIBUTES = "delete_custom_user_attributes"


class USER_TYPE(object):
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
                    'description': _('The value of the custom user attribute.')}
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
                        "attribute! action: {0!s}, handler: {1!s}".format(action, handler_def))
            return False

        attrkey = handler_options.get("attrkey")
        attrvalue = handler_options.get("attrvalue")
        if action.lower() == "set_custom_user_attributes":
            ret = user.set_attribute(attrkey, attrvalue)
        elif action.lower() == "delete_custom_user_attributes":
            ret = user.delete_attribute(attrkey)
        else:
            log.warning('Unknown action value: {0!s}'.format(action))
            ret = False

        return ret
