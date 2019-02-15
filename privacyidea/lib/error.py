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

import six
from privacyidea.lib import _
import logging
log = logging.getLogger(__name__)


class ERROR:
    SUBSCRIPTION = 101
    TOKENADMIN = 301
    CONFIGADMIN = 302
    POLICY = 303
    VALIDATE = 401
    REGISTRATION = 402
    AUTHENTICATE = 403
    AUTHENTICATE_WRONG_CREDENTIALS = 4031
    AUTHENTICATE_MISSING_USERNAME = 4032
    AUTHENTICATE_AUTH_HEADER = 4033
    AUTHENTICATE_DECODING_ERROR = 4304
    AUTHENTICATE_TOKEN_EXPIRED = 4305
    AUTHENTICATE_MISSING_RIGHT = 4306
    CA = 503
    RESOURCE_NOT_FOUND = 601
    HSM = 707
    SELFSERVICE = 807
    SERVER = 903
    USER = 904
    PARAMETER = 905


@six.python_2_unicode_compatible
class privacyIDEAError(Exception):

    def __init__(self, description=u"privacyIDEAError!", id=10):
        self.id = id
        self.message = description
        Exception.__init__(self, description)

    def getId(self):
        return self.id

    def getDescription(self):
        return self.message

    def __str__(self):
        pstr = u"ERR%d: %r"
        if isinstance(self.message, six.string_types):
            pstr = u"ERR%d: %s"

        ### if we have here unicode, we might fail with conversion error
        try:
            res = pstr % (self.id, self.message)
        except Exception as exx:
            res = u"ERR{0:d}: {1!r}".format(self.id, self.message)
        return res

    def __repr__(self):
        ret = '{0!s}(description={1!r}, id={2:d})'.format(type(self).__name__,
                                             self.message, self.id)
        return ret


class SubscriptionError(privacyIDEAError):
    def __init__(self, description=None, application=None, id=ERROR.SUBSCRIPTION):
        self.id = id
        self.message = description
        self.application = application
        privacyIDEAError.__init__(self, description, id=self.id)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        ret = '{0!s}({1!r}, application={2!s})'.format(type(
            self).__name__, self.message, self.application)
        return ret


class AuthError(privacyIDEAError):
    def __init__(self, description, id=ERROR.AUTHENTICATE, details=None):
        self.details = details
        privacyIDEAError.__init__(self, description=description, id=id)


class ResourceNotFoundError(privacyIDEAError):
    def __init__(self, description, id=ERROR.RESOURCE_NOT_FOUND):
        privacyIDEAError.__init__(self, description=description, id=id)


class PolicyError(privacyIDEAError):
    def __init__(self, description, id=ERROR.POLICY):
        privacyIDEAError.__init__(self, description=description, id=id)


class ValidateError(privacyIDEAError):
    def __init__(self, description="validation error!", id=ERROR.VALIDATE):
        privacyIDEAError.__init__(self, description=description, id=id)


class RegistrationError(privacyIDEAError):
    def __init__(self, description="registraion error!", id=ERROR.REGISTRATION):
        privacyIDEAError.__init__(self, description=description, id=id)


class TokenAdminError(privacyIDEAError):
    def __init__(self, description="token admin error!", id=ERROR.TOKENADMIN):
        privacyIDEAError.__init__(self, description=description, id=id)


class ConfigAdminError(privacyIDEAError):
    def __init__(self, description="config admin error!", id=ERROR.CONFIGADMIN):
        privacyIDEAError.__init__(self, description=description, id=id)


class CAError(privacyIDEAError):
    def __init__(self, description="CA error!", id=ERROR.CA):
        privacyIDEAError.__init__(self, description=description, id=id)


class UserError(privacyIDEAError):
    def __init__(self, description="user error!", id=ERROR.USER):
        privacyIDEAError.__init__(self, description=description, id=id)


class ServerError(privacyIDEAError):
    def __init__(self, description="server error!", id=ERROR.SERVER):
        privacyIDEAError.__init__(self, description=description, id=id)


class HSMException(privacyIDEAError):
    def __init__(self, description="hsm error!", id=ERROR.HSM):
        privacyIDEAError.__init__(self, description=description, id=id)


class SelfserviceException(privacyIDEAError):
    def __init__(self, description="selfservice error!", id=ERROR.SELFSERVICE):
        privacyIDEAError.__init__(self, description=description, id=id)


class ParameterError(privacyIDEAError):
    USER_OR_SERIAL = _('You either need to provide user or serial')

    def __init__(self, description="unspecified parameter error!", id=ERROR.PARAMETER):
        privacyIDEAError.__init__(self, description=description, id=id)
