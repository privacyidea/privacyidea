.. _api_clients:

API clients and "remember this device"
======================================

.. index:: API clients, API key, remember device

An **API client** is a machine identity for an integration that talks to
privacyIDEA — a Windows credential provider, a Keycloak or ADFS plugin, an Entra
ID connector, and so on. The client authenticates with an **API key** sent in
the ``X-API-Key`` HTTP header, independent of any user session, so that
per-client behaviour can be configured and audited.

On top of API clients, privacyIDEA offers a persistent **"remember this device"**
mechanism: after a full authentication, a client can obtain a rotating cookie and
later ask privacyIDEA whether the device is recognised, so it can skip the second
factor on subsequent logins.

Both features are **off by default** and gated by policy.

.. versionadded:: 3.14


Managing API clients
---------------------

API clients are managed in the WebUI or over the ``/clients`` REST API.
The admin actions :ref:`policy_clients_list`,
:ref:`policy_clients_add`, :ref:`policy_clients_delete` and
:ref:`policy_clients_rotate` control who may do what.

The API key has the form ``pi_<key_id>_<secret>``:

* ``key_id`` is a public, indexed identifier used to look the client up. It is
  safe to display and log.
* ``secret`` is high-entropy and is **never stored**; only an HMAC-SHA256 of it
  (keyed with the server's ``PI_PEPPER``) is kept.

The plaintext key is therefore shown **exactly once**, right after the client is
created or its key is rotated. If it is lost, rotate the key to generate a new
one — rotation invalidates the previous key immediately.

A client has a status of ``active`` or ``suspended``; only ``active`` clients
authenticate. ``suspended`` is a reversible off-switch. To remove a client
permanently, delete it (which also removes its remembered-device sessions); to
replace a compromised key, rotate it.

An absent, unknown or inactive ``X-API-Key`` simply leaves the request
*unidentified* — existing integrations that send no key are unaffected. Endpoints
that require an identified client enforce it themselves.


"Remember this device"
----------------------

The remember-device feature lets a client skip the second factor for a device it
has seen before, without weakening security: a stolen cookie is detectable and
revocable.

Enabling it
~~~~~~~~~~~

Set the :ref:`policy_remember_device` policy (scope *authentication*). It is
fail-closed — without the policy, no cookie is ever issued. Because it is a
normal policy, you can scope it by realm, user or other conditions. The cookie
lifetime defaults to 30 days and can be set per scope with
:ref:`policy_remember_device_validity`.

The feature only works for requests made by an identified API client. A client
can discover whether it is available with :http:get:`/validate/capabilities`.

.. note:: ``capabilities`` answers at the **client** level ("is the feature
   available to me?"). Whether it applies to a specific user is decided when a
   cookie is issued and recognised, so a policy scoped to particular users or
   realms may still report ``true`` to the client.

Issuing the cookie
~~~~~~~~~~~~~~~~~~

On a successful :http:post:`/validate/check` where the client sends
``request_persistent_cookie=1``, privacyIDEA issues a cookie when the client is
identified, the policy allows it and the authenticating user is resolvable. The
cookie is ``HttpOnly`` + ``Secure`` + ``SameSite=Strict``, carries both a
relative ``Max-Age`` and an ``Expires`` (a non-browser client should rely on
``Max-Age``), and holds only a
rotating ``series_id:counter`` token — **never** the API key.

Opt in **once per device** (the establishing login), not on every request: each
opt-in creates a new session, so opting in on every login accumulates sessions.

Recognising the device
~~~~~~~~~~~~~~~~~~~~~~~

On a later login the client calls :http:post:`/validate/remember_device` with the
stored cookie and the user. This is **not an authentication**: it verifies no
credential, triggers no challenge, and is recorded under its own audit action. It
simply answers whether the device is recognised, and the calling client decides
whether to skip the second factor (enforcing the first factor remains the
client's responsibility).

On a hit the cookie is **rotated** (the counter is incremented) and a new cookie
is returned; the client must store it. Recognition also confirms the bound user
still exists, so deleting or removing a user revokes their remembered devices.

On a miss the answer is simply "not recognised". The cookie is only cleared (a
``Set-Cookie`` with a past expiry) when it is genuinely dead - an unknown or
expired series, or a detected theft. If the presented cookie is still live but
belongs to a *different* user of the same client (a shared browser, where the
cookie is a single browser-level value), it is a **soft miss**: the cookie is
left untouched so that one user logging in does not wipe another user's
remembered device.

.. note:: Not clearing on a wrong-user miss is deliberate and does not weaken
   security. A foreign cookie is never *recognised* (the user must match), the
   cookie is a bearer token that possession already governs, and theft detection
   only ever acts on the owning user's series - so the soft miss changes none of
   those. Clearing a remembered device when a *different* user appears is not a
   reliable shared-machine control; the honest levers for shared or public
   browsers are to not enable ``remember_device`` there, to use a short
   :ref:`policy_remember_device_validity`, or a future user-bound
   "remember this browser" feature.

Theft detection
~~~~~~~~~~~~~~~

The counter must match the value stored server-side. Presenting a **stale**
counter (the hallmark of a replayed or cloned cookie) causes the whole session
series to be deleted, so neither the attacker nor the legitimate client can use
it again; the device must then re-register.

A narrow exception tolerates concurrent requests: the immediately-previous
counter is accepted, from the same source IP, within
:ref:`ini_remember_device_grace` seconds, without rotating. This is an accepted
trade-off — a legitimate client whose rotation response was lost and that retries
*after* the grace window is treated as theft and must re-register; the user is
never wrongly authenticated.


Viewing and revoking sessions
-----------------------------

Each remembered device is a session bound to ``(client, user)``. An administrator
with :ref:`policy_clients_list` can view a client's sessions — in the WebUI on the
client's *Sessions* view, or over :http:get:`/clients/(client_id)/sessions` — and
revoke individual ones with :http:delete:`/clients/(client_id)/sessions/(series_id)`.
Revoking a session invalidates that device's cookie immediately.

.. note:: The IP address and user agent shown for a session are those of the API
   client's request. For a centralised integration such as an IdP that is the
   integration itself, not the end user's browser or device.

Sessions are also removed automatically when they expire, when the user or the
client is deleted, or on theft detection. Expired rows are reclaimed by a
periodic cleanup (``pi-manage config authsession cleanup``), shipped as a daily
job in the packaged crontab.
