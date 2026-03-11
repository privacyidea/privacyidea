#  2018-02-13 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Allow expired attestation certificate
#  2017-04-18 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Save attestation cert info to tokeninfo
#  2015-11-22 Cornelius Kölbel <cornelius@privacyidea.org>
#             Adding dynamic facet list
#
#  http://www.privacyidea.org
#  2017-04-22 Cornelius Kölbel <cornelius.koelbel@netknights.it>
#             Add policies of attestation certificate
#  2015-09-21 Initial writeup.
#             Cornelius Kölbel <cornelius@privacyidea.org>
#
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import logging

from privacyidea.lib import _
from privacyidea.lib.decorators import check_token_locked
from privacyidea.lib.error import NoLongerSupportedError
from privacyidea.lib.log import log_with
from privacyidea.lib.tokenclass import TokenClass, CLIENTMODE

__doc__ = """
U2F is the "Universal 2nd Factor" specified by the FIDO Alliance.
The register and authentication process is described here:

https://fidoalliance.org/specs/fido-u2f-v1.0-nfc-bt-amendment-20150514/fido-u2f-raw-message-formats.html

But you do not need to be aware of this. privacyIDEA wraps all FIDO specific
communication, which should make it easier for you, to integrate the U2F
tokens managed by privacyIDEA into your application.

U2F Tokens can be either

 * registered by administrators for users or
 * registered by the users themselves.

Enrollment
----------
The enrollment/registering can be completely performed within privacyIDEA.

But if you want to enroll the U2F token via the REST API you need to do it in
two steps:

1. Step
~~~~~~~

.. sourcecode:: http

   POST /token/init HTTP/1.1
   Host: example.com
   Accept: application/json

   type=u2f

This step returns a serial number.

2. Step
~~~~~~~

.. sourcecode:: http

   POST /token/init HTTP/1.1
   Host: example.com
   Accept: application/json

   type=u2f
   serial=U2F1234578
   clientdata=<clientdata>
   regdata=<regdata>

*clientdata* and *regdata* are the values returned by the U2F device.

You need to call the javascript function

.. sourcecode:: javascript

    u2f.register([registerRequest], [], function(u2fData) {} );

and the responseHandler needs to send the *clientdata* and *regdata* back to
privacyIDEA (2. step).

Authentication
--------------

The U2F token is a challenge response token. I.e. you need to trigger a
challenge e.g. by sending the OTP PIN/Password for this token.

Get the challenge
~~~~~~~~~~~~~~~~~

.. sourcecode:: http

   POST /validate/check HTTP/1.1
   Host: example.com
   Accept: application/json

   user=cornelius
   pass=tokenpin

**Response**

.. sourcecode:: http

   HTTP/1.1 200 OK
   Content-Type: application/json

   {
      "detail": {
        "attributes": {
                        "hideResponseInput": true,
                        "img": "...imageUrl...",
                        "u2fSignRequest": {
                            "challenge": "...",
                            "appId": "...",
                            "keyHandle": "...",
                            "version": "U2F_V2"
                        }
                      },
        "message": "Please confirm with your U2F token (Yubico U2F EE ...)"
        "transaction_id": "02235076952647019161"
      },
      "id": 1,
      "jsonrpc": "2.0",
      "result": {
         "status": true,
         "value": false,
      },
      "version": "privacyIDEA unknown"
   }

Send the Response
~~~~~~~~~~~~~~~~~

The application now needs to call the javascript function *u2f.sign* with the
*u2fSignRequest* from the response.

   var signRequests = [ error.detail.attributes.u2fSignRequest ];
   u2f.sign(signRequests, function(u2fResult) {} );

The response handler function needs to call the */validate/check* API again with
the signatureData and clientData returned by the U2F device in the *u2fResult*:

.. sourcecode:: http

   POST /validate/check HTTP/1.1
   Host: example.com
   Accept: application/json

   user=cornelius
   pass=
   transaction_id=<transaction_id>
   signaturedata=signatureData
   clientdata=clientData

"""

# Images of the keys shown during enrollment.
#
# The solokeys image is copyright (C) 2020 Solokeys. License: CC-BY-SA 4.0
#
# The image is a relative file system path.
IMAGES = {"yubico": "privacyidea/static/img/FIDO-U2F-Security-Key-444x444.png",
          "plug-up": "privacyidea/static/img/plugup.jpg",
          "u2fzero.com": "privacyidea/static/img/u2fzero.png",
          "solokeys": "privacyidea/static/img/solokeys.png"}

U2F_Version = "U2F_V2"

log = logging.getLogger(__name__)
optional = True
required = False


class U2FACTION(object):
    FACETS = "u2f_facets"
    REQ = "u2f_req"
    NO_VERIFY_CERT = "u2f_no_verify_certificate"


class U2fTokenClass(TokenClass):
    """
    The U2F Token implementation.
    """

    client_mode = CLIENTMODE.U2F

    @staticmethod
    def get_class_type():
        """
        Returns the internal token type identifier
        :return: u2f
        :rtype: basestring
        """
        return "u2f"

    @staticmethod
    def get_class_prefix():
        """
        Return the prefix, that is used as a prefix for the serial numbers.
        :return: U2F
        :rtype: basestring
        """
        return "U2F"

    @log_with(log)
    def __init__(self, db_token):
        """
        Create a new U2F Token object from a database object

        :param db_token: instance of the orm db object
        :type db_token: DB object
        """
        raise NoLongerSupportedError(_("This token is no longer supported!"))

    def update(self, param, reset_failcount=True):
        """
        This method is called during the initialization process.

        :param param: parameters from the token init
        :type param: dict
        :return: None
        """
        raise NoLongerSupportedError(_("This token is no longer supported!"))

    @log_with(log)
    def get_init_detail(self, params=None, user=None):
        """
        At the end of the initialization we ask the user to press the button
        """
        raise NoLongerSupportedError(_("This token is no longer supported!"))

    @log_with(log)
    def is_challenge_request(self, passw, user=None, options=None):
        """
        check, if the request would start a challenge
        In fact every Request that is not a response needs to start a
        challenge request.

        At the moment we do not think of other ways to trigger a challenge.

        This function is not decorated with ``@challenge_response_allowed``
        as the U2F token is always a challenge response token!

        :param passw: The PIN of the token.
        :param options: dictionary of additional request parameters
        :return: returns true or false
        """
        raise NoLongerSupportedError(_("This token is no longer supported!"))

    def create_challenge(self, transactionid=None, options=None):
        """
        This method creates a challenge, which is submitted to the user.
        The submitted challenge will be preserved in the challenge
        database.

        If no transaction id is given, the system will create a transaction
        id and return it, so that the response can refer to this transaction.

        :param transactionid: the id of this challenge
        :param options: the request context parameters / data
        :type options: dict
        :return: tuple of (bool, message, transactionid, attributes)
        :rtype: tuple

        The return tuple builds up like this:
        ``bool`` if submit was successful;
        ``message`` which is displayed in the JSON response;
        additional challenge ``reply_dict``, which are displayed in the JSON challenges response.
        """
        raise NoLongerSupportedError(_("This token is no longer supported!"))

    @check_token_locked
    def check_otp(self, otpval, counter=None, window=None, options=None):
        """
        This checks the response of a previous challenge.

        :param otpval: N/A
        :param counter: The authentication counter
        :param window: N/A
        :param options: contains "clientdata", "signaturedata" and
            "transaction_id"
        :return: A value > 0 in case of success
        """
        raise NoLongerSupportedError(_("This token is no longer supported!"))

    @classmethod
    def api_endpoint(cls, request, g):
        """
        This provides a function to be plugged into the API endpoint
        /ttype/u2f

        The u2f token can return the facet list at this URL.

        :param request: The Flask request
        :param g: The Flask global object g
        :return: Flask Response or text
        """
        raise NoLongerSupportedError(_("This token is no longer supported!"))

    def export_token(self) -> dict:
        """
        Export for this token is not supported.
        """
        raise NotImplementedError("Export for U2F token is not supported.")

    def import_token(self, token_information: dict):
        """
        Import for this token is not supported.

        Concern that the database token must be deleted manually.
        """
        raise NotImplementedError("Import for U2F token is not supported.")
