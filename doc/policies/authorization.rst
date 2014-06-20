.. _authorization_policies:

Authorization policies
-----------------------

.. index:: authorization policies

The scope *authorization* provides means to define
what should happen if a user prooved his identity 
and authenticated successfully.
 
Authorization policies take the realm, the user
and the client into account.

Technically the authorization policies apply
to the :ref:`validate_controller`.

The following actions are available in the scope 
*authorization*:

authorize
~~~~~~~~~

type: bool

If this is set, only this realm will be authorized from the 
certain client IP.

As long as not policy *action: authorize* is set, all
users and realms from all client IPs will be allowed.

.. note:: If you start to use the authorize-action you will
   need to define all authorizations for all realms and clients.

tokentype
~~~~~~~~~

type: string

Users will only be auhorized with this very tokentype. 
The string can hold a comma seperated list of 
case insensitive tokentypes.

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

detail_on_success
~~~~~~~~~~~~~~~~~

type: bool

If this action is set and the user authenticated successfully
additional information will be returned:
The realm, the username, the tokentype and the serial number.

detail_on_fail
~~~~~~~~~~~~~~

type: bool

If this action is set and the user failed to authenticate
additional information about the error will be returned.

