
.. _sms_otp_token:

SMS OTP Token
.............

.. index:: SMS Token

The SMS OTP token creates a OTP value and sends this OTP value to the mobile
phone of the user. The SMS can be triggered by authenticating
with only the OTP PIN:

First step
~~~~~~~~~~

In the first step the user will enter his OTP PIN and the sending of the SMS is
triggered. The user is denied the access.

Second step
~~~~~~~~~~~

In the second step the user authenticates with the OTP PIN and the OTP value
he received via SMS. The user is granted access.

.. _index: transaction_id

Alternatively the user can authenticate with the *transaction_id* that was
sent to him in the response during the first step and only the OTP value. The
*transaction_id* assures that the user already presented the first factor (OTP
PIN) successfully.

.. index:: Sipgate, Clickatel, SMS Gateway

A python SMS provider module defines how the SMS is sent. This can be done
using an HTTP SMS Gateway. Most services like Clickatel or sendsms.de provide
such a simple HTTP gateway. Another possibility is to send SMS via sipgate, 
which provides an XMLRPC API.
The third possibility is to send the SMS via an SMTP gateway. The provider
receives a specially designed email and sends the SMS accordingly.
The last possibility to send SMS is to use an attached GSM modem.

.. _index: SMS Gateway

Starting with version 2.13 the SMS configuration has been redesigned. You can
now centrally define SMS gateways. These SMS gateways can be used for sending
SMS OTP token but also for the event notifications. (See
:ref:`usernotification`)

For configuring SMS Gateways read :ref:`sms_gateway_config`.
I this token configuration you can select on defined gateway to send SMS for
authentication.
