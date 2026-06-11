#  2018-11-15   Friedrich Weber <friedrich.weber@netknights.it>
#               Add a framework module to reduce the coupling to flask
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
from flask import current_app, g
# We import the gettext function here and export it as ``_``.
from flask_babel import gettext as _

from privacyidea.config import ConfigKey
from privacyidea.lib.error import ConfigAdminError


def get_app_local_store():
    """
    Get a dictionary which is local to the current flask application,
    but shared among all threads.
    :return: a Python dict
    """
    return current_app.config.setdefault('_app_local_store', {})


def get_request_local_store():
    """
    Get a dictionary which is local to the current request. Thus, it
    is not shared among threads.
    :return: a Python dict
    """
    if '_request_local_store' not in g:
        g._request_local_store = {}
    return g._request_local_store


def get_app_config():
    """
    Get all configuration options of the current app.
    :return: a dict-compatible object
    """
    return current_app.config


def get_app_config_value(key, default=None):
    """
    Get a specific configuration option of the current app.
    :param key: a string key
    :param default: a default value, returned if the config does not contain ``key``
    :return: the config value or the default value
    """
    return get_app_config().get(key, default)


def get_base_url(required=False):
    """
    Return the trusted public base URL of this privacyIDEA server.

    This is used to build user-facing links that are sent out of band (the
    password-recovery link, the ``{url}`` notification tag, ...). Such links are
    never derived from the inbound HTTP ``Host`` header.
    The value is taken solely from the ``PI_BASE_URL`` app configuration (set in ``pi.cfg``).

    If ``PI_BASE_URL`` is not configured:

    * with ``required=True`` a :class:`~privacyidea.lib.error.ConfigAdminError`
      is raised. This is used for security-critical links such as the
      password-recovery link.
    * otherwise an empty string is returned. The missing configuration is announced once at
      startup (see ``app.py``).

    :param required: if True, raise instead of returning an empty base URL
    :return: the trusted base URL (without a trailing slash), or ``""`` if unset
    """
    base_url = get_app_config_value(ConfigKey.BASE_URL)
    if base_url:
        return base_url.rstrip("/")
    if required:
        raise ConfigAdminError(
            "PI_BASE_URL is not configured. Refusing to build a user-facing link "
            "without a trusted base URL. Set PI_BASE_URL in pi.cfg to the public URL of "
            "this privacyIDEA server.")
    return ""


__all__ = ['get_app_local_store', 'get_request_local_store',
           'get_app_config', 'get_app_config_value', 'get_base_url', '_']
