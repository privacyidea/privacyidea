# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import Enum


class PushMode(str, Enum):
    STANDARD = "standard"
    REQUIRE_PRESENCE = "require_presence"
    CODE_TO_PHONE = "code_to_phone"

# Length of the short display code for code_to_phone mode.
# The security does not lie in this code; it's only used so the client
# knows the smartphone has completed its confirmation.
CODE_TO_PHONE_DISPLAY_CODE_LENGTH = 2


class PushPresenceOptions(str, Enum):
    ALPHABETIC = "ALPHABETIC"
    NUMERIC = "NUMERIC"
    CUSTOM = "CUSTOM"


class PushDeclineReason(str, Enum):
    """Why the user refused a push challenge. Signed by the smartphone as part
    of the decline payload and used to differentiate the two decline events in
    the authentication log / conditional-access policies.

    ``__str__`` returns the value so members interpolate to their string form on
    every supported Python version (3.10+). On a 3.11+ floor this can subclass
    :class:`enum.StrEnum` and drop ``__str__`` instead, with no change to usage.
    """
    UNKNOWN_TRIGGER = "unknown_trigger"  # the user did not trigger this request
    CANCELLED = "cancelled"  # the user triggered it, but aborted

    def __str__(self) -> str:
        return self.value


class PushCapability(str, Enum):
    """Optional push features this server version supports, advertised to the
    smartphone in every challenge so a newer app knows which fields it may add
    to its signed answer. An absent capability means the app falls back to
    legacy behaviour. Adding a feature is appending a member.

    ``__str__`` returns the value so members interpolate to their string form,
    matching :class:`PushDeclineReason`.
    """
    DECLINE_REASON = "decline_reason"

    def __str__(self) -> str:
        return self.value


class PushAction:
    FIREBASE_CONFIG = "push_firebase_configuration"
    REGISTRATION_URL = "push_registration_url"
    TTL = "push_ttl"
    MOBILE_TEXT = "push_text_on_mobile"
    MOBILE_TITLE = "push_title_on_mobile"
    SSL_VERIFY = "push_ssl_verify"
    WAIT = "push_wait"
    ALLOW_POLLING = "push_allow_polling"
    REQUIRE_PRESENCE = "push_require_presence"
    PUSH_CODE_TO_PHONE = "push_code_to_phone"
    PUSH_CODE_TO_PHONE_MESSAGE = "push_code_to_phone_message"
    PRESENCE_OPTIONS = "push_presence_options"
    PRESENCE_CUSTOM_OPTIONS = "push_presence_custom_options"
    PRESENCE_NUM_OPTIONS = "push_presence_num_options"
    USE_PIA_SCHEME = "push_use_pia_scheme"
    CHALLENGE_TEXT = "push_challenge_text"


class PushAllowPolling:
    ALLOW = 'allow'
    DENY = 'deny'
    TOKEN = 'token'  # nosec B105 # key name
