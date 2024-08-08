.. _rest_default_realm:

Default Realm endpoints
~~~~~~~~~~~~~~~~~~~~~~~

These endpoints are used to define the default realm, retrieve it and delete it.

.. autoflask:: privacyidea.app:create_app(silent=True)
   :endpoints:
   :blueprints: defaultrealm_blueprint

   :include-empty-docstring:
