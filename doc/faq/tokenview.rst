.. _performance_tokenview:

What happens in the tokenview?
------------------------------

A question which comes up often is why you can not view hundreds of tokens in
the tokenview. Well - you are doing - you are just paging through the list ;-)

OK, here is what happens in the tokenview.

The tokenview fetches a slice of the tokens from the token database. So, if
you configure the tokenview to display 15 tokens, only 15 tokens will be
fetched using the ``LIMIT`` and ``OFFSET`` mechanisms of SQL.

But what really influences the performance is the user resolver part.
privacyIDEA does not store the login name of the token owner.
The token table only contains a "pointer" to the user object in the user store.
This pointer consists of the user resolver ID and the user ID in this resolver.
This is useful, since the login name of the user may change.

This means that privacyIDEA needs to contact the user store to resolve the user
IDs of the listed tokens to login names. It looks up the users of each resolver
together: the LDAP resolver needs one search per 100 users of the page, the
SQL resolver one query per 500 users. Other resolvers (e.g. flat file, SCIM and
HTTP-based resolvers) are still asked once per user. So with LDAP and SQL resolvers,
the number of tokens on one page has little influence on the number of
requests to the user store.

We very much recommend using the search capabilities of the tokenview.


