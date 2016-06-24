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
__doc__="""This is the base class for SMS Modules, that can send SMS via
different means.
The function get_sms_provider_class loads an SMS Provider Module dynamically
and returns an instance.

The code is tested in tests/test_lib_smsprovider
"""

from privacyidea.models import SMSGateway, SMSGatewayOption
import logging
log = logging.getLogger(__name__)


SMS_PROVIDERS = [
    "privacyidea.lib.smsprovider.HttpSMSProvider.HttpSMSProvider",
    "privacyidea.lib.smsprovider.SipgateSMSProvider.SipgateSMSProvider",
    "privacyidea.lib.smsprovider.SmtpSMSProvider.SmtpSMSProvider"]


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
                  "parameters": {
                      "PARAMETER1": {
                          "required": True,
                          "description": "Some parameter",
                          "values": ["allowed value1", "allowed value2"]}
                  },
                  }
        return params

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
    mod = __import__(packageName, globals(), locals(), [className])
    klass = getattr(mod, className)
    if not hasattr(klass, "submit_message"):
        raise NameError("SMSProvider AttributeError: " + packageName + "." +
                        className + " instance of SMSProvider has no method"
                        " 'submitMessage'")
    else:
        return klass


def set_smsgateway(identifier, providermodule, description=None,
                   options=None):

    """
    Set an SMS Gateway configuration

    If the identifier already exist, the SMS Gateway is updated. Otherwise a
    new one is created.

    :param identifier: The unique identifier name of the SMS Gateway
    :param providermodule: The python module of the SMS Gateway
    :type providermodule: basestring
    :param description: A description of this gateway definition
    :param options: Options and Parameter for this module
    :type options: dict
    :return: The id of the event.
    """
    smsgateway = SMSGateway(identifier, providermodule,
                            description=description,
                            options=options)
    return smsgateway.id


def delete_smsgateway(identifier):
    """
    Delete the SMS gateway configuration with this given ID.
    :param identifier: The name of the SMS gateway definition
    :type identifier: basestring
    :return:
    """
    r = -1
    gw = SMSGateway.query.filter_by(identifier=identifier).first()
    if gw:
        r = gw.delete()
    return r


def delete_smsgateway_option(id, option_key):
    """
    Delete the SMS gateway option

    :param id: The id of the SMS Gateway definition
    :param option_key: The identifier/key of the option
    :return: True
    """
    r = SMSGatewayOption.query.filter_by(gateway_id=id,
                                         Key=option_key).first().delete()
    return r


def get_smsgateway(identifier=None, id=None):
    """
    return a list of all SMS Gateway Configurations!

    :param identifier: If the identifier is specified, then we return only
        this single gateway definition
    :param id: If the id is specified, we return only this single SMS gateway
        definition
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
    gateway_definition = get_smsgateway(identifier)[0]
    sms_klass = get_sms_provider_class(
        ".".join(gateway_definition.providermodule.split(".")[:-1]),
        gateway_definition.providermodule.split(".")[-1])
    sms_object = sms_klass(smsgateway=gateway_definition)
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
