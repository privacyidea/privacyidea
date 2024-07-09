import logging

from privacyidea.lib.containerclass import TokenContainerClass

log = logging.getLogger(__name__)


class SmartphoneContainer(TokenContainerClass):

    def __init__(self, db_container):
        super().__init__(db_container)

    @classmethod
    def get_class_type(cls):
        """
        Returns the type of the container class.
        """
        return "smartphone"

    @classmethod
    def get_supported_token_types(cls):
        """
        Returns the token types that are supported by the container class.
        """
        return ["hotp", "totp", "push", "daypassword", "sms"]

    @classmethod
    def get_container_policy_info(cls):
        """
        Returns the policy information of the container class.
        """
        res = {
            "token_count": {"type": "int",
                            "value": "any",
                            "desc": "The maximum number of tokens in this container"},
            "token_types": {"type": "list",
                            "value": cls.get_supported_token_types(),
                            "desc": "The token types that can be stored in this container"},
            "user_modifiable": {"type": "bool",
                                "value": ["true", "false"],
                                "desc": "Whether the user can modify the tokens in this container"}
        }

        return res

    @classmethod
    def get_class_prefix(cls):
        """
        Returns the container class specific prefix for the serial.
        """
        return "SMPH"

    @classmethod
    def get_class_description(cls):
        """
        Returns a description of the container class.
        """
        return "A smartphone that uses an authenticator app."
