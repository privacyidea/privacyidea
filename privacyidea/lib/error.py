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
"""
contains Errors and Exceptions
"""

from gettext import gettext as _
import logging
log = logging.getLogger(__name__)


class privacyIDEAError(Exception):

    def __init__(self, description=u"privacyIDEAError!", id=10):
        self.id = id
        self.message = description
        Exception.__init__(self, description)

    def getId(self):
        return self.id

    def getDescription(self):
        return self.message

    def __unicode__(self):
        pstr = u"ERR%d: %r"
        if type(self.message) in [str, unicode]:
            pstr = u"ERR%d: %s"
        return pstr % (self.id, self.message)

    def __str__(self):
        pstr = u"ERR%d: %r"
        if type(self.message) in [str, unicode]:
            pstr = "ERR%d: %s"

        ### if we have here unicode, we might fail with conversion error
        try:
            res = pstr % (self.id, self.message)
        except Exception as exx:
            res = u"ERR%d: %r" % (self.id, self.message)
        return res

    def __repr__(self):
        ret = '%s(description=%r, id=%d)' % (type(self).__name__,
                                             self.message, self.id)
        return ret


class BaseError(Exception):
    def __init__(self, error, description, status=400, headers=None):
        Exception.__init__(self)
        self.error = error
        self.description = description
        self.status_code = status
        self.headers = headers
        
    def to_dict(self):
        return {"status_code": self.status_code,
                "error": self.error,
                "description": self.description}
        
    def __repr__(self):
        ret = '%s(error=%r, description=%r, id=%d)' % (type(self).__name__,
                                                       self.error,
                                                       self.description,
                                                       self.status_code)
        return ret


class AuthError(BaseError):
    def __init__(self, error, description, status=401, headers=None,
                 details=None):
        self.details = details
        BaseError.__init__(self, error, description, status, headers)
        

class PolicyError(privacyIDEAError):
    def __init__(self, description, id=403):
        privacyIDEAError.__init__(self, description=description, id=id)


class ValidateError(privacyIDEAError):
    def __init__(self, description="validation error!", id=10):
        privacyIDEAError.__init__(self, description=description, id=id)


class TokenAdminError(privacyIDEAError):
    def __init__(self, description="token admin error!", id=10):
        privacyIDEAError.__init__(self, description=description, id=id)


class ConfigAdminError(privacyIDEAError):
    def __init__(self, description="config admin error!", id=10):
        privacyIDEAError.__init__(self, description=description, id=id)

class CAError(privacyIDEAError):
    def __init__(self, description="CA error!", id=503):
        privacyIDEAError.__init__(self, description=description, id=id)


class UserError(privacyIDEAError):
    def __init__(self, description="user error!", id=905):
        privacyIDEAError.__init__(self, description=description, id=id)


class ServerError(privacyIDEAError):
    def __init__(self, description="server error!", id=905):
        privacyIDEAError.__init__(self, description=description, id=id)


class HSMException(privacyIDEAError):
    def __init__(self, description="hsm error!", id=707):
        privacyIDEAError.__init__(self, description=description, id=id)


class SelfserviceException(privacyIDEAError):
    def __init__(self, description="selfservice error!", id=807):
        privacyIDEAError.__init__(self, description=description, id=id)


class ParameterError(privacyIDEAError):
    USER_OR_SERIAL = _('You either need to provide user or serial')

    def __init__(self, description="unspecified parameter error!", id=905):
        privacyIDEAError.__init__(self, description=description, id=id)
