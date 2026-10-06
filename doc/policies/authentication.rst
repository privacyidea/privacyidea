.. _authentication_policies:

Authentication policies
-----------------------

.. index:: authentication policies

The scope *authentication* gives you more detailed
possibilities to authenticate the user or to define
what happens during authentication.

Technically the authentication policies apply
to the REST API :ref:`rest_validate` and are checked
using :ref:`code_policy` and
:ref:`policy_decorators`.

The following actions are available in the scope
*authentication*:

.. _otppin_policy:

otppin
~~~~~~

type: ``string``

This action defines how the fixed password part during
authentication should be validated.
Each token has its own OTP PIN, but the administrator can choose
how the authentication should be processed:

``otppin=tokenpin``

   This is the default behavior. The user needs to
   pass the OTP PIN concatenated with the OTP value.

``otppin=userstore``

   The user needs to pass the user store password
   concatenated with the OTP value. It does not matter
   if the OTP PIN is set or not.
   If the user is located in an Active Directory the user
   needs to pass their domain password together with the
   OTP value.

.. note:: The domain password is checked with an LDAP
   bind right at the moment of authentication.
   So if the user is locked or the password was
   changed authentication will fail.

``otppin=none``

   The user must not send a fixed password, only the OTP value.
   A request with PIN and OTP fails.

.. versionadded:: 2.0

.. _passthru_policy:

passthru
~~~~~~~~

.. index:: passthru, migration

type: ``string``

If the user has no token assigned, they will be authenticated against the
userstore or the given RADIUS configuration.
Meaning the user needs to provide the LDAP/SQL password or valid credentials
for the RADIUS server.
If a :ref:`passonnotoken` policy also matches, it takes precedence: users without
a token are accepted without their password being checked.

.. note:: This is a good way to do a smooth enrollment.
   Users having a token enrolled will have to use the
   token, users not having a token, yet, will be able
   to authenticate with their domain password.

   It is also a way to do smooth migrations from other OTP systems.
   The authentication request of users without a token is forwarded to the
   specified RADIUS server. Only an Access-Accept of the RADIUS server
   authenticates the user. Challenge-response of the RADIUS server
   (Access-Challenge) is not supported; such a request fails.

.. note:: The passthru policy overrides the authorization policy
   for :ref:`tokentype_policy`. This means a user may authenticate due
   to the passthru policy (since they have no token)
   although a tokentype policy is active!

.. warning:: If the user has the right to delete their tokens in the selfservice
   portal, the user could delete all their tokens and then authenticate with
   their static password again.

.. versionadded:: 2.0

.. _policy_passthru_ignore_rollout_state:

passthru_ignore_rollout_state
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``string``

allowed values: ``clientwait``, ``pending``, ``verify``, ``enrolled``, ``broken``, ``failed``, ``denied``

This policy only takes effect if the policy ``passthru`` is set.
When privacyIDEA checks whether the user has a token, tokens in one of the given
rollout states are not counted. A user whose only tokens are in such a state is
then authenticated as described in :ref:`passthru_policy`. Several rollout states
can be given as a space-separated list.

.. versionadded:: 3.14

passthru_assign
~~~~~~~~~~~~~~~

.. index:: passthru, migration

type: ``string``

This policy is only evaluated, if the policy ``passthru`` is set.
If the user is authenticated against a RADIUS server, then privacyIDEA
splits the sent password into PIN and OTP value and tries to find an unassigned token,
that is in the user's realm by using the OTP value. If it can identify this token, it assigns this
token to the user and sets the sent PIN.

The policy is configured with a string value, which contains

* the position of the PIN
* the OTP length and
* the number of OTP values tested for each unassigned token (optional, default=100).

Examples are

* ``8:pin`` would be an eight digit OTP value followed by the PIN
* ``pin:6:10000`` would be the PIN followed by a 6-digit OTP value, 10,000
  OTP values would be checked for each token.

.. note:: This method can be used to automatically migrate tokens from an old system
   to privacyIDEA. The administrator needs to import all seeds of the old tokens
   and put the tokens in the user's realm.

.. warning:: This can be very time consuming if the number of OTP values to check is set too high!

.. versionadded:: 3.1

.. _passonnotoken:

passOnNoToken
~~~~~~~~~~~~~

.. index:: passOnNoToken

type: ``bool``

If the user has no token assigned an authentication request
for this user will always be true.

.. warning:: Only use this if you know exactly what
   you are doing.

.. versionadded:: 2.0

.. _policy_passonnotoken_ignore_rollout_state:

passonnotoken_ignore_rollout_state
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``string``

allowed values: ``clientwait``, ``pending``, ``verify``, ``enrolled``, ``broken``, ``failed``, ``denied``

This policy only takes effect if the policy ``passOnNoToken`` is set.
When privacyIDEA checks whether the user has a token, tokens in one of the given
rollout states are not counted. A user whose only tokens are in such a state is
then authenticated as described in :ref:`passonnotoken`. Several rollout states
can be given as a space-separated list.

.. versionadded:: 3.14

.. _passonnouser:

passOnNoUser
~~~~~~~~~~~~

.. index:: passOnNoUser

type: ``bool``

If the user does not exist, the authentication request is successful.

.. warning:: Only use this if you know exactly what you are doing.

.. versionadded:: 2.0

.. _smstext:

smstext
~~~~~~~

.. index:: SMS policy, SMS text

type: ``string``

This is the text that is sent via SMS to the user trying to
authenticate with an SMS token. This can contain the tags *<otp>* and *<serial>*.
Enclosing single quotes are optional and removed. A comma in the text has to be
escaped as ``\,``.

You can use the tag *{challenge}*. This will add
the challenge data that was passed in the first authentication request in the
challenge parameter. This could contain banking transaction data, like it is
used by the DisplayTAN token (see :ref:`ocra_token`). The tag is empty if the
authentication request did not contain a challenge parameter.

The ``smstext`` can contain a lot more tags similar to the
policy :ref:`emailtext`:

  * {otp} or *<otp>* the One-Time-Password
  * {serial} or *<serial>* the serial number of the token.
  * {user} the given name of the token owner.
  * {givenname} the given name of the token owner.
  * {surname} the surname of the token owner.
  * {username} the loginname of the token owner.
  * {userrealm} the realm of the token owner.
  * {tokentype} the type of the token.
  * {recipient_givenname} the given name of the recipient.
  * {recipient_surname} the surname of the recipient.
  * {time} the current server time in the format HH:MM:SS.
  * {date} the current server date in the format YYYY-MM-DD

Only the tags named above may be used. An unknown tag such as ``{foo}`` or a single curly
brace prevents the SMS from being sent; the authentication request fails with
"The PIN was correct, but the SMS could not be sent!".

In the :ref:`sms_gateway_config` the tag *{otp}* will be replaced by the custom
message, set with this policy.

Default: *<otp>*

.. note:: A single SMS holds 160 characters of the GSM 7-bit alphabet, or 70 characters if the text
   contains other characters. You should take care, that the *smstext* does not exceed this limit.
   SMS gateways could reject too long messages or the delivery could fail.

.. note:: Some apps may be able to handle incoming OTPs as a so called
   `origin-bound one-time code <https://github.com/wicg/sms-one-time-codes>`_
   in the format::

     Your OTP is {otp}
     @privacyidea.mydomain.com #{otp}

.. versionadded:: 2.1

smsautosend
~~~~~~~~~~~

.. index:: SMS automatic resend

type: ``bool``

A new OTP value will be sent via SMS if the user authenticated
successfully with their SMS token. Thus the user does not
have to trigger a new SMS when they want to log in again.

.. versionadded:: 2.1

.. _emailtext:

emailtext
~~~~~~~~~

.. index:: EMail policy, Email text

type: ``string``

This is the text that is sent via Email to be used with Email Token. This
text should contain the OTP tag.

The text can contain the following tags, that will be filled:

  * {otp} or *<otp>* the One-Time-Password
  * {serial} or *<serial>* the serial number of the token.
  * {user} the given name of the token owner.
  * {givenname} the given name of the token owner.
  * {surname} the surname of the token owner.
  * {username} the loginname of the token owner.
  * {userrealm} the realm of the token owner.
  * {tokentype} the type of the token.
  * {recipient_givenname} the given name of the recipient.
  * {recipient_surname} the surname of the recipient.
  * {time} the current server time in the format HH:MM:SS.
  * {date} the current server date in the format YYYY-MM-DD

You can use the tag *{challenge}*. This will add
the challenge data that was passed in the first authentication request in the
challenge parameter. This could contain banking transaction data, like it is
used by the DisplayTAN token (see :ref:`ocra_token`). The tag is empty if the
authentication request did not contain a challenge parameter.

Only the tags listed above may be used. An unknown tag such as ``{foo}`` or a
single curly brace prevents the email from being sent; the authentication request
fails with "The PIN was correct, but the EMail could not be sent!".

Default: *<otp>*

You can also provide the filename to an email template. The filename must be prefixed with
``file:`` like ``file:/etc/privacyidea/emailtemplate.html``. The template is
an HTML file.

.. note:: If a message text is supplied directly, the email is sent as plain text.
   If the email template is read from a file, an HTML-only email is sent when the
   email token uses an :ref:`SMTP server configuration <smtpserver>` (as required);
   with the deprecated ``email.mailserver`` settings the template is sent as plain
   text.

.. versionadded:: 2.3

emailsubject
~~~~~~~~~~~~

.. index:: Email policy, Email subject

type: ``string``

This is the subject of the Email sent by the Email Token.
You can use the same tags as mentioned in ``emailtext``.
Only these tags may be used. An unknown tag such as ``{foo}`` or a single curly
brace prevents the email from being sent; the authentication request fails with
"The PIN was correct, but the EMail could not be sent!".

Default: Your OTP

.. versionadded:: 2.3

emailautosend
~~~~~~~~~~~~~

.. index:: Email policy

type: ``bool``

If set, a new OTP Email will be sent, when successfully authenticated with an
Email Token.

.. versionadded:: 2.3

.. _policy_set_realm:

set_realm
~~~~~~~~~

.. index:: Set realm for authentication

type: ``string``

This policy sets or overwrites the realm parameter at the beginning of every request to the ``/validate/``
endpoints (e.g. :http:post:`/validate/check`, :http:post:`/validate/triggerchallenge`,
:http:post:`/validate/initialize`) and of :http:post:`/auth`. The same request handling also runs for ``/register``
and ``/recover``. It is applied before the first user resolving to avoid unnecessary user store
requests. This means, when this policy is evaluated there is no user object in the request, yet!

Due to this, the *user* and *realm* fields of the policy are compared with the login name and the realm of the
request (or the default realm); a *resolver* restriction is ignored. A condition on user attributes can not be
evaluated: by default the request fails with an error, unless :ref:`policy_condition_handle_missing_data` says
otherwise.

Also, the given parameters can actually point to a non-existing user object.

This policy can be used if the user can not pass his realm when authenticating at a certain
client, but this username would not be found in the default realm.

.. note:: This policy is evaluated before the :ref:`policy_mangle` policies. If this policy matches, the
   authorization policy :ref:`policy_setrealm` is not evaluated at all, and :ref:`policy_mangle` policies for the
   realm are ignored.

For in depth information about user and realm mapping read :ref:`realms`.

.. versionadded:: 3.12.2

.. _policy_mangle:

mangle
~~~~~~

.. index:: Mangle authentication request, Mangle policy

type: ``string``

The ``mangle`` policy can mangle the authentication request data before they
are processed. Meaning the parameters ``user``, ``pass`` and ``realm`` can be
modified prior to authentication. If ``user`` or ``realm`` is modified, the user object of the request is
created again from the modified parameters.

.. note:: This policy is applied to :http:post:`/validate/check`, :http:post:`/validate/radiuscheck` and
    :http:get:`/machine/authitem`, not to ``/validate/triggerchallenge`` or ``/auth``.

    If the policy :ref:`policy_set_realm` is set, this policy is only applied for ``user`` and ``pass``
    parameters. Policies with the ``realm`` parameter are ignored.

    Without a matching :ref:`policy_set_realm` policy, this policy is applied after the authorization policy
    :ref:`policy_setrealm`.

This is useful if either information needs to be stripped or added to such a
parameter.
To accomplish that, the mangle policy can do a regular expression search and
replace using the keywords *user*, *pass* (password) and *realm*.

A valid action could look like this::

   action: mangle=user/.*(.{4})/user\1/

This would modify a username like "userwithalongname" to "username", since it
would use the last four characters of the given username ("name") and prepend
the fixed string "user".

This way you can add, remove or modify the contents of the three parameters.
For more information on the regular expressions see [#pythonre]_.

The mangling happens after the user was read from the request as described in
:ref:`relate_realm`, and the user object is then created again from the mangled
parameters. So the request may name a user or realm that does not exist, as long
as the mangled values exist - the "admin_username" example below relies on this.
The mangle policy itself is matched against the user as sent: its *user* field
has to name the login as sent, and a mangle policy restricted to a resolver does
not match a user that does not exist.

.. note:: Use a single backslash, as in a Python regular expression: ``\1``
   refers to the first group, ``\s`` matches whitespace. The value is used as it
   is entered in the WebUI or sent in a JSON body. Write the backslash doubled
   only where the value itself is written inside an encoded string, e.g. a JSON
   or YAML double-quoted string, a Python string literal for
   ``pi-manage config policy create -f`` or ``pi-manage config import``, or a
   shell double-quoted string.

**Example**: A policy to remove whitespace characters from the realm name would
look like this::

   action: mangle=realm/\s//

**Example**: If you want to authenticate the user only by the OTP value, no
matter what OTP PIN they enter, a policy might look like this::

   action: mangle=pass/.*(.{6})/\1/

This only works for tokens without a PIN or with ``otppin=none``: after the
mangling, ``pass`` holds only the OTP value, so the token PIN is checked against
an empty value.

**Example**: If you want to strip a string from the front of a username, for
example to have "admin_username" resolve to just "username", it would look like
this::

   action: mangle=user/admin_(.*)/\1/

.. versionadded:: 2.5

.. _policy_challenge_response:

challenge_response
~~~~~~~~~~~~~~~~~~

type: ``string``

This is a list of token types for which challenge response can
be used during authentication. The list is separated by whitespaces like
*"hotp totp"*.

The policy is needed for token types that can also authenticate with PIN and
OTP in one value, like HOTP and TOTP, when the challenge is triggered by the PIN
in ``/validate/check`` or ``/auth``. Token types that only work with challenge
response (SMS, email, push, WebAuthn, passkey, indexed secret, questionnaire) do
not need it. ``/validate/triggerchallenge`` triggers challenges for all
challenge-capable tokens regardless of this policy.

.. versionadded:: 2.6

.. _policy_disabled_token_types:

disabled_token_types
~~~~~~~~~~~~~~~~~~~~

type: ``string``

This is a list of token types that are not allowed to be used during authentication.
The list is separated by whitespaces like *"hotp totp"*.

``/validate/triggerchallenge`` still creates challenges for these token types, but
an answer to them is rejected.

.. versionadded:: 3.12

.. _policy_force_challenge_response:

force_challenge_response
~~~~~~~~~~~~~~~~~~~~~~~~

.. index:: force_challenge_response

type: ``bool``

When enabled, authentication attempts will be interpreted as either the PIN or the answer to a challenge.
PIN concatenated with OTP can not be used anymore! It only works when authenticating with a username.

Token types that can also authenticate with PIN and OTP in one value (like HOTP and TOTP) must be listed in
:ref:`policy_challenge_response` as well; otherwise users can not authenticate with them at all.

.. versionadded:: 3.10

.. _policy_change_pin_via_validate:

change_pin_via_validate
~~~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

This works with the enrollment policies :ref:`policy_change_pin_first_use` and
:ref:`policy_change_pin_every`. When a PIN change is due, then a successful authentication
will start a challenge response mechanism in which the user is supposed to enter a new
PIN two times.

Only if the user successfully changes the PIN the authentication process is finished
successfully. E.g. if the user enters two different new PINs, the authentication process will fail.

.. note:: The application must support several consecutive challenge response requests.

.. versionadded:: 3.4

.. _policy_resync_via_multichallenge:

resync_via_multichallenge
~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

This policy is based on the global setting :ref:`autosync`.
If *AutoResync* is enabled and this policy is configured, a user can synchronize
their token during authentication via challenge response.

If privacyIDEA realizes that the first given OTP value is within the syncwindow,
a challenge will be presented to the user saying "To resync your token, please enter the next OTP value".
In contrast to the generic AutoResync a user has to enter the token PIN only once.

.. note:: The application must support several consecutive challenge response requests.

.. versionadded:: 3.7

.. _policy_enroll_via_multichallenge:

enroll_via_multichallenge
~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``string``

This policy allows the rollout of tokens during a successful authentication via ``/validate/check``. A user could
authenticate via :ref:`passthru_policy` or using a registration code and right during this authentication session be
asked to enroll a new token.

The policy action can take one of the token types ``hotp``, ``totp``, ``daypassword``, ``push``, ``email``,
``sms``, ``passkey`` or the container type ``smartphone``.

The clients and plugins should make use of this policy transparently and use multiple consecutive
challenges.

A new token is only enrolled if the user has no token of this type assigned yet. Additionally, the policies
:ref:`policy_max_token_per_user` and :ref:`policy_max_token_per_realm` are checked.

.. note:: During this kind of enrollment the policies for *require_description*
   and *verify_enrollment* are not checked.
   Also, currently no token PIN is set.

The different ways of enrollment are defined in detail by the token/container types:

**HOTP and TOTP**

If the policy is set to enroll an HOTP or a TOTP token, after successful authentication a QR code
is displayed to the user. The user has to scan the QR code and will then have to enter the valid OTP value,
generated by the newly scanned/enrolled token. Only after that, the user is finally authenticated.

The enrollment parameters, such as the hash algorithm or time step, are taken from the :ref:`token_config`. The user
policies :ref:`totp-timestep`, :ref:`hotp-hashlib` overwrite the default values from the token configuration.

.. note:: 2step enrollment is currently not supported in this enrollment scenario.

**SMS and Email**

After the first successful authentication step the user is presented with an input field to
enter their email address or mobile number. If done so, the user will then in the final step
have to enter the OTP value sent via email or text message.

.. note:: Enrolling an SMS token or Email token with the email address from the userstore
   can be easily accomplished with a *token event handler*. (See :ref:`event_token_enroll`).

**PUSH**

After the first successful authentication step the user is presented a QR code for push token
enrollment. The user needs to scan the QR code with the privacyIDEA Authenticator App.
If the token is successfully enrolled, the user is logged in without any further interaction.
Since the successful enrollment of the Push token already verifies the presence of the user's smartphone,
there is no additional authentication step anymore during enrollment.

**Smartphone**

A smartphone container is only created if the user has no smartphone container assigned yet, and at least the
registration policy :ref:`container_policy_server_url` is defined. If the user has exactly one smartphone container
that is not registered yet (or still waits for the client), the registration of this container is started again
instead. If the user has a registered smartphone container, or more than one, nothing is enrolled.

After the first successful authentication step, the user is presented with a QR code for smartphone registration. The
user needs to scan the QR code with the privacyIDEA Authenticator App. If the container is registered successfully, the
user is logged in without any further interaction.

When using the :ref:`policy_enroll_via_multichallenge_template` policy, the container is created using the selected
template. This allows the container to be enrolled with multiple tokens at once. Note that for these tokens, all
enrollment policies are checked.

.. versionadded:: 3.8

.. _policy_enroll_via_multichallenge_text:

enroll_via_multichallenge_text
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``string``

There is a default text that is shown to the user, when a token or container is enrolled via multichallenge. The
administrator can change this text using this policy.

.. versionadded:: 3.10

.. _policy_enroll_via_multichallenge_template:

enroll_via_multichallenge_template
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``string``

Select a container template for the smartphone container that is used during enrollment via multichallenge. This means
you can enroll a container and multiple tokens at once. For the tokens, all enrollment policies are checked. If an
error occurs during the enrollment of a token, it fails silently, and the remaining tokens can still be enrolled.

If this policy contains an invalid template name, the container is enrolled anyway, but without a template.

The policy :ref:`policy_enroll_via_multichallenge` has to be set to ``smartphone`` for this policy to take effect.

.. versionadded:: 3.12

.. _policy_enroll_via_multichallenge_optional:

enroll_via_multichallenge_optional
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

If this policy is set, the user can skip the enrollment that the policy
:ref:`policy_enroll_via_multichallenge` starts. The response then contains
``enroll_via_multichallenge_optional`` in the ``detail`` object, and the client can cancel
the enrollment by sending ``cancel_enrollment=1`` together with the ``transaction_id`` to
``/validate/check``. The token or container that was created for the enrollment is removed
and the authentication succeeds.

If this policy is not set, the user has to enroll the token or container. This is the default.

.. versionadded:: 3.12

.. _policy_enroll_via_multichallenge_passkey_offline:

enroll_via_multichallenge_passkey_offline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

If enabled, passkeys that are enrolled with the :ref:`policy_enroll_via_multichallenge` policy are automatically set to be
allowed for offline use and the required offline data is returned with completion of the enrollment.

.. versionadded:: 3.13

.. _reset_all_user_tokens:

reset_all_user_tokens
~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

If a user authenticates successfully the failcounters of all of their tokens
will be reset. This can be important, if using empty PINs or *otppin=None*.

.. versionadded:: 2.15

increase_failcounter_on_challenge
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

The normal behavior is: to not increase the failcounter in case of challenge response.

If this policy is activated the failcounter is increased for each token for which a challenge
is triggered.

The reason for this is that an attacker can no longer trigger an infinite number
of SMS or emails, for example. Because once the maximum failcounter has been reached,
no further challenges for these tokens can be triggered.

.. note:: It should be noted that for all tokens for which a challenge has been generated,
   the failcounter will be incremented. In the case of validate/triggerchallenge, the failcounters are increased for all tokens.
   In some cases it makes sense to use this policy together with :ref:`reset_all_user_tokens`.

.. versionadded:: 3.8

.. _policy_auth_cache:

auth_cache
~~~~~~~~~~

.. index:: AuthCache, Authentication Cache

type: ``string``

The Authentication Cache caches the credentials of a successful authentication
and allows using the same credentials (including the OTP value) for the specified
amount of time and optionally for a specified number of authentications. It is
meant for clients that authenticate again at short intervals - a VPN gateway that
reconnects every hour, for example - which would otherwise need a new OTP each
time.

Only a complete credential that was verified - against a token, a user store, or the
RADIUS server of a ``passthru`` policy - is cached, which means the credential of a
single ``/validate/check`` request. The following successful authentications are
therefore neither stored in the cache nor answered from it:

* **Requests that answer a challenge**, i.e. requests carrying a ``transaction_id`` or
  its legacy alias ``state``. Such a request contains only the response to the
  challenge and not the whole
  credential: the PIN was sent in the request that triggered the challenge, and a
  push token is confirmed on the phone and sends no credential at all. Users of a
  challenge-response token therefore authenticate against the token on every login.
* **Requests without a credential**, i.e. with an empty or absent ``pass``.
* Authentications that succeeded **without checking the presented credential**,
  namely through :ref:`passonnotoken` and :ref:`passonnouser`. Those decisions
  follow from the absence of a token or of a user, so they last only as long as
  that condition and the policy do.

.. warning:: With ``passthru`` pointing to a RADIUS server, the cached credential is
   whatever that server accepted, and for the duration of the policy privacyIDEA
   answers from its own cache instead of asking again. The replay protection and the
   counters of the remote system do not apply during that time. Keep the interval
   short, or do not combine the two.

The time to cache the credentials can be specified like "4h", "5m", "2d", "3s"
(hours, minutes, days, seconds). The number of allowed authentications can be
specified as a whole number, greater than zero.

The notation "4h/5m" means that credentials
are cached for 4 hours, but may only be used again, if every 5 minutes the
authentication occurs. If the authentication with the same credentials would
not occur within 5 minutes, the credentials can not be used anymore.

The notation "2m/3" means that credentials are cached for 2 minutes, but may only be used 3 times
in this timeframe.

.. note:: Cache entries are written to the database table ``authcache``. Expired
   entries of a user are deleted on that user's next authentication that is not
   answered from the cache: all entries older than the first interval of the policy
   or with their number of uses spent, plus the entries for the presented password.
   Entries that only exceeded the idle interval (the second value of e.g. ``4h/5m``)
   and belong to another password stay. These and the entries of users who do not
   authenticate again need to be deleted from this table by running::

      pi-manage config authcache cleanup

   which deletes the entries no active ``auth_cache`` policy accepts any more: those
   not used for longer than the most generous policy allows, or all of them if there
   is no such policy. With ``4h/5m`` that is every entry unused for 5 minutes, with
   ``2d`` every entry unused for two days. The Ubuntu packages and the Docker image run
   this daily, see :ref:`cleanup_jobs`.

   To delete by a fixed age instead, pass ``--minutes``::

      pi-manage config authcache cleanup --minutes 300

   deletes all authentication cache entries whose last authentication happened more
   than 5 hours ago.

.. note:: With :ref:`redis_auth_cache` enabled, cache entries live in Redis
   instead of the ``authcache`` table. They then carry the lifetime this policy
   grants and expire on their own, and the authentication path stops writing to
   the database - except while Redis cannot be reached. The entries written then
   are only removed by the cleanup command, so keep its cron job.

.. note:: The AuthCache only works for user authentication, not for
   authentication with serials.

.. versionadded:: 2.20

.. _policy_push_text_on_mobile:

push_text_on_mobile
~~~~~~~~~~~~~~~~~~~

.. index:: push token, push gateway

type: ``string``

This is the text that should be displayed on the push notification
during the login process with a :ref:`push_token`.
You can choose different texts for different users or IP addresses.
This way you could customize push notifications for different applications.

The text can contain the following tags, that will be filled:

  * {serial} the serial number of the token.
  * {user} the given name of the token owner.
  * {givenname} the given name of the token owner.
  * {surname} the surname of the token owner.
  * {username} the loginname of the token owner.
  * {userrealm} the realm of the token owner.
  * {recipient_givenname} the given name of the token owner.
  * {recipient_surname} the surname of the token owner.
  * {tokentype} the type of the token, which is always *push*.
  * {time} the current server time in the format HH:MM:SS.
  * {date} the current server date in the format YYYY-MM-DD.
  * {client_ip} the IP address of the client that triggered the challenge.
  * {ua_browser} the name of the application that triggered the challenge, taken from its
    user agent, like *privacyidea-keycloak*. Browsers report *Mozilla* here, use
    {ua_string} to get the complete user agent of a browser.
  * {ua_string} the complete user agent of the client that triggered the challenge.
  * {action} the endpoint that triggered the challenge, like */validate/check*.
  * {url} the base URL of the privacyIDEA server. This requires ``PI_BASE_URL`` to be
    configured in :ref:`cfgfile`.

.. note:: A tag that does not exist at all - like the {otp} of :ref:`emailtext`, which a
   push notification never contains - can not be filled. The complete text is discarded in
   this case and the default text *Do you want to confirm the login?* is displayed instead.

   Tags that exist but are not filled during an authentication with a push token are
   *not* replaced by the default text. They are inserted as an empty value, so the text is
   displayed with a gap. This applies to *{challenge}*, which is only filled for tokens
   that receive transaction data in the *challenge* parameter of the authentication request
   (see :ref:`ocra_token`), and to the tags of the other policies like
   {tokendescription}, {registrationcode} or {pin}.

.. note:: The tags {client_ip}, {ua_browser}, {ua_string} and {action} describe the
   client that triggered the challenge. The text is rendered when the challenge is
   triggered and stored with it, so these tags are also filled when the smartphone
   fetches the challenge by polling. Only challenges of an enrollment session store no
   text; for them the text is rendered when the smartphone polls, and the four tags are
   empty. The tags of the token owner are filled in all cases.

.. versionadded:: 3.0

.. _policy_push_title_on_mobile:

push_title_on_mobile
~~~~~~~~~~~~~~~~~~~~

.. index:: push token, push gateway

type: ``string``

This is the title of the push notification that is displayed
on the user's smartphone during the login process with
a :ref:`push_token`.

.. note:: In contrast to :ref:`policy_push_text_on_mobile`, tags are not replaced in
   the title.

.. versionadded:: 3.0

.. _policy_push_wait:

push_wait
~~~~~~~~~

.. index:: push token, push direct authentication

type: ``integer``

This can be set to a number of seconds. If this is set, the authentication
with a push token is only performed via one request to ``/validate/check``.
The HTTP request to ``/validate/check`` will wait up to this number of
seconds and check, if the push challenge was confirmed by the user.

This way push tokens can be used with any non-push-capable applications.

Sensible numbers might be 10 or 20 seconds.

.. note:: This behavior can interfere with other tokentypes. A request that
   sends only the PIN of the push token waits for this number of seconds, even
   if the user meant to use another token. A request that another token
   authenticates (e.g. PIN and OTP of an HOTP token) returns at once, since push
   tokens are checked last.

.. warning:: Using simple webserver setups like Apache WSGI this actually
   can block all available worker threads, which will cause privacyIDEA
   to become unresponsive if the number of open PUSH challenges exceeds
   the number of available worker threads!

.. versionadded:: 3.1

.. _policy_push_code_to_phone:

push_code_to_phone
~~~~~~~~~~~~~~~~~~

.. index:: push token

type: ``bool``

Alternative mode for push token that uses a 2-step confirmation process:

1. A push notification is sent to the smartphone (as in standard mode). The smartphone app
   confirms the authentication by signing the challenge.
2. After the smartphone confirms, a short display code is generated and shown on the smartphone.
   The user must enter this code into the login prompt on the client.

The display code is only used for synchronization — it lets the client know the smartphone has
completed its confirmation. The security lies in the smartphone's cryptographic confirmation,
not in the code itself.

If the wrong display code is entered, the failcount of the push token will be increased,
in contrast to the standard behavior.

If either :ref:`policy_push_require_presence` or :ref:`policy_push_wait` is active,
this policy will not be in effect.

.. versionadded:: 3.13

.. _policy_push_code_to_phone_message:

push_code_to_phone_message
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. index:: push token

type: ``string``

The message that the smartphone shows above the display code when
:ref:`policy_push_code_to_phone` is active. The default is *Enter the code to log in*.

.. versionadded:: 3.13

.. _policy_push_challenge_text:

push_challenge_text
~~~~~~~~~~~~~~~~~~~

.. index:: push token

type: ``string``

An alternative message to display in the application to tell the user to confirm the authentication on his mobile
device with the PUSH token.

This can be used to display different messages, if the user e.g. has different token types that triggered a challenge
or in combination with :ref:`policy_push_code_to_phone` to tell the user in more detail what to do.

If this policy is not set, the PUSH token falls back to the generic :ref:`policy_challenge_text` policy and finally
to the built-in default text.

.. versionadded:: 3.13.1

.. _policy_push_require_presence:

push_require_presence
~~~~~~~~~~~~~~~~~~~~~

.. index:: push token

type: ``bool``

If this policy is set, the login window will display a message like
``Please confirm login by pressing Button 'C' on your smartphone``.

The push notification on the smartphone will show several buttons. One is labeled ``C``.

The user then can confirm the login by pressing this button. Pressing another button does not confirm
the login. The challenge stays valid and can still be confirmed with the right button until it expires.

If this policy is not set, the PUSH message will simply ask the user if they
want to log in.

.. important:: This policy is incompatible with the policy :ref:`policy_push_wait`
   since the correct presence option can not be passed back to the calling client.
   If the ``push_wait`` policy is also set, ``push_require_presence`` will be disabled.

.. note:: This mechanism allows login scenarios where the user in front of the login window and the
   person owning the smartphone are two different persons. In this case they will have to communicate
   for a successful login.

.. versionadded:: 3.10

.. _policy_push_presence_options:

push_presence_options
~~~~~~~~~~~~~~~~~~~~~

.. index:: push token

type: ``string``

Only takes effect if :ref:`policy_push_require_presence` is set.

This policy configures the buttons that are displayed in the push notification on the smartphone.

The following options are available:

``ALPHABETIC``

    The buttons are labeled with the letters A to Z.

``NUMERIC``

    The buttons are labeled with the numbers 00 to 99.

``CUSTOM``

    The buttons are labeled with the characters defined in the policy :ref:`policy_push_presence_custom_options`.
    If the :ref:`policy_push_presence_custom_options` policy is not set, the fallback is to use the ``ALPHABETIC`` options.

The default is to use the ``ALPHABETIC`` options.

.. versionadded:: 3.10

.. _policy_push_presence_custom_options:

push_presence_custom_options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. index:: push token

type: ``string``

Only takes effect if :ref:`policy_push_presence_options` is set to ``CUSTOM``.

This policy configures the buttons that can be displayed in the push notification on the smartphone.
To set the number of buttons, see :ref:`push_presence_num_options`.

The string must contain at least 2 options and should be unique.

The options are separated by ":" e.g. ``01:02:03:1A:1B:1C``

.. versionadded:: 3.10

.. _push_presence_num_options:

push_presence_num_options
~~~~~~~~~~~~~~~~~~~~~~~~~

.. index:: push token

type: ``integer``

Only takes effect if :ref:`policy_push_require_presence` is set.

This policy configures the number of buttons that are displayed in the push notification on the smartphone.
Allowed are 2 to 10 buttons, the default is 3. Any other value uses the default of 3. If fewer options are available
(custom options), that number of buttons is shown.

.. versionadded:: 3.10

.. _policy_auth_push_allow_poll:

push_allow_polling
~~~~~~~~~~~~~~~~~~

.. index:: push token

type: ``string``

This policy configures if push tokens are allowed to poll the server for open
challenges (e.g. when the third-party push service is unavailable or
unreliable).

The following options are available:

``allow``

    *Allow* push tokens to poll for challenges.

``deny``

    *Deny* push tokens to poll for challenges. This basically returns a ``403``
    error when requesting the poll endpoint.

``token``

    *Allow* / *Deny* polling based on the individual token. The tokeninfo key
    ``polling_allowed`` is checked. If the value evaluates to ``False``, polling
    is denied for this token. If it evaluates to ``True`` or is not set, polling
    is allowed for this token.

The default is to ``allow`` polling

.. versionadded:: 3.4

.. _policy_push_ssl_verify_auth:

push_ssl_verify
~~~~~~~~~~~~~~~

type: ``string``

allowed values: ``0``, ``1``

The smartphone needs to verify the SSL certificate of the privacyIDEA server during
the authentication with push tokens. By default, the verification is enabled. To disable
verification during enrollment, see :ref:`policy_push_ssl_verify_enrollment`.

.. versionadded:: 3.0

.. _policy_challenge_text:
.. _challenge-text:
.. _challenge-text-footer:
.. _challenge-text-header:

challenge_text, challenge_text_header, challenge_text_footer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. index:: Challenge Text Policy

type: ``string``

Using these policies the administrator can modify the challenge texts. The
action *challenge_text* changes the challenge text of the token types that use
the generic challenge (e.g. HOTP, TOTP, day password) and of push tokens without
a :ref:`policy_push_challenge_text`. SMS, email, indexed secret, WebAuthn and
passkey tokens only use their own actions (``sms_challenge_text``,
``email_challenge_text``, ``indexedsecret_challenge_text``,
``webauthn_challenge_text``, ``passkey_challenge_text``).

If *challenge_text_header* is set, the message of a challenge response consists
of the header, the texts of all triggered tokens and the footer - also if only
one token was triggered. Without a header, the texts of several tokens are
joined with ", ". Duplicate challenge texts are reduced to one in both cases.

The *challenge_text_header* and *challenge_text_footer* may contain HTML.
If the *challenge_text_header* ends with an ``<ul>`` or ``<ol>``, then
all the challenge texts are formatted as an unordered or ordered list.
In this case the *challenge_text_footer* also should contain the closing
tag.

.. note:: The footer will only be used, if the header is also set.

.. note:: Starting with version 3.11 the ``challenge_text`` can contain tags similar to the
    policy :ref:`emailtext`:

    * {serial} the serial number of the token.
    * {user} the given name of the token owner.
    * {givenname} the given name of the token owner.
    * {surname} the surname of the token owner.
    * {username} the loginname of the token owner.
    * {userrealm} the realm of the token owner.
    * {tokentype} the type of the token.
    * {time} the current server time in the format HH:MM:SS.
    * {date} the current server date in the format YYYY-MM-DD.
    * {phone} the phone number from the challenge in case of sms token.
    * {phone_redacted} the phone number from the challenge in case of sms token in redacted form.
    * {email} email address from the challenge in case of email token.
    * {email_redacted} email address from the challenge in case of email token in redacted form.
    * {presence_answer} only for push token and only if require_presence is enabled.

    {phone}, {phone_redacted}, {email} and {email_redacted} take effect in
    ``sms_challenge_text`` and ``email_challenge_text``, which accept the same tags
    as ``challenge_text``.

.. versionadded:: 2.23 ``challenge_text``

.. versionadded:: 3.0 ``challenge_text_header`` and ``challenge_text_footer``

.. _policy_indexedsecret:

indexedsecret_challenge_text
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``string``

The Indexed Secret Token asks the user to provide the characters of the
secret from certain positions. The default text is:

*Please enter the positions 3,1,6,7 from your secret.*

with *3,1,6,7* being the positions of the characters, the user is supposed to
enter. This text can be changed with this policy setting.
The text needs to contain the python formatting tag *{0!s}* which will
be replaced with the list of the requested positions.

For more details of this token type see :ref:`indexedsecret_token`.

.. versionadded:: 3.3

.. _policy_webauthn_challenge_text_auth:

webauthn_challenge_text
~~~~~~~~~~~~~~~~~~~~~~~

type: ``string``

Use an alternate challenge text for requesting the user to confirm with
their WebAuthn token during authentication. This might be different from the
challenge text received during enrollment
(see :ref:`policy_webauthn_challenge_text_enrollment`).

.. versionadded:: 3.3

.. _policy_passkey_challenge_text:

passkey_challenge_text
~~~~~~~~~~~~~~~~~~~~~~

type: ``string``

Use an alternate challenge text for requesting the user to authenticate with
their passkey. The default text is *Please authenticate with your passkey!*. The text is
used for the challenge of ``/validate/initialize`` and for a challenge that is triggered
for a passkey token with :ref:`policy_passkey_trigger_by_pin`.

.. versionadded:: 3.11

.. _email-challenge-text:
.. _sms-challenge-text:

email_challenge_text, sms_challenge_text
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``string``

With these actions the administrator may set alternative challenge texts for email
and SMS tokens.

.. versionadded:: 2.23

.. _policy_indexedsecret_count:

indexedsecret_count
~~~~~~~~~~~~~~~~~~~

type: ``integer``

The Indexed Secret Token asks the user for a number of characters from
a shared secret. The default number to ask is 2.

The number of requested positions can be changed using this policy.

.. versionadded:: 3.3

.. _policy_webauthn_authn_allowed_transports:

webauthn_allowed_transports
~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``string``

This action sets the transports that are passed to the client as a hint for
contacting the authenticator during authentication. Browsers use it to decide how
to look for the authenticator, but privacyIDEA does not verify which transport was
used, so the policy does not prevent the use of other transports. The values of
all matching policies are combined. The transports are declared as a
space-separated list.

The default is to allow all transports (equivalent to a value of ``usb ble nfc
internal``).

.. versionadded:: 3.3

.. _policy_webauthn_authn_timeout:

webauthn_timeout
~~~~~~~~~~~~~~~~

type: ``integer``

This action sets the time in seconds the user has to confirm an authentication
request on their WebAuthn authenticator.

This is a client-side setting, that governs how long the client waits for the
authenticator. It is independent of the time for which a challenge for a
challenge response token is valid, which is governed by the server and
controlled by a separate setting. This means, that if you want to increase this
timeout beyond two minutes, you will have to also increase the challenge
validity time, as documented in :ref:`challenge_validity_time`.

This setting is a hint. It is interpreted by the client and may be adjusted by
an arbitrary amount in either direction, or even ignored entirely.

The default timeout is 60 seconds.

.. note:: If you set this policy you may also want to set
    :ref:`policy_webauthn_enroll_timeout`.

.. versionadded:: 3.3

.. _policy_webauthn_authn_user_verification_requirement:

webauthn_user_verification_requirement
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``string``

This action configures whether the user's identity should be checked when
authenticating with a WebAuthn token. If this is set to required, any user
signing in with their WebAuthn token will have to provide some form of
verification. This might be biometric identification or knowledge-based,
depending on the authenticator used.

This defaults to ``preferred``, meaning user verification will be performed if
supported by the token. Allowed values are ``required``, ``preferred`` and
``discouraged``.

The policy also sets the user verification for passkey authentication through
``/validate/initialize`` and :ref:`policy_passkey_trigger_by_pin` (see
:ref:`passkey`).

.. note:: User verification is different from user presence checking. The
    presence of a user will always be confirmed (by asking the user to take
    action on the token, which is usually done by tapping a button on the
    authenticator). User verification goes beyond this by ascertaining that the
    user is indeed the same user each time (for example through biometric
    means). Only set this to ``required`` if you know for a fact, that you have
    authenticators, that actually support some form of user verification.

.. note:: If you configure this, you will likely also want to configure
    :ref:`policy_webauthn_enroll_user_verification_requirement`.

.. note:: A login to the WebUI with a passkey always requires user
    verification, whatever this policy says. The same applies to a WebAuthn
    token used to log in to the WebUI without a username, since the token is
    then the only factor.

.. note:: When this is not set to ``required`` and a user has multiple
    discoverable credentials for the same relying party on a single
    authenticator (typical for external FIDO2 security keys), the browser's
    account picker may show generic placeholder labels instead of the user
    names. The authenticator only releases the credentials'
    ``user.name`` / ``user.displayName`` fields after user verification.
    See :ref:`passkey` for more detail.

.. versionadded:: 3.3

question_number
~~~~~~~~~~~~~~~

type: ``integer``

The questionnaire token can ask more than one question during one authentication process.
It will ask the first question, verify the answer, ask the next question and verify the answer.
This policy setting defines how many questions the user needs to answer.

The default amount to ask is 1.

.. note:: A question will be asked only once, unless the policy requires more questions to be asked,
   than the token has available answers.

.. versionadded:: 3.5

preferred_client_mode
~~~~~~~~~~~~~~~~~~~~~

type: ``string``

This action sets a list of the client modes in the preferred order. You can enter the different client
modes in the order you like. For example: "interactive webauthn poll". The client you are using
will show you the correct login for your preferred client mode. For example, with the list
"webauthn interactive poll" and a WebAuthn and an HOTP token in the multi-challenge, the client shows the
WebAuthn login. With the default list it shows the input field for the HOTP token.

The default list is "interactive webauthn poll".

.. versionadded:: 3.8

client_mode_per_user
~~~~~~~~~~~~~~~~~~~~

type: ``bool``

If this policy is set, the token type recently used during a successful authentication is stored per user and
application. For the next authentication, the last used token type is used to identify the preferred client mode. The
client you are using will show the correct login for the user's preferred client mode. For example, if the user last
used a TOTP token to authenticate, an input field to enter the OTP value is displayed.

This policy takes precedence over the ``preferred_client_mode`` policy.

.. versionadded:: 3.12

.. _policy_passkey_trigger_by_pin:

passkey_trigger_by_pin
~~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

If this policy is set, the passkey token can be triggered with its PIN or via the /validate/triggerchallenge endpoint.
For privacyIDEA plugins, enabling this is generally not recommended, unless stated otherwise in a plugin documentation.
It is advised to use a condition with this policy, for example on the user-agent.

.. note:: Make sure the user only has a WebAuthn **or** Passkey token assigned when using this policy.
    Triggering both types at the same time will probably result in a failed authentication: each type gets its own
    random challenge in the same transaction, so a client that signs one challenge can not answer the other.

.. versionadded:: 3.11.1

.. _policy_passkey_authn_allowed_authenticator_device_types:

passkey_allowed_authenticator_device_types
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``string``

Only allow authentication with passkeys that report one of the given device types, as a space-separated list of
``single_device`` and ``multi_device``. See :ref:`passkey_device_type` for what the two types mean. If several
policies match, the values of all of them are allowed. Any other value matches no passkey, so every passkey
authentication fails. If the policy is not set, both types are accepted.

The device type is taken from each authentication response, not from the value stored at enrollment. The policy
therefore also applies to passkeys that were enrolled before it was set: their users can no longer log in with
them. To find the passkeys that a policy would refuse, list them with
``GET /token/?type=passkey&infokey=device_type&infovalue=multi_device`` (or ``single_device``).

This policy is independent of the
:ref:`enrollment policy of the same name <policy_passkey_enroll_allowed_authenticator_device_types>`. For example,
you can allow the enrollment of both types but only allow ``single_device`` passkeys for a specific realm.

.. warning:: The device type is reported by the authenticator and is not backed by a verified attestation. The
    policy keeps out honest synced passkeys, but not an authenticator that reports a wrong device type. See
    :ref:`passkey_device_type`.

.. versionadded:: 3.14

.. _policy_passkey_enforce_user_handle:

passkey_enforce_user_handle
~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

When a passkey is enrolled, privacyIDEA passes the FIDO2 user ID of the user to the authenticator. The same ID is
used for all passkeys of a user. The authenticator stores it with the credential and returns it as ``userHandle``
on every authentication. By default, privacyIDEA ignores the ``userHandle`` and identifies the user only by the
credential ID and the user the passkey token is assigned to. If a passkey token is unassigned and then assigned to
a different user, whoever holds the passkey can log in as that user.

If this policy is set, the ``userHandle`` must match the FIDO2 user ID recorded for the user the passkey token is
assigned to, otherwise the authentication fails. This detects a passkey that was reassigned to a different user.

.. note:: A passkey can no longer authenticate if no FIDO2 user ID is recorded for its user.

.. note:: Unlike the device type, the ``userHandle`` is not covered by the signature of the authenticator. A
    client that deliberately sends a forged value is not detected. The policy protects against a passkey being
    reassigned by mistake, not against a manipulated client.

.. versionadded:: 3.14

.. _policy_hide_specific_error_message:

hide_specific_error_message
~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

If this policy is set, failed authentications will return a generic "Authentication failed" message.
Other information is also removed from the ``detail`` object of the response.

.. note:: To additionally return a uniform HTTP status code for failed authentications, see
    the :ref:`policies_hardening` scope policy ``hide_auth_error_status``.

.. note:: This policy does **not** mask an error message configured for
    :ref:`conditional_access`. Such a message exists only because an
    administrator wrote it on a stage or enabled
    :ref:`policy_show_default_ca_error_message`, so it survives while the rest
    of the ``detail`` object is still collapsed. See
    :ref:`conditional_access_error_messages_masking`.

.. versionadded:: 3.13

.. _policy_remember_device:

remember_device
~~~~~~~~~~~~~~~

type: ``bool``

Allow an API client to obtain a persistent "remember this device" cookie on a
successful authentication at :http:post:`/validate/check` (the client must send
``request_persistent_cookie=1``). The feature is off by default and requires the
request to be made by an identified API client (the ``X-API-Key`` header, see
the :ref:`policy_api_client_list` admin action): without a client, no cookie is
issued and the recognition endpoint returns ``401``.

The cookie holds only a rotating ``series_id:counter`` token (never the API key)
and is later checked at :http:post:`/validate/remember_device`, which reports
whether the device is recognized so the calling client can decide to skip the
second factor. Recognition is **not** an authentication and does not by itself
grant access.

.. note:: :http:get:`/validate/capabilities` reports whether this policy makes
    the feature available to a client. That is a *client-level* answer; whether
    it applies to a specific user is decided at issuance and recognition, so a
    policy scoped to specific users/realms may still report ``true`` to the
    client.

.. versionadded:: 3.14

.. _policy_remember_device_validity:

remember_device_validity
~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``integer``

How many days a "remember this device" cookie stays valid. If unset, the default
is 30 days. Because it is a policy value, it can be scoped per realm or user with
the usual conditions - for example a shorter lifetime for administrators than for
regular users. The lifetime is fixed when the cookie is issued; recognition
rotates the token but does not extend the expiry.

.. versionadded:: 3.14

.. _policy_remember_device_max_devices:

remember_device_max_devices
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``integer``

The maximum number of remembered devices a single user may have per API client.
Each opt-in on ``/validate/check`` mints a **new** device series (the server
cannot reliably tell one client's devices apart, and a user legitimately having
several devices is normal), so a client that opts in on every login would
accumulate rows until they expire. Set this to cap that: once the user already
has this many *live* devices for the client, further opt-ins issue no new cookie
and the existing devices keep working. Unset or ``0`` means unlimited (the
default). Scope it per realm/user like the other conditions.

.. versionadded:: 3.14

.. rubric:: Footnotes

.. [#pythonre] https://docs.python.org/3/library/re.html
