# -*- coding: utf-8 -*-
#
# 2015-06-04 Cornelius Kölbel  <cornelius.koelbel@netknights.it>
#            Initial writeup
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
__doc__ = """This is the Apache module to be used with mod_python with the
privacyIDEA authentication system to add OTP to Apache basic authentication.

To protect an Apache directory or Location add this to your apache config::

    <Directory /var/www/html/secretdir>
        AuthType Basic
        AuthName "Protected Area"
        AuthBasicProvider wsgi
        WSGIAuthUserScript /usr/share/pyshared/privacyidea_apache.py
        Require valid-user
    </Directory>


The code is tested in test_mod_apache.py
"""
import redis
import requests
import syslog
import traceback
import passlib.hash
from six.moves import configparser

OK = True
UNAUTHORIZED = False
CONFIG_FILE = "/etc/privacyidea/apache.conf"
DEFAULT_PRIVACYIDEA = "https://localhost"
DEFAULT_SSLVERIFY = False
DEFAULT_REDIS = "localhost"
DEFAULT_TIMEOUT = 300
ROUNDS = 2342
SALT_SIZE = 10


def check_password(environ, username, password):
    PRIVACYIDEA, REDIS, SSLVERIFY, TIMEOUT = _get_config()
    syslog.syslog(syslog.LOG_DEBUG, "Authentication with {0!s}, {1!s}, {2!s}".format(
        PRIVACYIDEA, REDIS, SSLVERIFY))
    r_value = UNAUTHORIZED
    rd = redis.Redis(REDIS)

    # check, if the user already exists in the database.
    key = _generate_key(username, environ)
    value = rd.get(key)
    if value and passlib.hash.pbkdf2_sha512.verify(password, value):
        # update the timeout
        rd.setex(key, _generate_digest(password), TIMEOUT)
        r_value = OK

    else:
        # Check against privacyidea
        data = {"user": username,
                "pass": password}
        response = requests.post(PRIVACYIDEA + "/validate/check", data=data,
                                 verify=SSLVERIFY)

        if response.status_code == 200:
            try:
                json_response = response.json()
                syslog.syslog(syslog.LOG_DEBUG, "requests > 1.0")
            except Exception as exx:
                # requests < 1.0
                json_response = response.json
                syslog.syslog(syslog.LOG_DEBUG, "requests < 1.0")
                syslog.syslog(syslog.LOG_DEBUG, "{0!s}".format(traceback.format_exc()))

            if json_response.get("result", {}).get("value"):
                rd.setex(key, _generate_digest(password), TIMEOUT)
                r_value = OK
        else:
            syslog.syslog(syslog.LOG_ERR, "Error connecting to privacyIDEA: "
                                          "%s: %s" % (response.status_code,
                                                      response.text))

    return r_value


def _generate_digest(password):
    pw_dig = passlib.hash.pbkdf2_sha512.encrypt(password,
                                                rounds=ROUNDS,
                                                salt_size=SALT_SIZE)
    return pw_dig


def _generate_key(username, environ):
    key = "{0!s}+{1!s}+{2!s}+{3!s}".format(environ.get("SERVER_NAME", ""),
                           environ.get("SERVER_PORT", ""),
                           environ.get("DOCUMENT_ROOT", ""),
                           username)
    return key


def _get_config():
    """
    Try to read config from the file /etc/privacyidea/apache.conf

    The config values are
        redis = IPAddress:Port
        privacyidea = https://hostname/path
        sslverify = True | filename to CA bundle
        timeout = seconds
    :return: The configuration
    :rtype: dict
    """
    config_file = configparser.ConfigParser()
    config_file.read(CONFIG_FILE)
    PRIVACYIDEA = DEFAULT_PRIVACYIDEA
    SSLVERIFY = DEFAULT_SSLVERIFY
    REDIS = DEFAULT_REDIS
    TIMEOUT = DEFAULT_TIMEOUT
    try:
        PRIVACYIDEA = config_file.get("DEFAULT", "privacyidea") or DEFAULT_PRIVACYIDEA
        SSLVERIFY = config_file.get("DEFAULT", "sslverify") or DEFAULT_SSLVERIFY
        if SSLVERIFY == "False":
            SSLVERIFY = False
        elif SSLVERIFY == "True":
            SSLVERIFY = True
        REDIS = config_file.get("DEFAULT", "redis") or DEFAULT_REDIS
        TIMEOUT = config_file.get("DEFAULT", "timeout") or DEFAULT_TIMEOUT
        TIMEOUT = int(TIMEOUT)
    except configparser.NoOptionError as exx:
        syslog.syslog(syslog.LOG_ERR, "{0!s}".format(exx))
    syslog.syslog(syslog.LOG_DEBUG, "Reading configuration {0!s}, {1!s}, {2!s}".format(
        PRIVACYIDEA, REDIS, SSLVERIFY))
    return PRIVACYIDEA, REDIS, SSLVERIFY, TIMEOUT
