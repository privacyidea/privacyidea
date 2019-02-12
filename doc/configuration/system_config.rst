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

.. _splitatsign:

Use @ sign to split the username and the realm.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``splitAtSign`` defines if the username like *user@company* 
given during authentication should
be split into the loginname *user* and the realm name *company*.
In most cases this is the wanted behaviour so this is enabled by default.

But given your users log in with email addresses like *user@gmail.com* and
*otheruser@outlook.com* you probably do not want to split.

How a user is related to a realm is described here: :ref:`relate_realm`

This option also affects the login via the :ref:`rest_auth`


Increase the failcounter if the wrong PIN was entered.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If during authentication the given PIN matches a token but the OTP value is
wrong the failcounter of
the tokens for which the PIN matches, is increased.
If the given PIN does not match any token, by default no failcounter is
increased. The latter behaviour can be adapted by ``FailCounterIncOnFalsePin``.
If ``FailCounterIncOnFalsePin`` is set and the given OTP PIN does not match
any token, the failcounter of *all* tokens is increased.


.. _clear_failcounter:

Clear failcounter after *x* minutes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the failcounter reaches the maximum the token gets a timestamp, when the
max fail count was reached. *After* the specified
amount of minutes in ``failcounter_clear_timeout`` the following will
clear the failcounter again:

* A successful authentication with correct PIN and correct OTP value
* A successfully triggered challenge (Usually this means a correct PIN)
* An authentication with a correct PIN, but a wrong OTP value (Only if
  :ref:`reset_failcounter_on_correct_pin` is set).

A "0" means automatically clearing the fail counter is not used.

.. note:: After the maximum failcounter is reached, new requests will not
   update the mentioned timestamp.

Also see :ref:`brute_force`.

.. todo:: Add description for ``Do not use an authentication counter per token.``


.. _reset_failcounter_on_correct_pin:

Resetting Failcounter on correct PIN
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After the above mentioned timeout the failcounter is reset by a successful
authentication (correct PIN and OTP value) or by the correct PIN of a challenge
response token.

It can be also reset by the correct PIN of any token, when setting
``ResetFailcounterOnPIN`` to True.
The default behaviour is, that the correct PIN of a normal token will *not*
reset the failcounter after the clearing timeout.


Prepend the PIN in front of the OTP value.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Defines if the OTP PIN should be given in front ("pin123456")
or in the back ("12345pin") of the OTP value.


.. _return_saml_attributes:

Include SAML attributes in the authentication response.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. index:: SAML attributes

``Return SAML attributes`` defines if during an SAML authentication request
additional SAML attributes should be returned.
Usually an authentication response only returns *true* or *false*.

The SAML attributes are the known attributes that are defined in the
attribute mapping e.g. of the LDAP resolver like *email*, *phone*,
*givenname*, *surname* or any other attributes you fetch from the LDAP
directory. For more information read :ref:`ldap_resolver`.

In addition you can set the parameter ``ReturnSamlAttributesOnFail``. In this
case the response contains the SAML attributes of the user, even if the user
failed to authenticate.


.. _autosync:

.. index:: autoresync, autosync

Automatic resync during authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Automatic *resync* defines if the system should try to resync a token if a user
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


.. todo:: Describe ``Auto resync timeout``


.. _user_cache_timeout:

User Cache expiration in seconds
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The setting ``User Cache expiration in seconds`` is used to enable the user cache and
configure its expiration timeout. If its value is set to ``0`` (which is the default value),
the user cache is disabled.
Otherwise, the value determines the time in seconds after which entries of the user
cache expire. For more information read :ref:`usercache`.

.. note:: If the user cache is already enabled and you increase the expiration timeout,
   expired entries that still exist in the user cache could be considered active again!

.. _override_client:

.. index:: authenticating client, client, override client

Override Authorization Client
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. index:: Override client, map client, proxies, RADIUS server

``Override Authorization client`` is important with client specific
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

.. _challenge_validity_time:

Challenge Validity Time
~~~~~~~~~~~~~~~~~~~~~~~

``DefaultChallengeValidityTime`` is the timeout for a challenge response
authentication. If the response is set after the ChallengeValidityTime, the
response is not accepted anymore.

SerialLength
~~~~~~~~~~~~

The default length of generated serial numbers is an 8 digit hex string.
If you need another length, it can be configured in the database table ``Config``
with the key word ``SerialLength``.

No Authenitcation Counter
~~~~~~~~~~~~~~~~~~~~~~~~~

Usually privacyIDEA keeps track of how often a token is used for authentication and
how often this authentication was successful. This is a per token counter.
This information is written to the token database as a parameter of each token.

The setting "Do not use an authentication counter per token" (``no_auth_counter``)
means that privacyIDEA does not track this information at all.
