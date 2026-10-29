.. _webhookhandler:

WebHook Handler Module
----------------------

.. index:: WebHook Handler, Handler Modules

The webhook event handler module can be used to trigger a webhook in case of certain events.

For example, you may have a machine or service with a webhook API, like an IoT coffee maker.
Assume you want your coffee maker to start when the first person logs in in the morning. The event of
the authentication request can trigger the webhook to the coffee maker, turning on the coffee machine.

The endpoint is not configured in the handler. It is a :ref:`webhook_config` object, which owns the URL, the
HTTP method, the authentication, the static headers and the TLS, proxy and timeout settings. This handler
picks one of them and contributes the payload. Several handlers can therefore share one endpoint, and a URL
that changes or a credential that is rotated is edited in one place.

Possible Actions
~~~~~~~~~~~~~~~~

post_webhook
............

The handler has a single action, ``post_webhook``. It needs a **webhook** -- that is where it posts. The
remaining options are optional, each with a meaningful empty state.

**webhook**

The webhook to post to, selected from the configured ones. Listing them requires
:ref:`policy_webhook_read`; without it the select has nothing to offer.

Delivery is synchronous and there are no retries, so a slow endpoint delays the request that triggered the
event; see :ref:`webhook_synchronous`. A webhook that fails never fails the event -- the failure is logged
and audited, and the remaining handlers still run. The :ref:`webhook_outbound_guard` applies to what the
handler sends, as it does to every webhook.

**URL** and **content_type** (shown only)

Where the handler posts and which MIME type it sends, taken from the webhook selected above. Both are shown
so that the endpoint is visible while editing the handler; neither can be changed here, because both belong
to the webhook.

**data**

The body posted to the endpoint. Leave it empty to send the webhook's own ``default_payload``, which is how
one webhook can serve several handlers with one body.

**replace**

If enabled, the placeholders in the data are replaced.

.. note:: You can use placeholders for more flexibility of the webhook, if the option **replace** is enabled.
    For example: If the user John authenticates and the webhook handler text is "This webhook is triggered by
    {logged_in_user}", then this text is sent: "This webhook is triggered by John".
    Possible placeholders are ``{admin}``, ``{realm}``, ``{action}``, ``{serial}``, ``{url}``, ``{user}``,
    ``{surname}``, ``{givenname}``, ``{username}``, ``{userrealm}``, ``{tokentype}``, ``{tokendescription}``,
    ``{time}``, ``{date}``, ``{client_ip}``, ``{ua_browser}``, ``{ua_string}`` and ``{challenge}``.
    For backward compatibility the aliases ``{logged_in_user}``, ``{token_serial}`` (= ``{serial}``),
    ``{token_owner}`` (= ``{givenname}``) and ``{user_realm}`` (= ``{userrealm}``) also work.
    The availability of the tags depends on the endpoint.

    ``{logged_in_user}`` and ``{realm}`` are the login name and the realm of the user the request is about (the
    user who authenticates, or the user an administrator acts on); only if the request names no user, they are
    the logged in user. ``{admin}`` is the logged in administrator. (In the other handlers ``{realm}`` is the
    realm of the logged in user.)

    ``{serial}`` is the ``serial`` parameter of the request. If the request has none, it is the comma-separated
    list of the serials of all tokens of the user, e.g. on ``/validate/check`` (the token that authenticated is
    not reported) or on ``/token/init`` without a serial (the new serial only appears within this list).

    ``{url}`` is the URL set in ``PI_BASE_URL`` (see :ref:`cfgfile`) and empty if it is not set.

    A payload that is a JSON object or array is substituted value by value, so a placeholder carrying a quote
    cannot break the document. Anything else -- including a plain sentence sent to a webhook whose content type
    is ``application/json`` -- is substituted as plain text. With ``application/x-www-form-urlencoded``,
    replaced values are not URL-encoded.

.. deprecated:: 3.15
    Before privacyIDEA 3.15 the handler carried the endpoint itself, in its own ``URL`` and ``content_type``
    options. Such a handler keeps working and shows its stored values in the two fields above, but it always
    verifies TLS, waits a fixed 10 seconds, counts an HTTP error status as a run and can not carry
    authentication. The options will be removed in privacyIDEA 3.16, after which it sends nothing.

    Convert it before that release by selecting a webhook above. The upgrade to 3.15 does it automatically,
    and ``pi-manage config import`` converts an export taken before 3.15 on the way in. A handler that sends
    nothing as it stands -- no ``URL``, or a ``content_type`` that is neither JSON nor urlencoded -- cannot
    be converted: the upgrade names it in the log and leaves it alone, and the import refuses it, failing the
    whole import unless ``--skip-invalid`` is given. Correct it and run the upgrade or import again.

Auditing
~~~~~~~~

Each run writes an audit entry naming the webhook and what the endpoint answered, for example
``My Hook (webhook 'siem': HTTP 200)``, or the reason on a failure. The URL never appears there: it belongs
to the webhook and may embed a token.

Code
~~~~

.. automodule:: privacyidea.lib.eventhandler.webhookeventhandler
   :members:
   :undoc-members:
