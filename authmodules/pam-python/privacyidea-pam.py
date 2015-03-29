# -*- coding: utf-8 -*-
#
# 2015-03-29 Cornelius Kölbel, <cornelius.koelbel@netknights.it>
#            Initial creation
#
# (c) Cornelius Kölbel
# Info: http://www.privacyidea.org
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
__doc__="""This is the PAM module to be used with python-pam with the
privacyIDEA authentication system.

"""

import requests
import syslog


def _get_config(argv):
    """
    Read the parameters from the arguments. If the argument can be split with a
    "=", the parameter will get the given value.

    :param argv:
    :return: dictionary with the parameters
    """
    config = {}
    for arg in argv:
        argument = arg.split("=")
        if len(argument) == 1:
            config[argument[0]] = True
        elif len(argument) == 2:
            config[argument[0]] = argument[1]
    return config


def pam_sm_authenticate(pamh, flags, argv):
    config = _get_config(argv)
    URL = config.get("url", "https://localhost")
    sslverify = not config.get("nosslverify", False)
    realm = config.get("realm")
    debug = config.get("debug")
    prompt = config.get("prompt", "Your OTP")
    rval = pamh.PAM_AUTH_ERR
    syslog.openlog(facility=syslog.LOG_AUTH)
    try:
        user = pamh.get_user(None)
        if pamh.authtok is None:
            message = pamh.Message(pamh.PAM_PROMPT_ECHO_OFF, "%s: " % prompt)
            response = pamh.conversation(message)
            pamh.authtok = response.resp

        # Now we have the password in pamh.authtok
        data={"user": user,
              "pass": pamh.authtok}
        if realm:
            data["realm"] = realm

        if debug:
            syslog.syslog(syslog.LOG_DEBUG,
                          "%s: user %s in realm %s" % (user,
                                                       realm,
                                                       __name__))
        response = requests.post(URL + "/validate/check", data=data,
                                 verify=sslverify)

        json_response = response.json()
        result = json_response.get("result")
        if debug:
            syslog.syslog(syslog.LOG_DEBUG, "%s: result: %s" % (__name__,
                                                                result))

        if result.get("status"):
            if result.get("value"):
                rval = pamh.PAM_SUCCESS
            else:
                rval = pamh.PAM_AUTH_ERR
        else:
            syslog.syslog(syslog.LOG_ERR,
                          "%s: %s" % (__name__,
                                      result.get("error").get("message")))
            rval = pamh.PAM_SYSTEM_ERR

    except pamh.exception as exx:
        rval = exx.pam_result
    except requests.exceptions.SSLError:
        syslog.syslog(syslog.LOG_CRIT, "%s: SSL Validation error. Get a valid "
                                       "SSL "
                                       "certificate for your privacyIDEA "
                                       "system. For testing you can use the "
                                       "options 'nosslverify'." % __name__)
    finally:
        syslog.closelog()

    return rval


def pam_sm_setcred(pamh, flags, argv):
  return pamh.PAM_SUCCESS

def pam_sm_acct_mgmt(pamh, flags, argv):
  return pamh.PAM_SUCCESS

def pam_sm_open_session(pamh, flags, argv):
  return pamh.PAM_SUCCESS

def pam_sm_close_session(pamh, flags, argv):
  return pamh.PAM_SUCCESS

def pam_sm_chauthtok(pamh, flags, argv):
  return pamh.PAM_SUCCESS
