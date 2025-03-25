.. _passkey:

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

To enroll a passkey, the policies :ref:`policy_webauthn_enroll_relying_party_id` and
:ref:`policy_webauthn_enroll_relying_party_name` have to be set. Moreover, passkeys always require a user assignment
for enrollment.

Passkeys are eligible for offline use as specified here :ref:`application_offline` as well as
:ref:`policy_enroll_via_multichallenge`. However, these features also have to be implemented in the client application.

Using passkeys in different browsers and environments can yield different user experiences. Most, if not all browsers,
will not allow enrollment of a passkey to a authenticator which does not have a PIN set, i.e. user verification is
always required for enrollment. Therefore, :ref:`policy_webauthn_enroll_user_verification_requirement` does not
affect passkey enrollment. The same policy :ref:`policy_webauthn_authn_user_verification_requirement` is available in
the scope authentication and that policy does affect passkey authentication.

On the token detail page, the passkey can be tested and, if successful, will show the username that is returned by
privacyIDEA to use for login.