.. _usernotification:

User Notification Handler Module
--------------------------------

.. index:: User Notification, Handler Modules

The user notification handler module is used to send emails to the owner of a
token.

This module can be used to inform users, whenever the administrator manages
any aspect of their tokens.

Possible Actions
~~~~~~~~~~~~~~~~

sendmail
........

The *sendmail* action sends an email to the tokenowner user. The email is
sent, if an administrator managed the users token.

**emailconfig**

  * *required* Option
  * The email is sent via this :ref:`smtpserver`.


Code
~~~~


.. automodule:: privacyidea.lib.eventhandler.usernotification
   :members:
   :undoc-members:
