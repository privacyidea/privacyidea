.. _authorization_policies:

Authorization policies
-----------------------

.. index:: authorization policies

The scope *authorization* provides means to define
what should happen if a user proved his identity
and authenticated successfully.

Authorization policies take the realm, the user
and the client into account.

Technically the authorization policies apply
to the :ref:`rest_validate` and are checked
using :ref:`code_policy` and
:ref:`policy_decorators`.

The following actions are available in the scope 
*authorization*:

.. _tokentype_policy:

tokentype
~~~~~~~~~

type: string

Users will only be authorized with this very tokentype.
The string can hold a space separated list of
case sensitive tokentypes. It should look like:

    hotp totp spass


This is checked after the authentication request, so that a valid OTP value
is wasted, so that it can not be used, even if the user was not authorized at
this request

.. note:: Combining this with the client IP
   you can use this to allow remote access to 
   sensitive areas only with one special token type
   while allowing access to less sensitive areas
   with other token types.

serial
~~~~~~

type: string

Users will only be authorized with the serial number.
The string can hold a regular expression as serial
number.

This is checked after the authentication request, so that a valid OTP value
is wasted, so that it can not be used, even if the user was not authorized at
this request

.. note:: Combining this with the client IP
   you can use this to allow remote access to 
   sensitive areas only with hardware tokens
   like the Yubikey, while allowing access
   to less secure areas also with a Google
   Authenticator.

setrealm
~~~~~~~~

type: string

This policy is checked before the user authenticates.
The realm of the user matching this policy will be set to
the realm in this action. 

.. note:: This can be used if the user can not pass his
   realm when authenticating at a certain client, but
   the realm needs to be available during authentication
   since the user is not located in the default realm.

.. _policy_no_detail_on_success:

no_detail_on_success
~~~~~~~~~~~~~~~~~~~~

type: bool

Usually an authentication response returns additional information like the
serial number of the token that was used to authenticate or the reason why
the authentication request failed.

If this action is set and the user authenticated successfully
this additional information will not be returned.

.. _policy_no_detail_on_fail:

no_detail_on_fail
~~~~~~~~~~~~~~~~~

type: bool

Usually an authentication response returns additional information like the
serial number of the token that was used to authenticate or the reason why
the authentication request failed.

If this action is set and the user fails to authenticate
this additional information will not be returned.

.. _policy_api_key:

api_key_required
~~~~~~~~~~~~~~~~

type: bool

This policy is checked *before* the user is validated.

You can create an API key, that needs to be passed to use the validate API.
If an API key is required, but no key is passed, the authentication request
will not be processed. This is used to avoid denial of service attacks by a
rogue user sending arbitrary requests, which could result in the token of a
user being locked.

You can also define a policy with certain IP addresses without issuing API
keys. This would result in "blocking" those IP addresses from using the
*validate* endpoint.

You can issue API keys like this::

   pi-manage api createtoken -r validate

The API key (Authorization token) which is generated is valid for 365 days.

The authorization token has to be used as described in :ref:`rest_auth`.

.. _policy_auth_max_success:

auth_max_success
~~~~~~~~~~~~~~~~

type: string

Here you can specify how many successful authentication requests a user is
allowed to perform during a given time.
If this value is exceeded, the authentication attempt is canceled.

Specify the value like ``2/5m`` meaning 2 successful authentication requests
per 5 minutes. If during the last 5 minutes 2 successful authentications were
performed the authentication request is discarded. The used OTP value is
invalidated.

Allowed time specifiers are *s* (second), *m* (minute) and *h* (hour).

.. _policy_auth_max_fail:

auth_max_fail
~~~~~~~~~~~~~

type: string

Here you can specify how many failed authentication requests a user is
allowed to perform during a given time.

If this value is exceeded, authentication is not possible anymore. The user
will have to wait.

If this policy is not defined, the normal behaviour of the failcounter
applies. (see :ref:`failcounter`)

Specify the value like ``2/1m`` meaning 2 successful authentication requests
per minute. If during the last 5 minutes 2 successful authentications were
performed the authentication request is discarded. The used OTP value is
invalidated.

Allowed time specifiers are *s* (second), *m* (minute) and *h* (hour).

last_auth
~~~~~~~~~

type: string

You can define if an authentication should fail, if the token was not
successfully used for a certain time.

Specify a value like ``12h``, ``123d`` or ``2y`` to disallow authentication,
if the token was not successfully used for 12 hours, 123 days or 2 years.

The date of the last successful authentication is store in the `tokeninfo`
field of a token and denoted in UTC.

u2f_req
~~~~~~~

type: string

Only the specified U2F devices are authorized to authenticate.
The administrator can specify the action like this:

    u2f_req=subject/.*Yubico.*/

The the key word can be "subject", "issuer" or "serial". Followed by a
regular expression. During registration of the U2F device the information
from the attestation certificate is stored in the tokeninfo.
Only if the regexp matches this value, the authentication with such U2F
device is authorized.

.. _policy_add_user_in_response:

add_user_in_response
~~~~~~~~~~~~~~~~~~~~

type: bool

In case of a successful authentication additional user information is added
to the response. A dictionary containing user information is added in
``detail->user``.
