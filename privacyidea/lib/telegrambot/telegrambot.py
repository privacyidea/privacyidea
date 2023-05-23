import telebot
from telebot.types import *
from telebot.util import quick_markup
from functools import cache
from privacyidea.lib import _
import time

from privacyidea.lib.tokens.telegrampushtoken import PushClickEvent, TelegramMessageData, TelegramPushTokenClass

log = logging.getLogger(__name__)


class TelegramBot:
    """
    This class wraps a singleton TeleBot instance to communicate with the Bot API
    It tries to have a unidirectional dependency only to a domain class TelegramPushTokenClass by using callbacks 
    with late binding
    """
    @classmethod
    def init_callbacks(cls):
        cls._complete_enrollment = TelegramPushTokenClass._complete_enrollment
        cls._on_push_click = TelegramPushTokenClass._on_push_click
        TelegramPushTokenClass._bot_factory = cls.get_instance

    @classmethod
    @cache
    def get_instance(cls, bot_api_token: str, bot_api_url: str, bot_webhook_endpoint: str):
        """
        :rtype: TelegramBot
        """
        return TelegramBot(bot_api_token, bot_api_url, bot_webhook_endpoint)

    def __init__(self, bot_api_token, bot_api_url, bot_webhook_endpoint):
        # Threaded environment doesn't work well with flask
        self._bot = telebot.TeleBot(bot_api_token, threaded=False)
        telebot.apihelper.API_URL = bot_api_url
        self._bot.register_message_handler(self._handle_start, commands=['start'])
        self._bot.register_message_handler(self._send_welcome)
        self._bot.register_callback_query_handler(self._handle_callback, lambda x: True)
        # Remove webhook, it fails sometimes if there is a previous webhook
        self._bot.remove_webhook()
        time.sleep(0.1)
        # Set webhook
        self._bot.set_webhook(url=bot_webhook_endpoint, drop_pending_updates=True)

    def _handle_callback(self, callback_query: CallbackQuery):
        """
        This method handles a click on inline button
        """
        try:
            event = PushClickEvent(callback_query.data)
            self._on_push_click(event, lambda msg: self._confirm_callback(callback_query, msg))
        finally:
            return

    def _handle_start(self, message: Message):
        """
        Handler of a start command - special command to a Telegram bot which is required to start conversation
        """
        try:
            split = message.text.split()
            if len(split) != 2:
                # If user manually types /start we give him a hint
                self._bot.reply_to(message,
                                _("Hi there, I am Telegram 2FA push bot. "
                                "To complete registration of your account as a 2nd factor you either have to use QR code "
                                ", or url link with embedded registration token, or manually run command /start [TOKEN]"))
                return

            enrollment_credential = split[1]
            chat_id = message.chat.id
            # normally users will send a start command during the 2nd step of an enrollment through deep link in a QR code
            self._complete_enrollment(chat_id, enrollment_credential, lambda msg: self.submit_message(chat_id, msg))
        finally:
            return

    def _send_welcome(self, message: Message):
        """
        Catch-all handler to greet the user if it sends unexpected things to a bot
        """
        self._bot.reply_to(message, _("Hi there, I am Telegram 2FA push bot. You'll need to register your Telegram account"
                                    " before I can send you 2FA notifications. You have to obtain registration link/QR and" 
                                    " then use this link to start dialog with me again. "))

    def process_new_update(self, update: Update):
        """
        Public method to pipe received json from a webhook to a TeleBot engine
        """
        self._bot.process_new_updates([update])

    def submit_message(self, chat_id: int, message: TelegramMessageData):
        """
        Public method which consumers can use to send arbitrary text message to a private chat of a bot with the user.
        Message could also contain 64-symbol data, in which case two inline buttons will be created under the message
        """
        try:
            markup = None
            if message.callback_data is not None:
                markup = quick_markup({
                    'Confirm': {'callback_data': f"C_{message.callback_data}"},
                    'Decline': {'callback_data': f"D_{message.callback_data}"}
                }, row_width=2)
            msg = self._bot.send_message(chat_id, text=message.message, reply_markup=markup)
            if msg is None:
                log.warning("Error sending message to a chat %s", chat_id)
                return False
            return True
        except Exception as err:
            log.error(f"Exception sending message to a chat: {err}")
            return False

    def _confirm_callback(self, callback: CallbackQuery, text: str):
        self._bot.answer_callback_query(callback.id, text)

    @cache
    def get_bot_name(self):
        """
        Asking username of a bot from API so that administrator won't need to set in manually in the policies
        """
        user = self._bot.get_me()
        return user.username
