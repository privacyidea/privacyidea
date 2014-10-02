.. _selfservice_policies:

Selfservice policies
--------------------

.. index:: selfservice policies

In the selfservice portal users can manage their own tokens.
User can login to the selfservice portal with the username of their
useridresolver. I.e. if a user is found in an LDAP resolver pointing
to Active Directory the user needs to login with his domain
password.

Selfservice policies are used to define, which actions users are
allowed to perform in the selfservice portal.
Selfservice policies are defined per realm. You can enter the wildcard "*"
as realm or you can enter a comma seperated realm list.

.. index:: client policies

The selfservice policies also respect the ``client`` input, where you
can enter an IP address or a subnet (like 10.2.0.0/16).

Using the ``client`` parameter you can allow different actions in
selfservice if the user either logs in from the internal network
or remotely from the internet via the firewall.

.. note:: The ``user`` in the selfservice policy can contain a list of users and
   also resolvers, which are identified by a ":". The notation
   is *user:resolver*. A policy containing *user=:resolver1* will only
   be valid for the users in *resolver1*.

Technically selfservice policies control the use of the :ref:`selfservice_controller`
and are checked using the method ``getSelfserviceActions``
of the :ref:`code_policy_class`.

.. note:: If no selfservice policy is defined, the user has 
   no actions available in the selfservice portal.

.. note:: In the scope selfservice you can use the wildcard "*" in the
   ``realm`` parameter but not in the ``action`` parameter.
   You need to specify each action, the user should be allowed to use.

The following actions are available in the scope 
*selfservice*:

enroll
~~~~~~

type: bool

There are ``enroll`` actions per token type. Thus you can 
create policy that allow the user to enroll 
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

getotp
~~~~~~

type: bool

The user is allowed to retrieve OTP values from a token.

otp_pin_maxlength
~~~~~~~~~~~~~~~~~
type: integer

range: 0 - 100

This is the maximum allowed PIN length the user is allowed to
use when setting the OTP PIN.

otp_pin_minlength
~~~~~~~~~~~~~~~~~
type: integer

range: o - 100

This is the minimum required PIN the user must use when setting the
OTP PIN.

otp_pin_contents
~~~~~~~~~~~~~~~~
type: string

contents: cnso+-

This defines what characters an OTP PIN should contain when the user
sets it.

**c** are letters matching [a-zA-Z].

**n** are digits mathcing [0-].

**s** are special characters matching [.:,;-_<>+*!/()=?$§%&#~\^]

**o** are other characters.

.. note:: You can change these character definitions in the privacyidea.ini
   file using ``privacyideaPolicy.pin_c``, ``privacyideaPolicy.pin_n``
   and ``privacyideaPolicy.pin_s``.

**Example:** The policy action ``otp_pin_contents=cn, otp_pin_minlength=8`` would
require the user to choose OTP PINs that consist of letters and digits
which have a minimum length of 8.

The logic of the ``otp_pin_contents`` can be enhanced and reversed using the
characters ``+`` and ``-``.

``-cn`` would still mean, that the OTP PIN needs to contain letters and digits
and it must not contain any other characters.

``cn``

   *test1234* and *test12$$* would be valid OTP PINs. *testABCD* would 
   not be a valid OTP PIN.

``-cn``

   *test1234* would be a valid OTP PIN, but *test12$$* and *testABCS* would
   not be valid OTP PINs. The later since it does not contain digits, the first 
   (*test12$$*) since it does contain a special character ($), which it should not.

``+cn`` combines the two required groups. I.e. the OTP PIN should contain 
characters from the sum of the two groups.

*test1234*, *test12$$*, *test* and *1234* would all be valid OTP PINs.

activateQR
~~~~~~~~~~
type: bool

The user is allowed to enroll a QR token.

webprovisionOATH
~~~~~~~~~~~~~~~~
type: bool

The user is allowed to enroll an HMAC token using the QR code for the
OATH token iOS app.

webprovisionGOOGLE
~~~~~~~~~~~~~~~~~~
type: bool

The uses is allowed to enroll a Google Authenticator event based using
the QR code for the Google Authenticator.

webprovisionGOOGLEtime
~~~~~~~~~~~~~~~~~~~~~~
type: bool

The user is allowed to enroll a Google Authenticator time based using
the QR code for the Google Authenticator.

max_count_dpw
~~~~~~~~~~~~~
type: integer

This works together with the ``getotp`` action. This is the maximum
number of OTP values the user may retrieve from DPW tokens.

max_count_hotp
~~~~~~~~~~~~~~
type: integer

This works together with the ``getotp`` action. This is the maximum
number of OTP values the user may retrieve from HOTP tokens.

max_count_totp
~~~~~~~~~~~~~~
type: integer

This works together with the ``getotp`` action. This is the maximum
number of OTP values the user may retrieve from TOTP tokens.

history
~~~~~~~
type: bool

This action allows the user to view and search the audit log
for actions with his own tokens.

getserial
~~~~~~~~~
type: bool

This action allows the user to search for the serial number
of an unassigned token by entering an OTP value.

.. _policy_auth_otp:

auth
~~~~
type: string

If this action is set to *auth=otp*, the users need to
authenticate against privacyIDEA when logging into the selfservie portal.
I.e. they can not login with their domain password anymore
but need to authenticate with one of their tokens.

.. note:: To have this action working correctly, you need to
   set the parameter ``privacyideaURL`` in the privacyidea.ini file.

.. warning:: If you set this action and the user deletes or disables
   all his tokens, he will not be able to authenticate anymore.

.. note:: A sensible way to use this, is to combine this action in 
   a policy with the ``client`` parameter: requiring the users to
   login to the selfservice portal remotely from the internet with
   OTP but still login from within the LAN with the domain password.



