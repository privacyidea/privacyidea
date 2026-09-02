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
that can be filtered and counted reliably. The only exception is
:ref:`policy_push_wait`, where one request writes two entries: one when the
challenge is triggered and one for the outcome, if the challenge was answered
or declined before the wait ended.

Each entry holds

* the time of the request,
* the user, as resolver, user ID, realm and the login name that was used, plus
  the role (user, internal or external administrator),
* the event type, see below,
* the source IP and the client description,
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
recognised as one logical authentication attempt, and a conditional access policy
using the ``PER_ATTEMPT`` count mode counts them once.

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
     the user exists but has no token.
   ``NO_USABLE_TOKEN``
     the user has tokens, but none of them can be used for the authentication as they are revoked, disabled, expired or
     over the failcount.
   ``INVALID_TOKEN_TYPE``
     the given token type can not be used to authenticate at this endpoint, e.g. `/validate/initialize` only accepts
     passkeys.
   ``CHALLENGE_ANSWERED_FAIL``
     the challenge response was wrong or expired, or the transaction ID is unknown.
   ``CHALLENGE_TRIGGER_FAIL``
     a challenge was requested but the server could not create one, for example
     because a required policy is missing.
   ``CHALLENGE_DECLINED``
     a challenge was rejected out of band, for example a push notification
     declined in the authenticator app.
   ``ENROLLMENT_CANCELED_FAIL``
     cancelling an enrollment failed.
   ``NOT_AUTHORIZED``
     an authorization policy refused the authentication.
   ``UNKNOWN_FAIL_REASON``
     the authentication failed and nothing more specific was determined. This is only used as fallback and should
     usually not be seen.

Three further types are written by conditional access itself, when it refuses a
request before any credentials are checked: ``USER_LOCKED`` (a user lock was in
force), ``IP_BLOCKED`` (a source-IP block was in force) and ``ACCESS_DENIED`` (a conditional access
policy's *deny* action refused this single request).

These entries record that the refusal happened, and can be filtered and sorted
like any other, so an administrator can see how often a lock or block took
effect. They are, however, the only types a conditional access policy cannot
count.

Searching
---------

The log can be filtered in the WebUI and via ``GET /authenticationlog/`` on any
column. Filter values are matched as follows:

* A value without a wildcard must match the column exactly, and is
  case-sensitive unless the case-insensitive option is set.
* ``*`` matches any sequence of characters, for example ``serial=TOTP*``.
  Wildcard matching is always case-insensitive.
* Several values can be given as a comma-separated list, for example
  ``event_type=MFA_FAIL,PIN_FAIL``, matching entries equal to any of them.

A time range can be given in addition, and the result can be sorted by any
column except the conditional-access outcomes and the other info.

The *Conditional access* column filters on what conditional access did: the
action type, the name of the policy that acted, and whether the outcome was a
dry run or enforced. Filtering on the action type with ``*`` shows every entry
conditional access acted on at all.

.. _authentication_log_statistics:

Summarising the log
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
the window is split into. Every filter the log listing accepts on a column of
its own row can be given as well, under its plural name and with the same
comma-separated lists and ``*`` wildcards, for example
``event_types=MFA_FAIL,PIN_FAIL`` or ``realms=realm1``. The filters apply to the
entry that classifies each attempt. The ``ca_*`` filters are not offered: they
match what conditional access did to a single request, which an attempt-level
summary has no notion of.

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

.. note:: Deleting entries also removes them from the counts a conditional
   access policy makes. Keep the retention period comfortably longer than the
   longest time window you use in a policy.
