# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  LSE
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
  Description:  This file containes the mOTP token implementation:
              - http://motp.sourceforge.net/ -

  Dependencies: -

'''

from privacyidea.lib.util        import getParam
from privacyidea.lib.util        import required
from privacyidea.lib.log import log_with

from privacyidea.lib.mOTP        import mTimeOtp
from privacyidea.lib.tokenclass  import TokenClass


import logging
log = logging.getLogger(__name__)


###############################################
class MotpTokenClass(TokenClass):
    '''
    implementation of the mOTP token class
    - see: http://motp.sourceforge.net/
    '''

    @classmethod
    def getClassType(cls):
        '''
        static method to return the token class identifier

        :return: fixed string
        '''

        return "motp"

    @classmethod
    def getClassPrefix(cls):
        return "LSMO"

    @classmethod
    def getClassInfo(cls, key=None, ret='all'):
        '''
        getClassInfo - returns all or a subtree of the token definition

        :param key: subsection identifier
        :type key: string

        :param ret: default return value, if nothing is found
        :type ret: user defined

        :return: subsection if key exists or user defined
        :rtype : s.o.

        '''

        res = {
               'type'           : 'motp',
               'title'          : 'mOTP Token',
               'description'    : ('mobile otp token'),

               'init'         : {'page' : {'html'      : 'motptoken.mako',
                                            'scope'      : 'enroll', },
                                   'title'  : {'html'      : 'motptoken.mako',
                                             'scope'     : 'enroll.title', },
                                   },

               'config'        : { 'page' : {'html'      : 'motptoken.mako',
                                            'scope'      : 'config', },
                                   'title'  : {'html'      : 'motptoken.mako',
                                             'scope'     : 'config.title', },
                                 },

               'selfservice'   :  { 'enroll' :
                                   {'page' :
                                    {'html'       : 'motptoken.mako',
                                     'scope'      : 'selfservice.enroll', },
                                   'title'  :
                                     { 'html'      : 'motptoken.mako',
                                      'scope'      : 'selfservice.title.enroll', },
                                    },
                                  },


               }


        if key is not None and res.has_key(key):
            ret = res.get(key)
        else:
            if ret == 'all':
                ret = res

        return ret

    @log_with(log)
    def __init__(self, a_token):
        '''
        constructor - create a token object

        :param a_token: instance of the orm db object
        :type a_token:  orm object
        '''
        TokenClass.__init__(self, a_token)
        self.setType(u"mOTP")

        return


    @log_with(log)
    def update(self, param, reset_failcount=True):
        '''
        update - process initialization parameters

        :param param: dict of initialization parameters
        :type param: dict

        :return: nothing

        '''
        getParam(param, "otpkey", required)

        ## motp token specific
        otpPin = getParam(param, "otppin", required)
        self.token.setUserPin(otpPin)

        TokenClass.update(self, param, reset_failcount)

        return

    @log_with(log)
    def checkOtp(self, anOtpVal, counter, window, options=None):
        '''
        checkOtp - validate the token otp against a given otpvalue

        :param anOtpVal: the to be verified otpvalue
        :type anOtpVal:  string

        :param counter: the counter state, that shoule be verified
        :type counter: int

        :param window: the counter +window, which should be checked
        :type window: int

        :param options: the dict, which could contain token specific info
        :type options: dict

        :return: the counter state or -1
        :rtype: int

        '''
        otplen = self.token.privacyIDEAOtpLen

        #otime contains the previous verification time
        # the new one must be newer than this!
        otime = self.token.privacyIDEACount
        secretHOtp = self.token.getHOtpKey()
        window = self.token.privacyIDEACountWindow
        secretPin = self.token.getUserPin()

        log.debug("otime %s", otime)

        mtimeOtp = mTimeOtp(secretHOtp, secretPin, otime, otplen)
        res = mtimeOtp.checkOtp(anOtpVal, window, options=options)

        if (res != -1):
            res = res - 1  ## later on this will be incremented by 1
        if res == -1:
            msg = "verification failed"
        else:
            msg = "verifiction was successful"

        log.debug("%s :res %r" % (msg, res))
        return res


