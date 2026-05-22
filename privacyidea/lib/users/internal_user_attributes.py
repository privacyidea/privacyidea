class InternalUserAttributes:
    """
    Reserved key names for the ``internaluserattribute`` table.

    Admins must not be able to create ``customuserattribute`` rows that
    collide with these names — :func:`get_internal_prefixes` is used at the
    user-attribute API boundary to reject such names.
    """
    LAST_USED_TOKEN = "last_used_token"

    @classmethod
    def get_internal_prefixes(cls):
        return [cls.LAST_USED_TOKEN]
