INTERNAL_USAGE = "pi_internal"

class InternalCustomUserAttributes:
    LAST_USED_TOKEN = "last_used_token"

    @classmethod
    def get_internal_prefixes(cls):
        return [cls.LAST_USED_TOKEN]
