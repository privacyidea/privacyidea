.. _federationhandler:

Federation Handler Module
-------------------------

.. index:: Federation Handler, Handler Modules

The federation event handler can be used to configure relations between
several privacyIDEA instances. Requests can be forwarded to child privacyIDEA
instances.

.. note:: The federation event handler can modify the original response.
   If the response was modified, the field ``origin`` is set in the
   ``detail`` section of the response. It contains the URL (including the
   path) of the privacyIDEA server this server forwarded the request to, and
   replaces an ``origin`` that the other server returned; in a chain of
   several servers it therefore names the next server only. If the response
   of that server has no ``detail`` section, no ``origin`` is added.

Possible Actions
~~~~~~~~~~~~~~~~

forward
.......

A request (usually an authentication request *validate_check*) can be
forwarded to another privacyIDEA instance. The administrator can
define privacyIDEA instances centrally, see :ref:`privacyideaserver_config`.

The handler runs in the post position, after the request was processed on
this server, and forwards the request parameters as this server processed
them: they contain the realm this server determined for the user (its default
realm if the client sent none) and values added by its policies (the child
sets its own policy values again). Requests with the methods GET, POST and
DELETE are forwarded; for other methods (e.g. PUT) a warning is logged and the
response of this server is returned.

In addition to the privacyIDEA instance the action ``forward`` takes the
following parameters:

**forward_client_ip**
  The original client IP will be passed to the child privacyIDEA
  server. Otherwise the child privacyIDEA server will use the parent
  privacyIDEA server as client. The child uses the forwarded client IP
  only for ``/validate/``, ``/ttype/`` and ``/auth`` requests; for
  forwarded token or system requests it sees this server as client.

  .. note:: You need to configure the :ref:`override_client` setting
     (``OverrideAuthorizationClient``) on the child privacyIDEA server.

**forward_authorization_token**
  The authorization header of the original request will be passed to the child
  privacyIDEA server. This makes it possible to also forward requests like token and system
  requests.

  The child verifies this authorization token with its own secret key, so both servers need
  the same ``SECRET_KEY`` in ``pi.cfg``; otherwise the child answers with an authentication
  error, which replaces the response. The child applies its own policies to the
  administrator named in the token. As the handler runs in the post position, a forwarded
  token or system request has already been executed on this server before it is sent to the
  child.

**realm**
  The forwarding request will change the realm to the specified realm.
  This might be necessary since the child privacyIDEA server could have
  different realms than the parent privacyIDEA server.
  Set **realm** whenever the child has no realm of the same name as the realm
  this server determined; otherwise the child looks the user up in a realm it
  does not have and the forwarded request fails.

**resolver**
  The forwarding request will change the resolver to the specified
  resolver. This might be necessary since the child privacyIDEA server could
  have different resolvers than the parent privacyIDEA server.

One simple possibility would be that a user has a token in the parent
privacyIDEA server and in the child privacyIDEA server. Configuring a forward
event handler on the parent with the condition ``result_value = False`` would
have the effect that the user can either authenticate with the parent's
token or with the child's token on the parent privacyIDEA server.
Note that the parent checks the request first: every authentication with the
child's token counts as a failed authentication with the parent's tokens and
increases their fail counter. Once the maximum is reached, the parent's token
is locked, and only the child's token still works.

Federation can be used if privacyIDEA was introduced in a subdivision of a
larger company. When privacyIDEA should be rolled out to the whole company
you can use federation. Instead of dropping the privacyIDEA instance in the
subdivision and installing one single central privacyIDEA, the subdivision can
still go on using the original privacyIDEA system (child) and the company
will install a new top level privacyIDEA system (parent).

Using the federation handler you can set up many other, different scenarios we
cannot think of yet.

Code
~~~~

.. automodule:: privacyidea.lib.eventhandler.federationhandler
   :members:
   :undoc-members:
