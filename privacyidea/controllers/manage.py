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
This file is part of the privacyidea service
In provides the web gui management interface
'''


import os

# In python 2.6 included
# We do not support python 2.5!
import json

from pylons import request, response, config, tmpl_context as c
from privacyidea.lib.base import BaseController
from pylons.templating import render_mako as render
from mako.exceptions import CompileException
from mako.template import Template

# Our Token stuff
from privacyidea.lib.token   import TokenIterator
from privacyidea.lib.token   import getTokenType
from privacyidea.lib.token   import newToken


from privacyidea.lib.user    import getUserFromParam, getUserFromRequest
from privacyidea.lib.user    import getUserList, User

from privacyidea.lib.util    import getParam
from privacyidea.lib.util    import get_version
from privacyidea.lib.util    import get_copyright_info
from privacyidea.lib.reply   import sendError

from privacyidea.lib.util    import remove_empty_lines
from privacyidea.weblib.util import get_client
from privacyidea.model.meta import Session
from privacyidea.lib.token import get_token_type_list
from privacyidea.lib.token import get_policy_definitions
from privacyidea.lib.policy import PolicyClass, PolicyException
from privacyidea.lib.config import get_privacyIDEA_config
from pylons.i18n.translation import _
from privacyidea.lib.log import log_with
import webob
import traceback
import logging

log = logging.getLogger(__name__)

EnterpriseEdition = False
KNOWN_TYPES = []
IMPORT_TEXT = {}
ENCODING = "utf-8"



optional = True
required = False

class ManageController(BaseController):

    @log_with(log)
    def __before__(self, action, **params):

        try:           
            c.audit['success'] = False
            c.audit['client'] = get_client()
            self.set_language()

            c.version = get_version()
            c.licenseinfo = get_copyright_info()
            self.Policy = PolicyClass(request, config, c,
                                      get_privacyIDEA_config(),
                                      token_type_list = get_token_type_list())
            c.polDefs = get_policy_definitions()

            self.before_identity_check(action)

            c.tokenArray = []
            c.user = self.authUser.login
            c.realm = self.authUser.realm

        except webob.exc.HTTPUnauthorized as acc:
            ## the exception, when an abort() is called if forwarded
            log.info("%r webob.exception %r" % (action, acc))
            log.info(traceback.format_exc())
            Session.rollback()
            Session.close()
            raise acc

        except Exception as exx:
            log.error("exception %r" % (action, exx))
            log.error(traceback.format_exc())
            Session.rollback()
            Session.close()
            return sendError(response, exx, context='before')

        finally:
            pass


    @log_with(log)
    def __after__(self, action, **params):

        if c.audit['action'] in [ 'manage/tokenview_flexi',
                                'manage/userview_flexi' ]:
            c.audit['administrator'] = getUserFromRequest(request).get("login")
            if request.params.has_key('serial'):
                    c.audit['serial'] = request.params['serial']
                    c.audit['token_type'] = getTokenType(request.params['serial'])

            self.audit.log(c.audit)


    @log_with(log)
    def index(self, action, **params):
        '''
        This is the main function of the management web UI
        '''

        try:
            c.title = "privacyIDEA Management"
            admin_user = getUserFromRequest(request)
            if admin_user.has_key('login'):
                c.admin = admin_user['login']

            log.debug("importers: %s" % IMPORT_TEXT)
            c.importers = IMPORT_TEXT

            ## add render info for token type config
            confs = _getTokenTypeConfig('config')
            token_config_tab = {}
            token_config_div = {}
            for conf in confs:
                tab = ''
                div = ''
                try:
                    #loc = conf +'_token_settings'
                    tab = confs.get(conf).get('title')
                    #tab = '<li ><a href=#'+loc+'>'+tab+'</a></li>'

                    div = Template(confs.get(conf).get('html')).render()
                    #div = +div+'</div>'
                except Exception as e:
                    log.debug('no config info for token type %s  (%r)' % (conf, e))

                if tab is not None and div is not None and len(tab) > 0 and len(div) > 0:
                    token_config_tab[conf] = tab
                    token_config_div[conf] = div

            c.token_config_tab = token_config_tab
            c.token_config_div = token_config_div

            ##  add the enrollment fragments from the token definition
            ##  tab: <option value="ocra">${_("OCRA - challenge/response Token")}</option>
            ##  div: "<div id='"+ tt + "'>"+enroll+"</div>"
            enrolls = _getTokenTypeConfig('init')

            token_enroll_tab = {}
            token_enroll_div = {}
            for conf in enrolls:
                tab = ''
                div = ''
                try:
                    tab = enrolls.get(conf).get('title')
                    div = enrolls.get(conf).get('html')
                except Exception as e:
                    log.debug('no enrollment info for token type %s  (%r)' % (conf, e))

                if tab is not None and div is not None and len(tab) > 0 and len(div) > 0:
                    token_enroll_tab[conf] = tab
                    token_enroll_div[conf] = div

            c.token_enroll_tab = token_enroll_tab
            c.token_enroll_div = token_enroll_div

            c.tokentypes = _getTokenTypes()

            http_host = request.environ.get("HTTP_HOST")
            url_scheme = request.environ.get("wsgi.url_scheme")
            c.logout_url = "%s://%s/account/logout" % (url_scheme, http_host)

            Session.commit()
            ren = render('/manage/start.mako')
            return ren

        except PolicyException as pe:
            log.error("Error during checking policies: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as ex:
            log.error("failed! %r" % ex)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, ex)

        finally:
            Session.close()

            
##### TODO: CKO: remove it. It is not used
#
#    def tokentype(self):
#        '''
#        '''
#        c.title = 'TokenTypeInfo'
#        g = config['pylons.app_globals']
#        tokens = g.tokenclasses
#        ttinfo = []
#        ttinfo.extend(tokens.keys())
#        for tok in tokens:
#            tclass = tokens.get(tok)
#            tclass_object = newToken(tclass)
#            if hasattr(tclass_object, 'getClassType'):
#                ii = tclass_object.getClassType()
#                ttinfo.append(ii)
#
#        c.tokeninfo = ttinfo
#
#        return render('/manage/tokentypeinfo.mako')

    def policies(self):
        '''
        This is the template for the policies TAB
        '''
        c.title = "privacyIDEA Management - Policies"
        return render('/manage/policies.mako')

    def machines(self):
        '''
        This is the template for the policies TAB
        '''
        c.title = "privacyIDEA Management - Machines"
        return render('/manage/machines.mako')

    def audittrail(self):
        '''
        This is the template for the audit trail TAB
        '''
        c.title = "privacyIDEA Management - Audit Trail"
        return render('/manage/audit.mako')


    def tokenview(self):
        '''
        This is the template for the token TAB
        '''
        c.title = "privacyIDEA Management"
        c.tokenArray = []
        return render('/manage/tokenview.mako')


    def userview(self):
        '''
        This is the template for the token TAB
        '''
        c.title = "privacyIDEA Management"
        c.tokenArray = []
        return render('/manage/userview.mako')

    def custom_style(self):
        '''
        If this action was called, the user hasn't created a custom-style.css yet. To avoid hitting
        the debug console over and over, we serve an empty file.
        '''
        response.headers['Content-type'] = 'text/css'
        return ''

    @log_with(log)
    def tokenview_flexi(self, action, **params):
        '''
        This function is used to fill the flexigrid.
        Unlike the complex /admin/show function, it only returns a
        simple array of the tokens.
        '''
        param = request.params

        try:
            #serial  = getParam(param,"serial",optional)
            c.page = getParam(param, "page", optional)
            c.filter = getParam(param, "query", optional)
            c.qtype = getParam(param, "qtype", optional)
            c.sort = getParam(param, "sortname", optional)
            c.dir = getParam(param, "sortorder", optional)
            c.psize = getParam(param, "rp", optional)

            filter_all = None
            filter_realm = None
            user = User()

            if c.qtype == "loginname":
                if "@" in c.filter:
                    (login, realm) = c.filter.split("@")
                    user = User(login, realm)
                else:
                    user = User(c.filter)

            elif c.qtype == "all":
                filter_all = c.filter
            elif c.qtype == "realm":
                filter_realm = c.filter

            # check admin authorization
            res = self.Policy.checkPolicyPre('admin', 'show', param , user=user)

            filterRealm = res['realms']
            # check if policies are active at all
            # If they are not active, we are allowed to SHOW any tokens.
            pol = self.Policy.getAdminPolicies("show")
            # If there are no admin policies, we are allowed to see all realms
            if not pol['active']:
                filterRealm = ["*"]

            # check if we only want to see ONE realm or see all realms we are allowerd to see.
            if filter_realm:
                if filter_realm in filterRealm or '*' in filterRealm:
                    filterRealm = [filter_realm]

            log.debug("admin >%s< may display the following realms: %s" % (pol['admin'], pol['realms']))
            log.debug("page: %s, filter: %s, sort: %s, dir: %s" % (c.page, c.filter, c.sort, c.dir))

            if c.page is None:
                c.page = 1
            if c.psize is None:
                c.psize = 20

            log.debug("calling TokenIterator for user=%s@%s, filter=%s, filterRealm=%s"
                        % (user.login, user.realm, filter_all, filterRealm))
            c.tokenArray = TokenIterator(user, None, c.page , c.psize, filter_all, c.sort, c.dir, filterRealm=filterRealm)
            c.resultset = c.tokenArray.getResultSetInfo()
            # If we have chosen a page to big!
            lines = []
            for tok in c.tokenArray:
                lines.append(
                    { 'id' : tok['privacyIDEA.TokenSerialnumber'],
                        'cell': [
                            tok['privacyIDEA.TokenSerialnumber'],
                            tok['privacyIDEA.Isactive'],
                            tok['User.username'],
                            tok['privacyIDEA.RealmNames'],
                            tok['privacyIDEA.TokenType'],
                            tok['privacyIDEA.FailCount'],
                            tok['privacyIDEA.TokenDesc'],
                            tok['privacyIDEA.MaxFail'],
                            tok['privacyIDEA.OtpLen'],
                            tok['privacyIDEA.CountWindow'],
                            tok['privacyIDEA.SyncWindow'],
                            tok['privacyIDEA.Userid'],
                            tok['privacyIDEA.IdResolver'], ]
                    }
                    )

            # We need to return 'page', 'total', 'rows'
            response.content_type = 'application/json'
            res = { "page": int(c.page),
                "total": c.resultset['tokens'],
                "rows": lines }

            c.audit['success'] = True

            Session.commit()
            return json.dumps(res, indent=3)

        except PolicyException as pe:
            log.error("Error during checking policies: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error("failed: %r" % e)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, e)

        finally:
            Session.close()


    @log_with(log)
    def userview_flexi(self, action, **params):
        '''
        This function is used to fill the flexigrid.
        Unlike the complex /admin/userlist function, it only returns a
        simple array of the tokens.
        '''
        param = request.params

        try:
            #serial  = getParam(param,"serial",optional)
            c.page = getParam(param, "page", optional)
            c.filter = getParam(param, "query", optional)
            qtype = getParam(param, "qtype", optional)
            c.sort = getParam(param, "sortname", optional)
            c.dir = getParam(param, "sortorder", optional)
            c.psize = getParam(param, "rp", optional)
            c.realm = getParam(param, "realm", optional)

            user = getUserFromParam(param, optional)
            # check admin authorization
            # check if we got a realm or resolver, that is ok!
            self.Policy.checkPolicyPre('admin', 'userlist', { 'user': "dummy", 'realm' : c.realm })

            if c.filter == "":
                c.filter = "*"

            log.debug("page: %s, filter: %s, sort: %s, dir: %s"
                      % (c.page, c.filter, c.sort, c.dir))

            if c.page is None:
                c.page = 1
            if c.psize is None:
                c.psize = 20

            c.userArray = getUserList({ qtype:c.filter,
                                       'realm':c.realm }, user)
            c.userNum = len(c.userArray)

            lines = []
            for u in c.userArray:
                # shorten the useridresolver, to get a better display value
                resolver_display = ""
                if "useridresolver" in u:
                    if len(u['useridresolver'].split(".")) > 3:
                        resolver_display = u['useridresolver'].split(".")[-1] + " (" + u['useridresolver'].split(".")[-3] + ")"
                    else:
                        resolver_display = u['useridresolver']
                lines.append(
                    { 'id' : u['username'],
                        'cell': [
                            (u['username']) if u.has_key('username') else (""),
                            (resolver_display),
                            (u['surname']) if u.has_key('surname') else (""),
                            (u['givenname']) if u.has_key('givenname') else (""),
                            (u['email']) if u.has_key('email') else (""),
                            (u['mobile']) if u.has_key('mobile') else (""),
                            (u['phone']) if u.has_key('phone') else (""),
                            (u['userid']) if u.has_key('userid') else (""),
                             ]
                    }
                    )

            # sorting
            reverse = False
            sortnames = { 'username' : 0, 'useridresolver' : 1,
                    'surname' : 2, 'givenname' : 3, 'email' : 4,
                    'mobile' :5, 'phone' : 6, 'userid' : 7 }
            if c.dir == "desc":
                reverse = True
            lines = sorted(lines, key=lambda user: user['cell'][sortnames[c.sort]] , reverse=reverse)
            # end: sorting

            # reducing the page
            if c.page and c.psize:
                page = int(c.page)
                psize = int(c.psize)
                start = psize * (page - 1)
                end = start + psize
                lines = lines[start:end]

            # We need to return 'page', 'total', 'rows'
            response.content_type = 'application/json'
            res = { "page": int(c.page),
                "total": c.userNum,
                "rows": lines }

            c.audit['success'] = True

            Session.commit()
            return json.dumps(res, indent=3)

        except PolicyException as pe:
            log.error("Error during checking policies: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error("failed: %r" % e)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, e)

        finally:
            Session.close()


    @log_with(log)
    def tokeninfo(self, action, **params):
        '''
        this returns the contents of /admin/show?serial=xyz in a html format
        '''
        param = request.params

        try:
            serial = getParam(param, 'serial', required)

            filterRealm = ""
            # check admin authorization
            res = self.Policy.checkPolicyPre('admin', 'show', param)

            filterRealm = res['realms']
            # check if policies are active at all
            # If they are not active, we are allowed to SHOW any tokens.
            pol = self.Policy.getAdminPolicies("show")
            if not pol['active']:
                filterRealm = ["*"]

            log.info("admin >%s< may display the following realms: %s" % (res['admin'], filterRealm))
            log.info("displaying tokens: serial: %s", serial)

            toks = TokenIterator(User("", "", ""), serial, filterRealm=filterRealm)

            ### now row by row
            lines = []
            for tok in toks:
                lines.append(tok)
            if len(lines) > 0:

                c.tokeninfo = lines[0]
            else:
                c.tokeninfo = {}

            for k in c.tokeninfo:
                if "privacyIDEA.TokenInfo" == k:
                    try:
                        # Try to convert string to Dictionary
                        c.tokeninfo['privacyIDEA.TokenInfo'] = json.loads(c.tokeninfo['privacyIDEA.TokenInfo'])
                    except:
                        pass

            return render('/manage/tokeninfo.mako')

        except PolicyException as pe:
            log.error("Error during checking policies: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error("failed! %r" % e)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, e)

        finally:
            Session.close()



############################################################
def _getTokenTypes():
    '''
        _getTokenTypes - retrieve the list of dynamic tokens and their title section

        :return: dict with token type and title
        :rtype:  dict
    '''

    glo = config['pylons.app_globals']
    tokenclasses = glo.tokenclasses

    tokens = []
    tokens.extend(tokenclasses.keys())

    tinfo = {}
    for tok in tokens:
        if tok in tokenclasses.keys():
            tclass = tokenclasses.get(tok)
            tclass_object = newToken(tclass)
            if hasattr(tclass_object, 'getClassInfo'):
                ii = tclass_object.getClassInfo('title') or tok
                tinfo[tok] = _(ii)

    return tinfo


def _getTokenTypeConfig(section='config'):
    '''
        _getTokenTypeConfig - retrieve from the dynamic token the
                            tokentype section, eg. config or enroll

        :param section: the section of the tokentypeconfig
        :type  section: string

        :return: dict with tab and page definition (rendered)
        :rtype:  dict
    '''

    res = {}

    g = config['pylons.app_globals']
    tokenclasses = g.tokenclasses

    for tok in tokenclasses.keys():
        tclass = tokenclasses.get(tok)
        tclass_object = newToken(tclass)
        if hasattr(tclass_object, 'getClassInfo'):

            conf = tclass_object.getClassInfo(section, ret={})

            ## set globale render scope, so that the mako
            ## renderer will return only a subsection from the template
            p_html = ''
            t_html = ''
            try:
                page = conf.get('page')
                c.scope = page.get('scope')
                p_html = render(os.path.sep + page.get('html'))
                p_html = remove_empty_lines(p_html)

                tab = conf.get('title')
                c.scope = tab.get('scope')
                t_html = render(os.path.sep + tab.get('html'))
                t_html = remove_empty_lines(t_html)

            except CompileException as ex:
                log.error("compile error while processing %r.%r:" % (tok, section))
                log.error(ex)
                log.error(traceback.format_exc())
                raise Exception(ex)

            except Exception as e:
                log.debug('no config for token type %r (%r)' % (tok, e))
                p_html = ''

            if len (p_html) > 0:
                res[tok] = { 'html' : p_html, 'title' : t_html}

    return res

############################################################

