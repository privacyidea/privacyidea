.. _customuserattributehandler:

Custom User Attribute Module
----------------------

.. index:: Custom User Attribute Handler, Handler Modules

The custom user attribute handler module can be used to automatically
set and remove custom user attributes.

This way you can automatically administer your custom user attributes or
an admin can make at easier for the helpdesk.


Possible Actions
~~~~~~~~~~~~~~~~

set_custom_user_attributes
................

You can set a custom_user_attribute automatically if a certain event is triggered. For example
if a user failed to log-in to many time, the eventhandler can automatically set the custom attribute
"this user has log-in problems".

delete_custom_user_attributes
................

With this action you can automatically delete custom_user_attributes. For example
you can give a new token the attribute "not working maybe" and if the user loges-in
for the first time the attribute is deleted.

