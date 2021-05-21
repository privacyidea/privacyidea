# -*- coding: utf-8 -*-
#
#  2021-05-20 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             YubiHSM2 via the yubihsm python library
#             encryption is done via RSA4096
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#

import logging
import datetime
from privacyidea.lib.security.default import DefaultSecurityModule, SecurityModule
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from privacyidea.lib.error import HSMException
from privacyidea.lib.crypto import get_alphanum_str
from six import int2byte

__doc__ = """
This is a YubiHSM2 Security module that encrypts and decrypts the data on a
YubiHSM2. It uses RSA4096 keys.
"""

log = logging.getLogger(__name__)

MAX_RETRIES = 5

try:
    from yubihsm import YubiHsm
    from yubihsm.defs import CAPABILITY, ALGORITHM
    from yubihsm.objects import AsymmetricKey, OBJECT
except ImportError:
    log.error("The python module YubiHSM is not available. "
              "So we can not use the YubiHSM security module.")


def int_list_to_bytestring(int_list):  # pragma: no cover
    return b"".join([int2byte(i) for i in int_list])


class YubiHSMSecurityModule(DefaultSecurityModule):  # pragma: no cover

    def __init__(self, config=None):
        """
        Initialize the YubiHSM Security Module.
        The configuration needs to contain the pkcs11 module and the ID of the key.

        {"url": "http://localhost:12345", "domain": 1, "key_label": "privacyidea"}

        The HSM is not directly ready, since the HSM is protected by a password.
        The function setup_module({"password": "HSM User password"}) needs to be called.

        :param config: contains the HSM configuration
        :type config: dict

        :return: The Security Module object
        """
        config = config or {}
        self.name = "HSM"
        self.config = config
        # Initially, we might be missing a password
        self.is_ready = False

        if "url" not in config:
            log.error("No YubiHSM URL defined!")
            raise HSMException("No YubiHSM URL defined!")
        self.url = config.get("url")

        label_prefix = config.get("key_label", "privacyidea")
        self.key_labels = {}
        for k in self.mapping:
            l = config.get(("key_label_{0!s}".format(k)))
            l = ('{0!s}_{1!s}'.format(label_prefix, k)) if l is None else l
            self.key_labels[k] = l

        log.debug("Setting key labels: {0!s}".format(self.key_labels))
        # convert the slot to int
        self.domain = int(config.get("domain", 1))
        log.debug("Setting domain: {0!s}".format(self.domain))
        self.password = config.get("password")
        log.debug("Setting a password: {0!s}".format(bool(self.password)))
        self.module = config.get("url")
        log.debug("Setting the YubiHSM URL: {0!s}".format(self.url))
        self.max_retries = config.get("max_retries", MAX_RETRIES)
        log.debug("Setting max retries: {0!s}".format(self.max_retries))
        self.hsm = None
        self.session = None
        # This will contain the ids of the keys
        self.key_handles = {}

        self.initialize_hsm()

    def initialize_hsm(self):
        """
        Initialize the HSM:
        * initialize PKCS11 library
        * login to HSM
        * get session
        :return:
        """
        self.hsm = YubiHsm.connect(self.url)
        if self.password:
            self._login()

    def setup_module(self, params):
        """
        callback, which is called during the runtime to initialze the
        security module.

        Here the password for the PKCS11 HSM can be provided

           {"password": "top secreT"}

        :param params: The password for the HSM
        :type  params: dict

        :return: -
        """
        if "password" in params:
            self.password = str(params.get("password"))
        else:
            raise HSMException("missing password")
        self._login()
        return self.is_ready

    def _login(self):
        # If the HSM is not connected at this point, it will fail
        self.session = self.hsm.create_session_derived(self.domain, self.password)
        log.debug(u"The following mapping is used: {0!s}".format(self.mapping))
        log.debug(u"We have the following key_labels: {0!s}".format(self.key_labels))
        for k in self.mapping:
            label = self.key_labels[k]
            objs = self.session.list_objects(object_type=OBJECT.ASYMMETRIC_KEY, label=label)
            if objs:
                self.key_handles[self.mapping[k]] = objs[0]
            else:
                log.error("Object {0!s} not found!".format(label))

        log.debug(u"Using the following key handles: {0!s}".format(self.key_handles))

        log.debug("Successfully setup the security module.")
        self.is_ready = True

    def encrypt(self, data, iv, key_id=SecurityModule.TOKEN_KEY):
        """

        :rtype: bytes
        """
        log.debug(u"Encrypting {0!s} bytes with key {0!s}".format(len(data), key_id))
        if len(data) == 0:
            return int_list_to_bytestring([])
        retries = 0
        while True:
            try:
                k = self.key_handles[key_id]
                pubkey = k.get_public_key()
                cipher_text = pubkey.encrypt(
                    data,
                    padding.OAEP(
                        mgf=padding.MGF1(algorithm=hashes.SHA256()),
                        algorithm=hashes.SHA256(),
                        label=None
                    )
                )
                break
            except Exception as exx:
                log.warning(u"Encryption failed: {0!s}".format(exx))
                # If something goes wrong in this process, we free memory,session and handles
                self.session.close()
                self.hsm.close()
                self.initialize_hsm()
                retries += 1
                if retries > self.max_retries:
                    raise HSMException("Failed to encrypt after multiple retries.")

        return int_list_to_bytestring(cipher_text)

    def decrypt(self, enc_data, iv, key_id=SecurityModule.TOKEN_KEY):
        """

        :rtype bytes
        """
        if len(enc_data) == 0:
            return bytes("")
        log.debug("Decrypting {} bytes with key {}".format(len(enc_data), key_id))
        start = datetime.datetime.now()
        retries = 0
        while True:
            try:
                k = self.key_handles[key_id]
                message = k.decrypt_oaep(enc_data)
                break
            except Exception as exx:
                log.warning(u"Decryption retry: {0!s}".format(exx))
                # If something goes wrong in this process, we free memory, session and handlers
                self.session.close()
                self.hsm.close()
                self.initialize_hsm()
                retries += 1
                if retries > self.max_retries:
                    td = datetime.datetime.now() - start
                    log.warning(u"Decryption finally failed: {0!s}. Time taken: {1!s}.".format(exx, td))
                    raise HSMException("Failed to decrypt after multiple retries.")

        if retries > 0:
            td = datetime.datetime.now() - start
            log.warning(u"Decryption after {0!s} retries successful. Time taken: {1!s}.".format(retries, td))
        return int_list_to_bytestring(message)

    def create_keys(self):
        """
        Connect to the HSM and create the encryption keys.
        The HSM connection should already be configured in pi.cfg.

        We will create new keys with new key labels
        :return: a dictionary of the created key labels
        """
        # We need a new read/write session
        log.debug(u"Connecting to HSM at {0!s} in domain {1!s}".format(self.url, self.domain))
        hsm = YubiHsm.connect(self.url)
        session = hsm.create_session_derived(self.domain, self.password)

        key_labels = {"token": "",
                      "config": "",
                      "value": ""}

        for kl in key_labels.keys():
            #label = "{0!s}_{1!s}".format(kl, get_alphanum_str())
            label = "{0!s}_{1!s}".format(self.config.get("key_label"), kl)
            log.debug("Create key {0!s}".format(label))
            key = AsymmetricKey.generate(  # Generate a new key object in the YubiHSM.
                session,  # Secure YubiHsm session to use.
                0,  # Object ID, 0 to get one assigned.
                label,  # Label for the object.
                self.domain,  # Domain(s) for the object.
                CAPABILITY.DECRYPT_OAEP,  # Capabilities for the object, can have multiple.
                ALGORITHM.RSA_4096  # Algorithm for the key.
            )
            key_labels[kl] = label

        session.close()
        hsm.close()

        return key_labels


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig()
    log.setLevel(logging.DEBUG)

    url = "http://localhost:12345"
    CONFIG = {"url": url, "domain": 1,
              "key_label": "privacyidea",
              "password": "password"}

    p = YubiHSMSecurityModule(CONFIG)

    # Do this only once, when you need to create the keys
    #p.create_keys()

    log.info("+++ Encrypt password")
    password = "topSekr3t" * 16
    crypted = p.encrypt_password(password)
    text = p.decrypt_password(crypted)
    assert(text == password)
    log.info("password encrypt/decrypt test successful")

    log.info("+++ Encrypt PIN")
    password = "topSekr3t"
    crypted = p.encrypt_pin(password)
    text = p.decrypt_pin(crypted)
    assert (text == password)
    log.info("pin encrypt/decrypt test successful")

    p = YubiHSMSecurityModule({"url": url, "domain": 1,
                               "key_label": "privacyidea"})
    p.setup_module({"password": "password"})

    log.info("+++ Create RANDOM")
    tmp_iv = p.random(16)
    plain = p.random(128)
    log.info("random test successful")

    log.info("+++ Encrypt / Decrypt")
    # generic encrypt / decrypt
    cipher = p.encrypt(plain, tmp_iv)
    assert (plain != cipher)
    text = p.decrypt(cipher, tmp_iv)
    assert (text == plain)
    log.info("generic encrypt/decrypt test successful")
