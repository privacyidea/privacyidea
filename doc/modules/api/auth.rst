.. _rest_auth:


Authentication endpoints
~~~~~~~~~~~~~~~~~~~~~~~~

You need to authenticate for all administrative tasks. If you are not
authenticated, the API returns a 401 response.

To authenticate you need to send a POST request to /auth containing username
and password.



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

