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

import os
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
    DEV_DATABASE_URL = "DEV_DATABASE_URL"
    TEST_DATABASE_URL = "TEST_DATABASE_URL"
    DB_EXTRA_PARAMS = "DB_EXTRA_PARAMS"

    AUDIT_KEY_PRIVATE = "PI_AUDIT_KEY_PRIVATE"
    AUDIT_KEY_PUBLIC = "PI_AUDIT_KEY_PUBLIC"
    AUDIT_MODULE = "PI_AUDIT_MODULE"
    AUDIT_SERVERNAME = "PI_AUDIT_SERVERNAME"
    AUDIT_SQL_TRUNCATE = "PI_AUDIT_SQL_TRUNCATE"
    AUDIT_NO_SIGN = "PI_AUDIT_NO_SIGN"

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


def _random_password(size):
    log.info("SECRET_KEY not set in config. Generating a random key.")
    passwd = [secrets.choice(string.ascii_lowercase + \
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


class DockerConfig:
    secrets_dir = Path("/run/secrets/")
    # Try to set the database uri from the environment variables
    if ConfigKey.SQLALCHEMY_DATABASE_URI in os.environ:
        SQLALCHEMY_DATABASE_URI = os.getenv(ConfigKey.SQLALCHEMY_DATABASE_URI)
    elif all(x in os.environ for x in ["DB_API", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME"]):
        SQLALCHEMY_DATABASE_URI = ("{DB_API}://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:"
                                   "{DB_PORT}/{DB_NAME}").format(**os.environ)
        if ConfigKey.DB_EXTRA_PARAMS in os.environ:
            SQLALCHEMY_DATABASE_URI += f"?{os.getenv(ConfigKey.DB_EXTRA_PARAMS)}"

    PI_AUDIT_MODULE = "privacyidea.lib.auditmodules.sqlaudit"
    PI_AUDIT_SQL_TRUNCATE = True

    if (secrets_dir / "enckey").is_file():
        PI_ENCFILE = str(secrets_dir / "enckey")
    if (secrets_dir / "pi_audit_key_public").is_file():
        PI_AUDIT_KEY_PUBLIC = str(secrets_dir / "pi_audit_key_public")
    if (secrets_dir / "pi_audit_key_private").is_file():
        PI_AUDIT_KEY_PRIVATE = str(secrets_dir / "pi_audit_key_private")

    try:
        with open(secrets_dir / "secret_key", "r") as f:
            SECRET_KEY = f.read().strip()
    except IOError as _e:
        if ConfigKey.SECRET_KEY in os.environ:
            SECRET_KEY = os.getenv(ConfigKey.SECRET_KEY)
    try:
        with open(secrets_dir / "pi_pepper", "r") as f:
            PI_PEPPER = f.read().strip()
    except IOError as _e:
        if ConfigKey.PEPPER in os.environ:
            PI_PEPPER = os.getenv(ConfigKey.PEPPER)


config = {
    'development': DevelopmentConfig,
    'docker': DockerConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
    'altUI': AltUIConfig
}
