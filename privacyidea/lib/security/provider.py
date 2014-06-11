# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  LSE
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
'''
  Description:  the security provider is a dynamic hanlder for the security
                relevant tasks like

                random 
                crypt
                decrypt
                sign

  Dependencies: -

'''


import thread
import time
import logging
import traceback

from privacyidea.lib.crypto import zerome
from privacyidea.lib.error import HSMException

DEFAULT_KEY = 0
CONFIG_KEY = 1
TOKEN_KEY = 2
VALUE_KEY = 3


log = logging.getLogger(__name__)

class SecurityProvider(object):
    '''
    the Security provider is the singleton in the server who provides
    the security modules to run security relevant methods

    - read the hsm configurations
    - set up a pool of hsm modules
    - bind a hsm to one session
    - free the hsm from session after usage

    as session identifier the thread id is used
    '''
    def __init__(self, secLock):
        '''
        setup the SecurityProvider, which is called on server startup
        from the app_globals init

        :param secLock: RWLock() to support server wide locking
        :type  secLock: RWLock

        :return: -

        '''
        self.config = {}
        self.security_modules = {}
        self.activeOne = 'default'
        self.hsmpool = {}
        self.rwLock = secLock
        self.max_retry = 5

    def __createDefault__(self, config):
        ''' 
        create a backward compatible default security provider

        :param config:

        '''
        keyFile = None
        if config.has_key('privacyideaSecretFile'):
            keyFile = config.get('privacyideaSecretFile')
        self.config['default'] = {'pinHandle'   : TOKEN_KEY,
                                  'passHandle'  : CONFIG_KEY,
                                  'valueHandle' : VALUE_KEY,
                                  'defaultHandle' : DEFAULT_KEY,
                                  'crypted'     : 'FALSE',
                                  'file'        : keyFile,
                                  'module'      : 'privacyidea.lib.security.default.DefaultSecurityModule',
                                  'poolsize'    : 20,
                                  }

        self.config['err'] = {'pinHandle'   : TOKEN_KEY,
                                  'passHandle'  : CONFIG_KEY,
                                  'valueHandle' : VALUE_KEY,
                                  'defaultHandle' : DEFAULT_KEY,
                                  'crypted'     : 'FALSE',
                                  'file'        : keyFile,
                                  'module'      : 'privacyidea.lib.security.default.ErrSecurityModule',
                                  'poolsize'    : 20,
                                  }

    def load_config(self, config):
        '''
        load the security modules configuration
        '''

        try:
            ## load backward compatible defaults
            self. __createDefault__(config)

            for key in config:

                ## lookup, which is the active security module
                if key == 'privacyideaActiveSecurityModule':
                    self.activeOne = config.get(key)
                    log.debug("setting active security module: %s" % self.activeOne)

                if key.startswith('privacyideaSecurity'):
                    entry = key.replace('privacyideaSecurity.', '')
                    try:
                        (id, val) = entry.split('.')
                    except Exception as e:
                        error = ('[SecurityProvider:load_config] failed to '
                                 'identify config entry: %s ' % (unicode(key)))
                        log.error(error)
                        log.error("%s" % traceback.format_exc())
                        raise HSMException(error, id=707)

                    if self.config.has_key(id):
                        id_config = self.config.get(id)
                        id_config[val] = config.get(key)
                    else:
                        self.config[id] = {val:config.get(key) }

        except Exception as e:
            log.error("failed to identify module: %r " % e)
            error = "failed to identify module: %s " % unicode(e)
            raise HSMException(error, id=707)

        ## now create for each module a pool of hsm objects
        self.rwLock.acquire_write()
        try:
            for id in self.config:
                self.createHSMPool(id)
        finally:
            self.rwLock.release()

        return


    def loadSecurityModule(self, id=None):
        ''' 
        return the specified security module 
        
        :param id:  identifier for the security module (from the configuration)
        :type  id:  String or None
        
        :return:    None or the created object
        :rtype:     security module
        '''

        ret = None

        if id is None:
            id = self.activeOne

        log.debug("Loading module %s" % id)

        if self.config.has_key(id) == False:
            return ret

        config = self.config.get(id)
        if config.has_key('module') == False:
            return ret

        module = config.get('module')
        methods = ["encrypt", "decrypt", "random", "setup_module"]
        method = ""

        parts = module.split('.')
        className = parts[-1]
        packageName = '.'.join(parts[:-1])

        mod = __import__(packageName, globals(), locals(), [className])
        klass = getattr(mod, className)

        for method in methods:
            if hasattr(klass, method) == False:
                error = ("[loadSecurityModule] Security Module %s misses the "
                         "following interface: %s" % (unicode(module), unicode(method)))
                log.error(error)
                raise NameError(error)

        ret = klass(config)
        self.security_modules[id] = ret

        log.debug("returning %r" % ret)

        return ret


    def _getHsmPool_(self, hsm_id):
        ret = None
        if self.hsmpool.has_key(hsm_id):
            ret = self.hsmpool.get(hsm_id)
        return ret


    def setupModule(self, hsm_id, config=None):
        ''' 
        setupModule is called during runtime to define
        the config parameters like passw or connection strings
        '''
        self.rwLock.acquire_write()
        try:
            pool = self._getHsmPool_(hsm_id)
            if pool is None:
                error = ("[setupModule] failed to retieve pool "
                         "for hsm_id: %s" % (unicode(hsm_id)))
                log.error(error)
                raise HSMException(error, id=707)

            for entry in pool:
                hsm = entry.get('obj')
                hsm.setup_module(config)

            self.activeOne = hsm_id
        except Exception as e:
            error = "[setupModule] failed to load hsm : %s" % (unicode(e))
            log.error(error)
            log.error(traceback.format_exc())
            raise HSMException(error, id=707)

        finally:
            self.rwLock.release()
        return self.activeOne

    def createHSMPool(self, hsm_id=None, *args, **kw):
        '''
        setup a pool of secutity provider
        '''
        pool = None
        ## amount has to be taken from the hsm-id config
        if hsm_id == None:
            ids = self.config
        else:
            if self.config.has_key(hsm_id):
                ids = []
                ids.append(hsm_id)
            else:
                error = "[createHSMPool] failed to find hsm_id: %s" % (unicode(hsm_id))
                log.error(error)
                raise HSMException(error, id=707)

        for id in ids:
            pool = self._getHsmPool_(id)
            log.debug("already got this pool: %r" % pool)
            if pool is None:
                ## get the number of entries from the hsd (id) config
                conf = self.config.get(id)
                amount = int(conf.get('poolsize', 10))
                log.debug("creating pool for %r with size %r" % (id, amount))
                pool = []
                for i in range(0, amount):
                    error = ''
                    hsm = None
                    try:
                        hsm = self.loadSecurityModule(id)
                    except Exception as e:
                        error = u"%r" % e
                        log.error("%r" % (e))
                        log.error(traceback.format_exc())
                    pool.append({'obj': hsm , 'session': 0, 'error':error})

                self.hsmpool[id] = pool
        return pool

    def _findHSM4Session(self, pool, sessionId):
        found = None
        ## find session
        for hsm in pool:
            hsession = hsm.get('session')
            if hsession == sessionId:
                found = hsm
        return found

    def _createHSM4Session(self, pool, sessionId):
        found = None
        for hsm in pool:
            hsession = hsm.get('session')
            if unicode(hsession) == u'0':
                hsm['session'] = sessionId
                found = hsm
                break
        return found

    def _freeHSMSession(self, pool, sessionId):
        hsm = None
        for hsm in pool:
            hsession = hsm.get('session')
            if unicode(hsession) == unicode(sessionId):
                hsm['session'] = 0
                break
        return hsm

    def dropSecurityModule(self, hsm_id=None, sessionId=None):
        found = None
        if hsm_id is None:
            hsm_id = self.activeOne
        if sessionId is None:
            sessionId = unicode(thread.get_ident())

        if self.config.has_key(hsm_id) == False:
            error = ('[SecurityProvider:dropSecurityModule] no config found '
                     'for hsm with id %s ' % (unicode(hsm_id)))
            log.error(error)
            raise HSMException(error, id=707)
            return None

        ## find session
        try:
            pool = self._getHsmPool_(hsm_id)
            self.rwLock.acquire_write()
            found = self._findHSM4Session(pool, sessionId)
            if found is None:
                log.info('could not bind hsm to session %r ' % hsm_id)
            else:
                self._freeHSMSession(pool, sessionId)
        finally:
            self.rwLock.release()
        return True

    def getSecurityModule(self, hsm_id=None, sessionId=None):
        found = None
        if hsm_id is None:
            hsm_id = self.activeOne
        if sessionId is None:
            sessionId = unicode(thread.get_ident())

        if self.config.has_key(hsm_id) == False:
            error = ('[SecurityProvider:getSecurityModule] no config found for '
                     'hsm with id %s ' % (unicode(hsm_id)))
            log.error(error)
            raise HSMException(error, id=707)

        retry = True
        tries = 0
        locked = False

        while retry == True:
            try:
                pool = self._getHsmPool_(hsm_id)
                self.rwLock.acquire_write()
                locked = True
                ## find session
                found = self._findHSM4Session(pool, sessionId)
                if found is not None:
                    ## if session is ok - return
                    self.rwLock.release()
                    locked = False
                    retry = False
                    log.debug("using existing pool session %s" % found)
                    return found.get('obj')
                else:
                    ## create new entry
                    log.debug("getting new Session (%s) "
                              "from pool %s" % (sessionId, pool))
                    found = self._createHSM4Session(pool, sessionId)
                    self.rwLock.release()
                    locked = False
                    if found is None:
                        tries += 1
                        log.warning('try %d: could not bind hsm to session  - '
                                    'going to sleep for  %r' % (tries, 10 * tries))
                        time.sleep(10 * tries)

                        if tries >= self.max_retry:
                            error = ('[SecurityProvider:getSecurityModule] '
                                     'max_retry %d: could not bind hsm to '
                                     'session  - going to sleep for  %r'
                                     % tries, 10 * tries)
                            log.error(error)
                            raise Exception(error)
                        retry = True
                    else:
                        retry = False

            finally:
                if locked == True:
                    self.rwLock.release()

        return found
        #return self.loadSecurityModule(id)

def main():
    ## hook for local provider test
    sep = SecurityProvider()
    sep.load_config({})
    sep.createHSMPool('default')
    sep.setupModule('default', {'passwd' : 'test123'})

    ## runtime catch an hsm for session
    hsm = sep.getSecurityModule()

    passwo = 'password'
    encpass = hsm.encryptPassword(passwo)
    passw = hsm.decryptPassword(encpass)

    zerome(passw)

    hsm2 = sep.getSecurityModule(sessionId='session2')

    passwo = 'password'
    encpass = hsm2.encryptPassword(passwo)
    passw = hsm2.decryptPassword(encpass)

    zerome(passw)

    ## session shutdown
    sep.dropSecurityModule(sessionId='session2')
    sep.dropSecurityModule()

    return True


if __name__ == '__main__':

    main()

#eof###########################################################################

