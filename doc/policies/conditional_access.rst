.. _policies_conditional_access:

Conditional access policies
---------------------------

.. index:: conditional access policies

.. versionadded:: 3.14

The scope *conditional_access* configures how :ref:`conditional_access` behaves
towards the end user. The rules that decide *whether* a request is refused are
not in this scope - they are the conditional access policies of their own, see
:ref:`conditional_access_policies`.

.. _policy_show_default_ca_error_message:

show_default_ca_error_message
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

Tell the user why conditional access turned their request away, using
privacyIDEA's default wording for the action that did it - for example *Your
account is temporarily locked. Please try again in about 10 minute(s).* for a
timed lock, or *Access has been denied.* for a ``DENY``.

Without this policy a rejection says only what the triggering stage was given
its own **error message** to say, and the generic ``Authentication failed.``
where none was written. A stage's own error message always takes precedence over
this policy.

Because the wording is per action, a stage that restricts more than one thing -
the user and the source address - is described by one sentence per restriction in
force, most severe first. There is wording only for the actions that turn a
request away, so a stage that locks the user *and* emails them is described by the
lock alone: the email is a one-off event that no lock records, and nothing is left
to report it on a later request.

The default wording is not stored on the lock or the block it describes - this
policy is matched on every request - so switching it on or off immediately
changes what the locks and blocks *already in force* say, with no re-locking
involved. It only fills in a missing message and never replaces one an
administrator wrote on a stage.

.. note:: This policy is independent of ``hide_specific_error_message``
   (:ref:`authentication scope <authentication_policies>`) and of
   ``no_detail_on_fail`` (:ref:`authorization scope <authorization_policies>`).
   Neither of those masks conditional access wording - see
   :ref:`conditional_access_error_messages_masking`.

.. warning:: Enabling this makes a lock, a block or a denial distinguishable
   from a wrong password. That is a deliberate trade: it tells a legitimate user
   whether to wait or to call the help desk, and it tells an attacker that they
   found a real account and hit a limit.

See :ref:`conditional_access_error_messages` for the whole picture: what each
endpoint says, which restriction is described, and how the wording of a lock is
stored.
