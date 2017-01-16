.. _performance_tokenview:

What happens in the tokenview?
------------------------------

A question which comes up often is why you can not view hundrets of tokens in
the tokenview. Well - you are doing - you are just paging through the list ;-)

Ok, here it what happens in the tokenview.

The tokenview fetches a slice of the tokens from the token database. So, if
you configure the tokenview to display 15 tokens, only 15 tokens will be
fetched using the ``LIMIT`` and ``OFFSET`` mechanisms of SQL.

But what really influences the performance is the user resolver part.
privacyIDEA does not store username, givenname or surname of the token owner.
The token table only contains a "pointer" to the user object in the userstore.
This pointer consists of the userresolver ID and the user ID in this resolver.
This is usefull, since the username or the surname of the user may change. At
least in Germany the givenname only changes in very rare cases.

This means that privacyIDEA needs to contact the userstore, to resolve the
user ID to a username and a surname, givenname. Now you know that you will
create 100 LDAP requests, if you choose to display 100 tokens on one page.

Although we are doing some LDAP caching, this will not help with new pages.

We very much recommend using the search capabilities of the tokenview.


