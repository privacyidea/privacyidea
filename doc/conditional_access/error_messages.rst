.. index:: Conditional Access error message, show_default_ca_error_message
.. _conditional_access_error_messages:

Error messages
==============

A request refused by conditional access says nothing about why, unless an
administrator chose to say something. The real reason is always recorded for the
administrator - in the :ref:`authentication_log` and in the :ref:`audit` log -
but what the end user sees is a separate, deliberately opt-in decision.

.. note:: Telling a user that their account is locked, or that their address is
   blocked, is useful for the user and useful for an attacker. privacyIDEA
   therefore says nothing about a restriction by default: with nothing
   configured a refused request carries the generic ``Authentication failed.``
   and names neither the restriction nor its duration. To make it look exactly
   like a wrong password, also set ``hide_specific_error_message``, see
   :ref:`conditional_access_error_messages_masking`.

Silent by default
-----------------

Without any configuration a rejection carries only the generic
``Authentication failed.``, whatever refused it - a user lock, a source IP block
or a ``DENY``. It does not say which restriction refused the request, how long it
lasts or which policy wrote it. It is not identical to every other failed
authentication, though: at ``/validate/check`` an ordinary failure names what
failed (for example ``wrong otp pin``), and at ``/auth`` a wrong password has the
error code ``4031`` where a rejection has ``403``. ``hide_specific_error_message``
removes both differences, ``no_detail_on_fail`` the one at ``/validate/check``,
see :ref:`conditional_access_error_messages_masking`.

There are two ways to say more, and they can be combined:

* write an **error message** on the stage that does the refusing, which is exact
  wording for that one stage;
* set the ``show_default_ca_error_message`` policy, which fills in privacyIDEA's
  own wording for whatever a stage did, without writing anything per stage.

A stage's own error message always wins over the policy default.

The error message of a stage
----------------------------

Each stage of a :ref:`conditional access policy <conditional_access_policies_stages>`
has one optional **error message** - free text, at most 500 characters. It is
shown on a request that is turned away *before* the password or OTP is checked:
while a lock or block written by that stage is in force, or when that stage
denies access.

.. important:: It is **not** shown on the request that trips the stage. That
   request has already been answered on its own merits - its own failure, its own
   challenge, even its own success - and the lock or block it wrote applies from
   the next request onwards. See :ref:`conditional_access_evaluation`.

This has a consequence worth planning for: a stage that **only notifies** - one
carrying nothing but ``EMAIL_USER`` or ``EMAIL_ADMIN`` - turns no request away at
any point, so there is never a moment at which its error message could be shown.
Such a stage is silent whatever is written on it, and the policy editor points
that out.

There is one field per stage rather than one per action, because a stage can lock
the user, block the address and send two emails at once; the administrator
writing one sentence for the stage decides what all of that should sound like.

``{duration}`` is the only tag substituted, with the time remaining **at the
moment of the rejection** - so it counts down over the life of a lock instead of
naming the duration the policy configured. The substituted text is deliberately
coarse - ``10 minute(s)`` or ``2 hour(s)``, rounded up and never below one
minute: a lock is a thing to come back after, not to count down to the second.
The default wording puts *in about* in front of it
(``Please try again in about {duration}.``); a message written as
``Try again in {duration}`` reads ``Try again in 10 minute(s)``.

Every other brace expression is left exactly as written, so braces in ordinary
prose need no escaping. That also means a mistyped tag is shown to the user as
written; the policy editor points out an unrecognized tag but does not refuse to
save it. ``{duration}`` itself is only substituted where there *is* a remaining
time. A permanent lock or block has none, and a ``DENY`` counts down nothing at
all, so there the tag is shown as written - the editor flags that combination
too.

In the WebUI the field is under each stage of *Policies → Conditional Access*,
behind the *Show specific error message* checkbox. The refresh button next to it
replaces the text with the suggested wording for the stage's current actions,
which is the same wording ``show_default_ca_error_message`` would apply. A stage
that carries wording but nothing that could ever show it - no lock, no block, no
``DENY`` - is flagged there as well.

Using the default wording instead
---------------------------------

Writing a message on every stage of every policy is tedious, and for most
installations the wording would be the same everywhere. The
``show_default_ca_error_message`` policy is the short form: with it set, a
restriction that carries no error message of its own is described by privacyIDEA's
default wording for what it is, for example

* *Your account is temporarily locked. Please try again in about 10 minute(s).*
* *Access from your IP address has been blocked. Please contact your administrator.*
* *Access has been denied.*

See :ref:`policy_show_default_ca_error_message` for the policy itself. Unlike a
stage's error message, the default wording is per *action*, and there is wording
only for the actions that turn a request away: the four lock and block actions and
``DENY``. A notification is a one-off event that no restriction records, so a stage
that locks the user *and* emails them is described by the lock alone. It is also
applied live rather than stored, so it covers the locks and blocks that already
exist - see :ref:`conditional_access_error_messages_snapshot`.

.. note:: The policy makes a rejection name the restriction that refused it. It
   is scoped like any other policy in the
   :ref:`policies_conditional_access` scope, so it can be limited to a realm, to
   a set of clients or to a user agent.

Which restriction is described
------------------------------

**Every restriction in force is reported, not only the one that binds.** A user
lock and an address block are independent facts that are lifted independently, so
a user facing both is told about both rather than left to discover the second by
failing again. Where several messages apply they are ordered by severity - the
one the user can do least about comes first - and an identical sentence
configured on two stages is said once.

The authentication log takes the opposite approach, because a log row records one
``event_type`` that an administrator can filter on: the rejection is filed under
the restriction that lasts longest, and the other one is recorded in the entry's
**other info**, under the key ``additional_event_types``. That keeps the entry
honest about both without pretending the second one is filterable - only
``event_type`` is.

Only a restriction is described. A stage that merely **notified** refused nothing
and left nothing behind for a later request to be refused by, so no request ever
carries wording for it - the failure that happened to trip it keeps its own
message and details, unchanged.

.. _conditional_access_error_messages_snapshot:

When a change to the wording takes effect
-----------------------------------------

A stage's **own** error message is copied onto the lock or block when it is
written, and the restriction is then described from that copy. Two consequences:

* Editing the error message on a conditional access policy's stage does not
  change what an already locked user is being told. The new wording applies from
  the next lock or block that stage writes.
* *Logs → Locked Users* and *Logs → IP Blocklist* show the stored text of each
  restriction, with ``{duration}`` unsubstituted - it is the template; when the
  restriction ends is shown in its own expiry column.

The default wording is the other way round. Nothing about
``show_default_ca_error_message`` is recorded on the lock or the block: the policy
is matched on every request, and the sentence is composed at that moment from what
the restriction *is* - whose it is, and whether it expires. Turning the policy on
therefore makes every silent restriction already in force start explaining itself
on the next request, and turning it off silences them again, with no re-locking
involved. Because it is matched per request like any other policy, the same lock
can also explain itself to one realm or client while staying silent for another.

That difference only shows where the two do not overlap: the default stands in
for a *missing* message and never replaces one, so a restriction that snapshotted
a stage's wording keeps saying that, whatever the policy does.

A restriction is never weakened, and its wording travels with it. A second policy
that locks the same user in the same request for the same or a shorter time, or
for a limited time where the lock is permanent, leaves the lock and its wording
as they are; where it writes the same lock, the policy whose message was not
applied is written to the log. A policy that locks for longer, or permanently
where the lock was timed, replaces the lock together with its wording - with the
error message of its own stage, or with none if that stage has none. The same
holds for a block of a source IP.

A ``DENY`` is the exception, because it stores nothing. Its wording is read from
the deciding stage on every request, so an edit takes effect immediately.

A lock or block an administrator set by hand carries no wording of its own, so it
is silent - unless ``show_default_ca_error_message`` is set, which describes the
restriction in force whoever imposed it.

.. note:: A manual lock or block that *replaces* one a policy wrote also
   replaces its wording: the stored error message is cleared together with the
   expiry and the cause, because the policy's wording describes neither. Extend
   the duration of a policy lock by hand and the restriction is silent from then
   on, like any other manual one - unless ``show_default_ca_error_message`` is
   set, which then describes it.

What each endpoint says
-----------------------

A configured message is shown at every gated endpoint except
``/validate/radiuscheck``, see below. What differs is what a *silent* rejection
looks like: it takes the form of an ordinary failed authentication of that
endpoint, without saying what refused it (for what still sets it apart from a
wrong credential, see :ref:`conditional_access_error_messages_masking`).

**The WebUI login** (``/auth``) answers with an error response, as every failed
login there does: HTTP ``401``, carrying the privacyIDEA error code ``403``. That
is the generic authentication failure rather than the "wrong credentials" code
``4031``, because the credential the request carried was never checked. An error
response has to carry some message, so a silent rejection there falls back to
``Authentication failed.``.

**The** ``/validate/`` **endpoints** ``/validate/check``,
``/validate/triggerchallenge`` and ``/validate/initialize`` answer with the
ordinary failure body - HTTP ``200``, ``result.value`` false (``0`` at
``/validate/triggerchallenge``, where the value is the number of triggered
challenges), ``result.authentication`` ``REJECT`` - and carry the wording in
``detail.message``. A silent rejection carries ``Authentication failed.`` there
rather than no detail at all: on these endpoints *every* failure has a detail, so
a response without one could only have come from conditional access.

``/validate/radiuscheck`` answers every failed authentication, a rejection
included, with an empty body and HTTP ``400``. No wording reaches a RADIUS
client; the reason is only in the logs.

``/validate/remember_device`` answers a rejection like a device that is not
remembered: HTTP ``200``, ``result.value`` and ``detail.remembered_device``
false, and no ``result.authentication``. A configured message is carried in
``detail.message``; a silent rejection carries no message, as an ordinary answer
there has none.

**The endpoint a push app answers a challenge on** (``/ttype/push``) is the
mirror image: an ordinary failed push answer carries no ``detail`` at all, so a
silent rejection carries none either.

``/validate/polltransaction`` is not gated - it reads the status of a challenge
rather than attempting an authentication - and so never produces a rejection
message.

The request that *creates* a lock is the one exception to all of this: it carries
no conditional access wording at all. It is answered exactly as it would have been
had no stage tripped - the token's own failure reason, or the challenge it was
about to hand out - and the lock speaks from the next request onwards. A silent
restriction is therefore undetectable at the moment it is written, the response
being the one the request had coming either way.

.. _conditional_access_error_messages_masking:

Interaction with the masking policies
-------------------------------------

.. index:: hide_specific_error_message, no_detail_on_fail

**A configured conditional access message is not masked.** Neither
``hide_specific_error_message`` (:ref:`authentication scope <authentication_policies>`)
nor ``no_detail_on_fail`` (:ref:`authorization scope <authorization_policies>`)
removes it, and neither does the combination of both.

Those two policies exist to suppress what privacyIDEA *volunteers by default* -
which factor failed, why a token refused, which serial was tried. A conditional
access message is the opposite: it exists only because an administrator wrote it
on the stage or turned it on with ``show_default_ca_error_message``. Masking it
would mean one policy silently overruling another administrator's explicit
decision about disclosure.

So on a rejection those policies keep their effect on everything *else*: the
error code and the rest of the ``detail`` object are collapsed as usual, and only
the conditional access wording survives. That costs a rejection nothing, because
a rejection has nothing else to say - it never carried the token serial or the
failure reason in the first place.

The reverse case follows the same rule from the other side. A **silent** rejection
is answered as an ordinary failure, so it is masked along with every other one:

* ``hide_specific_error_message`` replaces it with its own generic message, which
  is the same sentence a silent rejection already carried.
* ``no_detail_on_fail`` strips the ``detail`` from a ``/validate/check``
  response, so a silent rejection ends up saying nothing at all - it had only the
  generic sentence to lose.

To keep conditional access invisible, therefore, leave the error messages empty,
do not set ``show_default_ca_error_message`` - that is the default - and set
``hide_specific_error_message``. Without it, a silent rejection says nothing
about the restriction, but it can still be told apart from a wrong credential:
at ``/validate/check`` it lacks the message an ordinary failure carries about
what failed, and at ``/auth`` its error code is ``403`` instead of ``4031``.
``no_detail_on_fail`` closes the difference at ``/validate/check`` only. Neither
masking policy is sufficient against a message an administrator configured.

``hide_auth_error_status`` (:ref:`policies_hardening`) changes nothing about a
rejection: a refused login already returns the ``401`` that policy normalizes
to, and a refused ``/validate`` request already returns the ordinary ``200`` -
or, at ``/validate/radiuscheck``, the empty ``400`` every failure gets there.

Where the reason always is
--------------------------

Whatever the user is told, the administrator sees the whole reason:

* the :ref:`authentication_log` entry for the refused request, classified as
  ``USER_LOCKED``, ``IP_BLOCKED`` or ``ACCESS_DENIED`` - the only place a
  rejection can be filtered for, since the request is turned away before
  anything else logs an outcome for it;
* the :ref:`audit` entry, which names every restriction in force and whether each
  is permanent;
* *Logs → Locked Users* and *Logs → IP Blocklist*, which list the restriction,
  whether a policy or an administrator imposed it (*Policy* or *Manual*), when it
  expires, and the wording it carries. Which policy wrote a lock or block is
  recorded on the request that tripped it, in the conditional access outcome of
  its :ref:`authentication_log` entry.
