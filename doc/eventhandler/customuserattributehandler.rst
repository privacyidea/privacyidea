.. _customuserattributehandler:

Custom User Attribute Module
----------------------

.. index:: Custom User Attribute Handler, Handler Modules

The custom user attribute handler module is a god way to automatic your custom user attributes.
You can set and delete on a specific event or you can use him for eas the life of off the helpdesk.
You can also set generic attributes that can't be delete by hand.


Possible Actions
~~~~~~~~~~~~~~~~

set_custom_user_attributes
................

You can set a custom_user_attribute automatically if a certain event is triggered. For example
if a user failed to log-in to many time, the eventhandler can automatically set the custom attribute
"this user has log-in problems".

delete_custom_user_attributes
................

With this action you can automatically delete custom_user_attributes. For example you can give
a token for a new user and set the custom user attribute "new user maybe needs help by the
first login" and if the user loges-in for the first time the attribute can be automatically deleted.

