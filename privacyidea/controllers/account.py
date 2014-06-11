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
'''
import traceback

from pylons import request, response, tmpl_context as c
from pylons.controllers.util import abort, redirect

from privacyidea.lib.base import BaseController
from pylons.templating import render_mako as render

from privacyidea.lib.reply   import sendError
from privacyidea.model.meta  import Session

from privacyidea.lib.util    import get_version
from privacyidea.lib.util    import get_copyright_info
from privacyidea.lib.account import is_admin_identity

from privacyidea.lib.realm    import getRealms
from privacyidea.lib.realm    import getDefaultRealm
from privacyidea.lib.user     import getRealmBox
from privacyidea.lib.log import log_with

import logging
import webob


log = logging.getLogger(__name__)


optional = True
required = False

# The HTTP status code, that determines that
# the Login to the selfservice portal is required.
# Is also defined in selfservice.js
LOGIN_CODE = 576

class AccountController(BaseController):
    '''
    The AccountController
        /account/
    is responsible for authenticating the users for the selfservice portal.
    It has the following functions:
        /account/login
        /account/dologin
    '''


    @log_with(log)
    def __before__(self, action, **params):

        try:
            self.set_language()
            c.version = get_version()
            c.licenseinfo = get_copyright_info()

        except webob.exc.HTTPUnauthorized as acc:
            ## the exception, when an abort() is called if forwarded
            log.error("%r webob.exception %r" % (action, acc))
            log.error(traceback.format_exc())
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


    def login(self, action):
        log.debug("privacyidea login screen")
        identity = request.environ.get('repoze.who.identity')
        if identity is not None:
            # After login we either redirect to the manage interface or selfservice
            if is_admin_identity(identity, exception=False):
                redirect("/manage/")
            else:
                redirect("/")

        res = {}
        try:
            c.defaultRealm = getDefaultRealm()
            res = getRealms()

            c.realmArray = ["admin"]
            for (k, _v) in res.items():
                c.realmArray.append(k)                

            c.realmbox = getRealmBox()
            log.debug("displaying realmbox: %i" % int(c.realmbox))

            #TODO: How can we distinguish between failed login and first arrival.
            #c.status = _("Wrong credentials.")

            Session.commit()
            response.status = '%i Logout from privacyIDEA selfservice' % LOGIN_CODE
            return render('/selfservice/login.mako')

        except Exception as e:
            log.error('failed %r' % e)
            log.error(traceback.format_exc())
            Session.rollback()
            return sendError(response, e)

        finally:
            Session.close()


#eof##########################################################################

