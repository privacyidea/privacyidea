# -*- coding: utf-8 -*-
#
#  2018-12-19 Paul Lettich <paul.lettich@netknights.it>
#             Change public functions to accept and return unicode
#  2017-11-24 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Use HSM for iv in aes_encrypt
#  2017-10-17 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add encryption/decryption for PSKC containers.
#  2016-04-08 Cornelius Kölbel <cornelius@privacyidea.org>
#             Avoid consecutive if statements
#
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
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
contains all crypto functions.
Security module functions are contained under lib/security/

The encrypt/decrypt functions for PINs and passwords accept bytes as well
as unicode strings. They always return a hexlified unicode string.
The functions which encrypt/decrypt arbitrary data return bytes and let the
calling function handle the data.

This lib.cryto is tested in tests/test_lib_crypto.py
"""
from __future__ import division
import hmac
import logging
from hashlib import sha256
import random
import string
import binascii
import six
import ctypes
from Crypto.Hash import SHA256 as HashFunc
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA
import base64
try:
    from Crypto.Signature import pkcs1_15
    SIGN_WITH_RSA = False
except ImportError:
    # Bummer the version of PyCrypto has no PKCS1_15
    SIGN_WITH_RSA = True
import passlib.hash
import traceback
from six import PY2, text_type

from privacyidea.lib.log import log_with
from privacyidea.lib.error import HSMException
from privacyidea.lib.framework import (get_app_local_store, get_app_config_value,
                                       get_app_config)
from privacyidea.lib.utils import to_unicode, to_bytes, hexlify_and_unicode

if not PY2:
    long = int

FAILED_TO_DECRYPT_PASSWORD = "FAILED TO DECRYPT PASSWORD!"

log = logging.getLogger(__name__)


class SecretObj(object):
    def __init__(self, val, iv, preserve=True):
        self.val = val
        self.iv = iv
        self.bkey = None
        self.preserve = preserve

    def getKey(self):
        log.warning('Requesting secret key '
                    '- verify the usage scope and zero + free ')
        return decrypt(self.val, self.iv)

    def getPin(self):
        return decrypt(self.val, self.iv)

    def compare(self, key):
        bhOtpKey = binascii.unhexlify(key)
        enc_otp_key = to_bytes(encrypt(bhOtpKey, self.iv))
        return enc_otp_key == self.val

    def hmac_digest(self, data_input, hash_algo):
        self._setupKey_()
        h = hmac.new(self.bkey, data_input, hash_algo).digest()
        self._clearKey_(preserve=self.preserve)
        return h

    def aes_decrypt(self, data_input):
        '''
        support inplace aes decryption for the yubikey

        :param data_input: data, that should be decrypted
        :return: the decrypted data
        '''
        self._setupKey_()
        aes = AES.new(self.bkey, AES.MODE_ECB)
        msg_bin = aes.decrypt(data_input)
        self._clearKey_(preserve=self.preserve)
        return msg_bin

    def _setupKey_(self):
        if self.bkey is None:
            akey = decrypt(self.val, self.iv)
            self.bkey = binascii.unhexlify(akey)
            zerome(akey)
            del akey

    def _clearKey_(self, preserve=False):
        if preserve is False and self.bkey is not None:
            zerome(self.bkey)
            del self.bkey

    # This is used to remove the encryption key from the memory, but
    # this could also disturb the garbage collector and lead to memory eat ups.
    def __del__(self):
        self._clearKey_()


@log_with(log, log_entry=False, log_exit=False)
def hash(val, seed, algo=None):
    """

    :param val: value to hash
    :type val: bytes or str or unicode
    :param seed: seed for the hash
    :type seed: bytes, str, unicode
    :param algo:
    :return: the hexlified hash value calculated from hash and seed
    :rtype: str
    """
    log.debug('hash()')
    m = sha256()
    m.update(to_bytes(val))
    m.update(to_bytes(seed))
    return hexlify_and_unicode(m.digest())


def hash_with_pepper(password):
    """
    Hash function to hash with salt and pepper. The pepper is read from
    "PI_PEPPER" from pi.cfg.

    Is used with admins and passwordReset

    :param password: the password to hash
    :type password: str
    :return: hashed password string
    :rtype: str
    """
    key = get_app_config_value("PI_PEPPER", "missing")
    pw_dig = passlib.hash.pbkdf2_sha512.hash(key + password)
    return pw_dig


def verify_with_pepper(passwordhash, password):
    """
    verify the password hash with the given password and pepper

    :param passwordhash: the passwordhash
    :type passwordhash: str
    :param password: the password to verify
    :type password: str
    :return: whether the password matches the hash
    :rtype: bool
    """
    # get the password pepper
    password = password or ""
    key = get_app_config_value("PI_PEPPER", "missing")
    success = passlib.hash.pbkdf2_sha512.verify(key + password, passwordhash)
    return success


def init_hsm():
    """
    Initialize the HSM in the app-local store

    The config file pi.cfg may contain PI_HSM_MODULE and parameters like:
    PI_HSM_MODULE_MODULE
    PI_HSM_MODULE_SLOT_ID...

    :return: hsm object
    """
    app_store = get_app_local_store()
    if "pi_hsm" not in app_store or not isinstance(app_store["pi_hsm"], dict):
        config = get_app_config()
        HSM_config = {"obj": create_hsm_object(config)}
        app_store["pi_hsm"] = HSM_config
        log.info("Initialized HSM object {0}".format(HSM_config))
    return app_store["pi_hsm"]["obj"]


def get_hsm(require_ready=True):
    """
    Check that the HSM has been set up properly and return it.
    If it is None, raise a HSMException.
    If it is not ready, raise a HSMException. Optionally, the ready check can be disabled.
    :param require_ready: Check whether the HSM is ready
    :return: a HSM module object
    """
    hsm = init_hsm()
    if hsm is None:
        raise HSMException('hsm is None!')
    if require_ready and not hsm.is_ready:
        raise HSMException('hsm not ready!')
    return hsm


def set_hsm_password(password):
    """
    Set the password for the HSM. Raises an exception if the HSM is already set up.
    :param password: password string
    :return: boolean flag indicating whether the HSM is ready now
    """
    hsm = init_hsm()
    if hsm.is_ready:
        raise HSMException("HSM already set up.")
    return hsm.setup_module({"password": password})


@log_with(log, log_entry=False)
def encryptPassword(password):
    """
    Encrypt given password with hsm

    This function returns a unicode string with a
    hexlified contents of the IV and the encrypted data separated by a
    colon like u"4956:44415441"

    :param password: the password
    :type password: bytes or str
    :return: the encrypted password, hexlified
    :rtype: str
    """
    hsm = get_hsm()
    try:
        ret = hsm.encrypt_password(to_bytes(password))
    except Exception as exx:  # pragma: no cover
        log.warning(exx)
        ret = "FAILED TO ENCRYPT PASSWORD!"
    return ret


@log_with(log, log_entry=False)
def encryptPin(cryptPin):
    """
    :param cryptPin: the pin to encrypt
    :type cryptPin: bytes or str
    :return: the encrypted pin
    :rtype: str
    """
    hsm = get_hsm()
    return to_unicode(hsm.encrypt_pin(to_bytes(cryptPin)))


@log_with(log, log_exit=False)
def decryptPassword(cryptPass):
    """
    Decrypt the encrypted password ``cryptPass`` and return it.
    If an error occurs during decryption, return FAILED_TO_DECRYPT_PASSWORD.

    :param cryptPass: str
    :return: the decrypted password
    :rtype: str
    """
    hsm = get_hsm()
    try:
        ret = hsm.decrypt_password(cryptPass)
    except Exception as exx:
        log.warning(exx)
        ret = FAILED_TO_DECRYPT_PASSWORD
    return ret


@log_with(log, log_exit=False)
def decryptPin(cryptPin):
    """

    :param cryptPin: the encrypted pin
    :type cryptPin: str, bytes, unicode
    :return: the decrypted pin
    :rtype: str
    """
    hsm = get_hsm()
    return hsm.decrypt_pin(cryptPin)


@log_with(log, log_entry=False)
def encrypt(data, iv, id=0):
    '''
    encrypt a variable from the given input with an initialisation vector

    :param data: buffer, which contains the value
    :type  data: bytes or str
    :param iv:   initialisation vector
    :type  iv:   bytes or str
    :param id:   contains the key id of the keyset which should be used
    :type  id:   int
    :return:     encrypted and hexlified data
    :rtype: str

    '''
    hsm = get_hsm()
    ret = hsm.encrypt(to_bytes(data), to_bytes(iv), id)
    return hexlify_and_unicode(ret)


@log_with(log, log_exit=False)
def decrypt(input, iv, id=0):
    '''
    decrypt a variable from the given input with an initialiation vector

    :param input: buffer, which contains the crypted value
    :type  input: bytes or str
    :param iv:    initialisation vector
    :type  iv:    bytes or str
    :param id:    contains the key id of the keyset which should be used
    :type  id:    int
    :return:      decrypted buffer
    :rtype: bytes
    '''
    hsm = get_hsm()
    res = hsm.decrypt(to_bytes(input), to_bytes(iv), id)
    return res


@log_with(log, log_exit=False)
def aes_decrypt(key, iv, cipherdata, mode=AES.MODE_CBC):
    """
    Decrypts the given cipherdata with the key/iv.

    :param key: The encryption key
    :type key: bytes
    :param iv: The initialization vector
    :type iv: bytes
    :param cipherdata: The cipher text
    :type cipherdata: binary string
    :param mode: The AES MODE
    :return: plain text in binary data
    :rtype: bytes
    """
    aes = AES.new(key, mode, iv)
    output = aes.decrypt(cipherdata)
    padding = six.indexbytes(output, len(output) - 1)
    # remove padding
    output = output[0:-padding]
    return output


def aes_encrypt(key, iv, data, mode=AES.MODE_CBC):
    """
    encrypts the given data with key/iv

    :param key: The encryption key
    :type key: binary string
    :param iv: The initialization vector
    :type iv: binary string
    :param data: The cipher text
    :type data: bytes
    :param mode: The AES MODE
    :return: plain text in binary data
    :rtype: bytes
    """
    aes = AES.new(key, mode, iv)
    # pad data
    num_pad = aes.block_size - (len(data) % aes.block_size)
    data = data + six.int2byte(num_pad) * num_pad
    output = aes.encrypt(data)
    return output


def aes_encrypt_b64(key, data):
    """
    This function encrypts the data using AES-128-CBC. It generates
    and adds an IV.
    This is used for PSKC.

    :param key: Encryption key (binary format)
    :param data: Data to encrypt
    :type data: bytes
    :return: base64 encrypted output, containing IV
    :rtype: bytes
    """
    iv = geturandom(16)
    encdata = aes_encrypt(key, iv, data)
    return base64.b64encode(iv + encdata)


def aes_decrypt_b64(key, data_b64):
    """
    This function decrypts base64 encoded data (containing the IV)
    using AES-128-CBC. Used for PSKC

    :param key: binary key
    :param data_b64: base64 encoded data (IV + encdata)
    :return: encrypted data
    """
    data_bin = base64.b64decode(data_b64)
    iv = data_bin[:16]
    encdata = data_bin[16:]
    output = aes_decrypt(key, iv, encdata)
    return output


# @log_with(log)
def geturandom(length=20, hex=False):
    '''
    get random - from the security module

    :param length: length of the returned bytes - default is 20 bytes
    :type length: int
    :param hex: convert result to hexstring
    :type hex: bool

    :return:
    :rtype: bytes, unicode

    '''
    hsm = get_hsm()
    ret = hsm.random(length)
        
    if hex:
        ret = to_unicode(binascii.hexlify(ret))
    return ret

# some random functions based on geturandom #################################


class urandom(object):

    precision = 12

    @staticmethod
    def random():
        """
        get random float value between 0.0 and 1.0

        :return: float value
        """
        # get a binary random string
        randhex = geturandom(urandom.precision, hex=True)

        # convert this to an integer
        randi = int(randhex, 16) * 1.0

        # get the max integer
        intmax = 2 ** (8 * urandom.precision) * 1.0

        # scale the integer to an float between 0.0 and 1.0
        randf = randi / intmax

        return randf

    @staticmethod
    def uniform(start, end=None):
        """
        get a floating value between start and end

        :param start: start floating value
        :param end: end floating value
        :return: floating value between start and end
        """
        if end is None:
            end = start
            start = 0.0

        # make sure we have a float
        startf = start * 1.0

        dist = (end - start)
        # if end lower than start invert the distance and start at the end
        if dist < 0:
            dist = dist * -1.0
            startf = end * 1.0

        ret = urandom.random()

        # result is start value + stretched distance
        res = startf + ret * dist

        return res

    @staticmethod
    def randint(start, end=None):
        """
        get random integer in between of start and end

        :return: random int
        """
        if end is None:
            end = start
            start = 0

        dist = end - start
        # if end lower than start invert the distance and start at the end
        if dist < 0:
            dist = dist * -1
            start = end

        randf = urandom.random()

        # result is start value + stretched distance
        ret = int(start + randf * dist)

        return ret

    @staticmethod
    def choice(array):
        '''
        get one out of an array

        :param array: sequence - string or list
        :return: array element
        '''
        size = len(array)
        idx = urandom.randint(0, size)
        return array[idx]

    @staticmethod
    def randrange(start, stop=None, step=1):
        """
        get one out of a range of values

        :param start: start of range
        :param stop: end value
        :param step: the step distance between two values

        :return: int value
        """
        if stop is None:
            stop = start
            start = 0
        # see python definition of randrange
        res = urandom.choice(range(start, stop, step))
        return res


def get_rand_digit_str(length=16):
    """
    return a string of digits with a defined length
    using the urandom

    This is used for creating transaction ids of challenges.
    It does not work for length==1!

    :return: random string
    :rtype: basestring
    """
    if length == 1:
        raise ValueError("get_rand_digit_str only works for values > 1")
    clen = int(length / 2.4 + 0.5)
    randd = geturandom(clen, hex=True)
    s = "{0:d}".format((int(randd, 16)))
    if len(s) < length:
        s = "0" * (length - len(s)) + s
    elif len(s) > length:
        s = s[:length]
    return s


def get_alphanum_str(length=16):
    """
    return a string of alphanumeric characters

    :return: random string
    :rtype: basestring
    """
    ret = ""
    for i in range(length):
        ret += random.choice(string.ascii_letters + string.digits)
    return ret


def zerome(bufferObject):
    '''
    clear a string value from memory

    :param bufferObject: the string variable, which should be cleared
    :type  bufferObject: string or key buffer

    :return:    - nothing -
    '''
    data = ctypes.POINTER(ctypes.c_char)()
    size = ctypes.c_int()  # Note, int only valid for python 2.5
    ctypes.pythonapi.PyObject_AsCharBuffer(ctypes.py_object(bufferObject),
                                           ctypes.pointer(data),
                                           ctypes.pointer(size))
    ctypes.memset(data, 0, size.value)

    return


class Sign(object):
    """
    Signing class that is used to sign Audit Entries and to sign API responses.
    """
    def __init__(self, private_file, public_file):
        """
        :param private_file: The privacy Key file
        :type private_file: filename
        :param public_file:  The public key file
        :type public_file: filename
        :return: Sign Object
        """
        self.private = ""
        self.public = ""
        try:
            f = open(private_file, "r")
            self.private = f.read()
            f.close()
        except Exception as e:
            log.error("Error reading private key {0!s}: ({1!r})".format(private_file, e))
            raise e

        try:
            f = open(public_file, "r")
            self.public = f.read()
            f.close()
        except Exception as e:
            log.error("Error reading public key {0!s}: ({1!r})".format(public_file, e))
            raise e

    def sign(self, s):
        """
        Create a signature of the string s

        :param s: String to sign
        :type s: str
        :return: The signature of the string
        :rtype: long
        """
        if isinstance(s, text_type):
            s = s.encode('utf8')
        RSAkey = RSA.importKey(self.private)
        if SIGN_WITH_RSA:
            hashvalue = HashFunc.new(s).digest()
            signature = RSAkey.sign(hashvalue, 1)
        else:
            hashvalue = HashFunc.new(s)
            signature = pkcs1_15.new(RSAkey).sign(hashvalue)
        s_signature = str(signature[0])
        return s_signature

    def verify(self, s, signature):
        """
        Check the signature of the string s

        :param s: String to check
        :type s: str
        :param signature: the signature to compare
        :type signature: str
        """
        if isinstance(s, text_type):
            s = s.encode('utf8')
        r = False
        try:
            RSAkey = RSA.importKey(self.public)
            signature = long(signature)
            if SIGN_WITH_RSA:
                hashvalue = HashFunc.new(s).digest()
                r = RSAkey.verify(hashvalue, (signature,))
            else:
                hashvalue = HashFunc.new(s)
                pkcs1_15.new(RSAkey).verify(hashvalue, signature)
        except Exception as _e:  # pragma: no cover
            log.error("Failed to verify signature: {0!r}".format(s))
            log.debug("{0!s}".format(traceback.format_exc()))
        return r


def create_hsm_object(config):
    """
    This creates an HSM object from the given config dictionary.
    The config dictionary are the values that appear in pi.cfg.

    It is needed PI_HSM_MODULE and all other values
    PI_HSM_MODULE_* depending on the module implementation.

    :param config: A configuration dictionary
    :return: A HSM object
    """
    # We need this to resolve the circular dependency between utils and crypto.
    from privacyidea.lib.utils import get_module_class
    hsm_module_name = config.get("PI_HSM_MODULE",
                                 "privacyidea.lib.security.default.DefaultSecurityModule")
    package_name, class_name = hsm_module_name.rsplit(".", 1)
    hsm_class = get_module_class(package_name, class_name, "setup_module")
    log.info("initializing HSM class: {0!s}".format(hsm_class))
    hsm_parameters = {}
    if class_name == "DefaultSecurityModule":
        hsm_parameters = {"file": config.get("PI_ENCFILE")}
    else:
        # get all parameters by splitting every config entry starting with PI_HSM_MODULE_
        # and pass this as a config object to hsm_class.
        hsm_parameters = {}
        for key in config.keys():
            if key.startswith("PI_HSM_MODULE_"):
                param = key[len("PI_HSM_MODULE_"):].lower()
                hsm_parameters[param] = config.get(key)
        logging_params = dict(hsm_parameters)
        if "password" in logging_params:
            logging_params["password"] = "XXXX"
        log.info("calling HSM module with parameters {0}".format(logging_params))

    return hsm_class(hsm_parameters)


def generate_otpkey(key_size=20):
    """
    generates the HMAC key of keysize. Should be 20 or 32
    The key is returned as a hexlified string
    :param key_size: The size of the key to generate
    :type key_size: int
    :return: hexlified key
    :rtype: str
    """
    log.debug("generating key of size {0!s}".format(key_size))
    return hexlify_and_unicode(geturandom(key_size))


def generate_password(size=6, characters=string.ascii_lowercase +
                        string.ascii_uppercase + string.digits):
    """
    Generate a random password of the specified lenght of the given characters

    :param size: The length of the password
    :param characters: The characters the password may consist of
    :return: password
    :rtype: basestring
    """
    return ''.join(urandom.choice(characters) for _x in range(size))


def generate_keypair(rsa_keysize=2048):
    """
    This create a keypair, either RSA or ECC.
    The HSM should be used.

    # TODO: This must be much nicer...

    :return: tuple of (pubkey, privkey)
    """
    from OpenSSL import crypto
    from OpenSSL.crypto import _new_mem_buf, _bio_to_string
    from OpenSSL._util import lib as _lib, ffi as _ffi
    helper = crypto._PassphraseHelper(crypto.FILETYPE_PEM, None)

    bio_pub = _new_mem_buf()  # Memory buffers to write to
    bio_priv = _new_mem_buf()
    keypair = crypto.PKey()
    keypair.generate_key(crypto.TYPE_RSA, rsa_keysize)
    rsa_pkey = crypto._lib.EVP_PKEY_get1_RSA(keypair._pkey)
    crypto._lib.PEM_write_bio_RSAPublicKey(bio_pub, rsa_pkey)
    crypto._lib.PEM_write_bio_RSAPrivateKey(
            bio_priv, rsa_pkey,
        _ffi.NULL, _ffi.NULL, 0, helper.callback, helper.callback_args)
    return (_bio_to_string(bio_pub), _bio_to_string(bio_priv))
