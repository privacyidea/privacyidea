.. _rest_healthcheck:

Healthcheck endpoints
.....................

.. automodule:: privacyidea.api.healthcheck

For information on the current standard and how to configure these probes, see the Kubernetes documentations:

https://kubernetes.io/docs/reference/using-api/health-checks/

https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/

.. autoflask:: privacyidea.app:create_app()
   :endpoints:
   :blueprints: healthcheck_blueprint

   :include-empty-docstring:

.. http:get:: /healthz

    Checks the liveness and readiness of the application by verifying both the `/livez`
    and `/readyz` endpoints.

    :resheader Content-Type: application/json
    :status 200: Application is live and ready.
    :status 503: Application is live but not ready.

   **Example Request**:

   .. sourcecode:: http

      GET /healthz HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "status": "ready",
          "hsm": "OK"
      }

.. http:get:: /healthz/startupz

    Startup check endpoint that indicates if the app has started.

    :resheader Content-Type: application/json
    :status 200: Application has started.
    :status 503: Application has not started yet.

   **Example Request**:

   .. sourcecode:: http

      GET /healthz/startupz HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "status": "started"
      }

.. http:get:: /healthz/livez

    Liveness check endpoint that indicates if the app is running.

    :resheader Content-Type: application/json
    :status 200: Application is live.

   **Example Request**:

   .. sourcecode:: http

      GET /healthz/livez HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "status": "OK"
      }

.. http:get:: /healthz/readyz

    Readiness check endpoint that indicates if the app is ready to serve requests.
    This endpoint checks the readiness of the app and its dependencies, including
    the Hardware Security Module (HSM).

    :resheader Content-Type: application/json
    :status 200: Application is ready.
    :status 503: Application is not ready or HSM is not ready.

   **Example Request**:

   .. sourcecode:: http

      GET /healthz/readyz HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "status": "ready",
          "hsm": "OK"
      }

.. http:get:: /healthz/resolversz

    Resolver check endpoint that tests the connection to all LDAP and SQL resolvers.
    Tests the connectivity to both LDAP and SQL resolvers, returning their individual
    connection statuses.

    :resheader Content-Type: application/json
    :status 200: All resolvers have been successfully checked.
    :status 503: Failed to check resolvers or an error occurred.

   **Example Request**:

   .. sourcecode:: http

      GET /healthz/resolversz HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "status": "ready",
          "ldapresolvers" {
              "ldapresolver1": "OK",
              "ldapresolver2": "OK"
          },
          "sqlresolvers": {
              "sqlresolver1": "OK",
              "sqlresolver2": "OK"
          },
      }