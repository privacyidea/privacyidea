# -*- coding: utf-8 -*-
#
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  2019-02-08   Cornelius Kölbel <cornelius.koelbel@netknights.it>
#               Start the pushtoken class
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
__doc__ = """The pushtoken sends a push notification via Firebase service
to the registered smartphone.
The token is a challenge response token. The smartphone will sign the challenge
and send it back to the authentication endpoint. 

This code is tested in tests/test_lib_tokens_push
"""

import base64
from functools import cache

import telebot


from privacyidea.api.lib.utils import getParam
from privacyidea.lib.token import get_one_token
from privacyidea.lib.utils import prepare_result, is_true
from privacyidea.lib.error import (ResourceNotFoundError, ValidateError,
                                   privacyIDEAError)

from privacyidea.lib.config import get_from_config
from privacyidea.lib.policy import SCOPE, ACTION, GROUP, get_action_values_from_options
from privacyidea.lib.log import log_with
from privacyidea.lib import _

from privacyidea.lib.tokenclass import TokenClass, AUTHENTICATIONMODE, CLIENTMODE, ROLLOUTSTATE, CHALLENGE_SESSION
from privacyidea.models import Challenge, db
from privacyidea.lib.decorators import check_token_locked
import logging
from privacyidea.lib.utils import create_img, b32encode_and_unicode
from privacyidea.lib.error import ParameterError
from privacyidea.lib.crypto import geturandom
from privacyidea.lib.challenge import get_challenges
from privacyidea.lib.pirequest import PiRequestClass
from typing import Callable, Any
import time

log = logging.getLogger(__name__)

DEFAULT_CHALLENGE_TEXT = _("Please confirm the authentication in your Telegram!")
DEFAULT_MOBILE_TEXT = _("Is this you attempting to login as {username} from [{client_ip}]?")
TELEGRAM_CHAT_ID = "telegram_chat_id"
ISO_FORMAT = '%Y-%m-%dT%H:%M:%S.%f%z'
DELAY = 1.0


class TELEGRAM_PUSH_ACTION(object):
    TELEGRAM_BOT_TOKEN = "tpush_bot_token"
    TELEGRAM_BOT_API_URL = "tpush_bot_api_url"
    WEBHOOK_URL = "tpush_webhook_url"
    TTL = "tpush_ttl"
    MOBILE_TEXT = "tpush_text_on_mobile"
    WAIT = "tpush_wait"


class PushClickEvent:
    """
    Event which will be sent by Telegram bot upon receiving user click on inline button
    """
    serial: str
    challenge: str
    is_accepted: bool

    def __init__(self, data: str):
        try:
            split = data.split("_")
            self.is_accepted, self.serial, self.challenge = split[0] == "C", split[1], split[2]
        except Exception as err:
            log.error(f"Exception parsing callback data: {err}")
            raise


class TelegramMessageData:
    """
    Simple DTO for sending a private message from a bot to a user, possibly with callback_data for inline buttons
    """
    message: str
    callback_data: str | None

    def __init__(self, message: str, serial: str = None, challenge: str = None):
        self.message = message
        self.callback_data = None
        if serial is not None and challenge is not None:
            self.callback_data = f"{serial}_{challenge}"


def _build_message_data(serial, challenge, options):
    message_on_mobile = str.format(get_action_values_from_options(SCOPE.AUTH,
                                                       TELEGRAM_PUSH_ACTION.MOBILE_TEXT,
                                                       options) or DEFAULT_MOBILE_TEXT, client_ip=options.get("clientip"),
                                                       username = options.get('username')
                                                       )
    return TelegramMessageData(message_on_mobile, serial, challenge)


class TelegramPushTokenClass(TokenClass):
    """
    The :ref:`tpush_token` uses Telegram Bot Api to send challenges to the
    user's account in Telegram. The user confirms challenge by clicking button in a chat with the bot, Bot Api sends 
    a confirmation event back to PrivacyIDEA through webhook.

    The enrollment occurs in two enrollment steps:

    **Step 1**:
      The device is enrolled using a QR code, which encodes the following URI::

      https://t.me/telegram_bot_username?start=enrollment_credential

    **Step 2**:
      The QR code contains a Telegram deep link, which should automatically redirect user to a chat with the bot
      and automatically send a /start command with 64-symbol enrollment_credential passed back to the Bot API.
      Bot API calls a webhook with that event, which by default uses following endpoint:

        .. sourcecode:: http

            POST /ttype/tpush HTTP/1.1
            Host: https://yourprivacyideaserver/

    For more information see:

    - https://github.com/privacyidea/privacyidea/issues/3615
    """
    mode = [AUTHENTICATIONMODE.AUTHENTICATE, AUTHENTICATIONMODE.CHALLENGE, AUTHENTICATIONMODE.OUTOFBAND]
    client_mode = CLIENTMODE.POLL
    # A disabled PUSH token has to be removed from the list of checked tokens.
    check_if_disabled = False
    # If the token is enrollable via multichallenge
    is_multichallenge_enrollable = True

    def __init__(self, db_token):
        TokenClass.__init__(self, db_token)
        self.set_type(u"tpush")
        self.mode = ['challenge', 'authenticate']
        self.hKeyRequired = False

    @staticmethod
    def get_class_type():
        """
        return the generic token class identifier
        """
        return "tpush"

    @staticmethod
    def get_class_prefix():
        return "PITGP"

    @staticmethod
    @cache
    def get_class_info(key=None, ret='all'):
        """
        returns all or a subtree of the token definition

        :param key: subsection identifier
        :type key: str
        :param ret: default return value, if nothing is found
        :type ret: user defined
        :return: subsection if key exists or user defined
        :rtype: dict
        """
        group = "telegram_push"
        res = {'type': 'telegram_push',
               'title': _('Telegram PUSH Token'),
               'description':
                    _('Telegram PUSH: Send a push notification to a Telegram user through a bot'),
               'user': ['enroll'],
               # This tokentype is enrollable in the UI for...
               'ui_enroll': ["admin", "user"],
               'policy': {
                   SCOPE.ENROLL: {
                       TELEGRAM_PUSH_ACTION.WEBHOOK_URL: {
                            "required": True,
                            'type': 'str',
                            'group': group,
                            'desc': _('The URL the Telegram Bot API should use for calling webhooks.'
                                      ' Usually it is the endpoint /ttype/tpush of the privacyIDEA server.')
                       },
                       TELEGRAM_PUSH_ACTION.TTL: {
                           'type': 'int',
                           'group': group,
                           'desc': _('The second enrollment step must be completed within this time (in minutes).')
                       },
                       ACTION.MAXTOKENUSER: {
                           'type': 'int',
                           'desc': _("The user may only have this maximum number of Telegram Push tokens assigned."),
                           'group': GROUP.TOKEN
                       },
                       ACTION.MAXACTIVETOKENUSER: {
                           'type': 'int',
                           'desc': _("The user may only have this maximum number"
                                     " of active Telegram Push tokens assigned."),
                           'group': GROUP.TOKEN
                       }
                   },
                   SCOPE.AUTH: {
                       TELEGRAM_PUSH_ACTION.TELEGRAM_BOT_API_URL: {
                            "required": True,
                            'type': 'str',
                            'group': group,
                            'desc': _('The URL of Telegram Bot API which PrivacyIDEA will work with.'
                                      ' It could be a main https://api.telegram.org/bot{0}/{1} '
                                      ' or URL of your local Bot API server')
                       },
                       TELEGRAM_PUSH_ACTION.TELEGRAM_BOT_TOKEN: {
                           'type': 'str',
                           'desc': _('Telegram Bot API Token'),
                           'group': group
                       },
                       TELEGRAM_PUSH_ACTION.MOBILE_TEXT: {
                           'type': 'str',
                           'desc': _('The question the bot asks when challenging user.' 
                                     'It can be a Python format string with named variables username and client_ip'),
                           'group': group
                       },
                       TELEGRAM_PUSH_ACTION.WAIT: {
                           'type': 'int',
                           'desc': _('Wait for number of seconds for the user '
                                     'to confirm the challenge in the first request.'),
                           'group': group
                       }
                   }
               },
        }

        if key:
            ret = res.get(key, {})
        else:
            if ret == 'all':
                ret = res

        return ret

    @log_with(log)
    def update(self, param, reset_failcount=True):
        """
        process the initialization parameters

        We need to distinguish the first authentication step
        and the second authentication step.

        1. step:
            ``param`` contains:

            - ``type``
            - ``genkey``

        2. step:
            ``param`` contains:

            - ``serial``
            - ``fbtoken``
            - ``pubkey``

        :param param: dict of initialization parameters
        :type param: dict

        :return: nothing
        """
        upd_param = {}
        for k, v in param.items():
            upd_param[k] = v

        if "serial" in upd_param:
            # We are in step 2:
            if self.token.rollout_state != ROLLOUTSTATE.CLIENTWAIT:
                raise ParameterError("Invalid state! The token you want to enroll is not in the state 'clientwait'.")
            enrollment_credential = getParam(upd_param, "enrollment_credential", optional=False)
            if enrollment_credential != self.get_tokeninfo("enrollment_credential"):
                raise ParameterError("Invalid enrollment credential. You are not authorized to finalize this token.")
            self.del_tokeninfo("enrollment_credential")
            self.token.rollout_state = "enrolled"
            self.token.active = True
            # encrypting chat_id since it can be considered sensitive, personal information
            self.add_tokeninfo(TELEGRAM_CHAT_ID, upd_param.get(TELEGRAM_CHAT_ID), value_type="password")

        elif "genkey" in upd_param:
            # We are in step 1:
            upd_param["2stepinit"] = 1
            # Telegram deep link to a bot accepts a query parameter up to 64 symbols in base64
            # Each base64 symbol can encode 6 bits, so we have 48 bytes in our disposal
            random_bytes = base64.urlsafe_b64encode(geturandom(48))
            self.add_tokeninfo("enrollment_credential", random_bytes)
        else:
            raise ParameterError("Invalid Parameters. Either provide (genkey) or (serial, enrollment_credential).")

        TokenClass.update(self, upd_param, reset_failcount)

    @log_with(log)
    def get_init_detail(self, params=None, user=None):
        """
        This returns the init details during enrollment.

        In the 1st step the QR Code is returned.
        """
        response_detail = TokenClass.get_init_detail(self, params, user)
        if "otpkey" in response_detail:
            del response_detail["otpkey"]
        params = params or {}
        # Add rollout state the response
        response_detail['rollout_state'] = self.token.rollout_state

        extra_data = {"enrollment_credential": self.get_tokeninfo("enrollment_credential")}
        imageurl = params.get("appimageurl")
        if imageurl:
            extra_data.update({"image": imageurl})
        if self.token.rollout_state == ROLLOUTSTATE.CLIENTWAIT:
            # Get enrollment values from the policy
            # Get the values from the configured TPUSH config
            # this allows to upgrade our crypto
            extra_data["v"] = 1
            extra_data["serial"] = self.get_serial()

            # enforce App pin
            if params.get(ACTION.FORCE_APP_PIN):
                extra_data.update({'pin': True})

            # We display this during the first enrollment step!
            bot = self._get_bot({"g": params.get("g"), "user": user})
            enrollment_credential = self.get_tokeninfo("enrollment_credential")
            qr_url = f"https://t.me/{bot.get_bot_name()}?start={enrollment_credential}"
            response_detail["pushurl"] = {"description": _("URL for privacyIDEA Telegram Push Token"),
                                          "value": qr_url,
                                          "img": create_img(qr_url)
                                          }

            response_detail["enrollment_credential"] = enrollment_credential

        return response_detail

    _bot_factory = None

    @classmethod
    def _get_bot(cls, options):
        """
        Calls a bot factory method with necessary configuration values
        """
        bot_token = get_action_values_from_options(
            SCOPE.AUTH, TELEGRAM_PUSH_ACTION.TELEGRAM_BOT_TOKEN, options)
        bot_api_url = get_action_values_from_options(
            SCOPE.AUTH, TELEGRAM_PUSH_ACTION.TELEGRAM_BOT_API_URL, options)
        webhook_url = get_action_values_from_options(
            SCOPE.ENROLL, TELEGRAM_PUSH_ACTION.WEBHOOK_URL, options)
        return cls._bot_factory(bot_token, bot_api_url, webhook_url)

    @classmethod
    def _complete_enrollment(cls, chat_id: int, enrollment_credential: str, reply_func: Callable[[TelegramMessageData], Any]):
        log.debug("Do the 2nd step of the enrollment.")
        try:
            token_obj: TelegramPushTokenClass = get_one_token(tokeninfo={"enrollment_credential": enrollment_credential},
                                        tokentype="tpush",
                                        rollout_state=ROLLOUTSTATE.CLIENTWAIT)
            serial = token_obj.get_serial()
            token_obj.update({"serial": serial, TELEGRAM_CHAT_ID: str(chat_id), "enrollment_credential": enrollment_credential})
            # in case of validate/check enrollment
            chals = get_challenges(serial=serial)
            if chals and chals[0].is_valid() and chals[0].get_session() == CHALLENGE_SESSION.ENROLLMENT:
                chals[0].set_otp_status(True)
                chals[0].save()
            reply_func(TelegramMessageData(_("Registration of Telegram Push token successfully completed.")))
            return True
        except ResourceNotFoundError:
            log.debug("No token with this serial number in the rollout state 'clientwait'.")
        reply_func(TelegramMessageData(_("No unregistered token found for this enrollment challenge.")))

    @classmethod
    def _on_push_click(cls, push_click_event: PushClickEvent, reply_func: Callable[[str], Any]):
        log.debug("Handling the authentication response from the Telegram.")
        # Do the 2nd step of the authentication
        # Find valid challenges
        challengeobject_list = get_challenges(serial=push_click_event.serial, challenge=push_click_event.challenge)

        if challengeobject_list:
            # There are valid challenges, so we check this signature
            for chal in challengeobject_list:
                log.debug("Found matching challenge {0!s}.".format(chal))
                if not push_click_event.is_accepted:
                    # If the challenge is declined, we delete it from the DB
                    chal.delete()
                    reply_func(_("Login declined"))
                else:
                    chal.set_otp_status(True)
                    chal.save()
                    reply_func(_("Login confirmed"))
                return True
        return False

    @classmethod
    def _api_endpoint_post(cls, request_data, g):
        """ Handle all POST requests to the api endpoint

        :param request_data: Dictionary containing the parameters of the request
        :type request_data: dict
        :returns: The result of handling the request and a dictionary containing
                  the details of the request handling
        :rtype: (bool, dict)
        """
        details = {}

        update = telebot.types.Update.de_json(request_data)
        bot = cls._get_bot({"g": g})
        result = bot.process_new_update(update)
        return result, details

    @classmethod
    def api_endpoint(cls, request: PiRequestClass, g):
        """
        This provides a function which is called by the API endpoint
        ``/ttype/tpush`` which is defined in :doc:`../../api/ttype`

        The method returns a tuple ``("json", {})``

        This endpoint provides a webhook target for Telegram Bot API,
        since polling Bot API in a background thread is not feasible in Flask/WSGI context

        :param request: The Flask request
        :param g: The Flask global object g
        :return: The json string representing the result dictionary
        :rtype: tuple("json", str)
        """
        if request.method == 'POST':
            result, details = cls._api_endpoint_post(request.all_data, g)
        else:
            raise privacyIDEAError('Method {0!s} not allowed in \'api_endpoint\' '
                                   'for push token.'.format(request.method))

        return "json", prepare_result(result, details=details)

    @log_with(log)
    def is_challenge_request(self, passw, user=None, options=None):
        """
        check, if the request would start a challenge

        We need to define the function again, to get rid of the
        is_challenge_request-decorator of the base class

        :param passw: password, which might be pin or pin+otp
        :param options: dictionary of additional request parameters

        :return: returns true or false
        """
        if options.get(TELEGRAM_PUSH_ACTION.WAIT):
            # We have a push_wait in the parameters
            return False
        return self.check_pin(passw, user=user, options=options)

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

        data = None
        # Initially we assume there is no error from Firebase
        res = True
        telegram_chatid = self.get_tokeninfo(TELEGRAM_CHAT_ID)
        if telegram_chatid:
            challenge = b32encode_and_unicode(geturandom(10))
            if options.get("session") != CHALLENGE_SESSION.ENROLLMENT:
                bot = self._get_bot(options)
                message = _build_message_data(self.token.serial, challenge, options)
                res = bot.submit_message(telegram_chatid, message)

            # Create the challenge in the challenge table if either the message
            # was successfully submitted to the Bot API
            if res:
                validity = int(get_from_config('DefaultChallengeValidityTime', 120))
                tokentype = self.get_tokentype().lower()
                # Maybe there is a PushChallengeValidityTime...
                lookup_for = tokentype.capitalize() + 'ChallengeValidityTime'
                validity = int(get_from_config(lookup_for, validity))

                # Create the challenge in the database
                db_challenge = Challenge(self.token.serial,
                                         transaction_id=transactionid,
                                         challenge=challenge,
                                         data=data,
                                         session=options.get("session"),
                                         validitytime=validity)
                db_challenge.save()
                self.challenge_janitor()
                transactionid = db_challenge.transaction_id

            # If sending the Push message failed, we log a warning
            if not res:
                log.warning(u"Failed to submit message to Telegram bot api service for token {0!s}."
                            .format(self.token.serial))
                if is_true(options.get("exception")):
                    raise ValidateError("Failed to submit message to Telegram Bot Api.")
        else:
            log.warning(u"The token {0!s} has no tokeninfo {1!s}. "
                        u"The message could not be sent.".format(self.token.serial,
                                                                 TELEGRAM_CHAT_ID))
            if is_true(options.get("exception")):
                raise ValidateError("The token has no tokeninfo. Can not send via Firebase service.")

        reply_dict = {"attributes": {"hideResponseInput": self.client_mode != CLIENTMODE.INTERACTIVE}}
        return True, message.message, transactionid, reply_dict

    @check_token_locked
    def authenticate(self, passw, user=None, options=None):
        """
        High level interface which covers the check_pin and check_otp
        This is the method that verifies single shot authentication.
        The challenge is sent to the smartphone app and privacyIDEA
        waits for the response to arrive.

        :param passw: the password which could be pin+otp value
        :type passw: string
        :param user: The authenticating user
        :type user: User object
        :param options: dictionary of additional request parameters
        :type options: dict

        :return: returns tuple of

          1. true or false for the pin match,
          2. the otpcounter (int) and the
          3. reply (dict) that will be added as additional information in the
             JSON response of ``/validate/check``.

        :rtype: tuple
        """
        otp_counter = -1
        reply = None
        pin_match = self.check_pin(passw, user=user, options=options)
        if pin_match:
            if not options.get("valid_token_num"):
                # We should only do push_wait, if we do not already have successfully authenticated tokens!
                waiting = int(options.get(TELEGRAM_PUSH_ACTION.WAIT, 20))
                # Trigger the challenge
                _t, _m, transaction_id, _attr = self.create_challenge(options=options)
                # now we need to check and wait for the response to be answered in the challenge table
                starttime = time.time()
                while True:
                    db.session.commit()
                    otp_counter = self.check_challenge_response(options={"transaction_id": transaction_id})
                    elapsed_time = time.time() - starttime
                    if otp_counter >= 0 or elapsed_time > waiting or elapsed_time < 0:
                        break
                    time.sleep(DELAY - (elapsed_time % DELAY))

        return pin_match, otp_counter, reply

    @check_token_locked
    def check_challenge_response(self, user=None, passw=None, options=None):
        """
        This function checks, if the challenge for the given transaction_id
        was marked as answered correctly.
        For this we check the otp_status of the challenge with the
        transaction_id in the database.

        We do not care about the password

        :param user: the requesting user
        :type user: User object
        :param passw: the password (pin+otp)
        :type passw: string
        :param options: additional arguments from the request, which could
                        be token specific. Usually "transaction_id"
        :type options: dict
        :return: return otp_counter. If -1, challenge does not match
        :rtype: int
        """
        options = options or {}
        otp_counter = -1

        # fetch the transaction_id
        transaction_id = options.get('transaction_id')
        if transaction_id is None:
            transaction_id = options.get('state')

        # get the challenges for this transaction ID
        if transaction_id is not None:
            challengeobject_list = get_challenges(serial=self.token.serial,
                                                  transaction_id=transaction_id)

            for challengeobject in challengeobject_list:
                # check if we are still in time.
                if challengeobject.is_valid():
                    _, status = challengeobject.get_otp_status()
                    if status is True:
                        # create a positive response
                        otp_counter = 1
                        # delete the challenge, should we really delete the challenge? If we do so, the information
                        # about the successful authentication could be fetched only once!
                        # challengeobject.delete()
                        break

        return otp_counter
