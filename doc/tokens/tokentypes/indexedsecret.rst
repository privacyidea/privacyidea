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

Certain policies can be used to either preset or force the value of the indexed secret during
enrollment to the value of a user attribute. The attribute specified in these policies is a privacyidea
attribute from the attribute mapping of the corresponding user resolver.

Starting with version 3.4 the Indexed Secret Token can work in multi challenge authentication.
This way each position is asked seperately in consecutive challenges. To achive this, the token needs
the tokeninfo value ``multichallenge=1``.