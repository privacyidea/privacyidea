.. _login_webui:

Login to the Web UI
===================

.. _index: Web UI, Login

privacyIDEA has one login form for users to login and for
administrators to login.

The login screen can contain a dropdown box with the list of
existing realms. The dropdown box can be configured 
in the :ref:`system_config` dialog on the :ref:`gui_settings` tab.

You should enter your username and choose the right realm.
If the dropdown box is not displayed, then you need to 
append the realm to the username like ``username@realm``.

Login for normal users
----------------------

Normal users authenticate at the login form to access the
self service portal. By default users need to authenticate
with the password from their user source.

E.g. if the users are located in an LDAP or Active Directory
the user needs to authenticate with his LDAP/AD password.

.. note:: The administrator may change this behaviour
   by creating an according policy, which then requires
   the user to authenticate against privacyIDEA itself.
   I.e. this way the user needs to authenticate with
   a second factor/token to access the self service
   portal. (see the policy section :ref:`policy_auth_otp`)

Login for administrators
------------------------

Administrators can authenticate at this login form to access
the management UI and also access the self service portal,
if the account they login with is also contained in a realm.

By default administrators are defined in a file, that is
configured the ini-file. (see :ref:`_inifile_superusers`).
Administrators defined in this file, need to login with 
the "virtual" realm ``admin``. 

E.g. the administrator "administrator" defined in this
file needs to login as ``administrator@admin`` with
the password stored in this file.

.. note:: You can configure privacyIDEA to authenticate administrators
   against privacyIDEA itself, so that administrators
   need to login with a second factor. See :ref:`inifile_superusers`
   how to do this.

