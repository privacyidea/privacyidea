.. _rest_api:

REST API
--------

.. index:: API, REST

.. automodule:: privacyidea.api

Start to read about authentication to the API at :ref:`rest_auth`.
Read about the structure of the responses at :ref:`rest_api_response_format`.

.. toctree::

   api/audit
   api/auth
   api/validate
   api/authentication_log
   api/conditional_access
   api/system
   api/tokengroup
   api/serviceid
   api/resolver
   api/realm
   api/defaultrealm
   api/token
   api/container
   api/user
   api/policy
   api/event
   api/healthcheck
   api/machineresolver
   api/machines
   api/privacyideaserver
   api/caconnector
   api/recover
   api/register
   api/monitoring
   api/periodictask
   api/application
   api/ttype
   api/smtpserver
   api/smsgateway
   api/radiusserver
   api/subscriptions
   api/client
   api/clients
   api/info

.. _rest_api_response_format:

Response format
~~~~~~~~~~~~~~~

.. index:: API response, response signature

Most endpoints send a JSON object with the same structure. The documentation of an endpoint describes only the content
of ``result.value`` and ``detail``. This section describes all members of the object.

A request that privacyIDEA processes without an error, here :http:post:`/token/disable/(serial)`, gets this response:

.. sourcecode:: json

   {
     "id": 1,
     "jsonrpc": "2.0",
     "result": {
       "status": true,
       "value": 1
     },
     "signature": "rsa_sha256_pss:4a6a3b0e18...6668e39",
     "time": 1762683309.382107,
     "version": "privacyIDEA 3.14.1",
     "versionnumber": "3.14.1"
   }

A request that fails with an error, here the same request for a serial that does not exist, gets this response with
the HTTP status code ``404``:

.. sourcecode:: json

   {
     "detail": null,
     "id": 1,
     "jsonrpc": "2.0",
     "result": {
       "error": {
         "code": 601,
         "message": "No token found for serials: NOTEXIST"
       },
       "status": false
     },
     "signature": "rsa_sha256_pss:05c61cb73a...165e83",
     "time": 1762683309.488772,
     "version": "privacyIDEA 3.14.1"
   }

The response contains these members:

``result.status``
    ``true`` if privacyIDEA processed the request without an error, ``false`` if an error occurred. ``true`` does not
    mean that an authentication succeeded. For example, :http:post:`/validate/check` also returns ``true`` for a wrong
    OTP value. The outcome of an authentication is in ``result.value`` and ``result.authentication``.

``result.value``
    The return value of the endpoint, only in a response without an error. Its type depends on the endpoint, for
    example a boolean, a number, a string, a list or an object.

``result.authentication``
    The outcome of an authentication: ``ACCEPT``, ``REJECT``, ``CHALLENGE``, or ``DECLINED`` if the user declined a
    challenge, for example in the push app. Only the responses of :http:post:`/auth`, :http:post:`/validate/check`,
    :http:post:`/validate/triggerchallenge`, :http:get:`/validate/polltransaction` and
    :http:post:`/validate/initialize` contain it, and only if no error occurred.

``result.error``
    The error, only in a response with an error. ``code`` is the privacyIDEA error code, for example ``4031`` for wrong
    credentials at ``/auth``. It is not the HTTP status code. ``message`` describes the error in the language of the
    ``Accept-Language`` header of the request, if a translation exists. Because the text depends on the language, a
    client must evaluate ``code`` and not ``message``.

    At ``/auth`` and ``/validate/check``, the policy
    :ref:`hide_specific_error_message <policy_hide_specific_error_message>` replaces the code and the message with
    generic values.

``detail``
    An object with additional information. Its content depends on the endpoint. For example, the response of
    :http:post:`/validate/check` contains the serial and the type of the token. For a challenge-response
    authentication, it also contains the transaction ID and the challenges in ``multi_challenge``, see
    :ref:`authentication_modes`. If ``detail`` is not empty, it also contains ``threadid``, the ID of the server thread
    that processed the request.

    A response without an error contains ``detail`` only if the endpoint returns additional information. A response
    with an error always contains it, as ``null`` or as an empty object if the error has no additional information.

``version`` and ``versionnumber``
    The version of privacyIDEA. ``version`` contains the product name (``privacyIDEA 3.14.1``), ``versionnumber``
    contains only the number (``3.14.1``). A response with an error contains only ``version``. The hardening policy
    :ref:`hide_version <policies_hardening>` removes both from the responses to requests without authentication.

``time``
    The time at which privacyIDEA created the response, in seconds since 1970-01-01 00:00 UTC (Unix time), with a
    fractional part.

``signature``
    The signature of the response, see :ref:`rest_api_response_signature`.

``nonce``
    The value of the request parameter ``nonce``, only if the request contains this parameter and privacyIDEA signs the
    response. A client sends a random nonce (a value for one use only) and compares it with the value in the signed
    response. This makes sure that the signed response belongs to the request of the client.

``auth_items``
    The offline data of a token, only in a response of :http:post:`/validate/check` and
    :http:post:`/validate/offlinerefill`, see :ref:`application_offline`.

``jsonrpc`` and ``id``
    Members from the JSON-RPC format. They remain for compatibility with clients that read them. The response does
    not follow the JSON-RPC specification. ``jsonrpc`` is always ``"2.0"``. ``id`` is ``2`` in a response that
    contains ``result.authentication`` and ``1`` in all other responses. Clients do not need these members.

The :ref:`responsemanglerhandler` can change and remove members of the response.

HTTP status codes
.................

A response without an error has the HTTP status code ``200``. This also applies to an authentication that
:http:post:`/validate/check` rejects with ``result.value`` ``false``. A response with an error has a status code of
``400`` or higher. Examples are:

* ``400`` for an invalid request, for example a missing parameter or a user that does not exist
* ``401`` for a failed authentication, for example wrong credentials at ``/auth`` or a missing ``Authorization``
  header
* ``403`` for a request that a policy denies
* ``404`` for an object that does not exist
* ``409`` for a change that conflicts with the change of another client, for example at
  :http:put:`/conditionalaccess/policy/order` if the priority of a policy changed after the client read it
* ``500`` for an internal error
* ``501`` for a function that privacyIDEA does not implement

At ``/auth`` and at the ``/validate`` endpoints, the hardening policy ``hide_auth_error_status`` changes the status
code of an error response in the format above to ``401`` if the code is below ``500``, see :ref:`policies_hardening`.
The policy does not change the status codes of the responses in :ref:`rest_api_other_formats`, for example ``405``
for a wrong HTTP method or ``400`` from :http:post:`/validate/radiuscheck`.

.. _rest_api_response_signature:

Response signature
..................

privacyIDEA signs each JSON response with the private key in ``PI_AUDIT_KEY_PRIVATE`` (see :ref:`cfgfile`). The
algorithm is RSA-PSS with SHA-256 and the mask generation function MGF1 with SHA-256. The salt length is the maximum
that the key allows: the key length in bytes minus 34, for example 222 bytes for a 2048-bit key. The member
``signature`` contains the name of the algorithm and the signature as a hexadecimal number, separated by a colon:
``rsa_sha256_pss:<hex>``.

The signed data is the response without the member ``signature``, as JSON in the same format as the response body:

* The keys are in alphabetical order.
* ``", "`` separates the members and ``": "`` separates a key from its value.
* Non-ASCII characters are escaped as ``\uXXXX``, with lowercase hexadecimal digits.

In Python, ``json.dumps(response, sort_keys=True)`` creates this format.

To make sure that a response comes from your privacyIDEA server:

#. Remove the member ``signature`` from the parsed response.
#. Write the rest as JSON in the format above.
#. Verify the signature of this text with the public key in ``PI_AUDIT_KEY_PUBLIC``. Use the maximum salt length,
   or let the library detect the salt length.

.. note:: Some libraries use the length of the hash (32 bytes) as the salt length by default. With this default, the
   verification of the signature fails. In the Python library ``cryptography``, use ``padding.PSS.MAX_LENGTH`` or
   ``padding.PSS.AUTO``.

A response contains no ``signature`` in these cases:

* ``PI_NO_RESPONSE_SIGN`` is ``True`` in :ref:`cfgfile`.
* privacyIDEA cannot load the private key. It then writes ``Could not load private key`` to the log file, at the log
  level INFO.
* The response is not JSON, see :ref:`rest_api_other_formats`.
* The URL of the request matches no endpoint, see :ref:`rest_api_other_formats`.
* The response comes from a :ref:`health check endpoint <rest_healthcheck>`. These responses also never contain
  ``version`` and ``versionnumber``.

.. _rest_api_other_formats:

Other formats
.............

These endpoints do not send the JSON object described above:

* :http:get:`/audit/(csvfile)` and :http:get:`/token/` with ``outform=csv`` send CSV data.
* :http:get:`/policy/export/(export)` sends the policies as a file.
* :http:get:`/system/documentation` sends the configuration as a reStructuredText file.
* :http:post:`/validate/radiuscheck` sends an empty body with the HTTP status code ``204`` or ``400``.
* At ``/ttype/<type>``, some token types answer in their own format. Examples are the TiQR token and the Yubico
  validation protocol of the Yubikey token.

These error responses also do not have the format described above. privacyIDEA does not sign them.

* A request to a URL that matches no endpoint gets the HTTP status code ``404`` and the body
  ``{"error": "Not found"}``. A ``GET`` request that accepts HTML, for example with the header ``Accept: */*``, gets
  the WebUI or a redirect to the WebUI instead.
* A request with an HTTP method that the endpoint does not support gets the HTTP status code ``405`` and an HTML
  page.
* A request with the content type ``application/json`` and a body that is not valid JSON gets the HTTP status code
  ``400`` and an HTML page.
