#    2017-12-27 Cornelius Kölbel <cornelius.koelbel@netknights.i>
#               Restructuring Code.
#
#    E-mail: yurlov.alexandr@gmail.com
#
#    2017-12-22 Alexander Yurlov <yurlov.alexandr@gmail.com>
#               Add new SMPP SMS provider
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

__doc__ = """This is the SMSClass to send SMS via SMPP protocol to SMS center
It requires smpplib installation, this lib works with ascii only, but message support unicode 

"""

from privacyidea.lib.smsprovider.SMSProvider import (ISMSProvider, SMSError)
from privacyidea.lib import _
from privacyidea.lib.utils import parse_int
import logging
import traceback
import smpplib
import smpplib.gsm

log = logging.getLogger(__name__)


class SmppSMSProvider(ISMSProvider):

    def submit_message(self, phone, message):
        """
        send a message to a phone via a smpp protocol to smsc

        :param phone: the phone number
        :param message: the message to submit to the phone
        :return:
        """
        if not self.smsgateway:
            # this should not happen. We now always use sms gateway definitions.
            log.warning("Missing smsgateway definition!")
            raise SMSError(-1, "Missing smsgateway definition!")

        phone = self._mangle_phone(phone, self.smsgateway.option_dict)
        log.debug("submitting message {0!r} to {1!s}".format(message, phone))

        smsc_host = self.smsgateway.option_dict.get("SMSC_HOST")
        smsc_port = self.smsgateway.option_dict.get("SMSC_PORT")
        sys_id = self.smsgateway.option_dict.get("SYSTEM_ID")
        passwd = self.smsgateway.option_dict.get("PASSWORD")
        s_addr_ton = parse_int(self.smsgateway.option_dict.get("S_ADDR_TON"))
        s_addr_npi = parse_int(self.smsgateway.option_dict.get("S_ADDR_NPI"))
        s_addr = self.smsgateway.option_dict.get("S_ADDR")
        d_addr_ton = parse_int(self.smsgateway.option_dict.get("D_ADDR_TON"))
        d_addr_npi = parse_int(self.smsgateway.option_dict.get("D_ADDR_NPI"))

        if not smsc_host:
            log.warning("Can not submit message. SMSC_HOST is missing.")
            raise SMSError(-1, "No SMSC_HOST specified in the provider config.")

        if not smsc_port:
            log.warning("Can not submit message. SMSC_PORT is missing.")
            raise SMSError(-1, "No SMSC_PORT specified in the provider config.")

        # Initialize the SMPP Client
        client = None
        error_message = None 
        try:
            msg_parts, encoding_flag, msg_type_flag = smpplib.gsm.make_parts(message)
            client = smpplib.client.Client(smsc_host,
                                           smsc_port)
            client.connect()
            r = client.bind_transmitter(system_id=sys_id,
                                        password=passwd)
            log.debug("bind_transmitter returns {0!r}".format(r.get_status_desc()))
            for part in msg_parts:
                r = client.send_message(source_addr_ton=s_addr_ton,
                                        source_addr_npi=s_addr_npi,
                                        source_addr=s_addr,
                                        dest_addr_ton=d_addr_ton,
                                        dest_addr_npi=d_addr_npi,
                                        destination_addr=phone,
                                        short_message=part,
                                        data_coding=encoding_flag,
                                        esm_class=msg_type_flag)
                log.debug("send_message returns {0!r}".format(r.get_status_desc()))

        except Exception as err:
            error_message = "{0!r}".format(err)
            log.warning("Failed to send message: {0!r}".format(error_message))
            log.debug("{0!s}".format(traceback.format_exc()))

        finally:
            if client:
                client.disconnect()

        if error_message:
            raise SMSError(error_message, "SMS could not be "
                                          "sent: {0!r}".format(error_message))
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
                  "headers_allowed": False,
                    "parameters": {
                        "SMSC_HOST": {
                            "required": True,
                            "description": _("SMSC Host IP")},
                        "SMSC_PORT": {
                            "required": True,
                            "description": _("SMSC Port")},
                        "SYSTEM_ID": {
                            "description": _("SMSC Service ID")},
                        "PASSWORD": {
                            "description": _("Password for authentication on SMSC")},
                        "S_ADDR_TON": {
                            "description": _("SOURCE_ADDR_TON Special Flag")},
                        "S_ADDR_NPI": {
                            "description": _("S_ADDR_NPI Special Flag")},
                        "S_ADDR": {
                            "description": _("Source address (SMS sender)")},
                        "D_ADDR_TON": {"description": _("DESTINATION_ADDR_TON Special Flag")},
                        "D_ADDR_NPI": {"description": _("D_ADDR_NPI Special Flag")},
                        "REGEXP": {
                            "description": cls.regexp_description
                        }
                    }
                    }
        return params
