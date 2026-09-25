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

.. note:: Not all token types work well with all applications!

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

privacyIDEA ships the shell script ``privacyidea-authorizedkeys`` for this. It
is located in the ``tools/`` directory of the source tree, and an installation
from PyPI puts it into the ``bin`` directory of the virtual environment. The
script only needs ``curl`` and ``jq``, not privacyIDEA itself, so copy it to
every SSH server.

Set the privacyIDEA server (``server``), the service account (``serviceaccount``
and ``password``) and the ``service_id`` at the top of the script. The script
authenticates as this administrator and fetches the SSH keys that are attached
to the ``service_id`` for the user who logs in. If admin policies are defined,
the service account needs the admin right
:ref:`policy_fetch_authentication_items`.

In the ``sshd_config`` file configure the script as ``AuthorizedKeysCommand``,
e.g.::

   AuthorizedKeysCommand /usr/local/sbin/privacyidea-authorizedkeys %u
   AuthorizedKeysCommandUser pi-authkeys

``sshd`` requires an absolute path and refuses to start if
``AuthorizedKeysCommandUser`` is not set. Use a dedicated unprivileged user for
it. The script has to be owned by root and must not be writable by group or
others. As it contains the password of the service account, only root and the
``AuthorizedKeysCommandUser`` should be able to read it, e.g.::

   install -o root -g pi-authkeys -m 0750 privacyidea-authorizedkeys /usr/local/sbin/

The script writes the keys of the user to stdout, one per line, and nothing if
the user has no key. It writes its error messages to stderr and then exits with
a non-zero status, so that ``sshd`` logs them instead of reading them as keys.
A token whose key fails its integrity check is left out, the keys of the other
tokens are still returned, see :ref:`sshkey_token`.

The privacyideaadm repository contains an alternative Python script
``privacyidea-authorizedkey``. It expects a configuration file
*/etc/privacyidea/authorizedkeyscommand* which looks like this::

   [Default]
   url=https://localhost
   admin=admin
   password=test
   nosslcheck=False
   service_id=webservers

Check the documentation of privacyideaadm whether your version of the script
supports the ``service_id`` setting.

.. warning:: In a productive environment do not disable the check of the TLS
    certificate (``insecure="-k"`` in the shell script, ``nosslcheck=True``
    in the Python script), otherwise you are vulnerable to man in the middle
    attacks.

Managing in the WebUI
.....................

The administrator can view all SSH keys attached to service in the WebUI at *Tokens -> Token Applications*. There the
administrator can filter for service_ids., to find all SSH keys that are attached e.g. to webservers.

.. note:: To disable a SSH key for all servers, you simply can disable the
    distinct SSH token in privacyIDEA.

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

Currently working token types: HOTP, WebAuthn/Passkey.

Parameters:

``user`` The local user, who should authenticate. (Only needed when calling
machine/get_auth_items)

``count`` The number of OTP values passed to the client. This is specific to HOTP token.

The offline application triggers when the client calls a /validate/check.
If the user authenticates successfully with the correct token (serial number)
and this very token is attached to the machine with an offline application,
the response to validate/check is extended with a "auth_items" object.

.. _hotp_offline:

HOTP
....
For HOTP token that is a list containing the hashes of the next OTP values.
The number of values is defined by the "count" parameter.

.. warning:: Once these values are returned by the server, the counter of the token on the server side is increased by the number of values returned, which effectively makes the token unusable for online authentication.

The client that receives these values should store them locally and is then able to verify OTP values with that list.
An entry looks like this:

``4:'$pbkdf2-sha512$6549$uDeGMMYYw5jTWg$5Sp.vdpfOw2PMEr.r5PxA/DD4A8QZNs0hPslY.yHt8DgW2BXuEfrOfPjs1na4iNUoSixvkl.2YTsZMCLNEwL3A'``

It represents the OTP of the HOTP token with counter 4. The hash is stored in the format of the passlib library.
The format has 4 parts: the algorithm, the number of iterations, the salt and the hash, each separated by a $.
After a successful verification, clients should remove all values from the list between the first counter and the one
that matches the input.

.. _fido_offline:

WebAuthn/Passkey
................
For WebAuthn/Passkey token, the auth_items object contains the parameters ``rpId``, ``pubKey`` and ``credentialId``.
These can be used by a client to verify a FIDO2 assertion locally.
Because WebAuthn/Passkey token can have their credentials offline on multiple machines, the client has to identify itself via the UserAgent in the headers.
By default, the UserAgent is checked for the following keys (in order): ["ComputerName", "Hostname", "MachineName", "Windows", "Linux", "Mac"].
If the UserAgent does not contain any of these keys, there will be no offline data returned!
The list of keys to check can be extended by setting OFFLINE_MACHINE_KEYS = ["key1", "key2", ...] in pi.cfg. These keys will appended to the default list and will be checked after them, the order is preserved.

Refill
......
If a client with offline HOTP values runs out of OTP values, it can request a refill of the list.
This is done using :http:post:`/validate/offlinerefill`

If that endpoints returns an error, it indicates that the token has been unmarked for offline use, or the refilltoken
is out of sync. Therefore, clients managing WebAuthn/Passkey offline data should also call this endpoint regularly.


Managing in the WebUI
.....................

The administrator can view all offline tokens in the WebUI at *Tokens -> Token Applications*.
