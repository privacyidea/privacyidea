from privacyidea.lib.cache.redis import (  # noqa: F401
    get_redis,
    redis_feature_enabled,
    redis_feature_configured,
    redis_client_for_feature,
    cache_challenge,
    evict_challenge,
    evict_transaction,
    evict_challenges_for_serial,
    get_challenges_from_cache,
    CacheState,
    ChallengeDTO,
)
from privacyidea.lib.cache.auth import cache_enabled as auth_cache_enabled  # noqa: F401
from privacyidea.lib.cache.user import (  # noqa: F401
    cached_user_id,
    cached_user_info,
    cached_username,
    flush_user_cache,
    invalidate_resolver,
    invalidate_user,
)

POLICY_CACHE = None
CONFIG_CACHE = None


def set_policy_cache(pol):
    global POLICY_CACHE
    POLICY_CACHE = pol


def get_policy_cache():
    return POLICY_CACHE


def get_config_cache():
    return CONFIG_CACHE


def set_config_cache(conf):
    global CONFIG_CACHE
    CONFIG_CACHE = conf
