.. _enrollment_policies:

Enrollment policies
-------------------

.. index:: enrollment policies

The scope *enrollment* defines what happens during enrollment
either by an administrator or during the user self enrollment.

Enrollment policies take the realms, the client (see :ref:`policies`)
and the user settings into account.

Technically enrollment policies control the use of the
REST API :ref:`rest_token` and specially the *init* and *assign*-methods.

Technically the decorators in :ref:`code_api_policy` are used.

The following actions are available in the scope 
*enrollment*:

max_token_per_realm
~~~~~~~~~~~~~~~~~~~

type: int

This is the maximum allowed number of tokens in the specified realm.

.. note:: If you have several realms with realm admins and you
   imported a pool of hardware tokens you can thus limit the
   consumed hardware tokens per realm.

.. note:: If there are multiple matching policies, the *highest* maximum
   allowed number of tokens among the matching policies is enforced.
   Policy priorities are ignored.

max_token_per_user
~~~~~~~~~~~~~~~~~~

type: int

Limit the maximum number of tokens per user in this realm.

There are also token type specific policies to limit the
number of tokens of a specific token type, that a user is
allowed to have assigned.

.. note:: If you do not set this action, a user may have
   unlimited tokens assigned.

.. note:: If there are multiple matching policies, the *highest* maximum
   allowed number of tokens among the matching policies is enforced.
   Policy priorities are ignored.

max_active_token_per_user
~~~~~~~~~~~~~~~~~~~~~~~~~

type: int

Limit the maximum number of active tokens per user.

There are also token type specific policies to limit the
number of tokens of a specific token type, that a user is
allowed to have assigned.

.. note:: Inactive tokens will not be taken into account.
   If the token already exists, it can be recreated if the token
   is already active.

tokenissuer
~~~~~~~~~~~

type: string

This sets the issuer label for a newly enrolled Google Authenticator.
This policy takes a fixed string, to add additional information about the
issuer of the soft token.

Starting with version 2.20 you can use the tags ``{user}``, ``{realm}``, ``{serial}``
and as new tags ``{givenname}`` and ``{surname}`` in the field issuer.

.. note:: A good idea is to set this to the instance name of your privacyIDEA
   installation or the name of your company.

tokenlabel
~~~~~~~~~~

type: string

This sets the label for a newly enrolled Google Authenticator.
Possible tags to be replaces are <u> for user, <r> for realm an
<s> for the serial number.

The default behaviour is to use the serial number.

.. note:: This is useful to identify the token in the Authenticator App.

.. note:: Starting with version 2.19 the usage of ``<u>``, ``<s>`` and ``<r>``
   is deprecated. Instead you should use ``{user}``, ``{realm}``,
   ``{serial}`` and as new tags ``{givenname}`` and ``{surname}``.

.. warning:: If you are only using ``<u>`` or ``{user}`` as tokenlabel and you
   enroll the token without a user, this will result in an invalid QR code,
   since it will have an empty label.
   You should rather use a label like "{user}@{realm}",
   which would result in "@".


.. _autoassignment:

autoassignment
~~~~~~~~~~~~~~

.. index:: autoassignment

type: string

allowed values: any_pin, userstore

Users can assign a token just by using this token. The user can take
a token from a pool of unassigned tokens. When this policy is set,
and the user has no token assigned, autoassignment will be done:
The user authenticates with a new PIN or his userstore password and an OTP
value from the token.
If the OTP value is correct the token gets assigned to the user and the given
PIN is set as the OTP PIN.

.. note:: Requirements are:

  1. The user must have no other tokens assigned.
  2. The token must be not assigned to any user.
  3. The token must be located in the realm of the authenticating user.
  4. (The user needs to enter the correct userstore password)

.. warning:: If you set the policy to *any_pin* the token will be assigned to
   the user no matter what pin he enters.
   In this case assigning the token is only a
   one-factor-authentication: the possession of the token.



otp_pin_random
~~~~~~~~~~~~~~

type: int

Generates a random OTP PIN of the given length during enrollment. Thus the user
is forced to set a certain OTP PIN.

.. note:: To use the random PIN, you also need to define a
   :ref:`policy_pinhandling` policy.

.. _policy_pinhandling:

pinhandling
~~~~~~~~~~~
.. index:: PinHandler

type: string

If the ``otp_pin_random`` policy is defined, you can use this policy to
define, what should happen with the random pin.
The action value take the class of a PinHandler like
``privacyidea.lib.pinhandling.base.PinHandler``.
The base PinHandler just logs the PIN to the log file. You can add classes to
send the PIN via EMail or print it in a letter.

For more information see the base class :ref:`code_pinhandler`.

.. _policy_change_pin_first_use:

change_pin_on_first_use
~~~~~~~~~~~~~~~~~~~~~~~
.. index:: PIN policies, Change PIN

type: bool

If the administrator enrolls a token or resets a PIN of a token, then the PIN
of this token is marked to be changed on the first (or next) use.
When the user authenticates with the old PIN, the user is authenticated
successfully. But the detail-response contains the keys "next_pin_change" and
"pin_change". If "pin_change" is *True* the authenticating application must
trigger the change of the PIN using the API */token/setpin*. See
:ref:`rest_token`.

.. note:: If the application does not honour the "pin_change" attribute, then
   the user can still authenticate with his old PIN.

.. note:: Starting with version 3.4 privacyIDEA also allows to force the user to change
   the PIN in such a case using the policy :ref:`policy_change_pin_via_validate`.

.. _policy_change_pin_every:

change_pin_every
~~~~~~~~~~~~~~~~
.. index:: PIN policies, Change PIN

type: string

This policy requires the user to change the PIN of his token on a regular
basis. Enter a value follewed by "d", e.g. change the PIN every 180 days will
be "180d".

The date, when the PIN needs to be changed, is returned in the API response
of */validate/check*. For more information see :ref:`change_pin_first_use`.
To specify the contents of the PIN see :ref:`user_policies`.

otp_pin_encrypt
~~~~~~~~~~~~~~~

type: bool

If set the OTP PIN of a token will be encrypted. The default
behaviour is to hash the OTP PIN, which is safer.


lostTokenPWLen
~~~~~~~~~~~~~~

.. index:: lost token

type: int

This is the length of the generated password for the lost token process.
 
lostTokenPWContents
~~~~~~~~~~~~~~~~~~~

type: string

This is the contents that a generated password for the lost token process
should have. You can use

 * c: for lowercase letters
 * n: for digits
 * s: for special characters (!#$%&()*+,-./:;<=>?@[]^_)
 * C: for uppercase letters
 * 8: Base58 character set

**Example:**

The action *lostTokenPWLen=10, lostTokenPWContents=Cns* could generate a
password like *AC#!49MK))*.

.. note:: If you combine ``8`` with e.g. ``C`` there will be double characters
   like "A", "B"... Thus, those characters will have a higher probability of being
   part of the password. Also ``C`` would again add the character "I", which is
   not part of Base58.

lostTokenValid
~~~~~~~~~~~~~~

type: int

This is how many days the replacement token for the lost token should 
be valid. After this many days the replacement can not be used anymore.

yubikey_access_code
~~~~~~~~~~~~~~~~~~~

type: string

This is a 12 character long access code in hex format to be used to initialize yubikeys. If
no access code is set, yubikeys can be re-initialized by everybody. You can choose
a company wide access code, so that Yubikeys can only be re-initialized by your own system.

You can add two access codes separated by a colon to change from one access code to the other.

   313233343536:414243444546


papertoken_count
~~~~~~~~~~~~~~~~

type: int

This is a specific action of the paper token. Here the administrator can
define how many OTP values should be printed on the paper token.

tantoken_count
~~~~~~~~~~~~~~

type: int

This is a specific action for the TAN token. The administrator can define
how many TANs will be generated and printed.


u2f_req
~~~~~~~

type: string

Only the specified U2F devices are allowed to be registered.
The action can be specified like this:

    u2f_req=subject/.*Yubico.*/

The the key word can be "subject", "issuer" or "serial". Followed by a
regular expression. During registration of the U2F device the information
is fetched from the attestation certificate.
Only if the attribute in the attestation certificate matches accordingly the
token can be registered.

.. _policy_u2f_no_verify_certificate:

u2f_no_verify_certificate
~~~~~~~~~~~~~~~~~~~~~~~~~

type: bool

By default the validity period of the attestation certificate of a U2F device gets
verified during the registration process.
If you do not want to verify the validity period, you can check this action.


.. _2step_parameters:

{type}_2step_clientsize, {type}_2step_serversize, {type}_2step_difficulty
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: string

These are token type specific parameters. They control the key generation during the
2step token enrollment (see :ref:`2step_enrollment`).

The ``serversize`` is the optional size (in bytes) of the server's key part.
The ``clientsize`` is the size (in bytes) of the smartphone's key part.
The ``difficulty`` is a parameter for the key generation.
In the implementation in version 2.21 PBKDF2 is used. In this case the ``difficulty``
specifies the number of rounds.

This is new in version 2.21.

.. _force_app_pin:

.. hotp_force_app_pin, totp_force_app_pin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: bool

During enrollment of a privacyIDEA Authenticator smartphone app this policy is used
to force the user to protect the token with a PIN.

.. note:: This only works with the privacyIDEA Authenticator.
   This policy has no effect, if the QR code is scanned with other smartphone apps.

This is new in version 3.1.


.. _policy_firebase_config:

push_firebase_configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: string

For enrolling a :ref:`push_token`, the administrator can select which
Firebase configuration should be used.
The administrator can create several connections to the Firebase service
(see :ref:`firebase_provider`).
This way even different Firebase configurations could be
used depending on the user's realm or the IP address.

This is new in version 3.0.

.. _policy_webauthn_enroll_relying_party_id:

webauthn_relying_party_id
~~~~~~~~~~~~~~~~~~~~~~~~~

type: string

This action sets the relying party id to use for the enrollment of new WebAuthn
tokens, at defined by the WebAuthn specification [#rpid]_. Please note, that a
token will be rolled out with one particular ID and that the relying party of an
existing token can not be changed. In order to change the relying party id for
existing tokens, they need to be deleted and new tokens need to be enrolled.
This is a limitation of the WebAuthn standard and is unlikely to change in the
future.

The relying party id is a valid domain string that identifies the WebAuthn
Relying Party on whose behalf a given registration or authentication
ceremony is being performed. A public key credential can only be used for
authentication with the same entity (as identified by RP ID) it was registered
with.

This id needs to be a registrable suffix of or equal to the effective domain
for each webservice the tokens should be used with. This means if the token is
being enrolled on – for example – `https://login.example.com`, them the relying
party ID may be either `login.example.com`, or `example.com`, but not – for
instance – `m.login.example.com`, or `com`. Similarly, a token enrolled with a
relying party ID of `login.example.com` might be used by
`https://login.example.com`, or even `https://m.login.example.com:1337`, but not
by `https://example.com` (because the RP ID `login.example.com` is not a valid
relying party ID for the domain `example.com`).

.. note:: This action needs to be set to be able to enroll WebAuthn tokens. For
    an overview of all the settings required for the use of WebAuthn, see
    :ref:`webauthn_otp_token`.

.. _policy_webauthn_enroll_relying_party_name:

webauthn_relying_party_name
~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: string

This action sets the human-readable name for the relying party, as defined by
the WebAuthn specification [#webauthnrelyingparty]_. It should be the name of
the entity whose web applications the WebAuthn tokens are used for.

.. note:: This action needs to be set to be able to enroll WebAuthn tokens. For
    an overview of all the settings required for the use of WebAuthn, see
    :ref:`webauthn_otp_token`.

.. _policy_webauthn_enroll_timeout:

webauthn_timeout
~~~~~~~~~~~~~~~~

type: integer

This action sets the time in seconds the user has to confirm enrollment on his
WebAuthn authenticator.

This is a client-side setting, that governs how long the client waits for the
authenticator. It is independent of the time for which a challenge for a
challenge response token is valid, which is governed by the server and
controlled by a separate setting. This means, that if you want to increase this
timeout beyond two minutes, you will have to also increase the challenge
validity time, as documented in :ref:`challenge_validity_time`.

This setting is a hint. It is interpreted by the client and may be adjusted by
an arbitrary amount in either direction, or even ignored entirely.

The default timeout is 60 seconds.

.. note:: If you set this policy you may also want to set
    :ref:`policy_webauthn_authn_timeout`.

.. _policy_webauthn_enroll_authenticator_attachment:

webauthn_authenticator_attachment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: string

This action configures whether to limit roll out of WebAuthn tokens to either
only platform authenticators, or only platform authenticators. Cross-platform
authenticators are authenticators, that are intended to be plugged into
different devices, whereas platform authenticators are those, that are built
directly into one particular device and can not (easily) be removed and plugged
into a different device.

The default is to allow both `platform` and `cross-platform` attachment for
authenticators.

.. _policy_webauthn_enroll_authenticator_selection_list:

webauthn_authenticator_selection_list
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: string

This action configures a whitelist of authenticator models which may be
enrolled. It is a space-separated list of AAGUIDs. An AAGUID is a
hexadecimal string (usually grouped using dashes, although these are
optional) identifying one particular model of authenticator. To limit
enrollment to a few known-good authenticator models, simply specify the AAGUIDs
for each model of authenticator that is acceptable. If multiple policies with
this action apply, the set of acceptable authenticators will be the union off
all authenticators allowed by the various policies.

If this action is not configured, all authenticators will be deemed acceptable,
unless limited through some other action.

.. note:: If you configure this, you will likely also want to configure
    :ref:`policy_webauthn_authz_authenticator_selection_list`.

.. _policy_webauthn_enroll_user_verification_requirement:

webauthn_user_verification_requirement
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: string

This action configures whether the user's identity should be checked when
rolling out a new WebAuthn token. If this is set to required, any user rolling
out a new WebAuthn token will have to provide some form of verification. This
might be biometric identification, or knowledge-based, depending on the
authenticator used.

This defaults to `preferred`, meaning user verification will be performed if
supported by the token.

.. note:: User verification is different from user presence checking. The
    presence of a user will always be confirmed (by asking the user to take
    action on the token, which is usually done by tapping a button on the
    authenticator). User verification goes beyond this by ascertaining, that the
    user is indeed the same user each time (for example through biometric
    means), only set this to `required`, if you know for a fact, that you have
    authenticators, that actually support some form of user verification (these
    are still quite rare in practice).

.. note:: If you configure this, you will likely also want to configure
    :ref:`policy_webauthn_authn_user_verification_requirement`.

.. _policy_webauthn_enroll_public_key_credential_algorithm_preference:

webauthn_public_key_credential_algorithm_preference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: string

This action configures which algorithms should be preferred for the creation
of WebAuthn asymmetric cryptography key pairs, and in which order. privacyIDEA
currently supports ECDSA as well as RSASSA-PSS. Please check back with the
manufacturer of your authenticators to get information on which algorithms are
acceptable to your model of authenticator.

The default is to allow both ECDSA and RSASSA-PSS, but to prefer ECDSA over
RSASSA-PSS.

.. note:: Not all authenticators will supports all algorithms. It should not
    usually be necessary to configure this action. Do *not* change this
    preference, unless you are sure you know what you are doing!

.. _policy_webauthn_enroll_authenticator_attestation_form:

webauthn_authenticator_attestation_form
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: string

This action configures whether to request attestation data when enrolling a new
WebAuthn token. Attestation is used to verify, that the authenticator being
enrolled has been made by a trusted manufacturer. Since depending on the
authenticator this may include personally identifying information, `indirect`
attestation can be requested. If `indirect` attestation is requested the client
may pseudonymize the attestation data. Attestation can also be turned off
entirely.

The default is to request `direct` (full) attestation from the authenticator.

.. note:: In a normal business-context it will not be necessary to change this.
    If this is set to `none`,
    :ref:`policy_webauthn_enroll_authenticator_attestation_level` must also be none.

.. note:: Authenticators enrolled with this option set to `none` can not be
    filtered using :ref:`policy_webauthn_enroll_req` and
    :ref:`policy_webauthn_enroll_authenticator_selection_list` or
    :ref:`policy_webauthn_authz_req` and
    :ref:`policy_webauthn_authz_authenticator_selection_list`, respectively. Applying
    these filters is not possible without attestation information, since the
    fields these actions rely upon will be missing. With `indirect` attestation,
    checking may be possible (depending on the client). If any of
    :ref:`policy_webauthn_enroll_req`,
    :ref:`policy_webauthn_enroll_authenticator_selection_list`,
    :ref:`policy_webauthn_authz_req`, or
    :ref:`policy_webauthn_authz_authenticator_selection_list` are set and apply
    to a request for a token without attestation information, access will be
    denied.

.. _policy_webauthn_enroll_authenticator_attestation_level:

webauthn_authenticator_attestation_level
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: string

This action determines whether and how strictly to check authenticator
attestation data. Set this to `none`, to allow any authenticator, even if the
attestation information is missing completely. If this is set to `trusted`,
strict checking is performed. No authenticator is allowed, unless it contains
attestation information signed by a certificate trusted for attestation.

.. note:: Currently the certificate that signed the attestation needs to be
    trusted directly. Traversal of the trust path is not yet supported!

The default is `untrusted`. This will perform the attestation check like normal,
but will not fail the attestation, if the attestation is self-signed, or signed
by an unknown certificate.

.. note:: In order to be able to use `trusted` attestation, a directory needs
    to be provided, containing the certificates trusted for attestation. See
    :ref:`webauthn_otp_token` for details.

.. note:: If this is set to `untrusted`, a manipulated token could send a
    self-signed attestation message with modified a modified AAGUID and faked
    certificate fields in order to bypass :ref:`policy_webauthn_enroll_req` and
    :ref:`policy_webauthn_enroll_authenticator_selection_list`, or
    :ref:`policy_webauthn_authz_req` and
    :ref:`policy_webauthn_authz_authenticator_selection_list`, respectively. If
    this is of concern for your attack scenarios, please make sure to properly
    configure your attestation roots!

.. _policy_webauthn_enroll_req:

webauthn_req
~~~~~~~~~~~~

type: string

This action allows filtering of WebAuthn tokens by the fields of the
attestation certificate.

The action can be specified like this:

    webauthn_req=subject/.*Yubico.*/

The the key word can be "subject", "issuer" or "serial". Followed by a
regular expression. During registration of the WebAuthn authenticator the
information is fetched from the attestation certificate. Only if the attribute
in the attestation certificate matches accordingly the token can be enrolled.

.. note:: If you configure this, you will likely also want to configure
    :ref:`policy_webauthn_authz_req`.

.. rubric:: Footnotes

.. [#rpid] https://w3.org/TR/webauthn-2/#rp-id
.. [#webauthnrelyingparty] https://w3.org/TR/webauthn-2/#webauthn-relying-party
