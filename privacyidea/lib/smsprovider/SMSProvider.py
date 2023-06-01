# -*- coding: utf-8 -*-
#
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

__doc__ = """This is the base class for SMS Modules, that can send SMS via
different means.
The function get_sms_provider_class loads an SMS Provider Module dynamically
and returns an instance.

The code is tested in tests/test_lib_smsprovider
"""

from privacyidea.lib.error import ConfigAdminError
from privacyidea.models import SMSGateway, SMSGatewayOption
from privacyidea.lib.utils import fetch_one_resource, get_module_class
from privacyidea.lib.utils.export import (register_import, register_export)
from privacyidea.lib import _
import re
import logging
log = logging.getLogger(__name__)


SMS_PROVIDERS = [
    "privacyidea.lib.smsprovider.HttpSMSProvider.HttpSMSProvider",
    "privacyidea.lib.smsprovider.SipgateSMSProvider.SipgateSMSProvider",
    "privacyidea.lib.smsprovider.SmtpSMSProvider.SmtpSMSProvider",
    "privacyidea.lib.smsprovider.SmppSMSProvider.SmppSMSProvider",
    "privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider",
    "privacyidea.lib.smsprovider.ScriptSMSProvider.ScriptSMSProvider"]


class SMSError(Exception):
    def __init__(self, error_id, description):
        Exception.__init__(self)
        self.error_id = error_id
        self.description = description

    def __repr__(self):
        ret = '{0!s}(error_id={1!r}, description={2!r})'.format(type(self).__name__,
                                                   self.error_id,
                                                   self.description)
        return ret

    def __str__(self):
        ret = '{0!s}'.format(self.description)
        return ret


class ISMSProvider(object):
    """ the SMS Provider Interface - BaseClass """

    regexp_description = _("Regular expression to modify the phone number to make it compatible with provider. "
                           "For example to remove pluses and slashes enter something like '/[\\+/]//'.")

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
                            "Please check your REGEXP: {0!s}".format(regexp))

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
                   options=None, headers=None):

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
    :type options: dict
    :type headers: dict
    :return: The id of the event.
    """
    smsgateway = SMSGateway(identifier, providermodule,
                            description=description,
                            options=options, headers=headers)
    create_sms_instance(identifier).check_configuration()
    return smsgateway.id


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
    Delete the SMS gateway header

    :param id: The id of the SMS Gateway definition
    :param key: The identifier/key
    :param type: The type of the key
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
    sqlquery = SMSGateway.query
    if id:
        try:
            id = int(id)
            sqlquery = sqlquery.filter_by(id=id)
        except Exception:
            log.info("We can not filter for smsgateway {0!s}".format(id))
    if gwtype:
        sqlquery = sqlquery.filter_by(providermodule=gwtype)
    if identifier:
        sqlquery = sqlquery.filter_by(identifier=identifier)

    for gw in sqlquery.all():
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
                               'identifier "{0!s}"'.format(identifier))
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
    return sms.submit_message(phone, message)


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
    log.debug('Import smsgateway config: {0!s}'.format(data))
    for res_name, res_data in data.items():
        if name and name != res_name:
            continue
        rid = set_smsgateway(res_name, **res_data)
        log.info('Import of smsgateway "{0!s}" finished,'
                 ' id: {1!s}'.format(res_name, rid))
