# SPDX-FileCopyrightText: 2016 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later

#  2016-08-30 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Save client application information for authentication requests
#
# License:  AGPLv3
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
#
__doc__ = """Save and list client application information.
Client Application information was saved during authentication requests.

The code is tested in tests/test_lib_clientapplication.py.
"""

import logging
import traceback
from datetime import datetime

from netaddr import IPAddress
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, OperationalError

from privacyidea.lib.config import get_privacyidea_node
from privacyidea.lib.framework import get_app_config_value, get_app_local_store
from .log import log_with
from ..models import ClientApplication, db

log = logging.getLogger(__name__)

# ``save_clientapplication`` runs as a policy on every /validate/check request,
# and the only thing it records is that a client was seen just now. Writing that
# on every single request costs a SELECT, an UPDATE and a COMMIT per
# authentication - a cluster-wide write in a replicated setup - to keep a column
# accurate to the second that is only ever read as "when was this client last
# around". Remembering per worker when we last wrote a client's row lets us skip
# the writes in between.
_LAST_WRITE_KEY = '_clientapplication_last_write'
_DEFAULT_WRITE_INTERVAL_SECONDS = 60

# A worker tracks one entry per client it has seen within the interval. That is
# bounded in practice, but a server reached from very many addresses should not
# grow the dictionary without end, so it is pruned once it passes this size.
# Entries older than the interval are useless, which is what pruning drops.
_MAX_TRACKED_CLIENTS = 2048


def _write_interval_seconds() -> int:
    """
    Return how many seconds a client's row may keep its old ``lastseen`` before
    it is written again, or 0 to write on every request.
    """
    raw = get_app_config_value('PI_CLIENTAPPLICATION_WRITE_INTERVAL', _DEFAULT_WRITE_INTERVAL_SECONDS)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        log.warning(f"PI_CLIENTAPPLICATION_WRITE_INTERVAL is not a number ({raw!r}), "
                    f"using {_DEFAULT_WRITE_INTERVAL_SECONDS}s.")
        return _DEFAULT_WRITE_INTERVAL_SECONDS
    return max(value, 0)


def _written_within(client_key: tuple, interval: int) -> bool:
    """
    Return True if this worker wrote the given client's row less than
    ``interval`` seconds ago.

    The age is measured on the same clock the ``lastseen`` column is written
    from, because that is what the interval is about: how stale the recorded
    timestamp may become. A clock set backwards can therefore hold a refresh
    back for as long as the jump, which for a "last seen" column is not worth
    guarding against.

    Only ever reads. The timestamp is recorded in :py:func:`_note_write` after
    the row has actually been written, so a write that fails is retried on the
    next request instead of being skipped for a whole interval.
    """
    last_write = get_app_local_store().get(_LAST_WRITE_KEY, {}).get(client_key)
    return last_write is not None and (datetime.now() - last_write).total_seconds() < interval


def _note_write(client_key: tuple, interval: int) -> None:
    """Remember that this client's row was just written."""
    if not interval:
        # Nothing is being skipped, so there is nothing to remember
        return
    last_writes = get_app_local_store().setdefault(_LAST_WRITE_KEY, {})
    now = datetime.now()
    last_writes[client_key] = now
    if len(last_writes) <= _MAX_TRACKED_CLIENTS:
        return
    try:
        by_age = sorted(last_writes.items(), key=lambda item: item[1])
    except RuntimeError:
        # Another thread added a client while we were looking. Nothing here has
        # to be exact - the entries are only there to skip writes - so leave the
        # pruning to whoever gets there next
        return
    # Entries past the interval are useless, and dropping those is usually
    # enough. It is not enough when more clients than the bound are seen inside
    # one interval - a deployment reached from very many addresses - because
    # then every entry is still fresh. So the oldest are dropped either way, and
    # the worst case is that those clients pay one write again.
    doomed = [key for key, written_at in by_age
              if (now - written_at).total_seconds() >= interval]
    if len(last_writes) - len(doomed) > _MAX_TRACKED_CLIENTS:
        keep_from = len(last_writes) - _MAX_TRACKED_CLIENTS
        doomed = [key for key, _written_at in by_age[:keep_from]]
    for key in doomed:
        last_writes.pop(key, None)


@log_with(log)
def save_clientapplication(ip: IPAddress | str, clienttype: str):
    """
    Save (or update) the IP and the clienttype to the database table.

    Only the fact that the client was seen is recorded, so the row is not
    rewritten on every request: a client whose row this worker wrote less than
    ``PI_CLIENTAPPLICATION_WRITE_INTERVAL`` seconds ago is left alone. The
    ``lastseen`` column is then behind by at most that interval, which is
    invisible in both places it is read - the client list in the WebUI and the
    metering of plugin traffic. Set the interval to 0 to write on every request.

    :param ip: The IP address of the requesting client.
    :type ip: well formatted string or IPAddress
    :param clienttype: The type of the client
    :type ip: basestring
    :return: None
    """
    node = get_privacyidea_node()
    # Check for a valid IP address
    ip = IPAddress(ip)
    client_key = (node, f"{ip}", clienttype)
    write_interval = _write_interval_seconds()
    if write_interval and _written_within(client_key, write_interval):
        return
    last_seen = datetime.now()
    # TODO: resolve hostname

    stmt = select(ClientApplication).where(
        ClientApplication.ip == f"{ip}",
        ClientApplication.clienttype == clienttype,
        ClientApplication.node == node
    )
    client_app = db.session.execute(stmt).scalar_one_or_none()

    if client_app:
        client_app.lastseen = last_seen
    else:
        client_app = ClientApplication(ip=f"{ip}", clienttype=clienttype, node=node, lastseen=last_seen)
        db.session.add(client_app)
    try:
        db.session.commit()
        _note_write(client_key, write_interval)
    except (IntegrityError, OperationalError) as e:  # pragma: no cover
        db.session.rollback()
        log.info(f'Unable to write ClientApplication entry to db: {e}')
        log.debug(traceback.format_exc())


@log_with(log)
def get_clientapplication(ip=None, clienttype=None, group_by="clienttype"):
    """
    Return ClientApplications.

    :param ip: The IP address of the requesting client.
    :type ip: well formatted string or IPAddress
    :param clienttype: The type of the client
    :type ip: basestring
    :param group_by: can either be "ip" or "clienttype"
    :return: dictionary either grouped by clienttype or ip

    {"PAM": [{ <client1> },{ <client2> }, { <client3> }],
     "SAML": [ { <client2> } ]
    }
    """
    clients = {}
    # We group the results by IP, hostname and clienttype. Then, the rows in each group
    # only differ in the respective node names and the "lastseen" timestamp. Hence, we
    # then fetch MAX(lastseen) of each group to retrieve the most recent timestamp at
    # which the client was seen on *any* node. It is written to the ``max_lastseen``
    # attribute.
    stmt = select(ClientApplication.ip,
                  ClientApplication.hostname,
                  ClientApplication.clienttype,
                  func.max(ClientApplication.lastseen).label("max_lastseen"))
    if ip:
        # Check for a valid IP address
        ip = IPAddress(ip)
        stmt = stmt.where(ClientApplication.ip == f"{ip}")

    if clienttype:
        stmt = stmt.where(ClientApplication.clienttype == clienttype)

    stmt = stmt.group_by(ClientApplication.ip,
                         ClientApplication.hostname,
                         ClientApplication.clienttype)

    applications = db.session.execute(stmt).all()
    for row in applications:
        if group_by.lower() == "clienttype":
            clients.setdefault(row.clienttype, []).append({"ip": row.ip,
                                                           "hostname": row.hostname,
                                                           "lastseen": row.max_lastseen})
        else:
            clients.setdefault(row.ip, []).append({"hostname": row.hostname,
                                                   "clienttype": row.clienttype,
                                                   "lastseen": row.max_lastseen})
    return clients
