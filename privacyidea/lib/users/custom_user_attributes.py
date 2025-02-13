INTERNAL_USAGE = "pi_internal"

class InternalCustomUserAttributes:
    PREFERRED_TOKEN_TYPE = "preferred_token_type"

    def get_internal_custom_user_attributes(self):
        return [self.PREFERRED_TOKEN_TYPE]
