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
# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Shared test support to assert that a secret is compared in constant time: ``recorded_compare_digest()`` records the
arguments of every ``hmac.compare_digest()`` call, which is what ``privacyidea.lib.crypto.safe_compare()`` uses.
"""
import hmac
from collections.abc import Iterator
from contextlib import contextmanager
from unittest import mock

from privacyidea.lib.utils import to_bytes


class CompareDigestSpy:
    def __init__(self):
        self.calls: list[tuple] = []

    def saw(self, first, second) -> bool:
        """Whether the two values were compared with each other, in either order."""
        pair = (to_bytes(first), to_bytes(second))
        return pair in self.calls or pair[::-1] in self.calls


@contextmanager
def recorded_compare_digest() -> Iterator[CompareDigestSpy]:
    spy = CompareDigestSpy()
    real_compare_digest = hmac.compare_digest

    def record(first, second):
        spy.calls.append((to_bytes(first), to_bytes(second)))
        return real_compare_digest(first, second)

    with mock.patch("hmac.compare_digest", side_effect=record):
        yield spy
