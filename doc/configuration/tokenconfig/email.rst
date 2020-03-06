
.. _email_token_config:

Email Token Configuration
...............

.. index:: Email Token

.. figure:: images/email.png
   :width: 500

   *Email Token configuration*

For the email token to work, you have to first setup an :ref:`smtpserver` and link it
to the Email Token configuration at *Config -> Tokens -> Email*. The UI warns the user
if one of these requirements is not fulfilled yet.

The Email OTP token creates a OTP value and sends this OTP value to the email
address of the uses. The email can be triggered by authenticating with only
the OTP PIN:


First step
~~~~~~~~~~

In the first step the user will enter his OTP PIN and the sending of the
email is
triggered. The user is denied the access.

Seconds step
~~~~~~~~~~~~

In the second step the user authenticates with the OTP PIN and the OTP value
he received via email. The user is granted access.

.. _index: transaction_id

Alternatively the user can authenticate with the *transaction_id* that was
sent to him in the response during the first step and only the OTP value. The
*transaction_id* assures that the user already presented the first factor (OTP
PIN) successfully.

Configuration Parameters
~~~~~~~~~~~~~~~~~~~~~~~~

**Concurrent Challenges**

The config entry ``email.concurrent_challenges`` set in :ref:`cfgfile` will save the sent OTP
value in the challenge database. This way several challenges can be open at the same
time. The user can answer the challenges in an arbitrary order.
Set this to a true value. Defaults to off.

Deprecated Configuration Parameters
~~~~~~~~~~~~~~~~~~~~~~~~

There are few more config entries handled, which are deprecated in recent versions of privacyIDEA.

* ``email.mailserver`` - The name or IP address of the mail server that is used to send emails.

* ``email.port`` - The port of the mail server.

* ``email.username`` - If the mail server requires authentication you need to enter a username. If
  no username is entered, no authentication is performed on the mail server.

* ``email.password`` - The password of the mail username to send emails.

* ``email.mailfrom`` - The mail address of the mail sender. This needs to correspond to the *Mail
  User*.

* ``email.validtime`` - This is the time in seconds, for how long the sent OTP value is valid. If a
  user tries to authenticate with the sent OTP value after this time,
  authentication will fail.

* ``email.tls`` - Whether the mail server should use TLS.
