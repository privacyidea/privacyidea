.. _machines:

Applications and Machines or Services
=====================================

.. index:: machines, services, client machines

privacyIDEA supports authentication schemes that happen on other machines or services with special applications.

privacyIDEA lets you define Machine Resolvers to connect to existing machine
stores. The idea is for users to be able to authenticate
on those client machines.
An online authentication request is not always possible,
so authentication items
can also be passed to those client machines.

In addition, you need to define which application or service on the client machine
the user should authenticate
to. Different applications require different authentication items.

Therefore privacyIDEA can define application types.
At the moment privacyIDEA knows the applications
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

``user`` The login name on the SSH server for which the key is returned. There
is no default, and the name has to match exactly: a key attached without
``user`` is never returned to ``privacyidea-authorizedkeys``, which always asks
for the keys of the login name.

``service_id`` (required)

When the SSH token type is assigned to a client, the user specified in the
user parameter
can log in with the private key of the SSH token.

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

.. warning:: In a production environment do not disable the check of the TLS
    certificate (``insecure="-k"`` in the shell script, ``nosslcheck=True``
    in the Python script), otherwise you are vulnerable to man-in-the-middle
    attacks.

Managing in the WebUI
.....................

The administrator can view all SSH keys attached to a service in the WebUI at *Token -> Applications*. There the
administrator can filter for service IDs to find all SSH keys that are attached e.g. to webservers.

.. note:: To disable an SSH key for all servers, you simply can disable the
    distinct SSH token in privacyIDEA.

.. _application_luks:

LUKS
----

Currently working token types: TOTP tokens whose serial starts with ``UBOM``.
The privacyideaadm client creates such tokens when it initializes a YubiKey for
HMAC challenge-response, see :ref:`privacyideaadm_enrollment`. Other tokens,
including tokens of the type YubiKey, get no LUKS item.

Parameters:

``slot`` The slot to which the authentication information should be written

``partition`` The encrypted partition (usually /dev/sda3 or /dev/sda5)

These authentication items need to be pulled on the client machine from
the privacyIDEA server.

privacyIDEA does not ship a client for this. The privacyideaadm client (no
longer actively developed) contains the script ``privacyidea-luks-assign``,
which has to be executed with root rights (able to write to LUKS) on the client
machine::

   privacyidea-luks-assign @secrets.txt --clearslot --name salt-minion

For more information see the documentation of privacyideaadm.


.. _application_offline:

Offline
-------

Currently working token types: HOTP, WebAuthn/Passkey.

Parameters:

``user`` Optional, not used for the authentication. It only filters
:http:get:`/machine/authitem`: called with a ``user`` parameter, the endpoint
only returns the offline items of attachments whose ``user`` option is exactly
this value. The ``user`` in the returned offline items is always the owner of
the token.

``count`` The number of OTP values passed to the client, 100 if not set. This is specific to HOTP tokens.

``rounds`` The number of PBKDF2 iterations with which each OTP value is hashed, 6549 if not set. This is specific to
HOTP tokens.

Both options are read again at every refill. When a token is attached in the WebUI, the dialog suggests 100 values and
10000 rounds.

The offline application triggers when the client calls ``/validate/check``.
If the user authenticates successfully with a token that is attached with the
offline application, the response to ``/validate/check`` is extended with an
``auth_items`` object. The machine of the attachment is not compared with the
machine that sends the request: every client that authenticates with this token
receives the offline data (for WebAuthn/Passkey only with a machine name in the
UserAgent, see below). The current WebUI attaches offline tokens without a
machine.

.. _hotp_offline:

HOTP
....
For HOTP tokens, the ``response`` of the offline item is a dictionary that maps the counter of each of the next OTP
values to a hash. Each hash is computed over the OTP value together with the PIN, i.e. the part of ``pass`` in the
``/validate/check`` request that is not the OTP value, in the order of the system setting *Prepend the PIN in front of
the OTP value* (see :ref:`system_config`). A client therefore verifies the whole input of the user, PIN and OTP value,
against these hashes. The number of values is defined by the ``count`` parameter.

.. warning:: Once these values are returned by the server, the counter of the token on the server side is increased by the number of values returned, which effectively makes the token unusable for online authentication.

The client that receives these values should store them locally and is then able to verify OTP values with these hashes.
An entry looks like this:

``4:'$pbkdf2-sha512$6549$uDeGMMYYw5jTWg$5Sp.vdpfOw2PMEr.r5PxA/DD4A8QZNs0hPslY.yHt8DgW2BXuEfrOfPjs1na4iNUoSixvkl.2YTsZMCLNEwL3A'``

It represents the PIN and the OTP value of the HOTP token with counter 4. The hash is stored in the format of the passlib library.
The format has 4 parts: the algorithm, the number of iterations, the salt and the hash, each separated by a $.
After a successful verification, clients should remove all entries from the first counter up to the one that matches
the input.

.. _fido_offline:

WebAuthn/Passkey
................
For WebAuthn/Passkey token, the ``auth_items`` object contains the parameters ``rpId``, ``pubKey`` and ``credentialId``.
These can be used by a client to verify a FIDO2 assertion locally.
Because WebAuthn/Passkey token can have their credentials offline on multiple machines, the client has to identify itself via the UserAgent in the headers.
By default, the UserAgent is checked for the following keys (in order): ["ComputerName", "Hostname", "MachineName", "Windows", "Linux", "Mac"].
The key has to be followed by a slash and the machine name, e.g. ``ComputerName/Laptop-1``; the machine name ends at the next blank. The keys are case-sensitive.
If a key only appears without a slash after it (e.g. ``Windows NT 10.0`` in the UserAgent of a browser), the next key is checked.
If no key with a machine name is found, there will be no offline data returned!
The list of keys to check can be extended by setting ``OFFLINE_MACHINE_KEYS = ["key1", "key2"]`` in the :ref:`cfgfile`. These keys will be appended to the default list and will be checked after them, the order is preserved.

Refill
......
If a client with offline HOTP values runs out of OTP values, it can request a refill.
This is done using :http:post:`/validate/offlinerefill`

If that endpoint returns an error with the error code ``905``, the token can no longer be used offline: it is no longer
attached for offline use, it has been deleted, it can no longer be used at all (disabled, locked by its fail counter,
maximum number of authentications reached, outside its validity period), or the refilltoken is out of sync. Therefore,
clients managing WebAuthn/Passkey offline data should also call this endpoint regularly. A wrong OTP value or a refusal
by :ref:`conditional_access` is answered with the error code ``401`` instead; it does not invalidate the offline data,
so clients should keep it. For WebAuthn/Passkey, a UserAgent without a machine name (see above) is answered with
``905``, although the offline data is still valid. With the policy
:ref:`policy_hide_specific_error_message_for_offline_refill` every failed refill is answered with the same message and
the error code ``401``.

For an HOTP token the client sends the last PIN and OTP value the user entered. Only the OTP value is verified, against
the offline values issued to the client; the PIN is not checked and is only used to compute the new offline values. The
refilltoken is therefore what authorizes a refill.

A refill is subject to :ref:`conditional_access`: a lock of the token owner, a block of the source IP or a *deny*
action refuses it before the refilltoken is checked, so no new offline values are issued and the refilltoken is not
rotated. Such a refusal is recorded in the :ref:`authentication_log` as ``USER_LOCKED``, ``IP_BLOCKED`` or
``ACCESS_DENIED``. A refill that passes conditional access is recorded as ``OFFLINE_REFILL_SUCCESS`` or
``OFFLINE_REFILL_FAIL``, unless the request is missing the ``serial``, ``refilltoken`` or ``pass`` parameter.


Managing in the WebUI
.....................

The administrator can view all offline tokens in the WebUI at *Token -> Applications*.
