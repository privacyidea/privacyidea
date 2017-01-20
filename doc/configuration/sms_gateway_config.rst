.. _sms_gateway_config:

SMS Gateway configuration
-------------------------

.. index:: SMS Gateway, SMS Provider

You can centrally define SMS gateways that can be used to send SMS with the
SMS token (:ref:`sms_otp_token`) or to use the SMS gateway for sending
notifications.

There are different providers (gateways) to deliver SMS.

HTTP provider
~~~~~~~~~~~~~

.. index:: HTTP Provider

The HTTP provider can be used for any SMS gateway that provides a simple
HTTP POST or GET request. This is the most commonly used provider.
Each provider type defines its own set of parameters.

The following parameters can be used. These are parameters, that define the
behaviour of the SMS Gateway definition.


**URL**

   This is the URL for the gateway.

**HTTP_METHOD**

   Can be GET or POST.

**USERNAME** and **PASSWORD**

   These are the username and the password if the HTTP request requires
   **basic authentication**.

**RETURN_SUCCESS**

   You can either use ``RETURN_SUCCESS`` or ``RETURN_FAIL``.
   If the text of ``RETURN_SUCCESS`` is found in the HTTP response
   of the gateway privacyIDEA assumes that the SMS was sent successfully.

**RETURN_FAIL**

   If the text of ``RETURN_FAIL`` is found in the HTTP response
   of the gateway privacyIDEA assumes that the SMS could not be sent
   and an error occurred.

**PROXY**

   You can specify a proxy to connect to the HTTP gateway.

**PARAMETER**

   This can contain a dictionary of arbitrary fixed additional
   parameters. Usually this would also contain an ID or a password
   to identify you as a sender.

**CHECK_SSL**

   If the URL is secured via TLS (HTTPS), you can select, if the
   certificate should be verified or not.

**TIMEOUT**

   The timeout for contacting the API and receiving a response.

Options
.......

You can define additional options. These are sent as parameters in the GET or
POST request.

.. note:: The fixed parameters and the options can not have the same name! If
   you need an options, that has the same name as a parameter, you must not
   fill in the corresponding parameter.

.. note:: You can use the tags ``{phone}`` and ``{otp}`` to specify the mobile
   number and the otp value.

Examples
........

Clickatell
''''''''''

In case of the **Clickatell** provider the configuration will look like this:

 * **URL**: http://api.clickatell.com/http/sendmsg
 * **HTTP_METHOD**: GET
 * **RETURN_SUCCESS**: ID

Set the additional **options** to be passed as HTTP GET parameters:

 * user: *YOU*
 * password: *your password*
 * api_id: *you API ID*
 * text: "Your OTP value is {otp}"
 * to: {phone}

This will consturct an HTTP GET request like this::

   http://api.clickatell.com/http/sendmsg?user=YOU&password=YOU&\
        api_id=YOUR API ID&text=....&to=....

where ``text`` and ``to`` will contain the OTP value and the mobile
phone number. privacyIDEA will assume a successful sent SMS if the
response contains the text "ID".

GTX-Messaging
'''''''''''''

GTX-Messaging is an SMS Gateway located in Germany.

The configuration looks like this (see [#gtxapi]_):

 * **URL**: https://http.gtx-messaging.net/smsc.php
 * **HTTP_METHOD**: GET
 * **CHECK_SSL**: yes
 * **RETURN_SUCCESS**: 200 OK

You need to set the additional **options**:

 * user: <your account>
 * pass: <the account password>
 * to: {phone}
 * text: Your OTP value is {otp}.

.. note:: The *user* and *pass* are not the credentials you use to login.
   You can find the required credentials for sending SMS  in your GTX
   messaging account when viewing the details of your *routing account*.

Twilio
''''''

You can also use the **Twilio** service for sending SMS. [#twilio]_.

 * **URL**: https://api.twilio.com/2010-04-01/Accounts/B...8/Messages
 * **HTTP_METHOD**: POST

For basic authentication you need:

 * **USERNAME**: *your accountSid*
 * **PASSWORD**: *your password*

Set the additional **options** as POST parameters:

 * From: *your Twilio phone number*
 * Body: {otp}
 * To: {phone}


Sipgate provider
~~~~~~~~~~~~~~~~

The sipgate provider connects to https://samurai.sipgate.net/RPC2 and takes only
two arguments *USERNAME* and *PASSWORD*.

Parameters:

**USERNAME**

   The sipgate username.

**PASSWORD**

   The sipgate password.

**PROXY**

   You can specify a proxy to connect to the HTTP gateway.

It takes not options.

If you activate debug log level you will see the submitted SMS and the response
content from the Sipgate gateway.

SMTP provider
~~~~~~~~~~~~~

The SMTP provider sends an email to an email gateway. This is a specified,
fixed mail address.

The mail should contain the phone number and the OTP value. The email gateway
will send the OTP via SMS to the given phone number.

**SMTPIDENTIFIED**

   Here you can select on of your centrally defined SMTP servers.

**MAILTO**

   This is the address where the email with the OTP value will be sent.
   Usually this is a fixed email address provided by your SMTP Gateway
   provider. But you can also use the tags ``{phone}`` and ``{otp}`` to
   replace the phone number or the one time password.

**SUBJECT**

   This is the subject of the email to be sent.
   You can use the tags ``{phone}`` and ``{otp}`` to
   replace the phone number or the one time password.

**BODY**

   This is the body of the email. You can use this to explain the user, what
   he should do with this email.
   You can use the tags ``{phone}`` and ``{otp}`` to
   replace the phone number or the one time password.


The default *SUBJECT* is set to *{phone}* and the default *BODY* to *{otp}*.
You may change the *SUBJECT* and the *BODY* accordingly.


.. [#twilio] https://www.twilio.com/docs/api/rest/sending-messages
.. [#gtxapi] https://www.gtx-messaging.com/de/api-docs/http/

