POLICY_CACHE = None


def set_policy_cache(pol):
    global POLICY_CACHE
    POLICY_CACHE = pol


def get_policy_cache():
    return POLICY_CACHE
