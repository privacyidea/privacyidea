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
   therefore takes neither side by default: with nothing configured a refused
   request is worded exactly like any other failed authentication, so a locked
   account cannot be told apart from a wrong password.

Silent by default
-----------------

Without any configuration a rejection carries only the generic
``Authentication failed.``, whatever refused it - a user lock, a source IP block
or a ``DENY``. It reveals neither that a restriction exists, nor how long it
lasts, nor which policy wrote it.

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
shown when a request is turned away while that stage applies, including on the
later attempts that a lock or block written by that stage refuses.

There is one field per stage rather than one per action, because a stage can
lock the user, block the address and send two emails at once; the administrator
writing one sentence for the stage decides what all of that should sound like.

``{duration}`` is the only tag substituted, with the time remaining **at the
moment of the rejection** - so it counts down over the life of a lock instead of
naming the duration the policy configured. The phrase is deliberately coarse
("in about 10 minute(s)", "in about 2 hour(s)"): a lock is a thing to come back
after, not to count down to the second.

Every other brace expression is left exactly as written, so braces in ordinary
prose need no escaping. That also means a mistyped tag is shown to the user as
written; the policy editor points out an unrecognised tag but does not refuse to
save it. ``{duration}`` itself is only substituted where there *is* a remaining
time. On a permanent lock or block, on a ``DENY`` and on a stage that only
notified there is none, so the tag is shown as written - the editor flags that
combination too.

In the WebUI the field is under each stage of *Policies → Conditional Access*,
behind the *Show specific error message* checkbox. The refresh button next to it
replaces the text with the suggested wording for the stage's current actions,
which is the same wording ``show_default_ca_error_message`` would apply.

Using the default wording instead
---------------------------------

Writing a message on every stage of every policy is tedious, and for most
installations the wording would be the same everywhere. The
``show_default_ca_error_message`` policy is the short form: with it set, a stage
that carries no error message of its own is described by privacyIDEA's default
wording for what it actually did, for example

* *Your account is temporarily locked. Please try again in about 10 minute(s).*
* *Access from your IP address has been blocked. Please contact your administrator.*
* *Access has been denied.*
* *Your administrator has been notified by email.*

See :ref:`policy_show_default_ca_error_message` for the policy itself. Unlike a
stage's error message, the default wording is per *action*, so a stage that locks
the user and notifies them reports both, one sentence per action. It is also
applied live rather than stored, so it covers the locks and blocks that already
exist - see :ref:`conditional_access_error_messages_snapshot`.

.. note:: The policy is what makes a rejection distinguishable from an ordinary
   failed authentication. It is scoped like any other policy in the
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

A stage that only **notified** refused nothing, so its message does not replace
anything. The credential failure is still the reason the request failed and keeps
its own message and details, with the notification appended to it.

.. _conditional_access_error_messages_snapshot:

When a change to the wording takes effect
-----------------------------------------

A stage's **own** error message is copied onto the lock or block when it is
written, and the restriction is then described from that copy. Two consequences:

* Editing the error message on a conditional access policy's stage does not
  change what an already locked user is being told. The new wording applies from
  the next lock or block that stage writes.
* *Logs → Locked users* and *Logs → Blocklist* show the stored text of each
  restriction, with ``{duration}`` unsubstituted - it is the template, and the
  remaining time is its own column.

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

A restriction is never weakened, and its wording travels with it: a second policy
locking the same user in the same request cannot shorten the lock, and therefore
cannot replace the wording of the higher-priority policy that wrote it either.
The policy whose message was not applied is written to the log.

A ``DENY`` is the exception, because it stores nothing. Its wording is read from
the deciding stage on every request, so an edit takes effect immediately.

A lock or block an administrator set by hand carries no wording of its own, so it
is silent - unless ``show_default_ca_error_message`` is set, which describes the
restriction in force whoever imposed it.

.. note:: A manual lock or block that *replaces* one a policy wrote keeps the
   wording already on record, since only the expiry and the cause are rewritten.
   Extend the duration of a policy lock by hand and the user goes on being told
   what that policy said.

What each endpoint says
-----------------------

A configured message is shown at every gated endpoint. What differs is what a
*silent* rejection looks like, and the rule is the same everywhere: it has to
look like an ordinary failed authentication of that endpoint.

**The WebUI login** (``/auth``) answers with an error response, as every failed
login there does: HTTP ``401``, carrying the privacyIDEA error code ``403``. That
is the generic authentication failure rather than the "wrong credentials" code
``4031``, because the credential the request carried was never checked. An error
response has to carry some message, so a silent rejection there falls back to
``Authentication failed.``.

**The** ``/validate/`` **endpoints** answer with the ordinary failure body -
HTTP ``200``, ``result.value`` false, ``result.authentication`` ``REJECT`` - and
carry the wording in ``detail.message``. A silent rejection carries
``Authentication failed.`` there rather than no detail at all: on these endpoints
*every* failure has a detail, so a response without one could only have come
from conditional access.

**The endpoint a push app answers a challenge on** (``/ttype/push``) is the
mirror image: an ordinary failed push answer carries no ``detail`` at all, so a
silent rejection carries none either.

``/validate/polltransaction`` is not gated - it reads the status of a challenge
rather than attempting an authentication - and so never produces a rejection
message.

The request that *creates* a lock is answered exactly as the requests the lock
then refuses: the same body, the same wording, and nothing of the credential
failure it overtook. The message is failure-only in every case and is never shown
on a successful login.

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
*is* the ordinary failure, so it is masked along with every other one:

* ``hide_specific_error_message`` replaces it with its own generic message, which
  is the same sentence a silent rejection already carried.
* ``no_detail_on_fail`` strips the ``detail`` from a ``/validate/check``
  response, and a silent rejection then says nothing rather than putting a
  generic message back where that policy has just removed one.

To keep conditional access invisible, therefore, simply leave the error messages
empty and do not set ``show_default_ca_error_message`` - that is the default. The
masking policies are neither needed for it nor sufficient against a message an
administrator configured.

``hide_auth_error_status`` (:ref:`policies_hardening`) changes nothing about a
rejection: a refused login already returns the ``401`` that policy normalises
to, and a refused ``/validate`` request already returns the ordinary ``200``.

Where the reason always is
--------------------------

Whatever the user is told, the administrator sees the whole reason:

* the :ref:`authentication_log` entry for the refused request, classified as
  ``USER_LOCKED``, ``IP_BLOCKED`` or ``ACCESS_DENIED`` - the only place a
  rejection can be filtered for, since the request is turned away before
  anything else logs an outcome for it;
* the :ref:`audit` entry, which names every restriction in force and whether each
  is permanent;
* *Logs → Locked users* and *Logs → Blocklist*, which list the restriction, the
  policy or administrator that imposed it, and the wording it carries.
