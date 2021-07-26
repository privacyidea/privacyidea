__doc__ = """This is the event handler module for custom user attributes.
You can set or delete custom your attributes

"""

from privacyidea.lib.eventhandler.base import BaseEventHandler
from privacyidea.lib.user import User
from privacyidea.lib import _
import logging

log = logging.getLogger(__name__)


class VALIDITY(object):
    """
    Allowed validity options
    """
    START = "valid from"
    END = "valid till"


class CustomUserAttributesHandler(BaseEventHandler):
    """
    An Eventhandler needs to return a list of actions, which it can handle.

    It also returns a list of allowed action and conditions

    It returns an identifier, which can be used in the eventhandlig definitions
    """

    identifier = "Custom_User_Attributes"
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
        actions = {"set_custom_user_attributes":
            {"attrkey": {
                'type': 'str',
                'discription': _('The key of the attribute')
            },
                "attrvalue": {
                    'type': 'str',
                    'discription': _('The value of the attribute')
                }
            },
            "delete_custom_user_attributes":
                {"user": {
                    'type': 'user',
                    'discription': _('An object from the class user')
                }
                }
        }
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
        attrkey = options.get("attrkey")
        attrvalue = options.get("attrvalue")
        logged_in_user = g.logged_in_user
        if action.lower() in ["set_custom_user_attributes",
                              "delete_custom_user_attributes"]:
            if action.lower() == "set_custom_user_attributes":
                ret = logged_in_user.set_attribute(attrkey, attrvalue)
            elif action.lower() == "delete_custom_user_attributes":
                ret = User.delete_attribute(logged_in_user)

        return ret
