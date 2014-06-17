
.. _sms_otp_token:

SMS OTP Token
.............

.. index:: SMS token

The SMS OTP token creates a OTP value and sends this OTP value to the mobile
phone of the user. The SMS can be triggered by an API call or by authenticating
with only the OTP PIN:

In the first step the user will enter his OTP PIN an the sending of the SMS is
triggered. The user is denied the access.

In the second step the user authenticates with the OTP PIN and the OTP value
he received via SMS. The user is granted access.

.. index:: Sipgate, Clickatel, SMS Gateway

A python SMS provider module defines how the SMS is sent. This can be done
using an HTTP SMS Gateway. Most services like Clickatel or sendsms.de provide
such a simple HTTP gateway. Another possibility is to send SMS via sipgate, 
which provides an XMLRPC API.
The third possibility is to send the SMS via an SMTP gateway. The proovider
receives a specially designed email and sends the SMS accordingly.
The last possibility to send SMS is to use an attached GSM modem.

In the field ``SMS provider`` you can enter the SMS provider module, you
wish to use. In the *empty* field hit the arrow-down key and you will get 
a list of the ready made modules.

In the ``SMS configuration`` text area you can enter the configuration,
which contents is very much dependant on the selected provider module.

The HTTP and the Sipgate module provide a preset-button, which give you
an idea of the configuration.

HTTP provider
~~~~~~~~~~~~~

The HTTP provider can be used for any SMS gateway that provides a simple
HTTP POST or GET request.

The following parameters can be used:

**URL**

   This is the URL for the gateway.

**HTTP_Method**

   Can be GET or POST.

**USERNAME** and **PASSWORD**

   These are the username and the password if the HTTP request requires
   basic authentication.

**SMS_PHONENUMBER_KEY**

   This is the name of the HTTP parameter that holds the mobile phone
   number of the recipient.

**SMS_TEXT_KEY**

   This is the name of the HTTP parameter that holds the SMS text.

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

Example:
''''''''

In case of the Clicaktell provider the configuration will look like this::

   { "URL" : "http://api.clickatell.com/http/sendmsg",
     "PARAMETER" : {
                     "user":"YOU",
                     "password":"YOUR PASSWORD",
                     "api_id":"YOUR API ID"
                   },
     "SMS_TEXT_KEY":"text",
     "SMS_PHONENUMBER_KEY":"to",
     "HTTP_Method":"GET",
     "RETURN_SUCCESS" : "ID"
   }

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
The arguments have to be passed in a dictionary like this::
   
   { "USERNAME" : "youruser",
     "PASSWORD" : "yourpassword" }

.. note:: You need to use double quotes around the values.

If you activate debug log level you will see the submitted SMS and the response
content from the Sipgate gateway.


