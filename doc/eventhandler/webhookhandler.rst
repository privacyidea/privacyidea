.. _webhookhandler:

WebHook Handler Module
----------------------

.. index:: WebHook Handler, Handler Modules

The webhook event handler module can be used to trigger a webhook in case of certain events.

For example, you may have a machine or service with a webhook API, like an IoT coffee maker.
Assume you want your coffee maker to start when the first person logs in in the morning. The event of
the authentication request can trigger the webhook to the coffee maker, turning on the coffee machine.

Possible Actions
~~~~~~~~~~~~~~~~

post_webhook
............

Currently the webhook event handler has just one action, ``post_webhook``. You can post a webhook to
a URL. There is no predefined setting for webhook, because of the missing standard.
You can choose between HTTP encoding and JSON for your webhook and you can write
whatever your other application understands as data.

The action takes the following options:

**URL**

  * *required* Option

The URL the webhook is posted to.

**content_type**

  * *required* Option

The MIME type (Content-Type) used for the webhook payload, either ``application/json`` or
``application/x-www-form-urlencoded``.

**replace**

If enabled, the placeholders in the data are replaced.

**data**

  * *required* Option

The data posted in the webhook.

.. note:: You can use placeholders for more flexibility of the webhook, if the option **replace** is enabled.
    For example: If the user John is logged in and the webhook handler text is "This webhook is triggered by
    {logged_in_user}", then this text is sent: "This webhook is triggered by John".
    Possible placeholders are ``{admin}``, ``{realm}``, ``{action}``, ``{serial}``, ``{url}``, ``{user}``,
    ``{surname}``, ``{givenname}``, ``{username}``, ``{userrealm}``, ``{tokentype}``, ``{tokendescription}``,
    ``{time}``, ``{date}``, ``{client_ip}``, ``{ua_browser}``, ``{ua_string}`` and ``{challenge}``.
    For backward compatibility the aliases ``{logged_in_user}``, ``{token_serial}`` (= ``{serial}``),
    ``{token_owner}`` (= ``{givenname}``) and ``{user_realm}`` (= ``{userrealm}``) also work.
    The availability of the tags depends on the endpoint.

Code
~~~~

.. automodule:: privacyidea.lib.eventhandler.webhookeventhandler
   :members:
   :undoc-members:
