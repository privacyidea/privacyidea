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

from sqlalchemy import Unicode, Integer, Sequence
from sqlalchemy.orm import Mapped, mapped_column

from privacyidea.models.db import db
from privacyidea.models.utils import MethodsMixin


class PiInternal(MethodsMixin, db.Model):
    """
    This table stores an encrypted check value that is used to verify
    at server startup that the correct encryption key is being used.
    The check value is a known plaintext encrypted with the encryption key.
    """
    __tablename__ = "pi_internal"
    id: Mapped[int] = mapped_column(Integer, Sequence("pi_internal_seq"), primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    check_value: Mapped[str] = mapped_column(Unicode(2000), nullable=False)
