.. _system_config:

System Config
-------------

.. index:: system config, token default settings,

The system configuration has three logical topics: Settings,
token default settings and GUI settings.

.. figure:: images/system-config.png
   :width: 500

   *The system config*

Settings
........

Split @ Sign
~~~~~~~~~~~~

``splitAtSign`` defines if the username like *user@company* 
given during authentication should
be split into the loginname *user* and the realm name *company*.
In most cases this is the wanted behaviour.

But given your users log in with email addresses like *user@gmail.com* and
*otheruser@outlook.com* you probably do not want to split.

SAML Attributes
~~~~~~~~~~~~~~~

``Return SAML attributes`` defines if during an SAML authentication request
additional SAML attributes should be returned.
Usually an authentication response only returns *true* or *false*.


FailCounterIncOnFalsePin
~~~~~~~~~~~~~~~~~~~~~~~~

If during authentication the given PIN matches a token but the OTP value is
wrong the failcounter of
the tokens for which the PIN matches, is increased.
If the given PIN does not match any token, by default no failcounter is
increased. The later behaviour can be adapted by ``FailCounterIncOnFalsePin``.
If ``FailCounterIncOnFalsePin`` is set and the given OTP PIN does not match
any token, the failcounter of *all* tokens is increased.

Prepend PIN
~~~~~~~~~~~

``PrependPin`` defines if the OTP PIN should be given in front ("pin123456") 
or in the back ("12345pin") of the OTP value.

.. index:: autoresync, autosync

AutoResync
~~~~~~~~~~

``Auto resync`` defines if the system should try to resync a token if a user
provides a wrong OTP value. AutoResync works like this:

* If the counter of a wrong OTP value is within the resync window, the system
  remembers the counter of the OTP value for this token in the token info
  field ``otp1c``.

* Now the user needs to authenticate a second time within ``auto resync
  timeout`` with the next successive OTP value.

* The system checks if the counter of the second OTP value is the successive
  value to ``otp1c``.

* If it is, the token counter is set and the user is successfully authenticated.

.. note:: AutoResync works for all HOTP and TOTP based tokens including SMS and
   Email tokens.

.. index:: authenticating client, client, override client

Override Authentication Client
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``Override Authentication client`` is important with client specific 
policies (see :ref:`policies`) and RADIUS servers. In
case of RADIUS the authenticating client
for the privacyIDEA system will always be the RADIUS serve, which issues 
the authentication request. But you can allow the RADIUS server IP to 
send another client information (in this case the RADIUS client) so that
the policy is evaluated for the RADIUS client. This field takes a comma
separated list of IP addresses.

Token default settings
......................

.. _failcounter:

Reset Fail Counter
~~~~~~~~~~~~~~~~~~
``DefaultResetFailCount`` will reset the failcounter of a token if this token was
used for a successful authentication. If not checked, the failcounter will not
be resetted and must be resetted manually.

.. note:: The following settings are token specific value which are 
   set during enrollment.
   If you want to change this value of a token later on, you need to
   change this at the tokeninfo dialog.


Maximum Fail Counter
~~~~~~~~~~~~~~~~~~~~

``DefaultMaxFailCount`` is the maximum failcounter a token way get. If the
failcounter exceeds this number the token can not be used unless the failcounter
is resetted.

.. note:: In fact the failcounter will only increase till this maxfailcount.
   Even if more failed authentication request occur, the failcounter will 
   not increase anymore.

Sync Window
~~~~~~~~~~~

``DefaultSyncWindow`` is the window how many OTP values will be calculated
during resync of the token.

OTP Length
~~~~~~~~~~

``DefaultOtpLen`` is the length of the OTP value. If no OTP length is
specified during enrollment, this value will be used.

Count Window
~~~~~~~~~~~~

``DefaultCountWindow`` defines how many OTP values will be calculated during
an authentication request.

Challenge Validity Time
~~~~~~~~~~~~~~~~~~~~~~~

``DefaultChallengeValidityTime`` is the timeout for a challenge response
authentication. If the response is set after the ChallengeValidityTime, the
response is not accepted anymore.

