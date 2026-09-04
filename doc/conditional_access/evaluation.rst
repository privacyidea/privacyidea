.. _conditional_access_evaluation:

How a request is evaluated
==========================

Conditional access acts on a request twice: it can refuse the request before
the credentials are checked, and it evaluates the outcome once the request has
been answered.

It protects the WebUI login, the ``/validate/`` endpoints and the endpoint a
push app answers a challenge on.

Before the credentials are checked, each of these endpoints asks three
questions, in this order:

1. Is this user locked?
2. Is this source IP blocked?
3. Does a conditional access policy deny this request?

The first question answered with *yes* ends the request.

For the third question the policies are evaluated by ascending **priority** - a
lower number takes precedence, as elsewhere in privacyIDEA - and the first policy
that denies wins. If none denies, the request proceeds normally. A subject is
exempted from a policy by giving that policy a condition, see
:ref:`conditional_access_policies_exceptions`.

After the request has been answered, its authentication log entry is evaluated
against the thresholds. Locks, blocks and notifications are created at this
point, so they apply from the *next* request onwards.

Rejection messages
------------------

A refused ``/validate/`` request returns the same generic failure as a wrong
password, so a client learns nothing about why it failed. The reason is in the
authentication log and in the :ref:`audit` log.

On the WebUI login the message names the restriction instead, so the user knows
whether to wait or to call the help desk. Set the ``hide_specific_error_message``
policy (see :ref:`authentication_policies`) to mask it there as well.
