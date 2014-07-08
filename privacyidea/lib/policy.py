# -*- coding: utf-8 -*-
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  Jul 07, 2014 add check_machine_policy, Cornelius Kölbel

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
base functions for all policy handling
'''

from privacyidea.lib.util import get_token_in_realm
from privacyidea.lib.util import getParam, uniquify
from privacyidea.lib.log import log_with

from privacyidea.lib.realm import getDefaultRealm
from privacyidea.lib.realm import getRealms

from privacyidea.lib.user import getUserRealms
from privacyidea.lib.user import User, getUserFromParam, getUserFromRequest
from privacyidea.lib.user import getResolversOfUser

from privacyidea.lib.error import privacyIDEAError
from privacyidea.lib.crypto import urandom
from privacyidea.weblib.util import get_client

from netaddr import IPAddress
from netaddr import IPNetwork

from gettext import gettext as _

from configobj import ConfigObj
import logging
# for loading XML file
import re
# for generating random passwords
import string


log = logging.getLogger(__name__)


optional = True
required = False



# This dictionary maps the token_types to actions in the scope gettoken,
# that define the maximum allowed otp valies in case of getotp/getmultiotp
MAP_TYPE_GETOTP_ACTION = {"dpw": "max_count_dpw",
                          "hmac": "max_count_hotp",
                          "totp": "max_count_totp"}


class PolicyException(privacyIDEAError):
    def __init__(self, description="unspecified error!", id=410):
        privacyIDEAError.__init__(self, description=description, id=id)


class AuthorizeException(privacyIDEAError):
    def __init__(self, description="unspecified error!", id=510):
        privacyIDEAError.__init__(self, description=description, id=id)


class PolicyClass(object):
    '''
    This class is used to check policies.
    
    The contstructor takes all arguments so that the policy logic in itself
    does not need to access any pylons functions.
    '''
    

    def __init__(self, request, config, templ_context, 
                 privacyIDEAConfig,
                 tokenrealms = [],
                 tokentype = None,
                 token_type_list = None):
        self.REG_POLICY_C = config.get("privacyideaPolicy.pin_c", "[a-zA-Z]")
        self.REG_POLICY_N = config.get("privacyideaPolicy.pin_n", "[0-9]")
        self.REG_POLICY_S = config.get("privacyideaPolicy.pin_s", "[.:,;-_<>+*!/()=?$§%&#~\^]")

        self.privacyIDEAconfig = privacyIDEAConfig
        self.request = request
        self.config = config
        self.c = templ_context
        self.tokenrealms = tokenrealms
        self.tokentype = tokentype
        # THe list of all token types known to the system
        self.token_type_list = token_type_list
        pass
    
    def get_c(self):
        '''
        returns the modified template context
        '''
        return self.c
    
    @classmethod
    @log_with(log)
    def create_policy_export_file(self, policy, filename):
        '''
        This function takes a policy dictionary and creates an export file from it
        '''
        TMP_DIRECTORY = "/tmp"
        filename = "%s/%s" % (TMP_DIRECTORY, filename)
        if len(policy) == 0:
            f = open(filename, "w")
            f.write('')
            f.close()
        else:
            for value in policy.values():
                for k in value.keys():
                    value[k] = value[k] or ""
    
            policy_file = ConfigObj(encoding="UTF-8")
            policy_file.filename = filename
    
            for name in policy.keys():
                policy_file[name] = policy[name]
                policy_file.write()
    
        return filename
    
    @log_with(log)
    def getPolicy(self, param, display_inactive=False):
        '''
        Function to retrieve the list of policies.
    
        attributes:
            name:   (optional) will only return the policy with the name
            user:   (optional) will only return the policies for this user
            realm:  (optional) will only return the policies of this realm
            scope:  (optional) will only return the policies within this scope
            action: (optional) will only return the policies with this action
                    The action can also be something like "otppin" and will
                    return policies containing "otppin = 2"
    
        returns:
             a dictionary with the policies. The name of the policy being the key
        '''
        Policies = {}
        # First we load ALL policies from the Config
        lConfig = self.privacyIDEAconfig
        for entry in lConfig:
            if entry.startswith("privacyidea.Policy."):
                policy = entry.split(".", 4)
                if len(policy) == 4:
                    # check if we should return this named policy
                    insert_this = True
                    if param.get('name', None) is not None:
                        # If a named policy was requested, we do not want to add
                        # the policy if the name does not match!
                        insert_this = bool(param['name'].lower()
                                           == policy[2].lower())
    
                    if insert_this:
                        name = policy[2]
                        key = policy[3]
                        value = lConfig.get(entry)
    
                        if name in Policies:
                            if key == "realm":
                                if value is not None:
                                    value = value.lower()
                            Policies[name][key] = value
                        else:
                            Policies[name] = {key: value}
    
        # Now we need to clean up policies, that are inactive
        if not display_inactive:
            pol2delete = []
            for polname, policy in Policies.items():
                pol_active = policy.get("active", "True")
                if pol_active == "False":
                    pol2delete.append(polname)
            for polname in pol2delete:
                del Policies[polname]
    
        # Now we need to clean up realms, that were not requested
        pol2delete = []
        if param.get('realm', None) is not None:
            for polname, policy in Policies.items():
                delete_it = True
                if policy.get("realm") is not None:
                    pol_realms = [p.strip()
                                  for p in policy['realm'].lower().split(',')]
                    for r in pol_realms:
                        if r == param['realm'].lower() or r == '*':
                            delete_it = False
                if delete_it:
                    pol2delete.append(polname)
            for polname in pol2delete:
                del Policies[polname]
    
        pol2delete = []
        if param.get('scope', None) is not None:
            for polname, policy in Policies.items():
                if policy['scope'].lower() != param['scope'].lower():
                    pol2delete.append(polname)
            for polname in pol2delete:
                del Policies[polname]
    
        pol2delete = []
        if param.get('action', None) is not None:
            for polname, policy in Policies.items():
                delete_it = True
                if policy.get("action") is not None:
                    pol_actions = [p.strip()
                                   for p in policy.get('action', "").
                                   lower().split(',')]
                    # so even if there is an action like otppin=XXX,
                    # it will finde the action "otppin"
                    for a in [pa.split("=")[0].strip() for pa in pol_actions]:
                        # if the action in the policy is '*' it fits all actions!
                        if a.lower() == param['action'].lower() or a == "*":
                            #So we are using policy: %s" % str(polname))
                            delete_it = False
                if delete_it:
                    pol2delete.append(polname)
            for polname in pol2delete:
                del Policies[polname]
    
        pol2delete = []
        if param.get('user', None) is not None:
            for polname, policy in Policies.items():
                pol_users = [p.strip()
                             for p in policy.get('user').lower().split(',')]
                delete_it = True
                for u in pol_users:
                    if u == param['user'].lower():
                        delete_it = False
                if delete_it:
                    pol2delete.append(polname)
            for polname in pol2delete:
                del Policies[polname]
    
        return Policies
    

    @log_with(log)
    def getPolicyActionValue(self, policies, action, max=True, String=False):
        '''
        This function retrieves the int value of an action from a list of policies
        input
            policies: list of policies as returned from config.getPolicy
                  This is a list of dictionaries
            action: an action, to be searched
            max: if True, it will return the highest value, if there are
                  multiple policies
                  if False, it will return the lowest value, if there
                  are multiple policies
            String: if True, the value is a string and not an integer
    
                pol10: {
                * action: "maxtoken = 10"
                * scope: "enrollment"
                * realm: "realm1"
                * user: ""
                * time: ""
               }
        '''
        ret = -1
        if String:
            ret = ""
        for _polname, pol in policies.items():
            for a in [p.strip() for p in pol['action'].split(',')]:
                log.debug("Investigating %s (string=%s)"
                          % (a, unicode(String)))
                split_action = [ca.strip() for ca in a.rsplit('=', 1)]
                if len(split_action) > 1:
                    (name, value) = split_action
                    log.debug("splitting <<%s>> <<%s>>"
                              % (name, unicode(value)))
                    if name == action:
                        if String:
                            ret = value
                        else:
                            if not String:
                                value = int(value)
                            if max:
                                if value > ret:
                                    ret = value
                            else:
                                if value < ret or -1 == ret:
                                    ret = value
    
        return ret

    @log_with(log)
    def get_machine_manage_policies(self, action):
        """
        Return the machine manage policies

        :return: dictionary with the polcies for this administrator

        Todo: Also take care of realms...
        """
        policies = {}
        active = False
        admin_user = getUserFromRequest(self.request)
        # Do we have machine policies at all?
        pol = self.getPolicy({'scope': 'machine'})
        if len(pol) > 0:
            active = True
            client = get_client()
            policies = self.get_client_policy(client, scope="machine",
                            action=action, user=admin_user['login'])

        return {'active': active,
                'policies': policies,
                'admin': admin_user['login']}

    @log_with(log)
    def getAdminPolicies(self, action, lowerRealms=False):
        """
        This internal function returns the admin policies (of scope=admin)
        for the currently authenticated administrativ user.__builtins__
    
        :param action: this is the action (like enable, disable, init...)
        :param lowerRealms: if set to True, the list of realms returned will
                          be lower case.
    
        :return: a dictionary with the following keys:
            active (if policies are used)
            realms (the realms, in which the admin is allowed to do this action)
            resolvers    (the resolvers in which the admin is allowed to perform
                         this action)
            admin      (the name of the authenticated admin user)
        """
        active = True
        # check if we got admin policies at all
        p_at_all = self.getPolicy({'scope': 'admin'})
        if len(p_at_all) == 0:
            log.info("No policies in scope admin found."
                     " Admin authorization will be disabled.")
            active = False
    
        # We may change this later to other authetnication schemes
        admin_user = getUserFromRequest(self.request)
        log.info("Evaluating policies for the "
                 "user: %s" % admin_user['login'])
        pol_request = {'user': admin_user['login'], 'scope': 'admin'}
        if '' != action:
            pol_request['action'] = action
        policies = self.getPolicy(pol_request)
        log.debug("Found the following "
                  "policies: %r" % policies)
        # get all the realms from the policies:
        realms = []
        for _pol, val in policies.items():
            ## the val.get('realm') could return None
            pol_realm = val.get('realm', '') or ''
            pol_realm = pol_realm.split(',')
            for r in pol_realm:
                if lowerRealms:
                    realms.append(r.strip(" ").lower())
                else:
                    realms.append(r.strip(" "))
        log.debug("Found the following realms in the "
                  "policies: %r" % realms)
        # get resolvers from realms
        resolvers = []
        all_realms = getRealms()
        for realm, realm_conf in all_realms.items():
            if realm in realms:
                for r in realm_conf['useridresolver']:
                    resolvers.append(r.strip(" "))
        log.debug("Found the following resolvers in the "
                  "policy: %r" % resolvers)
        return {'active': active,
                'realms': realms,
                'resolvers': resolvers,
                'admin': admin_user['login']}
    
    @log_with(log)
    def getAuthorization(self, scope, action):
        """
        This internal function returns the Authorization within some
        scope=license or the scope=system. for the currently authenticated
        administrativ user. This does not take into account the REALMS!
    
        arguments:
            action  - this is the action
                        scope = license
                            setlicense
                        scope = system
                            read
                            write
    
        returns:
            a dictionary with the following keys:
            active     (if policies are used)
            admin      (the name of the authenticated admin user)
            auth       (True if admin is authorized for this action)
        """
        active = True
        auth = False
        # check if we got license policies at all
        p_at_all = self.getPolicy({'scope': scope})
        if len(p_at_all) == 0:
            log.info("No policies in scope %s found. Checking "
                     "of scope %s be disabled." % (scope, scope))
            active = False
            auth = True
    
        # TODO: We may change this later to other authentication schemes
        log.debug("now getting the admin user name")
    
        admin_user = getUserFromRequest(self.request)
    
        log.debug("Evaluating policies for the user: %s"
                  % admin_user['login'])
    
        policies = self.getPolicy({'user': admin_user['login'],
                              'scope': scope,
                              'action': action})
    
        log.debug("Found the following policies: "
                  "%r" % policies)
    
        if len(policies.keys()) > 0:
            auth = True
    
        return {'active': active, 'auth': auth, 'admin': admin_user['login']}
    
    @log_with(log)
    def _checkAdminAuthorization(self, policies, serial, user, fitAllRealms=False):
        """
        This function checks if the token object defined by either "serial"
        or "user" is in the corresponding realm, where the admin has access to /
        fits to the given policy.
    
        fitAllRealms: If set to True, then the administrator must have rights
                        in all realms of the token. e.g. for deleting tokens.
    
        returns:
            True: if admin is allowed
            False: if admin is not allowed
        """
        # in case there are absolutely no policies
        if not policies['active']:
            return True
    
        # If the policy is valid for all realms
        if '*' in policies['realms']:
            return True
    
        # convert realms and resolvers to lowercase
        policies['realms'] = [x.lower() for x in policies['realms']]
        policies['resolvers'] = [x.lower() for x in policies['resolvers']]
    
        # in case we got a serial
        if serial != "" and serial is not None:
            log.debug("the token %r is contained "
                      "in the realms: %r" % (serial, self.tokenrealms))
            log.debug("the policy contains "
                      "the realms: %r" % policies['realms'])
            for r in self.tokenrealms:
                if fitAllRealms:
                    if r not in policies['realms']:
                        return False
                else:
                    if r in policies['realms']:
                        return True
    
            return fitAllRealms
    
        # in case we got a user
        if user.login != "":
            # default realm user
            if user.realm == "" and user.conf == "":
                return getDefaultRealm() in policies['realms']
            if not user.realm and not user.conf:
                return getDefaultRealm() in policies['realms']
            # we got a realm:
            if user.realm != "":
                return user.realm.lower() in policies['realms']
            if user.conf != "":
                return user.conf.lower() in policies['resolvers']
    
        # catch all
        return False
    
    @log_with(log)
    def getSelfserviceActions(self, user):
        '''
        This function returns the allowed actions in the self service portal
        for the given user
        '''
        self.c.user = user.login
        self.c.realm = user.realm
        client = get_client()
        policies = self.get_client_policy(client, scope="selfservice", realm=user.realm,
                                     user=user.login, userObj=user)
        # Now we got a dictionary of all policies within the scope selfservice for
        # this realm. as there can be more than one policy, we concatenate all
        # their actions to a list later we might want to change this
        all_actions = []
        for pol in policies:
            # remove whitespaces and split at the comma
            action_list = policies[pol].\
                get('action', '').\
                replace(' ', '').split(',')
            all_actions.extend(action_list)
        for act in all_actions:
            act.strip()
    
        # return the list with all actions
        return all_actions
    
    @log_with(log)
    def _checkTokenNum(self, user=None, realm=None):
        '''
        This internal function checks if the number of the tokens is valid...
        either for the whole license of for a certain realm...
    
        Therefor it checks the policy
            "scope = enrollment", action = "tokencount = <number>"
        '''
    
        # If there is an empty user, we need to set it to None
        if user:
            if "" == user.login:
                user = None
    
        if user is None and realm is None:
            # No user and realm given, so we check all the
            # licensed tokens
            ret = True
            return ret
    
        else:
            #allRealms = getRealms()
            Realms = []
    
            if user:
                log.debug("checking token num in realm: %s,"
                          " resolver: %s" % (user.realm, user.conf))
                # 1. alle resolver aus dem Realm holen.
                # 2. fuer jeden Resolver die tNum holen.
                # 3. die Policy holen und gegen die tNum checken.
                Realms = getUserRealms(user)
            elif realm:
                Realms = [realm]
    
            log.debug("checking token num in realm: %r" % Realms)
    
            tokenInRealms = {}
            for R in Realms:
                tIR = get_token_in_realm(R)
                tokenInRealms[R] = tIR
                log.debug("There are %i tokens in realm %r"
                          % (tIR, R))
    
            # Now we are checking the policy for every Realm! (if there are more)
            policyFound = False
            maxToken = 0
            for R in Realms:
                pol = self.getPolicy({'scope': 'enrollment', 'realm': R})
                polTNum = self.getPolicyActionValue(pol, 'tokencount')
                if polTNum > -1:
                    policyFound = True
    
                    if int(polTNum) > int(maxToken):
                        maxToken = int(polTNum)
    
                log.info("Realm: %r, max: %i, tokens in realm: "
                         " %i" % (R, int(maxToken), int(tokenInRealms[R])))
                if int(maxToken) > int(tokenInRealms[R]):
                    return True
    
            if policyFound is False:
                log.debug("there is no scope=enrollment, "
                          "action=tokencount policy for the realms %r" % Realms)
                return True
    
            log.info("No policy available for realm %r, "
                     "where enough managable tokens were defined." % Realms)
    
        return False
    
    @log_with(log)
    def _checkTokenAssigned(self, user, token_num=0):
        '''
        This internal function checks the number of assigned tokens to a user
        Therefor it checks the policy
            "scope = enrollment", action = "maxtoken = <number>"

        :param user: The user
        :type user: User object
        :param num_tokens: Number of tokens of this user
        :type num_tokens: int
        
        returns FALSE, if the user has to many tokens assigned
        returns TRUE, if more tokens may be assigned to the user
        '''
        if user is None:
            return True
        if user.login == "":
            return True
    
        Realms = getUserRealms(user)
    
        log.debug("checking the already assigned tokens for"
                  " user %s, realms %s" % (user.login, Realms))
    
        for R in Realms:
            pol = self.get_client_policy(get_client(), scope='enrollment', realm=R,
                                    user=user.login, userObj=user)
            log.debug("found policies %s" % pol)
            if len(pol) == 0:
                log.debug("there is no scope=enrollment"
                          " policy for Realm %s" % R)
                return True
    
            maxTokenAssigned = self.getPolicyActionValue(pol, "maxtoken")
    
            # If there is a policy, where the tokennumber exceeds the tokens in
            # the corresponding realm..
            log.debug("the user %r has %r tokens assigned. "
                      "The policy says a maximum of %r tokens."
                      % (user.login, token_num, maxTokenAssigned))
            if (int(maxTokenAssigned) > token_num or
                    maxTokenAssigned == -1):
                return True
    
        return False
    
    @log_with(log)
    def get_tokenlabel(self, user="", realm="", serial=""):
        '''
        This internal function returns the naming of the token as defined in policy
        scope = enrollment, action = tokenname = <string>
        The string can have the following varaibles:
            <u>: user
            <r>: realm
            <s>: token serial
    
        This function is used by the creation of googleauthenticator url
        '''
        tokenlabel = ""
        # TODO: What happens when we got no realms?
        #pol = self.getPolicy( {'scope': 'enrollment', 'realm': realm} )
        pol = self.get_client_policy(get_client(), scope="enrollment",
                                realm=realm, user=user)
        if len(pol) == 0:
            # No policy, so we use the serial number as label
            log.debug("there is no scope=enrollment policy for realm %r" % realm)
            tokenlabel = serial
    
        else:
            string_label = self.getPolicyActionValue(pol, "tokenlabel", String=True)
            if "" == string_label:
                # empty label, so we use the serial
                tokenlabel = serial
            else:
                string_label = re.sub('<u>', user, string_label)
                string_label = re.sub('<r>', realm, string_label)
                string_label = re.sub('<s>', serial, string_label)
                tokenlabel = string_label
    
        return tokenlabel
    
    @log_with(log)
    def get_autoassignment(self, user):
        '''
        this function checks the policy scope=enrollment, action=autoassignment
        This is a boolean policy.
        The function returns true, if autoassignment is defined.
        '''
        ret = False
        otplen = 6
    
        pol = self.get_client_policy(get_client(), scope='enrollment',
                                realm=user.realm, user=user.login, userObj=user)
    
        if len(pol) > 0:
            otplen = self.getPolicyActionValue(pol, "autoassignment")
            log.debug("got the otplen = %s" % str(otplen))
            if type(otplen) == int:
                ret = True
    
        return ret, otplen
    
    @log_with(log)
    def ignore_autoassignment_pin(self, user):
        '''
        This function checks the policy
            scope=enrollment, action=ignore_autoassignment_pin
        This is a boolean policy.
        The function returns true, if the password used in the autoassignment
        should not be set as token pin.
        '''
        ret = False
    
        pol = self.get_client_policy(get_client(), scope='enrollment',
                                action="ignore_autoassignment_pin",
                                realm=user.realm, user=user.login, userObj=user)
    
        if len(pol) > 0:
            ret = True
    
        return ret
    
    @log_with(log)
    def getRandomOTPPINLength(self, user):
        '''
        This internal function returns the length of the random otp pin that is
        define in policy scope = enrollment, action = otp_pin_random = 111
        '''
        Realms = getUserRealms(user)
        maxOTPPINLength = -1
    
        for R in Realms:
            pol = self.get_client_policy(get_client(), scope='enrollment', realm=R,
                                    user=user.login, userObj=user)
            if len(pol) == 0:
                log.debug("there is no scope=enrollment "
                          "policy for Realm %r" % R)
                return -1
    
            OTPPINLength = self.getPolicyActionValue(pol, "otp_pin_random")
    
            # If there is a policy, with a higher random pin length
            log.debug("found policy with "
                      "otp_pin_random = %r" % OTPPINLength)
    
            if (int(OTPPINLength) > int(maxOTPPINLength)):
                maxOTPPINLength = OTPPINLength
    
        return maxOTPPINLength
    
    @log_with(log)
    def getOTPPINEncrypt(self, serial=None, user=None, tokenrealms=None):
        '''
        This function returns, if the otppin should be stored as
        an encrpyted value
        '''
        if tokenrealms:
            self.tokenrealms = tokenrealms
        # do store as hashed value
        encrypt_pin = 0
        Realms = []
        if serial is not None:
            Realms = self.tokenrealms
        elif user:
            Realms = getUserRealms(user)
    
        log.debug("checking realms: %r" % Realms)
        for R in Realms:
            pol = self.getPolicy({'scope': 'enrollment', 'realm': R})
            log.debug("realm: %r, pol: %r" % (R, pol))
            if 1 == self.getPolicyActionValue(pol, 'otp_pin_encrypt'):
                encrypt_pin = 1
    
        return encrypt_pin
    
    @log_with(log)
    def getOTPPINPolicies(self, user, scope="selfservice"):
        '''
        This internal function returns the PIN policies for a realm.
        These policies can either be in the scope "selfservice" or "admin"
        The policy define when resettng an OTP PIN:
         - what should be the length of the otp pin
         - what should be the contents of the otp pin
           by the actions:
                otp_pin_minlength =
                otp_pin_maxlength =
                otp_pin_contents = [cns] (character, number, special character)
        :return: dictionary like {contents: "cns", min: 7, max: 10}
        '''
        Realms = getUserRealms(user)
        ret = {'min':-1, 'max':-1, 'contents': ""}
    
        log.debug("searching for OTP PIN policies in "
                  "scope=%r policies." % scope)
        for R in Realms:
            pol = self.get_client_policy(get_client(), scope=scope, realm=R,
                                    user=user.login, userObj=user)
            if len(pol) == 0:
                log.debug("there is no "
                          "scope=%r policy for Realm %r" % (scope, R))
                return ret
            n_max = self.getPolicyActionValue(pol, "otp_pin_maxlength")
            n_min = self.getPolicyActionValue(pol, "otp_pin_minlength", max=False)
            n_contents = self.getPolicyActionValue(pol, "otp_pin_contents", String=True)
    
            # find the maximum length
            log.debug("find the maximum length for OTP PINs.")
            if (int(n_max) > ret['max']):
                ret['max'] = n_max
    
            # find the minimum length
            log.debug("find the minimum length for OTP_PINs")
            if (not n_min == -1):
                if (ret['min'] == -1):
                    ret['min'] = n_min
                elif (n_min < ret['min']):
                    ret['min'] = n_min
    
            # find all contents
            log.debug("find the allowed contents for OTP PINs")
            for k in n_contents:
                if k not in ret['contents']:
                    ret['contents'] += k
    
        return ret
    
    @log_with(log)
    def checkOTPPINPolicy(self, pin, user):
        '''
        This function checks the given PIN (OTP PIN) against the policy
        returned by the function
    
        getOTPPINPolicy
    
        It returns a dictionary:
            {'success': True/False,
              'error': errortext}
    
        At the moment this works for the selfservice portal
        '''
        pol = self.getOTPPINPolicies(user)
        log.debug("checking for otp_pin_minlength")
        if pol['min'] != -1:
            if pol['min'] > len(pin):
                return {'success': False,
                        'error': 'The provided PIN is too short. It should be at '
                                 'least %i characters.' % pol['min']}
    
        log.debug("checking for otp_pin_maxlength")
        if pol['max'] != -1:
            if pol['max'] < len(pin):
                return {'success': False,
                        'error': ('The provided PIN is too long. It should not '
                                  'be longer than %i characters.' % pol['max'])}
    
        log.debug("checking for otp_pin_contents")
        if pol['contents']:
            policy_c = "c" in pol['contents']
            policy_n = "n" in pol['contents']
            policy_s = "s" in pol['contents']
            policy_o = "o" in pol['contents']
    
            contains_c = False
            contains_n = False
            contains_s = False
            contains_other = False
    
            for c in pin:
                if re.search(self.REG_POLICY_C, c):
                    contains_c = True
                elif re.search(self.REG_POLICY_N, c):
                    contains_n = True
                elif re.search(self.REG_POLICY_S, c):
                    contains_s = True
                else:
                    contains_other = True
    
            if "+" == pol['contents'][0]:
                log.debug("checking for an additive character "
                          "group: %s" % pol['contents'])
                if ((not (
                        (policy_c and contains_c) or
                        (policy_s and contains_s) or
                        (policy_o and contains_other) or
                        (policy_n and contains_n)
                        )
                     ) or (
                        (not policy_c and contains_c) or
                        (not policy_s and contains_s) or
                        (not policy_n and contains_n) or
                        (not policy_o and contains_other))):
                    return {'success': False,
                            'error': "The provided PIN does not contain characters"
                                     " of the group or it does contains "
                                     "characters that are not in the group %s"
                                     % pol['contents']}
            else:
                log.debug("normal check: %s" % pol['contents'])
                if (policy_c and not contains_c):
                    return {'success': False,
                            'error': 'The provided PIN does not contain any ' +
                                     'letters. Check policy otp_pin_contents.'}
                if (policy_n and not contains_n):
                    return {'success': False,
                            'error': 'The provided PIN does not contain any ' +
                                     'numbers. Check policy otp_pin_contents.'}
                if (policy_s and not contains_s):
                    return {'success': False,
                            'error': 'The provided PIN does not contain any '
                                     'special characters. It should contain '
                                     'some of these characters like '
                                     '.: ,;-_<>+*~!/()=?$. Check policy '
                                     'otp_pin_contents.'}
                if (policy_o and not contains_other):
                    return {'success': False,
                            'error': 'The provided PIN does not contain any '
                                     'other characters. It should contain some of'
                                     ' these characters that are not contained '
                                     'in letters, digits and the defined special '
                                     'characters. Check policy otp_pin_contents.'}
                # Additionally: in case of -cn the PIN must not contain "s" or "o"
                if '-' == pol['contents'][0]:
                    if (not policy_c and contains_c):
                        return {'success': False,
                                'error': "The PIN contains letters, although it "
                                         "should not! (%s)" % pol['contents']}
                    if (not policy_n and contains_n):
                        return {'success':  False,
                                'error': "The PIN contains digits, although it "
                                         "should not! (%s)" % pol['contents']}
                    if (not policy_s and contains_s):
                        return {'success': False,
                                'error': "The PIN contains special characters, "
                                         "although it should not! "
                                         "(%s)" % pol['contents']}
                    if (not policy_o and contains_other):
                        return {'success': False,
                                'error': "The PIN contains other characters, "
                                         "although it should not! "
                                         "(%s)" % pol['contents']}
    
        return {'success': True,
                'error': ''}
    
    @log_with(log)
    def getRandomPin(self, randomPINLength):
        newpin = ""
        log.debug("creating a random otp pin of "
                  "length %r" % randomPINLength)
        chars = string.letters + string.digits
        for _i in range(randomPINLength):
            newpin = newpin + urandom.choice(chars)
    
        return newpin
    
    @log_with(log)
    def is_auth_selfservice_otp(self, username, realm):
        '''
        check the policy scope:selfservice, action:auth=otp
        
        :param username: The username who logs in to selfservice 
        :param realm: The realm of the user, who logs in to selfserivce
        :return: If the user should authenticate with OTP
        :rtype: boolean
        '''
        ret = False
        client = get_client()
        pol = self.get_client_policy(client, scope="selfservice",
                                realm=realm,
                                user=username)
        action_value = self.getPolicyActionValue(pol, "auth", String=True).lower()
        if action_value == "otp":
            ret = True
        return ret
    
    ##### Pre and Post checks
    @log_with(log)
    def checkPolicyPre(self, controller, method, param=None, authUser=None, user=None,
                       options=None,
                       tokenrealms=None,
                       tokentype=None):
        '''
        This function will check for all policy definition for a certain
        controller/method It is run directly before doing the action in the
        controller. I will raise an exception, if it fails.
    
        :param param: This is a dictionary with the necessary parameters.
        :type param: dict
        :param options: additional options 
        :type options: dict
        
        :return: dictionary with the necessary results. These depend on
                 the controller.
        '''
        if options == None:
            options = {}
        if param == None:
            param = {}
        ret = {}
        if tokenrealms:
            self.tokenrealms = tokenrealms
        if tokentype:
            self.tokentype = tokentype

        if controller == 'machine':
            pol = self.get_machine_manage_policies(method)
            if pol.get("active"):
                if len(pol.get("policies")) == 0:
                    log.error("The admin %r does not have"
                              "the right to %r" % (pol['admin'], method))
                    raise PolicyException(_("You do not have the right to manage machines with:"
                                            "%r" % method))

        elif 'admin' == controller:
    
            serial = getParam(param, "serial", optional)
            if user is None:
                user = getUserFromParam(param, optional)
            realm = getParam(param, "realm", optional)
            if realm is None or len(realm) == 0:
                realm = getDefaultRealm()
    
            if 'show' == method:
    
                # get the realms for this administrator
                policies = self.getAdminPolicies('')
                log.debug("The admin >%s< may manage the "
                          "following realms: %s" % (policies['admin'],
                                                    policies['realms']))
                if policies['active'] and 0 == len(policies['realms']):
                    log.error("The admin >%s< has no rights in "
                              "any realms!" % policies['admin'])
                    raise PolicyException(_("You do not have any rights in any realm! "
                                            "Check the policies."))
                return {'realms': policies['realms'], 'admin': policies['admin']}
    
            elif 'remove' == method:
                policies = self.getAdminPolicies("remove")
                # FIXME: A token that belongs to multiple realms should not be
                #        deleted. Should it? If an admin has the right on this
                #        token, he might be allowed to delete it,
                #        even if the token is in other realms.
                # We could use fitAllRealms=True
                if (policies['active'] and not
                        self._checkAdminAuthorization(policies, serial, user)):
                    log.warning("the admin >%s< is not allowed to remove "
                                "token %s for user %s@%s"
                                % (policies['admin'], serial,
                                   user.login, user.realm))
                    raise PolicyException(_("You do not have the administrative "
                                          "right to remove token %s. Check the "
                                          "policies.") % serial)
    
            elif 'enable' == method:
                policies = self.getAdminPolicies("enable")
                if (policies['active'] and not
                        self._checkAdminAuthorization(policies, serial, user)):
                    log.warning("the admin >%s< is not allowed to enable "
                                "token %s for user %s@%s"
                                % (policies['admin'], serial,
                                   user.login, user.realm))
                    raise PolicyException(_("You do not have the administrative "
                                          "right to enable token %s. Check the "
                                          "policies.") % serial)
    
                # We need to check which realm the token will be in.
                realmList = self.tokenrealms
                for r in realmList:
                    if not self._checkTokenNum(realm=r):
                        log.warning("the maximum tokens for the realm "
                                    "%s is exceeded." % r)
                        raise PolicyException(_("You may not enable any more tokens "
                                              "in realm %s. Check the policy "
                                              "'tokencount'") % r)
    
            elif 'disable' == method:
                policies = self.getAdminPolicies("disable")
                if (policies['active'] and not
                        self._checkAdminAuthorization(policies, serial, user)):
                    log.warning("the admin >%s< is not allowed to "
                                "disable token %s for user %s@%s"
                                % (policies['admin'], serial,
                                   user.login, user.realm))
                    raise PolicyException(_("You do not have the administrative "
                                          "right to disable token %s. Check the "
                                          "policies.") % serial)
    
            elif 'copytokenpin' == method:
                policies = self.getAdminPolicies("copytokenpin")
                if (policies['active'] and not
                        self._checkAdminAuthorization(policies, serial, user)):
                    log.warning("the admin >%s< is not allowed to "
                                "copy token pin of token %s for user %s@%s"
                                % (policies['admin'], serial,
                                   user.login, user.realm))
                    raise PolicyException(_("You do not have the administrative "
                                          "right to copy pin of token %s. Check "
                                          "the policies.") % serial)
    
            elif 'copytokenuser' == method:
                policies = self.getAdminPolicies("copytokenuser")
                if (policies['active'] and not
                        self._checkAdminAuthorization(policies, serial, user)):
                    log.warning("the admin >%s< is not allowed to "
                                "copy token user of token %s for user %s@%s"
                                % (policies['admin'], serial,
                                   user.login, user.realm))
                    raise PolicyException(_("You do not have the administrative "
                                          "right to copy user of token %s. Check "
                                          "the policies.") % serial)
    
            elif 'losttoken' == method:
                policies = self.getAdminPolicies("losttoken")
                if (policies['active'] and not
                        self._checkAdminAuthorization(policies, serial, user)):
                    log.warning("the admin >%s< is not allowed to run "
                                "the losttoken workflow for token %s for "
                                "user %s@%s" % (policies['admin'], serial,
                                                user.login, user.realm))
                    raise PolicyException(_("You do not have the administrative "
                                          "right to run the losttoken workflow "
                                          "for token %s. Check the "
                                          "policies.") % serial)
    
            elif 'getotp' == method:
                policies = self.getAdminPolicies("getotp")
                if (policies['active'] and not
                        self._checkAdminAuthorization(policies, serial, user)):
                    log.warning("the admin >%s< is not allowed to run "
                                "the getotp workflow for token %s for user %s@%s"
                                % (policies['admin'], serial, user.login,
                                   user.realm))
                    raise PolicyException(_("You do not have the administrative "
                                          "right to run the getotp workflow for "
                                          "token %s. Check the policies.") % serial)
    
            elif 'getserial' == method:
                policies = self.getAdminPolicies("getserial")
                # check if we want to search the token in certain realms
                if realm is not None:
                    dummy_user = User('dummy', realm, None)
                else:
                    dummy_user = User('', '', '')
                    # We need to allow this, as no realm was passed at all.
                    policies['realms'] = '*'
                if (policies['active'] and not
                        self._checkAdminAuthorization(policies, None, dummy_user)):
                    log.warning("the admin >%s< is not allowed to get "
                                "serials for user %s@%s"
                                % (policies['admin'], user.login, user.realm))
                    raise PolicyException(_("You do not have the administrative "
                                          "right to get serials by OTPs in "
                                          "this realm!"))
    
            elif 'init' == method:
                ttype = getParam(param, "type", optional)
                # possible actions are:
                # initSPASS, 	initHMAC,	initETNG, initSMS, 	initMOTP
                policies = {}
                # default: we got HMAC / ETNG

                if ((not ttype) or
                        (ttype and (ttype.lower() == "hmac"))):
                    p1 = self.getAdminPolicies("initHMAC")
                    p2 = self.getAdminPolicies("initETNG")
                    policies = {'active': p1['active'],
                                'admin': p1['admin'],
                                'realms': p1['realms'] + p2['realms'],
                                'resolvers': p1['resolvers'] + p2['resolvers']}
                else:
                    # See if there is a policy like initSPASS or ....
                    token_type_found = False
    
                    for tt in self.token_type_list:
                        if tt.lower() == ttype.lower():
                            policies = self.getAdminPolicies("init%s" % tt.upper())
                            token_type_found = True
                            break
    
                    if not token_type_found:
                        policies = {}
                        log.error("Unknown token type: %s" % ttype)
                        raise Exception("The tokentype '%s' could not be "
                                        "found." % ttype)
    
                """
                We need to assure, that an admin does not enroll a token into a
                realm were he has no ACCESS! : -(
                The admin may not enroll a token with a serial, that is already
                assigned to a user outside of his realm
                """
                # if a user is given, we need to check the realm of this user
                log.debug("checking realm of the user")
                if (policies['active'] and
                    (user.login != "" and not
                     self._checkAdminAuthorization(policies, "", user))):
                    log.warning("the admin >%s< is not allowed to enroll "
                                "token %s of type %s to user %s@%s"
                                % (policies['admin'], serial, ttype,
                                   user.login, user.realm))
    
                    raise PolicyException(_("You do not have the administrative "
                                          "right to init token %s of type %s to "
                                          "user %s@%s. Check the policies.")
                                          % (serial, ttype, user.login,
                                             user.realm))
    
                # no right to enroll token in any realm
                log.debug("checking enroll token at all")
                if policies['active'] and len(policies['realms']) == 0:
                    log.warning("the admin >%s< is not allowed to enroll "
                                "a token at all."
                                % (policies['admin']))
                    raise PolicyException(_("You do not have the administrative "
                                          "right to enroll tokens. Check the "
                                          "policies."))
    
                # the token is assigned to a user, not in the realm of the admin!
                # we only need to check this, if the token already exists. If
                # this is a new token, we do not need to check this.
                log.debug("checking for token existens")
                if policies['active']:
                    if not self._checkAdminAuthorization(policies, serial, ""):
                        log.warning("the admin >%s< is not allowed to "
                                    "enroll token %s of type %s."
                                    % (policies['admin'], serial, ttype))
                        raise PolicyException(_("You do not have the administrative "
                                              "right to init token %s of type %s.")
                                              % (serial, ttype))
    
                # if a policy restricts the tokennumber for a realm
                log.debug("checking tokens in realms "
                          "%s" % policies['realms'])
                for R in policies['realms']:
                    if not self._checkTokenNum(realm=R):
                        log.warning("the admin >%s< is not allowed to "
                                    "enroll any more tokens for the realm %s"
                                    % (policies['admin'], R))
                        raise PolicyException(_("The maximum allowed number of "
                                              "tokens for the realm %s was "
                                              "reached. You can not init any more "
                                              "tokens. Check the policies "
                                              "scope=enrollment, "
                                              "action=tokencount.") % R)
    
                log.debug("checking tokens in realm for "
                          "user %s" % user)
                if not self._checkTokenNum(user=user):
                    log.warning("the admin >%s< is not allowed to enroll "
                                "any more tokens for the realm %s"
                                % (policies['admin'], user.realm))
                    raise PolicyException(_("The maximum allowed number of tokens "
                                          "for the realm %s was reached. You can "
                                          "not init any more tokens. Check the "
                                          "policies scope=enrollment, "
                                          "action=tokencount.") % user.realm)
    
                log.debug("checking tokens of user")
                # if a policy restricts the tokennumber for the user in a realm
                if not self._checkTokenAssigned(user, options.get("token_num", 0)):
                    log.warning("the maximum number of allowed tokens per "
                                "user is exceeded. Check the policies")
                    raise PolicyException(_("the maximum number of allowed tokens "
                                          "per user is exceeded. Check the "
                                          "policies scope=enrollment, "
                                          "action=maxtoken"))
                # ==== End of policy check 'init' ======
                ret['realms'] = policies['realms']
    
            elif 'unassign' == method:
                policies = self.getAdminPolicies("unassign")
                if (policies['active'] and not
                        self._checkAdminAuthorization(policies, serial, user)):
                    log.warning("the admin >%s< is not allowed to "
                                "unassign token %s for user %s@%s"
                                % (policies['admin'], serial, user.login,
                                   user.realm))
                    raise PolicyException(_("You do not have the administrative "
                                          "right to unassign token %s. Check the "
                                          "policies.") % serial)
    
            elif 'assign' == method:
                policies = self.getAdminPolicies("assign")
    
                # the token is assigned to a user, not in the realm of the admin!
                if (policies['active'] and not
                        self._checkAdminAuthorization(policies, serial, "")):
                    log.warning("the admin >%s< is not allowed to assign "
                                "token %s. " % (policies['admin'], serial))
                    raise PolicyException(_("You do not have the administrative "
                                          "right to assign token %s. "
                                          "Check the policies.") % (serial))
    
                # The user, the token should be assigned to,
                # is not in the admins realm
                if (policies['active'] and not
                        self._checkAdminAuthorization(policies, "", user)):
                    log.warning("the admin >%s< is not allowed to assign "
                                "token %s for user %s@%s" % (policies['admin'],
                                                             serial, user.login,
                                                             user.realm))
                    raise PolicyException(_("You do not have the administrative "
                                          "right to assign token %s. Check the "
                                          "policies.") % serial)
    
                # if a policy restricts the tokennumber for the realm/user
                if not self._checkTokenNum(user):
                    log.warning("the admin >%s< is not allowed to assign "
                                "any more tokens for the realm %s(%s)"
                                % (policies['admin'], user.realm, user.conf))
                    raise PolicyException(_("The maximum allowed number of tokens "
                                          "for the realm %s (%s) was reached. You "
                                          "can not assign any more tokens. Check "
                                          "the policies.")
                                          % (user.realm, user.conf))
    
                # check the number of assigned tokens
                if not self._checkTokenAssigned(user, options.get("token_num",0)):
                    log.warning("the maximum number of allowed tokens "
                                "is exceeded. Check the policies")
                    raise PolicyException(_("The maximum number of allowed tokens "
                                          "is exceeded. Check the policies"))
    
            elif 'setPin' == method:
    
                if "userpin" in param:
                    getParam(param, "userpin", required)
                    # check admin authorization
                    policies1 = self.getAdminPolicies("setSCPIN")
                    policies2 = self.getAdminPolicies("setMOTPPIN")
                    if ((policies1['active'] and not
                            (self._checkAdminAuthorization(policies1, serial,
                                                     User("", "", ""))))
                            or (policies2['active'] and not
                            (self._checkAdminAuthorization(policies2, serial,
                                                     User("", "", ""))))):
                        log.warning("the admin >%s< is not allowed to "
                                    "set MOTP PIN/SC UserPIN for token %s."
                                    % (policies['admin'], serial))
                        raise PolicyException(_("You do not have the administrative "
                                              "right to set MOTP PIN/ SC UserPIN "
                                              "for token %s. Check the policies.")
                                              % serial)
    
                if "sopin" in param:
                    getParam(param, "sopin", required)
                    # check admin authorization
                    policies = self.getAdminPolicies("setSCPIN")
                    if (policies['active'] and not
                            self._checkAdminAuthorization(policies, serial,
                                                    User("", "", ""))):
                        log.warning("the admin >%s< is not allowed to "
                                    "setPIN for token %s."
                                    % (policies['admin'], serial))
                        raise PolicyException(_("You do not have the administrative "
                                              "right to set Smartcard PIN for "
                                              "token %s. Check the policies.")
                                              % serial)
    
            elif 'set' == method:
    
                if "pin" in param:
                    policies = self.getAdminPolicies("setOTPPIN")
                    if (policies['active'] and not
                            self._checkAdminAuthorization(policies, serial, user)):
                        log.warning("the admin >%s< is not allowed to set "
                                    "OTP PIN for token %s for user %s@%s"
                                    % (policies['admin'], serial, user.login,
                                       user.realm))
                        raise PolicyException(_("You do not have the administrative "
                                              "right to set OTP PIN for token %s. "
                                              "Check the policies.") % serial)
    
                if ("MaxFailCount".lower() in param or
                        "SyncWindow".lower() in param or
                        "CounterWindow".lower() in param or
                        "OtpLen".lower() in param):
                    policies = self.getAdminPolicies("set")
                    if (policies['active'] and not
                            self._checkAdminAuthorization(policies, serial, user)):
                        log.warning("the admin >%s< is not allowed to set "
                                    "token properites for %s for user %s@%s"
                                    % (policies['admin'], serial,
                                       user.login, user.realm))
                        raise PolicyException(_("You do not have the administrative "
                                              "right to set token properties for "
                                              "%s. Check the policies.") % serial)
    
            elif 'resync' == method:
    
                policies = self.getAdminPolicies("resync")
                if (policies['active'] and not
                        self._checkAdminAuthorization(policies, serial, user)):
                    log.warning("the admin >%s< is not allowed to resync "
                                "token %s for user %s@%s"
                                % (policies['admin'], serial,
                                   user.login, user.realm))
                    raise PolicyException(_("You do not have the administrative "
                                          "right to resync token %s. Check the "
                                          "policies.") % serial)
    
            elif 'userlist' == method:
                policies = self.getAdminPolicies("userlist")
                # check if the admin may view the users in this realm
                if (policies['active'] and
                        not self._checkAdminAuthorization(policies, "", user)):
                    log.warning("the admin >%s< is not allowed to list"
                                " users in realm %s(%s)!"
                                % (policies['admin'], user.realm, user.conf))
                    raise PolicyException(_("You do not have the administrative"
                                          " right to list users in realm %s(%s).")
                                          % (user.realm, user.conf))
    
            elif 'checkstatus' == method:
                policies = self.getAdminPolicies("checkstatus")
                # check if the admin may view the users in this realm
                if (policies['active'] and not
                        self._checkAdminAuthorization(policies, "", user)):
                    log.warning("the admin >%s< is not allowed to "
                                "show status of token challenges in realm %s(%s)!"
                                % (policies['admin'], user.realm, user.conf))
                    raise PolicyException(_("You do not have the administrative "
                                          "right to show status of token "
                                          "challenges in realm "
                                          "%s(%s).") % (user.realm, user.conf))
    
            elif 'tokenrealm' == method:
                log.debug("entering method %s" % method)
                # The admin needs to have the right "manageToken" for all realms,
                # the token is currently in and all realm the Token should go into.
                policies = self.getAdminPolicies("manageToken")
    
                realms = getParam(param, "realms", required)
                # List of the new realms
                realmNewList = realms.split(',')
                # List of existing realms
                realmExistList = self.tokenrealms
    
                for r in realmExistList:
                    if (policies['active'] and not
                        self._checkAdminAuthorization(policies, None,
                                                User("dummy", r, None))):
                        log.warning("the admin >%s< is not allowed "
                                    "to manage tokens in realm %s"
                                    % (policies['admin'], r))
                        raise PolicyException(_("You do not have the administrative "
                                              "right to remove tokens from realm "
                                              "%s. Check the policies.") % r)
    
                for r in realmNewList:
                    if (policies['active'] and not
                        self._checkAdminAuthorization(policies, None,
                                                User("dummy", r, None))):
                        log.warning("the admin >%s< is not allowed "
                                    "to manage tokens in realm %s"
                                    % (policies['admin'], r))
                        raise PolicyException(_("You do not have the administrative "
                                              "right to add tokens to realm %s. "
                                              "Check the policies.") % r)
    
                    if not self._checkTokenNum(realm=r):
                        log.warning("the maximum tokens for the "
                                    "realm %s is exceeded." % r)
                        raise PolicyException(_("You may not put any more tokens in "
                                              "realm %s. Check the policy "
                                              "'tokencount'") % r)
    
            elif 'reset' == method:
    
                policies = self.getAdminPolicies("reset")
                if (policies['active'] and not
                        self._checkAdminAuthorization(policies, serial, user)):
                    log.warning("the admin >%s< is not allowed to reset "
                                "token %s for user %s@%s" % (policies['admin'],
                                                             serial, user.login,
                                                             user.realm))
                    raise PolicyException(_("You do not have the administrative "
                                          "right to reset token %s. Check the "
                                          "policies.") % serial)
    
            elif 'import' == method:
                policies = self.getAdminPolicies("import")
                # no right to import token in any realm
                log.debug("checking import token at all")
                if policies['active'] and len(policies['realms']) == 0:
                    log.warning("the admin >%s< is not allowed "
                                "to import a token at all."
                                % (policies['admin']))
    
                    raise PolicyException(_("You do not have the administrative "
                                          "right to import tokens. Check the "
                                          "policies."))
                ret['realms'] = policies['realms']
    
            elif 'loadtokens' == method:
                tokenrealm = param.get('tokenrealm')
                policies = self.getAdminPolicies("import")
                if policies['active'] and tokenrealm not in policies['realms']:
                    log.warning("the admin >%s< is not allowed to "
                                "import token files to realm %s: %s"
                                % (policies['admin'], tokenrealm, policies))
                    raise PolicyException(_("You do not have the administrative "
                                          "right to import token files to realm %s"
                                          ". Check the policies.") % tokenrealm)
    
                if not self._checkTokenNum(realm=tokenrealm):
                    log.warning("the maximum tokens for the realm "
                                "%s is exceeded." % tokenrealm)
                    raise PolicyException(_("The maximum number of allowed tokens "
                                          "in realm %s is exceeded. Check policy "
                                          "tokencount!") % tokenrealm)
    
            else:
                # unknown method
                log.error("an unknown method "
                          "<<%s>> was passed." % method)
                raise PolicyException(_("Failed to run checkPolicyPre. "
                                      "Unknown method: %s") % method)
    
        elif 'gettoken' == controller:
            if 'max_count' == method[0: len('max_count')]:
                ret = 0
                serial = getParam(param, "serial", optional)
                pol_action = MAP_TYPE_GETOTP_ACTION.get(self.tokentype.lower(), "")
                admin_user = getUserFromRequest(self.request)
                if pol_action == "":
                    raise PolicyException(_("There is no policy gettoken/"
                                          "max_count definable for the "
                                          "tokentype %r") % self.tokentype)
    
                policies = {}
                for realm in self.tokenrealms:
                    pol = self.getPolicy({'scope': 'gettoken', 'realm': realm,
                                     'user': admin_user['login']})
                    log.error("got a policy: %r" % policies)
    
                    policies.update(pol)
    
                value = self.getPolicyActionValue(policies, pol_action)
                log.debug("got all policies: %r: %r" % (policies, value))
                ret = value
      
        elif 'audit' == controller:
            if 'view' == method:
                auth = self.getAuthorization("audit", "view")
                if auth['active'] and not auth['auth']:
                    log.warning("the admin >%r< is not allowed to "
                                "view the audit trail" % auth['admin'])
    
                    ret = _("You do not have the administrative right to view the "
                           "audit trail. You are missing a policy "
                           "scope=audit, action=view")
                    raise PolicyException(ret)
            else:
                log.error("an unknown method was passed in audit: %s" % method)
                raise PolicyException(_("Failed to run checkPolicyPre. Unknown "
                                      "method: %s") % method)
    
        elif 'manage' == controller:
            log.debug("entering controller %s" % controller)
    
        elif 'selfservice' == controller:
            log.debug("entering controller %s" % controller)
    
            if 'max_count' == method[0: len('max_count')]:
                ret = 0
                serial = getParam(param, "serial", optional)
                urealm = authUser.realm
                pol_action = MAP_TYPE_GETOTP_ACTION.get(self.tokentype.lower(), "")
                if pol_action == "":
                    raise PolicyException(_("There is no policy selfservice/"
                                          "max_count definable for the token "
                                          "type %s.") % self.tokentype)
    
                policies = self.get_client_policy(get_client(), scope='selfservice',
                                             realm=urealm, user=authUser.login,
                                             userObj=authUser)
                log.debug("seflservice:max_count: got a policy: "
                          " %r" % policies)
                if policies == {}:
                    raise PolicyException(_("There is no policy selfservice/"
                                          "max_count defined for the tokentype "
                                          "%s in realm %s.") % (self.tokentype, urealm))
    
                value = self.getPolicyActionValue(policies, pol_action)
                log.debug("seflservice:max_count: got all policies: %r: %r" % (policies, value))
                ret = value
    
            elif 'usersetpin' == method:
    
                if not 'setOTPPIN' in self.getSelfserviceActions(authUser):
                    log.warning("usersetpin: user %s@%s is not allowed to call "
                                "this function!" % (authUser.login,
                                                    authUser.realm))
                    raise PolicyException(_('The policy settings do not allow you '
                                          'to issue this request!'))
    
            elif 'userreset' == method:
    
                if not 'reset' in self.getSelfserviceActions(authUser):
                    log.warning("userreset: user %s@%s is not allowed to call "
                                "this function!" % (authUser.login,
                                                    authUser.realm))
                    raise PolicyException(_('The policy settings do not allow you '
                                          'to issue this request!'))
    
            elif 'userresync' == method:
    
                if not 'resync' in self.getSelfserviceActions(authUser):
                    log.warning("userresync: user %s@%s is not allowed to call "
                                "this function!" % (authUser.login,
                                                    authUser.realm))
                    raise PolicyException(_('The policy settings do not allow you '
                                          'to issue this request!'))
    
            elif 'usersetmpin' == method:
    
                if not 'setMOTPPIN' in self.getSelfserviceActions(authUser):
                    log.warning("usersetmpin: user %r@%r is not allowed to call "
                                "this function!" % (authUser.login,
                                                    authUser.realm))
                    raise PolicyException(_('The policy settings do not allow you '
                                          'to issue this request!'))
    
            elif 'useractivateocratoken' == method:
                user_selfservice_actions = self.getSelfserviceActions(authUser)
                typ = param.get('type').lower()
                if (typ == 'ocra'
                        and 'activateQR' not in user_selfservice_actions):
                    log.warning("activateQR: user %r@%r is not allowed to call "
                                "this function!" % (authUser.login,
                                                    authUser.realm))
                    raise PolicyException(_('The policy settings do not allow you '
                                          'to issue this request!'))
    
            elif 'useractivateocra2token' == method:
                user_selfservice_actions = self.getSelfserviceActions(authUser)
                typ = param.get('type').lower()
                if (typ == 'ocra2'
                        and 'activateQR2' not in user_selfservice_actions):
                    log.warning("[activateQR2 user %r@%r is not allowed to call "
                                "this function!" % (authUser.login,
                                                    authUser.realm))
                    raise PolicyException(_('The policy settings do not allow you '
                                          'to issue this request!'))
    
            elif 'userassign' == method:
    
                if not 'assign' in self.getSelfserviceActions(authUser):
                    log.warning("userassign: user %r@%r is not allowed to call "
                                "this function!" % (authUser.login,
                                                    authUser.realm))
                    raise PolicyException(_('The policy settings do not allow '
                                          'you to issue this request!'))
    
                # Here we check, if the tokennum exceeds the licensed tokens
                if not self._checkTokenNum():
                    log.error("The maximum licensed token number "
                              "is reached!")
                    raise PolicyException(_("You may not enroll any more tokens. "
                                          "Your maximum licensed token number "
                                          "is reached!"))
    
                if not self._checkTokenAssigned(authUser, options.get("token_num",0)):
                    log.warning("the maximum number of allowed tokens is"
                                " exceeded. Check the policies")
                    raise PolicyException(_("The maximum number of allowed tokens "
                                          "is exceeded. Check the policies"))
    
            elif 'usergetserialbyotp' == method:
    
                if not 'getserial' in self.getSelfserviceActions(authUser):
                    log.warning("usergetserialbyotp: user %s@%s is not allowed to"
                                " call this function!" % (authUser.login,
                                                          authUser.realm))
                    raise PolicyException(_('The policy settings do not allow you to'
                                          ' request a serial by OTP!'))
    
            elif 'userdisable' == method:
    
                if not 'disable' in self.getSelfserviceActions(authUser):
                    log.warning("userdisable: user %r@%r is not allowed to call "
                                "this function!"
                                % (authUser.login, authUser.realm))
                    raise PolicyException(_('The policy settings do not allow you '
                                          'to issue this request!'))
    
            elif 'userenable' == method:
    
                if not 'enable' in self.getSelfserviceActions(authUser):
                    log.warning("userenable: user %s@%s is not allowed to call "
                                "this function!"
                                % (authUser.login, authUser.realm))
                    raise PolicyException(_('The policy settings do not allow you to'
                                          ' issue this request!'))
    
            elif 'userunassign' == method:
    
                if not 'unassign' in self.getSelfserviceActions(authUser):
                    log.warning("userunassign: user %r@%r is not allowed to call "
                                "this function!"
                                % (authUser.login, authUser.realm))
                    raise PolicyException(_('The policy settings do not allow you '
                                          'to issue this request!'))
    
            elif 'userdelete' == method:
    
                if not 'delete' in self.getSelfserviceActions(authUser):
                    log.warning("userdelete: user %r@%r is not allowed to call "
                                "this function!"
                                % (authUser.login, authUser.realm))
                    raise PolicyException(_('The policy settings do not allow you '
                                          'to issue this request!'))
    
            elif 'userwebprovision' == method:
                user_selfservice_actions = self.getSelfserviceActions(authUser)
                typ = param.get('type').lower()
                if ((typ == 'oathtoken'
                        and 'webprovisionOATH' not in user_selfservice_actions)
                    or (typ == 'googleauthenticator_time'and
                        'webprovisionGOOGLEtime' not in user_selfservice_actions)
                    or (typ == 'googleauthenticator'
                        and 'webprovisionGOOGLE' not in user_selfservice_actions)):
                    log.warning("userwebprovision: user %r@%r is not allowed to "
                                "call this function!" % (authUser.login,
                                                         authUser.realm))
                    raise PolicyException(_('The policy settings do not allow you '
                                          'to issue this request!'))
    
                # Here we check, if the tokennum exceeds the licensed tokens
                if not self._checkTokenNum():
                    log.error("userwebprovision: The maximum licensed token "
                              "number is reached!")
                    raise PolicyException(_("You may not enroll any more tokens. "
                                          "Your maximum licensed token number "
                                          "is reached!"))
    
                if not self._checkTokenAssigned(authUser, token_num=options.get("token_num",0)):
                    log.warning("userwebprovision: the maximum number of allowed "
                                "tokens is exceeded. Check the policies")
                    raise PolicyException(_("The maximum number of allowed tokens "
                                          "is exceeded. Check the policies"))
    
            elif 'userhistory' == method:
                if not 'history' in self.getSelfserviceActions(authUser):
                    log.warning("userhistory: user %r@%r is not allowed to call "
                                "this function!"
                                % (authUser.login, authUser.realm))
                    raise PolicyException(_('The policy settings do not allow you '
                                          'to issue this request!'))
    
            elif 'userinit' == method:
    
                allowed_actions = self.getSelfserviceActions(authUser)
                typ = param['type'].lower()
                meth = 'enroll' + typ.upper()
    
                if meth not in allowed_actions:
                    log.warning("userinit: user %r@%r is not allowed to "
                                "enroll %s!" % (authUser.login,
                                                authUser.realm, typ))
                    raise PolicyException(_('The policy settings do not allow '
                                          'you to issue this request!'))
    
                # Here we check, if the tokennum exceeds the licensed tokens
                if not self._checkTokenNum():
                    log.error("userinit: The maximum licensed token "
                              "number is reached!")
                    raise PolicyException(_("You may not enroll any more tokens. "
                                          "Your maximum licensed token number "
                                          "is reached!"))
    
                if not self._checkTokenAssigned(authUser, token_num=options.get("token_num",0)):
                    log.warning("userinit: the maximum number of allowed tokens "
                                "is exceeded. Check the policies")
                    raise PolicyException(_("The maximum number of allowed tokens "
                                          "is exceeded. Check the policies"))
    
            else:
                log.error("Unknown method in selfservice: %s" % method)
                raise PolicyException(_("Unknown method in selfservice: %s") % method)
    
        elif 'system' == controller:
            actions = {
                'setDefault': 'write',
                'setConfig': 'write',
                'delConfig': 'write',
                'getConfig': 'read',
                'getRealms': 'read',
                'delResolver': 'write',
                'getResolver': 'read',
                'setResolver': 'write',
                'getResolvers': 'read',
                'setDefaultRealm': 'write',
                'getDefaultRealm': 'read',
                'get_resolver_list': 'read',
                'setRealm': 'write',
                'delRealm': 'write',
                'setPolicy': 'write',
                'importPolicy': 'write',
                'policies_flexi': 'read',
                'getPolicy': 'read',
                'getPolicyDef': 'read',
                'checkPolicy': "read",
                'delPolicy': 'write',
                }
    
            if not method in actions:
                log.error("an unknown method was passed in system: %s" % method)
                raise PolicyException(_("Failed to run checkPolicyPre. "
                                      "Unknown method: %s") % method)
    
            auth = self.getAuthorization('system', actions[method])
    
            if auth['active'] and not auth['auth']:
                log.warning("checkPolicyPre: admin >%s< is not authorited to %s."
                            " Missing policy scope=system, action=%s"
                            % (auth['admin'], method, actions[method]))
    
                raise PolicyException(_("Policy check failed. You are not allowed "
                                      "to %s system config.") % actions[method])
    
        elif controller == 'ocra':
    
            method_map = {'request': 'request', 'status': 'checkstatus',
                          'activationcode': 'getActivationCode',
                          'calcOTP': 'calculateOtp'}
    
            admin_user = getUserFromRequest(self.request)
            policies = self.getPolicy({'user': admin_user.get('login'), 'scope': 'ocra',
                                  'action': method, 'client': get_client()})
    
            if len(policies) == 0:
                log.warning("request: the admin >%r< is not allowed to do an ocra"
                            "/%r" % (admin_user.get('login'),
                                     method_map.get(method)))
                raise PolicyException(_("You do not have the administrative right to"
                                      " do an ocra/%s") % method_map.get(method))
    
        else:
            # unknown controller
            log.error("an unknown controller <<%r>> was passed." % controller)
            raise PolicyException(_("Failed to run getPolicyPre. Unknown "
                                  "controller: %s") % controller)
    
        return ret
    
    @log_with(log)
    def checkPolicyPost(self, controller, method, param=None, user=None):
        '''
        This function will check policies after a successful action in a
        controller. E.g. this can be setting a random PIN after successfully
        enrolling a token.
    
        :param controller: the controller context
        :param method: the calling action
        :param param: This is a dictionary with the necessary parameters.
        :param auth_user: This is the authenticated user. For the selfservice this
                          will be the user in the selfservice portal, for admin or
                          manage it will be the administrator
    
    
        :return: It returns a dictionary with the necessary results. These depend
                 on the controller.
        '''
        ret = {}
    
        if param is None:
            param = {}
    
        if 'admin' == controller:
            serial = getParam(param, "serial", optional)
            if user is None:
                user = getUserFromParam(param, optional)
    
            if 'init' == method:
                pass
                
            elif 'getserial' == method:
                # check if the serial/token, that was returned is in
                # the realms of the admin!
                policies = self.getAdminPolicies("getserial")
                if (policies['active'] and not
                        self._checkAdminAuthorization(policies, serial,
                                                User('', '', ''))):
                    log.warning("getserial:the admin >%s< is not allowed to get "
                                "serial of token %s" % (policies['admin'], serial))
                    raise PolicyException(_("You do not have the administrative "
                                          "right to get serials from this realm!"))
            else:
                # unknown method
                log.error("checkPolicyPost: an unknown method <<%s>>"
                          " was passed." % method)
                raise PolicyException(_("Failed to run getPolicyPost. "
                                      "Unknown method: %s") % method)
    
        elif 'system' == controller:
            log.debug("checkPolicyPost: entering controller %s" % controller)
    
            if 'getRealms' == method:
                systemReadRights = False
                res = param['realms']
                auth = self.getAuthorization('system', 'read')
                if auth['auth']:
                    systemReadRights = True
    
                if not systemReadRights:
                    # If the admin is not allowed to see all realms,
                    # (policy scope=system, action=read)
                    # the realms, where he has no administrative rights need,
                    # to be stripped.
                    pol = self.getAdminPolicies('')
                    if pol['active']:
                        log.debug("getRealms: the admin has policies "
                                  "in these realms: %r" % pol['realms'])
    
                        lowerRealms = uniquify(pol['realms'])
                        for realm, _v in res.items():
                            if ((not realm.lower() in lowerRealms)
                                    and (not '*' in lowerRealms)):
                                log.debug("getRealms: the admin has no policy in "
                                          "realm %r. Deleting "
                                          "it: %r" % (realm, res))
                                del res[realm]
                    else:
                        log.error("system: : getRealms: "
                                  "The admin >%s< is not allowed to read system "
                                  "config and has not realm administrative rights!"
                                  % auth['admin'])
                        raise PolicyException(_("You do not have system config read "
                                              "rights and not realm admin "
                                              "policies."))
                ret['realms'] = res
    
        else:
            # unknown controller
            log.error("checkPolicyPost: an unknown constroller <<%s>> "
                      "was passed." % controller)
            raise PolicyException(_("Failed to run getPolicyPost. "
                                  "Unknown controller: %s") % controller)
        return ret
    
    
    ###############################################################################
    #
    # Client Policies
    #
    @log_with(log)
    def get_client_policy(self, client, scope=None, action=None, realm=None, user=None,
                          find_resolver=True, userObj=None):
        '''
        This function returns the dictionary of policies for the given client.
    
        1. First it searches for all policies matching (scope, action, realm) and
        checks, whether the given client is contained in the policy field client.
        If no policy for the given client is found it takes the policy without
        a client
    
        2. Then it strips down the returnable policies to those, that only contain
        the username - UNLESS - none of the above policies contains a username
    
        3. then we try to find resolvers in the username (OPTIONAL)
        '''
        Policies = {}
    
        param = {}
    
        if scope:
            param["scope"] = scope
        if action:
            param["action"] = action
        if realm:
            param["realm"] = realm
    
        log.debug("with params %r, "
                  "client %r and user %r" % (param, client, user))
        Pols = self.getPolicy(param)
        log.debug("got policies %s " % Pols)
    
        def get_array(policy, attribute="client", marks=False):
            ## This function returns the parameter "client" or
            ## "user" in a policy as an array
            attrs = policy.get(attribute, "")
            if attrs == "None" or attrs is None:
                attrs = ""
            log.debug("splitting <%s>" % attrs)
            attrs_array = []
            if marks:
                attrs_array = [co.strip()[:-1] for co in attrs.split(',')
                               if len(co.strip()) and co.strip()[-1] == ":"]
            else:
                attrs_array = [co.strip()
                               for co in attrs.split(',')
                               if len(co.strip()) and co.strip()[-1] != ":"]
            # if for some reason the first element is empty, delete it.
            if len(attrs_array) and attrs_array[0] == "":
                del attrs_array[0]
            return attrs_array
    
        ## 1. Find a policy with this client
        for pol, policy in Pols.items():
            log.debug("checking policy %s" % pol)
            clients_array = get_array(policy, attribute="client")
            log.debug("the policy %s has these clients: %s. "
                      "checking against %s." % (pol, clients_array, client))
            client_found = False
            client_excluded = False
            for cl in clients_array:
                try:
                    if cl[0] in ['-', '!']:
                        if IPAddress(client) in IPNetwork(cl[1:]):
                            log.debug("the client %s is "
                                      "excluded by %s in policy "
                                      "%s" % (client, cl, pol))
                            client_excluded = True
                    if IPAddress(client) in IPNetwork(cl):
                        client_found = True
                except Exception as e:
                    log.warning("authorization policy %s with "
                                "invalid client: %r" % (pol, e))
    
            if client_found and not client_excluded:
                Policies[pol] = policy
    
        # No policy for this client was found, but maybe
        # there is one without clients
        if len(Policies) == 0:
            log.debug("looking for policy without any client")
            for pol, policy in Pols.items():
                if len(get_array(policy, attribute="client")) == 0:
                    Policies[pol] = policy
    
        ## 2. Within those policies select the policy with the user.
        ##     if there is a policy with this very user, return only
        ##     these policies, otherwise return all policies
        if user:
            user_policy_found = False
            own_policies = {}
            default_policies = {}
            for polname, pol in Policies.items():
                users = get_array(pol, attribute="user")
                log.debug("search user %s in users %s "
                          "of policy %s" % (user, users, polname))
                if user in users or '*' in users:
                    log.debug("adding %s to "
                              "own_policies" % polname)
                    own_policies[polname] = pol
                elif len(users) == 0:
                    log.debug("adding %s to "
                              "default_policies" % polname)
    
                    default_policies[polname] = pol
                else:
                    log.debug("policy %s contains only users "
                              "(%s) other than %s" % (polname, users, user))
    
            if len(own_policies):
                Policies = own_policies
                user_policy_found = True
            else:
                Policies = default_policies
    
            ##3. If no user specific policy was found, we now take a look,
            ##   if we find a policy with the matching resolver.
            if not user_policy_found and realm and find_resolver:
                ## get the resolver of the user in the realm and search for this
                ## resolver in the policies
                if userObj is not None:
                    resolvers = getResolversOfUser(userObj)
                else:
                    resolvers = getResolversOfUser(User(login=user, realm=realm))
                own_policies = {}
                default_policies = {}
                for polname, pol in Policies.items():
                    resolvs = get_array(pol, attribute="user", marks=True)
                    for r in resolvers:
                        # trim the resolver useridresolveree.LDAPIdResolver.\
                        # IdResolver.local to its name
                        r = r[r.rfind('.') + 1:]
                        if r in resolvs:
                            log.debug("adding %s to "
                                      "own_policies" % polname)
                            own_policies[polname] = pol
                        elif len(resolvs) == 0:
                            log.debug("adding %s (no "
                                      "resolvers) to default_policies" % polname)
                            default_policies[polname] = pol
                        else:
                            log.debug("policy %s contains "
                                      "only resolvers (%s) other than %s" %
                                      (polname, resolvs, r))
                if len(own_policies):
                    Policies = own_policies
                else:
                    Policies = default_policies
    
        return Policies
    
    @log_with(log)
    def set_realm(self, login, realm, exception=False):
        '''
        this function reads the policy scope: authorization, client: x.y.z,
        action: setrealm=new_realm and overwrites the existing realm of the user
        with the new_realm.
        This can be used, if the client is not able to pass a realm and the users
        are not be located in the default realm.
    
        returns:
            realm    - name of the new realm taken from the policy
        '''
        client = get_client()
        log.debug("got the client %s" % client)
        policies = self.get_client_policy(client, scope="authorization",
                                     action="setrealm", realm=realm,
                                     user=login, find_resolver=False)
    
        if len(policies):
            realm = self.getPolicyActionValue(policies, "setrealm", String=True)
    
        return realm
    
    @log_with(log)
    def check_user_authorization(self, login, realm, exception=False):
        '''
        check if the given user/realm is in the given policy.
        The realm may contain the wildcard '*', then the policy holds for
        all realms. If no username or '*' is given, the policy holds for all users.
    
        attributes:
            login    - loginname of the user
            realm    - realm of the user
            exception    - wether it should return True/False or raise an Exception
        '''
        res = False
    
        # if there is absolutely NO policy in scope authorization,
        # we return immediately
        if len(self.getPolicy({"scope": "authorization", "action": "authorize"})) == 0:
            log.debug("absolutely no authorization policy.")
            return True
    
        client = get_client()
        log.debug("got the client %s" % client)
        policies = self.get_client_policy(client, scope="authorization",
                                     action="authorize", realm=realm, user=login)
        log.debug("got policies %s for "
                  "user %s" % (policies, login))
    
        if len(policies):
            res = True
    
        if res is False and exception:
            raise AuthorizeException(_("Authorization on client %s failed "
                                     "for %s@%s.") % (client, login, realm))
    
        return res
    
    
    ###############################################################################
    #
    #  Authentication stuff
    #
    @log_with(log)
    def get_auth_passthru(self, user):
        '''
        returns True, if the user in this realm should be authenticated against
        the UserIdResolver in case the user has no tokens assigned.
        '''
        ret = False
        client = get_client()
        pol = self.get_client_policy(client, scope="authentication",
                                action="passthru", realm=user.realm,
                                user=user.login, userObj=user)
        if len(pol) > 0:
            ret = True
        return ret
    
    @log_with(log)
    def get_auth_passOnNoToken(self, user):
        '''
        returns True, if the user in this realm should be always authenticated
        in case the user has no tokens assigned.
        '''
        ret = False
        client = get_client()
        pol = self.get_client_policy(client, scope="authentication",
                                action="passOnNoToken", realm=user.realm,
                                user=user.login, userObj=user)
        if len(pol) > 0:
            ret = True
        return ret
    
    
    @log_with(log)
    def get_auth_smstext(self, user="", realm=""):
        '''
        this function checks the policy scope=authentication, action=smstext
        This is a string policy
        The function returns the tuple (bool, string),
            bool: If a policy is defined
            string: the string to use
        '''
        # the default string is the OTP value
        ret = False
        smstext = "<otp>"
    
        pol = self.getPolicy({'scope': 'authentication', 'realm': realm,
                          "action" : "smstext" })
    
        if len(pol) > 0:
            smstext = self.getPolicyActionValue(pol, "smstext", String=True)
            log.debug("got the smstext = %s" % smstext)
            ret = True
    
        return ret, smstext

    @log_with(log)
    def get_auth_AutoSMSPolicy(self, realms=None):
        '''
        Returns true, if the autosms policy is set in one of the realms
    
        return:
            True or False
    
        input:
            list of realms
        '''
        client = get_client()
        user = getUserFromParam(self.request.params, optional)
        login = user.login
        if realms is None:
            realm = user.realm or getDefaultRealm()
            realms = [realm]
    
        ret = False
        for realm in realms:
            pol = self.get_client_policy(client, scope="authentication",
                                    action="autosms", realm=realm,
                                    user=login, userObj=user)
    
            if len(pol) > 0:
                log.debug("found policy in realm %s" % realm)
                ret = True
    
        return ret
    
    @log_with(log)
    def get_auth_challenge_response(self, user, ttype):
        """
        returns True, if the user in this realm with this token type should be
        authenticated via Challenge Response
    
        :param user: the user object
        :param ttype: the type of the token
    
        :return: bool
        """
    
        ret = False
        p_user = None
        p_realm = None
    
        if user is not None:
            p_user = user.login
            p_realm = user.realm
    
        client = get_client()
    
        pol = self.get_client_policy(client, scope="authentication",
                                action="challenge_response",
                                realm=p_realm,
                                user=p_user, userObj=user)
        log.debug("got policy %r for user %r@%r from client %r" % (pol, 
                                                                   p_user, 
                                                                   p_realm, 
                                                                   client))
    
        Token_Types = self.getPolicyActionValue(pol, "challenge_response", String=True)
        token_types = [t.lower() for t in Token_Types.split()]
    
        if ttype.lower() in token_types or '*' in token_types:
            log.debug("found matching token type %s" % ttype)
            ret = True
    
        return ret
    
    @log_with(log)
    def get_auth_PinPolicy(self, realm=None, user=None):
        '''
        Returns the PIN policy, that defines, how the OTP PIN is to be verified
        within the given realm
    
        return:
            0    - verify against fixed OTP PIN
            1    - verify the password component against the
                          UserResolver (LPAP Password etc.)
            2    - verify no OTP PIN at all! Only OTP value!
    
        The policy is defined via
            scope : authentication
            realm : ....
            action: otppin=0/1/2
            client: IP
            user  : some user
        '''
        client = get_client()
        if user is None:
            user = getUserFromParam(self.request.params, optional)
        login = user.login
        if realm is None:
            realm = user.realm or getDefaultRealm()
    
        pol = self.get_client_policy(client, scope="authentication", action="otppin",
                                realm=realm, user=login, userObj=user)
    
        log.debug("got policy %s for user %s@%s  client %s" % (pol, login, realm, client))
        pin_check = self.getPolicyActionValue(pol, "otppin", max=False)
    
        if pin_check in [1, 2]:
            return pin_check
    
        return 0
    
    @log_with(log)
    def get_qrtan_url(self, realm):
        '''
        Returns the URL for the half automatic mode for the QR TAN token
        for the given realm
    
        :return: url string
    
        '''
        pol = self.getPolicy({"scope": "authentication", "realm": realm})
        url = self.getPolicyActionValue(pol, "qrtanurl", String=True)
        return url
    
    
    ###############################################################################
    #
    #  Authorization
    #
    @log_with(log)
    def check_auth_tokentype(self, tokentype = None, exception=False, user=None):
        '''
        Checks if the token type of the given serial matches the tokentype policy
    
        :return: True/False - returns true or false or raises an exception
                              if exception=True
        '''
        if tokentype is None:
            # if no serial is given, we return True right away
            log.debug("We have got no serial. Obviously doing passthru.")
            return True
    
        client = get_client()
        if user is None:
            user = getUserFromParam(self.request.params, optional)
        login = user.login
        realm = user.realm or getDefaultRealm()
        tokentypes = []
        res = False
    
        pol = self.get_client_policy(client, scope="authorization", action="tokentype",
                                realm=realm, user=login, userObj=user)
    
        log.debug("got policy %s for user %s@%s  client %s" % (pol,
                                                               login, 
                                                               realm, 
                                                               client))
    
        t_type = self.getPolicyActionValue(pol, "tokentype", max=False, String=True)
        if len(t_type) > 0:
            tokentypes = [t.strip() for t in t_type.lower().split(" ")]
    
        log.debug("found these "
                  "tokentypes: <%s>" % tokentypes)
    
        if len(tokentypes) == 0:
            res = True 
        if (tokentype in tokentypes or '*' in tokentypes):
            res = True
    
        if res is False and exception:
            self.c.audit["action_detail"] = \
                "failed due to authorization/tokentype policy"
            raise AuthorizeException(_("Authorization for token with type <<%s>> "
                                     "failed on client %s") % (tokentype,
                                                              client))
    
        return res
    

    @log_with(log)
    def check_auth_serial(self, serial, exception=False, user=None):
        '''
        Checks if the token with the serial number matches the serial
        authorize policy scope=authoriztaion, action=serial
    
        :param serial: The serial number of the token to check
        :type serial: string
        :param exception: If "True" an exception is raised instead of
                          returning False
        :type exception: boolean
        :param user: User to narrow down the policy
        :type user: User object
    
        :return: result
        :rtype: boolean
        '''
        if serial is None:
            # if no serial is given, we return True right away
            log.debug("We have got no serial. Obviously doing passthru.")
            return True
    
        client = get_client()
        if user is None:
            user = getUserFromParam(self.request.params, optional)
        login = user.login
        realm = user.realm or getDefaultRealm()
        res = False
    
        pol = self.get_client_policy(client, scope="authorization", action="serial",
                                realm=realm, user=login, userObj=user)
        if len(pol) == 0:
            # No policy found, so we skip the rest
            log.debug("No policy scope=authorize, action=serial for user %r, realm %r, client %r"  % (login, 
                                                                                                      realm, 
                                                                                                      client))
            return True
    
        log.debug("got policy %s for user %s@%s  client %s" % (pol, 
                                                               login, 
                                                               realm, 
                                                               client))
    
        # extract the value from the policy
        serial_regexp = self.getPolicyActionValue(pol, "serial", max=False, String=True)
        log.debug("found this regexp /%r/ for the serial %r"
                  % (serial_regexp, serial))
    
        if re.search(serial_regexp, serial):
            log.debug("regexp matches.")
            res = True
    
        if res is False and exception:
            self.c.audit["action_detail"] = "failed due to authorization/serial policy"
            raise AuthorizeException(_("Authorization for token %s failed on client %s") % (serial,
                                                                                         client))
    
        return res
    
    @log_with(log)
    def is_auth_return(self, success=True, user=None):
        '''
        returns True if the policy
            scope = authorization
            action = detail_on_success/detail_on_fail
            is set.
    
        :param success: Defines if we should check of the policy
                        detaul_on_success (True) or detail_on_fail (False)
        :type success: bool
        '''
        ret = False
    
        client = get_client()
        if user is None:
            user = getUserFromParam(self.request.params, optional)
        login = user.login
        realm = user.realm or getDefaultRealm()
        if success:
            pol = self.get_client_policy(client, scope="authorization",
                                    action="detail_on_success", realm=realm,
                                    user=login, userObj=user)
        else:
            pol = self.get_client_policy(client, scope="authorization",
                                    action="detail_on_fail", realm=realm,
                                    user=login, userObj=user)
    
        if len(pol):
            ret = True
    
        return ret
    
    
    ### helper ################################
    @log_with(log)
    def get_pin_policies(self, user):
        '''
        lookup for the pin policies - the list of policies
        is preserved for repeated lookups
    
        : raises: exception, if more then one pin policies are matching
    
        :param user: the policies which are applicable to the user
        :return: list of otppin id's
        '''
        pin_policies = []
    
        pin_policies.append(self.get_auth_PinPolicy(user=user))
        pin_policies = list(set(pin_policies))
    
        if len(pin_policies) > 1:
            msg = ("conflicting authentication polices. "
                   "Check scope=authentication. policies: %r" % pin_policies)
    
            log.error(msg)
            #self.context.audit['action_detail'] = msg
            raise Exception('multiple pin policies found')
            ## former return -2
    
        return pin_policies
    
    #eof###########################################################################
