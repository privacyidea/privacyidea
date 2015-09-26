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

max_token_per_user
~~~~~~~~~~~~~~~~~~

type: int

Limit the maximum number of tokens per user in this realm.

.. note:: If you do not set this action, a user may have
   unlimited tokens assigned.


tokenlabel
~~~~~~~~~~

type: string

This sets the label for a newly enrolled Google Authenticator.
Possible tags to be replaces are <u> for user, <r> for realm an
<s> for the serial number.

The default behaviour is to use the serial number.

.. note:: This is useful to identify the token in the Authenticator App.

.. warning:: If you are only using <u> as tokenlabel and you enroll the token
   without a user, this will result in an invalid QR code, since it will have
   an empty label. You should rather use a label like "user: <u>", which would
   result in "user: ".


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

**Example:**

The action *lostTokenPWLen=10, lostTokenPWContents=Cns* could generate a
password like *AC#!49MK))*.

lostTokenValid
~~~~~~~~~~~~~~

type: int

This is how many days the replacement token for the lost token should 
be valid. After this many days the replacement can not be used anymore.

