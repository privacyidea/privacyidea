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

import logging

log = logging.getLogger(__name__)


class ERROR:
    SUBSCRIPTION = 101
    TOKENADMIN = 301
    CONFIGADMIN = 302
    POLICY = 303
    IMPORTADMIN = 304
    VALIDATE = 401
    REGISTRATION = 402
    AUTHENTICATE = 403
    AUTHENTICATE_WRONG_CREDENTIALS = 4031
    AUTHENTICATE_MISSING_USERNAME = 4032
    AUTHENTICATE_AUTH_HEADER = 4033
    AUTHENTICATE_DECODING_ERROR = 4304
    AUTHENTICATE_TOKEN_EXPIRED = 4305
    AUTHENTICATE_MISSING_RIGHT = 4306
    AUTHENTICATE_ILLEGAL_METHOD = 4307
    ENROLLMENT = 404
    CA = 503
    CA_CSR_INVALID = 504
    CA_CSR_PENDING = 505
    RESOURCE_NOT_FOUND = 601
    HSM = 707
    SELFSERVICE = 807
    DATABASE = 902
    SERVER = 903
    USER = 904
    PARAMETER = 905
    RESOLVER = 907
    PARAMETER_USER_MISSING = 9051
    CONTAINER = 3000
    CONTAINER_NOT_REGISTERED = 3001
    CONTAINER_INVALID_CHALLENGE = 3002
    CONTAINER_ROLLOVER = 3003


class privacyIDEAError(Exception):

    def __init__(self, description="privacyIDEAError!", id=10):
        self.id = id
        self.message = description
        Exception.__init__(self, description)

    def getId(self):
        return self.id

    def getDescription(self):
        return self.message

    def __str__(self):
        if isinstance(self.message, str):
            return f"ERR{self.id}: {self.message}"

        return f"ERR{self.id}: {self.message!r}"

    def __repr__(self):
        return f"{type(self).__name__}(description={self.message!r}, id={self.id:d})"


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


class TokenImportException(privacyIDEAError):
    def __init__(self, description, id=ERROR.IMPORTADMIN):
        privacyIDEAError.__init__(self, description=description, id=id)


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
    def __init__(self, description="registration error!", id=ERROR.REGISTRATION):
        privacyIDEAError.__init__(self, description=description, id=id)


class EnrollmentError(privacyIDEAError):
    def __init__(self, description="enrollment error!", id=ERROR.ENROLLMENT):
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


class CSRError(CAError):
    def __init__(self, description="CSR invalid", id=ERROR.CA_CSR_INVALID):
        privacyIDEAError.__init__(self, description=description, id=id)


class CSRPending(CAError):
    def __init__(self, description="CSR pending", id=ERROR.CA_CSR_PENDING, requestId=None):
        privacyIDEAError.__init__(self, description=description, id=id)
        self.requestId = requestId


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

    def __init__(self, description="unspecified parameter error!", id=ERROR.PARAMETER):
        privacyIDEAError.__init__(self, description=description, id=id)


class DatabaseError(privacyIDEAError):
    """Error in the database layer"""

    def __init__(self, description="database error!", eid=ERROR.DATABASE):
        privacyIDEAError.__init__(self, description=description, id=eid)


class ResolverError(privacyIDEAError):
    """Error in user resolver"""
    def __init__(self, description="resolver error!", eid=ERROR.RESOLVER):
        privacyIDEAError.__init__(self, description=description, id=eid)


class ContainerError(privacyIDEAError):
    def __init__(self, description="container error!", eid=ERROR.CONTAINER):
        privacyIDEAError.__init__(self, description=description, id=eid)


class ContainerNotRegistered(ContainerError):
    def __init__(self, description="container is not registered error!", eid=ERROR.CONTAINER_NOT_REGISTERED):
        ContainerError.__init__(self, description=description, eid=eid)


class ContainerInvalidChallenge(ContainerError):
    def __init__(self, description="container challenge error!", eid=ERROR.CONTAINER_INVALID_CHALLENGE):
        ContainerError.__init__(self, description=description, eid=eid)


class ContainerRollover(ContainerError):
    def __init__(self, description="container rollover error", eid=ERROR.CONTAINER_ROLLOVER):
        ContainerError.__init__(self, description=description, eid=eid)
