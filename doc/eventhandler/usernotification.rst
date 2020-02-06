.. _usernotification:

User Notification Handler Module
--------------------------------

.. index:: User Notification, Handler Modules

The user notification handler module is used to send emails token owners or
administrators in case of any event.

Possible Actions
~~~~~~~~~~~~~~~~

.. _sendmail_action:

sendmail
........

The *sendmail* action sends an email to the specified email address each time
the event handler is triggered.

**emailconfig**

  * *required* Option

The email is sent via this :ref:`smtpserver`.

**To**

  * *required* Option

This specifies to which type of user the notification should be sent.
Possible recipient types are:

  * token owner,
  * logged in user,
  * admin realm,
  * internal admin,
  * email address.

Depending on the recipient type you can enter additional information. The
recipient type *email* takes a comma separated list of email addresses.

**reply_to**

Adds the specified ``Reply-To`` header to the email.

**subject**

The subject can take the same tags as the body, except for the ``{googleurl_img}``.

**mimetype**

Possible mime types are:

  * plain (default)
  * html

You can choose if the email should be sent as plain text or HTML. If the
email is sent as HTML, you can do the following::

   <a href={googleurl_value}>Your new token</a>

Which will create a clickable link. Clicked on the smartphone, the token will
be imported to the smartphone app.

You can also do this::

  <img src={googleurl_img}>

This will add the QR Code as an inline data image into the HTML email.

.. warning:: The KEY URI and the QR Code contain the secret OTP key in plain
   text. Everyone who receives this data has a detailed copy of this token.
   Thus we very much recommend to **never** send these data in an unencrypted
   email!

**attach_qrcode**

Instead of sending the QR-Code as an inline data image (which is not supported
by some email clients (i.e. Outlook) or GMail [#gmailimg]_), enabling this
option sends the email as a multipart message with the QR-Code image as an
attachment. The attached image can be referenced in a HTML body via CID
URL [#cidurl]_ with the *Content-ID* ``token_image``::

  <img src="cid:token_image" alt="Token Image" style="..."/>

.. _sendsms_action:

sendsms
.......

The *sendsms* action sends an SMS to the specified number each time the event
handler is triggered.

**smsconfig**

  * *required* Option

The :ref:`sms_gateway_config` for sending the notification.

**To**

  * *required* Option

Possible recipients are:

  * tokenowner

.. _savefile_action:

savefile
........

The *savefile* action saves a file to a spool directory.
Each time the event handler is triggered a new file is saved.

In the ``pi.cfg`` file you can use the setting ``PI_NOTIFICATION_HANDLER_SPOOLDIRECTORY``
to configure a spool directory, where the notification files will be written.
The default file location is ``/var/lib/privacyidea/notifications/``.
The directory needs to be writable for the user *privacyidea*.

**filename**

  * *required* option
  * The filename of the saved file. It can contain the tag
    ``{random}`` which will create a 16 characters long
    alpha numeric string. Thus you could have a filename like
    ``notification-{random}.csv``.

In addition you can use all tags that can be used in the body
also in the filename (some of them might not make a lot of sense!).

.. note:: Existing files are overwritten.

Body for all actions
~~~~~~~~~~~~~~~~~~~~

All actions take the common option *body*:

**body**

  * optional for :ref:`sendmail_action` and :ref:`sendsms_action`
  * required for :ref:`savefile_action`

Here the administrator can specify the body of the notification, that is sent or saved.
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
  * {googleurl_value} is the KEY URI for a google authenticator.
  * {googleurl_img} is the data image source of the google authenticator QR code.
  * {time} the current server time in the format HH:MM:SS.
  * {date} the current server date in the format YYYY-MM-DD
  * {client_ip} the client IP of the client, which issued the original request.
  * {ua_browser} the user agent of the client, which issued the original request.
  * {ua_string} the complete user agent string (including version number), which issued the original request.
  * {pin} the PIN of the token when set with ``/token/setrandompin``. You can remove the
    PIN from the response using the *response mangler*.


Code
~~~~


.. automodule:: privacyidea.lib.eventhandler.usernotification
   :members:
   :undoc-members:


.. rubric:: Footnotes

.. [#gmailimg] https://stackoverflow.com/a/42014708/7036742
.. [#cidurl] https://tools.ietf.org/html/rfc2392
