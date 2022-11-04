.. _login_webui:

Login to the Web UI
===================

.. _index: Web UI, Login

privacyIDEA has only one login form that is used by administrators and
normal users to login. Administrators will be able to configure the
system and to manage all tokens, while normal users will only be able
to manage their own tokens.

You should enter your username with the right realm.
You need to 
append the realm to the username like ``username@realm``.

Login for administrators
------------------------

Administrators can authenticate at this login form to access
the management UI.

Administrators are stored in the database table ``Admin`` and can be managed
with the tool::

   pi-manage admin ...

The administrator just logs in with his username.

.. note:: You can configure privacyIDEA to authenticate administrators
   against privacyIDEA itself, so that administrators
   need to login with a second factor. See
   :ref:`faq_admins` how to do this.


Login for normal users
----------------------

Normal users authenticate at the login form to be able to manage their own
tokens. By default users need to authenticate
with the password from their user source.

E.g. if the users are located in an LDAP or Active Directory
the user needs to authenticate with his LDAP/AD password.

But before a user can login, the administrator needs to configure 
realms, which is described in the next step :ref:`first_steps_realm`. 

.. note:: The user may either login with his password from the userstore
   or with any of his tokens.

.. note:: The administrator may change this behaviour
   by creating an according policy, which then requires
   the user to authenticate against privacyIDEA itself.
   I.e. this way the user needs to authenticate with
   a second factor/token to access the self service
   portal. (see the policy section :ref:`policy_login_mode`)

