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

This lib.crypto is tested in tests/test_lib_crypto.py
"""
import hmac
import logging
from hashlib import sha256
import secrets
import random
import string
import binascii
import ctypes

import base64
import traceback
from passlib.context import CryptContext
from privacyidea.lib.log import log_with
from privacyidea.lib.error import HSMException, ParameterError
from privacyidea.lib.framework import (get_app_local_store, get_app_config_value,
                                       get_app_config)
from privacyidea.lib.utils import (to_unicode, to_bytes, hexlify_and_unicode,
                                   b64encode_and_unicode)

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding


def safe_compare(a, b):
    return hmac.compare_digest(to_bytes(a), to_bytes(b))


ROUNDS = 9

# The CryptContext makes it easier to work with multiple password hash algorithms:
# The first algorithm in the list is the default algorithm used for hashing.
# When verifying a password hash, all algorithms in the context are checked
# until one succeeds (or all fail).

DEFAULT_HASH_ALGO_LIST = ['argon2', 'pbkdf2_sha512']
DEFAULT_HASH_ALGO_PARAMS = {'argon2__rounds': ROUNDS}

FAILED_TO_DECRYPT_PASSWORD = "FAILED TO DECRYPT PASSWORD!"  # nosec B105 # placeholder in case of error

log = logging.getLogger(__name__)


class SecretObj(object):
    def __init__(self, val, iv, preserve=True):
        self.val = val
        self.iv = iv
        self.bkey = None
        self.preserve = preserve

    def getKey(self):
        log.info('Requesting secret key '
                 '- verify the usage scope and zero + free ')
        return decrypt(self.val, self.iv)

    def getPin(self):
        return decrypt(self.val, self.iv)

    def compare(self, key):
        bhOtpKey = binascii.unhexlify(key)
        enc_otp_key = to_bytes(encrypt(bhOtpKey, self.iv))
        return safe_compare(enc_otp_key, self.val)

    def hmac_digest(self, data_input, hash_algo):
        self._setupKey_()
        h = hmac.new(self.bkey, data_input, hash_algo).digest()
        self._clearKey_(preserve=self.preserve)
        return h

    def aes_ecb_decrypt(self, enc_data):
        '''
        support inplace aes decryption for the yubikey (mode ECB)

        :param enc_data: data, that should be decrypted
        :return: the decrypted data
        '''
        self._setupKey_()
        backend = default_backend()
        cipher = Cipher(algorithms.AES(self.bkey), modes.ECB(), backend=backend)  # nosec B305 # part of Yubikey specification
        decryptor = cipher.decryptor()
        msg_bin = decryptor.update(enc_data) + decryptor.finalize()
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


@log_with(log, log_entry=False, log_exit=False)
def pass_hash(password):
    """
    Hash password with crypt context
    :param password: The password to hash
    :type password: str
    :return: The hash string of the password
    """
    DEFAULT_HASH_ALGO_PARAMS.update(get_app_config_value("PI_HASH_ALGO_PARAMS",
                                                         default={}))
    pass_ctx = CryptContext(get_app_config_value("PI_HASH_ALGO_LIST",
                                                 default=DEFAULT_HASH_ALGO_LIST),
                            **DEFAULT_HASH_ALGO_PARAMS)
    pw_dig = pass_ctx.hash(password)
    return pw_dig


@log_with(log, log_entry=False, log_exit=False)
def verify_pass_hash(password, hvalue):
    """
    Verify the hashed password value
    :param password: The plaintext password to verify
    :type password: str
    :param hvalue: The hashed password
    :type hvalue: str
    :return: True if the password matches
    :rtype: bool
    """
    pass_ctx = CryptContext(get_app_config_value("PI_HASH_ALGO_LIST",
                                                 default=DEFAULT_HASH_ALGO_LIST))
    return pass_ctx.verify(password, hvalue)


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
    return pass_hash(key + password)


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

    return verify_pass_hash(key + password, passwordhash)


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
    colon like "4956:44415441"

    :param password: the password
    :type password: bytes or str
    :return: the encrypted password, hexlified
    :rtype: str
    """
    hsm = get_hsm()
    try:
        password = password or ""
        ret = hsm.encrypt_password(to_bytes(password))
    except Exception as exx:  # pragma: no cover
        log.warning(exx)
        log.info(traceback.format_exc())
        raise HSMException("Failed to encrypt password!")
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
def encrypt(data, iv, key_id=0):
    """
    encrypt a variable from the given input with an initialisation vector

    :param data:   buffer, which contains the value
    :type  data:   bytes or str
    :param iv:     initialisation vector
    :type  iv:     bytes or str
    :param key_id: contains the key id of the keyset which should be used
    :type  key_id: int
    :return: encrypted and hexlified data
    :rtype: str
    """
    hsm = get_hsm()
    ret = hsm.encrypt(to_bytes(data), to_bytes(iv), key_id=key_id)
    return hexlify_and_unicode(ret)


@log_with(log, log_exit=False)
def decrypt(enc_data, iv, key_id=0):
    """
    decrypt a variable from the given input with an initialisation vector

    :param enc_data: buffer, which contains the crypted value
    :type  enc_data: bytes or str
    :param iv:       initialisation vector
    :type  iv:       bytes or str
    :param key_id:   contains the key id of the keyset which should be used
    :type  key_id:   int
    :return: decrypted buffer
    :rtype: bytes
    """
    hsm = get_hsm()
    res = hsm.decrypt(to_bytes(enc_data), to_bytes(iv), key_id=key_id)
    return res


@log_with(log, log_exit=False)
def aes_cbc_decrypt(key, iv, enc_data):
    """
    Decrypts the given cipherdata with AES (CBC Mode) using the key/iv.

    Attention: This function returns the decrypted data as is, without removing
    any padding. The calling function must take care of this!

    :param key: The encryption key
    :type key: bytes
    :param iv: The initialization vector
    :type iv: bytes
    :param enc_data: The cipher text
    :type enc_data: bytes
    :return: plain text in binary data
    :rtype: bytes
    """
    backend = default_backend()
    mode = modes.CBC(iv)
    cipher = Cipher(algorithms.AES(key), mode=mode, backend=backend)
    decryptor = cipher.decryptor()
    output = decryptor.update(enc_data) + decryptor.finalize()
    return output


def aes_cbc_encrypt(key, iv, data):
    """
    encrypts the given data with AES (CBC Mode) using key/iv.

    Attention: This function expects correctly padded input data (multiple of
    AES block size). The calling function must take care of this!

    :param key: The encryption key
    :type key: bytes
    :param iv: The initialization vector
    :type iv: bytes
    :param data: The cipher text
    :type data: bytes
    :return: plain text in binary data
    :rtype: bytes
    """
    if len(data) % (algorithms.AES.block_size // 8) != 0:  # pragma: no cover
        raise ParameterError("Invalid length of input data")
    # do the encryption
    backend = default_backend()
    mode = modes.CBC(iv)
    cipher = Cipher(algorithms.AES(key), mode=mode, backend=backend)
    encryptor = cipher.encryptor()
    output = encryptor.update(data) + encryptor.finalize()
    return output


def aes_encrypt_b64(key, data):
    """
    This function encrypts the data using AES-128-CBC. It generates
    and adds an IV.
    This is used for PSKC.

    :param key: Encryption key (binary format)
    :type key: bytes
    :param data: Data to encrypt
    :type data: bytes
    :return: base64 encrypted output, containing IV and encrypted data
    :rtype: str
    """
    # pad data
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded_data = padder.update(data) + padder.finalize()
    iv = geturandom(16)
    encdata = aes_cbc_encrypt(key, iv, padded_data)
    return b64encode_and_unicode(iv + encdata)


def aes_decrypt_b64(key, enc_data_b64):
    """
    This function decrypts base64 encoded data (containing the IV)
    using AES-128-CBC. Used for PSKC

    :param key: binary key
    :param enc_data_b64: base64 encoded data (IV + encdata)
    :type enc_data_b64: str
    :return: encrypted data
    """
    data_bin = base64.b64decode(enc_data_b64)
    iv = data_bin[:16]
    encdata = data_bin[16:]
    padded_data = aes_cbc_decrypt(key, iv, encdata)

    # remove padding
    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    output = unpadder.update(padded_data) + unpadder.finalize()

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
        ret += secrets.choice(string.ascii_letters + string.digits)
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


def _slow_rsa_verify_raw(key, sig, msg):
    if not (isinstance(sig, int) and isinstance(msg, int)):  # pragma: no cover
        raise ParameterError("Message and signature need to be integer")
    if hasattr(key, 'public_numbers'):
        pn = key.public_numbers()
    elif hasattr(key, 'private_numbers'):  # pragma: no cover
        pn = key.private_numbers().public_numbers
    else:  # pragma: no cover
        raise TypeError('No public key')

    # compute m**d (mod n) and compare the two integers
    return msg == pow(sig, pn.e, pn.n)


class Sign(object):
    """
    Signing class that is used to sign Audit Entries and to sign API responses.
    """
    sig_ver = 'rsa_sha256_pss'

    def __init__(self, private_key=None, public_key=None, check_private_key=True):
        """
        Initialize the Sign object with the given Keys.

        :param private_key: The private Key data in PEM format
        :type private_key: bytes or None
        :param public_key:  The public key data in PEM format
        :type public_key: bytes or None
        :param check_private_key: Check the private key when loading (default: True)
        :type check_private_key: bool
        :return: The Sign Object
        :rtype: Sign
        """
        self.private = None
        self.public = None
        backend = default_backend()
        if private_key:
            try:
                self.private = serialization.load_pem_private_key(private_key,
                                                                  password=None,
                                                                  backend=backend,
                                                                  unsafe_skip_rsa_key_validation=not check_private_key)
            except Exception as e:
                log.error("Error loading private key: ({0!r})".format(e))
                log.debug(traceback.format_exc())
                raise e

        if public_key:
            try:
                self.public = serialization.load_pem_public_key(public_key,
                                                                backend=backend)
            except Exception as e:
                log.error("Error loading public key: ({0!r})".format(e))
                log.debug(traceback.format_exc())
                raise e

    def sign(self, s):
        """
        Create a signature of the string s

        :param s: String to sign
        :type s: str
        :return: The hexlified and versioned signature of the string
        :rtype: str
        """
        if not self.private:
            log.info('Could not sign message {0!s}, no private key!'.format(s))
            # TODO: should we throw an exception in this case?
            return ''

        signature = self.private.sign(
            to_bytes(s),
            asym_padding.PSS(
                mgf=asym_padding.MGF1(hashes.SHA256()),
                salt_length=asym_padding.PSS.MAX_LENGTH),
            hashes.SHA256())
        res = ':'.join([self.sig_ver, hexlify_and_unicode(signature)])
        return res

    def verify(self, s, signature, verify_old_sigs=False):
        """
        Check the signature of the string s

        :param s: String to check
        :type s: str or bytes
        :param signature: the signature to compare
        :type signature: str or int
        :param verify_old_sigs: whether to check for old style signatures as well
        :type verify_old_sigs: bool
        :return: True if the signature is valid, false otherwise.
        :rtype: bool
        """
        r = False
        if not self.public:
            log.info('Could not verify signature for message {0!s}, '
                     'no public key!'.format(s))
            return r

        sver = ''
        try:
            sver, signature = str(signature).split(':')
        except ValueError:
            # if the signature does not contain a colon we assume an old style signature.
            pass

        try:
            if sver == self.sig_ver:
                self.public.verify(
                    binascii.unhexlify(signature),
                    to_bytes(s),
                    asym_padding.PSS(
                        mgf=asym_padding.MGF1(hashes.SHA256()),
                        salt_length=asym_padding.PSS.MAX_LENGTH),
                    hashes.SHA256())
                r = True
            else:
                if verify_old_sigs:
                    int_s = int(binascii.hexlify(sha256(to_bytes(s)).digest()), 16)
                    r = _slow_rsa_verify_raw(self.public, int(signature), int_s)
                else:
                    log.debug('Could not verify old style signature {0!s} '
                              'for data {1:s}'.format(signature, s))
        except Exception:
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
            logging_params["password"] = "XXXX"  # nosec B105 # Hide password
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
                        string.ascii_uppercase + string.digits, requirements=[]):
    """
    Generate a random password of the specified length of the given characters
    with optional requirements

    :param size: The length of the password. If smaller than the number of requirements,
    the requirements define the password length.
    :param characters: The characters the password may consist of
    :param requirements: A list of strings from which the password must contain at least one character.
    Note that the requirements are not automatically added to the base character set.
    :return: password
    :rtype: basestring
    """
    if len(requirements) > size:
        log.info('The number of requirements is larger then the password length.')
    # add one random character from each string in the requirements list
    passwd = [secrets.choice(str) for str in requirements]
    # fill the password until size with allowed characters
    passwd.extend(secrets.choice(characters) for _x in range(size - len(requirements)))
    # Shuffle, so that we mix the requirements and the generic characters
    random.shuffle(passwd)
    return "".join(passwd)


def generate_keypair(rsa_keysize=2048):
    """
    This creates an RSA key pair

    # TODO: The HSM should be used.

    The public key and private keys are returned in PKCS#1 Format.

    :return: tuple of (pubkey, privkey)
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=rsa_keysize,
        backend=default_backend()
        )
    public_key = private_key.public_key()
    pem_priv = to_unicode(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()))
    pem_pub = to_unicode(public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.PKCS1))
    return pem_pub, pem_priv
