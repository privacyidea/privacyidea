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

import cgi

from paste.urlparser    import PkgResourcesParser
from pylons             import request
from pylons.middleware  import error_document_template

from pylons.controllers.util import forward
from webhelpers.html.builder import literal

from privacyidea.lib.base    import BaseController


class ErrorController(BaseController):

    def document(self):
        """Render the error document"""
        resp = request.environ.get('pylons.original_response')
        if resp is not None:
            content = literal(resp.body)
        else:
            content = cgi.escape(request.GET.get('message', ''))

        page = error_document_template % \
            dict(prefix=request.environ.get('SCRIPT_NAME', ''),
                 code=cgi.escape(request.GET.get('code', unicode(resp.status_int))),
                 message=content)
        return page


    def img(self, id):
        """Serve Pylons' stock images"""
        return self._serve_file('/'.join(['media/img', id]))


    def style(self, id):
        """Serve Pylons' stock stylesheets"""
        return self._serve_file('/'.join(['media/style', id]))


    def _serve_file(self, path):
        """Call Paste's FileApp (a WSGI application) to serve the file
        at the specified path
        """
        request.environ['PATH_INFO'] = '/%s' % path
        return forward(PkgResourcesParser('pylons', 'pylons'))


#eof###########################################################################

