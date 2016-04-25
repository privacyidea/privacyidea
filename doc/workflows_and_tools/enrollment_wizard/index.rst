.. _enrollment_wizard:

Token Enrollment Wizard
=======================

.. index:: Enrollment Wizard, Token Enrollment Wizard

The enrollment wizard helps the user to enroll his first token. When
enrolling the first token, we assume, that the user is not very familiar with
the privacyIDEA web UI. So the enrollment wizard only contains a very
reduced API.

Necessary requirements for the enrollment wizard
------------------------------------------------

 * The enrollment wizard will only be displayed, if the user has no token
   assigned, yet. Thus the user must be able to login to the web UI with his
   userstore password. This is the default behaviour or set the corresponding
   policy.

 * Set a policy in scope *webui* and activate the policy action
   :ref:`policy_token_wizard`.

 * The user will not be able to choose a token type. But the default token
   type will be enrolled.

You can see the token enrollment wizard in action here:
https://www.youtube.com/watch?v=diAGbsiG8_A


Customization
-------------

There are two dialog windows in the wizard. You can configure the text in the
wizard in your html templates defined in these files:

   static/customize/views/includes/token.enroll.pre.top.html
   static/customize/views/includes/token.enroll.pre.bottom.html
   static/customize/views/includes/token.enroll.post.top.html
   static/customize/views/includes/token.enroll.post.bottom.html


.. note:: You can change the directory static/customize to a URL that fits
   your needs the best by defining a variable PI_CUSTOMIZATION in the file
   pi.cfg. This way you can put all modifications in one place apart from the
   original code.
