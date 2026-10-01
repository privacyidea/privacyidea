# SPDX-FileCopyrightText: (C) 2026 NetKnights GmbH <https://netknights.it>
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
"""
Keeps passlib 1.7.4, which is no longer maintained, working with current bcrypt releases.

Two changes in bcrypt break it:

1. bcrypt 4.1.0 removed ``__about__.__version__``, which passlib reads to detect the version.
   https://github.com/pyca/bcrypt/issues/684
2. bcrypt 5.0.0 raises a ValueError for passwords longer than 72 bytes instead of truncating them.
   passlib hashes such a password while it loads the bcrypt backend, so the backend fails to load
   and every bcrypt hash and verification fails with it.

passlib loads the bcrypt backend on the first bcrypt hash or verification, not on import. Every module
that builds a CryptContext which can contain bcrypt imports this module, so the patch is in place
before that happens, whichever of them is used first.

Remove this module once passlib is replaced.
"""
from types import SimpleNamespace

import bcrypt

# bcrypt only uses the first 72 bytes of a password; releases before 5.0.0 dropped the rest silently.
BCRYPT_MAX_PASSWORD_BYTES = 72

_original_hashpw = bcrypt.hashpw


def _hashpw_truncating(password: bytes, salt: bytes) -> bytes:
    if isinstance(password, bytes) and len(password) > BCRYPT_MAX_PASSWORD_BYTES:
        password = password[:BCRYPT_MAX_PASSWORD_BYTES]
    return _original_hashpw(password, salt)


if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = SimpleNamespace(__version__=bcrypt.__version__)
bcrypt.hashpw = _hashpw_truncating
