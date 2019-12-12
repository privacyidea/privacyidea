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

.. _change_pin_first_use:

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

change_pin_every
~~~~~~~~~~~~~~~~
.. index:: PIN policies, Change PIN

type: string

This policy requires the user to change the PIN of his token on a regular
basis. Enter a value follewed by "d", e.g. change the PIN every 180 days will
be "180d".

The date, when the PIN needs to be changed, is returned in the API response
of */validate/check*. For more information see :ref:`change_pin_first_use`.
To specifiy the contents of the PIN see :ref:`user_policies`.

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

For enrolling a :ref:`push token`, the administrator can select which
Firebase configuration should be used.
The administrator can create several connections to the Firebase service
(see :ref:`firebase_provider`).
This way even different Firebase configurations could be
used depending on the user's realm or the IP address.

This is new in version 3.0.