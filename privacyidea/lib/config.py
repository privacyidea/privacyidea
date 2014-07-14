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
'''
This file containes the Config object of the request.
'''



import logging
import time
import os
import copy

from pylons import tmpl_context as c
from privacyidea.config import environment as env
from privacyidea.lib.log import log_with
from privacyidea.lib.error import ConfigAdminError

from privacyidea.model import Config
from privacyidea.model.meta import Session

from privacyidea.lib.crypto import encryptPassword
from privacyidea.lib.crypto import decryptPassword

from datetime import datetime



log = logging.getLogger(__name__)

ENCODING = 'utf-8'


###############################################################################
##     public interface
###############################################################################

@log_with(log)
def init_privacyIDEA_config():
    '''
    return the privacyideaConfig class, which is integrated
    in the local thread context

    :return: thread local privacyIDEAConfig
    :rtype:  privacyIDEAConfig Class
    '''
    ret = get_privacyIDEA_config()
    return ret

@log_with(log)
def get_privacyIDEA_config():
    '''
    return the thread local dict with all entries

    :return: local config dict
    :rtype: dict
    '''

    ret = {}
    try:
        if False == hasattr(c, 'privacyideaConfig'):
            c.privacyideaConfig = privacyIDEAConfig()

        ty = type(c.privacyideaConfig).__name__
        if ty != 'privacyIDEAConfig':
            try:
                c.privacyideaConfig = privacyIDEAConfig()
            except Exception as e:
                log.error("privacyIDEA Definition Error")
                raise Exception(e)
        ret = c.privacyideaConfig

        if ret.delay == True:
            if hasattr(c, 'hsm') == True and isinstance(c.hsm, dict):
                hsm = c.hsm.get('obj')
                if hsm is not None and hsm.isReady() == True:
                    ret = privacyIDEAConfig()
                    c.privacyideaConfig = ret

    except Exception as e:
        log.debug("Bad Hack: privacyIDEAConfig called out of controller context")
        ret = privacyIDEAConfig()

        if ret.delay == True:
            if hasattr(c, 'hsm') == True and isinstance(c.hsm, dict):
                hsm = c.hsm.get('obj')
                if hsm is not None and hsm.isReady() == True:
                    ret = privacyIDEAConfig()

    return ret

###############################################################################
##     implementation class
###############################################################################
class privacyIDEAConfig(dict):
    '''
    this class should be a request singleton.

     In case of a change, it must cover the different aspects like
    - env config entry   and
    - app_globals
    and finally
    - sync this to disc


    '''
    @log_with(log)
    def __init__(self, *args, **kw):
        self.parent = super(privacyIDEAConfig, self)
        self.parent.__init__(*args, **kw)

        self.delay = False
        self.realms = None
        self.glo = getGlobalObject()
        conf = self.glo.getConfig()

        do_reload = False

        # do the bootstrap if no entry in the app_globals
        if len(conf.keys()) == 0:
            do_reload = True

        if self.glo.isConfigComplet() == False:
            do_reload = True
            self.delay = True

        if 'privacyidea.enableReplication' in conf:
            val = conf.get('privacyidea.enableReplication')
            if val.lower() == 'true':

                ## look for the timestamp when config was created
                e_conf_date = conf.get('privacyidea.Config')

                ## in case of replication, we always have to look if the
                ## config data in the database changed
                db_conf_date = _retrieveConfigDB('privacyidea.Config')

                if str(db_conf_date) != str(e_conf_date):
                    do_reload = True

        if do_reload == True:
            ## in case there is no entry in the dbconf or
            ## the config file is newer, we write the config back to the db
            entries = conf.keys()
            for entry in entries:
                del conf[entry]

            writeback = False
            ## get all conf entries from the config file
            fileconf = _getConfigFromEnv()

            ##  get all configs from the DB
            (dbconf, delay) = _retrieveAllConfigDB()
            self.glo.setConfigIncomplete(not delay)

            ## we only merge the config file once as a removed entry
            ##  might reappear otherwise
            if dbconf.has_key('privacyidea.Config') == False:
                conf.update(fileconf)
                writeback = True
            ##
            ##else:
            ##    modCFFileDatum = fileconf.get('privacyidea.Config')
            ##    dbTimeStr = dbconf.get('privacyidea.Config')
            ##    dbTimeStr = dbTimeStr.split('.')[0]
            ##    modDBFileDatum =
            ##           datetime.strptime(dbTimeStr,'%Y-%m-%d %H:%M:%S')
            ##    # if configFile timestamp is newer than last update:
            ##    #             reincorporate conf
            ##    #if modCFFileDatum > modDBFileDatum:
            ##    #    conf.update(fileconf)
            ##    #    writeback = True
            ##

            conf.update(dbconf)
            ## chck, if there is a selfTest in the DB and delete it
            if dbconf.has_key('privacyidea.selfTest'):
                _removeConfigDB('privacyidea.selfTest')
                _storeConfigDB('privacyidea.Config', datetime.now())

            ## the only thing we take from the fileconf is the selftest
            if fileconf.has_key('privacyidea.selfTest'):
                conf['privacyidea.selfTest'] = 'True'

            if writeback == True:
                for con in conf:
                    if con != 'privacyidea.selfTest':
                        _storeConfigDB(con, conf.get(con))
                _storeConfigDB('privacyidea.Config', datetime.now())

            self.glo.setConfig(conf, replace=True)

        self.parent.update(conf)
        return

    def setRealms(self, realmDict):
        self.realms = realmDict
        return

    def getRealms(self):
        return self.realms

    @log_with(log)
    def addEntry(self, key, val, typ=None, des=None):
        '''
        small wrapper, as the assignement opperator has only one value argument

        :param key: key of the dict
        :type  key: string
        :param val: any value, which is put in the dict
        :type  val: any type
        :param typ: used in the database to control if the data is encrypted
        :type  typ: None,string,password
        :param des: literal, which describes the data
        :type  des: string
        '''
        if key.startswith('privacyidea.') == False:
            key = 'privacyidea.' + key

        if type(val) in [str, unicode] and "%(here)s" in val:
            val = _expandHere(val)

        res = self.__setitem__(key, val, typ, des)
        return res

    @log_with(log)
    def __setitem__(self, key, val, typ=None, des=None):
        '''
        implemtation of the assignement operator == internal function

        :param key: key of the dict
        :type  key: string
        :param val: any value, which is put in the dict
        :type  val: any type
        :param typ: used in the database to control if the data is encrypted
        :type  typ: None,string,password
        :param des: literal, which describes the data
        :type  des: string
        '''

        if typ == 'password':

            ## in case we have a password type, we have to put
            ##- in the config only the encrypted pass and
            ##- add the config encprivacyidea.* with the clear password

            res = self.parent.__setitem__(key, encryptPassword(val))
            res = self.parent.__setitem__('enc' + key, val)
            self.glo.setConfig({key :encryptPassword(val)})
            self.glo.setConfig({'enc' + key : val})

        else:
            ## update this config and sync with global dict and db
            nVal = _expandHere(val)
            res = self.parent.__setitem__(key, nVal)
            self.glo.setConfig({key:nVal})

        _storeConfigDB(key, val, typ, des)
        _storeConfigDB('privacyidea.Config', datetime.now())
        return res

    def get(self, key, default=None):
        '''
            check for a key in the privacyidea config

            remark: the config entries all start with privacyidea.
            if a key is not found, we do a check if there is
            a privacyidea. prefix set in the key and potetialy prepend it

            :param key: search value
            :type  key: string
            :param default: default value, which is returned,
                            if the value is not found
            :type  default: any type

            :return: value or None
            :rtype:  any type
        '''
        if (self.parent.has_key(key) == False
                and key.startswith('privacyidea.') == False):
            key = 'privacyidea.' + key
        res = self.parent.get(key) or default
        return res

    def has_key(self, key):
        res = self.parent.has_key(key)
        if res == False and key.startswith('privacyidea.') == False:
            key = 'privacyidea.' + key

        res = self.parent.has_key(key)

        if res == False and key.startswith('encprivacyidea.') == False:
            key = 'encprivacyidea.' + key

        res = self.parent.has_key(key)

        return res

    @log_with(log)
    def __delitem__(self, key):
        '''
        remove an item from the config

        :param key: the name of the ocnfig entry
        :type  key: string

        :return : return the std value like the std dict does, whatever this is
        :rtype  : any value a dict update will return
        '''
        Key = key
        encKey = None
        if self.parent.has_key(key):
            Key = key
        elif self.parent.has_key('privacyidea.' + key):
            Key = 'privacyidea.' + key

        if self.parent.has_key('encprivacyidea.' + key):
            encKey = 'encprivacyidea.' + key
        elif self.parent.has_key('enc' + key):
            encKey = 'enc' + key

        res = self.parent.__delitem__(Key)
        ## sync with global dict
        self.glo.delConfig(Key)

        ## do we have an decrypted in local or global dict??
        if encKey is not None:
            res = self.parent.__delitem__(encKey)
            ## sync with global dict
            self.glo.delConfig(encKey)

        ## sync with db
        if key.startswith('privacyidea.'):
            Key = key
        else:
            Key = 'privacyidea.' + key

        _removeConfigDB(Key)
        _storeConfigDB('privacyidea.Config', datetime.now())
        return res

    @log_with(log)
    def update(self, dic):
        '''
        update the config dict with multiple items in a dict

        :param dic: dictionary of multiple items
        :type  dic: dict

        :return : return the std value like the std dict does, whatever this is
        :rtype  : any value a dict update will return
        '''
        res = self.parent.update(dic)
        ## sync the lobal dict
        self.glo.setConfig(dic)
        ## sync to disc
        for key in dic:
            if key != 'privacyidea.Config':
                _storeConfigDB(key, dic.get(key))

        _storeConfigDB('privacyidea.Config', datetime.now())
        return res


###############################################################################
##  helper class from here
###############################################################################
def getGlobalObject():
    glo = None

    try:
        if env.config.has_key('pylons.app_globals'):
            glo = env.config['pylons.app_globals']
        elif env.config.has_key('pylons.g'):
            glo = env.config['pylons.g']
    except:
        glo = None
    return glo

def _getConfigReadLock():
    glo = getGlobalObject()
    rcount = glo.setConfigReadLock()
    log.debug(" --------------------------------------- Read Lock %s" % rcount)

def _getConfigWriteLock():
    glo = getGlobalObject()
    rcount = glo.setConfigWriteLock()
    log.debug(" ------------------- ------------------ Write Lock %s" % rcount)

def _releaseConfigLock():
    glo = getGlobalObject()
    rcount = glo.releaseConfigLock()
    log.debug(" ------------------------------------ release Lock %s" % rcount)


@log_with(log)
def _expandHere(value):
    Value = unicode(value)
    if env.config.has_key("privacyidea.root"):
        root = env.config["privacyidea.root"]
        Value = Value.replace("%(here)s", root)
    return Value

@log_with(log)
def _getConfigFromEnv():
    privacyideaConfig = {}

    try:
        _getConfigReadLock()
        for entry in env.config:
            ## we check for the modification time of the config file
            if entry == '__file__':
                fname = env.config.get('__file__')
                mTime = time.localtime(os.path.getmtime(fname))
                modTime = datetime(*mTime[:6])
                privacyideaConfig['privacyidea.Config'] = modTime

            if entry.startswith("privacyidea."):
                privacyideaConfig[entry] = _expandHere(env.config[entry])
            if entry.startswith("encprivacyidea."):
                privacyideaConfig[entry] = env.config[entry]
        _releaseConfigLock()
    except Exception as e:
        log.error('Error while reading Config: %r' % e)
        _releaseConfigLock()
    return privacyideaConfig


# we insert or update the key / value the config DB
@log_with(log)
def _storeConfigDB(key, val, typ=None, desc=None):
    value = val

    if (not key.startswith("privacyidea.")):
        key = "privacyidea." + key

    confEntries = Session.query(Config).filter(Config.Key == unicode(key))
    theConf = None

    if typ is not None and typ == 'password':
        value = encryptPassword(val)
        en = decryptPassword(value)
        if (en != val):
            raise Exception("StoreConfig: Error during encoding password type!")

    ## update
    if confEntries.count() == 1:
        theConf = confEntries[0]
        theConf.Value = unicode(value)
        if (typ is not None):
            theConf.Type = unicode(typ)
        if (desc is not None):
            theConf.Description = unicode(desc)

    ## insert
    elif confEntries.count() == 0:
        theConf = Config(
                        Key=unicode(key),
                        Value=unicode(value),
                        Type=unicode(typ),
                        Description=unicode(desc)
                        )
    if theConf is not None:
        Session.add(theConf)

    return 101

@log_with(log)
def _removeConfigDB(key):
    if (not key.startswith("privacyidea.")):
        if not key.startswith('encprivacyidea.'):
            key = u"privacyidea." + key

    confEntries = Session.query(Config).filter(Config.Key == unicode(key))
    num = confEntries.count()
    if num == 1:
        theConf = confEntries[0]

        try:
            #Session.add(theConf)
            Session.delete(theConf)

        except Exception as e:
            log.error('failed')
            raise ConfigAdminError("remove Config failed for %r: %r"
                                   % (key, e), id=1133)

    return num

@log_with(log)
def _retrieveConfigDB(Key):
    ## prepend "lonotp." if required
    key = Key
    if (not key.startswith("privacyidea.")):
        if (not key.startswith("encprivacyidea.")):
            key = "privacyidea." + Key

    myVal = None
    key = u'' + key
    for theConf in Session.query(Config).filter(Config.Key == key):
        myVal = theConf.Value
        myVal = _expandHere(myVal)
    return myVal

@log_with(log)
def _retrieveAllConfigDB():

    config = {}
    delay = False
    for conf in Session.query(Config).all():
        log.debug("key %r:%r" % (conf.Key, conf.Value))
        key = conf.Key
        if (not key.startswith("privacyidea.")):
            key = "privacyidea." + conf.Key
        nVal = _expandHere(conf.Value)
        config[key] = nVal
        myTyp = conf.Type
        if myTyp is not None:
            if myTyp == 'password':
                if hasattr(c, 'hsm') == True and isinstance(c.hsm, dict):
                    hsm = c.hsm.get('obj')
                    if hsm is not None and hsm.isReady() == True:
                        config['enc' + key] = decryptPassword(conf.Value)
                else:
                    delay = True

    return (config, delay)

########### external interfaces ###############
@log_with(log)
def storeConfig(key, val, typ=None, desc=None):
    conf = get_privacyIDEA_config()
    conf.addEntry(key, val, typ, desc)
    return True

@log_with(log)
def updateConfig(confi):
    '''
    update the server config entries incl. syncing it to disc
    '''
    conf = get_privacyIDEA_config()

    ## remember all key, which should be processed
    p_keys = copy.deepcopy(confi)

    typing = False

    for entry in confi:
        typ = confi.get(entry + ".type", None)
        des = confi.get(entry + ".desc", None)
        ## check if we have a descriptive entry
        if typ is not None or des is not None:
            typing = True
            if typ is not None:
                del p_keys[entry + ".type"]
            if des is not None:
                del p_keys[entry + ".desc"]

    if typing == True:
        ## tuple dict containing the additional info
        t_dict = {}
        for entry in p_keys:
            val = confi.get(entry)
            typ = confi.get(entry + ".type", None)
            des = confi.get(entry + ".desc", None)
            t_dict[entry] = (val, typ or "string", des)

        for key in t_dict:
            (val, typ, desc) = t_dict.get(key)
            if val in [str, unicode] and "%(here)s" in val:
                val = _expandHere(val)
            conf.addEntry(key, val, typ, desc)

    else:
        conf_clean = {}
        for key, val in confi.iteritems():
            if "%(here)s" in val:
                val = _expandHere(val)
            conf_clean[key] = val

        conf.update(conf_clean)

    return True
    
@log_with(log)    
def getFromConfig(key, defVal=None):
    conf = get_privacyIDEA_config()
    value = conf.get(key, defVal)
    return value

@log_with(log)    
def removeFromConfig(key, iCase=False):
    conf = get_privacyIDEA_config()

    if iCase == False:
        if conf.has_key(key):
            del conf[key]
    else:
        ## case insensitive delete
        ##- might have multiple hits
        fConf = []
        for k in conf:
            if (k.lower() == key.lower() or
                  k.lower() == 'privacyidea.' + key.lower()):
                fConf.append(k)

        if len(fConf) > 0:
            for k in fConf:
                if conf.has_key(k) or conf.has_key('privacyidea.' + k):
                    del conf[k]

    return True


#### several config functions to follow
@log_with(log)
def setDefaultMaxFailCount(maxFailCount):
    return storeConfig(u"DefaultMaxFailCount", maxFailCount)

@log_with(log)
def setDefaultSyncWindow(syncWindowSize):
    return storeConfig(u"DefaultSyncWindow", syncWindowSize)

@log_with(log)
def setDefaultCountWindow(countWindowSize):
    return storeConfig(u"DefaultCountWindow", countWindowSize)

@log_with(log)
def setDefaultOtpLen(otpLen):
    return storeConfig(u"DefaultOtpLen", otpLen)

@log_with(log)
def setDefaultResetFailCount(resetFailCount):
    return storeConfig(u"DefaultResetFailCount", resetFailCount)


#eof###########################################################################

