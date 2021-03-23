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
from privacyidea.lib.framework import get_app_local_store
from privacyidea.lib import _
import logging
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession
import json
import time

FIREBASE_URL_SEND = 'https://fcm.googleapis.com/v1/projects/{0!s}/messages:send'
SCOPES = ['https://www.googleapis.com/auth/cloud-platform',
          'https://www.googleapis.com/auth/datastore',
          'https://www.googleapis.com/auth/devstorage.read_write',
          'https://www.googleapis.com/auth/firebase',
          'https://www.googleapis.com/auth/identitytoolkit',
          'https://www.googleapis.com/auth/userinfo.email']

log = logging.getLogger(__name__)


def get_firebase_access_token(config_file_name):
    """
    This returns the access token for a given JSON config file name

    :param config_file_name: The json file with the Service account credentials
    :type config_file_name: str
    :return: Firebase credentials
    :rtype: google.oauth2.service_account.Credentials
    """
    fbt = "firebase_token"
    app_store = get_app_local_store()

    if fbt not in app_store or not isinstance(app_store[fbt], dict):
        # initialize the firebase_token in the app_store as dict
        app_store[fbt] = {}

    if not isinstance(app_store[fbt].get(config_file_name), service_account.Credentials) or \
            app_store[fbt].get(config_file_name).expired:
        # If the type of the config is not of class Credentials or if the token
        # has expired we get new scoped access token credentials
        credentials = service_account.Credentials.from_service_account_file(config_file_name,
                                                                            scopes=SCOPES)

        log.debug("Fetching a new access_token for {!r} from firebase...".format(config_file_name))
        # We do not use a lock here: The worst that could happen is that two threads
        # fetch new auth tokens concurrently. In this case, one of them wins and
        # is written to the dictionary.
        app_store[fbt][config_file_name] = credentials
        readable_time = credentials.expiry.isoformat() if credentials.expiry else 'Never'
        log.debug(u"Setting the expiration for {!r} of the new access_token "
                  u"to {!s}.".format(config_file_name, readable_time))

    return app_store[fbt][config_file_name]


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
    HTTPS_PROXY = "httpsproxy"


class FirebaseProvider(ISMSProvider):

    def __init__(self, db_smsprovider_object=None, smsgateway=None):
        ISMSProvider.__init__(self, db_smsprovider_object, smsgateway)
        self.access_token_info = None
        self.access_token_expires_at = 0

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

        credentials = get_firebase_access_token(self.smsgateway.option_dict.get(
            FIREBASE_CONFIG.JSON_CONFIG))

        authed_session = AuthorizedSession(credentials)

        headers = {
            'Content-Type': 'application/json; UTF-8',
        }
        fcm_message = {
            "message": {
                        "data": data,
                        "token": firebase_token,
                        "android": {
                                    "priority": "HIGH",
                                    "ttl": "120s",
                                    "fcm_options": {"analytics_label": "AndroidPushToken"}
                                   },
                        "apns": {
                                 "headers": {
                                             "apns-priority": "10",
                                             "apns-push-type": "alert",
                                             "apns-collapse-id": "privacyidea.pushtoken",
                                             "apns-expiration": str(int(time.time()) + 120)
                                            },
                                 "payload": {
                                             "aps": {
                                                     "alert": {
                                                               "title": data.get("title"),
                                                               "body": data.get("question"),
                                                              },
                                                     "sound": "default",
                                                     "category": "PUSH_AUTHENTICATION"
                                                    },
                                            },
                                 "fcm_options": {"analytics_label": "iOSPushToken"}
                                }
                       }
            }

        proxies = {}
        if self.smsgateway.option_dict.get(FIREBASE_CONFIG.HTTPS_PROXY):
            proxies["https"] = self.smsgateway.option_dict.get(FIREBASE_CONFIG.HTTPS_PROXY)
        url = FIREBASE_URL_SEND.format(self.smsgateway.option_dict.get(FIREBASE_CONFIG.PROJECT_ID))
        resp = authed_session.post(url, data=json.dumps(fcm_message), headers=headers, proxies=proxies)

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
                  "headers_allowed": False,
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
                      },
                      FIREBASE_CONFIG.HTTPS_PROXY: {
                          "required": False,
                          "description": _("Proxy setting for HTTPS connections to googleapis.com.")
                      }
                  }
                  }
        return params
