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


.. _autoassignment:

autoassignment
~~~~~~~~~~~~~~

.. index:: autoassignment

type: bool

Users can assign a token just by using this token. The user can take
a token from a pool of unassigned tokens. When this policy is set,
and the user has no token assigned, autoassignment will be done:
The user authenticates with a new PIN and an OTP value from the token.
If the OTP value is correct the token gets assigned to the user and the given
PIN is set as the OTP PIN.

.. note:: Requirements are:

  1. The user must have no other tokens assign.
  2. The token must be not assigned to any user.
  3. The token must be located in the realm of the authenticating user.

.. warning:: In this case assigning the token is only a
one-factor-authentication: the possession of the token.



otp_pin_random
~~~~~~~~~~~~~~

type: int

Generates a random OTP PIN of the given length during enrollment. Thus the user
is forced to set a certain OTP PIN.

.. note:: At the moment this randomly generated PIN is not used.
   It could be used to be sent via a PIN letter in the future.

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

