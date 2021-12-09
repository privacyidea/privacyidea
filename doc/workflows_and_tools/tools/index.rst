.. _tools:

.. todo:: Extend description and add more tools from /opt/privacyidea/bin?

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

Starting with version 3.4 it can also set the tokenrealms of the found tokens.

If you are unsure to directly delete orphaned tokens, because there might be
a glimpse in the connection to your user store, you could as well in a first
step *mark* the orphaned tokens. A day later you could run the script again
and delete those tokens, which are (still) *orphaned* and *marked*.

With version 3.7 it can also filter for token attributes and attribute values.
It is also possible to check just for the existence or not-existence of a
certain tokeninfo-value.


Find
~~~~

With the token-janitor you have the possibility to search for tokens in different ways.

Description
***********
Searches through all tokens and returns the ones with the selected description.

Example::

    privacyidea-token-janitor find --description '^fo.*'

Return all tokens where the description begins with "fo".

Serial
******

Searches through all tokens and returns the ones with the selected serial.

Example::

    privacyidea-token-janitor find --serial OATH0013B2B4

Return all tokens with the serial ``OATH0013B2B4``.

You can also search for regular expressions. This is interesting, e.g. if finding yubikeys, which might be a tokentype "HOTP", but where the serial starts with UBOM.

Example::

    privacyidea-token-janitor find --serial '^UBOM.*'


Tokentype
*********

Searches through all tokens and returns the ones with the selected tokentype.

Example::

    privacyidea-token-janitor find --tokentype hotp

Return all tokens with the tokentype ``hotp``.

Tokenattribute
**************

Match for a certain token attribute from the database.

There are different ways of filtering here.

tokenattribute-value REGEX|INTEGER
..................................

The value of the token-attribute which should match.

Example::

    privacyidea-token-janitor find --tokenattribute rollout_state --tokenattribute-value clientwait

Search for all tokens with the tokenattribute-key ``rollout_state`` and the associated tokenattribute-value ``clientwait``.

**Note that it is also possible to work with regular expressions here.**

tokenattribute-value-less-than INTEGER
......................................

Match if the value of the token attribute is less than the given value.

Example::

    privacyidea-token-janitor find --tokenattribute active --tokenattribute-value-less-than 1

Search for all tokens with the tokenattribute-key ``active`` and the associated tokenattribute-value below ``1``.

tokenattribute-value-greater-than INTEGER
.........................................

Match if the value of the token attribute is greater than the given value.

Example::

    privacyidea-token-janitor find --tokenattribute active --tokenattribute-value-greater-than 0

Search for all tokens with the tokenattribute-key ``active`` and the associated tokenattribute-value greater than ``0``.

Tokeninfo-key
*************

The tokeninfo-key to match.

There are different ways of filtering here.

has-tokeninfo-key
.................

Filters for tokens that have given the specified tokeninfo-key.

Example::

    privacyidea-token-janitor find --has-tokeninfo-key import_time

Searches for all tokens that have stored the tokeninfo-key ``import_time``.

**Note, that it is not important, what value the "import_time" actually has!**

has-not-tokeninfo-key
.....................

Filters for tokens that have not given the specified tokeninfo-key.

Example::

    privacyidea-token-janitor find --has-not-tokeninfo-key import_time

Searches for all tokens that didn't store the tokeninfo-key ``import_time``.

tokeninfo-value REGEX|INTEGER
.............................

The tokeninfo-value to match.

Example::

    privacyidea-token-janitor find --tokeninfo-key tokenkind --tokeninfo-value software

Search for all tokens with the tokeninfo-key ``tokenkind`` and the associated tokeninfo-value ``software``.

tokeninfo-value-less-than INTEGER
.................................

Interpret tokeninfo-values as integers and match only if they are smaller than the given integer.

Example::

    privacyidea-token-janitor find --tokeninfo-key timeWindow --tokeninfo-value-less-than 200

Search for all tokens with the tokeninfo-key ``timeWindow`` and the associated tokeninfo-value below ``200``.

tokeninfo-value-greater-than INTEGER
....................................

Interpret tokeninfo-values as integers and match only if they are greater than the given integer.

Example::

    privacyidea-token-janitor find --tokeninfo-key timeWindow --tokeninfo-value-greater-than 100

Search for all tokens with the tokeninfo-key ``timeWindow`` and the associated tokeninfo-value greater than ``100``.

Actions
*******

Actions are performed by the token janitor on **all** found tokens.

mark - disable - delete - unassign - export - listuser - tokenrealms

mark
....

**Mark** makes it possible to mark single or multiple tokens in order to carry out further actions with them later.

The tokens are marked by setting a tokeninfo-key and an associated tokininfo-value.

Example::

    privacyidea-token-janitor find --serial OATH0004C934 --action mark --set-tokeninfo-key unused --set-tokeninfo-value True

A new tokeninfo-key and the associated tokeninfo-value have been added for the token ``OAUTH0004C934``
and are now marked for later processing.


disable
.......

With **disable** single or multiple tokens can be disabled.


Example::

    privacyidea-token-janitor find --serial OATH0004C934 --action disable

The token with the serial ``OAUTH0004C934`` will be disabled.

delete
......

With **delete** single or multiple tokens can be deleted.


Example::

    privacyidea-token-janitor find --serial OATH0004C934 --action delete

The token with the serial ``OAUTH0004C934`` will be deleted.

export
......

With **export** single or multiple tokens can be exported as csv or pskc.

Export is only possible with HOTP and TOTP token.

Example::

    privacyidea-token-janitor find --serial OATH0004C934 --action export > OAUTH0004C934.xml

The token with the serial ``OAUTH0004C934`` will be exported and saved in an xml file.

Note that you need your encryption key for re-import.

listuser
........

With **listuser** the various tokens are listed in a summarized view.

Example::

    privacyidea-token-janitor find --action listuser

lists all tokens in a summarized view.

sum
___

**Sum** and **listuser** together

For all found tokens the token janitor aggregate's the users and lists how many tokens this user has.

A user without any assigned token is not listed here!

Example::

    privacyidea-token-janitor find --sum --action listuser

tokenrealms
...........

**Tokenrealms** can be used to assign tokens to different realms.

To do this, the ``tokenrealms`` function is also required.

Please note that without a previous selection of a certain token, all found tokens will be assigned to the realm.

Example::

    privacyidea-token-janitor find --serial OATH0005B88E --action tokenrealms --tokenrealms defrealm

Setting realms of token ``OATH0005B88E`` to ``defrealm``.

You can also assign a list of realms by comma separating.

Example::

    privacyidea-token-janitor find --serial OATH0005B88E --action tokenrealms --tokenrealms defrealm,realmA,realmB

Set
***

With the tokenjanitor it is possible to set new tokeninfo-values, tokeninfo-keys and descriptions.

It is important to note that this is only possible with a previously marked token.

set-tokeninfo-key and set-tokeninfo-value
.........................................

Set a new tokeninfo-key and a new tokeninfo-value.

This will only work together it is not possible to set a tokeninfo-key or a tokenifno-value individually.

Example::

    privacyidea-token-janitor find --serial OATH0004C934 --action mark --set-tokeninfo-key import_time --set-tokeninfo-value $(date --iso-8601=minutes)

Mark the token with the serial ``OATH0004C934`` and set a new tokeninfo-key ``import_time`` and a
new tokeninfo-value ``$(date --iso-8601=minutes)``.

set description
...............

Set a new description.

It is important to note that this is only possible with a previously marked token.

Example::

    privacyidea-token-janitor find --serial OATH0004C934 --action mark --set-description L4

Mark the token with the serial ``OATH0004C934`` and set the description ``example``.

.. _get_unused_tokens:

privacyidea-get-unused-tokens
-----------------------------

The script ``privacyidea-get-unused-tokens`` allows you to search for tokens,
which were not used for authentication for a while. These tokens can be
listed, disabled, marked or deleted.

You can specify how old the last authentication of such a token has to be.
You can use the tags *h* (hours), *d* (day) and *y* (year).
Specifying *180d* will find tokens, that were not used for authentication for
the last 180 days.

The command::

    privacyidea-get-unused-tokens disable 180d

will disable those tokens.

This script can be well used with the :ref:`scripthandler`.
