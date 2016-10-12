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

**subject**

  * optional

The subject line of the mail that is sent.

**body**

  * optional

Here the administartor can specify the body of the email, that is sent.
The body may contain the following tags

  * {admin} name of the logged in user.
  * {realm} realm of the logged in user.
  * {action} the action that the logged in user performed.
  * {serial} the serial number of the token.
  * {url} the URL of the privacyIDEA system.
  * {user} the given name of the user.
  * {givenname} the given name of the user.
  * {surname} the surname of the user.
  * {username} the loginname of the user (token owner).
  * {userrealm} the realm of the user (token owner)
  * {tokentyp} the type of the token.
  * {registrationcode} the registration code in the detail response.


sendsms
.......

The *sendsms* action sends an SMS to the tokenowner. The SMS is sent, if an
administrator managed the users token.

**smsconfig**

  * *required* Option
  * The SMS Gateway configuration.

**body**

  * optional

Here the administartor can specify the body of the SMS, that is sent.
The body may contain the same tags as with *sendmail*.


Code
~~~~


.. automodule:: privacyidea.lib.eventhandler.usernotification
   :members:
   :undoc-members:
