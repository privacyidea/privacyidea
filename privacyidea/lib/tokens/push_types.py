from enum import Enum


class PushMode(str, Enum):
    STANDARD = "standard"
    REQUIRE_PRESENCE = "require_presence"
    CODE_TO_PHONE = "code_to_phone"


class PushPresenceOptions(str, Enum):
    ALPHABETIC = "ALPHABETIC"
    NUMERIC = "NUMERIC"
    CUSTOM = "CUSTOM"


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
    PUSH_MODE_CODE_TO_PHONE = "push_mode_code_to_phone"
    PRESENCE_OPTIONS = "push_presence_options"
    PRESENCE_CUSTOM_OPTIONS = "push_presence_custom_options"
    PRESENCE_NUM_OPTIONS = "push_presence_num_options"
    USE_PIA_SCHEME = "push_use_pia_scheme"


class PushAllowPolling:
    ALLOW = 'allow'
    DENY = 'deny'
    TOKEN = 'token'  # nosec B105 # key name