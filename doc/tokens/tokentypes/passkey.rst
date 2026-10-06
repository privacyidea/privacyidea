.. _passkey:

Passkey
-------

.. index:: Passkey, FIDO2

Starting with version 3.11 privacyIDEA supports the passkey token.
A passkey is a FIDO authentication credential based on FIDO standards, that allows a user to sign in to apps and
websites with the same process that they use to unlock their device (biometrics, PIN, or pattern).
Passkeys are FIDO cryptographic credentials that are tied to a user’s account on a website or application.
Passkeys are phishing resistant and secure by design. They inherently help reduce attacks from cybercriminals
such as phishing, credential stuffing, and other remote attacks.

This is a variation of the WebAuthn token, which is also a FIDO2 token supported by privacyIDEA.
It uses the WebAuthn configuration described in :ref:`webauthn_otp_token` (relying party ID and name, challenge
validity time) and the WebAuthn policies for user verification and public key credential algorithms. The WebAuthn
policies :ref:`policy_webauthn_enroll_timeout`, :ref:`policy_webauthn_enroll_authenticator_attachment` and
:ref:`policy_webauthn_authn_allowed_transports` do not apply to passkeys; the registration timeout of a passkey is
fixed at 12 seconds.
The Passkey token always requests to be created as a resident credential, i.e. the option
``resident_key`` is always set to ``required``, in contrast to the WebAuthn token, which does not request a resident
key.

To enroll a passkey, the policies :ref:`policy_webauthn_enroll_relying_party_id` and
:ref:`policy_webauthn_enroll_relying_party_name` have to be set. Moreover, passkeys always require a user assignment
for enrollment.

Passkeys are eligible for offline use as specified here :ref:`application_offline` as well as
:ref:`policy_enroll_via_multichallenge`. However, these features also have to be implemented in the client application.

Using passkeys in different browsers and environments can yield different user experiences. Most, if not all browsers,
will not allow enrollment of a passkey to an authenticator which does not have a PIN set. The enrollment policy
:ref:`policy_webauthn_enroll_user_verification_requirement` sets the user verification that privacyIDEA requests from
the authenticator when a passkey is registered (default ``preferred``). The same policy
:ref:`policy_webauthn_authn_user_verification_requirement` is available in the scope authentication and affects
passkey authentication. A login to the WebUI with a passkey always
requires user verification, and so does a login to the WebUI without a username with a WebAuthn token.

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

User Label
~~~~~~~~~~

The name of the passkey that the authenticator shows in the credential selection during login (and during
registration) can be configured with the policy :ref:`policy_passkey_user_label`. This is useful to tell passkeys
apart, for example when the same login name exists in several realms. The resolved value is also used as the
display name. If the policy is not set, the login name of the user is used. The policy value supports tags such
as ``{user}`` (login name), ``{realm}``, ``{resolver}`` and ``{serial}``, as well as any attribute the user's
resolver provides (e.g. ``{givenname}``, ``{surname}``, ``{email}``). A value like ``{user}@{realm}`` results in
a name such as ``alice@example``. See the policy for details on the available tags and the 64 byte length limit.

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

If the authenticator sends an attestation statement, the WebAuthn library checks it: the signature of the
statement, and for the ``apple``, ``android-key`` and ``android-safetynet`` formats the certificate chain up to the
vendor root certificates built into the library. A registration that fails these checks is rejected. Beyond that,
privacyIDEA only archives the leaf certificate: there is no configurable trust validation (the trust anchor directory
of the WebAuthn token is not used), no AAGUID allow-listing and no filtering of passkey tokens based on attestation
data. If attestation-based filtering or trust validation is required, use the :ref:`WebAuthn token <webauthn>`
instead.

.. _passkey_device_type:

Device type
~~~~~~~~~~~

Every passkey reports one of two device types:

* ``single_device``: the private key cannot be backed up and does not leave the authenticator, for example a
  FIDO2 security key or a platform authenticator that does not sync.
* ``multi_device``: the private key can be backed up, typically because a passkey manager syncs it to the user's
  other devices through a cloud account.

The device type is derived from the backup eligibility flag in the authenticator data. This flag is fixed when the
credential is created and does not change afterwards. privacyIDEA stores the device type in the token info as
``device_type``. The token info ``backed_up`` records whether the credential had actually been backed up at the
time of enrollment. That state can change at any time and is not updated later, so it is for information only.

The policy ``passkey_allowed_authenticator_device_types`` restricts passkeys to one of the device types. It exists
in the :ref:`enrollment scope <policy_passkey_enroll_allowed_authenticator_device_types>` and in the
:ref:`authentication scope <policy_passkey_authn_allowed_authenticator_device_types>`, and the two are independent
of each other.

.. warning:: The device type is reported by the authenticator in its authenticator data. At **authentication**,
    the authenticator data is signed with the passkey's own key, so the client between the authenticator and
    privacyIDEA cannot change the reported device type; the signature only shows that the authenticator holding
    the key reported it, not that it is true. At **enrollment**, privacyIDEA accepts registrations without an
    attestation statement - with the default :ref:`policy_passkey_attestation_conveyance_preference` ``none``, and
    also when ``direct`` was requested but the client sends no statement. The authenticator data of such a
    registration is not signed, so the client that relays the registration can change the reported device type,
    and the enrollment check only sees what the client reports.

    Use the :ref:`authentication policy <policy_passkey_authn_allowed_authenticator_device_types>` to enforce the
    device type: it keeps out passkeys whose authenticator reports ``multi_device``, such as passkeys synced by the
    passkey manager of the operating system. The
    :ref:`enrollment policy <policy_passkey_enroll_allowed_authenticator_device_types>` only filters registrations
    whose client passes the authenticator's value through unchanged. Neither keeps out an authenticator that
    reports ``single_device`` although it can export or sync the key, for example a software authenticator or a
    faulty implementation. If you need assurance that the key cannot leave the hardware, use the
    :ref:`WebAuthn token <webauthn>` and set :ref:`policy_webauthn_enroll_authenticator_attestation_level` to
    ``trusted``.

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
were enrolled as WebAuthn tokens before the passkey token type existed (before
3.11) are usable through the usernameless passkey flow once they have been used
for one regular authentication with a user name, which records their credential
ID. See :ref:`webauthn_passkey_interop` for how clients pass WebAuthn and
passkey challenges to the authenticator.

A non-exhaustive list of devices that are known to work can be found here :ref:`fido_device_matrix`.