# -*- coding: utf-8 -*-
#
#  product:  privacyIDEA is a fork of LinOTP
#  May, 08 2014 Cornelius Kölbel
#  http://www.privacyidea.org
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


import logging
import binascii
import os

from Crypto.Cipher import AES

from privacyidea.lib.crypto import zerome
from privacyidea.lib.security import SecurityModule


TOKEN_KEY = 0
CONFIG_KEY = 1
VALUE_KEY = 2
DEFAULT_KEY = 3


log = logging.getLogger(__name__)


class DefaultSecurityModule(SecurityModule):


    def __init__(self, config=None):
        '''
        initialsation of the security module

        :param config:  contains the configuration definition
        :type  config:  - dict -

        :return -
        '''

        self.name = "Default"
        self.config = config
        self.crypted = False
        self.is_ready = True
        self._id = binascii.hexlify(os.urandom(3))


        if config.has_key('crypted'):
            crypt = config.get('crypted').lower()
            if crypt == 'true':
                self.crypted = True
                self.is_ready = False

        if config.has_key('file') == False:
            log.error("No secret file defined. A parameter privacyideaSecretFile is missing in your privacyidea.ini.")
            raise Exception("no secret file defined: privacyideaSecretFile!")

        self.secFile = config.get('file')
        self.secrets = {}

        return

    def isReady(self):
        '''
        provides the status, if the security module is fully initializes
        this is required especially for the runtime confi like set password ++

        :return:  status, if the module is fully operational
        :rtype:   boolean 

        '''
        return self.is_ready

    def getSecret(self, id=0):
        '''
        internal function, which acceses the key in the defined slot

        :param id: slot id of the key array
        :type  id: int

        :return: key or secret
        :rtype:  binary string

        '''
        log.debug('getSecret()')
        id = int(id)

        if self.crypted:
            if self.secrets.has_key(id):
                return self.secrets.get(id)

        secret = ''
        try:
                f = open(self.secFile)
                for _i in range (0 , id + 1):
                    secret = f.read(32)
                f.close()
                if secret == "" :
                    #secret = setupKeyFile(secFile, id+1)
                    raise Exception ("No secret key defined for index: %s !\n"
                                     "Please extend your %s"" !"
                                     % (str(id), self.secFile))
        except Exception as e:
            raise Exception ("Exception:" + unicode(e))

        if self.crypted:
            self.secrets[id] = secret

        return secret;

    def setup_module(self, param):
        '''
        callback, which is called during the runtime to initialze the security module

        :param params: all parameters, which are provided by the http request
        :type  params: dict

        :return: -

        '''
        if self.crypted == False:
            return
        if param.has_key('password') == False:
            raise Exception("missing password")

        ## if we have a crypted file and a password, we take all keys
        ## from the file and put them in a hash
        ##
        ## After this we do not require the password anymore

        handles = ['pinHandle' , 'passHandle' , 'valueHandle', 'defaultHandle']
        for handle in handles:
            self.getSecret(self.config.get(handle, '0'))

        self.is_ready = True
        return

    ## the real interfaces: random, encrypt, decrypt '''
    def random(self, len=32):
        '''
        security module methods: random

        :param len: length of the random byte array
        :type  len: int

        :return: random bytes
        :rtype:  byte string
        '''

        log.debug('random()')
        return os.urandom(len)

    def encrypt(self, data, iv, id=0):
        '''
        security module methods: encrypt

        :param data: the to be encrypted data
        :type  data:byte string

        :param iv: initialisation vector (salt)
        :type  iv: random bytes

        :param  id: slot of the key array
        :type   id: int

        :return: encrypted data
        :rtype:  byte string
        '''

        log.debug('encrypt()')

        if self.is_ready == False:
            raise Exception('setup of security module incomplete')

        key = self.getSecret(id)
        ## convert input to ascii, so we can securely append bin data
        input = binascii.b2a_hex(data)
        input += u"\x01\x02"
        padding = (16 - len(input) % 16) % 16
        input += padding * "\0"
        aes = AES.new(key, AES.MODE_CBC, iv)

        # cko: ARGH: Only ECB!
        #import privacyideaee.lib.yhsm as yhsm
        #y = yhsm.YubiHSM(0x1111, password="14fda9321ae820aa34e57852a31b10d0")
        #y.unlock(password="14fda9321ae820aa34e57852a31b10d0")
        #res = y.encrypt(input)
        #
        res = aes.encrypt(input)

        if self.crypted == False:
            zerome(key)
            del key
        return res

    def decrypt(self, input, iv, id=0):
        '''
        security module methods: decrypt

        :param data: the to be decrypted data
        :type  data:byte string

        :param iv: initialisation vector (salt)
        :type  iv: random bytes

        :param  id: slot of the key array
        :type   id: int 

        :return: decrypted data
        :rtype:  byte string
        '''

        log.debug('decrypt()')

        if self.is_ready == False:
            raise Exception('setup of security module incomplete')

        key = self.getSecret(id)
        aes = AES.new(key, AES.MODE_CBC, iv)
        # cko
        #import privacyideaee.lib.yhsm as yhsm
        #y = yhsm.YubiHSM(0x1111, password="14fda9321ae820aa34e57852a31b10d0")
        #y.unlock(password="14fda9321ae820aa34e57852a31b10d0")
        #log.debug("CKO in: %s" % input)
        #output = binascii.hexlify(y.decrypt(input))
        #log.debug("CKO out: %s" % output)
        #
        output = aes.decrypt(input)
        #log.debug("CKO: output2: %s" % output)
        eof = output.rfind(u"\x01\x02")
        if eof >= 0: output = output[:eof]

        ## convert output from ascii, back to bin data
        data = binascii.a2b_hex(output)

        if self.crypted == False:
            zerome(key)
            del key

        return data


    def decryptPassword(self, cryptPass):
        '''
        dedicated security module methods: decryptPassword
        which used one slot id to decryt a string

        :param cryptPassword: the crypted password - leading iv, seperated by the ':'
        :param cryptPassword: byte string

        :return: decrypted data
        :rtype:  byte string
        '''

        return self._decryptValue(cryptPass, CONFIG_KEY)

    def decryptPin(self, cryptPin):
        '''
        dedicated security module methods: decryptPin
        which used one slot id to decryt a string

        :param cryptPin: the crypted pin - - leading iv, seperated by the ':'
        :param cryptPin: byte string

        :return: decrypted data
        :rtype:  byte string
        '''

        return self._decryptValue(cryptPin, TOKEN_KEY)

    def encryptPassword(self, password):
        '''
        dedicated security module methods: encryptPassword
        which used one slot id to encrypt a string

        :param password: the to be encrypted password
        :param password: byte string

        :return: encrypted data - leading iv, seperated by the ':'
        :rtype:  byte string
        '''
        return self._encryptValue(password, CONFIG_KEY)

    def encryptPin(self, pin):
        '''
        dedicated security module methods: encryptPin
        which used one slot id to encrypt a string

        :param pin: the to be encrypted pin
        :param pin: byte string

        :return: encrypted data - leading iv, seperated by the ':'
        :rtype:  byte string
        '''
        return self._encryptValue(pin, TOKEN_KEY)


    ''' base methods for pin and password '''

    def _encryptValue(self, value, keyNum):
        '''
        _encryptValue - base method to encrypt a value
        - uses one slot id to encrypt a string 
        retrurns as string with leading iv, seperated by ':'

        :param value: the to be encrypted value
        :param value: byte string

        :param  id: slot of the key array
        :type   id: int

        :return: encrypted data with leading iv and sepeartor ':'
        :rtype:  byte string 
        '''
        iv = self.random(16)
        v = self.encrypt(value, iv , keyNum)

        value = binascii.hexlify(iv) + ':' + binascii.hexlify(v)
        return value

    def _decryptValue(self, cryptValue, keyNum):
        '''
        _decryptValue - base method to decrypt a value
        - used one slot id to encrypt a string with leading iv, seperated by ':'

        :param cryptValue: the to be encrypted value
        :param cryptValue: byte string

        :param  id: slot of the key array
        :type   id: int 

        :return: decrypted data
        :rtype:  byte string
        '''
        ## split at ":"
        pos = cryptValue.find(':')
        bIV = cryptValue[:pos]
        bData = cryptValue[pos + 1:len(cryptValue)]

        iv = binascii.unhexlify(bIV)
        data = binascii.unhexlify(bData)

        password = self.decrypt(data, iv, keyNum)

        return password


class ErrSecurityModule(DefaultSecurityModule):

        def setup_module(self, params):
            ret = DefaultSecurityModule.setup_module(self, params)
            self.is_ready = False
            return ret


#eof###########################################################################

