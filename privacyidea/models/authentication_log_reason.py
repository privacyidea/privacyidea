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

from sqlalchemy import ForeignKey, Identity, Index
from sqlalchemy.orm import Mapped, mapped_column

from privacyidea.models import db
from privacyidea.models.utils import BigIntegerType, case_sensitive_unicode

# Maximum length of the string columns; the lib layer truncates values to these lengths before insert (see
# privacyidea.lib.conditional_access.authentication_log), the same contract as authentication_log_column_length.
authentication_log_reason_column_length = {
    # An AuthEventReason value; sized like the parent's event_type, which the longest member stays well inside.
    "reason": 40,
}


class AuthenticationLogReason(db.Model):
    """
    Why an authentication-log row came out the way it did: one row per :class:`AuthEventReason` the request produced,
    ordered by :data:`~privacyidea.lib.conditional_access.authentication_event_types.REASON_PRECEDENCE` (highest
    signal first) as their ids ascend.

    A request rarely fails for exactly one reason - a user with three tokens can have one revoked, one past its
    failcount and one that simply got the wrong OTP - so the reasons are a **list**, not the single highest-ranked
    one. Kept in a table of its own rather than as a column on the parent for the reason the parent's column existed
    at all: "every NO_USABLE_TOKEN caused by the failcounter" has to be a plain indexed predicate, and neither a
    separator-joined string (``LIKE`` scans, a length limit) nor a JSON array (predicates differ per backend) offers
    one. What is specific to one request - the deciding policy's name, which serial failed for which reason - still
    stays in the parent's ``other_info``.

    Like :class:`~privacyidea.models.conditional_access_outcome.ConditionalAccessOutcome`, a row belongs to its
    ``authentication_log`` row (``auth_log_id``, a real foreign key that cascades), is only ever read together with
    it - via ``selectinload``, never a ``JOIN``, which would multiply the parent row and break both ``LIMIT`` and the
    pagination count - and repeats nothing the parent already holds.

    Deliberately **without** :class:`~privacyidea.models.utils.MethodsMixin`, for the reason the outcome model is: the
    mixin's ``save()``/``delete()`` commit ``db.session``, while these rows are written on the conditional-access
    session so that a failure to record them cannot roll back the request's own work.
    """
    __tablename__ = "authentication_log_reason"
    __table_args__ = (
        # The lookup that loads a log page's reasons and the one the delete paths use to remove an entry's reasons
        # with it.
        Index("ix_authlog_reason_authlog", "auth_log_id"),
        # The filter "every entry with this reason": reason first, so the EXISTS that matches it seeks rather than
        # scans, with auth_log_id alongside so it is answered from the index.
        Index("ix_authlog_reason_reason", "reason", "auth_log_id"),
    )
    # The database generates the id (Oracle/PostgreSQL IDENTITY, MySQL/MariaDB AUTO_INCREMENT, SQLite's rowid alias),
    # so the type stays BigIntegerType: SQLite only aliases rowid for exactly "INTEGER PRIMARY KEY".
    id: Mapped[int] = mapped_column(BigIntegerType, Identity(always=False), primary_key=True)
    # The entry this reason belongs to; mandatory, since a reason without the event it explains is meaningless.
    auth_log_id: Mapped[int] = mapped_column(BigIntegerType,
                                             ForeignKey("authentication_log.id", ondelete="CASCADE"),
                                             nullable=False)
    # An AuthEventReason value.
    reason: Mapped[str] = mapped_column(
        case_sensitive_unicode(authentication_log_reason_column_length["reason"]), nullable=False)
