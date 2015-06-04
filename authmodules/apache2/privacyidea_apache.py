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
import ConfigParser

OK = True
UNAUTHORIZED = False
CONFIG_FILE = "/etc/privacyidea/apache.conf"
DEFAULT_PRIVACYIDEA = "https://localhost"
DEFAULT_SSLVERIFY = False
DEFAULT_REDIS = "localhost"


def check_password(environ, username, password):
    PRIVACYIDEA, REDIS, SSLVERIFY = _get_config()
    syslog.syslog(syslog.LOG_DEBUG, "Authentication with %s, %s, %s" % (
        PRIVACYIDEA, REDIS, SSLVERIFY))
    r_value = UNAUTHORIZED
    rd = redis.Redis(REDIS)
    seconds = 300  # 5 minutes timeout

    # check, if the user already exists in the database.
    value = rd.get(username)
    if password == value:
        # update the timeout
        rd.setex(username, password, seconds)
        r_value = OK

    else:
        # Check against privacyidea
        data = {"user": username,
                "pass": password}
        response = requests.post(PRIVACYIDEA + "/validate/check", data=data,
                                 verify=SSLVERIFY)

        try:
            json_response = response.json()
            syslog.syslog(syslog.LOG_DEBUG, "requests > 1.0")
        except:
            # requests < 1.0
            json_response = response.json
            syslog.syslog(syslog.LOG_DEBUG, "requests < 1.0")

        if json_response.get("result", {}).get("value"):
            rd.setex(username, password, seconds)
            r_value = OK

    return r_value


def _get_config():
    """
    Try to read config from the file /etc/privacyidea/apache.conf

    The config values are
        redis = IPAddress:Port
        privacyidea = https://hostname/path
        sslverify = True | filename to CA bundle
    :return: The configuration
    :rtype: dict
    """
    config_file = ConfigParser.ConfigParser()
    config_file.read(CONFIG_FILE)
    PRIVACYIDEA = DEFAULT_PRIVACYIDEA
    SSLVERIFY = DEFAULT_SSLVERIFY
    REDIS = DEFAULT_REDIS
    try:
        PRIVACYIDEA = config_file.get("DEFAULT", "privacyidea") or DEFAULT_PRIVACYIDEA
        SSLVERIFY = config_file.get("DEFAULT", "sslverify") or DEFAULT_SSLVERIFY
        if SSLVERIFY == "False":
            SSLVERIFY = False
        REDIS = config_file.get("DEFAULT", "redis") or DEFAULT_REDIS
    except ConfigParser.NoOptionError as exx:
        syslog.syslog(syslog.LOG_ERR, "%s" % exx)
    syslog.syslog(syslog.LOG_DEBUG, "Reading configuration %s, %s, %s" % (
        PRIVACYIDEA, REDIS, SSLVERIFY))
    return PRIVACYIDEA, REDIS, SSLVERIFY
