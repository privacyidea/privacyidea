.. _userview:

Userview
=========

.. index:: userview

The administrator can see all users in **realms** he is allowed 
to manage. 

.. note:: Users are only visible, if the useridresolver is located 
   within a realm. If you only define a useridresolver but no realm,
   you will not be able to see the users!

You can select one of the realms in the left drop down box. The administrator
will only see the realms in the drop down box, that he is allowed to manage.

The list shows the users from the select realm. The username, surname,
given name, email and phone are filled according to the definition of 
the useridresolver. 

Even if a realm contains several useridresolvers all users from all
resolvers within this realm are displayed.

As privacyIDEA only reads users from user sources the actions you can 
perform on the users are very limited.

Enroll tokens
-------------

The usual action to do is to enroll a token. To enroll a token to a specific user
you can search for the user, select the user and then click the button
*enroll* on the left side.

In the enrollment dialog you can choose which token type you want to enroll.


Assign tokens
-------------

If you want to assign an existing token to a user, you need to select the
user and select the token in the :ref:`tokenview` and then you can 
click the button *assign*.
