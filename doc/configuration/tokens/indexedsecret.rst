.. _indexedsecret_token:

Indexed Secret Token
--------------------

.. index:: Indexed Secret Token

The indexed secret token is a simple challenge response token.

A shared secret like "mySecret" is stored in the privacyIDEA server.
When the token is used a challenge is sent to the user like "Give me the 2nd and
the 4th position of your secret".

Then the user needs to respond with the concatenated characters from the given positions.
In the example the response would be "ye".

