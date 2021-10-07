__doc__ = """This is the event handler module for custom user attributes.
You can set or delete custom your attributes

"""

from privacyidea.lib.eventhandler.base import BaseEventHandler
from privacyidea.lib.user import User
from privacyidea.lib import _
import logging

log = logging.getLogger(__name__)

class USER_TYPE(object):
    """
    Allowed token owner
    """
    TOKENOWNER = "tokenowner"
    LOGGED_IN_USER = "logged_in_user"


class CustomUserAttributesHandler(BaseEventHandler):
    """
    An Eventhandler needs to return a list of actions, which it can handle.

    It also returns a list of allowed action and conditions

    It returns an identifier, which can be used in the eventhandlig definitions
    """

    identifier = "CustomUserAttributes"
    description = "This event handler can set and delete custom_user_attributes"

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
            "set_custom_user_attributes": {
                "user" : {
                    'type': 'str',
                    'required': True,
                    'description': ["logged in user", "tokenowner"],
                    "value": [
                        USER_TYPE.TOKENOWNER,
                        USER_TYPE.LOGGED_IN_USER,
                    ]},
                "attrkey": {
                    'type': 'str',
                    'description': _('The key of the custom user attribute that should be set.')},
                "attrvalue": {
                    'type': 'str',
                    'description': _('The value of the attribute')}
            },
            "delete_custom_user_attributes": {
                "user": {
                    'type': 'user',
                    'description': _('Delete the specified attribute of the user.')}
        }}
        return actions

    def do(self, action, options=None):
        """
        This method executes the defined action in the given event.

        :param action:
        :param options: Contains the flask parameters g,  attrkey and attrvalue
        :type options: dict
        :return:
        """
        ret = True
        g = options.get("g")
        request = options.get("request")
        handler_def = options.get("handler_def")
        handler_options = handler_def.get("options", {})
        user_type = handler_options.get("user", USER_TYPE.TOKENOWNER)
        try:
            logged_in_user = g.logged_in_user
        except Exception:
            logged_in_user = {}
        tokenowner = self._get_tokenowner(request)
        if user_type == USER_TYPE.TOKENOWNER and not tokenowner.is_empty():
            user = tokenowner
        elif user_type == USER_TYPE.LOGGED_IN_USER:
            user = logged_in_user
        else:
            log.warning("Was not able to determine the recipient for the user "
                        "notification: {0!s}".format(handler_def))

        attrkey = options.get("attrkey")
        attrvalue = options.get("attrvalue")
        if action.lower() in ["set_custom_user_attributes",
                              "delete_custom_user_attributes"]:
            if action.lower() == "set_custom_user_attributes":
                ret = user.set_attribute(attrkey, attrvalue)
            elif action.lower() == "delete_custom_user_attributes":
                ret = user.delete_attribute(attrkey)

        return ret
