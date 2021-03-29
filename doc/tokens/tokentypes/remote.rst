.. _remote_token:

Remote
------

.. index:: Remote token

The token type *remote* forwards the authentication request to another
privacyIDEA Server.

When forwarding the authentication request, you can

* change the username
* change the resolver
* change the realm
* change the serial number

and mangle the password.

The serial number of the token, that was used on the other privacyIDEA server, is stored in the tokeninfo
of the remote token object in the key ``last_matching_remote_serial``. This serial number can then be used in
further workflows and e.g. be processed in event handlers.

.. figure:: images/enroll_remote.png
   :width: 500

   *Enroll a Remote token*

**Check the PIN locally**

If checked, the PIN of the token will be checked on the local server. If the
PIN matches only the remaining part of the issued password will be sent to
the remote privacyIDEA server.

**Remote Server ID**

The other privacyIDEA server, to which the authentication request will be forwarded.
You need to configure the privacyIDEA Server at :ref:`privacyideaserver_config`.

.. note:: You can define a remote server to be localhost. Thus you can assign
   one token to several users.

Using the direct URL in the remote token is deprecated.

**Remote Serial**

If the *Remote Serial* is specified the given password will be checked
against the serial number on the remote privacyIDEA server. Usernames will be
ignored.

**Remote User**

When forwarding the request to the remote server, the authentication request
will be issued for this user.

**Remote Realm**

When forwarding the request to the remote server, the authentication request
will be issued for this realm.

**Remote Resolver**

When forwarding the request to the remote server, the authentication request
will be issued for this resolver.

.. note:: You can use *Remote Serial* to forward the request to a central
   privacyIDEA server, that only knows tokens but has no knowledge of users.
   Or you can use *Remote Serial* to forward the request to an existing to on
   *localhost* thus adding a second user to the same token.
