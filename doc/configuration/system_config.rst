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

``splitAtSign`` defines if the username like *user@company* 
given during authentication should
be split into the loginname *user* and the realm name *company*.
In most cases this is the wanted behaviour.

But given your users log in with email addresses like *user@gmail.com* and
*otheruser@outlook.com* you probably do not want to split.

``Return SAML attributes`` defines if during an SAML authentication request
additional SAML attributes should be returned.
Usuall an authentication response only returns *true* or *false*.

If during authentication the given PIN matches a token but the OTP value is
wrong the failcounter of
the tokens for which the PIN matches, is increased.
If the given PIN does not match any token, by default no failcounter is
increased. The later behaviour can be adapted by ``FailCounterIncOnFalsePin``.
If ``FailCounterIncOnFalsePin`` is set and the given OTP PIN does not match
any token, the failcounter of *all* tokens is increased.

``PrependPin`` defines if the OTP PIN should be given in front ("pin123456") 
or in the back ("12345pin") of the OTP value.

.. index:: autoresync

``Auto resync`` defines if the system should try to resync a token if a user
provides a wrong OTP value. If checked, the system remembers the OTP value
and if during ``auto resync timeout`` the user tries to authenticate again 
with the next, successive OTP value, the system tries to resync this token with the 
two given OTP values.

.. index:: authenticating client, client, override client

``Override Authentication client`` is important with client specific 
policies (see :ref:`policies`) and RADIUS servers. In case of RADIUS the authenticating client
for the privacyIDEA system will always be the RADIUS serve, which issues 
the authentication request. But you can allow the RADIUS server IP to 
send another client information (in this case the RADIUS client) so that
the policy is evaluated for the RADIUS client. This field takes a comma seperated list of IP addresses.

Token default settings
......................

Misc settings
~~~~~~~~~~~~~
``DefaultResetFailCount`` will reset the failcounter of a token if this token was
used for a successful authentication. If not checked, the failcounter will not
be resetted and must be resetted manually.

.. note:: The following settings are token specific value which are 
   set during enrollment.
   If you want to change this value of a token lateron, you need to 
   change this at the tokeninfo dialog.


``DefaultMaxFailCount`` is the maximum failcounter a token way get. If the
failcounter exceeds this number the token can not be used unless the failcounter
is resetted.

.. note:: In fact the failcounter will only increas till this maxfailcount. 
   Even if more failed authentication request occur, the failcounter will 
   not increase anymore.

``DefaultSyncWindow`` is the window how many OTP values will be caluculated
during resync of the token. 

``DefaultOtpLen`` is the length of the OTP value. If no OTP lenght is 
specified during enrollment, this value will be used.

``DefaultCountWindow`` defines how many OTP values will be calculated during
an authentication request.

``DefaultChallengeValidityTime`` is the timeout for a challenge response
authentication.

