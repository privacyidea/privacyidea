# SPDX-FileCopyrightText: (C) 2025 NetKnights GmbH <https://netknights.it>
# SPDX-FileCopyrightText: (C) 2025 Paul Lettich <paul.lettich@netknights.it>
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
import logging
from typing import Optional

from sqlalchemy import Sequence, Unicode, Integer, select, update
from sqlalchemy.orm import Mapped, mapped_column

from privacyidea.lib.log import log_with
from privacyidea.models import db
from privacyidea.models.config import TimestampMethodsMixin

log = logging.getLogger(__name__)


class Serviceid(TimestampMethodsMixin, db.Model):
    """
    The serviceid table contains the defined service IDs. These service ID
    describe services like "webservers" or "dbservers" which e.g. request SSH keys
    from the privacyIDEA system.
    """
    __tablename__ = 'serviceid'
    id: Mapped[int] = mapped_column(Integer, Sequence("serviceid_seq"), primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(Unicode(255), default='', unique=True, nullable=False)
    Description: Mapped[Optional[str]] = mapped_column(Unicode(2000), default='')

    @log_with(log)
    def __init__(self, servicename, description=None):
        self.name = servicename
        self.Description = description
