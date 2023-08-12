.. _machines:

Applications and Machines or Services
=====================================

.. index:: machines, services, client machines

privacyIDEA supports authentication schemes, that happen on other machines or services with special applications.

privacyIDEA lets you define Machine Resolvers to connect to existing machine
stores. The idea is for users to be able to authenticate
on those client machines.
Not in all cases an online authentication request is possible,
so that authentication items
can be passed to those client machines.

In addition you need to define, which application or service on the client machine
the user should authenticate
to. Different application require different authentication items.

Therefore privacyIDEA can define application types.
At the moment privacyIDEA knows the application
``luks``, ``offline`` and ``ssh``. You can write your own application class,
which is defined in
:ref:`code_application_class`.

You need to attach a token via an application to a client machine or service. Each application type
can work with certain token types and each application type can use additional parameters.

.. note:: Not all tokentypes work well with all applications!

.. _application_ssh:

SSH
---

Currently working token types: SSH

Parameters:

``user`` (optional, default=root)

``service_id`` (required)

When the SSH token type is assigned to a client, the user specified in the
user parameter
can login with the private key of the SSH token.

The ``service_id`` identifies the SSH servers or group of SSH servers, where the login is allowed to occur.
Read more about :ref:`serviceids`.

authorized keys command
.......................

To facilitate this, the SSH server fetches the managed SSH keys from the privacyIDEA server on demand.
The SSH server uses the ``AuthorizedKeysCommand`` in the ``sshd_config`` to do this.

There is an Python script `privacyidea-authorizedkey` in the privacyideaadm repository. Note, that this
script currently does not support the ``service_id``.
The `tools/` directory of the privacyIDEA Server ships a shell script `privacyidea-authorizedkeys` that
supports the ``service_id``.

In the ``sshd_config`` file you need to configure the ``AuthorizedKeysCommand`` accordingly.
Set it to e.g.::

   privacyidea-authorizedkeys

This will fetch the SSH public keys for the requesting machine and the given user.

If you are using the shell script you need to configure the privacyIDEA Server and
the service account at the top of the script.

The Python script however expects a configuration file
*/etc/privacyidea/authorizedkeyscommand* which looks like this::

   [Default]
   url=https://localhost
   admin=admin
   password=test
   nosslcheck=False
   service_id=webservers

In this example the SSH keys that are attached to the service_id "webservers" are fetched from the
privacyIDEA server.

managing in WebUI
.................

The administrator can view all SSH keys attached to service in the WebUI at *Tokens -> Token Applications*. There the
administrator can filter for service_ids., to find all SSH keys that are attached e.g. to webservers.

.. note:: To disable a SSH key for all servers, you simply can disable the
    distinct SSH token in privacyIDEA.

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

managing in WebUI
.................

The administrator can view all offline tokens in the WebUI at *Tokens -> Token Applications*.
