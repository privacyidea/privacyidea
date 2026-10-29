.. _webhook_config:

Webhook configuration
---------------------

.. index:: webhook

Starting with privacyIDEA 3.15 a webhook is a configuration object of its own,
like an :ref:`smtpserver` or an :ref:`sms_gateway_config`. :ref:`rest_webhook`.

A webhook **owns the endpoint**: the URL, the HTTP method, the authentication,
the static headers and the TLS, proxy and timeout settings. Whoever fires it -
an event handler or a conditional access policy - owns only the **payload**.
That split is what lets several call sites talk to the same endpoint without
each repeating its credentials, and it keeps those credentials out of the
places that merely reference the webhook.

Each webhook is addressed by a *unique identifier*. Under
*Config -> External Services -> Webhooks* you can list, create, edit and delete
them.

Settings
~~~~~~~~

Endpoint
   The **URL** must start with ``http://`` or ``https://``. The **HTTP method**
   is ``POST`` (default), ``GET``, ``PUT`` or ``PATCH``. The **content type** is
   any valid MIME type, ``application/json`` by default.

Default payload
   The body sent when the call site supplies none. An event handler that leaves
   its ``data`` option empty therefore sends this, which is how one webhook can
   serve several policies with one body.

Authentication
   ``none`` (default), ``basic`` (username and password), ``header`` (the
   credential is one of the static headers below, marked as secret) or ``mtls``
   (a client certificate and key, the key optionally encrypted with a password).
   The certificate and key are read from paths **on the privacyIDEA server**.

Headers
   Any number of static headers. A header marked as **secret** is stored
   encrypted and is never shown again; the editor displays ``__CENSORED__`` in
   its place. Sending that placeholder back keeps the stored value, an empty
   value clears it.

   .. note:: Renaming a header keeps its value, including a secret one.

TLS
   Certificate verification is **on** by default and should stay on. A **CA
   bundle** path may be given for an endpoint with a private CA; it is only
   consulted while verification is on.

Proxy
   Separate proxies for ``http://`` and ``https://`` targets.

Timeout
   Seconds to wait for the endpoint, 3 by default. See
   :ref:`webhook_synchronous` for why this matters more than it looks.

Testing a webhook
~~~~~~~~~~~~~~~~~

The **Test** button fires the **stored** configuration once and reports the
status code and the (truncated) response body. The request really goes out, so
testing a production endpoint has real side effects. Save your changes first -
the button is disabled while the form has unsaved ones, because it would
otherwise report on a configuration other than the one on screen.

.. _webhook_synchronous:

Delivery is synchronous
~~~~~~~~~~~~~~~~~~~~~~~

A webhook is delivered **synchronously, with no retries**. The request that
triggered it waits for the endpoint, bounded by the webhook's timeout.

Pointing a webhook at a slow endpoint therefore adds that much latency to every
triggering request. This is most pronounced for a :ref:`conditional_access`
``WEBHOOK`` action, which fires inside the authentication request itself: a
webhook with a 10 second timeout pointed at a host that does not answer adds 10
seconds to the authentication of the user who tripped the policy.

A failing webhook never fails its caller. The failure is logged and reported,
the authentication and the remaining event handler actions continue.

Payload placeholders
~~~~~~~~~~~~~~~~~~~~

The payload a call site supplies may contain ``{placeholders}``. Which ones are
available depends on the call site - see :ref:`webhookhandler` and
:ref:`conditional_access_policies`. Unknown placeholders are left as written.

A payload that is a JSON object or array is substituted value by value, so a
placeholder carrying a quote cannot break the document. Anything else is
substituted as plain text.

.. _webhook_outbound_guard:

The outbound request guard
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. index:: outbound request guard, SSRF

A webhook URL is chosen by an administrator, and privacyIDEA requests it from
the server. An administrator holding :ref:`policy_webhook_write` can therefore
make the server issue requests to any host it can reach, including hosts on
internal networks that are not reachable from outside (a *server-side request
forgery* surface).

The outbound request guard narrows that. It is configured in :ref:`cfgfile` and
is **off by default**, so an upgrade changes nothing until you opt in::

    PI_OUTBOUND_GUARD = "warn"
    PI_OUTBOUND_GUARD_ALLOW = ["10.1.2.0/24", "siem.corp:8443"]

``PI_OUTBOUND_GUARD``
   ``off``
      The default. No checks at all, byte for byte the behaviour of privacyIDEA
      3.14 and older.

   ``warn``
      Every check runs and a rejection is written to the log, but the request is
      still sent and redirects are still followed. A trial run: it tells you what
      ``enforce`` would refuse without refusing it yet.

   ``enforce``
      A rejected request is not sent, and redirects are not followed - a
      redirect target was never checked, so following one would defeat the
      guard. An endpoint that answers with a redirect is therefore reported as a
      failed delivery.

   An unrecognised value is logged and treated as ``off``.

The guard resolves the target host and refuses an address in a blocked range:
loopback, the unspecified addresses, RFC1918 private space, link-local
(which covers the cloud metadata endpoint ``169.254.169.254``), carrier-grade
NAT, IPv6 unique-local. When a proxy is used, the **proxy** is checked rather
than the destination - that is where the connection actually goes, and the
destination is resolved by the proxy rather than by privacyIDEA. This covers a
proxy out of the server's environment (``http_proxy`` / ``https_proxy``) as well
as one configured on the webhook, and it honours ``no_proxy``.

It applies to an event handler that still carries its URL inline, from before
webhooks became configuration objects, just as it does to a webhook object.

``PI_OUTBOUND_GUARD_ALLOW``
   Exceptions, checked against both the configured host name and every address
   it resolves to. An entry is either a CIDR network (``10.1.2.0/24``) or a host
   or address with an optional port (``siem.corp:8443``, ``10.1.2.3``, ``::1``).
   Bracket an IPv6 address only to give it a port (``[::1]:8443``). An entry that
   cannot be parsed matches nothing.

.. note:: The guard resolves the host and then connects, so a name that resolves
   differently between those two moments is not covered (*DNS rebinding*). It
   raises the cost of reaching an internal host; it does not replace treating
   :ref:`policy_webhook_write` as a sensitive right.

Secrets
~~~~~~~

The basic authentication password, the client key password and the values of
headers marked as secret are **encrypted at rest** with the installation's
encryption key. They are never returned in clear text: the API and the WebUI
show ``__CENSORED__``, and so does an export.

Importing an export that carries ``__CENSORED__`` keeps an existing secret and
leaves an unknown one empty - a censored export never wipes a stored credential,
and never carries one to another installation either. Such a secret has to be
entered once on the target system.

A URL may itself embed a token, so privacyIDEA never writes a webhook URL to the
log: the log names the identifier and the status code. Where a transport error
quotes the URL it failed on, its path and query are removed before the message
is logged, returned or written to the audit log.
