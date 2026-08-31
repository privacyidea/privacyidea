.. index:: Authentication log
.. _authentication_log:

Authentication log
==================

The authentication log records the outcome of every authentication request:
what was attempted, by whom, from where, and how it ended. It is the data
:ref:`lockout_policies` count, and it is readable on its own under
*Logs → Authentication log*.

It is separate from the :ref:`audit` log. The audit log records *what the API
did*, in free text, for every call. The authentication log records *how an
authentication ended*, one entry per request, with a fixed set of event types
that can be filtered and counted reliably.

Each entry holds

* the time of the request,
* the user, as resolver, user ID, realm and the login name that was used, plus
  the role (user, internal or external administrator),
* the event type and, for a failed one, every reason behind it, see below,
* the source IP, the client description and the endpoint the request
  authenticated against,
* the token serial, the transaction ID and the attempt ID,
* what conditional access did to this request, if anything,
* additional details, such as the part of an over-long value that did not fit
  its column.

The user is recorded by resolver, user ID and realm, so entries stay
attributable after a rename. A login naming a user that does not exist is still
recorded, with the attempted login name and no resolved user.

.. _authentication_log_attempts:

Attempts
--------

A challenge-response login takes several requests: one that triggers the
challenge and one that answers it. These share an **attempt ID**, so they can be
recognised as one logical authentication attempt, and a lockout policy using the
``PER_ATTEMPT`` count mode counts them once.

The attempt ID also survives a multi-challenge login, where answering one
challenge triggers the next one and the transaction ID changes. Filtering the
log on an attempt ID therefore shows the whole chain.

.. _authentication_log_event_types:

Event types
-----------

Every entry carries exactly one event type. Each type belongs to an outcome
class - *success*, *failure* or *pending* - which the WebUI uses to colour the
entry.

Success
   ``LOGIN_SUCCESS``
     the authentication completed.

Pending
   ``CHALLENGE_TRIGGERED``
     a challenge was created and sent to the client.
   ``CHALLENGE_CONTINUED``
     a challenge was answered correctly, but a further one is required.
   ``CHALLENGE_ANSWERED_OUT_OF_BAND``
     a push challenge was approved on the smartphone.
   ``ENROLLMENT_TRIGGERED``
     a successful authentication started the enrollment of a new token.

Failure
   ``PASSWORD_FAIL``
     wrong user store password.
   ``PIN_FAIL``
     wrong token PIN.
   ``TOKEN_ONLY_FAIL``
     no PIN was required, and the OTP value was wrong.
   ``MFA_FAIL``
     the first factor was correct but the second failed. Also used for a failed
     passkey authentication, where the cause cannot be determined.
   ``USER_UNKNOWN``
     the login name was not found in any resolver.
   ``NO_TOKEN``
     the user exists but has no token.
   ``NO_USABLE_TOKEN``
     the user has tokens, but every one is revoked, disabled, expired or over
     its failcount.
   ``INVALID_TOKEN_TYPE``
     the request named no token type this endpoint can authenticate with.
   ``CHALLENGE_ANSWERED_FAIL``
     the challenge response was wrong or expired, or the transaction is unknown.
   ``CHALLENGE_TRIGGER_FAIL``
     a challenge was requested but the server could not create one, for example
     because a required policy is missing.
   ``CHALLENGE_DECLINED``
     a push challenge was rejected on the smartphone.
   ``ENROLLMENT_CANCELED_FAIL``
     cancelling an enrollment failed.
   ``NOT_AUTHORIZED``
     an authorization policy refused the authentication.
   ``UNKNOWN_FAIL_REASON``
     the authentication failed and nothing more specific was determined.

Conditional access writes three further types for the requests it refuses
itself: ``USER_LOCKED``, ``IP_BLOCKED`` and ``ACCESS_DENIED``. They record why a
request was turned away, and they are the types a lockout policy cannot track,
see :ref:`lockout_policies`.

.. _authentication_log_reasons:

Why an event happened
---------------------

An event type says *what* happened to a request, and several different causes
share one type. ``NO_USABLE_TOKEN`` is the clearest case: it is the same event
whether every token of the user is disabled, past its failcount, outside its
validity period or not fully enrolled, which are four findings calling for four
different reactions. A failed entry therefore also carries its **reasons**,
which can be filtered like the event type.

The state of a token
   ``TOKEN_DISABLED``
     the token is disabled.
   ``TOKEN_REVOKED``
     the token is revoked, which is permanent.
   ``TOKEN_FAILCOUNT_EXCEEDED``
     the failcounter is at or past its maximum.
   ``TOKEN_AUTH_COUNTER_EXCEEDED``
     the token's own authentication counter is exhausted.
   ``TOKEN_OUTSIDE_VALIDITY_PERIOD``
     now is outside the token's validity period.
   ``TOKEN_NOT_YET_ENROLLED``
     the enrollment was never completed.
   ``TOKEN_TYPE_DISABLED``
     a policy disabled this token's whole type for the request.
   ``TOKEN_NOT_APPLICABLE``
     the token excluded itself from this request, for example an
     application-specific password whose service does not match.

A policy refusing an otherwise valid authentication
   ``AUTHORIZATION_POLICY``
     an authorization policy denied the request.
   ``AUTH_MAX_FAIL``
     too many failed attempts inside the policy's time limit, see
     :ref:`policy_auth_max_fail`.
   ``AUTH_MAX_SUCCESS``
     too many successful authentications inside the policy's time limit.
   ``LAST_AUTH_TOO_OLD``
     the token's last successful authentication is too long ago.

The credentials
   ``WRONG_USERSTORE_PASSWORD``
     the user store password was wrong.
   ``WRONG_TOKEN_PIN``
     the token PIN was wrong, or one was given where none was expected.
   ``WRONG_OTP``
     the first factor was right, or not required, but the OTP was not.

Challenge-response
   ``CHALLENGE_WRONG_RESPONSE``
     the response did not match the challenge.
   ``CHALLENGE_UNKNOWN_TRANSACTION``
     the transaction holds no challenge for this token: already consumed,
     belonging to another token, or never issued.
   ``CHALLENGE_EXPIRED``
     the challenge had lapsed when the response arrived.
   ``CHALLENGE_DECLINED_ON_DEVICE``
     the challenge was rejected on the device.
   ``TOKEN_NOT_FIT_FOR_CHALLENGE``
     the response matched, but the token may no longer complete a challenge.

A successful authentication needs no reason, and neither does one still in
flight. An entry is also without one where nothing determined a cause, so no
reason reads as *not classified* rather than *no cause*.

One entry, every reason
~~~~~~~~~~~~~~~~~~~~~~~

A request is checked against every token of the user, and those tokens can fail
for different reasons. The entry lists **all** of them, each filterable on its
own: a request whose one token is revoked while another merely got the wrong
OTP is found by either filter, because both are findings an admin may be
looking for.

They are ordered by how much they narrow down what to do about it, most
informative first: a policy decision outranks any token state, because it
applies whatever the tokens look like; a permanent state such as
``TOKEN_REVOKED`` outranks a transient one such as a failcounter that a reset
clears; and a wrong credential ranks below every state, since the state is what
made the credential moot.

Which token failed for which reason is not lost either: the details of the
entry keep the finding of every token under ``reason_detail.reasons``, keyed by
serial, and the names of the policies that decided under
``reason_detail.policies``.

.. note:: ``CHALLENGE_EXPIRED`` tells a timeout apart from a wrong answer - the
   user answered correctly, only too late. Recognizing it depends on the lapsed
   challenge still being readable, which is best-effort: stored in the database
   a challenge stays until the janitor removes it, while the Redis cache expires
   the key shortly after the challenge validity, so an answer arriving much
   later finds nothing and is recorded as ``CHALLENGE_UNKNOWN_TRANSACTION``.

.. _authentication_log_endpoints:

Which endpoint served the request
---------------------------------

Every entry records the endpoint the request authenticated against, as its
request path:

``/auth``
  the login of a user or an administrator, for example from the WebUI.
``/validate/check`` and ``/validate/radiuscheck``
  an authentication by an application or a RADIUS client.
``/validate/triggerchallenge``
  a challenge triggered by an administrator.
``/validate/initialize``
  the anonymous bootstrap of a FIDO2/passkey challenge before login.
``/ttype/push``
  a push challenge answered on the smartphone, which reaches the server out of
  band.

The column is empty for an event recorded outside a request, for example from
the command line. The same value is what an *Endpoint* condition of a lockout
policy is matched against, see :ref:`lockout_policies`, so a policy can be
limited to the endpoints it should watch: counting the failed authentications
of an application without counting WebUI logins, for instance.

Searching
---------

The log can be filtered in the WebUI and via ``GET /authenticationlog/`` on any
column. Every filter parameter takes a list of values, which is why it is named
in the plural while it matches one column: ``serials``, ``event_types``,
``reasons``, ``endpoints`` and so on. ``reasons`` is the one filter that does
not match a column: an entry has a list of reasons and matches if *any* of them
does. Filter values are matched as follows:

* A value without a wildcard must match the column exactly, and is
  case-sensitive unless the case-insensitive option is set.
* ``*`` matches any sequence of characters, for example ``serials=TOTP*``.
  Wildcard matching is always case-insensitive.
* Several values can be given as a comma-separated list, for example
  ``event_types=MFA_FAIL,PIN_FAIL``, matching entries equal to any of them.

The *Endpoint* and *Reasons* columns are filtered by selecting from the defined
values, which the WebUI reads from ``GET /authenticationlog/endpoints`` and
``GET /authenticationlog/reasons``.

A time range can be given in addition, and the result can be sorted by any
column except the reasons, the conditional-access outcomes and the details -
each of those is a list per entry rather than a single value.

The *Conditional access* column filters on what conditional access did: the
action type, the name of the policy that acted, and whether the outcome was a
dry run or enforced. Filtering on the action type with ``*`` shows every entry
conditional access acted on at all.

Who sees what
-------------

Reading the log requires the ``authentication_log_read`` right, see
:ref:`conditional_access_rights`.

If the administrator's policy is scoped to realms, resolvers or users, only
matching entries are returned; an administrator always also sees their own
entries. Users granted the right in the user scope see only their own entries,
and the columns identifying the user are hidden for them.

.. _authentication_log_cleanup:

Cleaning up entries
-------------------

.. index:: retention time

The authentication log grows with every authentication request and is **not**
pruned automatically. Set up a cron job to enforce your retention period, using
:ref:`pi-manage <pimanage>`::

   pi-manage authlog cleanup --age 365

This deletes all entries older than one year, together with the
conditional-access outcomes recorded on them. Add ``--chunksize`` to delete in
batches on a large table, and ``--dryrun`` to see how many entries would be
removed without deleting anything.

.. note:: Deleting entries also removes them from the counts a lockout policy
   makes. Keep the retention period comfortably longer than the longest time
   window you use in a policy.
