# SPDX-FileCopyrightText: 2026 NetKnights GmbH <https://netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum


class PushMode(StrEnum):
    STANDARD = "standard"
    REQUIRE_PRESENCE = "require_presence"
    CODE_TO_PHONE = "code_to_phone"

# Length of the short display code for code_to_phone mode.
# The security does not lie in this code; it's only used so the client
# knows the smartphone has completed its confirmation.
CODE_TO_PHONE_DISPLAY_CODE_LENGTH = 2


class PushPresenceOptions(StrEnum):
    ALPHABETIC = "ALPHABETIC"
    NUMERIC = "NUMERIC"
    CUSTOM = "CUSTOM"


class PushDeclineReason(StrEnum):
    """Why the user refused a push challenge. Signed by the smartphone as part
    of the decline payload and used to differentiate the two decline events in
    the authentication log / conditional-access policies.
    """
    UNKNOWN_TRIGGER = "unknown_trigger"  # the user did not trigger this request
    CANCELLED = "cancelled"  # the user triggered it, but aborted


class PushCapability(StrEnum):
    """Optional push features this server version supports, advertised to the
    smartphone in every challenge so a newer app knows which fields it may add
    to its signed answer, or in the enrollment URL for what the server can do
    at the enrollment (``key_algorithm``). An absent capability means the app
    falls back to legacy behaviour. Adding a feature is appending a member.

    Members are ``str``, so they serialise, compare and interpolate as their
    value without ``.value``.
    """
    DECLINE_REASON = "decline_reason"
    KEY_ALGORITHM = "key_algorithm"


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
    KEY_ALGORITHMS = "push_key_algorithms"


class PushKeyAlgorithm(StrEnum):
    """Key algorithms a push token may use for the smartphone and the server key pair.
    RSA 4096 is the default, ECDSA on secp256r1 is offered only when an enrollment
    policy allows it.
    """
    RSA_4096 = "rsa_4096"
    SECP256R1 = "secp256r1"


class PushAllowPolling:
    ALLOW = 'allow'
    DENY = 'deny'
    TOKEN = 'token'  # nosec B105 # key name
