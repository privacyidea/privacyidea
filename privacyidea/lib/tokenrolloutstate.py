class RolloutState:
    CLIENTWAIT = 'clientwait'
    # The rollout is pending in the backend, like CSRs that need to be approved
    PENDING = 'pending'
    # This means the user needs to authenticate to verify that the token was successfully enrolled.
    VERIFY_PENDING = 'verify'
    ENROLLED = 'enrolled'
    BROKEN = 'broken'
    FAILED = 'failed'
    DENIED = 'denied'

    @classmethod
    def all_states(cls):
        return [v for k, v in vars(cls).items() if not k.startswith('_') and isinstance(v, str)]
