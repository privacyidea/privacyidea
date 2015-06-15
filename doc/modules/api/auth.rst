.. _rest_auth:

Authentication endpoints
~~~~~~~~~~~~~~~~~~~~~~~~

.. use the docstring from the module file
.. automodule:: privacyidea.api.auth


.. autoflask:: privacyidea.app:create_app()
   :endpoints:
   :blueprints: jwtauth

   :include-empty-docstring:


**Example Request**:

Requests to privacyidea then should use this security token in the
Authorization field in the header.

.. sourcecode:: http

   GET /users/ HTTP/1.1
   Host: example.com
   Accept: application/json
   Authorization: eyJhbGciOiJIUz....jdpn9kIjuGRnGejmbFbM

