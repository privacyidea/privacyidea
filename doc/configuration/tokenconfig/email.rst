
.. _email_otp_token:

Email OTP Token
...............

.. index:: Email Token

.. figure:: images/email.png
   :width: 500

   *Email Token configuration*

The Email OTP token creates a OTP value and sends this OTP value to the email
address of the uses. The Email can be triggered by authenticating with only
the OTP PIN:

First step
~~~~~~~~~~

In the first step the user will enter his OTP PIN and the sending of the
Email is
triggered. The user is denied the access.

Seconds step
~~~~~~~~~~~~

In the second step the user authenticates with the OTP PIN and the OTP value
he received via Email. The user is granted access.

.. _index: transaction_id

Alternatively the user can authenticate with the *transaction_id* that was
sent to him in the response during the first step and only the OTP value. The
*transaction_id* assures that the user already presented the first factor (OTP
PIN) successfully.

Configuration Parameters
~~~~~~~~~~~~~~~~~~~~~~~~
You can configure the mail parameters for the Email Token centrally at
``Config -> Tokens -> Email``.

**Mail Server**

The name or IP address of the mail server that is used to send emails.

**Port**

The port of the mail server.

**Mail User**

If the mail server requires authentication you need to enter a username. If
no username is entered, no authentication is performed on the mail server.

**Mail User Password**

The password of the mail username to send emails.

**Mail Sender Address**

The mail address of the mail sender. This needs to correspond to the *Mail
User*.

**OTP validity time**

This is the time in seconds, for how long the sent OTP value is valid. If a
user tries to authenticate with the sent OTP value after this time,
authentication will fail.

**Use TLS**

Whether the mail server should use TLS.

**Concurrent Challenges**

The config entry ``email.concurrent_challenges`` will save the sent OTP
value in the challenge database. This way several challenges can be open at the same
time. The user can answer the challenges in an arbitrary order.
Set this to a true value.
