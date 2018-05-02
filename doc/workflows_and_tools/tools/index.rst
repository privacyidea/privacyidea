.. _tools:

Tools
=====

.. index:: tools

privacyIDEA comes with a list of command line tools, which also help to
automate tasks.

.. _token_janitor:

privacyidea-token-janitor
-------------------------

.. index:: orphaned tokens

Starting with version 2.19 privacyIDEA comes with a token janitor script.
This script can find orphaned tokens, unused tokens or tokens of specific
type, description or token info.

It can unassign, delete or disable those tokens and it can set additional
tokeninfo or descriptions.

If you are unsure to directly delete orphaned tokens, because there might be
a glimpse in the connection to your user store, you could as well in a first
step *mark* the orphaned tokens. A day later you could run the script again
and delete those tokens, which are (still) *orphaned* and *marked*.


.. _get_unused_tokens:

privacyidea-get-unused-tokens
-----------------------------

The script ``privacyidea-get-unused-tokens`` allows you to search for tokens,
which were not used for authentication for a while. These tokens can be
listed, disabled, marked or deleted.

You can specify how old the last authentication of such a token has to be.
You can use the tags *h* (hours), *d* (day) and *y* (year).
Sepcifying *180d* will find tokens, that were not used for authentication for
the last 180 days.

The command

    privacyidea-get-unused-tokens disable 180d

will disable those tokens.

This script can be well used with the :ref:`scripthandler`.
