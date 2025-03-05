.. _rest_healthcheck:

Healthcheck endpoints
.....................

.. automodule:: privacyidea.api.healthcheck

For information on the current standard and how to configure these probes, see the Kubernetes documentations:

https://kubernetes.io/docs/reference/using-api/health-checks/

https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/

.. autoflask:: privacyidea.app:create_app(silent=True)
   :endpoints:
   :blueprints: healthz_blueprint

   :include-empty-docstring:
