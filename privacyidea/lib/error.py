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
         
'''contains Errors and Exceptions
'''


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
        ret = '%s(description=%r, id=%d)' % (type(self).__name__, self.message, self.id)
        return ret


class ValidateError(privacyIDEAError):
    def __init__(self, description="validation error!", id=10):
        privacyIDEAError.__init__(self, description=description, id=id)


class TokenAdminError(privacyIDEAError):
    def __init__(self, description="token admin error!", id=10):
        privacyIDEAError.__init__(self, description=description, id=id)


class ConfigAdminError(privacyIDEAError):
    def __init__(self, description="config admin error!", id=10):
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
    def __init__(self, description="unspecified parameter error!", id=905):
        privacyIDEAError.__init__(self, description=description, id=id)


#eof###########################################################################

