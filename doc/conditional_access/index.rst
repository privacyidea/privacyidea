.. index:: Conditional Access, lockout, blocklist
.. _conditional_access:

Conditional Access
==================

.. versionadded:: 3.14

Conditional access refuses an authentication request because of what happened
*before* it.

Every authentication request is classified and written to the
:ref:`authentication_log`. :ref:`lockout_policies` count those entries for one
user or one source IP over a time window. When a threshold is reached, the
configured actions run: the user is locked, the source IP is blocked, an email
is sent, or the request is denied.

This extends the mechanisms privacyIDEA already had. The failcounter bars a
single token and has no time window. The :ref:`policy_auth_max_fail` policy
counts a user's failed authentications over a window, but keeps no state and
cannot look at the source IP. Conditional access counts per user *or* per
source IP, keeps the resulting lock or block until it expires or an
administrator lifts it, and can react to attacks that never hit the same
account twice, such as password spraying and user enumeration.

.. note:: Conditional access does nothing until you create a lockout policy.
   Nothing is enabled by default.

In the WebUI you will find it here:

* *Policies → Conditional Access* - create, order and enable the policies.
* *Logs → Authentication Log* - the classified authentication events.
* *Logs → Locked Users* and *Logs → IP Blocklist* - the restrictions in force,
  and where to lift them.
* The *Conditional Access* dashboard panel summarises all of it, see
  :ref:`dashboard`.

Every one of these views requires an administrator right:

* ``authentication_log_read`` - read the authentication log.
* ``lockout_policy_read``, ``lockout_policy_write`` - view, and create/edit/delete,
  the lockout policies.
* ``user_lockout_read``, ``user_lockout_reset`` - view locked users, and unlock them.
* ``blocklist_read``, ``blocklist_reset`` - view blocked addresses, and remove them.

The rights are defined in the :ref:`admin_policies`, starting at
:ref:`policy_authentication_log_read`. Users can be allowed to read their own
authentication log entries with ``authentication_log_read`` in the
:ref:`user scope <user_policies>`.

The following pages describe how a request is evaluated, how a policy is
configured, what the authentication log records, and how a lock or a block is
lifted again:

.. toctree::
   :maxdepth: 1

   evaluation
   lockout_policies
   authentication_log
   locks_and_blocks
