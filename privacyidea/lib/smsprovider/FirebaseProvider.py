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

from privacyidea.lib.smsprovider.SMSProvider import (ISMSProvider)
from privacyidea.lib.error import ConfigAdminError
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
    JSON_CONFIG = "JSON config file"
    PROJECT_ID = "projectid"
    PROJECT_NUMBER = "projectnumber"
    APP_ID = "appid"
    API_KEY = "apikey"
    APP_ID_IOS = "appidios"
    API_KEY_IOS = "apikeyios"


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
                from_json_keyfile_name(self.smsgateway.option_dict.get(FIREBASE_CONFIG.JSON_CONFIG),
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

    def check_configuration(self):
        """
        This method checks the sanity of the configuration of this provider.
        If there is a configuration error, than an exception is raised.
        :return:
        """
        json_file = self.smsgateway.option_dict.get(FIREBASE_CONFIG.JSON_CONFIG)
        server_config = None
        with open(json_file) as f:
            server_config = json.load(f)
        if server_config:
            if server_config.get("type") != "service_account":
                raise ConfigAdminError(description="The JSON file is not a valid firebase credentials file.")
            project_id = self.smsgateway.option_dict.get(FIREBASE_CONFIG.PROJECT_ID)
            if server_config.get("project_id") != project_id:
                raise ConfigAdminError(description="The project_id you entered does not match the project_id from the JSON file.")

        else:
            raise ConfigAdminError(description="Please check your configuration. Can not load JSON file.")

        # We need at least
        #         FIREBASE_CONFIG.API_KEY_IOS and FIREBASE_CONFIG.APP_ID_IOS
        # or
        #         FIREBASE_CONFIG.API_KEY and FIREBASE_CONFIG.APP_ID
        android_configured = bool(self.smsgateway.option_dict.get(FIREBASE_CONFIG.APP_ID)) and \
                             bool(self.smsgateway.option_dict.get(FIREBASE_CONFIG.API_KEY))
        ios_configured = bool(self.smsgateway.option_dict.get(FIREBASE_CONFIG.APP_ID_IOS)) and \
                             bool(self.smsgateway.option_dict.get(FIREBASE_CONFIG.API_KEY_IOS))
        if not android_configured and not ios_configured:
            raise ConfigAdminError(description="You need to at least configure either app_id and api_key or"
                                               " app_id_ios and api_key_ios.")

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
                          "required": False,
                          "description": _(
                              "The App ID, that the Android client should use. Get it from your Firebase console.")
                      },
                      FIREBASE_CONFIG.API_KEY: {
                          "required": False,
                          "description": _(
                              "The API Key, that the Android client should use. Get it from your Firebase console.")
                      },
                      FIREBASE_CONFIG.APP_ID_IOS:{
                          "required": False,
                          "description": _(
                              "The App ID, that the iOS client should use. Get it from your Firebase console.")
                      },
                      FIREBASE_CONFIG.API_KEY_IOS: {
                          "required": False,
                          "description": _(
                              "The API Key, that the iOS client should use. Get it from your Firebase console.")
                      },
                      FIREBASE_CONFIG.JSON_CONFIG: {
                          "required": True,
                          "description": _("The filename of the JSON config file, that allows privacyIDEA to talk"
                                           " to the Firebase REST API.")
                      }
                  }
                  }
        return params
        