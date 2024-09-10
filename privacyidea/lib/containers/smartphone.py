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
from flask import json

from privacyidea.api.lib.utils import getParam
from privacyidea.lib import _
from privacyidea.lib.apps import _construct_extra_parameters
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.containerclass import TokenContainerClass
from privacyidea.lib.crypto import (geturandom, encryptPassword, b64url_str_key_pair_to_ecc_obj,
                                    ecc_key_pair_to_b64url_str, generate_keypair_ecc, encrypt_ecc, ecdh_key_exchange)
from privacyidea.lib.error import privacyIDEAError
from privacyidea.lib.token import get_tokens_from_serial_or_user, get_tokens, get_serial_by_otp_list
from privacyidea.lib.user import User
from privacyidea.lib.utils import create_img
from privacyidea.models import Challenge

log = logging.getLogger(__name__)


def create_container_registration_url(nonce, time_stamp, registration_url, container_serial, key_algorithm,
                                      hash_algorithm, extra_data={}, passphrase="", issuer="privacyIDEA"):
    """
    Create a URL for binding a container to a physical container.

    :param nonce: Nonce (some random bytes).
    :param time_stamp: Timestamp of the registration in iso format.
    :param registration_url: URL of the endpoint to finalize the registration.
    :param container_serial: Serial of the container.
    :param key_algorithm: Algorithm to use to generate the ECC key pair, e.g. 'secp384r1'.
    :param hash_algorithm: Hash algorithm to be used in the signing algorithm, e.g. 'SHA256'.
    :param extra_data: Extra data to be included in the URL.
    :param passphrase: Passphrase Prompt to be displayed to the user in the app.
    :param issuer: Issuer of the registration, e.g. 'privacyIDEA'.
    :return: URL for binding a container to a physical container.
    """
    url_nonce = quote(nonce.encode("utf-8"))
    url_time_stamp = quote(time_stamp.encode("utf-8"))
    url_label = quote(container_serial.encode("utf-8"))
    url_issuer = quote(issuer.encode("utf-8"))
    url_extra_data = _construct_extra_parameters(extra_data)
    url_passphrase = quote(passphrase.encode("utf-8"))
    url_key_algorithm = quote(key_algorithm.encode("utf-8"))
    url_hash_algorithm = quote(hash_algorithm.encode("utf-8"))

    url = (f"pia://container/{url_label}?issuer={url_issuer}&nonce={url_nonce}&time={url_time_stamp}"
           f"&url={registration_url}&serial={container_serial}&key_algorithm={url_key_algorithm}"
           f"&hash_algorithm={url_hash_algorithm}&passphrase={url_passphrase}{url_extra_data}")
    return url


class SmartphoneContainer(TokenContainerClass):

    def __init__(self, db_container):
        super().__init__(db_container)
        self.add_container_info("key_algorithm", "secp384r1")
        self.add_container_info("hash_algorithm", "SHA256")
        self.add_container_info("encrypt_algorithm", "AES")
        self.add_container_info("encrypt_mode", "GCM")

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
        Initializes the registration: Generates a QR code containing all relevant data.

        :param params: The parameters for the registration as dictionary like:

            ::

                {
                    "container_registration_url": url of the endpoint to finalize the registration,
                    "passphrase_required": <bool>, (optional)
                    "passphrase_ad": <bool, whether the AD password shall be used>, (optional)
                    "passphrase_prompt": <str, the prompt for the passphrase displayed in the app>, (optional)
                    "passphrase_response": <str, passphrase>, (optional)
                    "extra_data": ..., (optional)
                }

        :return: A dictionary like:

            ::

            {
                "container_url": {
                    "description": "URL for privacyIDEA Container Registration",
                    "value": <url>,
                    "img": <qr code of url>
                },
                "nonce": "ajhbdsuiuojno49877n4no3u09on38r98n",
                "time_stamp": "2020-08-25T14:00:00.000000+00:00",
                "key_algorithm": "secp384r1",
                "hash_algorithm": "SHA256",
                "passphrase": <Passphrase prompt displayed to the user in the app> (optional)
            }
        """
        registration_url = getParam(params, 'container_registration_url', optional=False)
        nonce = geturandom(20, hex=True)
        extra_data = getParam(params, 'extra_data', optional=True) or {}

        # Check if a passphrase is required for the registration
        passphrase_ad = getParam(params, 'passphrase_ad', optional=True) or False
        passphrase_prompt = getParam(params, 'passphrase_prompt', optional=True) or ""
        passphrase_response = getParam(params, 'passphrase_response', optional=True) or ""
        if passphrase_ad:
            if not passphrase_prompt:
                passphrase_prompt = "Please enter your AD passphrase."
        passphrase_params = {"passphrase_prompt": passphrase_prompt, "passphrase_response": passphrase_response,
                             "passphrase_ad": passphrase_ad}

        # Get timeout (in minutes)
        timeout = getParam(params, 'timeout', optional=True)

        # Delete all other challenges for this container
        # Even if the container is already registered and a new QR code is generated it shall reset the registration
        # and therefor invalidate all existing challenges
        challenge_list = get_challenges(serial=self.serial)
        for challenge in challenge_list:
            challenge.delete()
        # Create challenge
        db_challenge = Challenge(serial=self.serial, challenge=nonce, data=json.dumps(passphrase_params))
        if timeout:
            db_challenge.validitytime = timeout * 60
        db_challenge.save()
        timestamp = db_challenge.timestamp.replace(tzinfo=timezone.utc)
        time_stamp_iso = timestamp.isoformat()

        # get algorithms
        container_info = self.get_container_info_dict()
        key_algorithm = container_info.get("key_algorithm", "secp384r1")
        hash_algorithm = container_info.get("hash_algorithm", "SHA256")

        # Generate URL
        qr_url = create_container_registration_url(nonce=nonce,
                                                   time_stamp=time_stamp_iso,
                                                   registration_url=registration_url,
                                                   container_serial=self.serial,
                                                   key_algorithm=key_algorithm,
                                                   hash_algorithm=hash_algorithm,
                                                   passphrase=passphrase_prompt,
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
                           "passphrase_prompt": passphrase_prompt}

        return response_detail

    def finalize_registration(self, params):
        """
        Finalize the registration of a pi container on a physical container.
        Validates whether the smartphone is authorized to register. If successful, the server generates a key pair.
        Raises a privacyIDEAError on any failure to not disclose information.

        :param params: The parameters from the smartphone for the registration as dictionary like:

            ::
                {
                    "container_serial": <serial of the container>,
                    "signature": <sign(message)>,
                    "message": <nonce|timestamp|registration_url|serial[|passphrase]>,
                    "public_key": <public key of the smartphone base 64 url safe encoded>,
                    "passphrase": <passphrase> (optional)
                }

        :return: The public key of the server in a dictionary like {"public_key": <pub key base 64 url encoded>}.
        """
        # Verifies the challenge response
        self.check_challenge_response(params)

        # Generate private + public key for the server
        container_info = self.get_container_info_dict()
        key_algorithm = container_info.get("key_algorithm", "secp384r1")
        public_key_server, private_key_server = generate_keypair_ecc(key_algorithm)
        public_key_server_str, private_key_server_str = ecc_key_pair_to_b64url_str(public_key_server,
                                                                                   private_key_server)

        # Update container info
        pub_key_container_str = getParam(params, "public_client_key", optional=False)
        self.add_container_info("public_key_container", pub_key_container_str)
        self.add_container_info("public_key_server", public_key_server_str)
        self.add_container_info("private_key_server", encryptPassword(private_key_server_str))
        self.add_container_info("registration_state", "registered")

        res = {"public_server_key": public_key_server_str}
        return res

    def terminate_registration(self):
        """
        Terminate the synchronisation of the container with privacyIDEA.
        """
        # Delete keys
        self.delete_container_info("public_key_container")
        self.delete_container_info("public_key_server")
        self.delete_container_info("private_key_server")

        # Delete registration state
        self.delete_container_info("registration_state")

        # Delete challenges
        challenge_list = get_challenges(serial=self.serial)
        for challenge in challenge_list:
            challenge.delete()

    def init_sync(self, params):
        """
        Initialize the synchronization of a container with the pi server.
        It creates a challenge for the container to allow the registration.

        :param params: Dictionary with the parameters for the synchronization.

            ::
                {
                    "scope": "https://pi/container/synchronize/SMPH0001/finalize"
                }

        :return: Dictionary with the challenge nonce and the timestamp

            ::
                {
                    "nonce": "nonce",
                    "time_stamp": "2021-06-01T12:00:00+00:00",
                    "key_algorithm": "secp384r1"
                }
        """
        scope = getParam(params, "scope", optional=False)

        # Create challenge
        nonce = geturandom(20, hex=True)
        data = json.dumps({"scope": scope})
        db_challenge = Challenge(serial=self.serial, challenge=nonce, data=data)
        db_challenge.save()
        timestamp = db_challenge.timestamp.replace(tzinfo=timezone.utc)
        time_stamp_iso = timestamp.isoformat()

        # Get key algorithms
        container_info = self.get_container_info_dict()
        key_algorithm = container_info.get("key_algorithm", "secp384r1")

        res = {"nonce": nonce,
               "time_stamp": time_stamp_iso,
               "key_algorithm": key_algorithm}
        return res

    def finalize_sync(self, params):
        """
        Finalizes the synchronization of a container with the pi server.
        Here the actual data exchange happens.

        :param params: Dictionary with the parameters for the synchronization.

            ::
                {
                    "signature": <sign(nonce|timestamp|serial|scope|pub_key|container_dict)>,
                    "public_client_key_encry": <public key of the client for encryption base 64 url safe encoded>,
                    "container_dict": {"serial": "SMPH0001", "type": "smartphone", ...}
                }

        :return: Dictionary with the result of the synchronization.

            ::
                {
                    "public_server_key_encry": <public key of the server for encryption base 64 url safe encoded>,
                    "encryption_algorithm": "AES",
                    "encryption_params": {"mode": "GCM", "init_vector": "init_vector", "tag": "tag"},
                    "container_dict_encrypted": <encrypted container dict from server>
                }
        """
        # Get params
        signature = base64.urlsafe_b64decode(getParam(params, "signature", optional=False))
        pub_key_encr_container_str = getParam(params, "public_enc_key_client", optional=False)
        pub_key_encr_container, _ = b64url_str_key_pair_to_ecc_obj(public_key_str=pub_key_encr_container_str)
        container_client_str = getParam(params, "container_client", optional=True)
        container_client = json.loads(container_client_str) if container_client_str else {}
        scope = getParam(params, "scope", optional=True)

        try:
            pub_key_sig_container_str = self.get_container_info_dict()["public_key_container"]
        except KeyError:
            raise privacyIDEAError("The container is not registered!")
        pub_key_sig_container, _ = b64url_str_key_pair_to_ecc_obj(public_key_str=pub_key_sig_container_str)

        # Validate challenge
        valid_challenge = self.validate_challenge(signature, pub_key_sig_container, scope=scope,
                                                  key=pub_key_encr_container_str,
                                                  container=container_client_str)
        if not valid_challenge:
            raise privacyIDEAError('Could not verify signature!')

        # Generate encryption key pair for the server
        # container_info = self.get_container_info_dict()
        # key_algorithm = container_info.get("key_algorithm", "secp384r1")
        public_key_encr_server, private_key_encr_server = generate_keypair_ecc("x25519")
        public_key_encr_server_str, private_key_encr_server_str = ecc_key_pair_to_b64url_str(public_key_encr_server,
                                                                                             private_key_encr_server)

        # Get encryption algorithm and mode
        container_info = self.get_container_info_dict()
        encrypt_algorithm = container_info.get("encrypt_algorithm", "SHA256")
        encrypt_mode = container_info.get("encrypt_mode", "ECB")

        # Get container dict with token secrets
        container_dict = self.synchronize_container_details(container_client)

        # encrypt container dict
        session_key = ecdh_key_exchange(private_key_encr_server, pub_key_encr_container)
        container_dict_bytes = json.dumps(container_dict).encode('utf-8')
        container_dict_encrypted, encryption_params = encrypt_ecc(container_dict_bytes, session_key, encrypt_algorithm,
                                                                  encrypt_mode)

        res = {"encryption_algorithm": encrypt_algorithm,
               "encryption_params": encryption_params,
               "container_dict": container_dict_encrypted,
               "public_server_key": public_key_encr_server_str}
        return res

    def synchronize_container_details(self, container_client: dict):
        """
        Compares the container from the client with the server and returns the differences.
        The container dictionary from the client contains information about the container itself and the tokens.
        For each token the type and serial shall be provided. If no serial is available, two otp values can be provided.
        The server than tries to find the serial for the otp values. If multiple serials are found, it will not be
        included in the returned dictionary, since the token can not be uniquely identified.
        The returned dictionary contains information about the container itself and the tokens that needs to be added
        or updated. For the tokens to be added the enrollUrl is provided. For the tokens to be updated the serial and
        further information is provided.

        :param container_client: The container from the client as dictionary.

            ::
                {
                    "container": {"states": ["active"]},
                    "tokens": [{"serial": "TOTP001", "type": "totp", "active: True},
                                {"otp": ["1234", "9876"], "type": "hotp"}]
                }

        :return: container dictionary like

            ::
                {
                    "container": {"states": ["active"]},
                    "tokens": {"add": ["enroll_url1", "enroll_url2"],
                               "update": [{"serial": "TOTP001", "active": True},
                                          {"serial": "HOTP001", "active": False, "otp": ["1234", "9876"],
                                           "type": "hotp"}]}
                }
        """
        container_dict = {"container": {"states": self.get_states()}}
        server_token_serials = [token.get_serial() for token in self.get_tokens()]

        # Get serials for client tokens without serial
        client_tokens = container_client.get("tokens", [])
        serial_otp_map = {}
        for token in client_tokens:
            dict_keys = token.keys()
            # Get serial from otp if required
            if "serial" not in dict_keys and "otp" in dict_keys:
                token_type = token.get("type")
                token_list = get_tokens(tokentype=token_type)
                serial_list = get_serial_by_otp_list(token_list, otp_list=token["otp"])
                if len(serial_list) == 1:
                    serial = serial_list[0]
                    token["serial"] = serial
                    serial_otp_map[serial] = token["otp"]
                # shall we ignore otp values where multiple serials are found?

        # map client and server tokens
        client_serials = [token["serial"] for token in client_tokens if "serial" in token.keys()]
        missing_serials = list(set(server_token_serials).difference(set(client_serials)))
        same_serials = list(set(server_token_serials).intersection(set(client_serials)))

        # Get info for missing serials: enroll url
        add_list = []
        for serial in missing_serials:
            token = get_tokens_from_serial_or_user(serial, None)[0]
            enroll_url = token.get_enroll_url(user=User())
            add_list.append(enroll_url)

        # Get info for same serials: token details
        update_dict = []
        for serial in same_serials:
            token = get_tokens_from_serial_or_user(serial, None)[0]
            token_dict = {"serial": serial, "active": token.is_active()}
            otp = serial_otp_map.get(serial)
            if otp:
                token_dict["otp"] = otp
            update_dict.append(token_dict)

        container_dict["tokens"] = {"add": add_list, "update": update_dict}

        return container_dict

    def create_challenge(self, params):
        """
        Create a challenge.

        :param params: a dictionary containing container type specific parameters
        :return: Dictionary with the challenge nonce and the timestamp

            ::
                {
                    "nonce": "nonce",
                    "time_stamp": "2021-06-01T12:00:00+00:00"
                }
        """
        scope = getParam(params, "scope", optional=True)
        nonce = geturandom(20, hex=True)
        db_challenge = Challenge(serial=self.serial, challenge=nonce, data=scope)
        db_challenge.save()
        timestamp = db_challenge.timestamp.replace(tzinfo=timezone.utc)
        time_stamp_iso = timestamp.isoformat()

        res = {"nonce": nonce,
               "time_stamp": time_stamp_iso,
               "scope": scope}
        return res

    def check_challenge_response(self, params):
        """
        Check the response of a challenge. Verifies that all required parameters are provided.
        Afterward, verifies the challenge.

        :param params: The parameters from the smartphone for the challenge response as dictionary
        :return: True if the challenge response is valid, raises a privacyIDEAError otherwise.
        """
        # Get params
        signature = base64.urlsafe_b64decode(getParam(params, "signature", optional=False))
        pub_key_container_str = getParam(params, "public_client_key", optional=False)
        pub_key_container, _ = b64url_str_key_pair_to_ecc_obj(public_key_str=pub_key_container_str)
        registration_url = getParam(params, "container_registration_url", optional=False)

        # Required Checks: Challenge, passphrase, signature
        valid = self.validate_challenge(signature, pub_key_container, url=registration_url)
        if not valid:
            raise privacyIDEAError('Could not verify signature!')

        return valid
