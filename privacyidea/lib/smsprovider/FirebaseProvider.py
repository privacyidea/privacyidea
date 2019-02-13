# -*- coding: utf-8 -*-
#
#    2019-02-12 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#
#
#    This program is free software: you can redistribute it and/or
#    modify it under the terms of the GNU Affero General Public
#    License, version 3, as published by the Free Software Foundation.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the
#               GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#

__doc__ = """This is the provider class that communicates with Googles
Firebase Cloud Messaging Service.
This provider is used for the push token and can be used for SMS tokens.
"""

from privacyidea.lib.smsprovider.SMSProvider import (ISMSProvider, SMSError)
from privacyidea.lib import _
import requests
from six.moves.urllib.parse import urlparse
import re
import logging
log = logging.getLogger(__name__)

class FIREBASE_CONFIG:
    REGISTRATION_URL = "registration URL"
    TTL = "time to live"
    PROJECT_ID = "project ID"
    PROJECT_NUMBER = "project number"
    APP_ID = "app ID"
    API_KEY = "API key"


class FirebaseProvider(ISMSProvider):

    def submit_message(self, phone, message):
        """
        send a message to a registered Firebase client
        This can be a simple OTP value or a cryptographic challenge response.

        :param phone: the phone number
        :param message: the message to submit to the phone
        :return:
        """
        success = False
        return success

    @classmethod
    def parameters(cls):
        """
        Return a dictionary, that describes the parameters and options for the
        Firebase Provider
        Parameters are required keys to values.

        :return: dict
        """
        params = {"options_allowed": False,
                  "parameters": {
                      FIREBASE_CONFIG.REGISTRATION_URL: {
                          "required": True,
                          "description": _('The URL the Push App should contact in the second enrollment step.'
                                     ' Usually it is the endpoint /ttype/push of the privacyIDEA server.')},
                      FIREBASE_CONFIG.TTL: {
                          "required": True,
                          "description": _('How long should the second step of the enrollment be accepted (in seconds).')
                      },
                      FIREBASE_CONFIG.PROJECT_ID: {
                          "required": True
                      },
                      FIREBASE_CONFIG.PROJECT_NUMBER: {
                          "required": True
                      },
                      FIREBASE_CONFIG.APP_ID: {
                          "required": True
                      },
                      FIREBASE_CONFIG.API_KEY: {
                          "required": True
                      }
                  }
                  }
        return params
        