.. _webauthn:

WebAuthn
--------

.. index:: WebAuthn, FIDO2

.. note:: For new deployments the :ref:`passkey` token type is recommended over
    WebAuthn. The passkey token is a re-implementation on top of a maintained
    FIDO2 library and was created specifically to address shortcomings of the
    older WebAuthn implementation. The WebAuthn token type is kept primarily
    for existing deployments and for the few cases where attestation-based
    filtering (:ref:`policy_webauthn_enroll_req`,
    :ref:`policy_webauthn_enroll_authenticator_selection_list`,
    :ref:`policy_webauthn_enroll_authenticator_attestation_level` = ``trusted``)
    is required, which the passkey token does not provide.

privacyIDEA supports WebAuthn tokens. The
administrator or the user himself can register a WebAuthn device and use this
WebAuthn token to log in to the privacyIDEA WebUI or to authenticate against
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
:ref:`webauthn_passkey_interop` below (also for tokens enrolled before 3.11). There is no policy that lets you force
or forbid resident-key creation on the WebAuthn token — use the :ref:`passkey` token type if you need a guaranteed
discoverable credential.

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

If you set the attestation form to ``none``, also set the attestation level to
``none``. With the default level ``untrusted``, a registration without an
attestation statement is rejected and the enrollment fails with "Could not
enroll webauthn token!". The same applies to authenticators that return no
attestation statement although ``direct`` or ``indirect`` was requested, as
some platform authenticators do: they can only be enrolled with the level
``none``.

With the default ``direct`` + ``untrusted`` combination, the authenticator
returns a full attestation statement and privacyIDEA records the leaf
certificate's issuer, subject and serial in token info
(``attestation_issuer``, ``attestation_subject``, ``attestation_serial``),
along with the AAGUID. The attestation signature is verified. For the
``packed``, ``fido-u2f`` and ``tpm`` formats a self-signed or unknown-signer
attestation is accepted; ``apple``, ``android-key`` and ``android-safetynet``
attestations are always checked against the vendor roots built into the
WebAuthn library and rejected if they do not chain to them. If the token has no
description yet, its description is set to the leaf certificate's Common Name
if the certificate has one; otherwise it falls back to ``Generic WebAuthn
Token``. A description already set on the token is left unchanged.

Setting the level to ``trusted`` requires configuring a directory of trusted
attestation roots; see :ref:`webauthn_otp_token`. Enrollment is then rejected
unless the attestation certificate chain - the leaf certificate plus the
intermediate certificates the authenticator sends in the attestation
statement - leads to a self-signed root certificate in that directory. Put the
vendors' root CA certificates there; a directory that only holds the intermediate
certificate that signs the attestation refuses every enrollment. For the
``apple``, ``android-key`` and ``android-safetynet`` attestation formats, the
root certificates built into the WebAuthn library (Apple, Google hardware
attestation, GlobalSign) are trusted in addition to the configured ones. There
is no FIDO Metadata Service (MDS) integration. For AAGUID allow-listing, use
:ref:`policy_webauthn_enroll_authenticator_selection_list` separately.

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
    authenticator will be sent to the server. With ``none`` (this requires
    the attestation level ``none``), the AAGUID is zeroed and no attestation
    statement is conveyed, which is more privacy-preserving but disables all
    attestation-based filtering.

.. _webauthn_passkey_interop:

Using existing WebAuthn tokens as passkeys
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

How the client passes the challenge to the authenticator depends on the kind of
challenge, not on the token type:

* A challenge bound to a WebAuthn token (created by ``/validate/check`` with the
  PIN or by ``/validate/triggerchallenge``) is sent as
  ``webAuthnSignRequest.challenge``, the base64url encoding of a random nonce.
  The client decodes it to bytes and passes those to the authenticator, as the
  WebAuthn specification describes, so ``clientDataJSON`` carries the same
  base64url string. This has not changed since earlier versions.
* A passkey challenge - from :http:post:`/validate/initialize`
  (``detail.passkey.challenge``), from :ref:`policy_passkey_trigger_by_pin`, and
  during passkey enrollment - is a base64url string that the client must pass
  to the authenticator as its UTF-8 bytes, without decoding it. A client that
  decodes it to bytes, as for the WebAuthn challenge, fails the verification.

A common real-world situation is that a platform passkey (for example a Touch
ID credential on macOS, or a synced platform credential on Windows or Android)
was enrolled into privacyIDEA as a WebAuthn token before the passkey token type
existed. Such a credential *is* a discoverable passkey at the authenticator
level, so the browser will offer it during a usernameless challenge.

A WebAuthn token enrolled before privacyIDEA 3.11 is only found in the
usernameless flow after it has been used once for a regular authentication
with a user name (a WebAuthn challenge bound to the token, e.g. triggered with
the PIN), which records its credential ID. Until then a usernameless login with
it fails with "No token found for the given credential ID or transaction ID!".

A WebAuthn token whose credential is discoverable can answer a passkey
challenge from :http:post:`/validate/initialize`: the WebAuthn token's verifier
accepts both challenge forms described above and picks the one that matches the
challenge it issued. When a WebAuthn challenge and a passkey challenge are
returned in one transaction (for example with
:ref:`policy_passkey_trigger_by_pin`), they use different nonces in the two
different forms; the client has to handle each challenge in its own form.

New deployments should use the :ref:`passkey` token type.

.. note:: An "open" challenge issued by :http:post:`/validate/initialize` is
    not bound to a specific user or token at creation time; it is resolved to
    a token only when the authenticator response comes back and the credential
    id can be matched against an enrolled token. Classical challenges, by
    contrast, are bound to a token and user from the moment they are created
    (the user proves possession of the token via its PIN to trigger the
    challenge).
