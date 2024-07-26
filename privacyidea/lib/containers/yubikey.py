import logging

from privacyidea.lib.containerclass import TokenContainerClass

log = logging.getLogger(__name__)


class YubikeyContainer(TokenContainerClass):

    def __init__(self, db_container):
        super().__init__(db_container)

    @classmethod
    def get_class_type(cls):
        """
        Returns the type of the container class.
        """
        return "yubikey"

    @classmethod
    def get_supported_token_types(cls):
        """
        Returns the token types that are supported by the container class.
        """
        return ["hotp", "certificate", "webauthn", "yubico", "yubikey"]

    @classmethod
    def get_class_prefix(cls):
        """
        Returns the container class specific prefix for the serial.
        """
        return "YUBI"

    @classmethod
    def get_class_description(cls):
        """
        Returns a description of the container class.
        """
        return "Yubikey hardware device that can hold HOTP, certificate and webauthn token"
