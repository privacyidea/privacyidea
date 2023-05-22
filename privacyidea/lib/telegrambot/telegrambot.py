import telebot
from telebot.types import *
from functools import cache
import time

from privacyidea.lib.tokens.telegrampushtoken import PushClickEvent, TelegramMessageData, TelegramPushTokenClass

log = logging.getLogger(__name__)


class TelegramBot:
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
        try:
            event = PushClickEvent(callback_query.data)
            self._on_push_click(event)
        finally:
            return
        
    def _handle_start(self, message: Message):
        try:
            split = message.text.split()
            if len(split) != 2:
                self._bot.reply_to(message, "Hi there, I am Telegram 2FA push bot. "
                                   "To complete registration of your account as a 2nd factor you have to use QR code or url link with embedded registration token, or manually run command /start [TOKEN]")
                return
            
            enrollment_credential = split[1]
            chat_id = message.chat.id
            self._complete_enrollment(chat_id, enrollment_credential, lambda msg: self.submit_message(chat_id, msg))
        finally:
            return

    def _send_welcome(self, message: Message):
        self._bot.reply_to(message, "Hi there, I am Telegram 2FA push bot. You'll need to register your Telegram account"
                                    " before I can send you 2FA notifications. You have to obtain registration link/QR and" 
                                    " then initiate dialog with me again. Please, delete this chat for now or the registration link won't work!")

    def process_new_update(self, update: Update):
        self._bot.process_new_updates([update])

    def submit_message(self, chat_id: int, message: TelegramMessageData):
        try:
            markup = None
            if message.callback_data is not None:
                from telebot.util import quick_markup

                markup = quick_markup({
                    'Confirm': {'callback_data': f"C_{message.callback_data}"},
                    'Decline': {'callback_data': f"D_{message.callback_data}"}
                }, row_width=2)
                # markup = InlineKeyboardMarkup()
                # markup.add(InlineKeyboardButton(text="Confirm", callback_data=f"C_{message.callback_data}"),
                #            InlineKeyboardButton(text="Decline", callback_data=), 2)
            msg = self._bot.send_message(chat_id, text=message.message, reply_markup=markup)
            if msg is None:
                log.warning("Error sending message to a chat %s", chat_id)
                return False
            return True
        except Exception as err:
            log.error(f"Exception sending message to a chat: {err}")
            return False

    def confirm_callback(self, callback: CallbackQuery):
        self._bot.answer_callback_query(callback.id, "Ok")

    @cache
    def get_bot_name(self):
        user = self._bot.get_me()
        return user.username