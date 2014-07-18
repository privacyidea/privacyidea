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
'''contains all crypto functions
'''


import hmac
import logging
from hashlib import sha256
import base64
from privacyidea.lib.log import log_with

import binascii
import os
import stat

''' for the hmac algo, we have to check the python version '''
import sys
(ma, mi, _, _, _,) = sys.version_info
pver = float(int(ma) + int(mi) * 0.1)

import ctypes

from pylons.configuration import config as env
from pylons import tmpl_context as c
from privacyidea.lib.error import HSMException

import Crypto.Hash as CryptoHash
from Crypto.Hash import HMAC
from Crypto.Hash import SHA as SHA1
from Crypto.Hash import SHA256
from Crypto.Cipher import AES


from privacyidea.lib.ext.pbkdf2  import PBKDF2




log = logging.getLogger(__name__)

c_hash = {
         'sha1': SHA1,
         'sha256': SHA256,
         }

try:
    from Crypto.Hash import SHA224
    c_hash['sha224'] = SHA224
except:
    log.warning('Your system does not support Crypto SHA224 hash algorithm')

try:
    from Crypto.Hash import SHA384
    c_hash['sha384'] = SHA384
except:
    log.warning('Your system does not support Crypto SHA384 hash algorithm')

try:
    from Crypto.Hash import SHA512
    c_hash['sha512'] = SHA512
except:
    log.warning('Your system does not support Crypto SHA512 hash algorithm')



## constant - later taken from the env?
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

    def encryptPin(self):
        self._setupKey_()
        res = encryptPin(self.bkey)
        self._clearKey_(preserve=self.preserve)
        return res

    def _setupKey_(self):
        if self.bkey is None:
            akey = decrypt(self.val, self.iv)
            self.bkey = binascii.unhexlify(akey)
            zerome(akey)
            del akey

    def _clearKey_(self, preserve=False):
        if preserve == False:
            if self.bkey is not None:
                zerome(self.bkey)
                del self.bkey

    # This is used to remove the encryption key from the memory, but
    # this could also disturbe the garbage collector and lead to memory eat ups.
    def __del__(self):
        self._clearKey_()
    def __enter__(self):
        self._clearKey_()
    def __exit__(self, type, value, traceback):
        self._clearKey_()

@log_with(log)
def getSecretDummy():
    log.debug('getSecretDummy()')
    return "no secret file defined: privacyideaSecretFile!"


@log_with(log, log_exit=False)
def getSecret(id=0):

    if not env.has_key("privacyideaSecretFile"):
        log.error("No secret file defined. A parameter privacyideaSecretFile is missing in your privacyidea.ini.")
        raise Exception("no secret file defined: privacyideaSecretFile!")

    secFile = env["privacyideaSecretFile"]

    #if True == isWorldAccessible(secFile):
    #    log.error("file permission of the secret file :%s: are not secure!", secFile)
    #    raise Exception("permissions of the secret file are not secure!")
    secret = ''

    try:
        f = open(secFile)
        for _i in range (0 , id + 1):
            secret = f.read(32)
        f.close()
        if secret == "" :
            #secret = setupKeyFile(secFile, id+1)
            raise Exception ("No secret key defined for index: %s !\n"
                             "Please extend your %s !" % (unicode(id), secFile))
    except Exception as exx:
        raise Exception ("Exception: %r" % exx)

    return secret

def setupKeyFile(secFile, maxId):
    secret = ''
    for index in range(0, maxId):
        f = open(secFile)
        for _c in range(0, index + 1):
            secret = f.read(32)
        f.close()

        ## if no secret: fill in a new one
        if secret == "" :
            f = open(secFile, 'ab+')
            secret = geturandom(32)
            f.write(secret)
            f.close()

    return secret

@log_with(log)
def isWorldAccessible(filepath):
    st = os.stat(filepath)
    u_w = bool(st.st_mode & stat.S_IWUSR)
    g_r = bool(st.st_mode & stat.S_IRGRP)
    g_w = bool(st.st_mode & stat.S_IWGRP)
    o_r = bool(st.st_mode & stat.S_IROTH)
    o_w = bool(st.st_mode & stat.S_IWOTH)
    return g_r or g_w or o_r or o_w or u_w


def _getCrypto(description):
    '''
       Convert the name of a hash algorithm as described in the OATH
       specifications, to a python object handling the digest algorithm
       interface
    '''
    algo = getattr(CryptoHash, description.upper(), None)
    #if not callable(algo):
    #    raise ValueError, ('Unknown hash algorithm', s[1])
    return algo

def check(st):
    """
    calculate the checksum of st
    :param st: input string
    :return: the checksum code as 2 hex bytes
    """
    sum = 0
    arry = bytearray(st)
    for x in arry:
        sum = sum ^ x
    res = str(hex(sum % 256))[2:]
    if len(res) < 2:
        res = '0' * (2 - len(res)) + res
    return res.upper()


def createActivationCode(acode=None, checksum=True):
    """
    create the activation code

    :param acode: activation code or None
    :param checksum: flag to indicate, if a checksum will be calculated
    :return: return the activation code
    """
    if acode is None:
        acode = geturandom(20)
    activationcode = base64.b32encode(acode)
    if checksum == True:
        chsum = check(acode)
        activationcode = u'' + activationcode + chsum

    return activationcode

def createNonce(len=64):
    """
    create a nonce - which is a random string
    :param len: len of bytes to return
    :return: hext string
    """
    key = os.urandom(len)
    return binascii.hexlify(key)


def kdf2(sharesecret, nonce , activationcode, len, iterations=10000,
                               digest='SHA256', macmodule=HMAC, checksum=True):
    '''
    key derivation function

    - takes the shareed secret, an activation code and a nonce to generate a new key
    - the last 4 btyes (8 chars) of the nonce is the salt
    - the last byte    (2 chars) of the activation code are the checksum
    - the activation code mitght contain '-' signs for grouping char blocks
       aabbcc-ddeeff-112233-445566

    :param sharedsecret:    hexlified binary value
    :param nonce:           hexlified binary value
    :param activationcode:  base32 encoded value

    '''
    digestmodule = c_hash.get(digest.lower(), None)

    byte_len = 2
    salt_len = 8 * byte_len

    salt = u'' + nonce[-salt_len:]
    bSalt = binascii.unhexlify(salt)
    activationcode = activationcode.replace('-', '')

    acode = activationcode
    if checksum == True:
        acode = str(activationcode)[:-2]

    try:
        bcode = base64.b32decode(acode)

    except Exception as exx:
        error = "Error during decoding activationcode %r: %r" % (acode, exx)
        log.error(error)
        raise Exception(error)

    if checksum == True:
        checkCode = str(activationcode[-2:])
        veriCode = str(check(bcode)[-2:])
        if checkCode != veriCode:
            raise Exception('[crypt:kdf2] activation code checksum error!! [%s]%s:%s' % (acode, veriCode, checkCode))

    activ = binascii.hexlify(bcode)
    passphrase = u'' + sharesecret + activ + nonce[:-salt_len]
    keyStream = PBKDF2(binascii.unhexlify(passphrase), bSalt, iterations=iterations, digestmodule=digestmodule)
    key = keyStream.read(len)
    return key

@log_with(log, log_entry=False)
def hash(val, seed, algo=None):
    log.debug('hash()')
    m = sha256()
    m.update(val.encode('utf-8'))
    m.update(seed)
    return m.digest()

@log_with(log, log_entry=False)
def encryptPassword(password):

    log.debug('encryptPassword()')
    if hasattr(c, 'hsm') == False or isinstance(c.hsm, dict) == False:
        raise HSMException('no hsm defined in execution context!')

    hsm = c.hsm.get('obj')
    if hsm is None or hsm.isReady() == False:
        raise HSMException('hsm not ready!')

    ret = hsm.encryptPassword(password)
    return ret

@log_with(log, log_entry=False)
def encryptPin(cryptPin):

    log.debug('encryptPin()')
    if hasattr(c, 'hsm') == False or isinstance(c.hsm, dict) == False:
        raise HSMException('no hsm defined in execution context!')

    hsm = c.hsm.get('obj')
    if hsm is None or  hsm.isReady() == False:
        raise HSMException('hsm not ready!')

    ret = hsm.encryptPin(cryptPin)
    return ret

@log_with(log, log_exit=False)
def decryptPassword(cryptPass):

    if hasattr(c, 'hsm') == False or isinstance(c.hsm, dict) == False:
        raise HSMException('no hsm defined in execution context!')

    hsm = c.hsm.get('obj')
    if hsm is None or hsm.isReady() == False:
        raise HSMException('hsm not ready!')

    ret = hsm.decryptPassword(cryptPass)
    return ret

@log_with(log, log_exit=False)
def decryptPin(cryptPin):

    if hasattr(c, 'hsm') == False or isinstance(c.hsm, dict) == False:
        raise HSMException('no hsm defined in execution context!')

    hsm = c.hsm.get('obj')
    if hsm is None or hsm.isReady() == False:
        raise HSMException('hsm not ready!')

    ret = hsm.decryptPin(cryptPin)
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

    log.debug('encrypt()')
    if hasattr(c, 'hsm') == False or isinstance(c.hsm, dict) == False:
        raise HSMException('no hsm defined in execution context!')

    hsm = c.hsm.get('obj')
    if hsm is None or hsm.isReady() == False:
        raise HSMException('hsm not ready!')
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
    if hasattr(c, 'hsm') == False or isinstance(c.hsm, dict) == False:
        raise HSMException('no hsm defined in execution context!')

    hsm = c.hsm.get('obj')
    if hsm is None or hsm.isReady() == False:
        raise HSMException('hsm not ready!')

    ret = hsm.decrypt(input, iv, id)
    return ret

# @log_with(log)
def geturandom(len=20):
    '''
    get random - from the security module

    :param len:  len of the returned bytes - default is 20 bytes
    :tyrpe len:    int

    :return: buffer of bytes

    '''
    if hasattr(c, 'hsm') == False:
        ret = os.urandom(len)
        return ret

    if isinstance(c.hsm, dict) == False:
        raise HSMException('hsm not found!')

    hsm = c.hsm.get('obj')
    if hsm is None or hsm.isReady() == False:
        raise HSMException('hsm not ready!')

    ret = hsm.random(len)
    return ret

### some random functions based on geturandom #################################

class urandom(object):

    precision = 12

    @classmethod
    def random(cls):
        """
        get random float value betwee 0.0 and 1.0

        :return: float value
        """
        ## get a binary random string
        randbin = geturandom(urandom.precision)

        ## convert this to an integer
        randi = int(randbin.encode('hex'), 16) * 1.0

        ## get the max integer
        intmax = 2 ** (8 * urandom.precision) * 1.0

        ## scale the integer to an float between 0.0 and 1.0
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

        ## make sure we have a float
        startf = start * 1.0

        dist = (end - start)
        ## if end lower than start invert the distance and start at the end
        if dist < 0:
            dist = dist * -1.0
            startf = end * 1.0

        ret = urandom.random()

        ## result is start value + stretched distance
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
        ## if end lower than start invert the distance and start at the end
        if dist < 0:
            dist = dist * -1
            start = end

        randf = urandom.random()

        ## result is start value + stretched distance
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
        :param step: the step distance beween two values

        :return: int value
        """
        if stop is None:
            stop = start
            start = 0
        ## see python definition of randrange
        res = urandom.choice(range(start, stop, step))
        return res


def get_rand_digit_str(length=16):
    '''
    return a sting of digits with a defined length
    using the urandom
    '''
    clen = int(length / 2.4 + 0.5)
    randd = geturandom(len=clen)
    s = "%d" % (int(randd.encode('hex'), 16))
    if len(s) < length:
        s = "0" * (length - len(s)) + s
    elif len(s) > length:
        s = s[:length]
    return s


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
                                    ctypes.pointer(data), ctypes.pointer(size))
    ctypes.memset(data, 0, size.value)
    #print repr(bufferObject)
    return

##eof##########################################################################
