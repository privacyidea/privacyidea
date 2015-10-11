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

tokentype
~~~~~~~~~

type: string

Users will only be authorized with this very tokentype.
The string can hold a comma separated list of
case insensitive tokentypes.

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

