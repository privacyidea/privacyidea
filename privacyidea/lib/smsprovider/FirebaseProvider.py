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
import logging
from oauth2client.service_account import ServiceAccountCredentials
import requests
import json

FIREBASE_URL_SEND = 'https://fcm.googleapis.com/v1/projects/{0!s}/messages:send'
SCOPES = ['https://www.googleapis.com/auth/cloud-platform',
          'https://www.googleapis.com/auth/datastore',
          'https://www.googleapis.com/auth/devstorage.read_write',
          'https://www.googleapis.com/auth/firebase',
          'https://www.googleapis.com/auth/identitytoolkit',
          'https://www.googleapis.com/auth/userinfo.email']

log = logging.getLogger(__name__)


class FIREBASE_CONFIG:
    REGISTRATION_URL = "registration URL"
    TTL = "time to live"
    JSON_CONFG = "JSON config file"
    PROJECT_ID = "projectid"
    PROJECT_NUMBER = "projectnumber"
    APP_ID = "appid"
    API_KEY = "apikey"


class FirebaseProvider(ISMSProvider):

    def submit_message(self, firebase_token, data):
        """
        send a message to a registered Firebase client
        This can be a simple OTP value or a cryptographic challenge response.

        :param firebase_token: The firebase token of the smartphone
        :type firebase_token: str
        :param data: the data dictionary part of the message to submit to the phone
        :type data: dict
        :return: bool
        """
        res = False

        credentials = ServiceAccountCredentials.\
                from_json_keyfile_name(self.smsgateway.option_dict.get(FIREBASE_CONFIG.JSON_CONFG),
                                       SCOPES)

        access_token_info = credentials.get_access_token()

        # Should we do something with expires in?
        # expires_in = access_token_info.expires_in

        bearer_token = access_token_info.access_token
        headers = {
            'Authorization': u'Bearer {0!s}'.format(bearer_token),
            'Content-Type': 'application/json; UTF-8',
        }
        fcm_message = {
            "message": {
                        "data": data,
                        "token": firebase_token
                       }
            }

        url = FIREBASE_URL_SEND.format(self.smsgateway.option_dict.get(FIREBASE_CONFIG.PROJECT_ID))
        resp = requests.post(url, data=json.dumps(fcm_message), headers=headers)

        if resp.status_code == 200:
            log.debug("Message sent successfully to Firebase service.")
            res = True
        else:
            log.warning(u"Failed to send message to firebase service: {0!s}".format(resp.text))

        return res

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
                          "description": _('The second enrollment step must be completed within this time (in minutes).')
                      },
                      FIREBASE_CONFIG.PROJECT_ID: {
                          "required": True,
                          "description": _("The project ID, that the client should use. Get it from your Firebase console.")
                      },
                      FIREBASE_CONFIG.PROJECT_NUMBER: {
                          "required": True,
                          "description": _(
                              "The project number, that the client should use. Get it from your Firebase console.")
                      },
                      FIREBASE_CONFIG.APP_ID: {
                          "required": True,
                          "description": _(
                              "The App ID, that the client should use. Get it from your Firebase console.")
                      },
                      FIREBASE_CONFIG.API_KEY: {
                          "required": True,
                          "description": _(
                              "The API Key, that the client should use. Get it from your Firebase console.")
                      },
                      FIREBASE_CONFIG.JSON_CONFG: {
                          "required": True,
                          "description": _("The filename of the JSON config file, that allows privacyIDEA to talk"
                                           " to the Firebase REST API.")
                      }
                  }
                  }
        return params
        