.. _container_policies:

Container Policies
------------------

.. index:: container policies, client policies

Starting with version 3.11, privacyIDEA supports the interaction of physical containers (e.g. smartphone) with the
server. In the container policies the registration and synchronization of containers can be configured as well as the
rights for containers to use the REST API :ref:`rest_container`.

Technically, container policies are checked using :ref:`code_policy` and :ref:`code_api_policy`.

The container policies respect all policy conditions. However, since no logged-in user is available in the client
container requests, instead the user is determined by the container owner.

The following actions are available in the scope *container*:

Registration and Synchronization
................................

The group ``registration and synchronization`` contains all actions to configure the registration and synchronization.
These actions are only read once at the registration and before a rollover. Changing the actions after the registration
has no effect on registered containers. To apply the changes to registered containers a rollover can be performed.


.. _container_policy_server_url:

privacyIDEA_server_url
~~~~~~~~~~~~~~~~~~~~~~

type: ``str``

The URL of the privacyIDEA server, e.g. ``https://pi.net/``. It is used to build URLs of API endpoints the container
can contact for registration and synchronization. Note that the URL might differ from the server URL of the WebUI.

New in version 3.11

container_registration_ttl
~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``int``

The time in minutes the client has to do the second step of the registration (to scan the QR code). The default is ten
minutes.

New in version 3.11

container_challenge_ttl
~~~~~~~~~~~~~~~~~~~~~~~~

type: ``int``

After the client (a registered container) has challenged an action such as synchronization,
``container_challenge_ttl`` defines the time in minutes the client has to complete the action.
The default is two minutes.

New in version 3.11

container_ssl_verify
~~~~~~~~~~~~~~~~~~~~

type: ``str``

If set to ``True`` the client needs to verify the SSL certificate of the privacyIDEA server.
If no value is set, the default is ``True``. It is highly recommended to use SSL.

New in version 3.11


Smartphone
..........

The group ``smartphone`` contains all actions applicable to smartphone containers.
The policies are checked before each API request and sent to the client during each synchronization.


.. _container_policy_client_rollover:

container_client_rollover
~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

This action allows the client to perform a container rollover with all contained tokens.
The rollover generates new secrets for all contained tokens, and the client has to generate a new asymmetric key pair.
The rollover can also be used to transfer the container with all tokens to a new device.

New in version 3.11

initially_add_tokens_to_container
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

During the first synchronization, this action allows the server to automatically add tokens from the client to the
container on the server. This allows to register devices with existing tokens as container without having to manually
add the tokens on the device to the container. However, the tokens already have to exist on the server. No new token is
created, it only allows to add existing tokens to the container.

New in version 3.11

disable_client_token_deletion
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

By default, the user is allowed to delete tokens locally on the smartphone. The tokens will remain on the server.
Activating this action will disable the deletion of tokens in the authenticator app as long as the smartphone is
registered on the server or this policy changes.

New in version 3.11


.. _container_policy_disable_client_unregister:

disable_client_container_unregister
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

By default, the user is allowed to delete the container locally on the smartphone and thus unregister the container.
The container will remain on the server but will not be connected to the smartphone.
To prevent the user from unregistering the container, this action can be activated. It will also disable the deletion of
the container in the authenticator app as long as the smartphone is registered on the server or this policy changes.

New in version 3.11
