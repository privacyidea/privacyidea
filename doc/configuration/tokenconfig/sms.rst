
.. _sms_token_config:

SMS Token Configuration
.......................

.. index:: SMS Token

The :ref:`SMS token <sms_token>` creates an OTP value and sends this OTP value to the mobile
phone of the user. The SMS can be triggered by authenticating
with only the OTP PIN:

First step
~~~~~~~~~~

In the first step the user will enter his OTP PIN and the sending of the SMS is
triggered. The user is denied access for now.

Second step
~~~~~~~~~~~

In the second step, the user authenticates with the OTP PIN and the OTP value
he received via SMS. The user is granted access if the OTP values match.

.. index:: transaction_id

Alternatively, the user can authenticate with the ``transaction_id`` that was
sent to him in the response during the first step and only the OTP value. The
``transaction_id`` assures that the user already presented the first factor (OTP
PIN) successfully.

Configuration Parameters
~~~~~~~~~~~~~~~~~~~~~~~~

**SMS Gateway configuration**
    .. index:: SMS Gateway

    You can centrally define the SMS gateways used for sending
    SMS OTP token but also for the event notifications. (See
    :ref:`usernotification`)

    For configuring SMS Gateways read :ref:`sms_gateway_config`.
    In this token configuration you can select on defined gateway to send SMS for
    authentication.

**OTP validity time**
  This is the time in seconds, for how long the sent OTP value is valid. If a
  user tries to authenticate with the sent OTP value after this time,
  authentication will fail.
