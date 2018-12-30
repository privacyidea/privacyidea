# -*- coding: utf-8 -*-
#
#  2018-08-08   Friedrich Weber <friedrich.weber@netknights.it>
#               Add a lifecycle module that allows to
#               register functions to be called after the request
#               has been handled.
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
import logging
from privacyidea.lib.framework import get_request_local_store

log = logging.getLogger(__name__)


def register_finalizer(func):
    """
    Register ``func`` to be called after the request has ended (this includes
    cases in which an error has been thrown)
    :param func: a function that takes no arguments
    """
    # from http://flask.pocoo.org/snippets/53/
    store = get_request_local_store()
    if 'call_on_teardown' not in store:
        store['call_on_teardown'] = []
    store['call_on_teardown'].append(func)


def call_finalizers():
    """
    Call all finalizers that have been registered with the current request.
    Exceptions will be caught and written to the log.
    """
    store = get_request_local_store()
    if 'call_on_teardown' in store:
        for func in store['call_on_teardown']:
            try:
                func()
            except Exception as exx:
                log.warning(u"Caught exception in finalizer: {!r}".format(exx))
                log.debug(u"Exception in finalizer:", exc_info=True)
        store['call_on_teardown'] = []
