.. _webauthn_otp_token:

WebAuthn Token Config
.....................

.. index:: WebAuthn Token

Trust Anchor Directory
~~~~~~~~~~~~~~~~~~~~~~

You may define a directory containing trust roots for attestation certificates.

This should be a path to a local directory on the server to which privacyIDEA has
read access. An attestation is trusted during enrollment if its certificate chain
leads to a root certificate in this directory (see below).

This does not need to be set for WebAuthn to work, however without this,
privacyIDEA cannot check whether an attestation certificate is actually
trusted. Therefore, it is mandatory to set this if
:ref:`policy_webauthn_enroll_authenticator_attestation_level` is set to
“trusted” through policy for any user.

The directory is only read at the attestation level “trusted”. At the other
levels the attestation signature is verified with the key of the certificate,
but for packed, FIDO U2F and TPM attestations the issuer and the validity period
of the certificate are not checked (Apple, Android key and SafetyNet
attestations are always checked against the library's built-in roots, see
below).

What this verifies (and what it does not):

* Certificates must be **PEM-encoded** files. Files that cannot be parsed as
  X.509 certificates are logged and skipped, so a directory with a
  mix of valid and invalid files will still work but trust will be reduced
  accordingly.
* The attestation certificate chain is verified up to a self-signed root
  certificate in this directory, including the validity periods. Put the root
  certificate here, plus every intermediate certificate that the authenticator
  does not send in its attestation statement. A directory that holds only the
  intermediate certificate that signs the attestation does not work. Each file
  is read as one certificate: put one certificate per file, in a PEM bundle only
  the first certificate counts.
* Besides the certificates in this directory, the WebAuthn library trusts its
  built-in root certificates for three attestation formats: Apple (``apple``),
  Google hardware attestation (``android-key``) and GlobalSign
  (``android-safetynet``). With the attestation level “trusted”, authenticators
  using these formats are accepted even if none of these roots is in the
  directory. To restrict enrollment to specific authenticator models, use
  :ref:`policy_webauthn_enroll_authenticator_selection_list` or
  :ref:`policy_webauthn_enroll_req`.
* There is **no FIDO Metadata Service (MDS) integration** and no AAGUID-based
  trust evaluation. AAGUID allow-listing is a separate mechanism configured
  via :ref:`policy_webauthn_enroll_authenticator_selection_list`.
* This setting is only consulted by the :ref:`webauthn` token type. The
  :ref:`passkey` token type does not check attestations against this
  directory; for the three formats above the library still checks them
  against its built-in roots.

WebAuthn Required Policies
~~~~~~~~~~~~~~~~~~~~~~~~~~

For WebAuthn to work, a name and ID for the relying party need to be set. The
relying party in WebAuthn represents the entity the user is registering with.
In most cases this will be your company. In larger companies it is often helpful
to segment according to department by setting up multiple ID and name policies for
WebAuthn that apply to different users.

Relying Party ID
""""""""""""""""

The ID of the relying party must be a fully-qualified domain name. Every web service
where the WebAuthn token should be used needs to be reachable under a domain name
which is a superset (i.e. a subdomain) of this ID.
This means that a WebAuthn token enrolled with a relying party ID of ``example.com``
may be used to sign in to ``privacyidea.example.com`` and ``owncloud.example.com``.
However, this token will not be able to sign in to a service under ``example.de``, or any
other webservice that is not hosted on a subdomain of ``example.com``.

See also: :ref:`policy_webauthn_enroll_relying_party_id`.

Relying Party Name
""""""""""""""""""

This is a human-readable name to go along with the relying party ID. It will
usually be either the name of your company (if there is just one relying
party for the entire company) or the name of the department or other
organizational unit the relying party represents.

See also: :ref:`policy_webauthn_enroll_relying_party_name`.

Challenge Validity Time
~~~~~~~~~~~~~~~~~~~~~~~

The validity time of a FIDO2 challenge — for both WebAuthn and passkey
enrollment and authentication — is governed by the system-wide
:ref:`challenge_validity_time` setting. To override this just for FIDO2
challenges, for example to give users more time to interact with their
authenticator without lengthening the validity time of every other challenge
type, set the config key ``WebauthnChallengeValidityTime`` (in seconds). The
lookup order is ``WebauthnChallengeValidityTime`` →
``DefaultChallengeValidityTime`` → ``120`` seconds.

If you raise :ref:`policy_webauthn_enroll_timeout` or
:ref:`policy_webauthn_authn_timeout` beyond the challenge validity time, the
client-side wait is meaningless: the server will already have discarded the
challenge by the time the response arrives. Keep the challenge validity time
at or above the largest WebAuthn/passkey client timeout in use.
