.. index:: PI_CONDITIONAL_ACCESS_NEVER_BLOCK, never-block
.. _conditional_access_locks_and_blocks:

Locks and blocks
================

A lock or a block created by a policy stays in force until it expires or an
administrator lifts it. Both are listed in the WebUI, where they can also be
lifted. Individual addresses or whole networks can be exempted from ever being
blocked, see :ref:`conditional_access_never_block`.

A **Cause** column says whether a conditional access policy or an administrator imposed the
restriction now in force - *Policy* or *Manual* - and can be filtered on. It
describes the restriction on record rather than its history: an administrator who
replaces a policy lock by hand turns it into a manual one, and a policy that
strengthens a manual lock turns it back, because the cause is written together
with the expiry it belongs to. A manual restriction is also the one that no
threshold created, so it lifts only when someone lifts it or its own duration
runs out.

Each entry also shows the error message the restriction carries - what the
affected user is being told on the requests it refuses, or nothing where the stage
said nothing. It is a copy taken when the restriction was written, see
:ref:`conditional_access_error_messages_snapshot`.


.. _conditional_access_policies_lifting:

Lifting locks and blocks
------------------------

*Logs → Locked Users* and *Logs → IP Blocklist* show the restrictions in force,
with the permanent ones marked. An entry can be lifted individually or in bulk.
Expired records restrict nobody; they are kept for the record and can be purged
from the same pages.

The same can be done on the command line with :ref:`pi-manage <pimanage>`::

   pi-manage conditionalaccess list-locked-users
   pi-manage conditionalaccess unlock-user <login> --realm <realm>
   pi-manage conditionalaccess unlock-user <login> --admin
   pi-manage conditionalaccess unlock-by-id --uid <uid> --realm <realm>
   pi-manage conditionalaccess clear-locks [--realm <realm>]
   pi-manage conditionalaccess purge-expired-locks

   pi-manage conditionalaccess list-blocked-ips
   pi-manage conditionalaccess unblock-ip <ip>
   pi-manage conditionalaccess clear-blocks
   pi-manage conditionalaccess purge-expired-blocks

``unlock-user`` takes the login name as an argument and requires ``--realm``;
add ``--resolver`` only if the login exists in more than one resolver. For a
**local administrator** pass ``--admin`` instead of ``--realm``: such an account
lives in the ``admin`` table rather than in a realm, so its login name is the
whole identity, see :ref:`conditional_access_local_admins`.
``unlock-by-id`` does the same for a user that no longer resolves to a login,
taking the stored ``--uid`` and ``--realm`` instead, again with ``--resolver``
only to disambiguate a uid shared between resolvers. The two
``clear-`` commands remove everything and ask for confirmation first, so pass
``--yes`` when calling them from a script.

.. note:: If you lock yourself out of the WebUI with a source IP policy, use
   ``pi-manage conditionalaccess clear-blocks`` on the server, or add your
   address to ``PI_CONDITIONAL_ACCESS_NEVER_BLOCK``, see
   :ref:`conditional_access_never_block`. If a *user* policy locked your local
   administrator account, ``pi-manage conditionalaccess unlock-user <login>
   --admin`` lifts it.

Lifting a lock only undoes what a policy has already done - it will do it again
on the next request. Switching the policy itself off, which is what a ``DENY``
needs (it stores nothing that could be lifted), is described in
:ref:`conditional_access_policies_cli`.

.. _conditional_access_manual_restrictions:

Locking or blocking by hand
---------------------------

.. index:: manual lock, manual block

A restriction does not have to come from a policy. The *User Lock State* card on
a user's details page offers a **Lock** action and the *IP Blocklist* page a
**Block IP** action; both ask whether the restriction lasts until an administrator lifts
it (the default) or for a chosen duration. On the command line::

   pi-manage conditionalaccess lock-user <login> --realm <realm> [--duration <seconds>]
   pi-manage conditionalaccess lock-user <login> --admin [--duration <seconds>]
   pi-manage conditionalaccess block-ip <ip> [--duration <seconds>]

A manual restriction is written to the same place a policy writes to and is
enforced by the same pre-check, so at authentication time it behaves exactly like
a policy lock, is described by the same *Cause* column, and is lifted by the same
actions.

Unlike a policy action, a manual write is **authoritative**: an administrator may
replace a permanent lock with a timed one, which the engine refuses to do to
itself, since a policy never weakens a restriction - that rule exists so the
order two policies happen to fire in cannot decide the outcome. An address on the
never-block list is refused with an explanation rather than silently skipped,
which is the other way round from the engine, see
:ref:`conditional_access_never_block`.

Imposing a restriction has rights of its own, :ref:`policy_user_lock_set` and
:ref:`policy_blocklist_set`, kept apart from the ``*_reset`` rights.

A local administrator is locked by hand from the command line only, with
``--admin`` in place of ``--realm``. There is no WebUI action for it: the
**Lock** button lives on a user's details page, and a local administrator has
none.


.. _conditional_access_local_admins:

Local administrators
--------------------

.. index:: local administrator, internal admin

Local (internal) administrators - the accounts created with ``pi-manage admin
add``, which authenticate at ``/auth`` and live in the ``admin`` table rather
than in a realm - are locked by ``user`` policies like anybody else. They are
identified differently, though, and it shows in a few places:

* They have no realm or resolver. Their login name **is** the identity, and it is
  what both the failure count and the lock are keyed on, together with the role
  the authentication log records them under (*admin-internal*).
* On MySQL and MariaDB the ``admin`` table matches a login without regard to
  case, so ``Admin`` and ``admin`` authenticate the same account. Counting and
  locking follow that: whichever spelling is typed, the failures are counted
  against the one account and the lock is written under the name the table
  holds. Unlocking by name lifts every lock standing under a spelling of it,
  since each of them would bar the account from logging in.
* On *Logs → Locked Users* such an entry carries an **internal admin** badge and
  has no realm, resolver or link to a user page. It is lifted like any other,
  individually or in bulk.
* On the command line they are addressed with ``--admin`` instead of
  ``--realm``, both to lock and to unlock.
* A **target-scoped** administrator does not see or lift their locks. An admin
  policy is scoped by realm, resolver and user - userstore terms, none of which
  describes an account that has only a login name - so such a delegation stops
  at ordinary users, and a policy scoped to a login name does not reach a local
  administrator who happens to share it. Lifting one needs a ``user_lock_reset``
  policy with no target scope, or the command line.
* If a user of the same login name exists in the default realm, the two share a
  lockout. ``/auth`` takes a bare login name and only learns which of them was
  meant from the credential that matches, so a request is refused while *either*
  is locked - anything else would let the name be locked over and over without a
  single request being refused. The failure count is shared for the same reason
  (see :ref:`policy_auth_max_fail`), so a colliding name is worth avoiding: give
  the local administrator one no realm will ever hold.

Since a lock applies to them like anyone else, a policy can lock out the account
you would use to undo it. Two things guard against that: a timed lock lifts
itself, and ``pi-manage conditionalaccess unlock-user <login> --admin`` lifts one
from the server without needing to log in. To keep such an account out of a
policy altogether, give the policy a ``USER_ROLE NOT IN [admin-internal]``
condition - the same break-glass condition the templates use, see
:ref:`conditional_access_policies_exceptions`.


.. _conditional_access_never_block:

Never blocking an address
-------------------------

Blocking the wrong address can lock out everybody. ``127.0.0.0/8`` and
``::1/128`` are therefore never blocked. Further addresses and networks are
added in ``PI_CONDITIONAL_ACCESS_NEVER_BLOCK``, a server-configuration setting
with no WebUI or API - deliberately, since it is the safety net that keeps an
administrator from locking themselves out. See
:ref:`ini_conditional_access_never_block` for the setting itself.

An IPv4 entry also covers the IPv4-mapped form of the same address
(``::ffff:10.0.0.1`` for ``10.0.0.1``), which is what a dual-stack listener
reports for an IPv4 client. Tunnel encodings that merely carry an IPv4 address
(6to4, Teredo) are not covered: unlike the mapped form, those are chosen by the
client rather than by the operating system.

The exemption is checked both when a block is created and when an existing one
is enforced, so adding an address immediately stops a block already in force
from taking effect. It withholds the block itself, not the whole policy: an
exempt address is never blocked and is never refused by a ``DENY``, but a policy
it trips still counts, still records what it did in the authentication log, and
still runs the other actions of the stage - an ``EMAIL_ADMIN`` alongside the
block is sent as usual.

.. warning:: A source IP is only meaningful if privacyIDEA sees the real client
   address. Behind a reverse proxy or a load balancer you have to configure
   ``OverrideAuthorizationClient`` in the :ref:`system_config`. Otherwise every
   request appears to come from the proxy, and a single ``BLOCK_IP`` action
   blocks all of them. List your proxies, load balancers and management
   networks in ``PI_CONDITIONAL_ACCESS_NEVER_BLOCK``.
