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

from sqlalchemy import Sequence, Unicode, Integer, Boolean, CheckConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column

from privacyidea.models import db
from privacyidea.models.utils import MethodsMixin

log = logging.getLogger(__name__)


class PrivacyIDEAServer(MethodsMixin, db.Model):
    """
    This table can store remote privacyIDEA server definitions
    """
    __tablename__ = 'privacyideaserver'
    id: Mapped[int] = mapped_column(Integer, Sequence("privacyideaserver_seq"),
                                    primary_key=True)
    # This is a name to refer to
    identifier: Mapped[str] = mapped_column(Unicode(255), nullable=False, unique=True)
    # This is the FQDN or the IP address
    url: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    tls: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    description: Mapped[Optional[str]] = mapped_column(Unicode(2000), default='')


class RADIUSServer(MethodsMixin, db.Model):
    """
    This table can store configurations of RADIUS servers.
    https://github.com/privacyidea/privacyidea/issues/321

    It saves
    * a unique name
    * a description
    * an IP address a
    * a Port
    * a secret
    * timeout in seconds (default 5)
    * retries (default 3)

    These RADIUS server definitions can be used in RADIUS tokens or in a
    radius passthru policy.
    """
    __tablename__ = 'radiusserver'
    __table_args__ = (
        CheckConstraint("options IS JSON", name="radiusserver_options_is_json",
                        _create_rule=lambda compiler: compiler.dialect.name == "oracle"),
    )
    id: Mapped[int] = mapped_column(Integer, Sequence("radiusserver_seq"), primary_key=True)
    # This is a name to refer to
    identifier: Mapped[str] = mapped_column(Unicode(255), nullable=False, unique=True)
    # This is the FQDN or the IP address
    server: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    port: Mapped[Optional[int]] = mapped_column(Integer, default=25)
    secret: Mapped[Optional[str]] = mapped_column(Unicode(255), default="")
    dictionary: Mapped[Optional[str]] = mapped_column(Unicode(255), default="/etc/privacyidea/dictionary")
    description: Mapped[Optional[str]] = mapped_column(Unicode(2000), default='')
    timeout: Mapped[Optional[int]] = mapped_column(Integer, default=5)
    retries: Mapped[Optional[int]] = mapped_column(Integer, default=3)
    options: Mapped[Optional[dict]] = mapped_column(JSON)


class SMTPServer(MethodsMixin, db.Model):
    """
    This table can store configurations for SMTP servers.
    Each entry represents an SMTP server.
    EMail Token, SMS SMTP Gateways or Notifications like PIN handlers are
    supposed to use a reference to a server definition.
    Each Machine Resolver can have multiple configuration entries.
    The config entries are referenced by the id of the machine resolver
    """
    __tablename__ = 'smtpserver'
    id: Mapped[int] = mapped_column(Integer, Sequence("smtpserver_seq"), primary_key=True)
    # This is a name to refer to
    identifier: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    # This is the FQDN or the IP address
    server: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    port: Mapped[Optional[int]] = mapped_column(Integer, default=25)
    username: Mapped[Optional[str]] = mapped_column(Unicode(255), default="")
    password: Mapped[Optional[str]] = mapped_column(Unicode(255), default="")
    sender: Mapped[Optional[str]] = mapped_column(Unicode(255), default="")
    tls: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    description: Mapped[Optional[str]] = mapped_column(Unicode(2000), default='')
    timeout: Mapped[Optional[int]] = mapped_column(Integer, default=10)
    enqueue_job: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def get(self):
        """
        :return: the configuration as a dictionary
        """
        return {
            "id": self.id,
            "identifier": self.identifier,
            "server": self.server,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "sender": self.sender,
            "tls": self.tls,
            "description": self.description,
            "timeout": self.timeout,
            "enqueue_job": self.enqueue_job,
        }
