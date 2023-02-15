# -*- coding: utf-8 -*-
#
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
from privacyidea.api.lib.utils import getParam, attestation_certificate_allowed
from privacyidea.lib.config import get_from_config
from privacyidea.lib.tokenclass import TokenClass, CLIENTMODE, ROLLOUTSTATE
from privacyidea.lib.token import get_tokens
from privacyidea.lib.log import log_with
import logging
from privacyidea.models import Challenge
from privacyidea.lib import _
from privacyidea.lib.decorators import check_token_locked
from privacyidea.lib.crypto import geturandom
from privacyidea.lib.tokens.u2f import (check_registration_data, url_decode,
                                        parse_registration_data, url_encode,
                                        parse_response_data, check_response,
                                        x509name_to_string)
from privacyidea.lib.error import ValidateError, PolicyError, ParameterError
from privacyidea.lib.policy import SCOPE, GROUP, ACTION, get_action_values_from_options
from privacyidea.lib.policy import Match
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.utils import is_true, hexlify_and_unicode, to_unicode, convert_imagefile_to_dataimage
import binascii
import json

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
                        "img": ...imageUrl...
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

    @staticmethod
    @log_with(log)
    def get_class_info(key=None, ret='all'):
        """
        returns a subtree of the token definition

        :param key: subsection identifier
        :type key: string
        :param ret: default return value, if nothing is found
        :type ret: user defined
        :return: subsection if key exists or user defined
        :rtype: dict or scalar
        """
        res = {'type': 'u2f',
               'title': 'U2F Token',
               'description': 'U2F: Enroll a U2F token.',
               'init': {},
               'config': {},
               'user':  ['enroll'],
               # This tokentype is enrollable in the UI for...
               'ui_enroll': ["admin", "user"],
               'policy': {
                   SCOPE.AUTH: {
                       U2FACTION.FACETS: {
                           'type': 'str',
                           'desc': _("This is a list of FQDN hostnames "
                                     "trusting the registered U2F tokens.")},
                       ACTION.CHALLENGETEXT: {
                           'type': 'str',
                           'desc': _('Use an alternate challenge text for telling the '
                                     'user to confirm with his U2F device.')
                       }
                   },
                   SCOPE.AUTHZ: {
                       U2FACTION.REQ: {
                           'type': 'str',
                           'desc': _("Only specified U2F tokens are "
                                     "authorized."),
                           'group': GROUP.CONDITIONS,
                       }
                   },
                   SCOPE.ENROLL: {
                       U2FACTION.REQ: {
                           'type': 'str',
                           'desc': _("Only specified U2F tokens are allowed "
                                     "to be registered."),
                           'group': GROUP.TOKEN},
                       U2FACTION.NO_VERIFY_CERT: {
                           'type': 'bool',
                           'desc': _("Do not verify the U2F attestation certificate."),
                           'group': GROUP.TOKEN
                       },
                       ACTION.MAXTOKENUSER: {
                           'type': 'int',
                           'desc': _("The user may only have this maximum number of U2F tokens assigned."),
                           'group': GROUP.TOKEN
                       },
                       ACTION.MAXACTIVETOKENUSER: {
                           'type': 'int',
                           'desc': _(
                               "The user may only have this maximum number of active U2F tokens assigned."),
                           'group': GROUP.TOKEN
                       }
                   }
               }
               }

        if key:
            ret = res.get(key, {})
        else:
            if ret == 'all':
                ret = res
        return ret

    @log_with(log)
    def __init__(self, db_token):
        """
        Create a new U2F Token object from a database object

        :param db_token: instance of the orm db object
        :type db_token: DB object
        """
        TokenClass.__init__(self, db_token)
        self.set_type("u2f")
        self.hKeyRequired = False

    def update(self, param, reset_failcount=True):
        """
        This method is called during the initialization process.

        :param param: parameters from the token init
        :type param: dict
        :return: None
        """
        TokenClass.update(self, param)
        reg_data = getParam(param, "regdata")
        verify_cert = is_true(getParam(param, "u2f.verify_cert", default=True))
        if not reg_data:
            self.token.rollout_state = ROLLOUTSTATE.CLIENTWAIT
            # Set the description in the first enrollment step
            if "description" in param:
                self.set_description(getParam(param, "description", default=""))
        elif reg_data and self.token.rollout_state == ROLLOUTSTATE.CLIENTWAIT:
            attestation_cert, user_pub_key, key_handle, \
                signature, automatic_description = parse_registration_data(reg_data,
                                                                 verify_cert=verify_cert)
            client_data = getParam(param, "clientdata", required)
            client_data_str = url_decode(client_data)
            app_id = self.get_tokeninfo("appId", "")
            # Verify the registration data
            # In case of any crypto error, check_data raises an exception
            check_registration_data(attestation_cert, app_id, client_data_str,
                                    user_pub_key, key_handle, signature)
            self.set_otpkey(key_handle)
            self.add_tokeninfo("pubKey", user_pub_key)
            # add attestation certificate info
            issuer = x509name_to_string(attestation_cert.get_issuer())
            serial = "{!s}".format(attestation_cert.get_serial_number())
            subject = x509name_to_string(attestation_cert.get_subject())

            self.add_tokeninfo("attestation_issuer", issuer)
            self.add_tokeninfo("attestation_serial", serial)
            self.add_tokeninfo("attestation_subject", subject)
            # Reset rollout state
            self.token.rollout_state = ""
            # If no description has already been set, set the automatic description or the
            # description given in the 2nd request
            if not self.token.description:
                self.set_description(getParam(param, "description", default=automatic_description))
        else:
            raise ParameterError("regdata provided but token not in clientwait rollout_state.")

    @log_with(log)
    def get_init_detail(self, params=None, user=None):
        """
        At the end of the initialization we ask the user to press the button
        """
        response_detail = {}
        # get_init_details runs after "update" method. So in the first step clientwait has already been set
        if self.token.rollout_state == ROLLOUTSTATE.CLIENTWAIT:
            # This is the first step of the init request
            app_id = get_from_config("u2f.appId", "").strip("/")
            from privacyidea.lib.error import TokenAdminError
            if not app_id:
                raise TokenAdminError(_("You need to define the appId in the "
                                        "token config!"))
            nonce = url_encode(geturandom(32))
            response_detail = TokenClass.get_init_detail(self, params, user)
            register_request = {"version": U2F_Version,
                                "challenge": nonce,
                                "appId": app_id}
            response_detail["u2fRegisterRequest"] = register_request
            self.add_tokeninfo("appId", app_id)

        elif self.token.rollout_state == "":
            # This is the second step of the init request, the clientwait rollout state has been reset
            response_detail["u2fRegisterResponse"] = {"subject":
                                                          self.token.description}

        return response_detail

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
        trigger_challenge = False
        options = options or {}
        pin_match = self.check_pin(passw, user=user, options=options)
        if pin_match is True:
            trigger_challenge = True

        return trigger_challenge

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
        options = options or {}
        message = get_action_values_from_options(SCOPE.AUTH,
                                                 "{0!s}_{1!s}".format(self.get_class_type(),
                                                                      ACTION.CHALLENGETEXT),
                                                 options)or _('Please confirm with your U2F token ({0!s})').format(
            self.token.description)

        validity = int(get_from_config('DefaultChallengeValidityTime', 120))
        tokentype = self.get_tokentype().lower()
        lookup_for = tokentype.capitalize() + 'ChallengeValidityTime'
        validity = int(get_from_config(lookup_for, validity))

        # if a transaction id is given, check if there are other u2f token and
        # reuse the challenge
        challenge = None
        if transactionid:
            for c in get_challenges(transaction_id=transactionid):
                if get_tokens(serial=c.serial, tokentype=self.get_class_type(),
                              count=True):
                    challenge = c.challenge
                    break

        if not challenge:
            nonce = geturandom(32)
            challenge = hexlify_and_unicode(nonce)
        else:
            nonce = binascii.unhexlify(challenge)

        # Create the challenge in the database
        db_challenge = Challenge(self.token.serial,
                                 transaction_id=transactionid,
                                 challenge=challenge,
                                 data=None,
                                 session=options.get("session"),
                                 validitytime=validity)
        db_challenge.save()
        sec_object = self.token.get_otpkey()
        key_handle_hex = sec_object.getKey()
        key_handle_bin = binascii.unhexlify(key_handle_hex)
        key_handle_url = url_encode(key_handle_bin)
        challenge_url = url_encode(nonce)
        u2f_sign_request = {"appId": self.get_tokeninfo("appId"),
                            "version": U2F_Version,
                            "challenge": challenge_url,
                            "keyHandle": key_handle_url}

        image_url = IMAGES.get(self.token.description.lower().split()[0], "")
        dataimage = convert_imagefile_to_dataimage(image_url) if image_url else ""
        reply_dict = {"attributes": {"u2fSignRequest": u2f_sign_request,
                                     "hideResponseInput": self.client_mode != CLIENTMODE.INTERACTIVE,
                                     "img": dataimage},
                      "image": dataimage}

        return True, message, db_challenge.transaction_id, reply_dict

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
        ret = -1
        clientdata = options.get("clientdata")
        signaturedata = options.get("signaturedata")
        transaction_id = options.get("transaction_id")
        # The challenge in the challenge DB object is saved in hex
        challenge = binascii.unhexlify(options.get("challenge", ""))
        if clientdata and signaturedata and transaction_id and challenge:
            # This is a valid response for a U2F token
            challenge_url = url_encode(challenge)
            clientdata = url_decode(clientdata)
            clientdata_dict = json.loads(to_unicode(clientdata))
            client_challenge = clientdata_dict.get("challenge")
            if challenge_url != client_challenge:
                return ret
            if clientdata_dict.get("typ") != "navigator.id.getAssertion":
                raise ValidateError("Incorrect navigator.id")
            #client_origin = clientdata_dict.get("origin")
            signaturedata = url_decode(signaturedata)
            signaturedata_hex = hexlify_and_unicode(signaturedata)
            user_presence, counter, signature = parse_response_data(
                signaturedata_hex)

            user_pub_key = self.get_tokeninfo("pubKey")
            app_id = self.get_tokeninfo("appId")
            if check_response(user_pub_key, app_id, clientdata,
                              hexlify_and_unicode(signature), counter,
                              user_presence):
                # Signature verified.
                # check, if the counter increased!
                if counter > self.get_otp_count():
                    self.set_otp_count(counter)
                    ret = counter
                    # At this point we can check, if the attestation
                    # certificate is authorized.
                    # If not, we can raise a policy exception
                    if not attestation_certificate_allowed(
                        {
                            "attestation_issuer": self.get_tokeninfo("attestation_issuer"),
                            "attestation_serial": self.get_tokeninfo("attestation_serial"),
                            "attestation_subject": self.get_tokeninfo("attestation_subject")
                        },
                        Match
                            .user(options.get("g"),
                                  scope=SCOPE.AUTHZ,
                                  action=U2FACTION.REQ,
                                  user_object=self.user if self.user else None)
                            .action_values(unique=False)
                    ):
                        log.warning(
                            "The U2F device {0!s} is not allowed to authenticate due to policy restriction"
                                .format(self.token.serial))
                        raise PolicyError("The U2F device is not allowed "
                                          "to authenticate due to policy "
                                          "restriction.")

                else:
                    log.warning("The signature of %s was valid, but contained "
                                "an old counter." % self.token.serial)
            else:
                log.warning("Checking response for token {0!s} failed.".format(
                            self.token.serial))

        return ret

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
        configured_app_id = get_from_config("u2f.appId")
        if configured_app_id is None:
            raise ParameterError("u2f is not configured")
        app_id = configured_app_id.strip("/")

        # Read the facets from the policies
        pol_facets = Match.action_only(g, scope=SCOPE.AUTH, action=U2FACTION.FACETS).action_values(unique=False)
        facet_list = ["https://{0!s}".format(x) for x in pol_facets]
        facet_list.append(app_id)

        log.debug("Sending facets lists for appId {0!s}: {1!s}".format(app_id,
                                                             facet_list))
        res = {"trustedFacets": [{"version": {"major": 1,
                                              "minor": 0},
                                  "ids": facet_list
                                  }
                                 ]
               }
        return "fido.trusted-apps+json", res
