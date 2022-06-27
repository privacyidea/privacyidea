.. _webhookhandler:

WebHook Handler Module
----------------------

.. index:: WebHook Handler, Handler Modules

The webhook event handler module can be used to trigger a webhook in case of certain events.

E.g. if you have a machine or a service that provides a certain API with webhooks, like an IoT coffee maker.
Assume you want that your coffee maker starts if the first person logs in in the morning. The event of
the authentication request can trigger the webhook to the coffee maker, turning on the coffee machine.

Possible Actions
~~~~~~~~~~~~~~~~

Currently the webhook event handler has just one action 'post'. You can post a webhook to
an URL. There is no predefined setting for webhook, because of the missing standard.
You can choose between HTTP encoding and JSON for your webhook and you can write
what ever your other application understands as data.

.. note:: You can use placeholder for more flexibility of the webhook. For example: If the user John is logged in
    and the webhook handler text is "This webhook is triggered by {logged_in_user}", than this text is send:
    "This webhook is triggered by John"
