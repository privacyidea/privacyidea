.. _machines:

Client machines
===============

.. index:: machines, client machines

privacyIDEA lets you define Machine Resolvers to connect to existing machine
stores. The idea is for users to be able to authenticate
on those client machines.
Not in all cases an online authentication request is possible,
so that authentication items
can be passed to those client machines.

In addition you need to define, which application on the client machine
the user should authenticate
to. Different application require different authentication items.

Therefore privacyIDEA can define application types.
At the moment privacyIDEA knows the application
``luks``, ``offline`` and ``ssh``. You can write your own application class,
which is defined in
:ref:`code_application_class`.

You need to assign an application and a token to a client machine. Each application type 
can work with certain token types and each application type can use additional parameters.

.. note:: Not all tokens work well with all applications!

.. _application_ssh:

SSH
---

Currently working token types: SSH

Parameters:

``user`` (optional, default=root)

When the SSH token type is assigned to a client, the user specified in the
user parameter
can login with the private key of the SSH token.

In the ``sshd_config`` file you need to configure the ``AuthorizedKeysCommand``.
Set it to::

   privacyidea-authorizedkeys

This will fetch the SSH public keys for the requesting machine.

The command expects a configuration file
*/etc/privacyidea/authorizedkeyscommand* which looks like this::

   [Default]
   url=https://localhost
   admin=admin
   password=test
   nosslcheck=False

.. note:: To disable a SSH key for all servers, you simple can disable the
    SSH token in privacyIDEA.

.. warning:: In a productive environment you should not set **nosslcheck** to
    true, otherwise you are vulnerable to man in the middle attacks.

.. _application_luks:

LUKS
----

Currently working token types: Yubikey Challenge Response

Parameters:

``slot`` The slot to which the authentication information should be written

``partition`` The encrypted partition (usually /dev/sda3 or /dev/sda5)

These authentication items need to be pulled on the client machine from
the privacyIDEA server.

Thus, the following script need to be executed with root rights (able to
write to LUKS) on the client machine::

   privacyidea-luks-assign @secrets.txt --clearslot --name salt-minion

For more information please see the man page of this tool.


.. _application_offline:

Offline
-------

Currently working token types: HOTP.

Parameters:

``user`` The local user, who should authenticate. (Only needed when calling
machine/get_auth_items)

``count`` The number of OTP values passed to the client.

The offline application also triggers when the client calls a /validate/check.
If the user authenticates successfully with the correct token (serial number)
and this very token is attached to the machine with an offline application
the response to validate/check is enriched with a "auth_items" tree
containing the salted SHA512 hashes of the next OTP values.

The client can cache these values to enable offline authentication.
The caching is implemented in the privacyIDEA PAM module.

The server increases the counter to the last offline cached OTP value, so
that it will not be possible to authenticate with those OTP values available
offline on the client side.
