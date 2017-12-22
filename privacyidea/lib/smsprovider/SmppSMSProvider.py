# -*- coding: utf-8 -*-
#
#    E-mail: yurlov.alexandr@gmail.com
#
#    2017-12-22 Alexander Yurlov <yurlov.alexandr@gmail.com>
#               Add new SMPP SMS provider
#
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
#

__doc__="""This is the SMSClass to send SMS via SMPP protocol to SMS center
It requires smpplib installation, this lib works with ascii only, but message support unicode 

"""

from privacyidea.lib.smsprovider.SMSProvider import (ISMSProvider, SMSError)
import requests
from urlparse import urlparse

import logging
log = logging.getLogger(__name__)

import smpplib

class SmppSMSProvider(ISMSProvider):

    def submit_message(self, phone, message):
        """
        send a message to a phone via an smpp protocol to smsc

        :param phone: the phone number
        :param message: the message to submit to the phone
        :return:
        """
        log.debug("submitting message {0!s} to {1!s}".format(message, phone))
        parameter = {}
        if self.smsgateway:
            smsc_host = self.smsgateway.option_dict.get("SMSC_HOST")
            smsc_port = self.smsgateway.option_dict.get("SMSC_PORT")
            sys_id = self.smsgateway.option_dict.get("SYSTEM_ID")
            passwd = self.smsgateway.option_dict.get("PASSWORD")
            s_addr_ton = int(self.smsgateway.option_dict.get("S_ADDR_TON"),16)
            s_addr_npi = int(self.smsgateway.option_dict.get("S_ADDR_NPI"),16)
            s_addr = self.smsgateway.option_dict.get("S_ADDR")
            d_addr_ton = int(self.smsgateway.option_dict.get("D_ADDR_TON"),16)
            d_addr_npi = int(self.smsgateway.option_dict.get("D_ADDR_NPI"),16)
			
        else:
            smsc_host = self.config.get('SMSC_HOST')
            smsc_port = self.config.get('SMSC_PORT')
            sys_id = self.config.get('SYSTEM_ID')
            passwd = self.config.get('PASSWORD')
            s_addr_ton = int(self.config.get('S_ADDR_TON'),16)
            s_addr_npi = int(self.config.get('S_ADDR_NPI'),16)
            s_addr = self.config.get('S_ADDR')
            d_addr_ton = int(self.config.get('D_ADDR_TON'),16)
            d_addr_npi = int(self.config.get('D_ADDR_NPI'),16)

        if smsc_host is None:
            log.warning("can not submit message. SMSC_HOST is missing.")
            raise SMSError(-1, "No SMSC_HOST specified in the provider config.")
        else:
            if smsc_port is None:
                log.warning("can not submit message. SMSC_PORT is missing.")
                raise SMSError(-1, "No SMSC_PORT specified in the provider config.")

        #SMPP Part
        client = None
        error_key = None 
        try:
            client = smpplib.client.Client(smsc_host.encode("ascii"), smsc_port.encode("ascii"))
            client.connect()
            try:
                client.bind_transmitter(system_id=sys_id.encode("ascii"), password=passwd.encode("ascii"))
                client.send_message(source_addr_ton=s_addr_ton,source_addr_npi=s_addr_npi,source_addr=s_addr.encode("ascii"),dest_addr_ton=d_addr_ton,dest_addr_npi=d_addr_npi,destination_addr=phone.encode("ascii"),short_message=message.encode("ascii"))
            except KeyError as inst:
                error_key = inst.args[0]
            finally:
                pass
        except:
            error_key = "Bad connection string" 
        finally:
            if client:    
                client.disconnect()
		
        if error_key is not None:
            raise SMSError(error_key, "SMS could not be "
                                          "sent: %s" % error_key)
        return True


    @classmethod
    def parameters(cls):
        """
        Return a dictionary, that describes the parameters and options for the
        SMS provider.
        Parameters are required keys to values.

        :return: dict
        """
		
        params = {"options_allowed": False,
                    "parameters": {
                        "SMSC_HOST": {
                            "required": True,
                            "description": "SMSC Host IP"},
                        "SMSC_PORT": {
                            "required": True,
                            "description": "SMSC Port"},
                        "SYSTEM_ID": {
                            "description": "SMSC Service ID"},
                        "PASSWORD": {
                            "description": "Password for authentication on SMSC"},
                        "S_ADDR_TON": {
                            "description": "SOURCE_ADDR_TON Special Flag"},
                        "S_ADDR_NPI": {
                            "description": "S_ADDR_NPI Special Flag"},
                        "S_ADDR": {
                            "description": "Source address (SMS sender)"},
                        "D_ADDR_TON": {"description": "DESTINATION_ADDR_TON Special Flag"},
                        "D_ADDR_NPI": {"description": "D_ADDR_NPI Special Flag"}
                    }
                    }
        return params
