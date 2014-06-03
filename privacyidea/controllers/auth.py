import logging


from pylons             import tmpl_context as c
from privacyidea.lib.base    import BaseController
from pylons.templating  import render_mako as render
from privacyidea.lib.util    import get_version
from privacyidea.lib.util    import get_copyright_info
from privacyidea.lib.reply import sendError

from pylons import response
from privacyidea.model.meta import Session
from privacyidea.lib.log import log_with

import traceback

log = logging.getLogger(__name__)

optional = True
required = False


class AuthController(BaseController):


    @log_with(log)
    def __before__(self, action, **params):

        try:

            c.version = get_version()
            c.licenseinfo = get_copyright_info()
            self.set_language()

        except Exception as exx:
            log.error("%r exception %r" % (action, exx))
            log.error(traceback.format_exc())
            Session.rollback()
            Session.close()
            return sendError(response, exx, context='before')

        finally:
            pass


    def index(self):
        '''
        This is the method for testing authentication

        Call it directly in your browser like this
            http(s)://server/auth/index
        '''
        log.debug("index, authenticating user")
        return render("/auth.mako")


    def index3(self):
        '''
        This is the method for testing authentication

        Call it directly in your browser like this
            http(s)://server/auth/index3
        '''
        log.debug("index, authenticating user")
        return render("/auth3.mako")


    def requestsms(self):
        '''
        This is the method for requesting the sending of SMS

        Call it directly in your browser like this
            http(s)://server/auth/requestsms
        '''
        log.debug("authenticating user")
        return render("/auth-sms.mako")


    def ocra(self):
        '''
        This is the method for testing ocra tokens

        Call it directly in your browser like this
            http(s)://server/auth/ocra
        '''
        log.debug("authenticating user")
        return render("/auth-ocra.mako")


    def ocra2(self):
        '''
        This is the method for testing ocra2 tokens

        Call it directly in your browser like this
            http(s)://server/auth/ocra2
        '''
        log.debug("authenticating user")
        return render("/auth-ocra2.mako")


#eof##########################################################################

