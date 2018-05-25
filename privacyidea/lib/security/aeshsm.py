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

import binascii
import logging
from privacyidea.lib.security.default import SecurityModule
from privacyidea.lib.error import HSMException

__doc__ = """
This is a PKCS11 Security module that encrypts and decrypts the data on a
HSM that is connected via PKCS11. This alternate version relies on AES keys.
"""

log = logging.getLogger(__name__)

TOKEN_KEY = 0
CONFIG_KEY = 1
VALUE_KEY = 2

MAX_RETRIES = 5

mapping = {
    'token':  TOKEN_KEY,
    'config': CONFIG_KEY,
    'value':  VALUE_KEY
}

try:
    import PyKCS11
except ImportError:
    log.info("The python module PyKCS11 is not available. "
             "So we can not use the PKCS11 security module.")


def int_list_to_bytestring(int_list):  # pragma: no cover
    return "".join([chr(i) for i in int_list])


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
        for k in ['token', 'config', 'value']:
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
        self.session = None
        self.key_handles = {}

        self.pkcs11 = PyKCS11.PyKCS11Lib()
        self.pkcs11.load(self.module)
        self.initialize_hsm()

    def initialize_hsm(self):
        """
        Initialize the HSM:
        * initialize PKCS11 library
        * login to HSM
        * get session
        :return:
        """
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

        for k in ['token', 'config', 'value']:
            label = self.key_labels[k]
            objs = self.session.findObjects([(PyKCS11.CKA_CLASS, PyKCS11.CKO_SECRET_KEY),
                                             (PyKCS11.CKA_LABEL, label)])
            log.debug("Loading '{}' key with label '{}'".format(k, label))
            self.key_handles[mapping[k]] = objs[0]

        # self.session.logout()
        log.debug("Successfully setup the security module.")
        self.is_ready = True

    def random(self, length):
        """
        Return a random bytestring
        :param length: length of the random bytestring
        :return:
        """
        retries = 0
        while True:
            try:
                r_integers = self.session.generateRandom(length)
                break
            except PyKCS11.PyKCS11Error as exx:
                log.warning(u"Generate Random failed: {0!s}".format(exx))
                self.initialize_hsm()
                retries += 1
                if retries > MAX_RETRIES:
                    raise HSMException("Failed to generate random number after multiple retries.")

        # convert the array of the random integers to a string
        return int_list_to_bytestring(r_integers)

    def encrypt(self, data, iv, key_id=TOKEN_KEY):
        if len(data) == 0:
            return bytes("")
        log.debug("Encrypting {} bytes with key {}".format(len(data), key_id))
        m = PyKCS11.Mechanism(PyKCS11.CKM_AES_CBC_PAD, iv)
        k = self.key_handles[key_id]
        retries = 0
        while True:
            try:
                r = self.session.encrypt(k, bytes(data), m)
                break
            except PyKCS11.PyKCS11Error as exx:
                log.warning(u"Encryption failed: {0!s}".format(exx))
                self.initialize_hsm()
                retries += 1
                if retries > MAX_RETRIES:
                    raise HSMException("Failed to encrypt after multiple retries.")

        return int_list_to_bytestring(r)

    def decrypt(self, data, iv, key_id=TOKEN_KEY):
        if len(data) == 0:
            return bytes("")
        log.debug("Decrypting {} bytes with key {}".format(len(data), key_id))
        m = PyKCS11.Mechanism(PyKCS11.CKM_AES_CBC_PAD, iv)
        k = self.key_handles[key_id]
        retries = 0
        while True:
            try:
                r = self.session.decrypt(k, bytes(data), m)
                break
            except PyKCS11.PyKCS11Error as exx:
                log.warning(u"Decryption failed: {0!s}".format(exx))
                self.initialize_hsm()
                retries += 1
                if retries > MAX_RETRIES:
                    raise HSMException("Failed to decrypt after multiple retries.")

        return int_list_to_bytestring(r)

    def decrypt_password(self, crypt_pass):
        """
        Decrypt the given password. The CONFIG_KEY is used to decrypt it.

        :param crypt_pass: the encrypted password with the leading iv,
            separated by the ':'
        :param crypt_pass: byte string

        :return: decrypted data
        :rtype: byte string
        """
        return self._decrypt_value(crypt_pass, CONFIG_KEY)

    def decrypt_pin(self, crypt_pin):
        """
        Decrypt the given encrypted PIN with the TOKEN_KEY

        :param crypt_pin: the encrypted pin with the leading iv,
            separated by the ':'
        :param crypt_pin: byte string

        :return: decrypted data
        :rtype: byte string
        """
        return self._decrypt_value(crypt_pin, TOKEN_KEY)

    def encrypt_password(self, password):
        """
        Encrypt the given password with the CONFIG_KEY an a random IV.

        :param password: The password that is to be encrypted
        :param password: byte string

        :return: encrypted data - leading iv, separated by the ':'
        :rtype: byte string
        """
        return self._encrypt_value(password, CONFIG_KEY)

    def encrypt_pin(self, pin):
        """
        Encrypt the given PIN with the TOKEN_KEY and a random IV

        :param pin: the to be encrypted pin
        :param pin: byte string

        :return: encrypted data - leading iv, separated by the ':'
        :rtype: byte string
        """
        return self._encrypt_value(pin, TOKEN_KEY)

    ''' base methods for pin and password '''
    def _encrypt_value(self, value, key_id):
        """
        base method to encrypt a value
        - uses one slot id to encrypt a string
        returns as string with leading iv, separated by ':'

        :param value: the value that is to be encrypted
        :param value: byte string

        :param key_id: slot of the key array
        :type key_id: int

        :return: encrypted data with leading iv and separator ':'
        :rtype: byte string
        """
        iv = self.random(16)
        v = self.encrypt(value, iv, key_id)

        return ':'.join([binascii.hexlify(x) for x in [iv, v]])

    def _decrypt_value(self, crypt_value, key_id):
        """
        base method to decrypt a value
        - used one slot id to encrypt a string with leading iv, separated by ':'

        :param crypt_value: the the value that is to be decrypted
        :param crypt_value: byte string

        :param  key_id: slot of the key array
        :type   key_id: int

        :return: decrypted data
        :rtype:  byte string
        """
        (iv, data) = [binascii.unhexlify(x) for x in crypt_value.split(':')]

        return self.decrypt(data, iv, key_id)


if __name__ == "__main__":
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
    iv = p.random(16)
    plain = p.random(128)
    log.info("random test successful")

    # generic encrypt / decrypt
    cipher = p.encrypt(plain, iv)
    assert (plain != cipher)
    text = p.decrypt(cipher, iv)
    assert (text == plain)
    log.info("generic encrypt/decrypt test successful")
