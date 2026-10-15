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
Database models for first-class webhook configuration objects.

See https://github.com/privacyidea/privacyidea/issues/5751
"""
import logging

from sqlalchemy import (Identity, Unicode, Integer, Boolean, ForeignKey,
                        UnicodeText, delete)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from privacyidea.models import db
from privacyidea.models.utils import MethodsMixin
from privacyidea.lib.crypto import FAILED_TO_DECRYPT_PASSWORD, decryptPassword

log = logging.getLogger(__name__)


class Webhook(MethodsMixin, db.Model):
    """
    A reusable, optionally authenticated webhook endpoint configuration.

    Follows the established pattern of :class:`SMTPServer`, :class:`RADIUSServer`,
    and :class:`SMSGateway`: the object owns the endpoint (URL, method, auth,
    headers, TLS, proxy, timeout) while the call site (event handler or
    Conditional Access stage action) owns the payload.
    """
    __tablename__ = 'webhook'

    # Identity, not a Sequence: it is one id source per column, used by the ORM and by a raw
    # INSERT alike - which the data migration does. A Sequence is known to the ORM only, so on a
    # backend with real sequences (MariaDB) a raw INSERT that omits the column finds no default.
    # Same choice as conditional_access_policies and authentication_log.
    id: Mapped[int] = mapped_column(
        Integer, Identity(always=False), primary_key=True)
    # Human-readable name used to reference this webhook from actions
    identifier: Mapped[str] = mapped_column(
        Unicode(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(
        Unicode(2000), default='')
    # Target URL
    url: Mapped[str] = mapped_column(
        Unicode(2000), nullable=False)
    # HTTP method: POST, PUT, PATCH, GET
    http_method: Mapped[str | None] = mapped_column(
        Unicode(10), default='POST')
    # MIME type for the request body
    content_type: Mapped[str | None] = mapped_column(
        Unicode(100), default='application/json')
    # Optional default body template (overridable per call site)
    default_payload: Mapped[str | None] = mapped_column(
        UnicodeText(), default=None)

    # --- Authentication --------------------------------------------------
    # Supported values: 'none', 'basic', 'header', 'mtls'
    auth_type: Mapped[str | None] = mapped_column(
        Unicode(50), default='none')
    # HTTP Basic auth
    username: Mapped[str | None] = mapped_column(
        Unicode(255), default='')
    # Encrypted at rest via encryptPassword()
    password: Mapped[str | None] = mapped_column(
        Unicode(1024), default='')

    # --- TLS -------------------------------------------------------------
    verify_tls: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True)
    # Optional path to a CA bundle file (passed to requests verify=<path>)
    tls_ca_bundle: Mapped[str | None] = mapped_column(
        Unicode(1024), default='')

    # --- mTLS (mutual TLS) -----------------------------------------------
    client_certificate: Mapped[str | None] = mapped_column(
        Unicode(1024), default='')
    client_key: Mapped[str | None] = mapped_column(
        Unicode(1024), default='')
    # Encrypted at rest via encryptPassword()
    client_key_password: Mapped[str | None] = mapped_column(
        Unicode(1024), default='')

    # --- Proxy -----------------------------------------------------------
    http_proxy: Mapped[str | None] = mapped_column(
        Unicode(1024), default='')
    https_proxy: Mapped[str | None] = mapped_column(
        Unicode(1024), default='')

    # --- Timeout (seconds) -----------------------------------------------
    # Deliberately low default — see issue #5751 "Delivery in V1"
    timeout: Mapped[int | None] = mapped_column(
        Integer, default=3)

    # --- Relationship to child header rows --------------------------------
    headers: Mapped[list["WebhookHeader"]] = relationship(
        'WebhookHeader',
        lazy='dynamic',
        back_populates='webhook',
        cascade='all, delete-orphan',
        passive_deletes=True,
    )

    def delete(self):
        """
        Delete this webhook and all associated headers.
        The cascade on the relationship handles the header deletion, but we
        also issue an explicit delete for safety (mirrors SMSGateway.delete).
        """
        ret = self.id
        delete_stmt = delete(WebhookHeader).where(
            WebhookHeader.webhook_id == ret)
        db.session.execute(delete_stmt)
        db.session.delete(self)
        db.session.commit()
        return ret

    @property
    def header_dict(self):
        """
        Return a dict of header key → decrypted value for all associated headers.

        A value that cannot be decrypted - after an enckey change or a restore from a backup
        without it - becomes an empty string, never the stored ciphertext. This is what the
        callers need: ``fire_webhook()`` would otherwise send the base64 ciphertext to the
        endpoint as a header value, and an uncensored ``export_webhook()`` would write it into
        the export, where re-importing it encrypts it a second time. It is the same treatment
        the two password columns get in
        :func:`~privacyidea.lib.webhook._decrypt_or_empty`; an empty credential fails the
        delivery visibly, a wrong one fails it confusingly.
        """
        res = {}
        for header in self.headers:
            value = header.value
            if header.encrypted and value:
                decrypted = decryptPassword(value)
                if decrypted == FAILED_TO_DECRYPT_PASSWORD:
                    log.warning(f"Failed to decrypt the value of header {header.key!r} of webhook "
                                f"{self.identifier!r}. Returning an empty value.")
                    decrypted = ""
                value = decrypted
            res[header.key] = value
        return res

    def get(self):
        """
        Return the webhook configuration as a dictionary.
        Mirrors :meth:`SMTPServer.get`.
        """
        return {
            "id": self.id,
            "identifier": self.identifier,
            "description": self.description,
            "url": self.url,
            "http_method": self.http_method,
            "content_type": self.content_type,
            "default_payload": self.default_payload,
            "auth_type": self.auth_type,
            "username": self.username,
            "password": self.password,
            "verify_tls": self.verify_tls,
            "tls_ca_bundle": self.tls_ca_bundle,
            "client_certificate": self.client_certificate,
            "client_key": self.client_key,
            "client_key_password": self.client_key_password,
            "http_proxy": self.http_proxy,
            "https_proxy": self.https_proxy,
            "timeout": self.timeout,
            "headers": self.header_dict,
        }


class WebhookHeader(MethodsMixin, db.Model):
    """
    Static HTTP headers for a :class:`Webhook`, one row per header.

    Mirrors :class:`SMSGatewayOption` — a key/value child table with a
    per-header ``encrypted`` flag so that secrets (e.g. ``Authorization``,
    ``X-API-Key``) are stored encrypted at rest.
    """
    __tablename__ = 'webhookheader'

    id: Mapped[int] = mapped_column(
        Integer, Identity(always=False), primary_key=True)
    webhook_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('webhook.id', ondelete='CASCADE'),
        nullable=False, index=True)
    # Header name, e.g. "Authorization", "X-API-Key", "X-Splunk-Request-Channel"
    key: Mapped[str] = mapped_column(
        Unicode(255), nullable=False)
    # Header value — encrypted when ``encrypted`` is set
    value: Mapped[str | None] = mapped_column(
        UnicodeText(), default='')
    # Whether the value is stored encrypted via encryptPassword()
    encrypted: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default='0')

    webhook = relationship("Webhook", back_populates="headers")

    def __init__(self, webhook_id, key, value, encrypted=False):
        """
        Create a new header entry for the given webhook_id.
        """
        self.webhook_id = webhook_id
        self.key = key
        self.value = value
        self.encrypted = encrypted
        self.save()
