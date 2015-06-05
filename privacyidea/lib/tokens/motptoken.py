# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  Sept 16, 2014 Cornelius Kölbel, added key generation for Token2
#
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  2015-01-27 Rewrite due to flask migration
#             Cornelius Klöbel <cornelius@privacyidea.org>
#  2014-10-03 Add getInitDetail
#             Cornelius Kölbel <cornelius@privacyidea.org>
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
__doc__="""This code implements the motp one time password algorithm
described in motp.sourceforge.net.

The code is tested in tests/test_lib_tokens_motp
"""
from .mOTP import mTimeOtp
from privacyidea.lib.apps import create_motp_url
from privacyidea.lib.tokenclass import TokenClass
from privacyidea.lib.log import log_with
from privacyidea.lib.utils import create_img
from privacyidea.api.lib.utils import getParam
from privacyidea.lib.utils import generate_otpkey

optional = True
required = False

import traceback
import logging
log = logging.getLogger(__name__)
import gettext
_ = gettext.gettext


class MotpTokenClass(TokenClass):

    @classmethod
    def get_class_type(cls):
        return "motp"

    @classmethod
    def get_class_prefix(cls):
        return "PIMO"

    @classmethod
    def get_class_info(cls, key=None, ret='all'):
        """
        returns a subtree of the token definition
        Is used by lib.token.get_token_info

        :param key: subsection identifier
        :type key: string
        :param ret: default return value, if nothing is found
        :type ret: user defined
        :return: subsection if key exists or user defined
        :rtype : dict or string
        """

        res = {'type': 'motp',
               'title': 'mOTP Token',
               'description': 'mOTP: Classical mobile One Time Passwords.',
               'init': {'page': {'html': 'motptoken.mako',
                                 'scope': 'enroll', },
                        'title': {'html': 'motptoken.mako',
                                  'scope': 'enroll.title'},
                        },
               'config': {'page': {'html': 'motptoken.mako',
                                   'scope': 'config'},
                          'title': {'html': 'motptoken.mako',
                                    'scope': 'config.title', },
                          },
               'user': ['enroll'],
               # This tokentype is enrollable in the UI for...
               'ui_enroll': ["admin", "user"],
               'policy': {'user': {'motp_webprovision': {'type': 'bool',
                                                                'desc': 'Enroll mOTP token via QR-Code.'}
                                          }}
               }

        if key is not None and key in res:
            ret = res.get(key)
        else:
            if ret == 'all':
                ret = res

        return ret

    @log_with(log)
    def __init__(self, db_token):
        """
        constructor - create a token object

        :param a_token: instance of the orm db object
        :type a_token:  orm object
        """
        TokenClass.__init__(self, db_token)
        self.set_type(u"motp")
        self.hKeyRequired = True
        return
    
    @log_with(log)
    def get_init_detail(self, params=None, user=None):
        """
        to complete the token normalisation, the response of the initialization
        should be build by the token specific method, the getInitDetails
        """
        response_detail = TokenClass.get_init_detail(self, params, user)
        otpkey = self.init_details.get('otpkey')
        if otpkey:
            tok_type = self.type.lower()
            if user is not None:
                try:
                    motp_url = create_motp_url(otpkey,
                                               user.login, user.realm,
                                               serial=self.get_serial())
                    response_detail["motpurl"] = {"description": _("URL for MOTP "
                                                                   "token"),
                                                  "value": motp_url,
                                                  "img": create_img(motp_url,
                                                                    width=250)
                                                  }
                except Exception as ex:   # pragma: no cover
                    log.error("%r" % (traceback.format_exc()))
                    log.error('failed to set motp url: %r' % ex)
                    
        return response_detail

    @log_with(log)
    def update(self, param, reset_failcount=True):
        """
        update - process initialization parameters

        :param param: dict of initialization parameters
        :type param: dict

        :return: nothing
        """
        if self.hKeyRequired is True:
            genkey = int(getParam(param, "genkey", optional) or 0)
            if not param.get('keysize'):
                param['keysize'] = 16
            if 1 == genkey:
                otpKey = generate_otpkey(param['keysize'])
                del param['genkey']
            else:
                # genkey not set: check otpkey is given
                # this will raise an exception if otpkey is not present
                otpKey = getParam(param, "otpkey", required)

            param['otpkey'] = otpKey
            
        # motp token specific
        mOTPPin = getParam(param, "motppin", required)
        self.token.set_user_pin(mOTPPin)

        TokenClass.update(self, param, reset_failcount)

        return

    @log_with(log)
    def check_otp(self, anOtpVal, counter=None, window=None, options=None):
        """
        validate the token otp against a given otpvalue

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
        """
        otplen = self.token.otplen

        # otime contains the previous verification time
        # the new one must be newer than this!
        otime = self.token.count
        secretHOtp = self.token.get_otpkey()
        window = self.token.count_window
        secretPin = self.token.get_user_pin()

        log.debug("otime %s", otime)

        mtimeOtp = mTimeOtp(secretHOtp, secretPin, otime, otplen)
        res = mtimeOtp.checkOtp(anOtpVal, window, options=options)

        if res != -1:
            # later on this will be incremented by 1
            res -= 1
            msg = "verifiction was successful"
        else:
            msg = "verification failed"

        log.debug("%s :res %r" % (msg, res))
        return res
