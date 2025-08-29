# SPDX-FileCopyrightText: (C) 2015 NetKnights GmbH <https://netknights.it>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import annotations

import os
import sys
import logging
from pathlib import Path
import secrets
import string

log = logging.getLogger(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
basedir = "/".join(basedir.split("/")[:-1]) + "/"


pubtest_key = b"""-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0stF+PVh/qR7I82ywgDW
X2rPxKnlBugU33SAbxZjfNz+aKYYM+irKJ0IdTOLtQ85DzZaEhocqO7cg1Qw85Ac
gU8NEIUdRQdHilO558Mc/E95jDeiI7AbzuLlG2gFyMHkObqwoA2N9ARk9vck+pIo
gCVhZfHs+ifRqdOMzbGNtWp8XGwpp9YLEFTZ2ZBloWJ6kkijatXwY5nTlP5ugbEU
cKMamksTyvRdZFryKwK3HfAQoL6fJAfB3u4NVp5nfcuD180MKcGk8CR9zwuXkRX5
m+qnl1W6iD0z5ws/SrtWBJiMuFm3hGaXdQLZVABSqgmvaru3GZbldlQU/0pcV855
NwIDAQAB
-----END PUBLIC KEY-----"""

non_matching_pubkey = b"""-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0R9Nos93gt6JdiY/Q+ac
WuukYcwr+JlCDa+RX8UDuKfF3wVkSjwAl6s3ADrEnRIgi9qCQD52o29YEVugftVh
HKiC+Gw5Cf95hkWKLl1MFoI6JUMDnNtPlPJrsCwLCi79TV+24BZ0v19P9ivxDa+c
bHUR+vUHbvYfhzpf5Zq8gHTNEQda6+ufcC48VjCdJwOiJJcjNZMZhYrQBoYyCHxm
HUb6rdpz/AsBSMV3+kZiDqv/NA5dgR8dXAK2or8JSK/ghw8c3qgt+yLW+1g9FDao
6Bn6LrQkUkMv/cANYsiVk/pnxtsb11cEbYNyv2VQd/lbCCMwK/rkuipZxu8XJl6g
WQIDAQAB
-----END PUBLIC KEY-----
"""


class ConfigKey:
    SECRET_KEY = "SECRET_KEY"
    PEPPER = "PI_PEPPER"
    ENCFILE = "PI_ENCFILE"

    SQLALCHEMY_DATABASE_URI = "SQLALCHEMY_DATABASE_URI"
    SQLALCHEMY_ENGINE_OPTIONS = "SQLALCHEMY_ENGINE_OPTIONS"
    DEV_DATABASE_URL = "DEV_DATABASE_URL"
    TEST_DATABASE_URL = "TEST_DATABASE_URL"
    DB_DRIVER = "PI_DB_DRIVER"
    DB_USER = "PI_DB_USER"
    DB_PASSWORD = "PI_DB_PASSWORD"
    DB_HOST = "PI_DB_HOST"
    DB_PORT = "PI_DB_PORT"
    DB_NAME = "PI_DB_NAME"
    DB_EXTRA_PARAMS = "PI_DB_EXTRA_PARAMS"

    AUDIT_SQL_URI = "PI_AUDIT_SQL_URI"
    AUDIT_SQL_OPTIONS = "PI_AUDIT_SQL_OPTIONS"
    AUDIT_POOL_SIZE = "PI_AUDIT_POOL_SIZE"
    AUDIT_POOL_RECYCLE = "PI_AUDIT_POOL_RECYCLE"
    AUDIT_KEY_PRIVATE = "PI_AUDIT_KEY_PRIVATE"
    AUDIT_KEY_PUBLIC = "PI_AUDIT_KEY_PUBLIC"
    AUDIT_MODULE = "PI_AUDIT_MODULE"
    AUDIT_SERVERNAME = "PI_AUDIT_SERVERNAME"
    AUDIT_SQL_TRUNCATE = "PI_AUDIT_SQL_TRUNCATE"
    AUDIT_NO_SIGN = "PI_AUDIT_NO_SIGN"
    AUDIT_NO_PRIVATE_KEY_CHECK = "PI_AUDIT_NO_PRIVATE_KEY_CHECK"
    AUDIT_SQL_COLUMN_LENGTH = "PI_AUDIT_SQL_COLUMN_LENGTH"
    CHECK_OLD_SIGNATURES = "PI_CHECK_OLD_SIGNATURES"

    LOGLEVEL = "PI_LOGLEVEL"
    LOGCONFIG = "PI_LOGCONFIG"
    LOGFILE = "PI_LOGFILE"

    NODE = "PI_NODE"
    NODE_UUID = "PI_NODE_UUID"
    UUID_FILE = "PI_UUID_FILE"

    VERBOSE = "VERBOSE"
    SUPERUSER_REALM = "SUPERUSER_REALM"
    APP_READY = "APP_READY"
    HSM_INITIALIZE = "PI_INITIALIZE_HSM"
    CONFIG_NAME = "PI_CONFIG_NAME"
    STATIC_FOLDER = "PI_STATIC_FOLDER"
    TEMPLATE_FOLDER = "PI_TEMPLATE_FOLDER"
    NO_RESPONSE_SIGN = "PI_NO_RESPONSE_SIGN"
    RESPONSE_NO_PRIVATE_KEY_CHECK = "PI_RESPONSE_NO_PRIVATE_KEY_CHECK"


class DefaultConfigValues:
    UUID_FILE = "/etc/privacyidea/uuid.txt"
    NODE_NAME = "localnode"

    STATIC_FOLDER = "static/"
    TEMPLATE_FOLDER = "static/templates/"

    CFG_PATH = "/etc/privacyidea/pi.cfg"
    LOGFILE_PATH = "/etc/privacyidea/privacyidea.log"
    LOGGING_CFG = "/etc/privacyidea/logging.cfg"


def _random_password(size):
    log.info("SECRET_KEY not set in config. Generating a random key.")
    passwd = [secrets.choice(string.ascii_lowercase +
                             string.ascii_uppercase + string.digits) for _x in range(size)]
    return "".join(passwd)


class Config:
    SECRET_KEY = os.environ.get(ConfigKey.SECRET_KEY)
    PI_ENCFILE = os.path.join(basedir, "tests/testdata/enckey")
    PI_HSM = "default"
    PI_AUDIT_MODULE = "privacyidea.lib.auditmodules.sqlaudit"
    PI_AUDIT_KEY_PRIVATE = os.path.join(basedir, "tests/testdata/private.pem")
    PI_AUDIT_KEY_PUBLIC = os.path.join(basedir, "tests/testdata/public.pem")
    PI_LOGFILE = "privacyidea.log"
    PI_LOGLEVEL = logging.INFO
    CACHE_TYPE = "simple"
    PI_EXTERNAL_LINKS = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # PI_GNUPG_HOME = "gpg"
    # PI_LOGO = "otherlogo.png"
    # PI_AUDIT_SQL_URI = sqlite://
    PI_VASCO_LIBRARY = None
    PI_CUSTOM_CSS = False


class DevelopmentConfig(Config):
    DEBUG = True
    SECRET_KEY = os.environ.get(ConfigKey.SECRET_KEY) or 't0p s3cr3t'
    SQLALCHEMY_DATABASE_URI = os.environ.get(ConfigKey.DEV_DATABASE_URL) or \
        'sqlite:///' + os.path.join(basedir, 'data-dev.sqlite')
    PI_LOGLEVEL = logging.DEBUG
    PI_TRANSLATION_WARNING = "[Missing]"


class TestingConfig(Config):
    TESTING = True
    # This is used to encrypt the auth token
    SUPERUSER_REALM = ['adminrealm']
    SECRET_KEY = 'secret'  # nosec B105 # used for testing
    SQLALCHEMY_DATABASE_URI = os.environ.get(ConfigKey.TEST_DATABASE_URL) or \
        'sqlite:///' + os.path.join(basedir, 'data-test.sqlite')
    # This is used to encrypt the admin passwords
    PI_PEPPER = ""
    # This is only for testing encrypted files
    PI_ENCFILE_ENC = "tests/testdata/enckey.enc"
    PI_LOGLEVEL = logging.INFO
    PI_GNUPG_HOME = "tests/testdata/gpg"
    PI_AUDIT_SQL_TRUNCATE = True
    CACHE_TYPE = "None"
    PI_SCRIPT_HANDLER_DIRECTORY = "tests/testdata/scripts/"
    PI_NOTIFICATION_HANDLER_SPOOLDIRECTORY = "tests/testdata/"
    PI_NODE_UUID = "8e4272a9-9037-40df-8aa3-976e4a04b5a9"
    PI_NODE = "Node1"
    PI_ENGINE_REGISTRY_CLASS = "null"
    PI_EMAIL_VALIDATOR_MODULES = ["tests.testdata.gmailvalidator"]
    PI_TRUSTED_JWT = [{"public_key": pubtest_key,
                       "algorithm": "HS256",
                       "role": "user",
                       "realm": "realm1",
                       "username": "userA",
                       "resolver": "resolverX"},
                      {"public_key": non_matching_pubkey,
                       "algorithm": "RS256",
                       "role": "user",
                       "realm": "realm1",
                       "username": "userA",
                       "resolver": "resolverX"},
                      {"public_key": pubtest_key,
                       "algorithm": "RS256",
                       "role": "user",
                       "realm": "realmX",
                       "resolver": "resolverX",
                       "username": "h.*s"},
                      {"public_key": pubtest_key,
                       "algorithm": "RS256",
                       "role": "user",
                       "realm": "realm1",
                       "username": "userA",
                       "resolver": "resolverX"}]


class AltUIConfig(TestingConfig):
    PI_INDEX_HTML = "testui.html"
    PI_STATIC_FOLDER = "../tests/testdata/altstatic"
    PI_TEMPLATE_FOLDER = "../tests/testdata/altstatic/templates"


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data.sqlite')
    # This is used to encrypt the auth_token
    SECRET_KEY = os.environ.get(ConfigKey.SECRET_KEY) or _random_password(24)
    # This is used to encrypt the admin passwords
    PI_PEPPER = "Never know..."
    # This is used to encrypt the token data and token passwords
    PI_ENCFILE = os.path.join(basedir, "enckey")
    # This is used to sign the audit log
    PI_AUDIT_KEY_PRIVATE = os.path.join(basedir, "private.pem")
    PI_AUDIT_KEY_PUBLIC = os.path.join(basedir, "public.pem")
    PI_LOGLEVEL = logging.INFO
    SUPERUSER_REALM = ['superuser']


docker_secrets_dir = Path("/run/secrets/")


def _get_secrets_from_environment(name: str) -> str | None:
    if f"{name}_FILE" in os.environ:
        file_name = os.environ[f"{name}_FILE"]
        try:
            with open(file_name) as f:
                return f.read().strip()
        except IOError as _e:
            sys.stderr.write(f"Could not read secret from file defined in variable '{name}_FILE'\n")
    return os.getenv(name)


def _get_secrets_paths_from_environment(path: str, name: str) -> str | None:
    if (docker_secrets_dir / path).is_file():
        return str(docker_secrets_dir / path)
    elif name in os.environ:
        if Path(os.environ[name]).is_file():
            return os.environ[name]
        else:
            sys.stderr.write(f"Could not read secret file path defined in variable '{name}'\n")
            return None
    else:
        return None


class DockerConfig:

    # Try to set the database url from the environment variables
    # First we try if the URL component was set individually
    if db_password := _get_secrets_from_environment(ConfigKey.DB_PASSWORD):
        PI_DB_PASSWORD = db_password

        if all(x in os.environ for x in [ConfigKey.DB_USER, ConfigKey.DB_HOST]) and PI_DB_PASSWORD:
            SQLALCHEMY_DATABASE_URI = "{0}://{1}:{2}@{3}{4}/{5}{6}".format(
                os.getenv(ConfigKey.DB_DRIVER, 'mysql+pymysql'),
                os.getenv(ConfigKey.DB_USER),
                PI_DB_PASSWORD,
                os.getenv(ConfigKey.DB_HOST),
                f":{os.getenv(ConfigKey.DB_PORT)}" if ConfigKey.DB_PORT in os.environ else "",
                os.getenv(ConfigKey.DB_NAME, ""),
                f"?{os.getenv(ConfigKey.DB_EXTRA_PARAMS)}" if ConfigKey.DB_EXTRA_PARAMS in os.environ else ""
            )
    # If the complete SQLALCHEMY_DATABASE_URI is given in the environment (secret)
    # it overwrites the one combined from components
    if sqlalchemy_db_url := _get_secrets_from_environment(ConfigKey.SQLALCHEMY_DATABASE_URI):
        SQLALCHEMY_DATABASE_URI = sqlalchemy_db_url
    if pi_pepper := _get_secrets_from_environment(ConfigKey.PEPPER):
        PI_PEPPER = pi_pepper
    if secret_key := _get_secrets_from_environment(ConfigKey.SECRET_KEY):
        SECRET_KEY = secret_key

    if enc_key := _get_secrets_paths_from_environment("enckey", ConfigKey.ENCFILE):
        PI_ENCFILE = enc_key
    if audit_key_public := _get_secrets_paths_from_environment("audit_key_public",
                                                               ConfigKey.AUDIT_KEY_PUBLIC):
        PI_AUDIT_KEY_PUBLIC = audit_key_public
    if audit_key_private := _get_secrets_paths_from_environment("audit_key_private",
                                                                ConfigKey.AUDIT_KEY_PRIVATE):
        PI_AUDIT_KEY_PRIVATE = audit_key_private

    PI_AUDIT_MODULE = "privacyidea.lib.auditmodules.sqlaudit"
    PI_AUDIT_SQL_TRUNCATE = True


config = {
    'development': DevelopmentConfig,
    'docker': DockerConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
    'altUI': AltUIConfig
}
