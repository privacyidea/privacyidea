.. _webhookhandler:

WebHook Handler Module
----------------------

.. index:: WebHook Handler, Handler Modules

The webhook event handler module can be used to post a webhook in case of certain events.

This way you can reduce your traffic because you don't have to send API requests
to privacyIDEA. In stat, privacyIDEA is calling your server, if the event has occurred.

For example. You wand that your coffee maker stars if the first person logs in in the morning.
Without the webhook handler, you have to send an API request every 5 minutes and ask did someone
logged in. With the webhook handler will the first login trigger the event and privacyIDEA will
send a post and the coffee maker turns on.

Possible Actions
~~~~~~~~~~~~~~~~

The webhook event handler has just one action 'post'. You can post a webhook to
an url. There is no predefined setting for webhook, because of the missing standard.
You can choose between HTTP encoding and JSON for your webhook and you can write
what ever your other application understands as data.

.. note:: You can use placeholder for more flexibility of the webhook. For example: If the user John is logged in
    and the webhook handler text is "This webhook is triggered by {logged_in_user}", than this text is send:
    "This webhook is triggered by John"
