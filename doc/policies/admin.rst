.. _admin_policies:

Admin policies
--------------

.. index:: admin policies, superuser realm, admin realm, help desk

Admin policies are used to regulate the actions that administrators are
allowed to do.
Technically admin policies control the use of the REST
API :ref:`rest_token`, :ref:`rest_system`, :ref:`rest_realm` and
:ref:`rest_resolver`.

Admin policies are implemented as decorators in :ref:`code_policy` and
:ref:`policy_decorators`.

The ``user`` in the admin policies refers to the name of the administrator.

Starting with privacyIDEA 2.4 admin policies can also store a field "admin
realm". This is used, if you define realms to be superuser realms. See
:ref:`cfgfile` for information how to do this.

This way it is easy to define administrative rights for big groups of
administrative users like help desk users in the IT department.

.. figure:: admin_policies.png
   :width: 500

   *Admin scope provides and additional field 'admin realm'.*

All administrative actions also refer to the defined user realm. Meaning
an administrator may have many rights in one user realm and only a few
rights in another realm.

Creating a policy with ``scope:admin``, ``user:frank``, ``action:enable``
and ``realm:sales``
means that the administrator *frank* is allowed to enable tokens in the
realm *sales*. 

.. note:: As long as no admin policy is defined all administrators
   are allowed to do everything.

The following actions are available in the scope
*admin*:

init
~~~~

type: bool

There are ``init`` actions per token type. Thus you can 
create policy that allow an administrator to enroll 
SMS tokens but not to enroll HMAC tokens.

enable
~~~~~~

type: bool

The ``enable`` action allows the administrator to activate 
disabled tokens.

disable
~~~~~~~

type: bool

Tokens can be enabled and disabled. Disabled tokens can not be
used to authenticate. The ``disable`` action allows the 
administrator to disable tokens.

revoke
~~~~~~

type: bool

Tokens can be revoked. Usually this means the token is disabled and locked.
A locked token can not be modified anymore. It can only be deleted.

Certain token types like *certificate* may define special actions when
revoking a token.

set
~~~

type: bool

Tokens can have additional token information, which can be
viewed in the :ref:`token_details`.

If the ``set`` action is defined, the administrator allowed
to set those token information.

setOTPPIN
~~~~~~~~~

type: bool

If the ``setOTPPIN`` action is defined, the administrator
is allowed to set the OTP PIN of a token.

setMOTPPIN
~~~~~~~~~~

type: bool

If the ``setMOTPPIN`` action is defined,  the administrator
is allowed to set the mOTP PIN of an mOTP token.

resync
~~~~~~

type: bool

If the ``resync`` action is defined, the administrator is
allowed to resynchronize a token.

assign
~~~~~~

type: bool

If the ``assign`` action is defined, the administrator is
allowed to assign a token to a user. This is used for 
assigning an existing token to a user but also to 
enroll a new token to a user.

Without this action, the administrator can not create 
a connection (assignment) between a user and a token.

unassign
~~~~~~~~

type: bool

If the ``unassign`` action is defined, the administrator
is allowed to unassign tokens from a user. I.e. the 
administrator can remove the link between the token 
and the user. The token still continues to exist in the system.

import
~~~~~~

type: bool

If the ``import`` action is defined, the administrator is 
allowed to import token seeds from a token file, thus
creating many new token objects in the systems database.

remove
~~~~~~

type: bool

If the ``remove`` action is defined, the administrator is
allowed to delete a token from the system. 

.. note:: If a token is removed, it can not be recovered.

.. note:: All audit entries of this token still exist in the audit log.

userlist
~~~~~~~~

type: bool

If the ``userlist`` action is defined, the administrator is 
allowed to view the user list in a realm.
An administrator might not be allowed to list the users, if
he should only work with tokens, but not see all users at once.

.. note:: If an administrator has any right in a realm, the administrator
   is also allowed to view the token list.

checkstatus
~~~~~~~~~~~

type: bool

If the ``checkstatus`` action is defined, the administrator is 
allowed to check the status of open challenge requests.

manageToken
~~~~~~~~~~~

type: bool

If the ``manageToken`` action is defined, the administrator is allowed
to manage the realms of a token.

.. index:: realm administrator

A token may be located in multiple realms. This can be interesting if
you have a pool of spare tokens and several realms but want to 
make the spare tokens available to several realm administrators.
(Administrators, who have only rights in one realm)

Then all administrators can see these tokens and assign the tokens.
But as soon as the token is assigned to a user in one realm, the
administrator of another realm can not manage the token anymore.

getserial
~~~~~~~~~

type: bool

.. index:: getserial

If the ``getserial`` action is defined, the administrator is
allowed to calculate the token serial number for a given OTP
value.


getrandom
~~~~~~~~~

type: bool

.. index:: getrandom

The ``getrandom`` action allows the administrator to retrieve random
keys from the endpoint *getrandom*. This is an endpoint in :ref:`rest_system`.

*getrandom* can be used by the client, if the client has no reliable random
number generator. Creating API keys for the Yubico Validation Protocol uses
this endpoint.

getchallenges
~~~~~~~~~~~~~

type: bool

.. index:: getchallenges

This policy allows the administrator to retrieve a list of active challenges
of a challenge response tokens. The administrator can view these challenges
in the web UI.

.. _lost_token:

losttoken
~~~~~~~~~

type: bool

If the ``losttoken`` action is defined, the administrator is
allowed to perform the lost token process.

To only perform the lost token process the actions ``copytokenuser``
and ``copytokenpin`` are not necessary!


adduser
~~~~~~~

type: bool

.. index:: Add User, Users

If the ``adduser`` action is defined, the administrator is allowed to add
users to a user store.

.. note:: The user store still must be defined as editable, otherwise no
   users can be added, edited or deleted.

updateuser
~~~~~~~~~~

.. index:: Edit User

type: bool

If the ``updateuser`` action is defined, the administrator is allowed to edit
users in the user store.

deleteuser
~~~~~~~~~~

.. index:: Delete User

type: bool

If the ``deleteuser`` action is defined, the administrator is allowed to
delete an existing user from the user store.


copytokenuser
~~~~~~~~~~~~~

**(TODO)** Not yet migrated.

type: bool

If the ``copytokenuser`` action is defined, the administrator is
allowed to copy the user assignment of one token to another.

This functionality is also used during the lost token process.
But you only need to define this action, if the administrator
should be able to perform this task manually.

copytokenpin
~~~~~~~~~~~~

**(TODO)** Not yet migrated.

type: bool

If the ``copytokenpin`` action is defined, the administrator is
allowed to copy the OTP PIN from one token to another without
knowing the PIN.

This functionality is also used during the lost token process.
But you only need to define this action, if the administrator
should be able to perform this task manually.

getotp
~~~~~~

**(TODO)** Not yet migrated.

type: bool

If the ``getserial`` action is defined, the administrator is
allowed to retrieve OTP values for a given token.

