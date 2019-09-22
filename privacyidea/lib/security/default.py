# -*- coding: utf-8 -*-
#
#  product:  privacyIDEA is a fork of LinOTP
#  May, 08 2014 Cornelius Kölbel
#  http://www.privacyidea.org
#
#  2014-12-15 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             remove remnant code and code cleanup during
#             flask migration. Ensure code coverage.
#  2014-10-19 Remove class SecurityModule from __init__.py
#             and add it here.
#             Cornelius Kölbel <cornelius@privacyidea.org>
#
#  product:  LinOTP2
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  AGPLv3
#  contact:  http://www.linotp.org
#            http://www.lsexperts.de
#            linotp@lsexperts.de
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
"""
Contains the crypto functions as implemented by the default security module,
which is the encryption key in the file.

The contents of the file is tested in tests/test_lib_crypto.py
"""

import logging
import binascii
import os

from hashlib import sha256

from privacyidea.lib.crypto import (geturandom, zerome, aes_cbc_encrypt,
                                    aes_cbc_decrypt)
from privacyidea.lib.error import HSMException
from privacyidea.lib.utils import (is_true, to_unicode, to_bytes,
                                   hexlify_and_unicode)

from .password import PASSWORD

log = logging.getLogger(__name__)


def create_key_from_password(password):
    """
    Create a key from the given password.
    This is used to encrypt and decrypt the enckey file.

    :param password:
    :type password: str or bytes
    :return: the generated key
    :rtype: bytes
    """
    key = sha256(to_bytes(password)).digest()[0:32]
    return key


class SecurityModule(object):
    TOKEN_KEY = 0
    CONFIG_KEY = 1
    VALUE_KEY = 2
    DEFAULT_KEY = 3

    mapping = {
        'token': TOKEN_KEY,
        'config': CONFIG_KEY,
        'value': VALUE_KEY
    }

    is_ready = False

    def __init__(self, config=None):
        log.error("This is the base class. You should implement this!")
        self.config = config
        self.name = "SecurityModule"

    def setup_module(self, params):
        fname = 'setup_module'
        log.error("This is the base class. You should implement "
                  "the method : %s " % (fname,))
        raise NotImplementedError("Should have been implemented {0!s}".format(fname))

    ''' base methods '''
    def random(self, length):
        fname = 'random'
        log.error("This is the base class. You should implement "
                  "the method : %s " % (fname,))
        raise NotImplementedError("Should have been implemented {0!s}".format(fname))

    def encrypt(self, data, iv, key_id=TOKEN_KEY):
        fname = 'encrypt'
        log.error("This is the base class. You should implement "
                  "the method : %s " % (fname,))
        raise NotImplementedError("Should have been implemented {0!s}".format(fname))

    def decrypt(self, enc_data, iv, key_id=TOKEN_KEY):
        fname = 'decrypt'
        log.error("This is the base class. You should implement "
                  "the method : %s " % (fname,))
        raise NotImplementedError("Should have been implemented {0!s}".format(fname))

    def decrypt_password(self, crypt_pass):
        """
        Decrypt the given password. The CONFIG_KEY is used to decrypt it.

        :param crypt_pass: the encrypted password with the leading iv,
            separated by the ':', hexlified
        :type crypt_pass: str

        :return: decrypted data
        :rtype: str
        """
        return self._decrypt_value(crypt_pass, self.CONFIG_KEY)

    def decrypt_pin(self, crypt_pin):
        """
        Decrypt the given encrypted PIN with the TOKEN_KEY

        :param crypt_pin: the encrypted pin with the leading iv,
            separated by the ':'
        :type crypt_pin: str

        :return: decrypted data
        :rtype: str
        """
        return self._decrypt_value(crypt_pin, self.TOKEN_KEY)

    def encrypt_password(self, password):
        """
        Encrypt the given password with the CONFIG_KEY and a random IV.

        This function returns a unicode string with a
        hexlified contents of the IV and the encrypted data separated by a
        colon like u"4956:44415441"

        :param password: The password that is to be encrypted
        :type password: str

        :return: encrypted data - leading iv, separated by the ':'
        :rtype: str
        """
        return self._encrypt_value(password, self.CONFIG_KEY)

    def encrypt_pin(self, pin):
        """
        Encrypt the given PIN with the TOKEN_KEY and a random IV

        This function returns a unicode string with a
        hexlified contents of the IV and the encrypted data separated by a
        colon like u"4956:44415441"

        :param pin: the pin that should be encrypted
        :type pin: str

        :return: encrypted data - leading iv, separated by the ':'
        :rtype: str
        """
        return self._encrypt_value(pin, self.TOKEN_KEY)

    ''' base methods for pin and password '''
    def _encrypt_value(self, value, slot_id):
        """
        base method to encrypt a value
        - uses one slot id to encrypt a string
        returns as string with leading iv, separated by ':'

        :param value: the value that is to be encrypted
        :type value: str

        :param slot_id: slot of the key array
        :type slot_id: int

        :return: encrypted data with leading iv and separator ':'
        :rtype: str
        """
        iv = self.random(16)
        v = self.encrypt(to_bytes(value), iv, slot_id)

        cipher_value = binascii.hexlify(iv) + b':' + binascii.hexlify(v)
        return cipher_value.decode("utf-8")

    def _decrypt_value(self, crypt_value, slot_id):
        """
        base method to decrypt a value
        - used one slot id to encrypt a string with leading iv, separated by ':'

        :param crypt_value: the the value that is to be decrypted
        :type crypt_value: str

        :param slot_id: slot of the key array
        :type slot_id: int

        :return: decrypted data
        :rtype: str
        """
        # split at ":"
        pos = crypt_value.find(':')
        bIV = crypt_value[:pos]
        bData = crypt_value[pos + 1:]

        iv = binascii.unhexlify(bIV)
        data = binascii.unhexlify(bData)

        clear_data = self.decrypt(data, iv, slot_id)

        return to_unicode(clear_data)

    def create_keys(self):
        """
        This can be used to create the encryption keys
        :return: Module dependent
        """
        fname = "create_keys"
        raise NotImplementedError("Should have been implemented {0!s}".format(fname))


class DefaultSecurityModule(SecurityModule):

    def __init__(self, config=None):
        """
        Init of the default security module. The config needs to contain the key
        file. The key file can be encrypted, then the config also needs to
        provide the information, that the key file is encrypted.

           {"file": "/etc/secretkey",
            "crypted": True}

        If the key file is encrypted, the HSM is not immediately ready. It will
        return HSM.is_ready == False.
        Then the function "setup_module({"password": "PW to decrypt"}) needs
        to be called.

        :param config: contains the configuration definition
        :type  config: dict

        :return -
        """
        config = config or {}
        self.name = "Default"
        self.config = config
        self.crypted = False
        self.is_ready = True
        self._id = binascii.hexlify(os.urandom(3))

        if "file" not in config:
            log.error("No secret file defined. A parameter "
                      "PI_ENCFILE is missing in your pi.cfg.")
            raise HSMException("no secret file defined: PI_ENCFILE!")

        # We determine, if the file is encrypted.
        with open(config.get("file"), 'rb') as f:
            cipher = f.read()

        if len(cipher) > 100:
            config["crypted"] = True

        if is_true(config.get("crypted", "")):
            self.crypted = True
            self.is_ready = False

        self.secFile = config.get('file')
        self.secrets = {}

    def _get_secret(self, slot_id=SecurityModule.TOKEN_KEY, password=None):
        """
        internal function, which reads the key from the defined
        slot in the file. It also caches the encryption key to the dictionary
        self.secrets.

        If the file is encrypted, the encryption key is decrypted with the
        password and also cached in self.secrets.

        :param slot_id: slot id of the key array
        :type slot_id: int

        :return: key or secret
        :rtype: binary string
        """
        slot_id = int(slot_id)
        if self.crypted and slot_id in self.secrets:
            return self.secrets.get(slot_id)

        secret = b''

        if self.crypted:
            # if the password was not provided, read it from the module
            # singleton cache
            password = password or PASSWORD
            if not password:
                raise HSMException("Error decrypting the encryption key. "
                                   "No password provided!")
            # Read all keys, decrypt them and return the key for
            # the slot id
            # TODO we assume here, that the file contains the hexlified data
            with open(self.secFile) as f:
                cipher = f.read()

            try:
                keys = self.password_decrypt(cipher, password)
            except UnicodeDecodeError as e:
                raise HSMException("Error decrypting the encryption key. You "
                                   "probably provided the wrong password.")
            secret = keys[slot_id*32:(slot_id+1)*32]

        else:
            # Only read the key with the slot_id
            with open(self.secFile, 'rb') as f:
                for _i in range(0, slot_id + 1):
                    secret = f.read(32)

            if secret == b"":
                raise HSMException("No secret key defined for index: %s !\n"
                                   "Please extend your %s"" !"
                                   % (str(slot_id), self.secFile))

        # cache the result
        self.secrets[slot_id] = secret
        return secret

    def setup_module(self, params):
        """
        callback, which is called during the runtime to initialze the
        security module.

        E.g. here the password for an encrypted keyfile can be provided like::

           {"password": "top secreT"}

        :param params: The password for the key file
        :type  params: dict

        :return: -
        """
        if self.crypted is False:
            return
        if "password" in params:
            PASSWORD = params.get("password")
        else:
            raise HSMException("missing password")

        # if we have a crypted file and a password, we take all keys
        # from the file and put them in a hash
        # After this we do not require the password anymore
        for handle in [self.TOKEN_KEY, self.CONFIG_KEY, self.VALUE_KEY]:
            # fill self.secrets
            self.secrets[handle] = self._get_secret(handle, PASSWORD)

        self.is_ready = True
        return self.is_ready

    # the real interfaces: random, encrypt, decrypt
    @staticmethod
    def random(length=32):
        """
        Create and return random bytes.

        :param length: length of the random byte array
        :type length: int

        :return: random bytes
        :rtype: byte string
        """
        return os.urandom(length)

    def encrypt(self, data, iv, key_id=SecurityModule.TOKEN_KEY):
        """
        security module methods: encrypt

        :param data: the data that is to be encrypted
        :type data: bytes

        :param iv: initialisation vector
        :type iv: bytes

        :param key_id: slot of the key array. The key file contains 96
            bytes, which are made up of 3 32byte keys.
        :type key_id: int

        :return: encrypted data
        :rtype:  bytes
        """
        if self.is_ready is False:
            raise HSMException('setup of security module incomplete')

        key = self._get_secret(key_id)

        # convert input to ascii, so we can securely append bin data for padding
        input_data = binascii.b2a_hex(data)
        input_data += b"\x01\x02"
        padding = (16 - len(input_data) % 16) % 16
        input_data += padding * b"\0"

        res = aes_cbc_encrypt(key, iv, input_data)

        if self.crypted is False:
            zerome(key)
            del key
        return res

    @staticmethod
    def password_encrypt(data, password):
        """
        Encrypt the given text with the password.
        A key is derived from the password and used to encrypt the text in
        AES MODE_CBC. The IV is returned together with the cipher text.
        <IV:Cipher>

        :param data: The text to encrypt
        :type data: str or bytes
        :param password: The password to derive a key from
        :type password: str or bytes
        :return: IV and cipher text
        :rtype: str
        """
        bkey = create_key_from_password(password)
        # convert input to ascii, so we can securely append bin data for padding
        input_data = binascii.hexlify(to_bytes(data))
        input_data += b"\x01\x02"
        padding = (16 - len(input_data) % 16) % 16
        input_data += padding * b"\0"
        iv = geturandom(16)
        cipher = aes_cbc_encrypt(bkey, iv, input_data)
        iv_hex = hexlify_and_unicode(iv)
        cipher_hex = hexlify_and_unicode(cipher)
        return "{0!s}:{1!s}".format(iv_hex, cipher_hex)

    @staticmethod
    def password_decrypt(enc_data, password):
        """
        Decrypt the given data with the password.
        A key is derived from the password. The data is hexlified data, the IV
        is the first part, separated with a ":".

        :param enc_data: The hexlified data
        :type enc_data: str
        :param password: The password, that is used to decrypt the data
        :type password: str or bytes
        :return: The clear test
        :rtype: bytes
        """
        bkey = create_key_from_password(password)
        # split the input data
        iv_hex, cipher_hex = enc_data.strip().split(":")
        iv_bin = binascii.unhexlify(iv_hex)
        cipher_bin = binascii.unhexlify(cipher_hex)
        output = aes_cbc_decrypt(bkey, iv_bin, cipher_bin)
        # remove padding
        eof = output.rfind(b"\x01\x02")
        if eof >= 0:
            output = output[:eof]
        cleartext = binascii.unhexlify(output)
        return cleartext

    def decrypt(self, enc_data, iv, key_id=SecurityModule.TOKEN_KEY):
        """
        Decrypt the given data with the key from the key slot

        :param enc_data: the to be decrypted data
        :type enc_data: bytes

        :param iv: initialisation vector (salt)
        :type iv: bytes

        :param key_id: slot of the key array
        :type key_id: int

        :return: decrypted data
        :rtype: bytes
        """
        if self.is_ready is False:
            raise HSMException('setup of security module incomplete')

        key = self._get_secret(key_id)
        output = aes_cbc_decrypt(key, iv, enc_data)
        # remove padding
        eof = output.rfind(b"\x01\x02")
        if eof >= 0:
            output = output[:eof]

        # convert output from ascii, back to bin data
        data = binascii.unhexlify(output)

        if self.crypted is False:
            zerome(key)
            del key

        return data
