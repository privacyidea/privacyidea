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

appimageurl
~~~~~~~~~~~

.. index:: Token Image, FreeOTP

type: string

With this action the administrator may specify the URL to a token image which is included in the
QR code during enrollment (key in otpauth URL: ``image``). It is used by the privacyIDEA Authenticator
and some other smartphone apps like FreeOTP (supported file formats: PNG, JPG and GIF).

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
basis. Enter a value followed by "d", e.g. change the PIN every 180 days will
be "180d".

The date, when the PIN needs to be changed, is returned in the API response
of */validate/check*. For more information see :ref:`policy_change_pin_first_use`.
To specify the contents of the PIN see :ref:`user_policies`.

encrypt_pin
~~~~~~~~~~~

type: bool

If set the OTP PIN of a token will be encrypted. The default
behaviour is to hash the OTP PIN, which is safer.

registration.length
~~~~~~~~~~~~~~~~~~~

.. index:: registration token

type: int

This is the length of the generated registration codes.

registration.contents
~~~~~~~~~~~~~~~~~~~~~

type: string

contents: cns

This defines what characters the registrationcodes should contain.

This takes the same values like the admin policy :ref:`admin_policies_otp_pin_contents`.

pw.length
~~~~~~~~~

.. index:: pw token

type: int

This is the length if the password of a password token (pw token) is automatically generated
with the `genkey` parameter.
The default length is 12.

pw.contents
~~~~~~~~~~~

type: string

contents: cns

This is the contents of an automatically generated password of a password token (pw token).

This takes the same values like the admin policy :ref:`admin_policies_otp_pin_contents`.

losttoken_PW_length
~~~~~~~~~~~~~~~~~~~

.. index:: lost token

type: int

This is the length of the generated password for the lost token process.
 
losttoken_PW_contents
~~~~~~~~~~~~~~~~~~~~~

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

losttoken_valid
~~~~~~~~~~~~~~~

type: int

This is how many days the replacement token for the lost token should 
be valid. After this many days the replacement can not be used anymore.

yubikey_access_code
~~~~~~~~~~~~~~~~~~~

type: string

This is a 12 character long access code in hex format to be used to initialize Yubikeys.
This access code is not actively used by the privacyIDEA server. It is meant to be read by
an admin client or enrollment client, so the component initializing the Yubikey can use this
access code, without the operator knowing the code.

If a yubikey uses an access code, Yubikeys can only be re-initialized by persons who know this code.
You could choose a company wide access code, so that Yubikeys can only be re-initialized by your own system.

You can add two access codes separated by a colon to change from one access code to the other.

   313233343536:414243444546

.. note:: As long as the enrollment client does not read and use this access code, this configuration
   has no effect.

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
.. _hotp-2step-clientsize:
.. _totp-2step-clientsize:
.. _hotp-2step-serversize:
.. _totp-2step-serversize:
.. _hotp-2step-difficulty:
.. _totp-2step-difficulty:

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
.. _hotp-force-app-pin:
.. _totp-force-app-pin:

hotp_force_app_pin, totp_force_app_pin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

Starting with version 3.6, if the push token is supposed to run in poll-only mode,
then the entry "poll only" can be selected instead of a firebase configuration.
In this mode, neither the privacyIDEA server nor the smartphone app will connect to Google
Firebase during enrollment or authentication.
Note, that you also need to set the authentication policy
:ref:`policy_auth_push_allow_poll` to allow the push token to poll for challenges.

push_registration_url
~~~~~~~~~~~~~~~~~~~~~

type: string

This is the URL of your privacyIDEA server, which the push App should
connect to for the second registration step.
This URL usually ends with ``/ttype/push``. Note, that the smartphone app
may connect to a different privacyIDEA URL than the URL of the privacyIDEA Web UI.

push_ttl
~~~~~~~~

This is the time (in minutes) how long the privacyIDEA server
accepts the response of the second registration step.
The smartphone could have connection issues, so the second step
could take some time to happen.

.. _policy_push_ssl_verify_enrollment:

push_ssl_verify
~~~~~~~~~~~~~~~

type: int

The smartphone needs to verify the SSL certificate of the privacyIDEA server during
the enrollment of push tokens. By default, the verification is enabled. To disable
verification during authentication, see :ref:`policy_push_ssl_verify_auth`.

.. _policy_verify_enrollment:


verify_enrollment
~~~~~~~~~~~~~~~~~

type: string

This action takes a white space separated list of tokentypes.
These tokens then need to be verified during enrollment.
This is supported for HOTP, TOTP, Email and SMS tokens.

In this case after enrolling the token the user is prompted to enter
a valid OTP value. This way the system can verify, that the user has
successfully enrolled the token.

As long as no OTP value is provided by the user during the enrollment process, the
token can not be used for authentication.

.. note:: This does not work in combination with the admin policy :ref:`admin_policy_2step` and
  the user policy :ref:`user_policy_2step`.

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

.. _policy_webauthn_enroll_public_key_credential_algorithms:

webauthn_public_key_credential_algorithms
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: string

This action configures which algorithms should be available for the creation
of WebAuthn asymmetric cryptography key pairs. privacyIDEA
currently supports ECDSA, RSASSA-PSS and RSASSA-PKCS1-v1_5. Please check back
with the manufacturer of your authenticators to get information on which
algorithms are acceptable to your model of authenticator.

The default is to allow both ECDSA and RSASSA-PSS.

The Order of preferred algorithms is `ECDSA > RSASSA-PSS > RSASSA-PKCS1-v1_5`

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

The action can be specified like this::

    webauthn_req=subject/.*Yubico.*/

The the key word can be "subject", "issuer" or "serial". Followed by a
regular expression. During registration of the WebAuthn authenticator the
information is fetched from the attestation certificate. Only if the attribute
in the attestation certificate matches accordingly the token can be enrolled.

.. note:: If you configure this, you will likely also want to configure
    :ref:`policy_webauthn_authz_req`.


.. _policy_webauthn_challenge_text_enrollment:

webauthn_challenge_text
~~~~~~~~~~~~~~~~~~~~~~~

type: str

Use an alternate challenge text for requesting the user to confirm with
his WebAuthn token during enrollment. This might be different from the
challenge text received during authentication
(see :ref:`policy_webauthn_challenge_text_auth`).


.. _policy_webauthn_avoid_double_registration:

webauthn_avoid_double_registration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: bool

If this policy is set, a user or an admin can not register the same webauthn
token to a user more than once.
However, the same webauthn token could be registered to a different user.


.. _require_attestation:

certificate_require_attestation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: string

When enrolling a certificate token, privacyIDEA can require that an attestation
certificate is passed along to verify, if the key pair was generated on a (PIV) smartcard.

This policy can be set to:

* ``ignore`` (default): Ignore any existence of an attestation certificate
* ``verify``: If an attestation certificate is passed along during enrollment,
  the attestation certificate gets verified.
* ``require_and_verify``: An attestation certificate is required and verified. If no attestation certificate
  is provided, the enrollment will fail.

The trusted root certificate authorities and intermediate certificate authorities can be configured via
the policies :ref:`admin_trusted_attestation_CA` and :ref:`user_trusted_attestation_CA`


.. _policy_certificate_ca_connector:

certificate_ca_connector
~~~~~~~~~~~~~~~~~~~~~~~~

type: string

During enrollment of a `certificate` token the user needs to specify the CA connector
from which the CSR should be signed.
This policy adds the given CA connector parameter to the request.
The list of CA connectors is read from the configured connectors.

.. note:: When using the privacyIDEA Smartcard Enrollment Tool, this policy needs to be set, otherwise
   the enrollment will fail.


.. _policy_certificate_template:

certificate_template
~~~~~~~~~~~~~~~~~~~~

type: string

During enrollment of a `certificate` token the user needs to specify the certificate template that should be used
for enrollment. This policy adds the given template parameter to the request.
The administrator needs to add the name of the template manually in this policy.

.. note:: When using the privacyIDEA Smartcard Enrollment Tool in combination with a Microsoft CA,
   this policy needs to be set, otherwise the enrollment will fail.


.. _policy_certificate_request_subject_component:

certificate_request_subject_component
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: string

During enrollment of a `certificate` by creating a request, privacyIDEA can add additional
components to the request subject.

This can be "email" (The email of the user read from the userstore) and/or "realm", which
is written to the orgnaizationalUnit (OU) of the request.

.. note:: A couple of certificate templates on the Microsoft CA will not allow to have the
   email component directly in the subject!

.. rubric:: Footnotes

.. [#rpid] https://w3.org/TR/webauthn-2/#rp-id
.. [#webauthnrelyingparty] https://w3.org/TR/webauthn-2/#webauthn-relying-party
