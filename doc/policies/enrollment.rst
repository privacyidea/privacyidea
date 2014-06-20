.. _enrollment_policies:

Enrollment policies
-------------------

.. index:: enrollment policies

The scope *enrollment* defines what happens during enrollment
either by an administrator or during the user self enrollment.

Enrollment policies take the realms, the client (see :ref:`policies`)
and the user
settings into account.

Technically enrollment policies control the use of the *init* and *assign*-methods
in the :ref:`admin_controller` and `selfservice_controller`.
Several functions are used from the :ref:`code_policy_class`.

The following actions are available in the scope 
*enrollment*:

tokencount
~~~~~~~~~~

type: int

This is the maximum allowed number of tokens in the specified realm.

.. note:: If you have several realms with realm admins and you
   imported a pool of hardware tokens you can thus limit the
   consumed hardware tokens per realm.

maxtoken
~~~~~~~~

type: int

Limit the maximum number of tokens per user in this realm.

.. note:: If you do not set this action, a user may have
   unlimited tokens assigned.

otp_pin_random
~~~~~~~~~~~~~~

type: int

Generates a random OTP PIN during self enrollment. Thus the user is forced
to set a certain OTP PIN.

.. note:: At the moment this randomly generated PIN is not used.
   It could be used to be sent via a PIN letter in the future.

otp_pin_encrypt
~~~~~~~~~~~~~~~

type: int

values: 0 or 1

If set to *1* the OTP PIN of a token will be encrypted. The default
behaviour is to hash the OTP PIN, which is safer.

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

type: int

value: 6 or 8

Users can assign a token just by using this token. The user can take
a token from a pool of unassigned tokens. When this policy is set,
and the user has no token assigned, autoassignment will be done:
The user authenticates with his user store (e.g. LDAP) password
together with the OTP value of the not-assigned-token.
The system will check the password and try to identify the token and
check the OTP value. Therefor the action needs to contain the length
of the OTP value (either 6 or 8).
If it succeeds the token gets assigned to the user, the OTP PIN is set
and the user is successfully authenticated.

ignore_autoassignment_pin
~~~~~~~~~~~~~~~~~~~~~~~~~

type: bool

If this action is set, the assigned token does not get a PIN
during autoassignment.

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

