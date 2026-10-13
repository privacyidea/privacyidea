.. _login_webui:

Login to the Web UI
===================

.. index:: Web UI, Login

privacyIDEA has only one login form that is used by administrators and
normal users to log in. Administrators will be able to configure the
system and to manage all tokens, while normal users will only be able
to manage their own tokens.

Users of the default realm log in with their username. Users of another
realm append the realm to the username, like ``username@realm`` (as long as
:ref:`splitatsign` is enabled, which is the default), or select the realm in
the *Realm* field of the login form, if a ``realm_dropdown`` policy (see
:ref:`webui_policies`) shows it. The administrators in the database table
``Admin`` always log in with their plain username, without a realm; a realm
selected in the login form is ignored for them.

Login for administrators
------------------------

Administrators can authenticate at this login form to access
the management UI.

Administrators are stored in the database table ``Admin`` and can be managed
with the tool::

   pi-manage admin

See :ref:`pimanage_admin`. The administrator just logs in with his username.

.. note:: The :ref:`policy_login_mode` policy does not apply to the
   administrators in the database table ``Admin``: they keep logging in with
   their password, also if a ``login_mode`` policy requires a token or
   disables the login. So they can not be required to use a second factor.
   Users of a realm that is listed in ``SUPERUSER_REALM`` in ``pi.cfg`` are
   administrators, too; they log in with their username and that realm
   (e.g. ``username@adminrealm``). For them, a ``login_mode`` policy with the
   value ``privacyIDEA`` requires a token at the login, unless an
   authentication policy such as ``passthru`` or ``passOnNoToken`` matches
   them. See :ref:`faq_admins` how to set this up.


Login for normal users
----------------------

Normal users authenticate at the login form to be able to manage their own
tokens. By default users need to authenticate
with the password from their user source.

E.g. if the users are located in an LDAP or Active Directory
the user needs to authenticate with his LDAP/AD password.

But before a user can log in, the administrator needs to configure
realms, which is described in the next step :ref:`first_steps_realm`.

.. note:: The PIN and OTP value of a token are not accepted at this login,
   only the password from the user store. A user who has a passkey can also
   log in with *Log In With Passkey* (see :ref:`policy_passkey_login`).

.. note:: The administrator may change this behavior with the
   :ref:`policy_login_mode` policy. With the value ``privacyIDEA`` the user
   has to log in with one of their tokens, e.g. with the token PIN followed
   by the OTP value, and the password from the user store is no longer
   accepted. Authentication policies that match the user also apply to this
   login: with ``passOnNoToken`` a user without a token logs in with any
   password, with ``passthru`` with the user store password.
