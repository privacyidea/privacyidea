System config
-------------

.. index:: system config, token default settings,

The system configuration has three tabs: Settings, 
token default settings and GUI settings.

Settings
........

``splitAtSign`` defines if the username like *user@company* 
given during authentication should
be split into the loginname *user* and the realm name *company*.
In most cases this is the wanted behavious.

But given your users login with email addresses like *user@gmail.com* and
*otheruser@outlook.com* you probably do not want to split.

``Return SAML attributes`` defines if during an SAML authentication request
additional SAML attributes should be returned.
Usuall an authentication response only returns *true* or *false*.

If ``FailCounterIncOnFalsePin`` is set the failcounter of all tokens of 
a user will be increased. When given a false PIN the system can not identify
the token the user wants to login with. So it either increases the failcounter
of all tokens of this user or none.

``PrependPin`` defines if the OTP PIN should be given in front ("pin123456") 
or in the back ("12345pin") of the OTP value.

.. index:: autoresync

``Auto resync`` defines if the system should try to resync a token if a user
provides a wrong OTP value. If checked, the system remembers the OTP value
and if during ``auto resync timeout`` the user tries to authenticate again 
with the next, successive OTP value, the system tries to resync this token with the 
two given OTP values.

.. index:: pass on user not found, pass on user no token

``Pass on user not found`` let the system return a successful authentication
response if the authenticating user does not exist in the system.

.. warning:: Use with care and only if you know what you are doing!

``Pass on user no token`` let the system return a successful authentication
response if the authenticating user exists in the system but has no token
assigned. 

.. warning:: Use with care and only if you know what you are doing! Since 
   the user could remove all his tokens in selfservice and then have free
   rides forever.

.. index:: authenticating client, client, override client

``Override Authentication client`` is important with client specific 
policies (see :ref:`policies`) and RADIUS servers. In case of RADIUS the authenticating client
for the privacyIDEA system will always be the RADIUS serve, which issues 
the authentication request. But you can allow the RADIUS server IP to 
send another client information (in this case the RADIUS client) so that
the policy is evaluated for the RADIUS client. This field takes a comma seperated list of IP addresses.

``maximum concurrent OCRA challenges`` defines how many OCRA requests for
a single OCRA token are allowed to be active simultaniously.

``OCRA challenge timeout`` defines how many seconds an OCRA challenge is kept
active. The response must be sent within this timeout.

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


OCRA settings
~~~~~~~~~~~~~

``default OCRA suite`` is the OCRA suite that is set for an OCRA token 
during enrollment if no OCRA suite is specified.

``default QR suite`` is the OCRA suite that is set for a QR token 
during enrollment if no OCRA suite is specified.



GUI settings
............

The login window of the WebUI may display a dropdown box with all realms.
You might hide this dropdown box, if you do not want to tell the world
which realms are defined on your system.
If you check ``display realm select box`` the list of all realms including 
the special realm *admin* for the administrators from the superuser file
will be displayed in the login form.
