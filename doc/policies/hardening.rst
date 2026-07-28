.. _policies_hardening:

Hardening policies
------------------

.. index:: hardening policies

The scope *hardening* contains policies that reduce the amount of
information privacyIDEA exposes to unauthenticated clients. They are
system-level controls: unlike most other scopes they are evaluated
without user, realm, resolver or time conditions (client IP and user
agent matching still apply).

hide_version
~~~~~~~~~~~~

type: ``bool``

If enabled, the version number is only shown after login. Responses to
unauthenticated requests have the ``version`` and ``versionnumber``
fields removed, so the running privacyIDEA version is not exposed to
anonymous clients.

hide_auth_error_status
~~~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

If this policy is set, failed authentications at the ``/auth`` and ``/validate`` endpoints
return a uniform ``401`` HTTP status code, regardless of the reason the request failed.
Without this policy the status code differs by cause (for example ``400`` for a denied
authorization, ``403`` for a disabled login, ``404`` for a missing resource), which allows
the status code to be used to distinguish why a request failed.

For full masking, combine this policy with ``hide_specific_error_message`` (authentication
scope; masks the error message and code in the response body) and the AUTHZ policy
``no_detail_on_fail`` (strips the ``detail`` object from a rejected ``/validate/check``
response). Used together these hide the reason an authentication failed via the status code,
the error body and the response detail. Requests to other endpoints keep their regular
status codes.

.. warning:: This policy deliberately changes the HTTP status codes returned by the
    ``/auth`` and ``/validate`` endpoints: failures that would otherwise return ``400``,
    ``403`` or ``404`` all return ``401`` instead. This is an opt-in change to the API
    contract of these endpoints. Any client, reverse proxy, load balancer or monitoring
    system that branches on the specific status code may behave differently once this is
    enabled. Only turn it on if you have reviewed how your integrations react to the
    uniform ``401``.

.. note:: This policy normalizes the *error* responses only. A ``/validate/check`` request
    that reaches the token check and is rejected still returns ``HTTP 200`` with
    ``result.value=false`` (the standard authentication response), while a failure before
    that point (for example an unknown user) returns ``401``. The status code therefore
    still distinguishes "rejected at the token check" from "failed earlier". Returning a
    uniform status for that case as well would change the long-standing ``200``/``value``
    contract that RADIUS, SAML and other consumers rely on, and is out of scope for this
    policy.
