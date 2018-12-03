# -*- coding: utf-8 -*-
#
#  2016-12-21 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Initial writup
#
# License:  AGPLv3
# (c) 2016. Cornelius Kölbel
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
#
__doc__ = """This is the event handler module for calling external scripts.
You can put any script in the directory specified in
PI_SCRIPT_HANDLER_DIRECTORY and call this script in any event.

The scripts can take parameters like
* serial
* user
* realm
* resolver
* logged_in_user
"""
from privacyidea.lib.eventhandler.base import BaseEventHandler
from privacyidea.lib.utils import is_true
from privacyidea.lib.framework import get_app_config_value
from privacyidea.lib.error import ServerError
from privacyidea.lib import _
import logging
import subprocess
import os
import traceback

log = logging.getLogger(__name__)

SCRIPT_BACKGROUND = "background"
SCRIPT_WAIT = "wait"


class ScriptEventHandler(BaseEventHandler):
    """
    An Eventhandler needs to return a list of actions, which it can handle.
    It also returns a list of allowed action and conditions
    It returns an identifier, which can be used in the eventhandling definitions
    """

    identifier = "Script"
    description = "This event handler can trigger external scripts."

    def __init__(self, script_directory=None):
        if not script_directory:
            try:
                self.script_directory = get_app_config_value("PI_SCRIPT_HANDLER_DIRECTORY",
                                                       "/etc/privacyidea/scripts")
            except RuntimeError as e:
                # In case of the tests we are outside of the application context
                self.script_directory = "tests/testdata/scripts"

        else:
            self.script_directory = script_directory

    @property
    def allowed_positions(cls):
        """
        This returns the allowed positions of the event handler definition.
        :return: list of allowed positions
        """
        return ["post", "pre"]

    @property
    def actions(cls):
        """
        This method returns a dictionary of allowed actions and possible
        options in this handler module.

        :return: dict with actions
        """
        scripts = os.listdir(cls.script_directory)
        actions = {}
        for script in scripts:
            actions[script] = {
                "background": {
                    "type": "str",
                    "required": True,
                    "description": _("Wait for script to complete or run script in background. This will "
                                     "either return the HTTP request early or could also block the request."),
                    "value": [SCRIPT_BACKGROUND, SCRIPT_WAIT]
                },
                "raise_error": {
                    "type": "bool",
                    "visibleIf": "background",
                    "visibleValue": SCRIPT_WAIT,
                    "description": _("On script error raise exception in HTTP request.")
                },
                "serial": {
                    "type": "bool",
                    "description": _("Add '--serial <serial number>' as script "
                                     "parameter.")
                },
                "user": {
                    "type": "bool",
                    "description": _("Add '--user <username>' as script "
                                     "parameter.")
                },
                "realm": {
                    "type": "bool",
                    "description": _("Add '--realm <realm>' as script "
                                     "parameter.")
                },
                "logged_in_user": {
                    "type": "bool",
                    "description": _("Add the username of the logged in user "
                                     "as script parameter like "
                                     "'--logged_in_user <username>'.")
                },
                "logged_in_role": {
                    "type": "bool",
                    "description": _("Add the role (either admin or user) of "
                                     "the logged in user as script parameter "
                                     "like '--logged_in_role <role>'.")
                }
            }

        return actions

    def do(self, action, options=None):
        """
        This method executes the defined action in the given event.

        :param action:
        :param options: Contains the flask parameters g, request, response
            and the handler_def configuration
        :type options: dict
        :return:
        """
        ret = True
        script_name = self.script_directory + "/" + action
        proc_args = [script_name]

        g = options.get("g")
        request = options.get("request")
        response = options.get("response")
        content = self._get_response_content(response)
        handler_def = options.get("handler_def")
        handler_options = handler_def.get("options", {})

        if hasattr(g, "logged_in_user"):
            logged_in_user = g.logged_in_user
        else:
            logged_in_user = {"username": "none",
                              "realm": "none",
                              "role": "none"}

        serial = request.all_data.get("serial") or \
                 content.get("detail", {}).get("serial") or \
                 g.audit_object.audit_data.get("serial")

        if handler_options.get("serial"):
            proc_args.append("--serial")
            proc_args.append(serial or "none")

        if handler_options.get("user"):
            proc_args.append("--user")
            proc_args.append(request.User.login or "none")

        if handler_options.get("realm"):
            proc_args.append("--realm")
            proc_args.append(request.User.realm or "none")

        if handler_options.get("logged_in_user"):
            proc_args.append("--logged_in_user")
            proc_args.append("{username}@{realm}".format(
                **logged_in_user))

        if handler_options.get("logged_in_role"):
            proc_args.append("--logged_in_role")
            proc_args.append(logged_in_user.get("role", "none"))

        rcode = 0
        try:
            log.info("Starting script {script!r}.".format(script=script_name))
            p = subprocess.Popen(proc_args, cwd=self.script_directory)
            if handler_options.get("background") == SCRIPT_WAIT:
                rcode = p.wait()

        except Exception as e:
            log.warning("Failed to execute script {0!r}: {1!r}".format(
                script_name, e))
            log.warning(traceback.format_exc())
            if handler_options.get("background") == SCRIPT_WAIT and is_true(handler_options.get("raise_error")):
                raise ServerError("Failed to start script.")

        if rcode:
            log.warning("Script {script!r} failed to execute with error code {error!r}".format(script=script_name,
                                                                                               error=rcode))
            if is_true(handler_options.get("raise_error")):
                raise ServerError("Error during execution of the script.")

        return ret

