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
'''This file is part of the privacyidea service
'''


import logging


from pylons import tmpl_context as c
from pylons import request, response, config
from privacyidea.lib.base import BaseController

from privacyidea.lib.user import  getUserFromRequest
from privacyidea.lib.policy import PolicyClass, PolicyException

from privacyidea.lib.reply import sendError
from privacyidea.lib.audit import CSVAuditIterator
from privacyidea.lib.audit import JSONAuditIterator
from privacyidea.lib.token import get_token_type_list
from privacyidea.lib.util import getParam
from privacyidea.weblib.util import get_client
from privacyidea.lib.config import get_privacyIDEA_config
from privacyidea.model.meta import Session
from privacyidea.lib.log import log_with

ENCODING = "utf-8"
import traceback


optional = True
required = False

log = logging.getLogger(__name__)


class AuditController(BaseController):

    '''
    this is the controller for doing some audit stuff

        https://server/audit/<functionname>

    '''

    @log_with(log)
    def __before__(self, action, **params):

        try:
            c.audit['client'] = get_client()
            self.before_identity_check(action)
            
        except Exception as exx:
            log.error("%r exception %r" % (action, exx))
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, exx, context='before')

        finally:
            Session.close()
            
    @log_with(log)
    def __after__(self, action, **params):
        try:
            c.audit['administrator'] = getUserFromRequest(request).get("login")
            self.audit.log(c.audit)
        finally:
            Session.close()

    @log_with(log)
    def search(self, action, **params):

        '''
        This functions searches within the audit trail
        It returns the audit information for the given search pattern

        method:
            audit/search

        arguments:
            key, value pairs as search patterns.

            * outform - optional: if set to "csv", than the token list will be
                        given in CSV


            or: Usually the key=values will be locally AND concatenated.
                it a parameter or=true is passed, the filters will
                be OR concatenated.

            The Flexigrid provides us the following parameters:
                ('page', u'1'), ('rp', u'100'),
                ('sortname', u'number'),
                ('sortorder', u'asc'),
                ('query', u''), ('qtype', u'serial')]
        returns:
            JSON response or csv format
        '''

        param = {}
        try:
            param.update(request.params)

            output_format = getParam(param, "outform", optional)
            Policy = PolicyClass(request, config, c,
                                 get_privacyIDEA_config(),
                                 token_type_list = get_token_type_list())
            Policy.checkPolicyPre('audit', 'view', {})

            # remove the param outform (and other parameters that should not
            # be used for search!
            search_params = {}
            for p in param:
                if p not in ["outform"]:
                    search_params[p] = param[p]

            log.debug("search params %r" % search_params)

            audit_iter = None

            if output_format == "csv":
                filename = "privacyidea-audit.csv"
                response.content_type = "application/force-download"
                response.headers['Content-disposition'] = (
                                        'attachment; filename=%s' % filename)
                audit_iter = CSVAuditIterator(search_params)
            else:
                response.content_type = 'application/json'
                audit_iter = JSONAuditIterator(search_params)

            c.audit['success'] = True
            Session.commit()
            return audit_iter

        except PolicyException as pe:
            log.error("gettoken/getotp policy failed: %r" % pe)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, unicode(pe), 1)

        except Exception as e:
            log.error("audit/search failed: %r" % e)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, "audit/search failed: %s" % unicode(e), 0)

        finally:
            Session.close()


#eof###########################################################################
