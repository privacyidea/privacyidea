# -*- coding: utf-8 -*-
#
#  2018-08-07   Friedrich Weber <friedrich.weber@netknights.it>
#               Add a shared registry of SQLAlchemy engines to
#               properly implement connection pooling for
#               SQLIdResolvers and SQLAudit modules
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
__doc__ = """
This module implements a so-called engine registry which manages
the SQLAlchemy engines used for connections to external SQL databases
by the SQL audit module and SQLIdResolver.

There should only be one shared registry per application which is
used by all threads. This is necessary to properly implement pooling.

This module is tested in tests/test_lib_pooling.py.
"""

import logging
from threading import Lock

from privacyidea.lib.framework import get_app_local_store, get_app_config_value

log = logging.getLogger(__name__)


class BaseEngineRegistry(object):
    """
    Abstract base class for engine registries.
    """
    def get_engine(self, key, creator):
        """
        Return the engine associated with the key ``key``.
        :param key: An arbitrary hashable Python object
        :param creator: A function with no arguments which returns a new SQLAlchemy engine.
                        Called to initially create an engine.
        :return: an SQLAlchemy engine
        """
        raise NotImplementedError()


class NullEngineRegistry(BaseEngineRegistry):
    """
    A registry which creates a new engine for every request.
    Consequently, engines are not shared among threads and
    no pooling is implemented.

    It can be activated by setting ``PI_ENGINE_REGISTRY_CLASS`` to "null".
    """
    def get_engine(self, key, creator):
        return creator()


class SharedEngineRegistry(BaseEngineRegistry):
    """
    A registry which holds a dictionary mapping a key to an SQLAlchemy engine.

    It can be activated by setting ``PI_ENGINE_REGISTRY_CLASS`` to "shared".
    """
    def __init__(self):
        BaseEngineRegistry.__init__(self)
        self._engine_lock = Lock()
        self._engines = {}

    def get_engine(self, key, creator):
        # This method will be called concurrently by multiple threads.
        # Thus, to be sure that we do not create an engine when there
        # is already one associated with the given key, we use a lock.
        with self._engine_lock:
            if key not in self._engines:
                log.info("Creating a new engine and connection pool for key {!s}".format(key))
                self._engines[key] = creator()
            return self._engines[key]


ENGINE_REGISTRY_CLASSES = {
    "null": NullEngineRegistry,
    "shared": SharedEngineRegistry,
}
DEFAULT_REGISTRY_CLASS_NAME = "null"


def get_registry():
    """
    Return the ``EngineRegistry`` object associated with the current application.
    If there is no such object yet, create one and write it to the app-local store.
    This respects the ``PI_ENGINE_REGISTRY_CLASS`` config option.
    :return: an ``EngineRegistry`` object
    """
    # This function will be called concurrently by multiple threads.
    # This is no problem when we already have an engine registry object.
    # However, if there is no registry object yet, two threads may concurrently
    # decide to create a new one. But as ``setdefault`` is atomic, only the
    # first one will be the written to ``app_store['config']``. The latter
    # one will not be referenced and will be garbage-collected at some point.
    app_store = get_app_local_store()
    try:
        return app_store["engine_registry"]
    except KeyError:
        # create a new engine registry of the appropriate class
        registry_class_name = get_app_config_value("PI_ENGINE_REGISTRY_CLASS", DEFAULT_REGISTRY_CLASS_NAME)
        if registry_class_name not in ENGINE_REGISTRY_CLASSES:
            log.warning("Unknown engine registry class: {!r}".format(registry_class_name))
            registry_class_name = DEFAULT_REGISTRY_CLASS_NAME
        registry = ENGINE_REGISTRY_CLASSES[registry_class_name]()
        log.info("Created a new engine registry: {!r}".format(registry))
        return app_store.setdefault("engine_registry", registry)


def get_engine(key, creator):
    """
    Shortcut to get an engine from the application-global engine registry.
    :return: an SQLAlchemy engine
    """
    return get_registry().get_engine(key, creator)