# -*- coding: utf-8 -*-
#
# 2015-04-01 Cornelius Kölbel  <cornelius.koelbel@netknights.it>
#            Add storing of OTP hashes
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
import sqlite3
# TODO: We might want to avoid having to install the privacyidea server libs
# as dependency!
from privacyidea.lib.crypto import verify_salted_hash_256


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
    sqlfile = config.get("sqlfile", "/etc/privacyidea/pam.sqlite")
    prompt = config.get("prompt", "Your OTP")
    rval = pamh.PAM_AUTH_ERR
    syslog.openlog(facility=syslog.LOG_AUTH)
    try:
        user = pamh.get_user(None)
        if pamh.authtok is None:
            message = pamh.Message(pamh.PAM_PROMPT_ECHO_OFF, "%s: " % prompt)
            response = pamh.conversation(message)
            pamh.authtok = response.resp

        if debug:
            syslog.syslog(syslog.LOG_DEBUG,
                          "%s: user %s in realm %s" % (__name__, user,
                                                       realm))
        # First we try to authenticate against the sqlitedb
        if check_otp(user, pamh.authtok, sqlfile, window=10):
            syslog.syslog(syslog.LOG_DEBUG,
                          "%s: successfully authenticated against offline "
                          "database %s" % (__name__, sqlfile))
            rval = pamh.PAM_SUCCESS
        else:
            # If we do not successfully authenticate against the offline
            # database, we do an online request.
            # Now we have the password in pamh.authtok
            data = {"user": user,
                    "pass": pamh.authtok}
            if realm:
                data["realm"] = realm

            response = requests.post(URL + "/validate/check", data=data,
                                     verify=sslverify)

            json_response = response.json()
            result = json_response.get("result")
            auth_item = json_response.get("auth_items")
            if debug:
                syslog.syslog(syslog.LOG_DEBUG, "%s: result: %s" % (__name__,
                                                                    result))

            if result.get("status"):
                if result.get("value"):
                    rval = pamh.PAM_SUCCESS
                    save_auth_item(sqlfile, user, auth_item)
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


def check_otp(user, otp, sqlfile, window=10):
    """
    compare the given otp values with the next hashes of the user.

    DB entries older than the matching counter will be deleted from the
    database.

    :param user: The local user in the sql file
    :param otp: The otp value
    :param sqlfile: The sqlite file
    :return: True or False
    """
    res = False
    conn = sqlite3.connect(sqlfile)
    c = conn.cursor()
    c.execute("SELECT counter, user, otp FROM authitems WHERE user='%s' "
              "ORDER by counter" % user)
    for x in range(0, window):
        r = c.fetchone()
        hash_value = r[2]
        if verify_salted_hash_256(otp, hash_value):
            res = True
            counter = r[0]
            break
    # We found a matching password, so we remove the old entries
    if res:
        c.execute("DELETE from authitems WHERE counter <= %i" % counter)
        conn.commit()
    conn.close()
    return res


def save_auth_item(sqlfile, user, authitem):
    """
    Save the given authitem to the sqlite file to be used later for offline
    authentication.

    There is only one table in it with the columns:

        username, counter, otp

    :param sqlfile: An SQLite file. If it does not exist, it will be generated.
    :type sqlfile: basestring
    :param user: The PAM user
    :param authitem: A dictionary with all authitem information being:
    username, count, and a response dict with counter and otphash.

    :return:
    """
    # TODO: At the moment two OTP tokens per user will cause a conflict!
    conn = sqlite3.connect(sqlfile)
    c = conn.cursor()
    # Create the table if necessary
    try:
        c.execute("CREATE TABLE authitems "
                  "(counter int, user text, tokenowner text, otp text)")
    except:
        pass

    syslog.syslog(syslog.LOG_DEBUG, "%s: offline save authitem: %s" % (
        __name__, authitem))
    if authitem:
        offline = authitem.get("offline", [{}])[0]
        tokenowner = offline.get("username")
        for counter, otphash in offline.get("response").iteritems():
            # Insert the OTP hash
            c.execute("INSERT INTO authitems (counter, user, tokenowner, otp) "
                      "VALUES ('%s','%s','%s','%s')"
                      % (counter, user, tokenowner, otphash))

    # Save (commit) the changes
    conn.commit()

    # We can also close the connection if we are done with it.
    # Just be sure any changes have been committed or they will be lost.
    conn.close()
