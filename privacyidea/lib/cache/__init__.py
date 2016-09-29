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
