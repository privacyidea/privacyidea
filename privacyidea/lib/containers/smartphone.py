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
