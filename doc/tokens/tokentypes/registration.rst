.. _registration_token:

Registration
------------

(See FAQ :ref:`faq_registration_code`)

The registration token can be used to create a registration code for a user.
This registration code can be sent via postal mail to the user, so that the
user can use this registration code as a second factor to login to a portal.

After a one single use, the registration code is deleted and can not be used
a second time.

The length and the contents of the registration code can be configured using the
:ref:`enrollment_policies` *registrationcode_length* and *registrationcode_contents*.

.. note:: The registration code can only be enrolled via the API to provide
   automated smooth workflow to your needs.

For a more detailed insight see the code documentation
:ref:`code_registration_token`.
