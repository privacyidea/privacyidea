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
import base64
import logging
from datetime import timezone
from urllib.parse import quote

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey
from flask import json

from privacyidea.api.lib.utils import getParam
from privacyidea.lib import _
from privacyidea.lib.apps import _construct_extra_parameters
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.containerclass import TokenContainerClass
from privacyidea.lib.containers.smartphone_options import SmartphoneOptions
from privacyidea.lib.crypto import (geturandom, encryptPassword, b64url_str_key_pair_to_ecc_obj,
                                    generate_keypair_ecc, encrypt_aes)
from privacyidea.lib.error import ContainerInvalidChallenge, ContainerNotRegistered
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.utils import create_img
from privacyidea.models import Challenge

log = logging.getLogger(__name__)


def create_container_registration_url(nonce: str, time_stamp: str, server_url: str, container_serial: str,
                                      key_algorithm: str, hash_algorithm: str, extra_data: dict = None,
                                      passphrase: str = "", issuer: str = "privacyIDEA", ttl: int = 10,
                                      ssl_verify: bool = True) -> str:
    """
    Create a URL for binding a container to a physical container.

    :param nonce: Nonce (some random bytes).
    :param time_stamp: Time stamp of the registration in iso format.
    :param server_url: URL of the server reachable for the client.
    :param container_serial: Serial of the container.
    :param key_algorithm: Algorithm to use to generate the ECC key pair, e.g. 'secp384r1'.
    :param hash_algorithm: Hash algorithm to be used in the signing algorithm, e.g. 'SHA256'.
    :param extra_data: Extra data to be included in the URL.
    :param passphrase: Passphrase Prompt to be displayed to the user in the app.
    :param issuer: Issuer of the registration, e.g. 'privacyIDEA'.
    :param ttl: Time to live of the URL in seconds.
    :param ssl_verify: Whether the smartphone shall verify the SSL certificate of the server.
    :return: URL for binding a container to a physical container.
    """
    url_nonce = quote(nonce.encode("utf-8"))
    url_time_stamp = quote(time_stamp.encode("utf-8"))
    url_label = quote(container_serial.encode("utf-8"))
    url_issuer = quote(issuer.encode("utf-8"))
    extra_data = extra_data or {}
    url_extra_data = _construct_extra_parameters(extra_data)
    url_passphrase = quote(passphrase.encode("utf-8"))
    url_key_algorithm = quote(key_algorithm.encode("utf-8"))
    url_hash_algorithm = quote(hash_algorithm.encode("utf-8"))
    url_ssl_verify = quote(ssl_verify.encode("utf-8"))
    url_server_url = quote(server_url.encode("utf-8"))

    url = (f"pia://container/{url_label}?issuer={url_issuer}&ttl={ttl}&nonce={url_nonce}&time={url_time_stamp}"
           f"&url={url_server_url}&serial={container_serial}&key_algorithm={url_key_algorithm}"
           f"&hash_algorithm={url_hash_algorithm}&ssl_verify={url_ssl_verify}"
           f"&passphrase={url_passphrase}{url_extra_data}")
    return url


class SmartphoneContainer(TokenContainerClass):
    # The first value in the list is the default value
    options = {SmartphoneOptions.KEY_ALGORITHM: ["secp384r1"],
               SmartphoneOptions.HASH_ALGORITHM: ["SHA256"],
               SmartphoneOptions.ENCRYPT_KEY_ALGORITHM: ["x25519"],
               SmartphoneOptions.ENCRYPT_ALGORITHM: ["AES"],
               SmartphoneOptions.ENCRYPT_MODE: ["GCM"]}

    def __init__(self, db_container):
        super().__init__(db_container)

    @classmethod
    def get_class_type(cls) -> str:
        """
        Returns the type of the container class.
        """
        return "smartphone"

    @classmethod
    def get_supported_token_types(cls) -> list[str]:
        """
        Returns the token types that are supported by the container class.
        """
        supported_token_types = ["hotp", "totp", "push", "daypassword", "sms"]
        supported_token_types.sort()
        return supported_token_types

    @classmethod
    def get_class_prefix(cls) -> str:
        """
        Returns the container class specific prefix for the serial.
        """
        return "SMPH"

    @classmethod
    def get_class_description(cls) -> str:
        """
        Returns a description of the container class.
        """
        return _("A smartphone that uses an authenticator app.")

    def get_tokens_for_synchronization(self) -> list[TokenClass]:
        """
        Returns the tokens of the container that can be synchronized with a client as a list of TokenClass objects.
        """
        return [token for token in self.tokens if token.get_tokentype() != "sms"]

    def init_registration(self, server_url: str, scope: str, registration_ttl: int, ssl_verify: bool,
                          params: dict = None) -> dict:
        """
        Initializes the registration: Generates a QR code containing all relevant data.

        :param server_url: URL of the server reachable for the client.
        :param scope: The URL the client contacts to finalize the registration e.g. "https://pi.net/container/register/finalize".
        :param registration_ttl: Time to live of the registration link in minutes.
        :param ssl_verify: Whether the client shall use ssl.
        :param params: Container specific parameters in the format:

        ::

            {
                "passphrase_prompt": <str, the prompt for the passphrase displayed in the app>, (optional)
                "passphrase_response": <str, passphrase>, (optional)
                "extra_data": <dict, any additional data>, (optional)
            }

        :return: A dictionary with the registration data

        An example of a returned dictionary:
            ::

                {
                    "container_url": {
                        "description": "URL for privacyIDEA Container Registration",
                        "value": <url>,
                        "img": <qr code of the url>
                    },
                    "nonce": "ajhbdsuiuojno49877n4no3u09on38r98n",
                    "time_stamp": "2020-08-25T14:00:00.000000+00:00",
                    "key_algorithm": "secp384r1",
                    "hash_algorithm": "SHA256",
                    "ssl_verify": "True",
                    "ttl": 10,
                    "passphrase": <Passphrase prompt displayed to the user in the app> (optional)
                }
        """
        # get params
        params = params or {}
        extra_data = getParam(params, 'extra_data', optional=True) or {}
        passphrase_ad = getParam(params, 'passphrase_ad', optional=True) or False
        passphrase_prompt = getParam(params, 'passphrase_prompt', optional=True) or ""
        passphrase_response = getParam(params, 'passphrase_response', optional=True) or ""
        if passphrase_ad:
            if not passphrase_prompt:
                passphrase_prompt = "Please enter your AD passphrase."
        if passphrase_response:
            passphrase_response = encryptPassword(passphrase_response)
        challenge_params = {"scope": scope, "passphrase_prompt": passphrase_prompt,
                            "passphrase_response": passphrase_response,
                            "passphrase_ad": passphrase_ad}

        # Delete all other challenges for this container
        challenge_list = get_challenges(serial=self.serial)
        for challenge in challenge_list:
            challenge.delete()

        # Create challenge
        res = self.create_challenge(scope=scope, validity_time=registration_ttl, data=challenge_params)
        time_stamp_iso = res["time_stamp"]
        nonce = res["nonce"]

        # set all options and get algorithms
        class_options = self.get_class_options()
        options = {}
        for key in list(class_options.keys()):
            value = self.set_default_option(key)
            if value is not None:
                options[key] = value
        key_algorithm = options[SmartphoneOptions.KEY_ALGORITHM]
        hash_algorithm = options[SmartphoneOptions.HASH_ALGORITHM]

        # Generate URL
        qr_url = create_container_registration_url(nonce=nonce,
                                                   time_stamp=time_stamp_iso,
                                                   server_url=server_url,
                                                   container_serial=self.serial,
                                                   key_algorithm=key_algorithm,
                                                   hash_algorithm=hash_algorithm,
                                                   passphrase=passphrase_prompt,
                                                   ttl=registration_ttl,
                                                   ssl_verify=ssl_verify,
                                                   extra_data=extra_data)
        # Generate QR code
        qr_img = create_img(qr_url)

        # Set container info
        self.add_container_info("registration_state", "client_wait")

        # Response
        response_detail = {"container_url": {"description": _("URL for privacyIDEA Container Registration"),
                                             "value": qr_url,
                                             "img": qr_img},
                           "nonce": nonce,
                           "time_stamp": time_stamp_iso,
                           "key_algorithm": key_algorithm,
                           "hash_algorithm": hash_algorithm,
                           "ssl_verify": ssl_verify,
                           "ttl": registration_ttl,
                           "passphrase_prompt": passphrase_prompt,
                           "server_url": server_url}

        return response_detail

    def finalize_registration(self, params: dict) -> dict[str, bool]:
        """
        Finalize the registration of a container.
        Validates whether the smartphone is authorized to register. If successful, the registration state is set as
        registered and the client public key is stored in the container info.
        Raises a ContainerInvalidSignature error if the signature is not valid.

        The message the client shall sign is a concatenation of the following values separated by '|':
            * nonce (from the registration challenge)
            * timestamp (from the registration challenge)
            * serial of the container
            * scope: The URL the client contacts to finalize the registration, e.g.
              "https://pi.net/container/register/finalize"
            * device brand (optional)
            * device model (optional)
            * passphrase response if defined in the registration challenge
            * public key of the client in PEM format (curve secp384r1)

        ::

            message = <nonce>|<time>|<serial>|<scope>|<device_brand>|<device_model>|<passphrase_response>|<public_key_client>

        To verify the signature, the ECDSA signature algorithm with SHA256 hash function is used. The public key is
        expected to be an ecc key of curve secp384r1.

        :param params: The parameters from the smartphone for the registration as dictionary like:

        ::

            {
                "container_serial": <serial of the container, str>,
                "signature": <sign(message), str>,
                "public_client_key": <public key of the smartphone serialized in the PEM format>,
                "device_brand": <Brand of the smartphone, str> (optional),
                "device_model": <Model of the smartphone, str> (optional),
            }

        :return: A dictionary with the success status like ``{"success": True}``
        """
        # Get params
        signature = base64.urlsafe_b64decode(getParam(params, "signature", optional=False))
        pub_key_container_str = getParam(params, "public_client_key", optional=False)
        keys_container = b64url_str_key_pair_to_ecc_obj(public_key_str=pub_key_container_str)
        scope = getParam(params, "scope", optional=False)
        device_brand = getParam(params, "device_brand", optional=True)
        device_model = getParam(params, "device_model", optional=True)
        device = ""
        if device_brand:
            device += device_brand
        if device_model:
            device += f" {device_model}"

        # Verifies challenge
        valid = self.validate_challenge(signature, keys_container.public_key, scope=scope, device_brand=device_brand,
                                        device_model=device_model)
        if not valid:
            raise ContainerInvalidChallenge('Could not verify signature!')

        # Update container info
        new_container_info = {"public_key_client": pub_key_container_str}

        if device != "":
            new_container_info["device"] = device
        else:
            # this might be a rollover, delete old device information
            self.delete_container_info("device")

        # The rollover is completed with the first synchronization
        container_info = self.get_container_info_dict()
        registration_state = container_info.get("registration_state", "")
        if registration_state != "rollover":
            new_container_info["registration_state"] = "registered"

        # check right for initial token transfer
        if params.get("client_policies", {}).get("initially_add_tokens_to_container"):
            new_container_info["initially_synchronized"] = "False"

        # update container info
        self.update_container_info(new_container_info)

        return {"success": True}

    def terminate_registration(self):
        """
        Terminate the synchronisation of the container with privacyIDEA.
        The associated information is deleted from the container info and all challenges for this container are deleted
        as well.
        """
        # Delete registration / synchronization info
        self.delete_container_info("public_key_client")
        self.delete_container_info("device")
        self.delete_container_info("server_url")
        self.delete_container_info("registration_state")
        self.delete_container_info("challenge_ttl")
        self.delete_container_info("initially_synchronized")

    def create_challenge(self, scope: str, validity_time: int = 2, data: dict = None) -> dict[str, str]:
        """
        Create a challenge for the container.

        :param scope: The scope (endpoint) of the challenge, e.g. "https://pi.com/container/SMPH001/sync"
        :param validity_time: The validity time of the challenge in minutes.
        :param data: Additional data for the challenge.
        :return: A dictionary with the challenge data in the format:
            ::

                {
                    "nonce": <nonce, str>,
                    "time_stamp": <time stamp iso format, str>,
                    "enc_key_algorithm": <encryption key algorithm, str>
                }
        """
        data = data or {}

        # Create challenge
        nonce = geturandom(20, hex=True)
        data["scope"] = scope
        data["type"] = "container"
        data_str = json.dumps(data)
        if validity_time:
            validity_time *= 60
        db_challenge = Challenge(serial=self.serial, challenge=nonce, data=data_str, validitytime=validity_time)
        db_challenge.save()
        timestamp = db_challenge.timestamp.replace(tzinfo=timezone.utc)
        time_stamp_iso = timestamp.isoformat()

        # Get encryption info (optional)
        container_info = self.get_container_info_dict()
        enc_key_algorithm = container_info.get(SmartphoneOptions.ENCRYPT_KEY_ALGORITHM)

        res = {"nonce": nonce,
               "time_stamp": time_stamp_iso,
               "enc_key_algorithm": enc_key_algorithm}
        return res

    def check_challenge_response(self, params: dict) -> bool:
        """
        Checks if the response to a challenge is valid:
            * Challenge exists and is not expired
            * Equal scope
            * Valid signature

        The message the client shall sign is a concatenation of the following values separated by '|':
            * nonce (from the challenge)
            * timestamp (from the challenge)
            * serial of the container
            * scope: The URL the client wants to contact, e.g. "https://pi.net/container/register/finalize"
            * ecc public key of the client in PEM format (optional)
            * container dict of the client (optional)

        :param params: Dictionary with the parameters for the challenge. The device information is optional.

        An example params dictionary:
            ::

                {
                    "signature": <sign(nonce|timestamp|serial|scope|pub_key|container_dict)>,
                    "public_client_key_encry": <public key of the client for encryption base 64 url safe encoded>,
                    "container_dict_client": {"serial": "SMPH0001", "type": "smartphone",
                        "tokens": [{"serial": "1234", "type": "HOTP"}]...}
                    "scope": "https://pi/container/SMPH001/sync",
                    "device_brand": "XYZ",
                    "device_model": "123"
                }

        :return: True if a valid challenge exists, raises a privacyIDEAError otherwise.
        """
        # Get params
        signature = base64.urlsafe_b64decode(getParam(params, "signature", optional=False))
        pub_key_encr_container_str = getParam(params, "public_enc_key_client", optional=True)
        container_client_str = getParam(params, "container_dict_client", optional=True)
        scope = getParam(params, "scope", optional=False)
        device_brand = getParam(params, "device_brand", optional=True)
        device_model = getParam(params, "device_model", optional=True)

        try:
            pub_key_sig_container_str = self.get_container_info_dict()["public_key_client"]
        except KeyError:
            raise ContainerNotRegistered("The container is not registered or was unregistered!")
        sig_keys_container = b64url_str_key_pair_to_ecc_obj(public_key_str=pub_key_sig_container_str)

        # Validate challenge
        valid_challenge = self.validate_challenge(signature, sig_keys_container.public_key, scope=scope,
                                                  key=pub_key_encr_container_str,
                                                  container=container_client_str,
                                                  device_brand=device_brand,
                                                  device_model=device_model)
        if not valid_challenge:
            raise ContainerInvalidChallenge('Could not verify signature!')

        return valid_challenge

    def encrypt_dict(self, container_dict: dict, params: dict) -> dict:
        """
        Encrypt a container dictionary.

        :param container_dict: The container dictionary to be encrypted.
        :param params: Dictionary with the parameters for the encryption from the client.
        :return: Dictionary with the encrypted container dictionary and further encryption parameters

        An example of a returned dictionary:
            ::

                {
                    "public_server_key": <public key of the server for encryption base 64 url safe encoded>,
                    "encryption_algorithm": "AES",
                    "encryption_params": {"mode": "GCM", "init_vector": "init_vector", "tag": "tag"},
                    "container_dict_server": <encrypted container dict from server>
                }
        """
        pub_key_encr_container_str = getParam(params, "public_enc_key_client", optional=False)
        pub_key_encr_container_bytes = base64.urlsafe_b64decode(pub_key_encr_container_str)
        pub_key_encr_container = X25519PublicKey.from_public_bytes(pub_key_encr_container_bytes)

        # Generate encryption key pair for the server
        container_info = self.get_container_info_dict()
        enc_key_algorithm = container_info.get(SmartphoneOptions.ENCRYPT_KEY_ALGORITHM)
        encr_server = generate_keypair_ecc(enc_key_algorithm)
        public_key_encr_server_str = base64.urlsafe_b64encode(encr_server.public_key.public_bytes_raw()).decode('utf-8')

        # encrypt container dict
        session_key = encr_server.private_key.exchange(pub_key_encr_container)
        container_dict_bytes = json.dumps(container_dict).encode('utf-8')
        encryption_params = encrypt_aes(container_dict_bytes, session_key)
        container_dict_encrypted = encryption_params["cipher"]
        del encryption_params["cipher"]

        res = {"encryption_algorithm": "AES",
               "encryption_params": encryption_params,
               "container_dict_server": container_dict_encrypted,
               "public_server_key": public_key_encr_server_str}
        return res
