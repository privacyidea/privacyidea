.. _webauthn:

WebAuthn
--------

.. index:: WebAuth, FIDO2

Starting with version 3.4 privacyIDEA supports WebAuthn tokens. The
administrator or the user himself can register a WebAuthn device and use this
WebAuthn token to login to the privacyIDEA WebUI or to authenticate against
applications.

When enrolling the token, a key pair is generated and the public key is sent to
privacyIDEA. During this process, the user needs to prove that he is
present, which typically happens by tapping a button on the token. The user may
also be required by policy to provide some form of verification, which might be
biometric or knowledge-based, depending on the token.

When enrolling, the authenticator is not requested to create a resident key, in contrast to the passkey token: :ref:`passkey`.
However, the authenticator can still decide to create a resident key. If that is the case, the WebAuthn token can be used
like a passkey token for usernameless logins with privacyIDEA.

.. note:: This is a normal token object which can also be reassigned to
    another user.

.. note:: As the key pair is only generated virtually, you can register one
    physical device for several users.

For configuring privacyIDEA for the use of WebAuthn tokens, please see
:ref:`webauthn_otp_token`.

For further details and information how to add this to your application, see
the code documentation at :ref:`code_webauthn_token`.
