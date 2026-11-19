# (c) NetKnights GmbH 2026,  https://netknights.it
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
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
"""
Workarounds for platform differences. Nothing in this module changes the behaviour on Linux.
It is tested in test_lib_utils.py
"""
import select
import time


class SelectPoll:
    """
    A minimal replacement for ``select.poll()`` for platforms that have none (Windows), based on ``select.select()``.
    It only supports waiting for data to read, which is all that is needed.
    """
    POLLIN = 1

    def __init__(self):
        self._sockets = []

    def register(self, fd, eventmask=POLLIN):
        if fd not in self._sockets:
            self._sockets.append(fd)

    def unregister(self, fd):
        try:
            self._sockets.remove(fd)
        except ValueError:
            raise KeyError(fd) from None

    def poll(self, timeout=None):
        """
        Wait for one of the registered sockets to become readable.

        :param timeout: The time to wait in milliseconds, wait forever if it is ``None`` or negative
        :return: A list of ``(fd, event)`` tuples of the sockets that can be read, empty after a timeout
        """
        seconds = None if timeout is None or timeout < 0 else timeout / 1000
        if not self._sockets:
            # select.select() refuses to wait on nothing on Windows
            if seconds:
                time.sleep(seconds)
            return []
        readable, _, _ = select.select(self._sockets, [], [], seconds)
        return [(sock.fileno() if hasattr(sock, "fileno") else sock, self.POLLIN) for sock in readable]


class _SelectModuleWithPoll:
    """The ``select`` module as pyrad sees it: the real one plus ``poll()`` and ``POLLIN``"""
    POLLIN = SelectPoll.POLLIN
    poll = SelectPoll

    def __getattr__(self, name):
        return getattr(select, name)


def make_pyrad_work_without_poll():
    """
    The RADIUS client of pyrad waits for the answer with ``select.poll()``, which does not exist on Windows. Give the
    client module a ``select`` with a ``poll()`` that is based on ``select.select()`` instead.
    Nothing happens if ``select.poll()`` exists. Only the module of pyrad is affected, not the ``select`` module.
    """
    if hasattr(select, "poll"):
        return
    import pyrad.client
    pyrad.client.select = _SelectModuleWithPoll()
