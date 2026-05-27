.. _token_policies:

Token policies
-------------------

.. index:: token policies

The scope *token* defines properties of token objects, which are not subject to :ref:`enrollment_policies` or :ref:`authentication_policies`, so
typically revolving around the management of tokens.

The following actions are available in the scope *token*:


require_description_on_edit
~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``list``

To prevent tokens from becoming unidentifiable after a device loss, a description can
be enforced with the "require_description_on_edit policy". The desired token-types can be
selected here. After setting up the policy, the description of selected token types can only be
edited with non-empty values.

.. versionadded:: 3.12


.. _policy_hide_specific_error_message_for_ttype:

hide_specific_error_message_for_ttype
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``bool``

If this policy is set, exceptions raised by a token class' ``api_endpoint``
during a request to ``/ttype/<tokentype>`` are masked into a generic
"Failed special token function" error response. Without the policy the
underlying error message is propagated to the caller.

This is useful when token-type-specific endpoints (TiQR, push, U2F,
Yubikey) are exposed to untrusted networks and detailed error messages
could leak server-side state.
