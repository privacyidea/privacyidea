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

* *Policies → Conditional access* - create, order and enable the policies.
* *Logs → Authentication log* - the classified authentication events.
* *Logs → Locked users* and *Logs → Blocklist* - the restrictions in force,
  and where to lift them.
* The *Conditional Access* dashboard panel summarises all of it, see
  :ref:`dashboard`.

.. toctree::
   :maxdepth: 1

   lockout_policies
   authentication_log

.. _conditional_access_evaluation:

How a request is evaluated
--------------------------

Before the credentials are checked, every protected endpoint asks three
questions, in this order:

1. Is this user locked?
2. Is this source IP blocked?
3. Does a policy deny this request?

The first question answered with *yes* ends the request. Because the lock and
the block are checked first, an ``ALLOW`` action can never re-admit a user who
is already locked.

For the third question the policies are evaluated by ascending **priority** -
a lower number takes precedence, as elsewhere in privacyIDEA - and the first
policy that decides wins. If none decides, the request proceeds normally.

After the request has been answered, its authentication log entry is evaluated
against the thresholds. Locks, blocks and notifications are created at this
point, so they apply from the *next* request onwards.

Conditional access protects the WebUI login, the ``/validate/`` endpoints and
the endpoint a push app answers a challenge on. Polling for an answered
challenge is refused as well, but never recorded, because the answer it polls
for is recorded where it arrives.

Rejection messages
~~~~~~~~~~~~~~~~~~

A refused ``/validate/`` request returns the same generic failure as a wrong
password, so a client learns nothing about why it failed. The reason is in the
authentication log and in the :ref:`audit` log.

On the WebUI login the message names the restriction instead, so the user knows
whether to wait or to call the help desk. Set the ``hide_specific_error_message``
policy (see :ref:`authentication_policies`) to mask it there as well.

.. _conditional_access_never_block:

Never blocking an address
-------------------------

.. index:: ConditionalAccessNeverBlock

Blocking the wrong address can lock out everybody. ``127.0.0.0/8`` and
``::1/128`` are therefore never blocked. Add further addresses in the
**ConditionalAccessNeverBlock** entry of the :ref:`system_config` as a
comma-separated list of IP addresses or CIDR networks.

The exemption is also applied while enforcing, so adding an address
immediately stops an existing block from taking effect. An exempt address is
skipped silently: no block is created and nothing is recorded for it, so a
source IP policy tried out from the privacyIDEA host itself looks as if it never
triggered.

.. warning:: A source IP is only meaningful if privacyIDEA sees the real client
   address. Behind a reverse proxy or a load balancer you have to configure
   ``OverrideAuthorizationClient`` in the :ref:`system_config`. Otherwise every
   request appears to come from the proxy, and a single ``BLOCK_IP`` action
   blocks all of them. List your proxies, load balancers and management
   networks in *ConditionalAccessNeverBlock*.

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
hundreds of users behind one address. The two per-IP rate limit templates are
therefore delivered with dry run enabled.

Filter the authentication log on *dry run* outcomes to see what a policy would
have done, then disable dry run once the threshold fits.

.. _conditional_access_rights:

Rights
------

The administrator rights are defined in the :ref:`admin_policies`:

``authentication_log_read``
    read the authentication log. Scoping the policy to realms, resolvers or
    users limits which entries the administrator sees.

``lockout_policy_read``, ``lockout_policy_write``
    view, and create/edit/delete, the lockout policies.

``user_lockout_read``, ``user_lockout_reset``
    view locked users, and unlock them.

``blocklist_read``, ``blocklist_reset``
    view blocked addresses, and remove them.

Users can be allowed to read their own authentication log entries with
``authentication_log_read`` in the user scope, see :ref:`user_policies`.
