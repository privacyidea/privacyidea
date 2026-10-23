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
The system documentation: a reStructuredText report of the configuration of privacyIDEA.

The report is read by somebody other than the administrators of privacyIDEA, e.g. to learn which kinds of user
stores and tokens are in use and how privacyIDEA is set up. It therefore lists selected settings: the system
configuration and the policies completely, the pi.cfg, the resolvers, the event handlers and the external services
by the settings that describe the setup. A host, a URL, a credential and free text are not part of it.
"""
import datetime
import logging
import re
import socket
import string

from alembic.runtime.migration import MigrationContext
from flask import current_app
from jinja2 import Environment, PackageLoader, select_autoescape
from sqlalchemy import case, func, select, true
from sqlalchemy.engine.url import make_url

from privacyidea.lib.auth import get_all_db_admins
from privacyidea.lib.config import (get_config_object, get_from_config, get_privacyidea_nodes,
                                    is_password_config_entry)
from privacyidea.lib.crypto import CENSORED
from privacyidea.lib.event import EventConfiguration, get_handler_object
from privacyidea.lib.machineresolver import get_resolver_list as get_machine_resolver_list
from privacyidea.lib.policy import PolicyClass
from privacyidea.lib.radiusserver import get_radiusservers
from privacyidea.lib.realm import get_realms
from privacyidea.lib.resolver import get_resolver_class, get_resolver_list
from privacyidea.lib.smsprovider.SMSProvider import SMS_PROVIDERS, get_sms_provider_class, get_smsgateway
from privacyidea.lib.smtpserver import get_smtpservers
from privacyidea.lib.utils import get_version_number, is_true
from privacyidea.models import CAConnector, MachineToken, Token, TokenContainer, TokenOwner, db

log = logging.getLogger(__name__)

# The pi.cfg settings that the system documentation lists. The report is read by somebody other than the person who
# wrote pi.cfg, so only the settings named here are part of it: a path, a URL, a credential and a setting that an
# installation or a plugin defines itself are not. A setting that holds one of them, but is worth documenting, is
# listed by a value derived from it, see get_app_config_for_documentation().
DOCUMENTED_APP_CONFIG_KEYS = (
    "SUPERUSER_REALM", "PI_NODE", "PI_ENGINE_REGISTRY_CLASS", "PI_LOGLEVEL", "PI_CHECK_RELOAD_CONFIG",
    "PI_AUDIT_MODULE", "PI_AUDIT_NO_SIGN", "PI_AUDIT_POOL_SIZE", "PI_AUDIT_POOL_RECYCLE", "PI_AUDIT_SQL_COLUMN_LENGTH",
    "PI_CHECK_OLD_SIGNATURES", "PI_NO_RESPONSE_SIGN", "PI_MONITORING_MODULE", "PI_NO_INTERNAL_METRICS",
    "PI_HSM_MODULE", "PI_HASH_ALGO_LIST",
    "PI_REDIS_CACHE_CHALLENGES", "PI_REDIS_CACHE_USERS", "PI_REDIS_USER_CACHE_TTL", "PI_REDIS_CACHE_AUTH",
    "PI_REDIS_AUTH_CACHE_TTL", "PI_REDIS_CACHE_HEALTH",
    "PI_TOKEN_MODULES", "PI_SMS_PROVIDER_MODULES", "PI_PIN_HANDLER_MODULES", "PI_EMAIL_VALIDATOR_MODULES",
    "PI_MODULE_ALLOWLIST_MODE", "PI_TOKEN_SERIAL_RANDOM", "PI_ALLOWED_SSH_KEY_TYPES",
    "PI_ENABLE_CSP", "PI_FORCE_HTTPS", "PI_SESSION_COOKIE_SECURE", "PI_CONDITIONAL_ACCESS_NEVER_BLOCK",
    "PI_PREFERRED_LANGUAGE", "PI_UI_DEACTIVATED",
)

# Settings whose value is a database connect string. They are documented by the driver.
CONNECT_STRING_APP_CONFIG_KEYS = ("SQLALCHEMY_DATABASE_URI", "PI_AUDIT_SQL_URI", "PI_MONITORING_SQL_URI")

# Settings that hold a URL. They are documented by whether they are set.
URL_APP_CONFIG_KEYS = ("PI_REDIS_URL", "PI_BASE_URL")

# The template is rendered without escaping, it is no HTML. select_autoescape() escapes HTML and XML templates only.
_TEMPLATE_ENVIRONMENT = Environment(loader=PackageLoader("privacyidea.lib", "templates"),
                                    autoescape=select_autoescape())


def _get_connect_string_driver(connect_string: str) -> str:
    try:
        return make_url(connect_string).drivername
    except Exception:
        return "unknown"


def get_app_config_for_documentation(app_config: dict) -> dict:
    """
    Return the pi.cfg settings that the system documentation lists, see DOCUMENTED_APP_CONFIG_KEYS.

    The value of a setting that is listed by a value derived from it is under a name that says how it is derived,
    e.g. "PI_AUDIT_SQL_URI (driver)".

    :param app_config: the application configuration
    :return: the documented settings and their values
    """
    documented = {key: app_config[key] for key in DOCUMENTED_APP_CONFIG_KEYS if key in app_config}
    for key in CONNECT_STRING_APP_CONFIG_KEYS:
        if app_config.get(key):
            documented[f"{key} (driver)"] = _get_connect_string_driver(app_config[key])
    for key in URL_APP_CONFIG_KEYS:
        documented[f"{key} (set)"] = bool(app_config.get(key))
    if app_config.get("PI_TRUSTED_JWT"):
        documented["PI_TRUSTED_JWT (entries)"] = len(app_config["PI_TRUSTED_JWT"])
    return documented


def _get_documented_value(definition: dict | None, value: object) -> object:
    """
    Return the value of a setting as the system documentation lists it: a value that is one of the choices declared
    for the setting, a bool or a number. Free text, like the URL of a WebHook or the body of a notification, and a
    value that is not one of the declared choices are censored.

    :param definition: the declaration of the setting, like an option of an event handler or a parameter of an SMS
        provider, which names its choices under "value" or "values"
    :param value: the value of the setting
    """
    if not isinstance(definition, dict):
        return CENSORED
    if definition.get("type") == "bool":
        return is_true(value)
    if definition.get("type") == "int":
        try:
            return int(value)
        except (TypeError, ValueError):
            return CENSORED
    declared_choices = definition.get("value") or definition.get("values") or ()
    choices = {str(choice.get("name") if isinstance(choice, dict) else choice) for choice in declared_choices}
    if not choices:
        return CENSORED
    # A condition of type "multi" holds a comma-separated selection of the choices
    values = str(value).split(",") if definition.get("type") == "multi" else [str(value)]
    return value if all(part.strip() in choices for part in values) else CENSORED


def get_events_for_documentation() -> list[dict]:
    """
    Return the event handlers as the system documentation lists them, to learn which handlers react to which events
    and what they do. An option or a condition is listed with its value only if that value is one of the choices the
    handler declares for it, a bool or a number, see _get_documented_value().

    :return: a list with one dict per event handler
    """
    documented_events = []
    for event_definition in EventConfiguration().events:
        handler = get_handler_object(event_definition.get("handlermodule"))
        action_definitions = {}
        condition_definitions = {}
        try:
            if handler:
                actions = handler.actions
                if isinstance(actions, dict):
                    action_definitions = actions.get(event_definition.get("action")) or {}
                condition_definitions = handler.conditions
        except Exception as error:
            # A handler that can not describe its settings, like the script handler without its script directory,
            # is documented with all values censored
            log.warning(f"The settings of the event handler {event_definition.get('name')!r} can not be "
                        f"documented: {type(error).__name__}")
            action_definitions = {}
            condition_definitions = {}
        documented_events.append({
            "name": event_definition.get("name"),
            "handlermodule": event_definition.get("handlermodule"),
            "active": event_definition.get("active"),
            "position": event_definition.get("position"),
            "ordering": event_definition.get("ordering"),
            "event": event_definition.get("event"),
            "action": event_definition.get("action"),
            "abort_on_error": event_definition.get("abort_on_error"),
            "conditions": {key: _get_documented_value(condition_definitions.get(key), value)
                           for key, value in event_definition.get("conditions", {}).items()},
            "options": {key: _get_documented_value(action_definitions.get(key), value)
                        for key, value in event_definition.get("options", {}).items()}})
    return documented_events


def get_smtpservers_for_documentation() -> list[dict]:
    """
    Return the SMTP servers as the system documentation lists them: by how they are connected, not by the host,
    the sender or the account.
    """
    return [{"identifier": server.config.identifier,
             "port": server.config.port,
             "tls": bool(server.config.tls),
             "authentication": bool(server.config.username),
             "smime": bool(server.config.smime),
             "timeout": server.config.timeout}
            for server in get_smtpservers()]


def get_radiusservers_for_documentation() -> list[dict]:
    """
    Return the RADIUS servers as the system documentation lists them: by how they are queried, not by the host or
    the shared secret.
    """
    return [{"identifier": server.config.identifier,
             "port": server.config.port,
             "timeout": server.config.timeout,
             "retries": server.config.retries,
             "message_authenticator": is_true((server.config.options or {}).get("message_authenticator"))}
            for server in get_radiusservers()]


def _get_sms_provider_parameters(provider_module: str) -> dict:
    """
    Return the parameters an SMS provider declares. Only the providers that ship with privacyIDEA are imported for
    this, the options of a gateway with another provider are all censored.
    """
    if provider_module not in SMS_PROVIDERS:
        return {}
    package_name, class_name = provider_module.rsplit(".", 1)
    return get_sms_provider_class(package_name, class_name).parameters().get("parameters", {})


def get_smsgateways_for_documentation() -> list[dict]:
    """
    Return the SMS gateways as the system documentation lists them: by their provider and the options whose value
    is one of the choices the provider declares, see _get_documented_value(). The other options and the headers are
    listed censored, they hold the URL and the credentials of the gateway.
    """
    documented_gateways = []
    for gateway in get_smsgateway():
        parameters = _get_sms_provider_parameters(gateway.providermodule)
        documented_gateways.append({
            "identifier": gateway.identifier,
            "providermodule": gateway.providermodule,
            "options": {key: _get_documented_value(parameters.get(key), value)
                        for key, value in gateway.option_dict.items()},
            "headers": {key: CENSORED for key in gateway.header_dict}})
    return documented_gateways


def get_caconnectors_for_documentation() -> list[dict]:
    """
    Return the CA connectors as the system documentation lists them: by their type, not by their files or hosts.
    """
    return [{"name": connector.name, "type": connector.catype}
            for connector in db.session.scalars(select(CAConnector).order_by(CAConnector.name))]


def get_machines_for_documentation() -> dict:
    """
    Return the machine resolvers by their type, and the number of tokens attached to machines per application, like
    "ssh" or "offline".
    """
    machine_resolvers = [{"name": resolver["resolvername"], "type": resolver["type"]}
                         for resolver in get_machine_resolver_list(censor=True).values()]
    attachments = db.session.execute(select(MachineToken.application, func.count(MachineToken.id))
                                     .group_by(MachineToken.application)
                                     .order_by(MachineToken.application)).all()
    # An attachment without an application is counted as "unknown", whether its application is NULL or empty
    attachments_per_application = {}
    for application, count in attachments:
        key = application or "unknown"
        attachments_per_application[key] = attachments_per_application.get(key, 0) + count
    return {"resolvers": machine_resolvers, "attachments": attachments_per_application}


def get_token_statistics() -> dict:
    """
    Return the number of tokens per token type, in total, active and assigned to a user, and the number of
    containers per container type.
    """
    assigned_tokens = select(TokenOwner.token_id)
    # Counted with CASE rather than with an aggregate FILTER clause, which not every database supports
    token_rows = db.session.execute(
        select(Token.tokentype,
               func.count(Token.id),
               func.count(case((Token.active == true(), Token.id))),
               func.count(case((Token.id.in_(assigned_tokens), Token.id))))
        .group_by(Token.tokentype)
        .order_by(Token.tokentype)).all()
    container_rows = db.session.execute(select(TokenContainer.type, func.count(TokenContainer.id))
                                        .group_by(TokenContainer.type)
                                        .order_by(TokenContainer.type)).all()
    # A token without a type is counted as "unknown", whether its type is NULL or empty
    tokens = {}
    for token_type, total, active, assigned in token_rows:
        counts = tokens.setdefault(token_type or "unknown", {"total": 0, "active": 0, "assigned": 0})
        counts["total"] += total
        counts["active"] += active
        counts["assigned"] += assigned
    return {"tokens": tokens,
            "containers": {container_type: count for container_type, count in container_rows}}


def get_schema_revision() -> str:
    """
    Return the revision of the database schema, "unknown" for a database the schema migrations have not stamped.
    """
    heads = MigrationContext.configure(db.session.connection()).get_current_heads()
    return ", ".join(heads) or "unknown"


def _get_system_config() -> dict:
    # The values of password-type entries are censored, also the ones a token class declares a password and that
    # are still stored in plain text
    config = get_from_config()
    for config_key, config_entry in get_config_object().config.items():
        if is_password_config_entry(config_key, config_entry.get("Type")) and config_key in config:
            config[config_key] = CENSORED
    return config


def _get_resolvers() -> dict:
    resolvers = get_resolver_list(censor=True)
    for resolver in resolvers.values():
        resolver_class = get_resolver_class(resolver["type"])
        resolver["data"] = resolver_class.get_config_for_documentation(resolver["data"])
    return resolvers


def get_system_documentation_context() -> dict:
    """
    Return the data the system documentation is rendered from.
    """
    nodes = get_privacyidea_nodes()
    return {"system": socket.getfqdn(socket.gethostname()),
            "date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "version": get_version_number(),
            "schema_revision": get_schema_revision(),
            "nodes": sorted(node["name"] for node in nodes),
            "nodenames": {node["uuid"]: node["name"] for node in nodes},
            "systemconfig": _get_system_config(),
            "appconfig": get_app_config_for_documentation(current_app.config),
            "admins": get_all_db_admins(),
            "resolverconfig": _get_resolvers(),
            "realmconfig": get_realms(),
            "policyconfig": PolicyClass().list_policies(),
            "eventconfig": get_events_for_documentation(),
            "smtpservers": get_smtpservers_for_documentation(),
            "smsgateways": get_smsgateways_for_documentation(),
            "radiusservers": get_radiusservers_for_documentation(),
            "caconnectors": get_caconnectors_for_documentation(),
            "machines": get_machines_for_documentation(),
            "tokens": get_token_statistics()}


def rst_text(text: object) -> str:
    """
    Escape a name, like the name of an event handler, for the running text and the section titles of the
    documentation. The values are rendered into literal blocks, in which reStructuredText has no markup, but outside
    of them a name like "1. Mail", "* Mail" or "users_" is read as a list or a reference. Every punctuation character
    is escaped, and line breaks are replaced, so that a name is always text on one line.
    """
    return re.sub(f"([{re.escape(string.punctuation)}])", r"\\\1", " ".join(str(text).split()))


def render_system_documentation() -> str:
    """
    Render the system documentation as reStructuredText.
    """
    template = _TEMPLATE_ENVIRONMENT.get_template("system_documentation.rst")
    rendered = template.render(context=get_system_documentation_context(), rst_text=rst_text)
    # The template lines that hold no text leave empty lines, three or more line breaks are reduced to two
    return re.sub("\n{3,}", "\n\n", rendered)
