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
