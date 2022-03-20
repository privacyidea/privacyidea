.. _webauthn_otp_token:

WebAuthn Token Config
.....................

.. index:: WebAuthn Token

Trust Anchor Directory
~~~~~~~~~~~~~~~~~~~~~~

You may define a directory containing trust roots for attestation certificates.

This should be a path to a local directory on the server which privacyIDEA has
read access to. Any certificate in this
directory will be trusted to correctly attest authenticators during enrollment.

This does not need to be set for WebAuthn to work, however without this,
privacyIDEA can not check, whether an attestation certificate is actually
trusted (it will still be checked for validity). Therefore it is mandatory to
set this, if :ref:`policy_webauthn_enroll_authenticator_attestation_level` is
set to “trusted” through policy for any user.

WebAuthn Required Policies
..........................

For WebAuthn to work, a name and ID for the relying party need to be set. The
relying party in WebAuthn represents the entity the user is registering with.
In most cases this will be your company. In larger companies it is often helpful
to segment according to department by setting up multiple ID and name policies for
WebAuthn which apply to different users.

Relying Party ID
~~~~~~~~~~~~~~~~

The ID of the relying party must be a fully-qualified domain name. Every web-service,
where the WebAuthn token should be used needs to be reachable under a domain name
which is a superset (i.e. a subdomain) of this ID.
This means that a WebAuthn token enrolled with a relying party ID of `example.com`
may be used to sign in to `privacyidea.example.com` and `owncloud.example.com`.
However, this token will not be able to sign in to a service under `example.de`, or any
other webservice that is not hosted on a subdomain of `example.com`.

See also: :ref:`policy_webauthn_enroll_relying_party_id`.

Relying Party Name
~~~~~~~~~~~~~~~~~~

This is a human-readable name to go along with the relying party ID. It will
usually be either the name of your company (if there is just one relying
party for the entire company), or the name of the department or other
organizational unit the relying party represents.

See also: :ref:`policy_webauthn_enroll_relying_party_name`.
