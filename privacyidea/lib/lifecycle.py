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
from collections.abc import Callable
from typing import Any

from flask import Flask
from sqlalchemy import event
from sqlalchemy.orm import Session

from privacyidea.lib.framework import get_request_local_store, is_request_context

log = logging.getLogger(__name__)

#: Key in the request-local store of the finalizers of the current request
REQUEST_FINALIZERS_KEY = "call_on_teardown"
#: Key in the request-local store of the finalizers that were registered outside a request
APP_CONTEXT_FINALIZERS_KEY = "call_on_app_context_teardown"


def register_finalizer(func):
    """
    Register ``func`` to be called after the request has ended (this includes
    cases in which an error has been thrown).

    Outside a request, for example in ``pi-manage`` or a cron job, ``func`` is called when
    the application context ends (see :py:func:`init_finalizers`). A request that runs in the
    same application context does not call it.

    :param func: a function that takes no arguments
    """
    # from http://flask.pocoo.org/snippets/53/
    key = REQUEST_FINALIZERS_KEY if is_request_context() else APP_CONTEXT_FINALIZERS_KEY
    get_request_local_store().setdefault(key, []).append(func)


def register_session_finalizer(session: Session, func: Callable[[], None]) -> None:
    """
    Register ``func``, which closes ``session``, as a finalizer, and register it again whenever
    the session begins a transaction after ``func`` ran.

    An object can use its session again after its finalizer closed it, for example in a streamed
    response, whose lines are read after the teardown of the request. The session then opens a new
    connection, and without a new finalizer nothing closes it. The new finalizer belongs to the
    request or the application context in which the session is used again.

    :param session: the session that ``func`` closes
    :param func: a function that takes no arguments
    """
    registered = False

    def finalize() -> None:
        nonlocal registered
        registered = False
        func()

    def register(*_args: Any) -> None:
        nonlocal registered
        if not registered:
            registered = True
            register_finalizer(finalize)

    register()
    event.listen(session, "after_begin", register)


def _call_registered_finalizers(key: str) -> None:
    store = get_request_local_store()
    if key in store:
        for func in store[key]:
            try:
                func()
            except Exception as exx:
                log.warning(f"Caught exception in finalizer: {exx!r}")
                log.debug("Exception in finalizer:", exc_info=True)
        store[key] = []


def call_finalizers() -> None:
    """
    Call all finalizers that have been registered with the current request.
    Exceptions will be caught and written to the log.
    """
    _call_registered_finalizers(REQUEST_FINALIZERS_KEY)


def call_app_context_finalizers() -> None:
    """
    Call all finalizers that have been registered outside a request in the current
    application context. Exceptions will be caught and written to the log.
    """
    _call_registered_finalizers(APP_CONTEXT_FINALIZERS_KEY)


def _call_finalizers_on_teardown(_exception: BaseException | None) -> None:
    # A request calls its finalizers in its own teardown, so normally none of them are left.
    call_finalizers()
    call_app_context_finalizers()


def init_finalizers(app: Flask) -> None:
    """
    Call the finalizers registered outside a request when an application context of *app* ends.

    A request calls its finalizers in its own teardown. Code outside a request, for example a
    command line tool, has no request teardown, so without this its finalizers never run. A
    database connection that such a finalizer has to close then stays open until the process
    exits, and the database server logs the dropped connection.

    :param app: the privacyIDEA app
    """
    app.teardown_appcontext(_call_finalizers_on_teardown)
