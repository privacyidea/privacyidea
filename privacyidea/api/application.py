# http://www.privacyidea.org
# (c) Cornelius Kölbel, privacyidea.org
#
# 2015-02-26 Cornelius Kölbel, <cornelius@privacyidea.org>
#            Initial writeup
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
"""
The application REST API exposes which machine application plugins
(``ssh``, ``luks``, ``offline``, ...) are known to this server and which
configuration options each plugin accepts per token type.

Application plugins are used to attach tokens to machines so the token
can authenticate the user against the machine in a specific context (SSH
login, LUKS unlock, offline OTP, ...). See :ref:`application_plugins` for
the conceptual chapter and :ref:`rest_machine` for the endpoints that
actually create the attachments.
"""
from flask import (Blueprint)
from .lib.utils import (send_result)
from ..lib.log import log_with
from flask import g
import logging
from privacyidea.lib.applications import get_application_types


log = logging.getLogger(__name__)


application_blueprint = Blueprint('application_blueprint', __name__)


@application_blueprint.route('/', methods=['GET'])
@log_with(log)
def get_applications():
    """
    Return the application plugins available on this server and the
    configuration options each plugin accepts per token type.

    The response is a dictionary keyed by application name (``ssh``, ``luks``,
    ``offline``, ...). Each entry has an ``options`` sub-dictionary that is
    keyed by token type, and each token-type entry maps option names to a
    type descriptor. This is consumed by the WebUI when an admin attaches a
    token to a machine.

    Requires admin authentication.

    **Example request**:

    .. sourcecode:: http

       GET /application/ HTTP/1.1
       Host: example.com
       Accept: application/json

    **Example response**:

    .. sourcecode:: http

       HTTP/1.1 200 OK
       Content-Type: application/json

       {
         "id": 1,
         "jsonrpc": "2.0",
         "result": {
           "status": true,
           "value": {
             "luks": {
               "options": {
                 "totp": {
                   "slot": {"type": "int"},
                   "partition": {"type": "str"}
                 }
               }
             },
             "ssh": {
               "options": {
                 "sshkey": {
                   "user": {"type": "str"}
                 }
               }
             }
           }
         },
         "version": "privacyIDEA unknown"
       }

    :status 200: applications dict in ``result.value``.
    """
    res = get_application_types()
    g.audit_object.log({"success": True})
    return send_result(res)
