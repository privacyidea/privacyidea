.. _synchronization:

Synchronization
................

Beginning from version 3.11, privacyIDEA supports the synchronization of smartphones with the privacyIDEA
server. This requires the privacyIDEA Authenticator App (v4.5.0 or higher) to be installed on the smartphone.
It is only currently supported for the container type ``smartphone``.

Use Cases
~~~~~~~~~

The synchronization enables the following use cases:
    * The user only needs to scan the QR code for the container and gets all tokens on his smartphone without the need
      to scan each token individually.
    * If new tokens are added to the container on the server, the user can synchronize the container with the
      privacyIDEA server to add the new tokens to the authenticator app.
    * If the user already has tokens on his smartphone, he can synchronize the container with the privacyIDEA server
      to add the tokens to the container on the server.
    * Perform a rollover for all tokens in case the token secrets might be compromised.
    * Transfer all tokens to a new smartphone and invalidate the tokens on the old smartphone. This might be required if
      the smartphone is lost or stolen or if the user switches to a new smartphone.

Note that not all of these scenarios work for offline tokens. Offline tokens already existing on the smartphone
can be synchronized with the server and also be automatically added to the container on the server. However, a transfer
to a new device or a rollover is not possible, as this would renew the token secret and hence invalidate the
offline otp values.

Additionally, SMS tokens will not be synchronized, because they are not stored on the smartphone.

Setup
~~~~~

To enable the synchronization, the smartphone container first needs to be registered on the smartphone. For the
registration, a QR code is generated either during the container creation or on the container details page. The QR code
contains the URL of the privacyIDEA server the smartphone can contact for synchronization.

To set up the smartphone synchronization properly, the following steps are required:

1. **Define container policies**:
   In the policy scope ``Container`` at least the :ref:`container_policy_server_url` needs to be set. This
   is the base URL of
   the privacyIDEA server the smartphone shall contact for registration and synchronization. Note, that the
   smartphone app may connect to a different privacyIDEA URL than the URL of the privacyIDEA Web UI.
2. **Define user or admin policies**:
   In the scope user or admin, the action :ref:`admin_policy_container_register` needs to be allowed. This allows the
   user to create the registration QR code.
3. **Register Container**:
   To register the container on the smartphone, the user needs to scan the QR code. The QR code can be generated
   during the container creation or on the container details page. Optionally, a passphrase prompt and response can be
   set to secure the container registration. The passphrase prompt will be displayed to the user in the app, e.g.
   "Enter the last four digits of your employee ID.", and the passphrase response is the correct answer to the prompt,
   the actual passphrase.
   The registration is completed if the user scans the QR code and enters the correct passphrase.
4. **Synchronize Container**:
   After a successful registration, the pi Authenticator app triggers a synchronization automatically. The user
   can also manually synchronize the container.

The following endpoints must be reachable for the smartphone:
    * :http:post:`/container/register/finalize`: The endpoint that the smartphone contacts to complete the registration.
    * :http:post:`/container/register/terminate/client`: The endpoint to terminate the registration. If the container
      is deleted on the smartphone, this endpoint is called to inform the server that the container is no longer
      available. It does not need to be available if the policy :ref:`container_policy_disable_client_unregister` is
      activated.
    * :http:post:`/container/challenge`: Creates a scoped challenge.
    * :http:post:`/container/synchronize`: The endpoint to synchronize the container.
    * :http:post:`/container/rollover`: The endpoint to perform a rollover of the container with all tokens. This
      endpoint must only be available if the rollover is allowed for the client using the policy
      :ref:`container_policy_client_rollover`.


Implementation Details
~~~~~~~~~~~~~~~~~~~~~~

To perform any action, the client first requests a challenge from the server. The client answers this challenge by
signing a message containing a random nonce and the timestamp from the challenge and sends the response to the endpoint
he wants to access. The server first verifies the response and then performs the requested action.
For the signature, the Elliptic Curve Digital Signature Algorithm (ECDSA) with the curve `secp384r1` is used.

Possible actions the client can perform are:
    * Register a container
    * Synchronize a container
    * Unregister a container
    * Perform a container rollover

.. _synchronization_registration:

Registration
------------

The server initiates the registration by creating the QR code. The QR code contains a URI which uses the pi scheme.
The following variables are included in the URI:

    * ``issuer``: The issuer of the container, e.g. privacyIDEA
    * ``ttl``: Time To Live of the registration challenge (Time the user has to scan the QR code)
    * ``nonce``: A random nonce to prevent replay attacks
    * ``time``: The time the registration challenge was created (ISO 8601 format)
    * ``url``: URL of the privacyIDEA server
    * ``serial``: Container serial
    * ``key_algorithm``: The key algorithm to be used to generate the key pair
    * ``hash_algorithm``: The hash algorithm to be used to generate the key pair
    * ``ssl_verify``: Whether the SSL certificate of the privacyIDEA server should be verified
    * ``passphrase``: Optional passphrase prompt, displayed to the user to enter the corresponding passphrase

Example of a URI:

.. code-block::

    pia://container/SMPH000588A4?issuer=privacyIDEA&ttl=10&nonce=97f94b36c199f4a0980720e18fcbcef99dbe871e
    &time=2024-12-17T09%3A11%3A08.675629%2B00%3A00&url=https://pi.com&serial=SMPH000588A4
    &key_algorithm=secp384r1&hash_algorithm=SHA256&ssl_verify=True
    &passphrase=Enter%20the%20last%20four%20digits%20of%20your%20employee%20ID.


The server creates an entry in the challenge database with the scope (URL of the API endpoint the client needs to
contact to finalize the registration), the nonce, the time, and the correct passphrase response.

After scanning the QR code with the pi authenticator, the app creates an asymmetric elliptic key pair
`(k_priv, k_pub)` with the curve `secp384r1` and signs a message concatenating at least the nonce, time (ISO 8601
format), serial, and scope. Optionally, the passphrase response and device information are included in the signature:

``sign(k_pub, nonce|time|serial|scope|device_brand|device_model|passphrase_response|public_key)``

To complete the registration the endpoint :http:post:`/container/register/finalize` is called with the following
parameters:

.. code-block::

    container_serial: <serial>
    signature: <signature>
    public_key: <ecc public key of the client in PEM format (curve secp384r1)>
    device_brand: <device brand>
    device_model: <device model>

The server verifies the signature. If it is valid the registration is completed. See also
:meth:`privacyidea.lib.containers.smartphone.SmartphoneContainer.finalize_registration`
for more details on the implementation details of the registration for smartphones.

It is highly recommended to always use SSL to verify the privacyIDEA server's certificate. By default, SSL is activated
but can be deactivated in the policies.


Synchronization
---------------

When synchronising, the server response is additionally encrypted to secure the token secrets included in the
response. For the encryption, the ECC Diffie-Hellmann key exchange is used to create a session key.

To synchronize the smartphone with the server, the authenticator app first requests a challenge at
:http:post:`/container/challenge` for the container and a scope (the synchronization endpoint). This endpoint returns
a random nonce and a timestamp.

The authenticator app generates an ecc asymmetric key pair with the curve `x25519` for the encryption. To synchronize
with the server the app signs a message containing the parameters in the following order separated by "|":

    * nonce (from the challenge)
    * timestamp (from the challenge)
    * serial of the container to synchronize
    * scope: The URL of the synchronization endpoint, e.g. `https://pi.net/container/synchronize`
    * ecc public key of the client in PEM format (curve `x25519`)
    * container dictionary of the client

The container dictionary of the client contains the tokens that are already in the authenticator app in the
following format:

.. code-block::

    {"tokens": [{"serial": "TOTP0001", "tokentype": "totp"},
                {"otp": ["123456", "234567"], "tokentype": "hotp"}]}

If the app does not know the serial of a token, it can also include a list of the next two otp values. The server will
then try to find the token by the otp values.

Finally, the synchronization endpoint :http:post:`/container/synchronize` is called with the following parameters:

.. code-block::

    container_serial: <serial>
    signature: <signature>
    public_key: <ecc encryption public key of the client in PEM format (curve x25519)>
    container_dict_client: <container dictionary containing the tokens of the client>

The server verifies the response of the challenge. See also
:meth:`privacyidea.lib.containers.smartphone.SmartphoneContainer.check_challenge_response` for more information on how
the server verifies the response.
If the challenge is valid, the server compares the clients tokens with the tokens in the
container on the server. For tokens that are not yet in the authenticator app, the server performs a rollover and
includes the enrollment data in the response. For equal tokens, token details from the server are included in the
response.

The pi authenticator adds the missing tokens, updates existing tokens, and removes tokens not available on the server.


Rollover
--------

The rollover generates new secrets for all tokens and the client has to generate a new asymmetric key pair for the
signatures. It can be initiated on the server, but also from the client. The client can use it to just renew all
secrets in case they might be compromised or to transfer the container with all tokens to a new device.

Similar to the synchronization, the client first requests a challenge from the server at
:http:post:`/container/challenge`. The client has to pass the container serial and the scope (e.g.
`https://pi.net/container/rollover`) as parameters. This endpoint returns a random nonce and a timestamp.

The client signs a message containing the nonce, the timestamp, the serial of the container, and the scope and sends
the signature and the container serial to the endpoint :http:post:`/container/rollover`. This endpoint verifies the
signature and if it is valid, the server initiates the rollover which is similar to the
:http:post:`/container/register/initialize` endpoint. The registration configurations are fetched from the policies
such as :ref:`container_policy_server_url` and a challenge is created. The endpoint returns a QR code containing the
data as described for the :ref:`synchronization_registration`. This QR code is displayed in the authenticator app if
the container shall be transferred to a new device. The new smartphone can scan the QR code and finalize the rollover
at :http:post:`/container/register/finalize`. To differentiate between a registration and a rollover, a parameter
``rollover = True`` has to be added in the request. This endpoint generates new token secrets and stores the new
public key of the client. Now the old smartphone will not be able to synchronize with the server anymore and the tokens
on the old smartphone are invalidated. The new smartphone can now synchronize with the server to get all tokens.
After this initial synchronization the rollover process is completed.


Terminate Registration
----------------------

To unregister the container, the client first requests a challenge from the server at :http:post:`/container/challenge`
with the container serial and the scope (e.g. `https://pi.net/container/register/terminate/client`) as parameters.
Afterward, the client can sign a message containing the nonce, the timestamp, the serial of the container, and the
scope. The signature and the container serial are send to the endpoint :http:post:`/container/register/terminate/client`.
The server verifies the signature and if it is valid, the container is unregistered. The server deletes all data
relevant for the synchronization such as the public client key and the registration state. Hence, a synchronization
with the server is not possible anymore. The container is deleted in the authenticator app, but remains on the
server.

If the user shall not be able to delete the container in the authenticator app and hence terminate the registration,
the policy :ref:`container_policy_disable_client_unregister` can be activated.
