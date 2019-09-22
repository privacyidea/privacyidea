# -*- coding: utf-8 -*-
#
#  2017-09-25 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add reinitialization of the PKCS11 module
#  2016-09-01 Mathias Brossard <mathias@axiadids.com>
#             Alternate PKCS11 Security Module
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
from privacyidea.lib.security.default import SecurityModule
from privacyidea.lib.error import HSMException
from privacyidea.lib.crypto import get_alphanum_str
from six import int2byte

__doc__ = """
This is a PKCS11 Security module that encrypts and decrypts the data on a
HSM that is connected via PKCS11. This alternate version relies on AES keys.
"""

log = logging.getLogger(__name__)

MAX_RETRIES = 5

try:
    import PyKCS11
except ImportError:
    log.info("The python module PyKCS11 is not available. "
             "So we can not use the PKCS11 security module.")


def int_list_to_bytestring(int_list):  # pragma: no cover
    return b"".join([int2byte(i) for i in int_list])


class AESHardwareSecurityModule(SecurityModule):  # pragma: no cover

    def __init__(self, config=None):
        """
        Initialize the PKCS11 Security Module.
        The configuration needs to contain the pkcs11 module and the ID of the key.

        {"module": "/usr/lib/hsm_pkcs11.so", "slot": 42, "key_label": "privacyidea"}

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

        if "module" not in config:
            log.error("No PKCS11 module defined!")
            raise HSMException("No PKCS11 module defined.")

        label_prefix = config.get("key_label", "privacyidea")
        self.key_labels = {}
        for k in self.mapping:
            l = config.get(("key_label_{0!s}".format(k)))
            l = ('{0!s}_{1!s}'.format(label_prefix, k)) if l is None else l
            self.key_labels[k] = l

        log.debug("Setting key labels: {0!s}".format(self.key_labels))
        # convert the slot to int
        self.slot = int(config.get("slot", 1))
        log.debug("Setting slot: {0!s}".format(self.slot))
        self.password = config.get("password")
        log.debug("Setting a password: {0!s}".format(bool(self.password)))
        self.module = config.get("module")
        log.debug("Setting the modules: {0!s}".format(self.module))
        self.max_retries = config.get("max_retries", MAX_RETRIES)
        log.debug("Setting max retries: {0!s}".format(self.max_retries))
        self.session = None
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
        self.pkcs11 = PyKCS11.PyKCS11Lib()
        self.pkcs11.load(self.module)
        self.pkcs11.lib.C_Initialize()
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
        slotlist = self.pkcs11.getSlotList()
        if not len(slotlist):
            raise HSMException("No HSM connected")
        if self.slot not in slotlist:
            raise HSMException("Slot {0:d} not present".format(self.slot))

        slotinfo = self.pkcs11.getSlotInfo(self.slot)
        log.debug("Setting up '{}'".format(slotinfo.slotDescription))

        # If the HSM is not connected at this point, it will fail
        self.session = self.pkcs11.openSession(slot=self.slot)

        log.debug("Logging on to '{}'".format(slotinfo.slotDescription))
        self.session.login(self.password)

        for k in self.mapping:
            label = self.key_labels[k]
            objs = self.session.findObjects([(PyKCS11.CKA_CLASS, PyKCS11.CKO_SECRET_KEY),
                                             (PyKCS11.CKA_LABEL, label)])
            log.debug("Loading '{}' key with label '{}'".format(k, label))
            if objs:
                self.key_handles[self.mapping[k]] = objs[0]

        # self.session.logout()
        log.debug("Successfully setup the security module.")
        self.is_ready = True

    def random(self, length):
        """
        Return a random bytestring
        :param length: length of the random bytestring
        :rtype bytes
        """
        retries = 0
        while True:
            try:
                r_integers = self.session.generateRandom(length)
                break
            except PyKCS11.PyKCS11Error as exx:
                log.warning(u"Generate Random failed: {0!s}".format(exx))
                # If something goes wrong in this process, we free memory, session and handles
                self.pkcs11.lib.C_Finalize()
                self.initialize_hsm()
                retries += 1
                if retries > self.max_retries:
                    raise HSMException("Failed to generate random number after multiple retries.")

        # convert the array of the random integers to a string
        return int_list_to_bytestring(r_integers)

    def encrypt(self, data, iv, key_id=SecurityModule.TOKEN_KEY):
        """

        :rtype: bytes
        """
        if len(data) == 0:
            return bytes("")
        log.debug("Encrypting {} bytes with key {}".format(len(data), key_id))
        m = PyKCS11.Mechanism(PyKCS11.CKM_AES_CBC_PAD, iv)
        retries = 0
        while True:
            try:
                k = self.key_handles[key_id]
                r = self.session.encrypt(k, bytes(data), m)
                break
            except PyKCS11.PyKCS11Error as exx:
                log.warning(u"Encryption failed: {0!s}".format(exx))
                # If something goes wrong in this process, we free memory,session and handles
                self.pkcs11.lib.C_Finalize()
                self.initialize_hsm()
                retries += 1
                if retries > self.max_retries:
                    raise HSMException("Failed to encrypt after multiple retries.")

        return int_list_to_bytestring(r)

    def decrypt(self, enc_data, iv, key_id=SecurityModule.TOKEN_KEY):
        """

        :rtype bytes
        """
        if len(enc_data) == 0:
            return bytes("")
        log.debug("Decrypting {} bytes with key {}".format(len(enc_data), key_id))
        m = PyKCS11.Mechanism(PyKCS11.CKM_AES_CBC_PAD, iv)
        start = datetime.datetime.now()
        retries = 0
        while True:
            try:
                k = self.key_handles[key_id]
                r = self.session.decrypt(k, bytes(enc_data), m)
                break
            except PyKCS11.PyKCS11Error as exx:
                log.warning(u"Decryption retry: {0!s}".format(exx))
                # If something goes wrong in this process, we free memory, session and handlers
                self.pkcs11.lib.C_Finalize()
                self.initialize_hsm()
                retries += 1
                if retries > self.max_retries:
                    td = datetime.datetime.now() - start
                    log.warning(u"Decryption finally failed: {0!s}. Time taken: {1!s}.".format(exx, td))
                    raise HSMException("Failed to decrypt after multiple retries.")

        if retries > 0:
            td = datetime.datetime.now() - start
            log.warning(u"Decryption after {0!s} retries successful. Time taken: {1!s}.".format(retries, td))
        return int_list_to_bytestring(r)

    def create_keys(self):
        """
        Connect to the HSM and create the encryption keys.
        The HSM connection should already be configured in pi.cfg.

        We will create new keys with new key labels
        :return: a dictionary of the created key labels
        """
        # We need a new read/write session
        session = self.pkcs11.openSession(self.slot,
                                          PyKCS11.CKF_SERIAL_SESSION | PyKCS11.CKF_RW_SESSION)
        # We need to logout, otherwise we get CKR_USER_ALREADY_LOGGED_IN
        session.logout()
        session.login(self.password)

        key_labels = {"token": "",
                      "config": "",
                      "value": ""}

        for kl in key_labels.keys():
            label = "{0!s}_{1!s}".format(kl, get_alphanum_str())
            aesTemplate = [
                (PyKCS11.CKA_CLASS, PyKCS11.CKO_SECRET_KEY),
                (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_AES),
                (PyKCS11.CKA_VALUE_LEN, 32),
                (PyKCS11.CKA_LABEL, label),
                (PyKCS11.CKA_ID, label),
                (PyKCS11.CKA_TOKEN, PyKCS11.CK_TRUE),
                (PyKCS11.CKA_PRIVATE, True),
                (PyKCS11.CKA_SENSITIVE, True),
                (PyKCS11.CKA_ENCRYPT, True),
                (PyKCS11.CKA_DECRYPT, True),
                (PyKCS11.CKA_TOKEN, True),
                (PyKCS11.CKA_WRAP, True),
                (PyKCS11.CKA_UNWRAP, True),
                (PyKCS11.CKA_EXTRACTABLE, False)
            ]
            aesKey = session.generateKey(aesTemplate)
            key_labels[kl] = label

        session.logout()
        session.closeSession()

        return key_labels


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig()
    log.setLevel(logging.INFO)
    # log.setLevel(logging.DEBUG)

    module = "/usr/local/opt/pkcs11/lib/pkcs11-token.so"

    p = AESHardwareSecurityModule({"module": module, "slot": 2,
                                   "key_label": "privacyidea",
                                   "password": "12345678"})

    # password
    password = "topSekr3t" * 16
    crypted = p.encrypt_password(password)
    text = p.decrypt_password(crypted)
    assert(text == password)
    log.info("password encrypt/decrypt test successful")

    # pin
    password = "topSekr3t"
    crypted = p.encrypt_pin(password)
    text = p.decrypt_pin(crypted)
    assert (text == password)
    log.info("pin encrypt/decrypt test successful")

    p = AESHardwareSecurityModule({"module": module, "slot": 2,
                                   "key_label": "privacyidea"})
    p.setup_module({"password": "12345678"})

    # random
    tmp_iv = p.random(16)
    plain = p.random(128)
    log.info("random test successful")

    # generic encrypt / decrypt
    cipher = p.encrypt(plain, tmp_iv)
    assert (plain != cipher)
    text = p.decrypt(cipher, tmp_iv)
    assert (text == plain)
    log.info("generic encrypt/decrypt test successful")
