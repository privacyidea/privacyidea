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
import base64
import hashlib as _hashlib
import hmac as _hmac
import os as _os
import redis
import requests
import syslog
import traceback
import configparser

OK = True
UNAUTHORIZED = False
CONFIG_FILE = "/etc/privacyidea/apache.conf"
DEFAULT_PRIVACYIDEA = "https://localhost"
DEFAULT_SSLVERIFY = False
DEFAULT_REDIS = "localhost"
DEFAULT_TIMEOUT = 300
ROUNDS = 2342
SALT_SIZE = 10


def _ab64_encode(data):
    """Passlib-compatible ab64: standard base64 with '.' instead of '+', no '=' padding."""
    return base64.b64encode(data).decode('ascii').replace('+', '.').rstrip('=')


def _ab64_decode(s):
    return base64.b64decode(s.replace('.', '+') + '=' * (-len(s) % 4))


def _pbkdf2_sha512_verify(password, hash_str):
    """Verify a password against a $pbkdf2-sha512$ hash."""
    if isinstance(password, str):
        password = password.encode('utf-8')
    if isinstance(hash_str, bytes):
        hash_str = hash_str.decode('utf-8')
    try:
        _, scheme, rounds_str, salt_b64, hash_b64 = hash_str.split('$')
        salt = _ab64_decode(salt_b64)
        expected = _ab64_decode(hash_b64)
        actual = _hashlib.pbkdf2_hmac('sha512', password, salt, int(rounds_str))
        return _hmac.compare_digest(actual, expected)
    except Exception:
        return False


def check_password(environ, username, password):
    PRIVACYIDEA, REDIS, SSLVERIFY, TIMEOUT = _get_config()
    syslog.syslog(syslog.LOG_DEBUG, "Authentication with {0!s}, {1!s}, {2!s}".format(
        PRIVACYIDEA, REDIS, SSLVERIFY))
    r_value = UNAUTHORIZED
    rd = redis.Redis(REDIS)

    # check, if the user already exists in the database.
    key = _generate_key(username, environ)
    value = rd.get(key)
    if value and _pbkdf2_sha512_verify(password, value):
        # update the timeout
        rd.setex(key, value=_generate_digest(password), time=TIMEOUT)
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
                rd.setex(key, value=_generate_digest(password), time=TIMEOUT)
                r_value = OK
        else:
            syslog.syslog(syslog.LOG_ERR, "Error connecting to privacyIDEA: "
                                          "%s: %s" % (response.status_code,
                                                      response.text))

    return r_value


def _ab64_encode(data):
    return base64.b64encode(data).rstrip(b'=').replace(b'+', b'.').decode('ascii')


def _ab64_decode(s):
    s = s.replace('.', '+')
    return base64.b64decode(s + '=' * ((4 - len(s) % 4) % 4))


def _pbkdf2_sha512_verify(password, hash_str):
    if isinstance(password, str):
        password = password.encode('utf-8')
    if isinstance(hash_str, bytes):
        hash_str = hash_str.decode('utf-8')
    try:
        parts = hash_str.split('$')
        rounds = int(parts[2])
        salt = _ab64_decode(parts[3])
        stored = _ab64_decode(parts[4])
        computed = _hashlib.pbkdf2_hmac('sha512', password, salt, rounds)
        return _hmac.compare_digest(computed, stored)
    except Exception:
        return False


def _generate_digest(password):
    if isinstance(password, str):
        password = password.encode('utf-8')
    salt = _os.urandom(SALT_SIZE)
    dk = _hashlib.pbkdf2_hmac('sha512', password, salt, ROUNDS)
    return '$pbkdf2-sha512${r}${s}${h}'.format(
        r=ROUNDS, s=_ab64_encode(salt), h=_ab64_encode(dk)
    )


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
