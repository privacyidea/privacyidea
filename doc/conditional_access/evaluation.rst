.. _conditional_access_evaluation:

How a request is evaluated
==========================

Conditional access acts on a request twice: it can refuse the request before
the credentials are checked, and it evaluates the outcome once the request has
been answered.

It protects the WebUI login, the ``/validate/`` endpoints and the endpoint a
push app answers a challenge on.

Before the credentials are checked, each of these endpoints asks two questions:

1. Is this user locked, or is this source IP blocked?
2. Does a conditional access policy deny this request?

A lock or a block in force ends the request, and no policy is asked. If both are
in force, the request is refused for both: the authentication log files it under
the one that lasts longer - a permanent one before a timed one, the lock on a
tie - and records the other in the entry's other info, and the user is told
about each of them that carries an error message, see
:ref:`conditional_access_error_messages`.

For the second question the policies are evaluated by ascending **priority** - a
lower number takes precedence, as elsewhere in privacyIDEA - and the first policy
that denies wins. If none denies, the request proceeds normally. A subject is
exempted from a policy by giving that policy a condition, see
:ref:`conditional_access_policies_exceptions`.

After the request has been answered, its authentication log entry is evaluated
against the thresholds. Locks, blocks and notifications are created at this
point, so they apply from the *next* request onwards.

.. important:: The evaluation never changes the response of the request it
   evaluates. A request that trips a stage gets the answer it had coming - its own
   failure, its own challenge, even its own success - and is told nothing about
   what it triggered. Only the requests that follow meet the lock or block, and
   only they are refused by it.

   So a threshold of 3 is reached by the third tracked event, and the request that
   carried it is answered normally; the *fourth* request is the first one refused.
   A ``DENY`` behaves the same way, for a different reason: it is evaluated before
   the credentials are checked, against the events already recorded, and this
   request's own event is not among them yet. Nothing turns away the request that
   reaches the threshold - if a threshold must bite one attempt earlier, lower it.

Rejection messages
------------------

A refused request is not told why: with nothing configured it carries at most
the generic ``Authentication failed.``, and the reason is in the
:ref:`authentication_log` and in the :ref:`audit` log. By default it can still
be told apart from a wrong password, though. At ``/validate/check`` an ordinary
failure names what failed (for example ``wrong otp pin``), and at ``/auth`` -
the WebUI login - a wrong password returns the error code ``4031`` where a
refusal returns ``403``; the WebUI shows the same sentence for both. Set the
authentication policy ``hide_specific_error_message`` to make a refusal
identical to any other failed authentication at these two endpoints
(``no_detail_on_fail`` does so at ``/validate/check`` only), see
:ref:`conditional_access_error_messages_masking`. ``/validate/radiuscheck``
answers every failure, a refusal included, with an empty ``400``.

Only a request refused by one of the questions above carries a message at
all. Because the request that writes a restriction is answered normally, a
restriction reaches a user in exactly one shape: the pre-credential refusal of
every request after it.

An administrator can choose to say more, either by writing an error message on
the stage that refuses, or by setting the ``show_default_ca_error_message``
policy. What is then shown, and how it relates to
``hide_specific_error_message`` and ``no_detail_on_fail``, is described in
:ref:`conditional_access_error_messages`.
