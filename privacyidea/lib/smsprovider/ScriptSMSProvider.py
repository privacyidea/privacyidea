# -*- coding: utf-8 -*-
#
#    2020-06-04 Cornelius Kölbel <cornelius.koelbel@netknights.i>
#               Initial Code
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

__doc__ = """This is the SMSClass to send SMS via a script.
"""

from privacyidea.lib.smsprovider.SMSProvider import (ISMSProvider, SMSError)
from privacyidea.lib import _
from privacyidea.lib.framework import get_app_config_value
import subprocess  # nosec B404 # We know what we are doing and only allow trusted scripts
import logging
import traceback
log = logging.getLogger(__name__)


SCRIPT_BACKGROUND = "background"
SCRIPT_WAIT = "wait"


class ScriptSMSProvider(ISMSProvider):

    def __init__(self, db_smsprovider_object=None, smsgateway=None, directory=None):
        """
        Create a new SMS Provider object fom a DB SMS provider object

        :param db_smsprovider_object: The database object
        :param smsgateway: The SMS gateway object from the database table
            SMS gateway. The options can be accessed via
            self.smsgateway.option_dict
        :param directory: The directory where the SMS sending scripts are located.
        :type directory: str
        :return: An SMS provider object
        """
        self.config = db_smsprovider_object or {}
        self.smsgateway = smsgateway
        self.script_directory = directory or get_app_config_value("PI_SCRIPT_SMSPROVIDER_DIRECTORY",
                                                                  "/etc/privacyidea/scripts")

    def submit_message(self, phone, message):
        """
        send a message to a phone using an external script

        :param phone: the phone number
        :param message: the message to submit to the phone
        :return:
        """
        if not self.smsgateway:
            # this should not happen. We now always use sms gateway definitions.
            log.warning("Missing smsgateway definition!")
            raise SMSError(-1, "Missing smsgateway definition!")

        phone = self._mangle_phone(phone, self.smsgateway.option_dict)
        log.debug("submitting message {0!s} to {1!s}".format(message, phone))

        script = self.smsgateway.option_dict.get("script")
        background = self.smsgateway.option_dict.get("background")

        script_name = self.script_directory + "/" + script
        proc_args = [script_name, phone]

        # As the message can contain blanks... it is passed via stdin
        rcode = 0
        try:
            log.info("Starting script {script!r}.".format(script=script_name))
            # Trusted input/no user input: The scripts are created by user root and read from hard disk
            p = subprocess.Popen(proc_args, cwd=self.script_directory,   # nosec B603
                                 universal_newlines=True, stdin=subprocess.PIPE)
            p.communicate(message)
            if background == SCRIPT_WAIT:
                rcode = p.wait()
        except Exception as e:
            log.warning("Failed to execute script {0!r}: {1!r}".format(
                script_name, e))
            log.warning(traceback.format_exc())
            if background == SCRIPT_WAIT:
                raise SMSError(-1, "Failed to start script for sending SMS.")

        if rcode:
            log.warning("Script {script!r} failed to execute with error code {error!r}".format(script=script_name,
                                                                                               error=rcode))
            raise SMSError(-1, "Error during execution of the script.")
        else:
            log.info("SMS delivered to {0!s}.".format(phone))

        return True

    @classmethod
    def parameters(cls):
        """
        Return a dictionary, that describes the parameters and options for the
        SMS provider.
        Parameters are required keys to values.

        :return: dict
        """
        params = {"options_allowed": False,
                  "parameters": {
                      "script": {
                          "required": True,
                          "description": _("The script in script directory PI_SCRIPT_SMSPROVIDER_DIRECTORY to call. "
                                           "Expects phone as the parameter and the message from stdin.")
                      },
                      "REGEXP": {
                          "description": cls.regexp_description
                      },
                      "background": {
                          "required": True,
                          "description": _("Wait for script to complete or run script in background. This will "
                                           "either return the HTTP request early or could also block the request."),
                          "values": [SCRIPT_BACKGROUND, SCRIPT_WAIT]}
                    }
                  }
        return params
