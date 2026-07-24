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
The Passkey token always requests to be created as a resident credential, i.e. the option
``resident_key`` is always set to ``required``, in contrast to the WebAuthn token, which does not request a resident
key.

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

.. note:: If user verification is **not** required on authentication and a user has multiple discoverable credentials
    for the same relying party on one authenticator (typically an external FIDO2 security key with several passkeys
    enrolled to the same site), the browser's account picker may display generic placeholder labels for the
    credentials (for example "Passkey 1", "Passkey 2" or "Unknown") instead of the actual user names. This is a
    CTAP2 behavior: the authenticator only releases the ``user.name`` and ``user.displayName`` fields of a
    discoverable credential after user verification has been performed. Without UV, the browser has only the opaque
    ``user.id`` handle to work with and falls back to a non-identifying label. The exact string shown depends on the
    browser and operating system. Platform authenticators (Touch ID, Windows Hello, Face ID, synced platform
    passkeys) intrinsically perform user verification on every assertion and are not affected. Set
    :ref:`policy_webauthn_authn_user_verification_requirement` to ``required`` if you want the names to appear in
    the picker for external security keys as well.

On the token detail page, the passkey can be tested and, if successful, will show the username that is returned by
privacyIDEA to use for login.

Display Name
~~~~~~~~~~~~

The display name of the passkey that the authenticator shows during registration can be configured with the
policy :ref:`policy_passkey_user_display_name`. If the policy is not set, the login name of the user is used.
The policy value supports tags such as ``{user}`` (login name), ``{realm}``, ``{resolver}`` and ``{serial}``, as
well as any attribute the user's resolver provides (e.g. ``{givenname}``, ``{surname}``, ``{email}`` for LDAP).
A value like ``{user}@{realm}`` results in a display name such as ``alice@example``. See the policy for details
on the available tags and the 64 byte length limit.

Attestation
~~~~~~~~~~~

Attestation during passkey registration is controlled by its own policy,
:ref:`policy_passkey_attestation_conveyance_preference`. The WebAuthn attestation policies
:ref:`policy_webauthn_enroll_authenticator_attestation_form` and
:ref:`policy_webauthn_enroll_authenticator_attestation_level` do **not** apply to passkey enrollment.

The default and recommended value is ``none``. Passkeys are intended as a user-friendly, privacy-preserving
credential, and requesting attestation works against both goals:

* With ``none``, the authenticator data returned to privacyIDEA contains a zeroed AAGUID and no attestation
  statement, so the specific make and model of the authenticator is not disclosed.
* With ``indirect``, ``direct`` or ``enterprise``, the authenticator returns its real AAGUID and an attestation
  statement. If the statement contains an x5c certificate chain, the leaf certificate (which typically identifies
  the make and model of the authenticator) is stored in the token info as ``attestation_certificate``. If the
  token has no description yet, its description is set to the certificate's Common Name.
* Requesting attestation also causes additional friction during enrollment: most browsers will show an extra
  consent dialog informing the user that information identifying their authenticator will be sent to the site,
  which can be confusing for end users and is not aligned with how passkeys are typically presented.

privacyIDEA currently only archives the attestation certificate; there is no trust-chain validation, AAGUID
allow-listing or filtering of passkey tokens based on attestation data. If attestation-based filtering or trust
validation is required, use the :ref:`webauthn_otp_token` instead.

Avoiding double registration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

During passkey enrollment, privacyIDEA always sends the credential ids of the user's existing passkey and
WebAuthn tokens in the WebAuthn ``excludeCredentials`` list. The authenticator will then refuse to create a new
credential if it already holds one of these, preventing a user from accidentally registering the same authenticator
twice. Unlike the :ref:`policy_webauthn_avoid_double_registration` policy for WebAuthn tokens, this behavior is
always on for passkeys and is not configurable.

Tokens that have been **revoked** are excluded from this list, so the same authenticator can be re-enrolled for
the user after revocation. Tokens that are merely **disabled** are still included, since disabling is reversible
and the underlying credential is still bound to the user. Tokens whose enrollment never finished
(rollout state ``clientwait``) are also excluded.

Relationship to the WebAuthn token
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Platform credentials (Touch ID, Windows Hello, synced platform passkeys) that
were enrolled as WebAuthn tokens before the passkey token type existed are
still usable through the usernameless passkey flow. See
:ref:`webauthn_passkey_interop` for the encoding background and the
recommendation to prefer the passkey token when both a passkey and a WebAuthn
token are triggered for the same user in one transaction.

A non-exhaustive list of devices that are known to work can be found here :ref:`fido_device_matrix`.