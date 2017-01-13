.. _tools:

Tools
=====

.. index:: tools

privacyIDEA comes with a list of command line tools, which also help to
automate tasks.

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
