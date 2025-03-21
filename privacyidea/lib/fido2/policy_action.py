class FIDO2PolicyAction:
    ALLOWED_TRANSPORTS = 'webauthn_allowed_transports'
    TIMEOUT = 'webauthn_timeout'
    RELYING_PARTY_NAME = 'webauthn_relying_party_name'
    RELYING_PARTY_ID = 'webauthn_relying_party_id'
    AUTHENTICATOR_ATTACHMENT = 'webauthn_authenticator_attachment'
    AUTHENTICATOR_SELECTION_LIST = 'webauthn_authenticator_selection_list'
    USER_VERIFICATION_REQUIREMENT = 'webauthn_user_verification_requirement'
    PUBLIC_KEY_CREDENTIAL_ALGORITHMS = 'webauthn_public_key_credential_algorithms'
    AUTHENTICATOR_ATTESTATION_FORM = 'webauthn_authenticator_attestation_form'
    AUTHENTICATOR_ATTESTATION_LEVEL = 'webauthn_authenticator_attestation_level'
    REQ = 'webauthn_req'
    AVOID_DOUBLE_REGISTRATION = 'webauthn_avoid_double_registration'


class PasskeyAction:
    AttestationConveyancePreference = "passkey_attestation_conveyance_preference"
    EnableTriggerByPIN= "passkey_trigger_by_pin"