.. _usernotification:

User Notification Handler Module
--------------------------------

.. index:: User Notification, Handler Modules

The user notification handler module is used to send emails token owners or
administrators in case of any event.

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

sendsms
.......

The *sendsms* action sends an SMS to the tokenowner. The SMS is sent, if an
administrator managed the users token.

**smsconfig**

  * *required* Option
  * The SMS Gateway configuration.


Options for both actions
~~~~~~~~~~~~~~~~~~~~~~~~

Both actions **sendmail** and **sendsms** take several common options.

**body**

  * optional

Here the administartor can specify the body of the email, that is sent.
The body may contain the following tags

  * {admin} name of the logged in user.
  * {realm} realm of the logged in user.
  * {action} the action that the logged in user performed.
  * {serial} the serial number of the token.
  * {url} the URL of the privacyIDEA system.
  * {user} the given name of the token owner.
  * {givenname} the given name of the token owner.
  * {surname} the surname of the token owner.
  * {username} the loginname of the token owner.
  * {userrealm} the realm of the token owner.
  * {tokentype} the type of the token.
  * {registrationcode} the registration code in the detail response.
  * {recipient_givenname} the given name of the recipient.
  * {recipient_surname} the surname of the recipient.

**To**

  * required

This specifies to which type of user the notification should be sent.
Possible recipient types are:

  * token owner,
  * logged in user,
  * admin realm,
  * internal admin,
  * email address.

Depending on the recipient type you can enter additional information. The
recipient type *email* takes a comma separated list of email addresses.

Code
~~~~


.. automodule:: privacyidea.lib.eventhandler.usernotification
   :members:
   :undoc-members:
