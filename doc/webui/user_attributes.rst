.. _user_attributes:

Additional user attributes
--------------------------

.. index:: User Attributes, Additional User Attributes

privacyIDEA allows you to manage additional internal attributes for
users read from resolvers.
These additional attributes are stored and managed within privacyIDEA.
The attributes are stored per realm: a user who is in several realms has separate attributes in
each of them, and a policy condition on an attribute only matches in the realm the attribute was
set in.
Administrators can manage attributes of users in the *Custom Attributes* section of the user
details (see policies :ref:`admin_set_custom_user_attributes` and
:ref:`admin_delete_custom_user_attributes`). Users can manage their attributes themselves through
the API, with ``POST /user/attribute`` and ``DELETE /user/attribute/<attrkey>/<username>/<realm>``
(see policies :ref:`user_set_custom_user_attributes` and :ref:`user_delete_custom_user_attributes`).
The WebUI offers adding and deleting attributes only to administrators.

The additional attributes are added to the user object, whenever a user is used.
With the authorization policy :ref:`policy_add_user_in_response`, the attributes are also added to
the response of a successful authentication request (in ``detail.user``). Thus these attributes
could be used to pass additional attributes via the RADIUS protocol.

The user attributes can also be used as additional conditions in policies
(see :ref:`policy_conditions`) in the userinfo section.
This way the additional attributes can be used to
group users together within privacyIDEA and assign distinct policies to these groups,
without the need to rely on information from the user store.

The policy condition uses attributes (userinfo) from the user store and additional user
attributes managed in privacyIDEA at the same time.

.. note:: If the user already has a certain key in the userinfo that is fetched from the
   resolver, the *additional user attributes* can also be used to *overwrite* the value
   from the user store!