.. _api_clients:

API clients and "remember this device"
======================================

.. index:: API clients, API key, remember device

An **API client** is a machine identity for an integration that talks to
privacyIDEA — a Windows credential provider, a Keycloak or ADFS plugin, an Entra
ID connector, and so on. The client authenticates with an **API key** sent in
the ``X-API-Key`` HTTP header, independent of any user session, so that
privacyIDEA can recognize which integration sends a request. In this version
that is only used for "remember this device": policies cannot be restricted to an
API client, and the audit log does not record which client made a request. Only
a request with a suspended key is recorded in the audit and the authentication
log.

On top of API clients, privacyIDEA offers a persistent **"remember this device"**
mechanism: after a full authentication, a client can obtain a rotating cookie and
later ask privacyIDEA whether the device is recognized, so it can skip the second
factor on subsequent logins.

Both features are **off by default** and gated by policy.

.. versionadded:: 3.14


Managing API clients
---------------------

API clients are managed in the WebUI or over the ``/clients`` REST API.
The admin actions :ref:`policy_api_client_list`, :ref:`policy_api_client_add`,
:ref:`policy_api_client_edit`, :ref:`policy_api_client_delete` and
:ref:`policy_api_client_rotate` control who may do what.

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
permanently, delete it (which also removes its remembered devices); to
replace a compromised key, rotate it.

An absent, unknown or inactive ``X-API-Key`` simply leaves the request
*unidentified* — existing integrations that send no key are unaffected. Endpoints
that require an identified client enforce it themselves.


"Remember this device"
----------------------

The remember-device feature lets a client skip the second factor for a device it
has seen before. This is a convenience trade-off, not a free one - requiring the
second factor on every login is always the stronger posture. What the rotating
cookie does provide is that a stolen cookie is detectable (theft invalidates the
series) and revocable, so the reduced friction does not come with an
undetectable, unrevocable long-lived token.

Enabling it
~~~~~~~~~~~

Set the :ref:`policy_remember_device` policy (scope *authentication*). It is
fail-closed — without the policy, no cookie is ever issued. Because it is a
normal policy, you can scope it by realm, user or other conditions. The cookie
lifetime defaults to 30 days and can be set per scope with
:ref:`policy_remember_device_validity`, for example to a few hours. A device
that is not used for a while can be forgotten before that with
:ref:`policy_remember_device_idle_timeout`.

Each opt-in creates a new remembered device, so a client that opts in on every
login (rather than once per device) accumulates them until they expire. If that
matters, cap it per user with :ref:`policy_remember_device_max_devices`.

The feature only works for requests made by an identified API client. A client
can discover whether it is available with :http:get:`/validate/capabilities`.

.. note:: ``capabilities`` answers at the **client** level ("is the feature
   available to me?"). Whether it applies to a specific user is decided when a
   cookie is issued and recognized, so a policy scoped to particular users or
   realms may still report ``true`` to the client.

Issuing the cookie
~~~~~~~~~~~~~~~~~~

On a successful :http:post:`/validate/check` where the client sends
``request_persistent_cookie=1``, privacyIDEA issues a cookie when a token of the
user verified the request, the client is identified, the policy allows it and
the authenticating user is resolvable. A login that a policy accepts without a
token gets no cookie, for example through :ref:`passonnotoken`,
:ref:`passonnouser`, :ref:`passthru_policy` or the :ref:`policy_auth_cache`. The
cookie is ``HttpOnly`` + ``Secure`` + ``SameSite=Strict``, carries both a
relative ``Max-Age`` and an ``Expires`` (a non-browser client should rely on
``Max-Age``), and holds only a
rotating ``series_id:counter`` token — **never** the API key.

.. _api_clients_recognizing_device:

Recognizing the device
~~~~~~~~~~~~~~~~~~~~~~~

On a later login the client calls :http:post:`/validate/remember_device` with the
stored cookie and the user. This is **not an authentication**: it verifies no
credential, triggers no challenge, and is recorded under its own audit action. It
simply answers whether the device is recognized, and the calling client decides
whether to skip the second factor (enforcing the first factor remains the
client's responsibility).

On a hit the cookie is **rotated** (the counter is incremented) and a new cookie
is returned; the client must store it. A remembered device is bound to the user's
resolver-stable identity (resolver, user id and realm), not to the login name,
so a remembered device survives a login rename and is never recognized for a
*different* account that later reuses a freed login. Recognition also confirms
the bound user still resolves, so deleting or removing a user revokes their
remembered devices.

Recognition is subject to :ref:`conditional_access`, because a recognized device
is what lets a client skip the second factor. While a user lock or a source-IP
block is in force - or a policy's *deny* action decides the request - the answer
is "not recognized", and the presented cookie is not read at all: it is neither
rotated nor cleared, so the device is recognized again once the restriction
lifts. The client is told only what was configured on
the policy, exactly as at ``/validate/check``; with nothing configured the
*body* of a refusal is identical to that of an ordinary miss.

.. note:: The match is not perfect, and deliberately so. A miss on a dead cookie
   clears it (a ``Set-Cookie`` with a past expiry) while a refusal leaves the
   cookie alone, so a caller that already holds a **valid API key** can tell the
   two apart by the presence of that header, and could use it to learn which
   accounts are locked. Closing this would mean clearing the cookie on every
   refusal, which would cost the user their remembered device on every temporary
   lock — a worse trade against a party that is already trusted enough to hold a
   key, and that can learn the same thing from ``/validate/check``.

A remembered device stands in for the second factor, so it is only recognized
while the user still has a token that can be used for a login. Such a token
passes the checks that a login applies to it:

* It is active and not revoked, within its validity period and fully enrolled.
  Neither its fail counter nor its authentication counters are exceeded.
* Its type can verify a login. An SSH key token and a certificate token cannot.
  An application-specific password does not count either, because the request
  carries no service ID.
* The token restrictions of the policies allow it. These are
  :ref:`policy_disabled_token_types` in the authentication scope and
  :ref:`tokentype_policy`, :ref:`serial_policy`, :ref:`policy_tokeninfo` and
  :ref:`policy_last_auth` in the authorization scope.

A user whose tokens are all disabled, revoked, removed, locked or excluded by
these policies gets "not recognized" from a remembered device as well. As with
conditional access, the cookie is neither rotated nor cleared and the device is
kept, so it can be recognized again once a token of the user is usable. The same
holds while :ref:`policy_remember_device_idle_timeout` policies of the same
priority set different values. To end the devices for good, revoke them (see
below).

A remembered device is also not recognized while :ref:`policy_auth_max_fail` or
:ref:`policy_auth_max_success` refuses a login of the user. The device is kept in
the same way. A recognition is not an authentication, so it does not count
toward these limits.

These checks apply only to a live device. The cookie is checked first, so a
replayed cookie, a dead cookie and an idle device are handled in the same way,
whatever the state of the user's tokens. While the idle timeout policies
conflict, no device counts as idle. A refusal is not a recognition, so a device
still expires and becomes idle while its recognition is refused, also by
conditional access.

On a miss the answer is simply "not recognized". The cookie is only cleared (a
``Set-Cookie`` with a past expiry) when it is genuinely dead - an unknown or
expired series, or a detected theft. If the presented cookie is still live but
belongs to a *different* user of the same client (a shared browser, where the
cookie is a single browser-level value), it is a **soft miss**: the cookie is
left untouched so that one user logging in does not wipe another user's
remembered device.

.. note:: Not clearing on a wrong-user miss is deliberate and does not weaken
   security. A foreign cookie is never *recognized* (the user must match), the
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
counter is the hallmark of a replayed or cloned cookie, and is treated as a
compromise of the user's browser rather than of the one series that happened to
be replayed: **every** remembered device of that user is revoked, on every
client, so neither the attacker nor the legitimate client can use any of them
again. Each of the user's devices must then re-register, including those
registered through other integrations.

The detection is recorded as a ``DEVICE_TOKEN_REUSED`` authentication event, so a
:ref:`conditional_access` policy can act on it. A replay is a security incident
rather than a failed guess, which is why the ready-made failed-attempt templates
leave the event out and why a threshold of one is the sensible setting for it.
The templates *Per-User Rate Limit* and *Per-IP Rate Limit (Distinct Accounts)*
count every attempt and include it.

.. warning:: Consider carefully what that one event should *do*. Notifying an
   administrator at a threshold of one is safe. **Locking** the account at a
   threshold of one is not, because the detection has a benign false positive
   that no configuration removes: a client whose rotation response was lost
   retries with the counter it still holds, and after the grace window that is
   indistinguishable from a replay. With a lock in place, one dropped HTTP
   response on a flaky connection costs the user every remembered device *and*
   an account lockout only an administrator (or the timer) can lift. Start with
   a notification, and lock only where the population and the network make that
   trade worth it.

A narrow exception tolerates concurrent requests: the immediately-previous
counter is accepted, from the same source IP, within
:ref:`ini_remember_device_grace` seconds, without rotating. Widening that window
is the first knob to reach for against false positives; it trades
theft-detection tightness for fewer of them. The user is never wrongly
authenticated either way.

The source IP is the client IP privacyIDEA determines for the request. Without
further configuration that is the address of the integration, which is the same
for every user behind it, so for such an integration the exception is only
bounded by time. If the integration passes the end user's address (as ``client``
parameter or in ``X-Forwarded-For``) and :ref:`override_client` allows that for
the integration, the duplicate request has to come from the address the device
was last seen at, and the list of remembered devices shows the end users'
addresses. Configuring the override this way is recommended for integrations
that can pass the address. Turning it on or off later does not affect the
remembered devices: a recognition with the current counter does not compare
addresses, and it records the new one.


.. _api_clients_revoking_devices:

Viewing and revoking remembered devices
----------------------------------------

Each remembered device is bound to a client and the user's resolver-stable
identity (resolver, user id and realm). An administrator with
:ref:`policy_remembered_device_list` can view a client's remembered devices — in
the WebUI on the client's *Remembered devices* view, or over
:http:get:`/clients/(client_id)/remembered_devices`. Each device is identified by
a non-secret ``device_id``; the cookie's secret ``series_id`` is never returned,
so viewing a device never exposes a usable credential.

The remembered devices of one user on all clients are listed on the user's
details page in the WebUI, or over :http:get:`/clients/remembered_devices` with
``user`` and ``realm``. There each device also names the client it is
remembered for, which helps when offboarding a user.

Revoking (which requires :ref:`policy_remembered_device_revoke`) invalidates the affected
device cookies immediately, and comes in two forms:

* a single device, with :http:delete:`/clients/(client_id)/remembered_devices/(device_id)`;
* all of a client's remembered devices at once, with
  :http:delete:`/clients/(client_id)/remembered_devices` — optionally narrowed to one
  ``realm`` or to one ``user`` (together with ``realm``). This is a single
  atomic, server-side delete scoped to the client, so it also catches devices
  created between listing and revoking — useful for incident response ("re-MFA
  every remembered device for this realm now");
* all remembered devices of a realm, or of one ``user`` in it, on every client,
  with :http:delete:`/clients/remembered_devices`. The user's details page in the
  WebUI offers this for the user.

.. note:: The IP address shown for a device is the client IP privacyIDEA
   determined for the request: the address of the integration, or the end user's
   address if the integration passes it (as ``client`` parameter or in
   ``X-Forwarded-For``) and :ref:`override_client` allows that for the
   integration. The user agent is the plugin name from the integration's
   ``User-Agent`` header, not the end user's browser or device.

Remembered devices are also removed automatically when they expire, when the
client is deleted, or on theft detection. A device of a user who no longer
resolves, e.g. after the user was deleted from the user store, is no longer
recognized; its row is removed when it expires. Expired rows are reclaimed by a
periodic cleanup (``pi-manage config remembered_device cleanup``), shipped as a daily
job in the Ubuntu packages and the Docker image, see :ref:`cleanup_jobs`.
