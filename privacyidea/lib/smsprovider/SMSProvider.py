# -*- coding: utf-8 -*-
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
    def __init__(self):
        self.config = {}
        
    def submit_message(self, phone, message):  # pragma: no cover
        """
        Sends the SMS. It should return a bool indicating if the SMS was
        sent successfully.

        In case of SMS send fail, an Exception should be raised.
        :return: Success
        :rtype: bool
        """
        return True
    
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
