# -*- coding: utf-8 -*-
#
#  May 08, 2014 Author: Cornelius Kölbel
#  contact:  http://www.privacyidea.org
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
from privacyidea.lib.policy import PolicyClass
from privacyidea.lib.config import get_privacyIDEA_config
from privacyidea.lib.log import log_with
from pylons import config as ini_config
import urllib, httplib2, json
import crypt
ENCODING = "utf-8"
import logging
from pylons import request, config, tmpl_context as c


log = logging.getLogger(__name__)

@log_with(log)
def _get_superuser_realms():
    '''
    return the list of realms, that contain superusers.
    '''
    superuser_realms = [ "admin" ]
    ini_su = ini_config.get("privacyideaSuperuserRealms", "")
    ini_su_list = [w.strip() for w in ini_su.split(",")]
    for r in ini_su_list:
        superuser_realms.append(r.lower())
    return superuser_realms

@log_with(log)
def check_admin_password(user, password, realm="admin"):
    '''
    Check the password of the admin user from the file defined in
    ini: privacyideaSuperuserFile
    
    :param user: the username used to login
    :param password: the password provided at login
    :return: The identity (user@realm) of the user or None
    :rtype: string
    '''
    success = None
    
    # check in the admin file
    admin_file = ini_config.get("privacyideaSuperuserFile")
    if admin_file:
        fileHandle = open(admin_file, "r")
        line = fileHandle.readline()
        while line:
            line = line.strip()
            fields = line.split(":", 7)
            if fields[0] == user:
                crypted_pass = fields[1]
                if crypt.crypt(password, crypted_pass) == crypted_pass:
                    success = "%s@%s" % (user, realm)
                    break

            line = fileHandle.readline()
        fileHandle.close()
        
    # check in LinOTP
    if not success:
        success = authenticate_privacyidea_user(user, realm, password)
                
    return success

@log_with(log)
def authenticate_privacyidea_user(user, realm, password):
    '''
    this function performs an authentication against the
    privacyidea server.
    
    :param user: Username of the user
    :type user: string
    :return: In case of success return the username
    :rtype: string 
    '''
    res = False
    success = None
    Policy = PolicyClass(request, config, c,
                             get_privacyIDEA_config())
    if Policy.check_user_authorization(user, realm, exception=False):
        '''
        We SHOULD do it this way, but unfortunately we 
        only get the complete context in a web request.
        We are missing the client and the HSM!
         
        (res, _opt) = checkUserPass(User(login=user, realm=realm), password)
        
        FIXME: THe server is asking himself... :-/
        '''
        # FIXME: we need to pass the client= to cope with client dependent policies.
        data = urllib.urlencode({'user' : user,
                                 'realm' : realm,
                                 'pass' : password})
        url = ini_config.get("privacyideaURL") + "/validate/check"
        disable_ssl = ini_config.get("privacyideaURL.disable_ssl", False)
        headers = {"Content-type": "application/x-www-form-urlencoded",
                   "Accept": "text/plain"}
        try:
            ## is httplib compiled with ssl?
            http = httplib2.Http(disable_ssl_certificate_validation=disable_ssl)
        except TypeError as exx:
            ## not so on squeeze:
            ## TypeError: __init__() got an unexpected keyword argument
            ## 'disable_ssl_certificate_validation'
            log.warning("httplib2 'disable_ssl_certificate_validation' "
                        "attribute error: %r" % exx)
            ## so we run in fallback mode
            http = httplib2.Http()
        (_resp, content) = http.request(url,
                                       method="POST",
                                       body=data,
                                       headers=headers)
        rv = json.loads(content)
        if rv.get("result"):        
            # in case of normal json output
            res = rv['result'].get('value', False)

        if res:
            success = "%s@%s" % (user, realm)

    return success

@log_with(log)
def is_admin_identity(identity, exception=True):
    '''
    Check if the repoze identity is an admin, who is allowed to
    use the /admin, /system and all management controllers
    
    This is checked by verifying the standard realmname "admin" and 
    the realms defined in privacyideaSuperuserRealms.
    
    Fixme: We need to get rid of the standard realm
    
    :param exception: If set to False the method will return a bool value otherwise it will throw an exception
    '''
    # During selftest the identity can be None!
    if identity == None:
        return False
    
    res = True
    try:
        # the identity could be a repoze identity object
        user_id = identity.get('repoze.who.userid')
        if type(user_id) == unicode:
            user_id = user_id.encode(ENCODING)
        identity = user_id.decode(ENCODING)
    except:
        pass   
        
    (user, _foo, realm) = identity.rpartition('@')
    if realm.lower() not in _get_superuser_realms():
        if exception:
            path = request.path.lower()
            log.warning("User %s@%s tried to call the admin function %s." %(user, realm, path))
            raise Exception("You are not an admin user and are not allowed to call this function!")
        else:
            res = False
    return res
