.. index:: ConditionalAccessNeverBlock
.. _conditional_access_locks_and_blocks:

Locks and blocks
================

A lock or a block created by a policy stays in force until it expires or an
administrator lifts it. Both are listed in the WebUI, where they can also be
lifted, and individual addresses or whole networks can be exempted from ever
being blocked.

.. _conditional_access_policies_lifting:

Lifting locks and blocks
------------------------

*Logs → Locked users* and *Logs → Blocklist* show the restrictions in force,
with the permanent ones marked. An entry can be lifted individually or in bulk.
Expired records restrict nobody; they are kept for the record and can be purged
from the same pages.

The same can be done on the command line with :ref:`pi-manage <pimanage>`::

   pi-manage conditionalaccess list-locked-users
   pi-manage conditionalaccess unlock-user <login> --realm <realm>
   pi-manage conditionalaccess clear-locks [--realm <realm>]
   pi-manage conditionalaccess purge-expired-locks

   pi-manage conditionalaccess list-blocked-ips
   pi-manage conditionalaccess unblock-ip <ip>
   pi-manage conditionalaccess clear-blocks
   pi-manage conditionalaccess purge-expired-blocks

``unlock-user`` takes the login name as an argument and requires ``--realm``;
add ``--resolver`` only if the login exists in more than one resolver. The two
``clear-`` commands remove everything and ask for confirmation first, so pass
``--yes`` when calling them from a script.

.. note:: If you lock yourself out of the WebUI with a source IP policy, use
   ``pi-manage conditionalaccess clear-blocks`` on the server, or add your
   address to *ConditionalAccessNeverBlock*, see
   :ref:`conditional_access_never_block`.

.. _conditional_access_never_block:

Never blocking an address
-------------------------

Blocking the wrong address can lock out everybody. ``127.0.0.0/8`` and
``::1/128`` are therefore never blocked. Add further addresses in the
**ConditionalAccessNeverBlock** entry of the :ref:`system_config` as a
comma-separated list of IP addresses or CIDR networks.

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
   networks in *ConditionalAccessNeverBlock*.
