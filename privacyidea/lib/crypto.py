# -*- coding: utf-8 -*-
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

This lib.cryto is tested in tests/test_lib_crypto.py
"""
import hmac
import logging
from hashlib import sha256
import random
import string
from .log import log_with
from .error import HSMException
import binascii
import ctypes
from flask import current_app
from Crypto.Hash import SHA as SHA1
from Crypto.Hash import SHA256 as HashFunc
from Crypto.Cipher import AES
import sys
import traceback
from Crypto.PublicKey import RSA


(ma, mi, _, _, _,) = sys.version_info
pver = float(int(ma) + int(mi) * 0.1)

log = logging.getLogger(__name__)

c_hash = {'sha1': SHA1,
          'sha256': HashFunc}

try:
    from Crypto.Hash import SHA224
    c_hash['sha224'] = SHA224
except:  # pragma: no cover
    log.warning('Your system does not support Crypto SHA224 hash algorithm')

try:
    from Crypto.Hash import SHA384
    c_hash['sha384'] = SHA384
except:  # pragma: no cover
    log.warning('Your system does not support Crypto SHA384 hash algorithm')

try:
    from Crypto.Hash import SHA512
    c_hash['sha512'] = SHA512
except:  # pragma: no cover
    log.warning('Your system does not support Crypto SHA512 hash algorithm')


# constant - later taken from the env?
CONFIG_KEY = 1
TOKEN_KEY = 2
VALUE_KEY = 3


class SecretObj:
    def __init__(self, val, iv, preserve=True):
        self.val = val
        self.iv = iv
        self.bkey = None
        self.preserve = preserve

    def getKey(self):
        log.warn('Requesting secret key '
                 '- verify the usage scope and zero + free ')
        return decrypt(self.val, self.iv)

    def getPin(self):
        return decrypt(self.val, self.iv)

    def compare(self, key):
        bhOtpKey = binascii.unhexlify(key)
        enc_otp_key = encrypt(bhOtpKey, self.iv)
        otpKeyEnc = binascii.hexlify(enc_otp_key)
        return (otpKeyEnc == self.val)

    def hmac_digest(self, data_input, hash_algo):
        self._setupKey_()
        if pver > 2.6:
            # only for debugging
            _hex_kex = binascii.hexlify(self.bkey)
            h = hmac.new(self.bkey, data_input, hash_algo).digest()
        else:
            h = hmac.new(self.bkey, str(data_input), hash_algo).digest()
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

# This is never used. So we will remove it.
#    def encryptPin(self):
#        self._setupKey_()
#        res = encryptPin(self.bkey)
#        self._clearKey_(preserve=self.preserve)
#        return res

    def _setupKey_(self):
        if self.bkey is None:
            akey = decrypt(self.val, self.iv)
            self.bkey = binascii.unhexlify(akey)
            zerome(akey)
            del akey

    def _clearKey_(self, preserve=False):
        if preserve is False:
            if self.bkey is not None:
                zerome(self.bkey)
                del self.bkey

    # This is used to remove the encryption key from the memory, but
    # this could also disturb the garbage collector and lead to memory eat ups.
    def __del__(self):
        self._clearKey_()
        
# This is never used. It would be used for something like:
# with SecretObj:
#    ....
#    def __enter__(self):
#        self._clearKey_()
#
#    def __exit__(self, typ, value, traceback):
#        self._clearKey_()


# def check(st):
#     """
#     calculate the checksum of st
#     :param st: input string
#     :return: the checksum code as 2 hex bytes
#     """
#     summ = 0
#     arry = bytearray(st)
#     for x in arry:
#         summ = summ ^ x
#     res = str(hex(summ % 256))[2:]
#     if len(res) < 2:
#         res = '0' * (2 - len(res)) + res
#     return res.upper()

#
# def kdf2(sharesecret, nonce,
#          activationcode, length,
#          iterations=10000,
#          digest='SHA256', macmodule=HMAC, checksum=True):
#     '''
#     key derivation function
#
#     - takes the shared secret, an activation code and a nonce to generate a
#          new key
#     - the last 4 btyes (8 chars) of the nonce is the salt
#     - the last byte    (2 chars) of the activation code are the checksum
#     - the activation code mitght contain '-' signs for grouping char blocks
#        aabbcc-ddeeff-112233-445566
#
#     :param sharedsecret:    hexlified binary value
#     :param nonce:           hexlified binary value
#     :param activationcode:  base32 encoded value
#
#     '''
#     digestmodule = c_hash.get(digest.lower(), None)
#
#     byte_len = 2
#     salt_len = 8 * byte_len
#
#     salt = u'' + nonce[-salt_len:]
#     bSalt = binascii.unhexlify(salt)
#     activationcode = activationcode.replace('-', '')
#
#     acode = activationcode
#     if checksum is True:
#         acode = str(activationcode)[:-2]
#
#     try:
#         bcode = base64.b32decode(acode)
#
#     except Exception as exx:
#         error = "Error during decoding activationcode %r: %r" % (acode, exx)
#         log.error(error)
#         raise Exception(error)
#
#     if checksum is True:
#         checkCode = str(activationcode[-2:])
#         veriCode = str(check(bcode)[-2:])
#         if checkCode != veriCode:
#             raise Exception('[crypt:kdf2] activation code checksum error!! '
#                             ' [%s]%s:%s' % (acode, veriCode, checkCode))
#
#     activ = binascii.hexlify(bcode)
#     passphrase = u'' + sharesecret + activ + nonce[:-salt_len]
#     #keyStream = PBKDF2(binascii.unhexlify(passphrase),
#     #                   bSalt, iterations=iterations,
#     #                   digestmodule=digestmodule)
#     #key = keyStream.read(length)
#     key = pbkdf2_sha256(binascii.unhexlify(passphrase),
#                         salt=bSalt, rounds=iterations)
#     return key


@log_with(log, log_entry=False, log_exit=False)
def hash(val, seed, algo=None):
    log.debug('hash()')
    m = sha256()
    m.update(val.encode('utf-8'))
    m.update(seed)
    return m.digest()


def init_hsm():
    """
    Initialize the HSM in the current_app config
    :return: hsm object
    """
    config = current_app.config
    if "pi_hsm" not in config or not isinstance(config["pi_hsm"], dict):
        from security.default import DefaultSecurityModule
        # TODO: Migration fix it
        HSM_config = {"obj": DefaultSecurityModule({"file":
                                                        config.get("PI_ENCFILE")})}
        current_app.config["pi_hsm"] = HSM_config
    hsm = current_app.config.get("pi_hsm").get('obj')
    return hsm


def _get_hsm():
    hsm = init_hsm()
    if hsm is None or not hsm.is_ready:  # pragma: no cover
        raise HSMException('hsm not ready!')

    return hsm


@log_with(log, log_entry=False)
def encryptPassword(password):
    hsm = _get_hsm()
    try:
        ret = hsm.encrypt_password(password)
    except Exception as exx:  # pragma: no cover
        log.warning(exx)
        ret = "FAILED TO ENCRYPT PASSWORD!"
    return ret


@log_with(log, log_entry=False)
def encryptPin(cryptPin):
    hsm = _get_hsm()
    ret = hsm.encrypt_pin(cryptPin)
    return ret


@log_with(log, log_exit=False)
def decryptPassword(cryptPass):
    hsm = _get_hsm()
    try:
        ret = hsm.decrypt_password(cryptPass)
    except Exception as exx:  # pragma: no cover
        log.warning(exx)
        ret = "FAILED TO DECRYPT PASSWORD!"
    return ret


@log_with(log, log_exit=False)
def decryptPin(cryptPin):
    hsm = _get_hsm()
    ret = hsm.decrypt_pin(cryptPin)
    return ret


@log_with(log, log_entry=False)
def encrypt(data, iv, id=0):
    '''
    encrypt a variable from the given input with an initialiation vector

    :param input: buffer, which contains the value
    :type  input: buffer of bytes
    :param iv:    initilaitation vector
    :type  iv:    buffer (20 bytes random)
    :param id:    contains the id of which key of the keyset should be used
    :type  id:    int
    :return:      encryted buffer


    '''
    hsm = _get_hsm()
    ret = hsm.encrypt(data, iv, id)
    return ret


@log_with(log, log_exit=False)
def decrypt(input, iv, id=0):
    '''
    decrypt a variable from the given input with an initialiation vector

    :param input: buffer, which contains the crypted value
    :type  input: buffer of bytes
    :param iv:    initilaitation vector
    :type  iv:    buffer (20 bytes random)
    :param id:    contains the id of which key of the keyset should be used
    :type  id:    int
    :return:      decryted buffer

    '''
    hsm = _get_hsm()
    ret = hsm.decrypt(input, iv, id)
    return ret


# @log_with(log)
def geturandom(length=20, hex=False):
    '''
    get random - from the security module

    :param length: length of the returned bytes - default is 20 bytes
    :rtype length: int

    :return: buffer of bytes

    '''
    hsm = _get_hsm()
    ret = hsm.random(length)
        
    if hex:
        ret = binascii.hexlify(ret)
    return ret

# some random functions based on geturandom #################################


class urandom(object):

    precision = 12

    @classmethod
    def random(cls):
        """
        get random float value betwee 0.0 and 1.0

        :return: float value
        """
        # get a binary random string
        randbin = geturandom(urandom.precision)

        # convert this to an integer
        randi = int(randbin.encode('hex'), 16) * 1.0

        # get the max integer
        intmax = 2 ** (8 * urandom.precision) * 1.0

        # scale the integer to an float between 0.0 and 1.0
        randf = randi / intmax

        assert randf >= 0.0
        assert randf <= 1.0

        return randf

    @classmethod
    def uniform(cls, start, end=None):
        """
        get a floating value between start and end

        :param start: start floafing value
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

    @classmethod
    def randint(cls, start, end=None):
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

    @classmethod
    def choice(cls, array):
        '''
        get one out of an array

        :param array: sequence - string or list
        :return: array element
        '''
        size = len(array)
        idx = urandom.randint(0, size)
        return array[idx]

    @classmethod
    def randrange(cls, start, stop=None, step=1):
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
    randd = geturandom(clen)
    s = "%d" % (int(randd.encode('hex'), 16))
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
        ret += random.choice(string.lowercase + string.uppercase +
                             string.digits)
    return ret


def zerome(bufferObject):
    '''
    clear a string value from memory

    :param string: the string variable, which should be cleared
    :type  string: string or key buffer

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
            log.error("Error reading private key %s: (%r)" % (private_file, e))
            raise e

        try:
            f = open(public_file, "r")
            self.public = f.read()
            f.close()
        except Exception as e:
            log.error("Error reading public key %s: (%r)" % (public_file, e))
            raise e

    def sign(self, s):
        """
        Create a signature of the string s

        :return: The signature of the string
        :rtype: long
        """
        RSAkey = RSA.importKey(self.private)
        hashvalue = HashFunc.new(s).digest()
        signature = RSAkey.sign(hashvalue, 1)
        s_signature = str(signature[0])
        return s_signature

    def verify(self, s, signature):
        """
        Check the signature of the string s
        """
        r = False
        try:
            RSAkey = RSA.importKey(self.public)
            hashvalue = HashFunc.new(s).digest()
            signature = long(signature)
            r = RSAkey.verify(hashvalue, (signature,))
        except Exception:  # pragma: no cover
            log.error("Failed to verify signature: %r" % s)
            log.error(traceback.format_exc())
        return r
