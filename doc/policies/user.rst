.. _user_policies:

User Policies
-------------

.. index:: selfservice policies, user policies

In the Web UI users can manage their own tokens.
User can login to the Web UI with the username of their
useridresolver. I.e. if a user is found in an LDAP resolver pointing
to Active Directory the user needs to login with his domain
password.

User policies are used to define, which actions users are
allowed to perform.

.. index:: client policies

The user policies also respect the ``client`` input, where you
can enter a list of IP addresses and subnets (like 10.2.0.0/16).

Using the ``client`` parameter you can allow different actions in
if the user either logs in from the internal network
or remotely from the internet via the firewall.

Technically user policies control the use of the REST API
:ref:`rest_token` and are checked using :ref:`code_policy` and
:ref:`policy_decorators`.

.. note:: If no user policy is defined, the user has
   all actions available to him, to manage his tokens.

The following actions are available in the scope
*user*:

enroll
~~~~~~

type: bool

There are ``enroll`` actions per token type. Thus you can 
create policies that allow the user to enroll
SMS tokens but not to enroll HMAC tokens.

assgin
~~~~~~

type: bool

The user is allowed to assgin an existing token, that is
located in his realm and that does not belong to any other user,
by entering the serial number.

disable
~~~~~~~

type: bool

The user is allowed to disable his own tokens.
Disabled tokens can not be used to authenticate.

enable
~~~~~~

type: bool

The user is allowed to enable his own tokens.

delete
~~~~~~

type: bool

The user is allowed to delete his own tokens from the database.
Those tokens can not be recovered. Anyway, the audit log concerning
these tokens remains.

unassign
~~~~~~~~

type: bool

The user is allowed to drop his ownership of the token.
The token does not belong to any user anymore and can be
reassigned.

resync
~~~~~~

type: bool

The user is allowed to resynchronize the token if it has got out 
of synchronization.

reset
~~~~~

type: bool

The user is allowed to reset the failcounter of the token.

setOTPPIN
~~~~~~~~~

type: bool 

The user ist allowed to set the OTP PIN for his tokens.

setMOTPPIN
~~~~~~~~~~

type: bool 

The user is allowed to set the mOTP PIN of mOTP tokens.


otp_pin_maxlength
~~~~~~~~~~~~~~~~~

type: integer

range: 0 - 31

This is the maximum allowed PIN length the user is allowed to
use when setting the OTP PIN.

otp_pin_minlength
~~~~~~~~~~~~~~~~~

type: integer

range: 0 - 31

This is the minimum required PIN the user must use when setting the
OTP PIN.

otp_pin_contents
~~~~~~~~~~~~~~~~

type: string

contents: cns

This defines what characters an OTP PIN should contain when the user
sets it.

**c** are letters matching [a-zA-Z].

**n** are digits matching [0-9].

**s** are special characters matching [.:,;-_<>+*!/()=?$§%&#~\^].

**Example:** The policy action ``otp_pin_contents=cn, otp_pin_minlength=8`` would
require the user to choose OTP PINs that consist of letters and digits
which have a minimum length of 8.

``cn``

   *test1234* and *test12$$* would be valid OTP PINs. *testABCD* would 
   not be a valid OTP PIN.

The logic of the ``otp_pin_contents`` can be enhanced and reversed using the
characters ``+`` and ``-``.

``-cn`` would still mean, that the OTP PIN needs to contain letters and digits
and it must not contain any other characters.

``-cn`` (substraction)

   *test1234* would be a valid OTP PIN, but *test12$$* and *testABCS* would
   not be valid OTP PINs. The later since it does not contain digits, the first 
   (*test12$$*) since it does contain a special character ($), which it should not.

``+cn`` (grouping)

   combines the two required groups. I.e. the OTP PIN should contain
   characters from the sum of the two groups.
   *test1234*, *test12$$*, *test*
   and *1234* would all be valid OTP PINs.

(**TODO**) grouping and substraction are not implemented, yet.

.. note:: You can change these character definitions in the privacyidea.ini
   file using ``privacyideaPolicy.pin_c``, ``privacyideaPolicy.pin_n``
   and ``privacyideaPolicy.pin_s``.
   (**Not migrated, yet**)


auditlog
~~~~~~~~
type: bool

This action allows the user to view and search the audit log
for actions with his own tokens.

updateuser
~~~~~~~~~~

.. index:: Edit User

type: bool

If the ``updateuser`` action is defined, the user is allowed to change his
attributes in the user store.

.. note:: To be able to edit the attributes, the resolver must be defined as
   editable.


revoke
~~~~~~

type: bool

Tokens can be revoked. Usually this means the token is disabled and locked.
A locked token can not be modified anymore. It can only be deleted.

Certain token types like *certificate* may define special actions when
revoking a token.


password_reset
~~~~~~~~~~~~~~

.. index:: reset password, password reset

type: bool

Introduced in version 2.10.

If the user is located in an editable user store, this policy can define, if
the user is allowed to perform a password reset. During the password reset an
email with a link to reset the password is sent to the user.
