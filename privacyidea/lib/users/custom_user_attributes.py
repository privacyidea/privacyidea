INTERNAL_USAGE = "pi_internal"

class InternalCustomUserAttributes:
    LAST_USED_TOKEN = "last_used_token"

    def get_internal_custom_user_attributes(self):
        return [self.LAST_USED_TOKEN]
