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
This file is part of the privacyidead service
In provides the self service interface,
where users can manage their own tokens

All functions starting with /selfservice/user...
are data functions and protected by the session key
i.e. the session key must be passed as the parameter session=
'''
import os

import json
import webob


from pylons import request, response, config, tmpl_context as c
from pylons.controllers.util import abort
from mako.exceptions import CompileException

from privacyidea.lib.base import BaseController
from pylons.templating import render_mako as render
from privacyidea.lib.token import genSerial


from privacyidea.lib.token import enableToken, assignToken, unassignToken
from privacyidea.lib.token import initToken, removeToken
from privacyidea.lib.token import setPin
from privacyidea.lib.token import resyncToken, resetToken, setPinUser
from privacyidea.lib.token import TokenIterator, isTokenOwner
from privacyidea.lib.token import hasOwner, getTokenType
from privacyidea.lib.token import getTokenRealms
from privacyidea.lib.token import get_multi_otp
from privacyidea.lib.token import get_serial_by_otp

from privacyidea.lib.token import get_tokenserial_of_transaction

from privacyidea.lib.token import getTokens4UserOrSerial

from privacyidea.lib.token import checkSerialPass
from privacyidea.lib.tokenclass import OcraTokenClass
from privacyidea.lib.audit import search as audit_search

from privacyidea.lib.policy import PolicyClass
from privacyidea.lib.policy import PolicyException

from privacyidea.lib.util import getParam
from privacyidea.lib.util import getLowerParams
from privacyidea.lib.util import generate_otpkey
from privacyidea.lib.util import remove_empty_lines

from privacyidea.lib.apps import create_google_authenticator_url
from privacyidea.lib.apps import create_oathtoken_url

from privacyidea.lib.reply import sendResult, sendError

from privacyidea.lib.audit import logTokenNum
from privacyidea.lib.util    import get_version
from privacyidea.lib.util    import get_copyright_info
from privacyidea.weblib.util import get_client
from privacyidea.lib.account import is_admin_identity
from privacyidea.lib.realm import getDefaultRealm

from privacyidea.model.meta import Session

from privacyidea.lib.reply import sendQRImageResult
from privacyidea.lib.reply import create_img

from privacyidea.weblib.selfservice import get_imprint
from privacyidea.lib.user import getUserInfo, User

from privacyidea.lib.error import SelfserviceException

import traceback
#import datetime, random
import copy

from privacyidea.lib.selftest import isSelfTest

from privacyidea.lib.token import newToken
from privacyidea.lib.token import get_token_type_list
from pylons.i18n.translation import _
from privacyidea.lib.config import get_privacyIDEA_config
from privacyidea.lib.log import log_with
import logging
log = logging.getLogger(__name__)

ENCODING = "utf-8"

optional = True
required = False

@log_with(log)
def getTokenForUser(user):
    tokenArray = []
    
    log.debug("user %s in realm %s." % (user.login, user.realm))
    toks = TokenIterator(user, None, filterRealm=user.realm)

    for tok in toks:
        tokenArray.append(tok)

    return tokenArray


class SelfserviceController(BaseController):

    authUser = None

    @log_with(log)
    def __before__(self, action, **params):
        '''
        This is the authentication to self service
        If you want to do ANYTHING with selfservice, you need to be authenticated
        The _before_ is executed before any other function in this controller.
        '''

        try:

            param = request.params

            # Call the __before__ from the parents class to do the translation
            self.set_language()

            c.audit['success'] = False
            c.audit['client'] = get_client()
            if request.params.get('serial'):
                tokentype = getTokenType(request.params.get('serial'))
            else:
                tokentype = None
            self.Policy = PolicyClass(request, config, c,
                                      get_privacyIDEA_config(),
                                      tokenrealms = request.params.get('serial'),
                                      tokentype = tokentype,
                                      token_type_list = get_token_type_list())

            c.version = get_version()
            c.licenseinfo = get_copyright_info()
            self.before_identity_check(action, check_admin=False)

            c.imprint = get_imprint(c.realm)

            c.tokenArray = []

            c.user = self.authUser.login
            c.realm = self.authUser.realm
            c.tokenArray = getTokenForUser (self.authUser)

            ## only the defined actions should be displayed
            ## - remark: the generic actions like enrollTT are already approved
            ##   to have a rendering section and included
            actions = self.Policy.getSelfserviceActions(self.authUser)
            c.actions = actions
            for policy in actions:
                if "=" in policy:
                    (name, val) = policy.split('=')
                    val = val.strip()
                    ## try if val is a simple numeric -
                    ## w.r.t. javascript evaluation
                    try:
                        nval = int(val)
                    except:
                        nval = val
                    c.__setattr__(name.strip(), nval)

            c.dynamic_actions = add_dynamic_selfservice_enrollment(c.actions)

            ## we require to establish all token local defined policies to be initialiezd
            additional_policies = add_dynamic_selfservice_policies(actions)
            for policy in additional_policies:
                c.__setattr__(policy, -1)

            add_local_policies()
            c.otplen = -1

            return response

        except webob.exc.HTTPUnauthorized as acc:
            ## the exception, when an abort() is called if forwarded
            log.info("%r: webob.exception %r" % (action, acc))
            log.info(traceback.format_exc())
            Session.rollback()
            Session.close()
            raise acc

        except Exception as e:
            log.error("failed with error: %r" % e)
            log.error(traceback.format_exc())
            Session.rollback()
            Session.close()
            return sendError(response, e, context='before')

        finally:
            pass


    @log_with(log)
    def __after__(self, action, **params):
        '''

        '''
        param = request.params

        try:
            if c.audit['action'] in ['selfservice/userassign',
                                    'selfservice/userdisable',
                                    'selfservice/userinit',
                                    'selfservice/userdelete',
                                    'selfservice/userenable',
                                    'selfservice/userresync',
                                    'selfservice/usersetmpin',
                                    'selfservice/usersetpin',
                                    'selfservice/userwebprovision',
                                    'selfservice/usergetmultiotp',
                                    'selfservice/userhistory',
                                    'selfservice/index']:
                if isSelfTest():
                    log.debug("Doing selftest!")
                    suser = getParam(param, "selftest_user", True)
                    if suser is not None:
                        (c.user, _foo, c.realm) = getParam(param, "selftest_user", True).rpartition('@')
                    else:
                        raise SelfserviceException("When running in selftest, you need to specify a selftsest_user!")

                log.debug("authenticating as %s in realm %s!" % (c.user, c.realm))

                c.audit['user'] = c.user
                c.audit['realm'] = c.realm
                c.audit['success'] = True

                if param.has_key('serial'):
                    c.audit['serial'] = param['serial']
                    c.audit['token_type'] = getTokenType(param['serial'])

                self.audit.log(c.audit)

            return response

        except webob.exc.HTTPUnauthorized as acc:
            ## the exception, when an abort() is called if forwarded
            log.error("%r: webob.exception %r" % (action, acc))
            log.error(traceback.format_exc())
            Session.rollback()
            Session.close()
            raise acc

        except Exception as e:
            log.error("failed with error: %r" % e)
            log.error(traceback.format_exc())
            Session.rollback()
            Session.close()
            return sendError(response, e, context='after')

        finally:
            pass

    def index(self):
        '''
        This is the redirect to the first template
        '''
        c.title = "privacyIDEA Self Service"
        http_host = request.environ.get("HTTP_HOST")
        url_scheme = request.environ.get("wsgi.url_scheme")
        c.logout_url = "%s://%s/account/logout" % (url_scheme, http_host)
        c.is_admin = is_admin_identity(request.environ.get('repoze.who.identity'), exception=False)
        ren = render('/selfservice/base.mako')
        return ren

    @log_with(log)
    def load_form(self, action, **params):
        '''
        This shows the enrollment form for a requested token type.

        implicit parameters are:

        :param type: token type
        :param scope: defines the rendering scope

        :return: rendered html of the requested token
        '''
        res = ''
        param = {}

        try:

            param.update(request.params)

            act = getParam(param, "type", required)
            try:
                (tok, section, scope) = act.split('.')
            except Exception:
                return res

            if section != 'selfservice':
                return res

            g = config['pylons.app_globals']
            tokenclasses = copy.deepcopy(g.tokenclasses)

            if tok in tokenclasses:
                tclass = tokenclasses.get(tok)
                tclt = newToken(tclass)
                if hasattr(tclt, 'getClassInfo'):
                    sections = tclt.getClassInfo(section, {})
                    if scope in sections.keys():
                        section = sections.get(scope)
                        page = section.get('page')
                        c.scope = page.get('scope')
                        c.authUser = self.authUser
                        html = page.get('html')
                        res = render(os.path.sep + html)
                        res = remove_empty_lines(res)

            Session.commit()
            return res

        except CompileException as exx:
            log.error("compile error while processing %r.%r:" %
                                                                (tok, scope))
            log.error(exx)
            log.error(traceback.format_exc())
            Session.rollback()
            raise Exception(exx)

        except Exception as exx:
            Session.rollback()
            error = ('error (%r) accessing form data for: tok:%r, scope:%r'
                                ', section:%r' % (exx, tok, scope, section))
            log.error(error)
            log.error(traceback.format_exc())
            return '<pre>%s</pre>' % error

        finally:
            Session.close()


    def custom_style(self):
        '''
        In case the user hasn't defined a custom css, Pylons calls this action.
        Return an empty file instead of a 404 (which would mean hitting the
        debug console)
        '''
        response.headers['Content-type'] = 'text/css'
        return ''

    def assign(self):
        '''
        In this form the user may assign an already existing Token to himself.
        For this, the user needs to know the serial number of the Token.
        '''
        return render('/selfservice/assign.mako')

    def resync(self):
        '''
        In this form, the user can resync an HMAC based OTP token
        by providing two OTP values
        '''
        return render('/selfservice/resync.mako')

    def reset(self):
        '''
        In this form the user can reset the Failcounter of the Token.
        '''
        return render('/selfservice/reset.mako')

    def getotp(self):
        '''
        In this form, the user can retrieve OTP values
        '''
        return render('/selfservice/getotp.mako')

    def disable(self):
        '''
        In this form the user may select a token of his own and
        disable this token.
        '''
        return render('/selfservice/disable.mako')

    def enable(self):
        '''
        In this form the user may select a token of his own and
        enable this token.
        '''
        return render('/selfservice/enable.mako')

    def unassign(self):
        '''
        In this form the user may select a token of his own and
        unassign this token.
        '''
        return render('/selfservice/unassign.mako')

    def delete(self):
        '''
        In this form the user may select a token of his own and
        delete this token.
        '''
        return render('/selfservice/delete.mako')


    def setpin(self):
        '''
        In this form the user may set the OTP PIN, which is the static password
        he enters when logging in in front of the otp value.
        '''
        return render('/selfservice/setpin.mako')

    def setmpin(self):
        '''
        In this form the user my set the PIN for his mOTP application soft
        token on his phone. This is the pin, he needs to enter on his phone,
        before a otp value will be generated.
        '''
        return render('/selfservice/setmpin.mako')

    def history(self):
        '''
        This is the form to display the history table for the user
        '''
        return render('/selfservice/history.mako')

    def webprovisionoathtoken(self):
        '''
        This is the form for an oathtoken to do web provisioning.
        '''
        return render('/selfservice/webprovisionoath.mako')

    def activateqrtoken(self):
        '''
        return the form for an qr token activation
        '''
        return render('/selfservice/activateqr.mako')

    def webprovisiongoogletoken(self):
        '''
        This is the form for an google token to do web provisioning.
        '''
        try:
            c.actions = self.Policy.getSelfserviceActions(self.authUser)
            Session.commit()
            return render('/selfservice/webprovisiongoogle.mako')

        except Exception as exx:
            log.error("failed with error: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, exx)

        finally:
            Session.close()


###### API functions
    @log_with(log)
    def userhistory(self, action, **params):
        '''
        This returns the list of the tokenactions of this user
        It returns the audit information for the given search pattern

        method:
            selfservice/userhistory

        arguments:
            key, value pairs as search patterns.

            or: Usually the key=values will be locally AND concatenated.
                it a parameter or=true is passed, the filters will be OR
                concatenated.

            The Flexigrid provides us the following parameters:
                ('page', u'1'), ('rp', u'100'),
                ('sortname', u'number'),
                ('sortorder', u'asc'),
                ('query', u''), ('qtype', u'serial')]
        returns:
            JSON response
        '''

        param = request.params
        res = {}
        try:

            self.Policy.checkPolicyPre('selfservice', 'userhistory', param, self.authUser)

            lines, total, page = audit_search(param, user=self.authUser,
                                columns=['date', 'action', 'success', 'serial',
                                        'token_type', 'administrator',
                                        'action_detail', 'info'])

            response.content_type = 'application/json'

            if not total:
                total = len(lines)

            res = { "page" : page,
                "total" : total,
                "rows" : lines }

            c.audit['success'] = True

            Session.commit()
            return json.dumps(res, indent=3)

        except PolicyException as pe:
            log.error("policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as exx:
            log.error("audit/search failed: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, u"audit/search failed: %s"
                                                        % unicode(exx), 0)

        finally:
            Session.close()


    def usertokenlist(self):
        '''
        This returns a tokenlist as html output
        '''
        res = render('/selfservice/tokenlist.mako')
        return res

    @log_with(log)
    def userreset(self, action, **params):
        '''
        This internally resets the failcounter of the given token.
        '''
        res = {}
        param = request.params
        serial = None

        try:
            self.Policy.checkPolicyPre('selfservice', 'userreset', param, self.authUser)

            serial = getParam(param, "serial", required)

            if (True == isTokenOwner(serial, self.authUser)):
                log.info("user %s@%s is resetting the failcounter"
                                " of his token with serial %s"
                        % (self.authUser.login, self.authUser.realm, serial))
                ret = resetToken(serial=serial)
                res["reset Failcounter"] = ret

                c.audit['success'] = ret

            Session.commit()
            return sendResult(response, res, 1)

        except PolicyException as pe:
            log.error("policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error("error resetting token with serial %s: %r"
                      % (serial, e))
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, e, 1)

        finally:
            Session.close()

    @log_with(log)
    def userresync(self, action, **params):
        '''
        This is the internal resync function that is called from within the self service portal
        '''

        res = {}
        param = request.params
        serial = "N/A"

        try:
            # check selfservice authorization
            self.Policy.checkPolicyPre('selfservice', 'userresync', param, self.authUser)

            serial = getParam(param, "serial", required)
            otp1 = getParam(param, "otp1", required)
            otp2 = getParam(param, "otp2", required)

            if (True == isTokenOwner(serial, self.authUser)):
                log.info("user %s@%s is resyncing his "
                          "token with serial %s"
                        % (self.authUser.login, self.authUser.realm, serial))
                ret = resyncToken(otp1, otp2, None, serial)
                res["resync Token"] = ret

                c.audit['success'] = ret

            Session.commit()
            return sendResult(response, res, 1)

        except PolicyException as pe:
            log.error("policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error("error resyncing token with serial %s:%r"
                       % (serial, e))
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, e, 1)

        finally:
            Session.close()


    @log_with(log)
    def usersetmpin(self, action, **params):
        '''
        When the user hits the set pin button, this function is called.
        '''
        res = {}

        ## if there is a pin
        try:
            param = getLowerParams(request.params)

            # check selfservice authorization
            self.Policy.checkPolicyPre('selfservice', 'usersetmpin', param, self.authUser)

            pin = getParam(param, "pin", required)
            serial = getParam(param, "serial", required)

            if (True == isTokenOwner(serial, self.authUser)):
                log.info("user %s@%s is setting the mOTP PIN"
                         " for token with serial %s"
                          % (self.authUser.login, self.authUser.realm, serial))
                ret = setPinUser(pin, serial)
                res["set userpin"] = ret

                c.audit['success'] = ret

            Session.commit()
            return sendResult(response, res, 1)

        except PolicyException as pex:
            log.error("policy failed: %r" % pex)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pex), 1)

        except Exception as exx:
            log.error("Error setting the mOTP PIN %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, exx, 1)

        finally:
            Session.close()

    @log_with(log)
    def usersetpin(self, action, **params):
        '''
        When the user hits the set pin button, this function is called.
        '''
        res = {}

        ## if there is a pin
        try:
            param = getLowerParams(request.params)

            # check selfservice authorization
            self.Policy.checkPolicyPre('selfservice', 'usersetpin', param, self.authUser)

            userPin = getParam(param, "userpin", required)
            serial = getParam(param, "serial", required)

            if (True == isTokenOwner(serial, self.authUser)):
                log.info("user %s@%s is setting the OTP PIN "
                         "for token with serial %s" %
                         (self.authUser.login, self.authUser.realm, serial))

                check_res = self.Policy.checkOTPPINPolicy(userPin, self.authUser)

                if not check_res['success']:
                    log.warning("Setting of OTP PIN for Token %s"
                                " by user %s failed: %s" %
                                        (serial, c.user, check_res['error']))
                    return sendError(response, u"Setting OTP PIN failed: %s"
                                                        % check_res['error'])

                if 1 == self.Policy.getOTPPINEncrypt(serial=serial,
                                         user=User(c.user, "", c.realm),
                                         tokenrealms = getTokenRealms(serial)):
                    param['encryptpin'] = "True"
                ret = setPin(userPin, None, serial, param)
                res["set userpin"] = ret

                c.audit['success'] = ret

            Session.commit()
            return sendResult(response, res, 1)

        except PolicyException as pex:
            log.error("policy failed: %r" % pex)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pex), 1)

        except Exception as exx:
            log.error("Error setting OTP PIN: %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, exx, 1)

        finally:
            Session.close()

    @log_with(log)
    def usergetSerialByOtp(self, action, **params):
        '''
         method:
            selfservice/usergetSerialByOtp

        description:
            searches for the token, that generates the given OTP value.
            The search can be restricted by several critterions
            This method only searches tokens in the realm of the user
            and tokens that are not assigned!

        arguments:
            otp      - required. Will search for the token, that produces
                       this OTP value
            type     - optional, will only search in tokens of type

        returns:
            a json result with the serial


        exception:
            if an error occurs an exception is serialized and returned

        '''
        param = request.params
        res = {}
        try:
            # check selfservice authorization

            self.Policy.checkPolicyPre('selfservice', 'usergetserialbyotp', param,
                                                                self.authUser)

            otp = getParam(param, "otp", required)
            ttype = getParam(param, "type", optional)

            c.audit['token_type'] = ttype
            serial, _username, _resolverClass = get_serial_by_otp(None,
                    otp, 10, typ=ttype, realm=self.authUser.realm, assigned=0)
            res = {'serial' : serial}

            c.audit['success'] = 1
            c.audit['serial'] = serial

            Session.commit()
            return sendResult(response, res, 1)

        except PolicyException as pe:
            log.error("policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as exx:
            log.error("token assignment failed! %r" % exx)
            Session.rollback()
            return sendError(response, exx, 1)

        finally:
            Session.close()

    @log_with(log)
    def userassign(self, action, **params):
        '''
        This is the internal assign function that is called from within
        the self service portal
        '''
        param = request.params
        res = {}

        try:
            # check selfservice authorization
            self.Policy.checkPolicyPre('selfservice', 'userassign', param, self.authUser)

            upin = getParam(param, "pin", optional)
            serial = getParam(param, "serial", required)

            # check if token is in another realm
            realm_list = getTokenRealms(serial)
            if (not self.authUser.realm.lower() in realm_list
                        and len(realm_list)):
                # if the token is assigned to realms, then the user must be in
                # one of the realms, otherwise the token can not be assigned
                raise SelfserviceException(_("The token you want to assign is "
                                             " not contained in your realm!"))

            if (False == hasOwner(serial)):
                log.info("user %s@%s is assign the token with "
                                                    "serial %s to himself."
                        % (self.authUser.login, self.authUser.realm, serial))
                ret = assignToken(serial, self.authUser, upin)
                res["assign token"] = ret

                c.audit['success'] = ret
            else:
                raise SelfserviceException(_("The token is already assigned "
                                             "to another user."))

            Session.commit()
            return sendResult(response, res, 1)

        except PolicyException as pe:
            log.error("policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as exx:
            log.error("token assignment failed! %r" % exx)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, exx, 1)

        finally:
            Session.close()

    @log_with(log)
    def userunassign(self, action, **params):
        '''
        This is the internal unassign function that is called from within
        the self service portal. The user is only allowed to unassign token,
        that belong to him.
        '''
        param = request.params
        res = {}

        try:
            # check selfservice authorization

            self.Policy.checkPolicyPre('selfservice', 'userunassign', param, self.authUser)

            serial = getParam(param, "serial", optional)
            upin = getParam(param, "pin", optional)

            if (True == isTokenOwner(serial, self.authUser)):
                log.info("user %s@%s is unassigning his "
                                                        "token with serial %s."
                         % (self.authUser.login, self.authUser.realm, serial))
                # TODO: In what realm will the unassigned token be? We should
                # handle this in the unassign Function
                ret = unassignToken(serial, None, upin)
                res["unassign token"] = ret

                c.audit['success'] = ret

            Session.commit()
            return sendResult(response, res, 1)

        except PolicyException as pe:
            log.error("policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error("unassigning token %s of user %s failed! %r"
                       % (serial, c.user, e))
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, e, 1)

        finally:
            Session.close()


    @log_with(log)
    def userdelete(self, action, **params):
        '''
        This is the internal delete token function that is called from within the self service portal
        The user is only allowed to delete token, that belong to him.
        '''
        param = request.params
        res = {}

        try:
            # check selfservice authorization
            self.Policy.checkPolicyPre('selfservice', 'userdelete', param, self.authUser)

            serial = getParam(param, "serial", optional)

            if (True == isTokenOwner(serial, self.authUser)):
                log.info("user %s@%s is deleting his token with serial %s."
                            % (self.authUser.login, self.authUser.realm, serial))
                ret = removeToken(serial=serial)
                res["delete token"] = ret

                c.audit['success'] = ret

            Session.commit()
            return sendResult(response, res, 1)

        except PolicyException as pe:
            log.error("policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error("deleting token %s of user %s failed! %r"
                      % (serial, c.user, e))
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, e, 1)

        finally:
            Session.close()


    @log_with(log)
    def userdisable(self, action, **params):
        '''
        This is the internal disable function that is called from within the self service portal
        '''
        param = request.params
        res = {}
        try:
            # check selfservice authorization
            self.Policy.checkPolicyPre('selfservice', 'userdisable', param, self.authUser)

            serial = getParam(param, "serial", optional)

            if (True == isTokenOwner(serial, self.authUser)):
                log.info("user %s@%s is disabling his token with serial %s."
                            % (self.authUser.login, self.authUser.realm, serial))
                ret = enableToken(False, None, serial)
                res["disable token"] = ret

                c.audit['success'] = ret
            Session.commit()
            return sendResult(response, res, 1)

        except PolicyException as pe:
            log.error("policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error("disabling token %s of user %s failed! %r"
                      % (serial, c.user, e))
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, e, 1)

        finally:
            Session.close()


    @log_with(log)
    def userenable(self, action, **params):
        '''
        This is the internal disable function that is called from within
        the self service portal to enable a token
        '''
        param = request.params
        res = {}

        try:
            # check selfservice authorization
            self.Policy.checkPolicyPre('selfservice', 'userenable', param, self.authUser)

            serial = getParam(param, "serial", optional)

            if (True == isTokenOwner(serial, self.authUser)):
                log.info("user %s@%s is enabling his token with serial %s."
                            % (self.authUser.login, self.authUser.realm, serial))
                ret = enableToken(True, None, serial)
                res["enable token"] = ret

                c.audit['success'] = ret

            Session.commit()
            return sendResult(response, res, 1)

        except PolicyException as pe:
            log.error("policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error("enabling token %s of user %s failed! %r"
                      % (serial, c.user, e))
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, e, 1)

        finally:
            Session.close()


    @log_with(log)
    def token_call(self, action, **params):
        '''
            the generic method call for an dynamic token
        '''
        param = {}

        res = {}

        try:
            param.update(request.params)

            ## method could be part of the virtual url
            context = request.path_info.split('/')
            if len(context) > 2:
                method = context[2]
            else:
                method = getParam(param, "method", required)

            typ = getParam(param, "type", required)
            serial = getParam(param, "serial", optional)

            # check selfservice authorization
            #
            #TODO: use get_client_policy instead
            #Cornelius Kölbel        Apr 18 7:31 PM
            #
            #Hier sollte nicht mehr die Funktion getPolicy verwendet werden sondern die Funktion
            #
            #get_client_policy
            #
            #Wenn ich genau wüsste, was die Funktion token_call macht (gräßlicher Name) dann könnte ich mehr dazu sagen.
            #
            #Die Funktion getPolicy ist zu grobschlächtig ;-) get_client_policy liefert die Policies auch in Abhängigkeit vom Benutzer, vom Realm und vom anfragenden Client zurück.

            pols = self.Policy.getPolicy({ "realm" : self.authUser.realm,
                                "scope" : "selfservice" })
            found = False
            for policy in pols.values():
                action = u'' + policy.get('action')
                actions_in = action.split(',')

                ## TODO: verify
                ## Cornelius Kölbel        Apr 18 7:31 PM
                ##
                ## Das könnte schlecht sein, wenn es eine Action gibt, die irgendwie so lautet:
                ##
                ## sms_string="Hallo und viel Freude"
                ##
                ## dann wird daraus
                ##
                ## HalloundvielFreude

                actions = []
                for act in actions_in:
                    actions.append(act.strip())

                if method in actions:
                    found = True
                    break

            if found == False:
                log.error('user %r not authorized to call %s'
                          % (self.authUser, method))
                raise PolicyException('user %r not authorized to call %s'
                                      % (self.authUser, method))

            glo = config['pylons.app_globals']
            tokenclasses = glo.tokenclasses

            if typ in tokenclasses.keys():
                tclass = tokenclasses.get(typ)
                tclt = None
                if serial is not None:
                    toks = getTokens4UserOrSerial(None, serial, _class=False)
                    tokenNum = len(toks)
                    if tokenNum == 1:
                        token = toks[0]
                        ## object method call
                        tclt = newToken(tclass)(token)

                ## static method call
                if tclt is None:
                    tclt = newToken(tclass)
                method = '' + method.strip()
                if hasattr(tclt, method):
                    ret = getattr(tclt, method)(param)
                    if len(ret) == 1:
                        res = ret[0]
                    if len(ret) > 1:
                        res = ret[1]
                else:
                    res['status'] = 'method %s.%s not supported!' % (typ, method)

            Session.commit()
            return sendResult(response, res, 1)

        except PolicyException as pe:
            log.error("policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error("calling method %s.%s of user %s failed! %r"
                      % (typ, method, c.user, e))
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, e, 1)

        finally:
            Session.close()


    @log_with(log)
    def usergetmultiotp(self, action, **params):
        '''
        Using this function the user may receive OTP values for his own tokens.

        method:
            selfservice/getmultiotp

        arguments:
            serial  - the serial number of the token
            count   - number of otp values to return
            curTime - used ONLY for internal testing: datetime.datetime object

        returns:
            JSON response
        '''
        getotp_active = config.get("privacyideaGetotp.active")
        if "True" != getotp_active:
            return sendError(response, "getotp is not activated.", 0)

        param = request.params
        ret = {}

        try:
            serial = getParam(param, "serial", required)
            count = int(getParam(param, "count", required))
            curTime = getParam(param, "curTime", optional)
            timestamp = getParam(param, "timestamp", optional)
            view = getParam(param, "view", optional)

            if (True != isTokenOwner(serial, self.authUser)):
                log.error("The serial %s does not belong to user %s@%s" % (serial, self.authUser.login, self.authUser.realm))
                return sendError(response, "The serial %s does not belong to user %s@%s" % (serial, self.authUser.login, self.authUser.realm), 1)

            max_count = self.Policy.checkPolicyPre('selfservice', 'max_count', param, self.authUser)
            log.debug("checkpolicypre returned %s" % max_count)
            if count > max_count:
                count = max_count



            log.debug("retrieving OTP value for token %s" % serial)
            ret = get_multi_otp(serial, count=int(count), curTime=curTime, timestamp=timestamp)
            ret["serial"] = serial
            c.audit['success'] = True

            Session.commit()
            if view:
                c.ret = ret
                return render('/selfservice/multiotp_view.mako')
            else:
                return sendResult(response, ret , 0)

        except PolicyException as pe:
            log.error("policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error("gettoken/getmultiotp failed: %r" % e)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, u"selfservice/usergetmultiotp failed: %s"
                             % unicode(e), 0)

        finally:
            Session.close()


    @log_with(log)
    def userinit(self, action, **params):
        '''
        When the register motp button is hit, this function is called.
        '''
        response_detail = {}
        param = {}

        try:
            param.update(request.params)

            # check selfservice authorization

            self.Policy.checkPolicyPre('selfservice', 'userinit', param, self.authUser,
                                       options={'token_num':len(getTokens4UserOrSerial(self.authUser))})

            tok_type = getParam(param, "type", required)

            serial = param.get('serial', None)
            prefix = param.get('prefix', None)
            if serial is None or len(serial) == 0:
                serial = genSerial(tok_type, prefix)
                param['serial'] = serial

            desc = getParam(param, "description", optional)
            otppin = getParam(param, "otppin", optional)

            log.info("initialize a token with serial %s "
                     "and type %s by user %s@%s"
                % (serial, tok_type, self.authUser.login, self.authUser.realm))

            log.debug("Initializing the token serial: %s,"
                      " desc: %s, otppin: %s for user %s @ %s." %
            (serial, desc, otppin, self.authUser.login, self.authUser.realm))
            log.debug(param)

            (ret, tokenObj) = initToken(param, self.authUser)
            if tokenObj is not None and hasattr(tokenObj, 'getInfo'):
                info = tokenObj.getInfo()
                response_detail.update(info)

            ## result enrichment - if the token is sucessfully created,
            ## some processing info is added to the result document,
            ##  e.g. the otpkey :-) as qr code
            initDetail = tokenObj.getInitDetail(param, self.authUser)
            response_detail.update(initDetail)

            logTokenNum()
            c.audit['success'] = ret

            # check if we are supposed to genereate a random OTP PIN
            randomPINLength = self.Policy.getRandomOTPPINLength(self.authUser)
            if  randomPINLength > 0:
                newpin = self.Policy.getRandomPin(randomPINLength)
                log.debug("setting random pin for token "
                                                    "with serial %s" % serial)
                # TODO: This random PIN could be processed.
                # TODO: handle result of setPin
                setPin(newpin, None, serial)

            Session.commit()

            ## finally we render the info as qr image, if the qr parameter
            ## is provided and if the token supports this
            if 'qr' in param and tokenObj is not None:
                (rdata, hparam) = tokenObj.getQRImageData(response_detail)
                hparam.update(response_detail)
                hparam['qr'] = param.get('qr') or 'html'
                return sendQRImageResult(response, rdata, hparam)
            else:
                return sendResult(response, ret, opt=response_detail)

        except PolicyException as pe:
            log.error("policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error("token initialization failed! %r" % e)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, e, 1)

        finally:
            Session.close()


    @log_with(log)
    def userwebprovision(self, action, **params):
        '''
        This function is called, when the create OATHtoken button is hit.
        This is used for web provisioning. See:
            http://code.google.com/p/oathtoken/wiki/WebProvisioning
            and
            http://code.google.com/p/google-authenticator/wiki/KeyUriFormat

        in param:
            type: valid values are "oathtoken" and "googleauthenticator" and "googleauthenticator_time"
        It returns the data and the URL containing the HMAC key
        '''
        param = {}

        try:

            ret = {}
            ret1 = False
            ret2 = False
            param.update(request.params)

            # check selfservice authorization
            self.Policy.checkPolicyPre('selfservice', 'userwebprovision', param, self.authUser,
                                       options={'token_num':len(getTokens4UserOrSerial(self.authUser))})

            type = getParam(param, "type", required)

            serial = param.get('serial', None)
            prefix = param.get('prefix', None)

            desc = ""
            #date = datetime.datetime.now().strftime("%y%m%d%H%M%S")
            #rNum = random.randrange(1000, 9999)

            if type.lower() == "oathtoken":
                t_type = 'hmac'
                desc = "OATHtoken web provisioning"

                if prefix is None:
                    prefix = 'LSAO'
                if serial is None:
                    serial = genSerial(t_type, prefix)

                # deal: 32 byte. We could use 20 bytes.
                # we must take care, that the url is not longer than 119 chars.
                # otherwise qrcode.js will fail.Change to 32!
                # Usually the URL is 106 bytes long
                otpkey = generate_otpkey(20)

                log.debug("Initializing the token serial: %s, desc: %s for user %s @ %s." %
                        (serial, desc, self.authUser.login, self.authUser.realm))
                (ret1, tokenObj) = initToken({ 'type': t_type,
                                'serial': serial,
                                'description' : desc,
                                'otpkey' : otpkey,
                                'otplen' : 6,
                                'timeStep' : 30,
                                'timeWindow' : 180,
                                'hashlib' : "sha1"
                                }, self.authUser)

                if ret1:
                    url = create_oathtoken_url(self.authUser.login, self.authUser.realm , otpkey, serial=serial)
                    ret = {
                        'url' : url,
                        'img' : create_img(url, width=300, alt=serial),
                        'key' : otpkey,
                        'name' : serial,
                        'serial' : serial,
                        'timeBased' : False,
                        'counter' : 0,
                        'numDigits': 6,
                        'lockdown' : True
                    }

            elif type.lower() in [ "googleauthenticator", "googleauthenticator_time"]:
                desc	 = "Google Authenticator web prov"

                # ideal: 32 byte.
                otpkey = generate_otpkey(32)
                t_type = "hmac"
                if type.lower() == "googleauthenticator_time":
                    t_type = "totp"

                if prefix is None:
                    prefix = "LSGO"
                if serial is None:
                    serial = genSerial(t_type, prefix)

                log.debug("Initializing the token serial: %s, desc: %s for user %s @ %s." %
                        (serial, desc, self.authUser.login, self.authUser.realm))
                (ret1, tokenObj) = initToken({ 'type': t_type,
                                'serial': serial,
                                'otplen': 6,
                                'description' : desc,
                                'otpkey' : otpkey,
                                'timeStep' : 30,
                                'timeWindow' : 180,
                                'hashlib' : "sha1"
                                }, self.authUser)

                if ret1:
                        url = create_google_authenticator_url(self.authUser.login, self.authUser.realm, otpkey, serial=serial, type=t_type)
                        label = "%s@%s" % (self.authUser.login, self.authUser.realm)
                        ret = {
                            'url' :     url,
                            'img' :     create_img(url, width=300, alt=serial),
                            'key' :     otpkey,
                            'label' :   label,
                            'serial' :  serial,
                            'counter' : 0,
                            'digits':   6,
                        }
            else:
                return sendError(response, "valid types are 'oathtoken' and 'googleauthenticator' and 'googleauthenticator_time'. You provided %s" % type)

            logTokenNum()
            c.audit['serial'] = serial
            # the Google and OATH are always HMAC; sometimes (FUTURE) totp"
            c.audit['token_type'] = "HMAC"
            c.audit['success'] = ret1

            # check if we are supposed to genereate a random OTP PIN
            randomPINLength = self.Policy.getRandomOTPPINLength(self.authUser)
            if  randomPINLength > 0:
                newpin = self.Policy.getRandomPin(randomPINLength)
                log.debug("setting random pin for token with serial %s" % serial)
                ret2 = setPin(newpin, None, serial)
                # TODO: This random PIN could be processed.

            Session.commit()
            return sendResult(response, { 'init': ret1, 'setpin' : ret2, 'oathtoken' : ret})

        except PolicyException as pe:
            log.error("policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error("token initialization failed! %r" % e)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, e, 1)

        finally:
            Session.close()


##
    @log_with(log)
    def userfinshocratoken(self, action, **params):
        '''

        userfinshocratoken - called from the selfservice web ui to finish the  OCRA token to
                             run the final check_t for the token

        :param passw: the calculated verificaton otp
        :type  passw: string
        :param transactionid: the transactionid
        :type  transactionid: string

        :return:    dict about the token
        :rtype:     { 'result' = ok
                      'failcount' = int(failcount)
                    }

        '''
        param = request.params

        try:
            ''' check selfservice authorization '''

            self.Policy.checkPolicyPre('selfservice', 'userwebprovision',
                                                    param, self.authUser)

            transid = getParam(param, 'transactionid', required)
            passw = getParam(param, 'pass', required)
            p_serial = getParam(param, 'serial', optional)

            value = {}

            ocraChallenge = OcraTokenClass.getTransaction(transid)
            if ocraChallenge is None:
                error = ('[userfinshocratoken] No challenge for transaction'
                            ' %s found' % unicode(transid))
                log.error(error)
                raise SelfserviceException(error)

            serial = ocraChallenge.tokenserial
            if serial != p_serial:
                error = ('[userfinshocratoken] token mismatch for token '
                      'serial: %s - %s' % (unicode(serial), unicode(p_serial)))
                log.error(error)
                raise SelfserviceException(error)

            tokens = getTokens4UserOrSerial(serial=serial)
            if len(tokens) == 0 or len(tokens) > 1:
                error = ('[userfinshocratoken] no token found for '
                         'serial: %s' % (unicode(serial)))
                log.error(error)
                raise SelfserviceException(error)

            theToken = tokens[0]
            tok = theToken.token
            desc = tok.get()
            realms = desc.get('privacyIDEA.RealmNames')
            if realms is None or len(realms) == 0:
                realm = getDefaultRealm()
            elif len(realms) > 0:
                realm = realms[0]

            userInfo = getUserInfo(tok.privacyIDEAUserid, tok.privacyIDEAIdResolver,
                                                        tok.privacyIDEAIdResClass)
            user = User(login=userInfo.get('username'), realm=realm)

            (ok, opt) = checkSerialPass(serial, passw, user=user,
                                            options={'transactionid': transid})

            failcount = tokens[0].getFailCount()
            typ = tokens[0].type

            value['result'] = ok
            value['failcount'] = int(failcount)

            c.audit['transactionid'] = transid
            c.audit['token_type'] = typ
            c.audit['success'] = value.get('result')

            Session.commit()
            return sendResult(response, value, opt)

        except PolicyException as pe:
            log.error("policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            error = "[userfinshocratoken] token initialization failed! %r" % e
            log.error(traceback.format_exc())
            log.error(error)
            Session.rollback()
            return sendError(response, error, 1)

        finally:
            Session.close()



##--
    @log_with(log)
    def userfinshocra2token(self, action, **params):
        '''

        userfinshocra2token - called from the selfservice web ui to finish
                        the OCRA2 token to run the final check_t for the token

        :param passw: the calculated verificaton otp
        :type  passw: string
        :param transactionid: the transactionid
        :type  transactionid: string

        :return:    dict about the token
        :rtype:     { 'result' = ok
                      'failcount' = int(failcount)
                    }

        '''
        param = {}
        param.update(request.params)
        if 'session' in param:
            del param['session']

        value = {}
        ok = False
        typ = ''

        try:
            ''' check selfservice authorization '''

            self.Policy.checkPolicyPre('selfservice', 'userwebprovision',
                                                        param, self.authUser)
            passw = getParam(param, "pass", required)

            transid = param.get('state', None)
            if transid is not None:
                param['transactionid'] = transid
                del param['state']

            if transid is None:
                transid = param.get('transactionid', None)

            if transid is None:
                raise SelfserviceException("missing parameter: state or transactionid!")

            serial = get_tokenserial_of_transaction(transId=transid)
            if serial is None:
                value['value'] = False
                value['failure'] = 'No challenge for transaction %r found'\
                                    % transid

            else:
                param['serial'] = serial

                tokens = getTokens4UserOrSerial(serial=serial)
                if len(tokens) == 0 or len(tokens) > 1:
                    raise SelfserviceException('tokenmismatch for token serial: %s'
                                    % (unicode(serial)))

                theToken = tokens[0]
                tok = theToken.token
                typ = theToken.getType()
                realms = tok.getRealmNames()
                if realms is None or len(realms) == 0:
                    realm = getDefaultRealm()
                elif len(realms) > 0:
                    realm = realms[0]

                userInfo = getUserInfo(tok.privacyIDEAUserid, tok.privacyIDEAIdResolver, tok.privacyIDEAIdResClass)
                user = User(login=userInfo.get('username'), realm=realm)

                (ok, opt) = checkSerialPass(serial, passw, user=user,
                                     options=param)

                value['value'] = ok
                failcount = theToken.getFailCount()
                value['failcount'] = int(failcount)

            value['result'] = ok
            value['failcount'] = int(failcount)

            c.audit['transactionid'] = transid
            c.audit['token_type'] = typ
            c.audit['success'] = value.get('result')

            Session.commit()
            return sendResult(response, value, opt)

        except PolicyException as pe:
            log.error("policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            error = "token initialization failed! %r" % e
            log.error(traceback.format_exc())
            log.error(error)
            Session.rollback()
            return sendError(response, error, 1)

        finally:
            Session.close()


    @log_with(log)
    def useractivateocratoken(self, action, **params):
        '''

        useractivateocratoken - called from the selfservice web ui to activate the  OCRA token

        :param type:    'ocra'
        :type type:     string
        :param serial:    serial number of the token
        :type  serial:    string
        :param activationcode: the calculated activation code
        :type  activationcode: string - activationcode format

        :return:    dict about the token
        :rtype:     { 'activate': True, 'ocratoken' : {
                        'url' :     url,
                        'img' :     '<img />',
                        'label' :   "%s@%s" % (self.authUser.login,
                                                   self.authUser.realm),
                        'serial' :  serial,
                    }  }
        '''
        param = {}
        ret = {}

        try:
            param.update(request.params)

            # check selfservice authorization
            self.Policy.checkPolicyPre('selfservice', 'useractivateocratoken',
                                                    param, self.authUser)

            typ = getParam(param, "type", required)
            if typ.lower() not in ["ocra", "ocra2"]:
                return sendError(response, "valid types are 'ocra'. "
                                                    "You provided %s" % typ)

            helper_param = {}
            helper_param['type'] = typ
            helper_param['serial'] = getParam(param, "serial", required)

            acode = getParam(param, "activationcode", required)
            helper_param['activationcode'] = acode.upper()

            helper_param['genkey'] = getParam(param, "genkey", required)

            (ret, tokenObj) = initToken(helper_param, self.authUser)

            info = {}
            serial = ""
            if tokenObj is not None:
                info = tokenObj.getInfo()
                serial = tokenObj.getSerial()
            else:
                raise SelfserviceException('Token not found!')

            url = info.get('app_import')
            trans = info.get('transactionid')

            ret = {
                'url'       : url,
                'img'       : create_img(url, width=400, alt=url),
                'label'     : "%s@%s" % (self.authUser.login,
                                            self.authUser.realm),
                'serial'    : serial,
                'transaction' : trans,
            }

            logTokenNum()

            c.audit['serial'] = serial
            c.audit['token_type'] = typ
            c.audit['success'] = True

            Session.commit()
            return sendResult(response, {'activate': True, 'ocratoken': ret})

        except PolicyException as pe:
            log.error("policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error("token initialization failed! %r"
                      % e)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, e, 1)

        finally:
            Session.close()


@log_with(log)
def add_dynamic_selfservice_enrollment(actions):
    '''
        add_dynamic_actions - load the html of the dynamic tokens
            according to the policy definition

        :param actions: the allowd policy actions for the current scope
        :type  actions: array of actions names

        :return: hash of {tokentype : html for tab}
    '''

    dynanmic_actions = {}
    g = config['pylons.app_globals']
    tokenclasses = g.tokenclasses

    for tok in tokenclasses.keys():
        tclass = tokenclasses.get(tok)
        tclass_object = newToken(tclass)
        if hasattr(tclass_object, 'getClassInfo'):

            try:
                selfservice = tclass_object.getClassInfo('selfservice', ret=None)
                ## check if we have a policy in the token definition for the enroll
                if selfservice.has_key('enroll') and 'enroll' + tok.upper() in actions:
                    service = selfservice.get('enroll')
                    tab = service.get('title')
                    c.scope = tab.get('scope')
                    t_file = tab.get('html')
                    t_html = render(t_file)
                    ''' remove empty lines '''
                    t_html = '\n'.join([line for line in t_html.split('\n') if line.strip() != ''])
                    e_name = "%s.%s.%s" % (tok, 'selfservice', 'enroll')
                    dynanmic_actions[e_name] = t_html

                ## check if there are other selfserive policy actions
                policy = tclass_object.getClassInfo('policy', ret=None)
                if 'selfservice' in policy:
                    selfserv_policies = policy.get('selfservice').keys()
                    for action in actions:
                        if action in selfserv_policies:
                            ## now lookup, if there is an additional section
                            ## in the selfservice to render
                            service = selfservice.get(action)
                            tab = service.get('title')
                            c.scope = tab.get('scope')
                            t_file = tab.get('html')
                            t_html = render(t_file)
                            ''' remove empty lines '''
                            t_html = '\n'.join([line for line in t_html.split('\n') if line.strip() != ''])
                            e_name = "%s.%s.%s" % (tok, 'selfservice', action)
                            dynanmic_actions[e_name] = t_html


            except Exception as e:
                log.info('no policy for tokentype '
                         '%s found (%r)' % (unicode(tok), e))

    return dynanmic_actions


@log_with(log)
def add_dynamic_selfservice_policies(actions):
    '''
        add_dynamic_actions - load the html of the dynamic tokens
            according to the policy definition

        :param actions: the allowd policy actions for the current scope
        :type  actions: array of actions names

        :return: hash of {tokentype : html for tab}
    '''

    dynamic_policies = []
    g = config['pylons.app_globals']
    tokenclasses = g.tokenclasses


    defined_policies = []

    for tok in tokenclasses.keys():
        tclass = tokenclasses.get(tok)
        tclt = newToken(tclass)
        if hasattr(tclt, 'getClassInfo'):
            ## check if we have a policy in the token definition
            try:
                policy = tclt.getClassInfo('policy', ret=None)
                if policy is not None and policy.has_key('selfservice'):
                    scope_policies = policy.get('selfservice').keys()
                    ''' initialize the policies '''
                    if len(defined_policies) == 0:
                        for pol in actions:
                            if '=' in pol:
                                (name, val) = pol.split('=')
                                defined_policies.append(name)

                    for local_policy in scope_policies:
                        if local_policy not in defined_policies:
                            dynamic_policies.append(local_policy)
            except Exception as e:
                log.info('no policy for tokentype '
                         '%s found (%r)' % (unicode(tok), e))

    return dynamic_policies

def add_local_policies():

    return

#eof##########################################################################

