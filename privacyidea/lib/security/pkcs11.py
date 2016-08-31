# -*- coding: utf-8 -*-
#
#  2016-04-15 Cornelius Kölbel <cornelius@privacyidea.org>
#             PKCS11 Security Module
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
__doc__ = """
This is a PKCS11 Security module that encrypts and decrypts the data on a Smartcard/HSM that is connected via PKCS11.
"""
import logging
from privacyidea.lib.security.default import SecurityModule
from privacyidea.lib.security.password import PASSWORD
from privacyidea.lib.error import HSMException
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
log = logging.getLogger(__name__)

try:
    import PyKCS11
except ImportError:
    log.info("The python module PyKCS11 is not available. So we can not use the PKCS11 security module.")


# FIXME: At the moment this only works with one (1) wsgi process!


def int_list_to_bytestring(int_list):  # pragma: no cover
    r = ""
    for i in int_list:
        r += chr(i)
    return r


class PKCS11SecurityModule(SecurityModule):  # pragma: no cover

    def __init__(self, config=None):
        """
        Initialize the PKCS11 Security Module.
        The configuration needs to contain the pkcs11 module and the ID of the key.

          {"module": "/usr/lib/x86_64-linux-gnu/opensc-pkcs11.so",
           "key_id": 10}

        The HSM is not directly ready, since the HSM is protected by a password.
        The function setup_module({"password": "HSM User password"}) needs to be called.

        :param config: contains the HSM configuration
        :type config: dict

        :return: The Security Module object
        """
        config = config or {}
        self.name = "PKCS11"
        self.config = config
        self.is_ready = False

        if "module" not in config:
            log.error("No PKCS11 module defined!")
            raise HSMException("No PKCS11 module defined.")
        self.key_id = config.get("key_id", 16)
        self.pkcs11 = PyKCS11.PyKCS11Lib()
        self.pkcs11.load(config.get("module"))
        self.session = None
        self.key_handle = None

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
            PASSWORD = str(params.get("password"))
        else:
            raise HSMException("missing password")

        slotlist = self.pkcs11.getSlotList()
        if not len(slotlist):
            raise HSMException("No HSM connected")
        slot_id = slotlist[0]
        # If the HSM is not connected at this point, it will fail
        self.session = self.pkcs11.openSession(slot=slot_id)

        slotinfo = self.pkcs11.getSlotInfo(1)
        log.info("Setting up {}".format(slotinfo.fields.get("slotDescription")))
        # get the public key
        objs = self.session.findObjects([(PyKCS11.CKA_CLASS, PyKCS11.CKO_PUBLIC_KEY),
                                         (PyKCS11.CKA_ID, (self.key_id,))])
        self.key_handle = objs[0]
        pubkey_list = self.session.getAttributeValue(self.key_handle,  [PyKCS11.CKA_VALUE], allAsBinary=True)
        pubkey_bin = int_list_to_bytestring(pubkey_list[0])
        self.rsa_pubkey = RSA.importKey(pubkey_bin)

        # We do a login and logout to see if
        self.session.login(PASSWORD)
        self.session.logout()
        self.is_ready = True
        log.info("Successfully setup the security module.")

        return self.is_ready

    def random(self, length):
        """
        Return a random bytestring
        :param length: length of the random bytestring
        :return:
        """
        r = ''
        r_integers = self.session.generateRandom(length)
        # convert the array of the random integers to a string
        return int_list_to_bytestring(r_integers)

    def encrypt(self, value, iv=None):
        cipher = PKCS1_v1_5.new(self.rsa_pubkey)
        encrypted = cipher.encrypt(value)
        return encrypted

    def decrypt(self, value, iv=None):
        if not PASSWORD:
            log.error("empty PASSWORD. Your security module is probably not "
                      "initialized.")
        self.session.login(PASSWORD)
        objs = self.session.findObjects([(PyKCS11.CKA_CLASS, PyKCS11.CKO_PRIVATE_KEY),
                                         (PyKCS11.CKA_ID, (self.key_id,))])

        key_handle_private = objs[0]
        text = self.session.decrypt(key_handle_private, value)
        text = int_list_to_bytestring(text)
        self.session.logout()
        return text

    def encrypt_password(self, clear_pass):
        return self.encrypt(clear_pass)

    def encrypt_pin(self, clear_pin):
        return self.encrypt(clear_pin)

    def decrypt_password(self, crypt_pass):
        return self.decrypt(crypt_pass)

    def decrypt_pin(self, crypt_pin):
        return self.decrypt(crypt_pin)


if __name__ == "__main__":

    module = "/usr/local/lib/opensc-pkcs11.so"
    #module = "/usr/lib/x86_64-linux-gnu/opensc-pkcs11.so"

    p = PKCS11SecurityModule({"module": module,
                              "key_id": 17})
    p.setup_module({"password": "123456"})

    cleartext = "Hello there!"
    cipher = p.encrypt(cleartext)
    text = p.decrypt(cipher)
    print text
    assert(text == cleartext)

    cleartext = "Hello, this is a really long text and so and and so on..."
    cipher = p.encrypt(cleartext)
    text = p.decrypt(cipher)
    print text
    assert (text == cleartext)

    # password
    password = "topSekr3t"
    crypted = p.encrypt_password(password)
    text = p.decrypt_password(crypted)
    print text
    assert(text == password)

    # pin
    password = "topSekr3t"
    crypted = p.encrypt_pin(password)
    text = p.decrypt_pin(crypted)
    print text
    assert (text == password)
