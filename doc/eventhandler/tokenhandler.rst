.. _tokenhandler:

Token Handler Module
--------------------

.. index:: Token Handler, Handler Modules

The token event handler module is used to perform actions on tokens in
certain events.

This way you can define workflows to automatically modify tokens, delete or
even create new tokens.

Possible Actions
~~~~~~~~~~~~~~~~

set tokenrealm
..............

Here you can set the token realms of the token.

E.g. You could use this action to automatically put all newly enrolled tokens
 into a special realm by attaching this action to the event *token_init*.

delete
......

The token which was identified in the request will be deleted if all
conditions are matched.

unassign
........

The token which was identified in the request will be unassign from the user
if all conditions are matched.

disable
.......

The token which was identified in the request will be disabled
if all conditions are matched.

enable
......

The token which was identified in the request will be enabled
if all conditions are matched.

.. _event_token_enroll:

enroll
......

If all conditions are matched a new token will be enrolled. This new token
can be assigned to a user, which was identified in the request.

The administrator can specify the **tokentype** and the **realms** of the new
token. By default the generation of the token will use the parameter ``genkey``, to
generate the otp key. (see :ref:`rest_token`).

The action ``enroll`` also can take the options **dynamic_phone** (in case of tokentype SMS) and
**dynamic_email** (in case of tokentype email). Then these tokens are created with a dynamic
loadable phone number or email address, that is read from the user store on each authentication request.

Finally the administrator can specify the option **additional_params**. This needs to be a dictionary
with parameters, that get passed to the init request. You can specify all parameters, that
would be used in a ``/token/init`` request:

   {"hashlib": "sha256", "type": "totp", "genkey": 0, "otpkey": "31323334"}

would create a TOTP token, that uses the SHA256 hashing algorithm instead of SHA1.
``genkey: 0`` overrides the default behaviour of generating an OTP secret. Instead the
fixed OTP secret "31323334" (``otpkey``) is used.

If the tokentype is set to "email" or "sms", you can also specify an SMTP server or SMS gateway
configuration for the token enrolled by selecting a configuration in the corresponding field
(**smtp_identifier** or **sms_identifier**). If none is selected, then the default system configuration
will be used.

set description
...............

If all conditions are matched the description of the token identified in the
request will be set.

You can use the tag ``{current_time}`` or ``{now}`` to set the current
timestamp. In addition you can append an offset to *current_time* or *now*
like ``{now}-12d`` or ``{now}+10m``. This would write a timestamp which is 12
days in the past or 10 minutes in the future. The plus or minus must follow
without blank, allowed time identifiers are s (seconds), m (minutes), h
(hours) and d (days).

Other tags are ``{client_ip}`` for the client IP address and ``{ua_browser}``
and ``{ua_string}`` for information on the user agent.

set validity
............

If all conditions are matched the validity period of the token will be set.

There are different possibilities to set the start and the end of the
validity period. The event definition can either contain a fixed date and
time or if can contain a time offset.

**Fixed Time**

A fixed time can be specified in the following formats.

Only date without time:

  * 2016/12/23
  * 23.12.2016

Date with time:

  * 2016/12/23 9:30am
  * 2016/12/23 11:20:pm
  * 23.12.2016 9:30
  * 23.12.2016 23:20

Starting with version 2.19 we recommend setting the fixed time in the ISO
8601 corresponding time format

  * 2016-12-23T15:30+0600

**Time Offset**

You can also specify a time offset. In this case the validity period will be
set such many days after the event occurred. This is indicated by using a "+"
and a specifier for days (d), hours (h) and minutes (m).

E.g. ``+30m`` will set to start the validity period in 30 minutes after the
event occurred.

``+30d`` could set the validity period to end 30 days after an event occurred.

.. note:: This way you could easily define a event definition, which will set
   newly enrolled tokens to be only valid for a certain amount of days.

set countwindow
...............

Here the count window of a token can be set. This requires an integer value.

set tokeninfo
.............

Using the action ``set tokeninfo`` you can set any arbitrary tokeninfo
attribute for the token. You need to specify the ``key`` of the
tokeninfo and the ``value``.

In the value field you can use the tag ``{current_time}`` to set the current
timestamp. In addition you can append an offset to *current_time* or *now*
like ``{now}-12d`` or ``{now}+10m``. This would write a timestamp which is 12
days in the passt or 10 minutes in the future. The plus or minus must follow
without blank, allowed time identifiers are s (seconds), m (minutes), h
(hours) and d (days).

Other tags are ``{client_ip}`` for the client IP address and ``{ua_browser}``
and ``{ua_string}`` for information on the user agent and ``{username}`` and
``{realm}`` for information on the user in the parameters.

.. note:: Some tokens have token specific attributes that are stored in the
   tokeninfo. The TOTP token type has a ``timeWindow``. The TOTP and the HOTP
   token store the ``hashlib`` in the tokeninfo, the SMS token stores the
   ``phone`` number.

.. note:: You can use this to set the ``timeWindow`` of a TOTP token for
   :ref:`faq_initial_synchronization`.

set failcounter
...............

Using the action ``set failcounter`` you can reset the fail counter by
setting it to 0 or also "block" the token by setting the fail counter to what
ever value the "max_fail" is, e.g. 10. Only integer values are allowed.

See :ref:`failcounter`.

change failcounter
..................

Using the action ``change failcounter`` you can increase or decrease the fail counter.
Positive and negative integer values are allowed. Positive values will increase the
fail counter, negative values will decrease it.

.. note:: To limit a token handler in decreasing the fail counter, you may use the
   event handler condition **failcounter** (c.f. :ref:`handlerconditions`) and set
   it to e.g. ">-5". Once this condition is not met anymore, the event handler will
   not be triggered.

set max failcount
.................

Using the action ``set max failcount`` you can set the maximum failcounter of a
token to the specific value.
Only integer values are allowed.

See :ref:`failcounter`.

set random pin
..............

Sets a random PIN for the handled token. The PIN is then added to the response in
``detail->pin``. This can be used in the *notification handler*.
Please take care, that probably the PIN needs to be removed from the response
using the *response mangler handler* after
handling it with the notification handler.

add tokengroup
..............

The token is assigned to the given tokengroup.

.. Note:: A token can be assigned to several different tokengroups at the same time.

remove tokengroup
.................

The token is unassigned from the given tokengroup.

Code
~~~~


.. automodule:: privacyidea.lib.eventhandler.tokenhandler
   :members:
   :undoc-members:
