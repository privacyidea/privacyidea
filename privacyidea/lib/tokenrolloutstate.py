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

    @classmethod
    def enrollment_pending_states(cls) -> list[str]:
        """
        The states in which the enrollment of a token is under way and a further request is expected to finish
        it, e.g. the second request of a two-step or a FIDO2 enrollment.

        A token in one of these states cannot authenticate yet, so a request that continues its enrollment is
        still an enrollment. A token in any other state either authenticates or has failed, and a request
        against it changes a token that is already in use.

        :return: list of rollout states
        """
        return [cls.CLIENTWAIT, cls.PENDING, cls.VERIFY_PENDING]
