.. index:: Authentication log
.. _authentication_log:

Authentication Log
==================

The authentication log records the outcome of every authentication request:
what was attempted, by whom, from where, and how it ended. It is the data
:ref:`conditional_access_policies` count, and it is readable on its own under
*Logs → Authentication log*.

It is separate from the :ref:`audit` log. The audit log records *what the API
did*, in free text, for every call. The authentication log records *how an
authentication ended*, one entry per request, with a fixed set of event types
that can be filtered and counted reliably. There are two exceptions. With
:ref:`policy_push_wait` one request writes two entries: one when the challenge
is triggered and one for the outcome, if the challenge was answered or declined
before the wait ended. And a request that carries the API key of a suspended
client gets an additional ``SUSPENDED_API_KEY_USED`` entry, see
:ref:`authentication_log_event_types`.

Each entry holds

* the time of the request,
* the user, as resolver, user ID, realm and the login name that was used, plus
  the role (user, internal or external administrator),
* the event type and, for a failed one, the reasons behind it, see below,
* the source IP, the client description and the endpoint the request
  authenticated against,
* the token serial, the transaction ID and the attempt ID,
* what conditional access did to this request, if anything,
* additional details, such as the part of an over-long value that did not fit
  its column.

The user is recorded by resolver, user ID and realm, so entries stay
attributable after a rename. The login name is recorded as well and doesn't change on a rename.
For non-existing users, the used login name and realm are recorded as well. The realm might not be passed explicitly,
but defaults to the default realm.

.. _authentication_log_attempts:

Attempts
--------

A challenge-response login takes several requests, e.g. one that triggers the
challenge and one that answers it. These share an **attempt ID**, so they can be
recognized as one logical authentication attempt, and a conditional access policy
using the ``PER_ATTEMPT`` count mode counts them once.

The attempt ID also survives a multi-challenge login, where answering one
challenge triggers the next one and the transaction ID changes. Filtering the
log on an attempt ID therefore shows the whole chain.

.. _authentication_log_event_types:

Event types
-----------

Every entry carries exactly one event type. Each type belongs to an outcome
class - *success*, *failure* or *pending* - which the WebUI uses to color the
entry.

Success
   ``LOGIN_SUCCESS``
     the authentication completed.

Pending
   ``CHALLENGE_TRIGGERED``
     a challenge was created.
   ``CHALLENGE_CONTINUED``
     a challenge was answered correctly, which triggered a new challenge required to be answered.
   ``CHALLENGE_ANSWERED_OUT_OF_BAND``
     a challenge was approved out of band, for example a push notification
     confirmed in the authenticator app.
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
     the login name was not found in any resolver of the given realm (or default realm if none were given).
   ``NO_TOKEN``
     the user exists but has no token. It is also recorded for a passkey answer whose serial or credential ID matches
     no token, or a token of another user than the one named in the request, and at ``/validate/triggerchallenge``
     whenever no challenge was triggered - also when the user has tokens, but none that is active, not revoked, not
     locked and able to do challenge-response. A user whose only token is disabled therefore gets ``NO_TOKEN`` there,
     not ``NO_USABLE_TOKEN``.
   ``NO_USABLE_TOKEN``
     the user has tokens, but none of them can be used for the authentication as they are revoked, disabled, expired or
     over the failcount.
   ``INVALID_TOKEN_TYPE``
     the given token type can not be used to authenticate at this endpoint, e.g. ``/validate/initialize`` only accepts
     passkeys.
   ``CHALLENGE_ANSWERED_FAIL``
     the challenge response was wrong or expired, or the transaction ID is unknown.
   ``CHALLENGE_TRIGGER_FAIL``
     ``/validate/initialize`` could not create the passkey challenge, for
     example because the :ref:`policy_webauthn_enroll_relying_party_id` policy
     is missing.
   ``CHALLENGE_DECLINED``
     a challenge was rejected out of band, for example a push notification
     declined in the authenticator app, without the app saying why. Either it is
     an older app that does not send a decline reason, or it sent one this
     server version does not know. It is also the type of the
     ``/validate/check`` a client sends to finalize a push challenge the user
     declined for any reason other than canceling it (see
     ``CHALLENGE_CANCELLED``): the decline reason is only recorded on the
     ``/ttype/push`` entry. A push declined as not triggered by the user is
     therefore ``CHALLENGE_DECLINED_UNKNOWN_TRIGGER`` on ``/ttype/push`` and
     ``CHALLENGE_DECLINED`` on the finalizing request.
   ``CHALLENGE_DECLINED_UNKNOWN_TRIGGER``
     the user rejected a push challenge stating that they did not trigger it.
     This is the user reporting someone else's attempt rather than a credential
     the server found wrong, and the statement is signed by the smartphone, so
     whoever triggered the challenge can neither forge nor suppress it. Worth a
     policy of its own with a low threshold: if the challenge came from
     ``/validate/check``, the first factor was already accepted, so somebody
     else is holding a working credential.
   ``CHALLENGE_CANCELLED``
     the user aborted a push challenge they triggered themselves. Abandonment
     rather than a failed attempt, which is why the ready-made failure rate
     limits leave it out - counting it would spend part of a brute-force budget
     on users changing their mind. If the client then finalizes the canceled
     push with ``/validate/check``, that request is recorded as
     ``CHALLENGE_CANCELLED`` as well.
   ``ENROLLMENT_CANCELED_FAIL``
     canceling an enrollment failed.
   ``ENROLLMENT_FAIL``
     completing the enrollment of a token during authentication failed, for
     example of a passkey with :ref:`policy_enroll_via_multichallenge`. Either a
     required enrollment policy is missing, or the registration data from the
     authenticator was rejected. The ready-made failure rate limits leave it out.
   ``NOT_AUTHORIZED``
     an authorization policy or the server configuration refused the authentication.
   ``UNKNOWN_FAIL_REASON``
     the authentication failed and nothing more specific was determined. This is only used as fallback and should
     usually not be seen.
   ``DEVICE_TOKEN_REUSED``
     a "remember this device" cookie was replayed with a stale counter - a sign the cookie was stolen. The whole
     device series, and every other remembered device of this user, is revoked.
   ``SUSPENDED_API_KEY_USED``
     a request carried a valid API key whose client is suspended. The request is not identified by it and proceeds
     unauthenticated by that key. This entry is written in addition to the entry of the request itself, on whatever
     endpoint the request was sent to - also outside authentication, for example ``/token``. It names no user; the
     client is recorded in the other info as ``client_id``. A conditional access policy cannot count it.

Three further types are written by conditional access itself, when it refuses a
request before any credentials are checked: ``USER_LOCKED`` (a user lock was in
force), ``IP_BLOCKED`` (a source-IP block was in force) and ``ACCESS_DENIED`` (a conditional access
policy's *deny* action refused this single request).

These entries record that the refusal happened, and can be filtered and sorted
like any other, so an administrator can see how often a lock or block took
effect. They and ``SUSPENDED_API_KEY_USED`` are, however, the only types a
conditional access policy cannot count.

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

A policy or the server configuration refusing the request
   ``AUTHORIZATION_DENIED``
     an authorization policy turned the request away outright
     (``authorized=deny``); the next three are authorization decisions too,
     each naming the specific limit that was hit.
   ``AUTH_MAX_FAIL``
     too many failed attempts inside the policy's time limit, see
     :ref:`policy_auth_max_fail`.
   ``AUTH_MAX_SUCCESS``
     too many successful authentications inside the policy's time limit.
   ``LAST_AUTH_TOO_OLD``
     the token's last successful authentication is too long ago.
   ``LOGIN_MODE_DISABLED``
     the login to the WebUI is disabled for the user, see
     :ref:`policy_login_mode`.
   ``WEBUI_PASSKEY_LOGIN_DISABLED``
     a login to the WebUI without a username was refused because
     ``WEBUI_PASSKEY_LOGIN_ENABLED`` is switched off in the :ref:`cfgfile`.

The credentials
   ``WRONG_OTP``
     the first factor was right, or not required, but the OTP was not. A wrong
     first factor gets no reason of its own: the event type already names the
     credential that failed (``PASSWORD_FAIL``, ``PIN_FAIL``), while
     ``MFA_FAIL`` alone would not tell a wrong OTP apart from a token the
     request never got to check.

Challenge-response
   ``CHALLENGE_WRONG_RESPONSE``
     the response did not match the challenge.
   ``CHALLENGE_UNKNOWN_TRANSACTION``
     the transaction holds no challenge for this token: already consumed,
     belonging to another token, or never issued.
   ``CHALLENGE_EXPIRED``
     the challenge had lapsed when the response arrived.
   ``TOKEN_NOT_FIT_FOR_CHALLENGE``
     the response matched, but the token may no longer complete the challenge:
     its state changed between the trigger and the answer. That check is the
     same one every token passes before it is used at all, so the entry normally
     names the state itself - one of the token states above, such as a token
     disabled or a failcounter filled up in the meantime. This reason is the
     fallback for a token type that refuses the answer without naming a state.
   ``CHALLENGE_DECLINED_ON_DEVICE``
     the challenge was rejected on the device. Carried by all three decline
     event types and says only where the refusal came from; which refusal it was
     is what the event type names.

A successful authentication needs no reason, and neither does one still in
flight. An entry is also without one where nothing determined a cause, so no
reason reads as *not classified* rather than *no cause*.

Which reasons an entry carries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A request is checked against every token of the user, and those tokens can fail
for different reasons. The reasons of an entry explain its event type: they are
taken from the tokens that produced that event, and each is filterable on its
own. A request whose one token is revoked while another merely got the wrong
OTP is classified by the wrong OTP, for example as ``MFA_FAIL`` with the reason
``WRONG_OTP``; the filter ``TOKEN_REVOKED`` does not find it. Only where no
token produced an event - a ``NO_USABLE_TOKEN``, where every token was turned
away before it was checked - does the entry carry the reasons of all tokens,
for example ``TOKEN_DISABLED`` for one token and ``TOKEN_FAILCOUNT_EXCEEDED``
for another. A token that produced the event without a reason of its own, such
as one with a wrong PIN, leaves the entry without one.

No reason is picked out as the one that counts: they are listed in the order
the vocabulary above declares them - the token states, then the authorization
decisions, then the credentials, then challenge-response - so that the same
findings always read the same way. The order carries no ranking; each reason is
recorded and each is filterable on its own.

Which token failed for which reason is not lost either: the details of the
entry keep the finding of every token under ``reason_detail.reasons``, keyed by
serial, also for the tokens whose reasons are not on the entry, and the names of
the policies that decided under ``reason_detail.policies``.

.. note:: ``CHALLENGE_EXPIRED`` tells a timeout apart from a wrong answer - the
   user answered correctly, only too late. Recognizing it depends on the lapsed
   challenge still being readable, which is best-effort: stored in the database
   a challenge stays until ``pi-manage config challenge cleanup`` removes it
   (see :ref:`cleanup_jobs`), while the Redis cache expires
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
``/validate/remember_device``
  an application asking whether a device is remembered, so that it may skip the
  second factor. This is not an authentication and writes no entry of its own
  when it succeeds; it appears here when a replayed device cookie was detected
  (``DEVICE_TOKEN_REUSED``) and when a lock, a block or a *deny* action turned
  the request away.
``/ttype/push``
  a push challenge answered on the smartphone, which reaches the server out of
  band.

Every authentication reaches the server as a request, so an entry written by an
authentication always names its endpoint; the column is empty only for an entry
staged outside a view. A ``SUSPENDED_API_KEY_USED`` entry names the path of
whatever request carried the key, which need not be one of the endpoints above.
The recorded endpoint is what an *Endpoint* condition of a conditional access
policy is matched against, see :ref:`conditional_access_policies`, so a policy
can be limited to the endpoints it should watch: counting the failed
authentications of an application without counting WebUI logins, for instance.

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
column except the user role, the IP chain, the reasons, the conditional-access
outcomes and the other info: the reasons and the outcomes each hold a list per
entry rather than a single value, and the IP chain and the other info are
excluded because ordering by JSON content is neither meaningful nor portable.
Any other sort column is not refused; the entries are then sorted by their ID.

The *Conditional access* column filters on what conditional access did: the
action type, the name of the policy that acted, and whether the outcome was a
dry run or enforced. Filtering on the action type with ``*`` shows every entry
conditional access acted on at all.

.. _authentication_log_statistics:

Summarizing the log
-------------------

:http:get:`/authenticationlog/statistics` answers "how did authentication go
lately" in one request, instead of paging through entries. It returns the
number of authentication **attempts** in a time window, grouped by the event
type that classifies each of them and bucketed over the window, which is what
the *Authentication activity* widget on the :ref:`dashboard` draws.

It counts attempts, not entries, and the difference is not cosmetic: a
challenge-response login writes both a ``CHALLENGE_TRIGGERED`` and a
``LOGIN_SUCCESS`` entry, so counting entries would report one successful login
as both a pending and a successful event. The entries sharing an attempt ID
(see :ref:`authentication_log_attempts`) are therefore reduced to the one that
classifies the whole attempt, by the same rule a ``PER_ATTEMPT`` policy uses:

* the ``LOGIN_SUCCESS`` entry if the attempt ever logged in, because a
  completed success is terminal;
* otherwise the **latest** entry of the attempt.

Which entry is latest is decided by insertion order, not by ranking the event
types. That is what tells a wrong answer *followed by* a new challenge (still
in progress) from a new challenge *followed by* a wrong answer (failed) - the
two contain the same event types in the same attempt.

Two consequences are worth knowing before reading the numbers:

* ``event_type`` selects attempts that **ended** that way, rather than every
  attempt that passed through such an event. It is the only meaning the filter
  can have once the entries of an attempt are collapsed into one.
* The three types conditional access writes for its own refusals -
  ``USER_LOCKED``, ``IP_BLOCKED`` and ``ACCESS_DENIED`` - classify attempts
  here like any other failure, because an attempt that was turned away did
  fail. Note that one lock can refuse many retries, so such a count follows
  retry volume rather than the number of locks; the locks themselves are
  counted on the conditional-access side.

An entry without an attempt ID counts as an attempt of its own, and an attempt
that began before the window is classified from the entries inside it alone -
the same edge a policy's sliding window has.

The window is given by ``start_time`` and ``end_time``, both required ISO 8601
timestamps and both inclusive, and ``bins`` sets how many equal-width buckets
the window is split into - between 1 and 100, 48 by default. Asking for more
than 100 is refused rather than quietly reduced, so a caller is never handed a
coarser resolution than it asked for without being told; a value that is not a
positive number at all falls back to the default. Every filter the log listing
accepts on an entry can be given as well, under the same plural name and with
the same comma-separated lists and ``*`` wildcards, for example
``event_types=MFA_FAIL,PIN_FAIL`` or ``realms=realm1``. The plural is the only
name recognized, so a query written in the singular - ``realm=realm1`` rather
than ``realms=`` - is no filter at all and the summary then covers every
attempt in the window. The filters apply to the entry that classifies each
attempt. The ``ca_*`` filters are not offered: they match what conditional
access did to a single request, which an attempt-level summary has no notion
of. Neither are ``peer_ips``, ``source_ip_sources`` and
``client_label_sources``, which describe how the client of an entry was derived
rather than the attempt. Given anyway, these filters are ignored, and the
summary covers every attempt the other filters match.

Who sees what
-------------

Reading the log requires the ``authentication_log_read`` right, see
:ref:`policy_authentication_log_read`.

If the administrator's policy is scoped to realms, resolvers or users, only
matching entries are returned; an administrator always also sees their own
entries. The same restriction applies to the summary described above, so a
scoped administrator's counts only cover the attempts they may read. Users
granted the right in the user scope see only their own entries, and the columns
identifying the user are hidden for them.

Whose entry is "their own" is decided by the account, not by the login name it
carries: an entry belongs to the resolver, user id and realm it was recorded
for. It therefore stays with the account when its login is renamed, and it is
never handed to a different account that is later given a freed login name.
Entries that resolved to no account at all - a login attempt for a name no
resolver knows, for instance - are nobody's own and only an administrator sees
them, as are the entries of an account that no longer resolves. A local
administrator has no such identity, having neither realm nor resolver, so their
own entries are matched by login name together with the internal-admin role.

.. _authentication_log_cleanup:

Cleaning up entries
-------------------

.. index:: retention time

The authentication log grows with every authentication request and is **not**
pruned automatically. Set up a cron job to enforce your retention period, using
:ref:`pi-manage <pimanage>`::

   pi-manage authlog cleanup --age 365

``--age`` is required and counts in days, so this deletes all entries older
than one year, together with the classified reasons and the conditional-access
outcomes recorded on them. Add ``--chunksize`` to delete in batches on a large
table, and ``--dryrun`` to see how many entries would be removed without
deleting anything.

The retention period is yours to choose, so this job is not scheduled by
default: the Ubuntu packages ship it commented out, and the Docker image runs it
only once ``PI_CRON_AUTHLOG_AGE`` is set, see :ref:`cleanup_jobs`.

.. note:: Deleting entries also removes them from the counts a conditional
   access policy makes. Keep the retention period comfortably longer than the
   longest time window you use in a policy.
