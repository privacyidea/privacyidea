.. _management_policies:

Management policies
-------------------

.. index:: management policies

The scope *management* defines what happens when managing tokens
either by an administrator or the user.

The following actions are available in the scope
*management*:


require_description_on_edit
~~~~~~~~~~~~~~~~~~~~~~~~~~~

type: ``list``

To prevent tokens from becoming unidentifiable after a device loss, a description can
be enforced with the "require_description_on_edit policy". The desired token-types can be
selected here. After setting up the policy, the description of selected token types can only be
edited with non-empty values.