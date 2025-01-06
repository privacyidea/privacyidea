.. _passkey.rst

Passkey
-------

.. index:: Passkey, FIDO2

Starting with version 3.11 privacyIDEA supports Passkey token.
A passkey is a FIDO authentication credential based on FIDO standards, that allows a user to sign in to apps and
websites with the same process that they use to unlock their device (biometrics, PIN, or pattern).
Passkeys are FIDO cryptographic credentials that are tied to a user’s account on a website or application.
Passkeys are phishing resistant and secure by design. They inherently help reduce attacks from cybercriminals
such as phishing, credential stuffing, and other remote attacks.

This is a variation of the WebAuthn token, which is also a FIDO2 token supported by privacyIDEA.
Therefore, it inherits the configuration of the Webauthn token, which is described here: :ref:`webauthn_otp_token`.