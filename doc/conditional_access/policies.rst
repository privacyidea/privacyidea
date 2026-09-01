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

  A unique positive number. Policies are evaluated in ascending order and the
  first one that denies a request decides it, so a lower number takes
  precedence. Use *Reorder Policies* in the policy list to change the order.

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

**conditions**

  Restrict which requests the policy applies to at all. Without conditions it
  applies to every request. Available conditions:

  * ``USER_REALM`` - the realm of the authenticating user.
  * ``USER_ROLE`` - ``user``, ``admin-internal`` or ``admin-external``.

  Each condition is either *is one of* or *is not one of* a list of values.
  Several conditions are combined with AND. Conditions also narrow what is
  counted, not just whether the policy applies.

  .. note:: A request that carries no value for a condition does not match
     *is one of*, but does match *is not one of*. An exception written as
     *realm is not one of [sales]* therefore also covers requests with no
     realm at all. However, this only happens if the client does not send
     a realm at all and no default realm is defined.

Counting and resetting
----------------------

A ``user`` policy counts the failures **since the user's last successful
login**, so a legitimate user is not locked by failures from days ago.

A ``source_ip`` policy never resets on a success. One user authenticating
successfully must not clear a signal that is aggregated over everybody sharing
that address.

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
every further request as well. ``DENY`` defaults to re-trigger, as it is a one-time action denying only the current
request.

Stages are evaluated from the highest threshold down, so the order follows the
thresholds themselves and there is nothing else to configure.

A threshold counts failures and therefore starts at 1. ``DENY`` is the exception:
it states a standing verdict instead of reacting to a count, so a stage carrying
nothing but ``DENY`` may use threshold ``0``, which then means *always*. That is
how a lockdown is written - refuse everything the policy covers, whatever the
subject has done.

.. warning:: A ``DENY`` at threshold 0 refuses **every** request the policy
   covers, whatever the subject has done. Scope it with conditions, and leave
   yourself a way back in - *user role is not one of [admin-internal]* keeps the
   internal administrators able to log in. A ``DENY`` stores no state, so none of
   the ``pi-manage conditionalaccess`` reset commands can lift it; undoing an
   unscoped one means disabling the policy in the database.

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
    The rejection lifts by itself as the counted entries age out of the window.
    Use it for a rate limit that must not leave a lock behind.

**EMAIL_USER**, **EMAIL_ADMIN**
    Notify the user, or an administrator, that the threshold was reached.
    ``EMAIL_USER`` sends to the address in the user store. ``EMAIL_ADMIN`` sends
    to a list of addresses or to the internal administrators.

    An email action needs the identifier of an :ref:`smtpserver` configuration
    plus subject and body. Subject and body may contain ``{username}``,
    ``{realm}``, ``{resolver}``, ``{client_ip}``, ``{count}``, ``{threshold}``,
    ``{stage_id}``, ``{event_type}``, ``{policy}`` and ``{time}``; ``EMAIL_USER``
    additionally offers ``{email}``, ``{givenname}`` and ``{surname}``.

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
count mode, stages and actions; you pick the priority and review the
thresholds. The two per-IP rate limit templates are pre-set to dry run, because
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
have done, then disable dry run once the threshold fits.
