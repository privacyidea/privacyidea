
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

HTTP provider
~~~~~~~~~~~~~

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
'''''''

You can define additional options. These are sent as parameters in the GET or
POST request.

.. note:: The fixed parameters and the options can not have the same name! If
   you need an options, that has the same name as a parameter, you must not
   fill in the corresponding parameter.

.. note:: You can use the tags ``{phone}`` and ``{otp}`` to specify the mobile
   number and the otp value.

Example
'''''''

In case of the Clicaktell provider the configuration will look like this::

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


