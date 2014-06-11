# -*- coding: utf-8 -*-
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
realm handling
'''


from privacyidea.model import Realm, TokenRealm
from privacyidea.model.meta import Session

from privacyidea.lib.config import get_privacyIDEA_config
from privacyidea.lib.config import storeConfig
from privacyidea.lib.config import getFromConfig
from privacyidea.lib.log import log_with
from sqlalchemy import func

import logging
log = logging.getLogger(__name__)


@log_with(log)
def createDBRealm(realm):
    '''
        Store Realm in the DB Realm Table. 
        If the realm already exist, we do not need to store it
       
       @param realm: the realm name
       @type  realm: string
       
       @return : if realm is created(True) or already esists(False)
       @rtype  : boolean
    '''

    ret = False
    if not getRealmObject(name=realm):
        log.debug("No realm with name %s exist in database. Creating new" % realm)
        r = Realm(realm)
        r.storeRealm()
        ret = True

    return ret

@log_with(log)
def realm2Objects(realmList):
    ''' 
        convert a list of realm names to a list of realmObjects
        
        @param realmList: list of realnames
        @type  realmList: list
        
        @return: list of realmObjects
        @rtype:  list
    '''

    realmObjList = []
    if realmList is not None:
        for r in realmList:
            realmObj = getRealmObject(name=r)
            if realmObj is not None:
                log.debug("added realm %s to realmObjList" % realmObj)
                realmObjList.append(realmObj)
    return realmObjList

@log_with(log)
def getRealmObject(name=u"", id=0):
    '''
        returns the Realm Object for a given realm name. 
        If the given realm name is not found, it returns "None"
        
        @param name: realmname to be searched
        @type  name: string
        
        @TODO: search by id not implemented, yet
        @param id:   id of the realm object 
        @type  id:   integer
        
        @return : realmObject - the database object
        @rtype  : the sql db object
        
    '''

    log.debug("getting Realm object for name=%s, id=%i" % (name, id))
    realmObj = None
    name = u'' + str(name)
    if (0 == id):
        realmObjects = Session.query(Realm).filter(func.lower(Realm.name) == name.lower())
        if realmObjects.count() > 0:
            realmObj = realmObjects[0]
    return realmObj



@log_with(log)
def getRealms(aRealmName=""):
    '''

        lookup for a defined realm or all realms
    
        @note:  the realms dict is inserted into the privacyIDEA Config object 
        so that a lookup has not to reparse the whole config again
        
        @param aRealmName: a realmname - the realm, that is of interestet, if =="" all realms are returned
        @type  aRealmName: string

        @return:  a dict with realm description like 
        @rtype :  dict : {
                    u'myotherrealm': {'realmname': u'myotherrealm', 
                                    'useridresolver': ['useridresolver.PasswdIdResolver.IdResolver.myOtherRes'], 
                                    'entry': u'privacyidea.useridresolver.group.myotherrealm'}, 
                    u'mydefrealm': {'default': 'true', 
                                    'realmname': u'mydefrealm', 
                                    'useridresolver': ['useridresolver.PasswdIdResolver.IdResolver.myDefRes'], 
                                    'entry': u'privacyidea.useridresolver.group.mydefrealm'}, 
                   u'mymixrealm': {'realmname': u'mymixrealm', 
                                   'useridresolver': ['useridresolver.PasswdIdResolver.IdResolver.myOtherRes', 'useridresolver.PasswdIdResolver.IdResolver.myDefRes'], 
                                   'entry': u'privacyidea.useridresolver.group.mymixrealm'}}
        
    '''
    ret = {}

    config = get_privacyIDEA_config()

    realms = config.getRealms()
    ''' only parse once per session '''
    if realms is None:
        realms = _initalGetRealms()
        config.setRealms(realms)

    ''' check if only one realm is searched '''
    if aRealmName != "" :
        if realms.has_key(aRealmName):
            ret[aRealmName] = realms.get(aRealmName)
    else:
        ret.update(realms)
    return ret

@log_with(log)
def _initalGetRealms():
    '''
       initaly parse all config entries, and extract the realm definition

        @return : a dict with all realm definitions
        @rtype  : dict of definitions
    '''
    Realms = {}
    defRealmConf = "privacyidea.useridresolver"
    realmConf = "privacyidea.useridresolver.group."
    defaultRealmDef = "privacyidea.DefaultRealm"
    defaultRealm = None


    dc = get_privacyIDEA_config()
    for entry in dc:

        if entry.startswith(realmConf):

            #the realm might contain dots "."
            # so take all after the 3rd dot for realm
            r = {}
            realm = entry.split(".", 3)
            theRealm = realm[3].lower()
            r["realmname"] = realm[3]
            r["entry"] = entry

            ##resids          = env.config[entry]
            resids = getFromConfig(entry)
            r["useridresolver"] = resids.split(",")

            Realms[theRealm] = r

        if entry == defRealmConf:
            r = {}

            theRealm = "_default_"
            r["realmname"] = theRealm
            r["entry"] = defRealmConf

            #resids          = env.config[entry]
            resids = getFromConfig(entry)
            r["useridresolver"] = resids.split(",")

            defaultRealm = "_default_"
            Realms[theRealm] = r

        if entry == defaultRealmDef:
            defaultRealm = getFromConfig(defaultRealmDef)

    if defaultRealm is not None:
        _setDefaultRealm(Realms, defaultRealm)

    return Realms

@log_with(log)
def _setDefaultRealm(realms, defaultRealm):
    """
        internal method to set in the realm array the default attribute
        (used by the _initalGetRealms)
        
        @param realms: dict of all realm descriptions
        @type  realms: dict
        @param defaultRealm : name of the default realm
        @type  defaultRelam : string
        
        @return success or not
        @rtype  boolean
    """
    ret = False
    for k in realms:
        '''
            there could be only one default realm
            - all other defaults will be removed  
        '''
        r = realms.get(k)
        if k == defaultRealm.lower():
            r["default"] = "true"
            ret = True
        else:
            if r.has_key("default"):
                del r["default"]
    return ret


@log_with(log)
def isRealmDefined(realm):
    '''
        check, if a realm already exists or not
        
        @param realm: the realm, that should be verified
        @type  realm: string
        
        @return :found or not found
        @rtype  :boolean
    '''
    ret = False
    realms = getRealms();
    if realms.has_key(realm.lower()):
        ret = True
    return ret

@log_with(log)
def setDefaultRealm(defaultRealm):
    """
        set the defualt realm attrbute
        
        @note: verify, if the defualtRealm could be empty :""
        
        @param defaultRealm: the default realm name
        @type  defualtRealm: string
        
        @return:  success or not
        @rtype:   boolean 
    """
    ret = isRealmDefined(defaultRealm)
    if True == ret or defaultRealm == "":
        storeConfig(u"privacyidea.DefaultRealm", defaultRealm);
    return ret

@log_with(log)
def getDefaultRealm():
    """
        return the default realm 
        - lookup in the config for the DefaultRealm key
        
        @return: the realm name
        @rtype : string
    """
    defaultRealmDef = "privacyidea.DefaultRealm"
    defaultRealm = getFromConfig(defaultRealmDef, "")

    if defaultRealm is None or defaultRealm == "":
        log.warning("Serious configuration Issue: no Default Realm defined!")
        defaultRealm = ""

    return defaultRealm.lower()


@log_with(log)
def deleteRealm(realmname):
    '''
        delete the realm from the Database Table with the given name
        
        @param realmname: the to be deleted realm
        @type  realmname: string 
    
    '''
    r = getRealmObject(name=realmname)
    if r is None:
        ''' if no realm is found, we re-try the lowercase name for backward compatibility '''
        r = getRealmObject(name=realmname.lower())
    realmId = 0
    if r is not None:
        realmId = r.id

        if realmId != 0:
            log.debug("Now deleting all realations with realm_id=%i" % realmId)
            Session.query(TokenRealm).filter(TokenRealm.realm_id == realmId).delete()
        Session.delete(r)

    else:
        log.warning("There is no realm object with the name %s to be deleted." % realmname)
        return False
    # now delete all relations, i.e. remove all Tokens from this realm.

    return True

