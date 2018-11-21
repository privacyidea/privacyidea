# -*- coding: utf-8 -*-
#
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


def get_app_local_store():
    """
    Get a dictionary which is local to the current flask application,
    but shared among all threads.
    :return: a Python dict
    """
    # We can use ``setdefault`` here because starting from
    # Python 2.7.3 and 3.2.3, it is guaranteed to be atomic.
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


__all__ = ['get_app_local_store', 'get_request_local_store',
           'get_app_config', 'get_app_config_value', '_']
