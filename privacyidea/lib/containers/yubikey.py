import logging

from privacyidea.api.lib.utils import verify_auth_token
from privacyidea.lib.containerclass import TokenContainerClass

log = logging.getLogger(__name__)


def verify_auth_token(params):
    """
    Verify the authentication token.
    """
    auth_token = params.get("auth_token")
    verify_auth_token(auth_token, ["user", "admin"])
    return True


class YubikeyContainer(TokenContainerClass):

    def __init__(self, db_container):
        super().__init__(db_container)

    def finalize_synchronization(self, params):
        """
        Finalize the synchronization of the container.
        """
        verify_auth_token(params)
        pass

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
