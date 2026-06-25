#   2016-06-14 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#              Enhance the base class according to
#              https://github.com/privacyidea/privacyidea/wiki/concept:-Delivery-Gateway
#
#
#    privacyIDEA is a fork of LinOTP
#    May 28, 2014 Cornelius Kölbel
#    E-mail: info@privacyidea.org
#    Contact: www.privacyidea.org
#
#    Copyright (C) LinOTP: 2010 - 2014 LSE Leading Security Experts GmbH
#
#    This program is free software: you can redistribute it and/or
#    modify it under the terms of the GNU Affero General Public
#    License, version 3, as published by the Free Software Foundation.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the
#               GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""This is the base class for SMS Modules, that can send SMS via
different means.
The function get_sms_provider_class loads an SMS Provider Module dynamically
and returns an instance.

The code is tested in tests/test_lib_smsprovider
"""
import logging
import re
import time

from sqlalchemy import select, update

from privacyidea.lib import lazy_gettext
from privacyidea.lib.crypto import is_censored, encryptPassword
from privacyidea.lib.error import ConfigAdminError
from privacyidea.lib.metrics import inc, observe
from privacyidea.lib.utils import fetch_one_resource, get_module_class
from privacyidea.lib.utils.export import (register_import, register_export)
from privacyidea.models import SMSGateway, SMSGatewayOption, db

log = logging.getLogger(__name__)

SMS_PROVIDERS = [
    "privacyidea.lib.smsprovider.HttpSMSProvider.HttpSMSProvider",
    "privacyidea.lib.smsprovider.SipgateSMSProvider.SipgateSMSProvider",
    "privacyidea.lib.smsprovider.SmtpSMSProvider.SmtpSMSProvider",
    "privacyidea.lib.smsprovider.SmppSMSProvider.SmppSMSProvider",
    "privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider",
    "privacyidea.lib.smsprovider.ScriptSMSProvider.ScriptSMSProvider"]

# Keywords in option keys that indicate the value is sensitive and must be
# stored encrypted in the database (case-insensitive substring match).
SENSITIVE_OPTION_KEYWORDS = ("PASSWORD", "SECRET")


def _is_sensitive_key(key):
    """Return True if the given option/header key name indicates a secret value."""
    upper_key = key.upper()
    return any(kw in upper_key for kw in SENSITIVE_OPTION_KEYWORDS)


class SMSError(Exception):
    def __init__(self, error_id, description):
        Exception.__init__(self)
        self.error_id = error_id
        self.description = description

    def __repr__(self):
        ret = f'{type(self).__name__!s}(error_id={self.error_id!r}, description={self.description!r})'
        return ret

    def __str__(self):
        ret = f'{self.description!s}'
        return ret


class ISMSProvider:
    """ the SMS Provider Interface - BaseClass """

    regexp_description = lazy_gettext("Regular expression to modify the phone number to make it compatible with"
                                      " the provider. For example to remove pluses and slashes"
                                      " enter something like '/[\\+/]//'.")

    def __init__(self, db_smsprovider_object=None, smsgateway=None):
        """
        Create a new SMS Provider object fom a DB SMS provider object

        :param db_smsprovider_object: The database object
        :param smsgateway: The SMS gateway object from the database table
            SMS gateway. The options can be accessed via
            self.smsgateway.option_dict
        :return: An SMS provider object
        """
        self.config = db_smsprovider_object or {}
        self.smsgateway = smsgateway

    def submit_message(self, phone, message):  # pragma: no cover
        """
        Sends the SMS. It should return a bool indicating if the SMS was
        sent successfully.

        In case of SMS send fail, an Exception should be raised.
        :return: Success
        :rtype: bool
        """
        return True

    def check_configuration(self):
        """
        This method checks the sanity of the configuration of this provider.
        If there is a configuration error, than an exception is raised.
        :return:
        """
        return

    @classmethod
    def parameters(cls):
        """
        Return a dictionary, that describes the parameters and options for the
        SMS provider.
        Parameters are required keys to values with defined keys,
        while options can be any combination.

        Each option is the key to another dict, that describes this option,
        if it is required, a description and which values it can take. The
        values are optional.

        Additional options can not be named in advance. E.g. some provider
        specific HTTP parameters of HTTP gateways are options. The HTTP
        parameter for the SMS text could be "text" at one provider and "sms"
        at another one.

        The options can be fixed values or also take the tags {otp},
        {user}, {phone}.

        :return: dict
        """
        params = {"options_allowed": False,
                  "headers_allowed": False,
                  "parameters": {
                      "PARAMETER1": {
                          "required": True,
                          "description": "Some parameter",
                          "values": ["allowed value1", "allowed value2"]}
                  },
                  }
        return params

    @staticmethod
    def _mangle_phone(phone, config):
        regexp = config.get("REGEXP")
        if regexp:
            try:
                m = re.match("^/(.*)/(.*)/$", regexp)
                if m:
                    phone = re.sub(m.group(1), m.group(2), phone)
            except re.error:
                log.warning("Can not mangle phone number. "
                            f"Please check your REGEXP: {regexp!s}")

        return phone

    def load_config(self, config_dict):
        """
        Load the configuration dictionary

        :param config_dict: The conifugration of the SMS provider
        :type config_dict: dict
        :return: None
        """
        self.config = config_dict


def get_sms_provider_class(packageName, className):
    """
    helper method to load the SMSProvider class from a given
    package in literal:

    example:

        get_sms_provider_class("HTTPSMSProvider", "SMSProvider")()

    check:
        checks, if the submit_message method exists
        if not an error is thrown
    """
    return get_module_class(packageName, className, "submit_message")


def set_smsgateway(identifier, providermodule=None, description=None,
                   options=None, headers=None,
                   secret_options=None, secret_headers=None):
    """
    Set an SMS Gateway configuration

    If the identifier already exist, the SMS Gateway is updated. Otherwise a
    new one is created.

    :param identifier: The unique identifier name of the SMS Gateway
    :param providermodule: The python module of the SMS Gateway
    :type providermodule: basestring
    :param description: A description of this gateway definition
    :param options: Options and Parameter for this module
    :param headers: Headers for this module
    :param secret_options: Set of option key names whose values are secret
        and must be stored encrypted. If None, falls back to the key-name
        heuristic (PASSWORD/SECRET).
    :param secret_headers: Set of header key names whose values are secret
        and must be stored encrypted. If None, falls back to the key-name
        heuristic (PASSWORD/SECRET).
    :type options: dict
    :type headers: dict
    :type secret_options: set or None
    :type secret_headers: set or None
    :return: The id of the event.
    """
    stmt = select(SMSGateway).filter_by(identifier=identifier)
    sms_gateway = db.session.execute(stmt).scalar_one_or_none()

    if sms_gateway:
        # update existing sms gateway
        if providermodule is not None:
            sms_gateway.providermodule = providermodule
        sms_gateway.description = description
    else:
        # create new provider
        sms_gateway = SMSGateway(identifier, providermodule, description=description)
        db.session.add(sms_gateway)
    db.session.flush()

    options = options or {}
    new_option_keys = set(options.keys())
    headers = headers or {}
    new_header_keys = set(headers.keys())
    # Delete options/headers that are not in the new options/headers
    for option in sms_gateway.options:
        if option.Type == "option" and option.Key not in new_option_keys:
            db.session.delete(option)
        if option.Type == "header" and option.Key not in new_header_keys:
            db.session.delete(option)

    # Update / Create options and headers
    existing_option_keys = {opt.Key for opt in sms_gateway.options if opt.Type == "option"}
    existing_header_keys = {opt.Key for opt in sms_gateway.options if opt.Type == "header"}
    secret_sets = {"option": secret_options, "header": secret_headers}
    sections = {"option": options, "header": headers}
    for option_type, key_values in sections.items():
        for key in key_values:
            # Skip updating if the value is CENSORED (keep existing value)
            if is_censored(key_values[key]):
                continue
            # Determine if this value is secret: use explicit set if provided,
            # otherwise fall back to the key-name heuristic.
            value = key_values[key]
            explicit_secrets = secret_sets[option_type]
            if explicit_secrets is not None:
                is_secret = key in explicit_secrets
            else:
                is_secret = _is_sensitive_key(key)
            encrypted = False
            if is_secret and value:
                value = encryptPassword(value)
                encrypted = True
            if (option_type == "option" and key in existing_option_keys) or (
                    option_type == "header" and key in existing_header_keys):
                # Update existing option
                update_stmt = update(SMSGatewayOption).where(
                    SMSGatewayOption.gateway_id == sms_gateway.id,
                    SMSGatewayOption.Key == key,
                    SMSGatewayOption.Type == option_type
                ).values(Value=value, Encrypted=encrypted)
                db.session.execute(update_stmt)
            else:
                # Create new option
                sms_option = SMSGatewayOption(gateway_id=sms_gateway.id,
                                              Key=key,
                                              Value=value,
                                              Type=option_type,
                                              Encrypted=encrypted)
                db.session.add(sms_option)
    db.session.commit()

    # Validate configuration
    create_sms_instance(identifier).check_configuration()
    return sms_gateway.id


def delete_smsgateway(identifier):
    """
    Delete the SMS gateway configuration with this given ID.
    :param identifier: The name of the SMS gateway definition
    :type identifier: basestring
    :return:
    """
    return fetch_one_resource(SMSGateway, identifier=identifier).delete()


def delete_smsgateway_option(id, option_key):
    """
    Delete the SMS gateway option

    :param id: The id of the SMS Gateway definition
    :param option_key: The identifier/key of the option
    :return: True
    """
    return delete_smsgateway_key_generic(id, option_key, Type="option")


def delete_smsgateway_header(id, header_key):
    """
    Delete the SMS gateway header

    :param id: The id of the SMS Gateway definition
    :param header_key: The identifier/key of the header
    :return: True
    """
    return delete_smsgateway_key_generic(id, header_key, Type="header")


def delete_smsgateway_key_generic(id, key, Type="option"):
    """
    Delete an SMS gateway option or header.

    :param id: The id of the SMS Gateway definition
    :param key: The identifier/key
    :param Type: The type of the key ("option" or "header")
    :return: True
    """
    return fetch_one_resource(SMSGatewayOption, gateway_id=id, Key=key, Type=Type).delete()


def get_smsgateway(identifier=None, id=None, gwtype=None):
    """
    return a list of all SMS Gateway Configurations!

    :param identifier: If the identifier is specified, then we return only
        this single gateway definition
    :param id: If the id is specified, we return only this single SMS gateway
        definition
    :param gwtype: The type of the gateway to return
    :return: list of gateway definitions
    """
    res = []
    stmt = select(SMSGateway)
    if id:
        try:
            id = int(id)
            stmt = stmt.filter_by(id=id)
        except Exception:
            log.info(f"We can not filter for smsgateway {id!s}")
    if gwtype:
        stmt = stmt.filter_by(providermodule=gwtype)
    if identifier:
        stmt = stmt.filter_by(identifier=identifier)

    gateways = db.session.scalars(stmt).all()
    for gw in gateways:
        res.append(gw)
    return res


def create_sms_instance(identifier):
    """
    This function creates and instance of SMS Provider (either HTTP, Smtp,
    Sipgate) depending on the given sms gateway identifier.

    :param identifier: The name of the SMS gateway configuration
    :return: SMS Provider object
    """
    gateway_definition = get_smsgateway(identifier)
    if not gateway_definition:
        raise ConfigAdminError('Could not find gateway definition with '
                               f'identifier "{identifier!s}"')
    package_name, class_name = gateway_definition[0].providermodule.rsplit(".", 1)
    sms_klass = get_sms_provider_class(package_name, class_name)
    sms_object = sms_klass(smsgateway=gateway_definition[0])
    return sms_object


def send_sms_identifier(identifier, phone, message):
    """
    Send an SMS using the SMS Gateway "identifier".

    :param identifier: The name of the SMS Gateway
    :param phone: The phone number
    :param message: The message to be sent
    :return: True in case of success
    """
    sms = create_sms_instance(identifier)
    labels = {"gateway": identifier}
    start = time.monotonic()
    try:
        result = sms.submit_message(phone, message)
    except Exception:
        observe("sms_send_duration_seconds", time.monotonic() - start, labels)
        inc("sms_send_total", {**labels, "result": "failed"})
        raise
    observe("sms_send_duration_seconds", time.monotonic() - start, labels)
    inc("sms_send_total", {**labels, "result": "ok" if result else "failed"})
    return result


def list_smsgateways(identifier=None, id=None, gwtype=None):
    """
    This returns a list of all sms gateways matching the criterion.
    If no identifier or server is provided, it will return a list of all sms
    gateway definitions.

    :param identifier: The identifier or the name of the SMSGateway definition.
        As the identifier is unique, providing an identifier will return a
        list with either one or no sms gateway
    :type identifier: basestring
    :param id: The id of the sms gateway in the database
    :type id: basestring
    :return: dict of SMSGateway configurations with gateway identifiers as keys.
    """
    res = {}
    for gw in get_smsgateway(identifier=identifier, id=id, gwtype=gwtype):
        res[gw.identifier] = gw.as_dict()
        res[gw.identifier].pop('name')
        res[gw.identifier].pop('id')

    return res


@register_export('smsgateway')
def export_smsgateway(name=None):
    """ Export given or all sms gateway configuration """
    res = list_smsgateways(identifier=name)

    return res


@register_import('smsgateway')
def import_smsgateway(data, name=None):
    """Import sms gateway configuration"""
    log.debug(f'Import smsgateway config: {data!s}')
    for res_name, res_data in data.items():
        if name and name != res_name:
            continue
        rid = set_smsgateway(res_name, **res_data)
        log.info(f'Import of smsgateway "{res_name!s}" finished,'
                 f' id: {rid!s}')
