.. index:: system config, token default settings,
.. _system_config:

System Config
-------------

The system configuration has three logical topics: Settings,
token default settings and GUI settings.

.. figure:: images/system-config.png
   :width: 500

   *The system config*

Settings
........

.. _splitatsign:

Use @ sign to split the username and the realm.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This option defines if the username like *user@company*
given during authentication should
be split into the loginname *user* and the realm name *company*.
In most cases this is the desired behavior so this is enabled by default.

But if users log in with email addresses like *user@gmail.com* and
*otheruser@outlook.com* you probably do not want to split.

How a user is related to a realm is described here: :ref:`relate_realm`

This option also affects the login via the :ref:`rest_auth`


.. index:: failcount

Increase the failcounter if the wrong PIN was entered.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If during authentication the given PIN matches a token but the OTP value is
wrong, the failcounter of the tokens for which the PIN matches, is increased.
If the given PIN does not match any token, by default no failcounter is
increased. The latter behavior can be adapted by this option.
If it is set and the given OTP PIN does not match
any token, the failcounter of *all* tokens is increased.


.. index:: failcount
.. _clear_failcounter:

Clear failcounter after minutes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the failcounter reaches the maximum the token gets a timestamp, when the
max fail count was reached. *After* the specified
amount of minutes in this option, the following will
clear the failcounter again:

* A successful authentication with correct PIN and correct OTP value
* A successfully triggered challenge (Usually this means a correct PIN)

A ``0`` means that the automatic clearing of the fail counter is not used.

.. note:: After the maximum failcounter is reached, new requests will not
   update the mentioned timestamp.

Also see :ref:`brute_force`.

.. todo:: Add description for ``Do not use an authentication counter per token.``


Do not use an authentication counter per token.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Usually privacyIDEA keeps track of how often a token is used for authentication and
how often this authentication was successful. This is a per token counter.
This information is written to the token database as a parameter of each token.

This setting means that privacyIDEA does not track this information at all.


Prepend the PIN in front of the OTP value.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Defines if the OTP PIN should be given in front (``pin123456``)
or in the back (``123456pin``) of the OTP value.


.. index:: SAML attributes
.. _return_saml_attributes:

Include SAML attributes in the authentication response.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This option defines, if during a SAML authentication request
additional SAML attributes should be returned.
Usually an authentication response only returns *true* or *false*.

The SAML attributes are the known attributes of a user that are defined in the
attribute mapping of the user resolver and possible :ref:`custom user attributes <user_attributes>`,
like *email*, *phone*, *givenname*, *surname* or any other attributes the resolver
provides. For more information read :ref:`useridresolvers`.

In addition you can set the parameter **Include SAML attributes even if the user
failed to authenticate.**. In this case the response contains the SAML attributes
of the user, even if the user failed to authenticate.


.. index:: autoresync, autosync
.. _autosync:

Automatic resync during authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Automatic *resync* defines if the system should try to resync a token if a user
provides a wrong OTP value. AutoResync works like this:

* If the counter of a wrong OTP value is within the resync window, the system
  remembers the counter of the OTP value for this token in the token info
  field ``otp1c``.

* Now the user needs to authenticate a second time within the time-interval
  given in **Auto resync timeout** with the next successive OTP value.

* The system checks if the counter of the second OTP value is the successive
  value to ``otp1c``.

* If it is, the token counter is set and the user is successfully authenticated.

.. note:: AutoResync works for all HOTP and TOTP based tokens including SMS and
   Email tokens.


.. index:: usercache
.. _user_cache_timeout:

User Cache expiration in seconds
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This setting is used to enable the user cache and
configure its expiration timeout. If its value is set to ``0`` (which is the default value),
the user cache is disabled.
Otherwise, the value determines the time in seconds after which entries of the user
cache expire. For more information read :ref:`usercache`.

.. note:: If the user cache is already enabled and you increase the expiration timeout,
   expired entries that still exist in the user cache could be considered active again!


.. index:: Override client, map client, proxies, RADIUS server, authenticating client, client
.. _override_client:

Override Authorization Client
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This setting is important with client specific
policies (see :ref:`policies`) and RADIUS servers or other proxies. In
case of RADIUS the authenticating client
for the privacyIDEA system will always be the RADIUS server, which issues
the authentication request. But you can allow the RADIUS server IP to
send another client information (in this case the RADIUS client) so that
the policy is evaluated for the RADIUS client. A RADIUS server
may add the API parameter *client* with a new IP address. A HTTP reverse
proxy may append the respective client IP to the ``X-Forwarded-For`` HTTP
header.

This field takes a comma separated list of sequences of IP Networks
mapping to other IP networks.

**Examples**

::

   10.1.2.0/24 > 192.168.0.0/16

Proxies in the sub net 10.1.2.0/24 may mask as client IPs 192.168.0.0/16. In
this case the policies for the corresponding client in 192.168.x.x apply.

::

   172.16.0.1

The proxy 172.16.0.1 may mask as any arbitrary client IP.

::

   10.0.0.18 > 10.0.0.0/8

The proxy 10.0.0.18 may mask as any client in the subnet 10.x.x.x.

Note that the proxy definitions may be nested in order to support multiple proxy hops. As an example::

    10.0.0.18 > 10.1.2.0/24 > 192.168.0.0/16

means that the proxy 10.0.0.18 may map to another proxy into the subnet 10.1.2.x, and a proxy in this
subnet may mask as any client in the subnet 192.168.x.x.

With the same configuration, a proxy 10.0.0.18 may map to an application plugin in the subnet 10.1.2.x,
which may in turn use a ``client`` parameter to mask as any client in the subnet 192.168.x.x.


SMTP server for password recovery
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Specify the :ref:`SMTP server configuration <smtpserver>` which should be used
for sending password recovery emails.


Token default settings
......................

.. note:: The following settings are token specific values which are
   set during enrollment.
   Some of these values can be overridden by policies or events during rollout.


OTP length of newly enrolled tokens
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is the default length of the OTP value. If no OTP length is
specified during enrollment, this value will be used. This affects all
OATH-based tokens like SMS, Email, TOTP and HOTP.

Count Window of newly enrolled tokens
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This setting defines how many OTP values will be calculated during
an authentication request to check for a match.

.. index:: failcount

Max Failcount of newly enrolled tokens
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This setting defines the maximum failcounter for newly enrolled tokens. If the
failcounter exceeds this number the token can not be used unless it is reset.

.. note:: In fact the failcounter will only increase up to this maximum failcount (``Maxfail``).
   Even if more failed authentication request occur, the failcounter will
   not be increased.

.. index:: syncwindow

Sync Window of newly enrolled tokens
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This setting defines the synchronization window for newly enrolled tokens.
The window defines how many OTP values will be calculated
during a resync of the token.

.. note:: In case of HOTP token, this is the amount of steps that will be calculated
   from the current token counter onwards. For TOTP token, the number of steps
   will be multiplied with the timestep of the token and this interval will be checked
   *before* **and** *after* the current time.

.. _challenge_validity_time:

The challenge validity time
~~~~~~~~~~~~~~~~~~~~~~~~~~~

This setting defines the timeout for a challenge response
authentication. If the response is received after the given time interval, the
response is not accepted anymore.
