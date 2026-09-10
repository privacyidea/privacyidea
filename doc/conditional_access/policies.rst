.. index:: Conditional Access policies, Conditional Access
.. _conditional_access_policies:

Conditional access policies
===========================

A conditional access policy counts authentication log entries for one subject
over a time window and runs actions when a threshold is reached. These policies
are managed under *Policies → Conditional Access* and are independent of the
policies described in :ref:`policies`.

Policy settings
---------------

**name**

  A unique name for the policy. It identifies the policy in the authentication
  log and in the notification emails.

**priority**

  A unique positive number; a lower number takes precedence. This only decides
  an outcome for the pre-auth ``DENY`` question (see
  :ref:`conditional_access_evaluation`): policies are consulted in ascending
  priority order and the first one that denies a request wins, so no
  lower-priority policy is even evaluated. Every other action - ``LOCK_USER``,
  ``BLOCK_IP``, the email actions - runs for **every** enabled, matching
  policy regardless of priority; there, priority only decides whose error
  message stands when two policies write the same lock or block, see
  :ref:`conditional_access_policies_lifting`. Use *Reorder Policies* in the
  policy list to change the order.

**enabled**

  A disabled policy is not evaluated at all.

**dry run**

  Evaluate the policy but enforce nothing, see :ref:`conditional_access_policies_dry_run`.

**target**

  What the policy counts and acts on:

  * ``user`` - the authenticating user, identified by resolver, user ID and
    realm. Requests without a resolvable user are ignored by these policies.
    An internal privacyIDEA administrator is never counted here.
  * ``source_ip`` - the client address. These policies also apply when no user
    could be resolved, which is what makes spraying and enumeration visible.

  The target restricts the available count modes and actions.

**tracked events**

  The authentication event types this policy counts, see
  :ref:`authentication_log_event_types`. Several types can be selected; the
  policy counts their **sum**, so a policy tracking three failure types trips
  on their combined total.

  The event types conditional access writes for its own rejections cannot be
  tracked. Otherwise a lock would keep refreshing itself on the very requests
  it refuses, and never expire.

**time window**

  How far back the count reaches. Entries older than the window do not count,
  so an idle account recovers on its own.

**count mode**

  What a single count represents:

  * ``PER_REQUEST`` - one authentication log entry. Default for ``user``.
  * ``PER_ATTEMPT`` - one authentication attempt. A challenge-response login
    spans several requests; they count once. Use this if a
    multi-challenge login should not count as several events.
  * ``DISTINCT_USERS`` - the number of *different* accounts the address
    targeted, not the number of requests. Available for ``source_ip`` only,
    and its default. This is the password spraying and user enumeration
    signal: attempted user names are counted, so guesses at accounts that do
    not exist count too.

  For a ``source_ip`` target the two volume modes amount to plain rate limiting
  per address.

**reset the count on a successful login**

  Whether a completed login clears what has been counted so far, see
  :ref:`conditional_access_policies_counting`. On by default, and available for a
  ``user`` target only.

**conditions**

  Restrict which requests the policy applies to at all. Without conditions it
  applies to every request. Available conditions:

  * ``USER_REALM`` - the realm of the authenticating user.
  * ``USER_ROLE`` - ``user``, ``admin-internal`` or ``admin-external``.
  * ``ENDPOINT`` - the endpoint the request authenticated against, see
    :ref:`authentication_log_endpoints`.

  Each condition is either *is one of* or *is not one of* a list of values.
  Several conditions are combined with AND. Conditions also narrow what is
  counted, not just whether the policy applies. Pre-authentication they read
  what the request claims - see :ref:`conditional_access_policies_exceptions`.

  .. note:: A request that carries no value for a condition does not match
     *is one of*, but does match *is not one of*. An exception written as
     *realm is not one of [sales]* therefore also covers requests with no
     realm at all. For ``USER_REALM`` this happens when the client does not
     send a realm and no default realm is defined, and always for an internal
     administrator, who has no realm to carry regardless of that setting.

.. _conditional_access_policies_counting:

Counting and resetting
----------------------

With **reset the count on a successful login** - the default for a ``user``
policy - the policy counts the failures **since the user's last successful
login**, so a legitimate user is not locked by failures from days ago. Every
threshold of the policy counts that way, the ``DENY`` decision included, so a
denial also lifts on a successful login and not only as the window drains.

Turn it off to make a threshold mean *this many entries in the window* outright,
whatever happened in between. That is what a rate limit wants: the shipped rate
limit templates cap how many attempts an account may make per window, and one of
those attempts succeeding must not hand the next burst a fresh budget.

A ``source_ip`` policy never resets on a success. One user authenticating
successfully must not clear a signal that is aggregated over everybody sharing
that address. The setting is therefore unavailable for that target, and a policy
that asks for it is rejected rather than quietly ignored.

.. _conditional_access_policies_stages:

Stages and thresholds
---------------------

A policy has one or more **stages**. Each stage has a failure **threshold** and
a list of actions, and may be given a name for the log.

Only the stage with the highest matching threshold runs, and only its actions.
This is how an escalation is expressed: lock for ten minutes at 5 failures,
lock permanently at 20. Thresholds must be unique within a policy.

By default an action fires **once**, exactly when the count reaches the
threshold: an email configured at 8 is sent on the 8th failure and not again on
the 9th. Enable **re-trigger above threshold** for an action that should fire on
every further request instead, for as long as the count stays in the range its
stage owns - at or above its own threshold, below the next stage's. Each stage
therefore owns one range of counts, and only the stage owning the *current*
count acts, so escalation is a hand-over rather than an overlay.

This is a live read of the count, not a state the policy remembers: should the
count later drop back into a milder stage's range - the time window ageing old
failures out, or a successful login where ``reset_on_success`` applies - that
stage's re-triggering action fires again. ``DENY`` defaults to re-trigger, as it
is a one-time action denying only the current request, and follows the same
rule. In practice, though, a re-triggering ``DENY`` rarely hands over to a
higher stage on its own: once enforced, every further request is refused before
any credentials are checked and logged as ``ACCESS_DENIED``, a type no policy
can count, so the very count that would carry it past the next threshold stops
climbing while the refusal holds.

Stages are evaluated from the highest threshold down, so the order follows the
thresholds themselves and there is nothing else to configure.

A threshold counts failures and therefore starts at 1. ``DENY`` is the exception:
it states a standing verdict instead of reacting to a count, so a stage carrying
nothing but ``DENY`` may use threshold ``0``, which then means *always*. That is
how a lockdown is written - refuse everything the policy covers, whatever the
subject has done. Where the policy has further stages, that ``0`` stage hands
over like any other, so *always* reaches up to the next threshold.

.. warning:: A ``DENY`` at threshold 0 refuses **every** request the policy
   covers, whatever the subject has done. Scope it with conditions, and leave
   yourself a way back in. A ``user`` policy never decides an internal
   administrator to begin with, as a local administrator has no resolved
   identity to count against, so it is a ``source_ip`` policy that can shut you
   out: exempt your own address in *ConditionalAccessNeverBlock*, which is never
   denied either (see :ref:`conditional_access_never_block`), or write *user role
   is not one of [admin-internal]* and read what that exemption costs in
   :ref:`conditional_access_policies_exceptions`. A ``DENY`` stores no state, so
   none of the ``pi-manage conditionalaccess`` reset commands can lift it;
   undoing an unscoped one means disabling the policy itself, with
   ``pi-manage conditionalaccess disable-policy <name>`` if it has locked you out
   of the WebUI, see :ref:`conditional_access_policies_cli`.

Each stage also has an optional **error message**, the text an end user sees when
a request is turned away by that stage. It is empty by default, which keeps a
rejection indistinguishable from any other failed authentication, see
:ref:`conditional_access_error_messages`.

.. _conditional_access_policies_actions:

Actions
-------

**LOCK_USER**, **BLOCK_IP**
    Lock the user, or block the source address, for the configured duration.
    The restriction lifts itself when the duration has passed. A missing or
    invalid duration is a misconfiguration: the action is skipped and logged.

**PERMANENT_LOCK_USER**, **PERMANENT_BLOCK_IP**
    The same, without an expiry. Only an administrator can lift these.

**DENY**
    Refuse this single request pre-authentication, without storing anything.
    The rejection lifts by itself as the counted entries age out of the window -
    and, on a policy that resets on success, on the next successful login.
    Use it for a rate limit that must not leave a lock behind.

**EMAIL_USER**, **EMAIL_ADMIN**
    Notify the user, or an administrator, that the threshold was reached.
    ``EMAIL_USER`` sends to the address in the user store. ``EMAIL_ADMIN`` sends
    to a list of addresses or to the internal administrators.

    An email action needs the identifier of an :ref:`smtpserver` configuration
    plus subject and body. Subject and body may contain ``{username}``,
    ``{realm}``, ``{resolver}``, ``{client_ip}``, ``{count}``, ``{threshold}``,
    ``{stage_id}``, ``{event_type}``, ``{policy}``, ``{time}``, ``{email}``,
    ``{givenname}`` and ``{surname}``. The last three come from the resolver
    and are only filled in when a user was resolved for the request - which
    ``EMAIL_ADMIN`` on a ``source_ip`` policy is not guaranteed to have,
    since that target also applies where no user could be resolved at all.

.. _conditional_access_policies_exceptions:

Exempting a subject
-------------------

An exception is written as a **condition** on the policy you want the subject
exempted from - *realm is not one of [service]*, or *user role is not one of
[admin-internal]*. A policy whose conditions do not match is never evaluated for
that request at all, so the exemption is exact and visible on the rule it applies
to.

Because the condition takes the whole policy out of play, it covers every action
the policy carries. The exempt subject is neither refused, nor locked, nor
blocked, nor mailed about.

An exemption for a service account or a monitoring probe therefore goes on each
policy it needs to be out of - which is also where an administrator reading that
policy will look for it.

.. warning:: An exemption written as *user role is not one of [admin-internal]*
   also exempts everyone who merely **claims** to be an internal administrator.
   The role is read from the login name before any password is checked, so a
   login naming a local administrator is exempt whoever sent it, and the
   attempts made under that name are neither refused nor counted by the policy.
   The most guessable account in the installation is then the one account the
   policy does not protect. Write the exemption only on the policies that need
   it, and where an address will do, exempt the address in
   *ConditionalAccessNeverBlock* (see :ref:`conditional_access_never_block`)
   instead: an address is a fact of the connection rather than a claim of the
   request.

Which actions a policy may use depends on its target:

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Target
     - Actions
     - Count modes
   * - ``user``
     - LOCK_USER, PERMANENT_LOCK_USER, EMAIL_USER, EMAIL_ADMIN, DENY
     - PER_REQUEST, PER_ATTEMPT
   * - ``source_ip``
     - BLOCK_IP, PERMANENT_BLOCK_IP, EMAIL_ADMIN, DENY
     - DISTINCT_USERS, PER_REQUEST, PER_ATTEMPT

.. note:: ``BLOCK_IP`` in a ``user`` policy is not available: a user policy
   knows nothing about how many accounts an address attacked. Use a
   ``source_ip`` policy with ``DISTINCT_USERS`` for that.

Templates
---------

The *New Conditional Access* page offers templates for the common cases - password
brute force, MFA brute force, per-user and per-IP rate limits, password
spraying and user enumeration. A template fills in tracked events, window,
count mode, stages, actions and whether the count resets on a successful
login; you pick the priority and review the thresholds. The two per-IP rate limit templates are pre-set to dry run, because
their threshold depends on how many users share an address, see
:ref:`conditional_access_policies_dry_run`.

.. _conditional_access_policies_dry_run:

Trying a policy out first
-------------------------

.. index:: dry run

A policy with **dry run** enabled is evaluated like any other, but nothing is
enforced: no user is locked, no address is blocked, no email is sent and no
request is refused. Instead each action that *would* have run is recorded with
the authentication log entry that triggered it, including how long the
restriction would have lasted.

This is the way to size a threshold against real traffic. It is particularly
recommended for source IP policies, where the right threshold depends on how
many users share an address - shared egress such as NAT or CGNAT can put
hundreds of users behind one address.

Filter the authentication log on *dry run* outcomes to see what a policy would
have done, then disable dry run once the threshold fits. Dry run can also be
switched on and off from the command line, which defuses a policy that has
locked everybody out without losing what it records.

.. _conditional_access_policies_cli:

Managing policies on the command line
-------------------------------------

The policies can also be managed with :ref:`pi-manage <pimanage>`, which is what
you need when a policy has locked you out of the WebUI itself - an unscoped
``DENY``, say::

   pi-manage conditionalaccess list-policies
   pi-manage conditionalaccess disable-policy <name>
   pi-manage conditionalaccess enable-policy <name>
   pi-manage conditionalaccess enable-dry-run <name>
   pi-manage conditionalaccess disable-dry-run <name>
   pi-manage conditionalaccess delete-policy <name> [--yes]

``list-policies`` prints one line per policy - name, id, enabled and dry-run
state, priority and target - lowest priority number first, which is the order
the policies are evaluated in.

Every other command addresses one policy, either by the name given as its
argument or by ``--id`` - which is the handier one for a name that contains
spaces::

   pi-manage conditionalaccess disable-policy --id 7


``disable-policy`` is the way back in: the policy is no longer evaluated, so it
cannot refuse the next request. ``enable-dry-run`` is the gentler variant - the
policy stays enabled and keeps recording what it *would* do, but nothing is
enforced. Both leave the locks and blocks the policy has already written in
force, so clear those as well, see :ref:`conditional_access_policies_lifting`.
``delete-policy`` removes the policy with its stages and actions for good and
asks for confirmation first, so pass ``--yes`` when calling it from a script.
