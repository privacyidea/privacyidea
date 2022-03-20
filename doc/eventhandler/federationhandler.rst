.. _federationhandler:

Federation Handler Module
-------------------------

.. index:: Federation Handler, Handler Modules

The federation event handler can be used to configure relations between
several privacyIDEA instances. Requests can be forwarded to child privacyIDEA
instances.

.. note:: The federation event handler can modify the original response.
   If the response was modified a new field ``origin`` will be added to the
   ``detail`` section in the response. The *origin* will contain the URL of
   the privacyIDEA server that finally handled the request.

Possible Actions
~~~~~~~~~~~~~~~~

forward
.......

A request (usually an authentication request *validate_check*) can be
forwarded to another privacyIDEA instance. The administrator can
define privacyIDEA instances centrally at *config* -> *privacyIDEA servers*.

In addition to the privacyIDEA instance the action ``forward`` takes the
following parameters:

**client_ip** The original client IP will be passed to the child privacyIDEA
server. Otherwise the child privacyIDEA server will use the parent
privacyIDEA server as client.

.. note:: You need to configure the allow override client in the child
   privacyIDEA server.

**realm** The forwarding request will change the realm to the specified realm.
  This might be necessary since the child privacyIDEA server could have
  different realms than the parent privacyIDEA server.

**resolver** The forwarding request will change the resolver to the specified
  resolver. This might be necessary since the child privacyIDEA server could
  have different resolvers than the parent privacyIDEA server.

One simple possibility would be, that a user has a token in the parent
privacyIDEA server and in the child privacyIDEA server. Configuring a forward
event handler on the parent with the condition ``result_value = False`` would
have the effect, that the user can either authenticate with the parent's
token or with the child's token on the parent privacyIDEA server.

Federation can be used, if privacyIDEA was introduced in a subdivision of a
larger company. When privacyIDEA should be enrolled to the complete company
you can use federation. Instead of dropping the privacyIDEA instance in the
subdivision and installing on single central privacyIDEA, the subdivision can
still go on using the original privacyIDEA system (child) and the company
will install a new top level privacyIDEA system (parent).

Using the federation handler you can setup many other, different scenarios we
can not think of, yet.

Code
~~~~

.. automodule:: privacyidea.lib.eventhandler.federationhandler
   :members:
   :undoc-members:
