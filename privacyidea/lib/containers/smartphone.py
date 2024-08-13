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
# SPDX-FileCopyrightText: 2024 Nils Behlen <nils.behlen@netknights.it>
# SPDX-FileCopyrightText: 2024 Jelina Unger <jelina.unger@netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
#
import logging
from datetime import datetime, timezone
from urllib.parse import quote

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives._serialization import NoEncryption
from cryptography.hazmat.primitives.asymmetric import ec

from privacyidea.api.lib.utils import getParam
from privacyidea.lib import _
from privacyidea.lib.apps import _construct_extra_parameters
from privacyidea.lib.containerclass import TokenContainerClass
from privacyidea.lib.crypto import geturandom, encryptPassword
from privacyidea.lib.user import User
from privacyidea.lib.utils import create_img, to_bytes

log = logging.getLogger(__name__)


def create_container_registration_url(nonce, time_stamp, registration_url, container_serial, extra_data={},
                                      passphrase="", issuer="privacyIDEA"):
    """
    Create a URL for binding a container to a physical container.
    """
    # TODO: Aufbau url?
    url_nonce = quote(nonce.encode("utf-8"))
    url_time_stamp = quote(time_stamp.strftime("%Y-%m-%d:%M:%S%z").encode("utf-8"))
    url_label = quote(container_serial.encode("utf-8"))
    url_issuer = quote(issuer.encode("utf-8"))
    url_extra_data = _construct_extra_parameters(extra_data)
    url_passphrase = quote(passphrase.encode("utf-8"))

    url = (f"container://smartphone/{url_label}?issuer={url_issuer}?nonce={url_nonce}?time={url_time_stamp}"
           f"?url={registration_url}?serial={container_serial}?passphrase={url_passphrase}{url_extra_data}")
    return url


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

    def init_registration(self, params):
        """
        Initialize binding of a pi container to a physical container.
        Preparing the information that the smartphone requires to bind to the server.
        """
        container_owners = self.get_users()
        if len(container_owners) > 0:
            user = container_owners[0]
        else:
            user = User()

        binding_nonce = geturandom(20, hex=True)
        self.add_container_info("nonce", binding_nonce)

        time_stamp = datetime.now(timezone.utc)
        self.add_container_info("registration_time", time_stamp)

        image_url = params.get("appimageurl")
        extra_data = {}
        if image_url:
            extra_data["image"] = image_url

        # TODO: Somewhere the registration url has to be defined
        registration_url = getParam(params, 'container_registration_url', optional=False)

        qr_url = create_container_registration_url(nonce=binding_nonce,
                                                   time_stamp=time_stamp,
                                                   registration_url=registration_url,
                                                   container_serial=self.serial,
                                                   extra_data=extra_data)

        response_detail = {"containerUrl": {"description": _("URL for privacyIDEA Container Binding"),
                                            "value": qr_url,
                                            "img": create_img(qr_url)},
                           "nonce": binding_nonce}

        return response_detail

    def validate_registration(self, params):
        """
        Validate binding request of a pi container to a physical container.
        """
        # Get params
        signature = base64.b64decode(getParam(params, "signature", optional=False))
        pub_key_container_b64 = base64.b64decode(getParam(params, "public_key", optional=False))
        pub_key_container = serialization.load_pem_public_key(pub_key_container_b64)

        # Create message
        container_info = self.get_container_info_dict()
        registration_url = "http://test/container/register/initialization"
        message = f"{container_info['nonce']}|{container_info['registration_time']}|{registration_url}|{self.serial}"
        if "extra_data" in container_info.keys():
            for extra in container_info['extra_data']:
                message += f"|{extra.value}"

        # Check signature: Raises InvalidSignature if invalid, else returns None
        # TODO: Catch exception and throw privacyIDEA exception?
        pub_key_container.verify(signature, message.encode("utf-8"), ec.ECDSA(hashes.SHA256()))

        # Generate private + public key for the server
        private_key_server = ec.generate_private_key(ec.SECP384R1())
        private_key_server_b64 = base64.b64encode(
            private_key_server.private_bytes(encoding=serialization.Encoding.PEM,
                                             format=serialization.PrivateFormat.PKCS8,
                                             encryption_algorithm=NoEncryption()))
        public_key_server = private_key_server.public_key()
        public_key_server_b64 = base64.b64encode(
            public_key_server.public_bytes(encoding=serialization.Encoding.PEM,
                                           format=serialization.PublicFormat.SubjectPublicKeyInfo))
        public_key_server_str = public_key_server_b64.decode("utf-8")

        # Update container info
        self.add_container_info("public_key_container", pub_key_container_b64.decode('utf-8'))
        self.add_container_info("public_key_server", private_key_server_b64.decode('utf-8'))
        self.add_container_info("private_key_server", encryptPassword(public_key_server_str))
        self.delete_container_info("nonce")
        self.delete_container_info("registration_time")

        # TODO: Update state

        res = {"public_key": public_key_server_b64.decode('utf-8')}
        return res

    def terminate_registration(self):
        """
        Terminate the synchronisation of the container with privacyIDEA.
        """
        # Delete info from registration
        self.delete_container_info("nonce")
        self.delete_container_info("registration_time")

        # Delete keys
        self.delete_container_info("public_key_container")
        self.delete_container_info("public_key_server")
        self.delete_container_info("private_key_server")
