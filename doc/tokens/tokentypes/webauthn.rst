.. _webauthn:

WebAuthn
--------

.. index:: WebAuth, FIDO2

.. note:: For new deployments the :ref:`passkey` token type is recommended over
    WebAuthn. The passkey token is a re-implementation on top of a maintained
    FIDO2 library and was created specifically to address shortcomings of the
    older WebAuthn implementation. The WebAuthn token type is kept primarily
    for existing deployments and for the few cases where attestation-based
    filtering (:ref:`policy_webauthn_enroll_req`,
    :ref:`policy_webauthn_enroll_authenticator_selection_list`,
    :ref:`policy_webauthn_enroll_authenticator_attestation_level` = ``trusted``)
    is required, which the passkey token does not provide.

Starting with version 3.4 privacyIDEA supports WebAuthn tokens. The
administrator or the user himself can register a WebAuthn device and use this
WebAuthn token to login to the privacyIDEA WebUI or to authenticate against
applications.

When enrolling the token, a key pair is generated and the public key is sent to
privacyIDEA. During this process, the user needs to prove that he is
present, which typically happens by tapping a button on the token. The user may
also be required by policy to provide some form of verification, which might be
biometric or knowledge-based, depending on the token.

When enrolling, the authenticator is not requested to create a resident key, in contrast to the :ref:`passkey` token,
which always requires one. The WebAuthn token does not pass a ``resident_key`` option to the authenticator, so the
authenticator falls back to its own default behavior. Some authenticators (notably platform authenticators such as
Touch ID, Windows Hello and synced platform passkeys) will still create a discoverable credential anyway. If that is
the case, the WebAuthn token can be used like a passkey token for usernameless logins; see
:ref:`webauthn_passkey_interop` below. There is no policy that lets you force or forbid resident-key creation on the
WebAuthn token — use the :ref:`passkey` token type if you need a guaranteed discoverable credential.

.. note:: This is a normal token object which can also be reassigned to
    another user.

.. note:: As the key pair is only generated virtually, you can register one
    physical device for several users.

For configuring privacyIDEA for the use of WebAuthn tokens, please see
:ref:`webauthn_otp_token`.

For further details and information how to add this to your application, see
the code documentation at :ref:`code_webauthn_token`.

Attestation
~~~~~~~~~~~

Attestation during WebAuthn enrollment is controlled by two policies:

* :ref:`policy_webauthn_enroll_authenticator_attestation_form` — what the
  client is asked to convey. ``none``, ``indirect``, ``direct`` (the default).
* :ref:`policy_webauthn_enroll_authenticator_attestation_level` — how
  strictly privacyIDEA evaluates whatever it receives. ``none``, ``untrusted``
  (the default), or ``trusted``.

With the default ``direct`` + ``untrusted`` combination, the authenticator
returns a full attestation statement and privacyIDEA records the leaf
certificate's issuer, subject and serial in token info
(``attestation_issuer``, ``attestation_subject``, ``attestation_serial``),
along with the AAGUID. The attestation signature is verified, but a
self-signed or unknown-signer attestation is accepted. If the token has no
description yet, the description is set to the leaf certificate's Common
Name (otherwise it falls back to ``Generic WebAuthn Token``).

Setting the level to ``trusted`` requires configuring a directory of trusted
attestation roots; see :ref:`webauthn_otp_token`. Enrollment is then rejected
unless the attestation statement's leaf certificate is signed directly by one
of the configured roots. **Full certificate chain traversal is not
performed**, and there is no FIDO Metadata Service (MDS) integration — trust
decisions are based purely on the configured leaf-signing roots. For AAGUID
allow-listing, use :ref:`policy_webauthn_enroll_authenticator_selection_list`
separately.

In contrast to the :ref:`passkey` token, the WebAuthn token type is the right
choice when attestation data must drive enrollment decisions: the
:ref:`policy_webauthn_enroll_req` policy filters acceptable authenticators
based on the attestation certificate's subject, issuer or serial fields, and
:ref:`policy_webauthn_enroll_authenticator_selection_list` restricts
enrollment to a list of known AAGUIDs. The corresponding ``..._authz_...``
policies enforce the same conditions at authentication time. None of these
filters are available for passkey tokens.

.. note:: Requesting attestation (``direct`` or ``indirect``) typically
    causes the browser to display an additional consent dialog to the user
    during enrollment, informing them that information identifying their
    authenticator will be sent to the server. With ``none``, the AAGUID is
    zeroed and no attestation statement is conveyed, which is more
    privacy-preserving but disables all attestation-based filtering.

.. _webauthn_passkey_interop:

Using existing WebAuthn tokens as passkeys
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Older versions of privacyIDEA expected the WebAuthn challenge in the
``clientDataJSON`` returned by the authenticator to be hex-encoded. This
deviates from the WebAuthn specification, which mandates base64url. Challenges
generated by :http:post:`/validate/initialize` — the endpoint used for the
usernameless passkey flow — are base64url-encoded as the spec requires.

A common real-world situation is that a platform passkey (for example a Touch
ID credential on macOS, or a synced platform credential on Windows or Android)
was enrolled into privacyIDEA as a WebAuthn token before the passkey token type
existed. Such a credential *is* a discoverable passkey at the authenticator
level, so the browser will offer it during a usernameless challenge. To keep
those credentials usable in the passkey flow, the WebAuthn token's
authentication verifier accepts both the legacy hex encoding and the
spec-compliant base64url encoding of the challenge in ``clientDataJSON``.

This dual-encoding tolerance applies only to authentication:

* When the credential is used through the **usernameless passkey path**
  (challenge from :http:post:`/validate/initialize`), the response will be
  base64url-encoded and the WebAuthn verifier accepts it.
* When the credential is used through the **classical, bound challenge-response
  path** (a challenge created by a /validate/check or
  /validate/triggerchallenge against a specific token/user, including the
  passkey-as-WebAuthn case enabled by
  :ref:`policy_passkey_trigger_by_pin`), the legacy hex encoding is used. If a
  user has both a WebAuthn token and a passkey token triggered in the same
  transaction, clients should prefer the passkey token to avoid encoding
  ambiguity.

Newly enrolled passkey tokens use base64url-encoded challenges throughout. The
hex/base64url tolerance in the WebAuthn token verifier is a backwards
compatibility layer; correcting the encoding everywhere would require a
coordinated upgrade of the privacyIDEA server and *every* client application
in use at a given site, since clients currently carry matching encode/decode
logic for both shapes. For this reason the legacy encoding is preserved on the
WebAuthn token and is not planned to change. New deployments should use the
:ref:`passkey` token type, which uses base64url end-to-end.

.. note:: An "open" challenge issued by :http:post:`/validate/initialize` is
    not bound to a specific user or token at creation time; it is resolved to
    a token only when the authenticator response comes back and the credential
    id can be matched against an enrolled token. Classical challenges, by
    contrast, are bound to a token and user from the moment they are created
    (the user proves possession of the token via its PIN to trigger the
    challenge).
