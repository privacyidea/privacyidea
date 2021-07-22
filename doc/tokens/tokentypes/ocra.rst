.. _ocra_token:

OCRA
----

.. index:: OCRA

Starting with version 2.20 privacyIDEA supports common OCRA tokens.
OCRA tokens can not be enrolled via the UI but need to be imported via a seed
file.
The OATH CSV seed file would look like this::

    <serial>, <seed>, ocra, <ocrasuite>

The OCRA token is a challenge/response token. So the first authentication
request issues a challenge. This challenge is the input for the response of
the OCRA token.

For more information see :ref:`code_ocra_token`.

DisplayTAN token
~~~~~~~~~~~~~~~~

privacyIDEA supports the DisplayTAN [#displaytan]_, which can be used for
securing banking
transactions. The OCRA Algorithm is used to digitally sign transaction data.
The transaction data can be verified by the user on an external banking card.
All cryptographical processes are running on the external card, so that an
attacker can not interfere with the user's component.

The DisplayTAN cards would be imported into privacyIDEA using the token import.

A banking website will use the :ref:`rest_validate` API.

The first call will trigger the challenge response mechanism. The first call
needs to contain the transaction data: the recipient's account number and
amount of money to transfer::

   <account>~<amount>~

Please note the tilde::

    POST https://privacyidea.example.com/validate/check

    pass=pin
    serial=ocra1234
    challenge=1234567890~423,40~
    addrandomchallenge=20
    hashchallenge=sha1

This will result in a response like this::

   {
     "jsonrpc": "2.0",
     "signature": "128057011582042...408",
     "detail": {
                "multi_challenge": [
                   {
                    "attributes": {
                    "qrcode": "data:image/png;base64, iVBORw0KG..RK5CYII=",
                    "original_challenge": "83507112  ~320,
                  00~cfbGSopfdDROOMjeu3IR",
                    "challenge": "f8a1818f35ae0cc64fe8a191961ec829487dfa82"
                    },
                    "serial": "ocra1234",
                    "transaction_id": "05221757445370623976"
                   }
                ],
                "threadid": 139847557760768,
                "attributes": {
                "qrcode": "data:image/png;base64, iVBO...CYII=",
                "original_challenge": "83507112  ~320,00~cfbGSopfdDROOMjeu3IR",
                "challenge": "f8a1818f35ae0cc64fe8a191961ec829487dfa82"
                },
                "message": "Please answer the challenge",
                "serial": "ocra1234",
                "transaction_id": "05221757445370623976"
     },
     "versionnumber": "2.20.dev2",
     "version": "privacyIDEA 2.20.dev2",
     "result": {
                "status": true,
                "value": false
     },
     "time": 1504005837.417481,
     "id": 1
   }

.. note:: The response also contains the QR code. The banking website should
   show the QR code, so that the user can scan it with the DisplayTAN App to
   transfer the data to the card.

The user can verify the data on the card and transaction data will be
digitally signed on the card.
The card will calculate an OTP value for this very transaction.

The banking website can now send the OTP value to privacyIDEA to check,
if the user authorized the correct transaction data. The banking site
will issue this request::

    POST https://privacyidea.example.com/validate/check

    serial=ocra1234
    transaction_id=05221757445370623976
    pass=54006635

privacyIDEA will respond with a usual authentication response::

    {
     "jsonrpc": "2.0",
     "signature": "162....2454851",
     "detail": {
                "message": "Found matching challenge",
                "serial": "ocra1234",
                "threadid": 139847549368064
               },
     "versionnumber": "2.20.dev2",
     "version": "privacyIDEA 2.20.dev2",
     "result": {
                "status": true,
                "value": true
     },
     "time": 1504005901.823667,
     "id": 1
    }


.. [#displaytan] http://www.display-tan.com/
