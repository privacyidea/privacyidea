.. _tools:

Tools
=====

.. index:: tools

privacyIDEA comes with a list of command line tools, which also help to
automate tasks. The tools are automatically available after an installation in
the virtual environment.

.. _token_janitor:

privacyidea-token-janitor
-------------------------

.. index:: orphaned tokens

Starting with version 2.19 privacyIDEA comes with a token janitor script.
This script can find orphaned tokens, unused tokens or tokens of specific
type, description or token info.

It can unassign, delete or disable those tokens, it can set additional
tokeninfo or descriptions and perform other tasks on the found tokens.

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
You can find tokens by providing filter parameters. Note, that you can combine as many filter
parameters as you want to. This way you can reduce the set of found tokens.
Several filter parameters allow to search with regular expressions.

Actions will then be performed only on this reduced set.

These are important filter parameters:

Orphaned
********

Searches for tokens, that are orphaned. Orphaned tokens are assigned to a user. But the
user does not exist in the user store anymore. This can happen e.g. if an LDAP user gets
deleted in the LDAP directory.

Example::

    privacyidea-token-janitor find --orphaned 1

This returns all orphaned tokens for later processing.

Active
******

Searches for tokens that are either active or inactive, this means enabled or disabled.

Example::

    privacyidea-token-janitor find --active False

This returns all disabled tokens. May you later want to delete these disabled tokens.

Assigned
********

Searches for tokens that are either assigned to a user or unassigned.

Example::

    privacyidea-token-janitor find --assigned False

This returns all tokens, that are not assigned to a user. You could combine this with other filters
like the ``tokenkind`` to find out how many hardware tokens are not assigned and still available for assignment.


Last_auth
*********

Searches for all tokens, where the last authentication happens longer ago than the given value:

Example::

    privacyidea-token-janitor find --last_auth 10d

This will find all tokens, that did not authenticate within the last 10 days. You can also use "h" and "y"
to specify hours and years.

Since the last_auth is an entry in the ``tokeninfo`` table you could also search like this::

   privacyidea-token-janitor find --tokeninfo-key last_auth --tokeninfo-value-after '2021-06-01 18:00:00+0200'


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

By searching for regular expressions, it is e.g. possible to find Yubikeys,
which might be a tokentype "HOTP", but where the serial starts with UBOM.

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

Match for a certain token attribute from the database table ``token``.

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

    privacyidea-token-janitor find --tokenattribute failcount --tokenattribute-value-less-than 10

Search for all tokens with the tokenattribute-key ``failcount`` and the associated tokenattribute-value below ``10``.
This way you can find tokens, where the fail counter is less than 10 and thus the tokens are not blocked.

tokenattribute-value-greater-than INTEGER
.........................................

Match if the value of the token attribute is greater than the given value.

Example::

    privacyidea-token-janitor find --tokenattribute failcount --tokenattribute-value-greater-than 10

Search for all tokens with the tokenattribute-key ``failcount`` and the associated tokenattribute-value greater than ``10``.
This way you can find tokens, where the fail counter is greater than 10 and thus the tokens are blocked.

Tokeninfo-key
*************

This matches on values for tokeninfo, which is actually the database table `tokeninfo`.

There are different ways of filtering here.

has-tokeninfo-key
.................

Filters for tokens that have given the specified tokeninfo-key no matter which value the key has.

Example::

    privacyidea-token-janitor find --has-tokeninfo-key import_time

Searches for all tokens that have a tokeninfo-key ``import_time`` set.

**Note, that it is not important, what value the "import_time" actually has!**

has-not-tokeninfo-key
.....................

Filters for tokens that have not set the specified tokeninfo-key.

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

**Mark** makes it possible to mark the found tokens in order to carry out further actions with them later.

The tokens are marked by setting a tokeninfo-key and an associated tokininfo-value.

Example::

    privacyidea-token-janitor find --serial OATH0004C934 --action mark --set-tokeninfo-key unused --set-tokeninfo-value True

A new tokeninfo-key and the associated tokeninfo-value would be added for the token ``OATH0004C934``
and are now marked for later processing. If the token already containd this tokeninf-key, the value
would be changed.


disable
.......

With **disable** the found tokens can be disabled.


Example::

    privacyidea-token-janitor find --serial OATH0004C934 --action disable

The token with the serial ``OATH0004C934`` will be disabled.

delete
......

With **delete** the found tokens can be deleted.


Example::

    privacyidea-token-janitor find --serial OATH0004C934 --action delete

The token with the serial ``OATH0004C934`` will be deleted.

export
......

With **export** the found tokens can be exported as csv, yaml or pskc.

CSV will only export HOTP and TOTP tokens.
The PSKC file exports HOTP, TOTP and password tokens (PW).
YAML in theory can export all token types and all tokeninfo.

Example::

    privacyidea-token-janitor find --serial OATH0004C934 --action export > OATH0004C934.xml

The token with the serial ``OATH0004C934`` will be exported and saved in an xml file.

.. note:: With PSCK you need your encryption key for re-import.

.. note:: You can also use YAML export or re-encrypting data. See :ref:`faq_reencryption`.

listuser
........

With **listuser** the found tokens are listed in a summarized view.

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

Set a new tokeninfo-key and a new tokeninfo-value or update the tokeninfo-value of an existing key.

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

.. _pi-tokenjanitor:

The pi-tokenjanitor Script
--------------------------
.. index:: pi-token-janitor
.. versionadded:: 3.11

Starting with version 3.11 privacyIDEA comes with an improved version of the :ref:`token_janitor` script.
The new script is called **pi-token-janitor**. The script can be used for three different tasks: to find
tokens and perform actions on them, to import tokens from a PSKC file or to update the token data.

Find
~~~~

With the **find** command you can search for tokens in the database.
You can use several options to filter the tokens.

``--chunksize``
    The number of tokens to fetch in one database request (default: 1000).

``--tokenattribute``
    Find tokens with specific token attributes. The most common used token attributes
    are  ``serial``, ``description``, ``tokentype``, ``active``, ``locked``,
    ``failcount`` and ``rollout_state``.
    This option can be used multiple times.

    Example::

        pi-tokenjanitor find --tokenattribute 'serial=HOTP123456'

    Search for all tokens with the serial ``HOTP123456``.

    .. note:: You can also use regular expressions in the tokenattribute filter.

``--tokeninfo``
    Find tokens with specific tokeninfo values.
    This option can be used multiple times.

    Example::

        pi-tokenjanitor find --tokeninfo 'tokenkind=software'

    Search for all tokens with the tokeninfo-key ``tokenkind`` and the value ''software''.

    .. note:: You can also use regular expressions in the tokeninfo filter.

``--tokencontainer``
    Find tokens in a specific token container.
    This option can be used multiple times.

    Example::

        pi-tokenjanitor find --tokencontainer 'serial=SMPH00009272'

    Search for all tokens in the token container with the serial ``SMPH00009272``.

    .. note:: You can also use regular expressions in the tokencontainer filter.

``--has-tokeninfo-key/--has-not-tokeninfo-key``
    Find tokens with a specific tokeninfo-key set or not set.

    Example::

        pi-tokenjanitor find --has-tokeninfo-key 'import_time'

    Search for all tokens which have the tokeninfo-key ``import_time``.

``--tokenower``
    Find tokens from a specific token owner(user). You can use user attributes
    like the username, the realm or the resolver.
    This option can be used multiple times.

    Example::

        pi-tokenjanitor find --tokenowner 'uid=642cf598-d9cf-1037-8083-a1df7d38c897'

    .. note:: You can also use regular expressions in the tokenowner filter.

``--assigned``
    Find tokens that are assigned to a user.

    Example::

        pi-tokenjanitor find --assigned true

    or::

        pi-tokenjanitor find --assigned 0

``--active``
    Find tokens that are either active/enabled or inactive/disabled.

    Example::

        pi-tokenjanitor find --active True

    or::

        pi-tokenjanitor find --active 0

``--orphaned``
    Find tokens, that are orphaned. Orphaned tokens are assigned to a user but the user does not
    exist in the user store anymore. This can happen e.g. if an LDAP user gets deleted in the LDAP directory.

    Example::

        pi-tokenjanitor find --orphaned 1

``--orphaned-on-error``
    When searching for orphaned tokens, mark the token as orphaned if the user
    can not be found due to a resolver error.

``--range-of-serials``
    Find tokens with serials in a specific range.

    Example::

        pi-tokenjanitor find --range-of-serials 'HOTP00000000-HOTP99999999'

    .. note:: This matches the string as ASCII values. So consider case sensitivity.

list
****
List all found tokens.

Example::

    pi-tokenjanitor find --tokenattribute 'serial=OATH0004C934' list

.. note:: This command is the default command if no action is specified.

``-u``, ``--show-user-attributes``
    You can use this option to extend the output with user attributes.
    This option can be used multiple times.

    Example::

        pi-tokenjanitor find --tokenattribute 'serial=OATH0004C934' list -u email


``-t``, ``--show-token-attributes``
    You can use this option to extend the output with token attributes.
    This option can be used multiple times.

    Example::

        pi-tokenjanitor find --tokenattribute 'serial=OATH0004C934' list -t tokenkind

``--sum``
    You can use this option to group the token output by user.

    Example::

        pi-tokenjanitor find --tokenattribute 'serial=OATH0004C934' list --sum

    .. note:: The option ``--sum`` only works with the option ``--show-user-attributes``.

export
******
Exports all tokens found.

Example::

    pi-tokenjanitor find --tokenattribute 'serial=OATH0004C934' export

``--format``
    The export format of the token list. The format can be 'pi', 'csv', 'yaml' or 'pskc'.

    Example::

        pi-tokenjanitor find --tokenattribute 'serial=OATH0004C934' export --format yaml

``--b32``
    Export the token secret as base32 instead of hex. Can be used with format CSV and YAML

    Example::

        pi-tokenjanitor find --tokenattribute 'serial=OATH0004C934' export --format CSV --b32

``--file``
    The file to export the tokens to. If not specified, the output will be printed to stdout.

    Example::

        pi-tokenjanitor find --tokenattribute 'serial=OATH0004C934' export --file /path/to/export

``--user/--no-user``
    If set, the user will be exported as well. If not set, only the tokens will be exported. Default: ``--user``.

    Example::

        pi-tokenjanitor find --tokenattribute 'serial=OATH0004C934' export --file /path/to/export --user




set_tokenrealms
***************
Sets a tokenrealm for the found tokens.

``--tokenrealm``
    The tokenrealm to set. Can be given multiple times.

    Example::

        pi-tokenjanitor find --tokenattribute 'serial=OATH0004C934' set-tokenrealms --tokenrealm defrealm

disable
*******
Disable the found tokens.

delete
******
Delete the found tokens.

unassign
********
Unassign the found tokens.

set_description
***************
Sets a description for the found tokens.

``--description``
    The description to set.

Example::

    pi-tokenjanitor find --tokenattribute 'serial=OATH0004C934' set_description --description 'example description'

set_tokeninfo
**************
Set a tokeninfo for the found tokens.

``--tokeninfo``
    The tokeninfo to set.

    Example::

        pi-tokenjanitor find --tokenattribute 'serial=OATH0004C934' set_tokeninfo --tokeninfo 'foo=bar'

remove_tokeninfo
****************
Remove a tokeninfo from the found tokens.

``--tokeninfo_key``
    This argument must be set to specify witch tokeninfo should be removed.

    Example::

        pi-tokenjanitor find --tokenattribute 'serial=OATH0004C934' remove_tokeninfo --tokeninfo_key 'import_time'

list_containers
***************
List all token containers of the found tokens.

Example::

    pi-tokenjanitor find --tokenattribute 'serial=OATH0004C934' list_containers

add_to_container
****************
Add the found tokens to a token container.

``--container_serial``
    The serial of the token container to add the tokens to.

    Example::

        pi-tokenjanitor find --tokenattribute 'serial=OATH0004C934' add_to_container 'SMPH00009272'

remove_from_container
*********************
Remove the found tokens from their token container.

    Example::

        pi-tokenjanitor find --tokenattribute 'serial=OATH0004C934' remove_from_container

Import
~~~~~~
This command can be used to import token data from a file.

pskc
****
Imports token data from a PSKC file.

Example::

    pi-tokenjanitor import pskc /path/to/pskcfile.xml

``--preshared_key``
    Specify the preshared key for the PSKC file.

    Example::

        pi-tokenjanitor import pskc /path/to/pskcfile.xml --preshared_key 'mykey'

``--validate_mac``
    With this option you can specify how the file should be validated:

    - ``'no_check'``:  every token is parsed, ignoring HMAC
    - ``'check_fail_soft'``:  skip tokens with invalid HMAC
    - ``'check_fail_hard'``: only import tokens if all HMAC are valid.

privacyidea
***********
Imports token data from a privacyIDEA created with pi-tokenjanitor export_for_privacyidea.

``file``
    The path to the privacyIDEA file to import.

    Example::

        pi-tokenjanitor import privacyidea /path/to/privacyidea.txt

``--key``
    Specify the encryption key for the privacyIDEA file.

    Example::

        pi-tokenjanitor import privacyidea /path/to/privacyidea.txt --key myencryptionkey

``--user/--no-user``
    If set, the user will be imported as well. If not set, only the tokens will be imported. Default: ``--no-user``.

    Example::

        pi-tokenjanitor import privacyidea /path/to/privacyidea.txt --key myencryptionkey --user

Update
~~~~~~
This command can be used to update already existing token data with a given YAML file.

Example::

    pi-tokenjanitor update /path/to/yamlfile.yaml


Container
~~~~~~~~~~~~~
With the **container** command you can search for containers in the database.
You can use several options to filter the containers.

``--serial``
    Find containers with a specific serial.

    Example::

        pi-tokenjanitor container --serial 'SMPH00009272'

``--type``
    Find containers with a specific type.

    Example::

        pi-tokenjanitor container --type 'smartphone'

``--token-serial``
    Find containers that contain a token with a specific serial.

    Example::

        pi-tokenjanitor container --token-serial 'HOTP123456'

``--realm``
    Find containers that belong to a specific realm.

    Example::

        pi-tokenjanitor container --realm 'defrealm'

``--template``
    Find containers that are based on a specific template.

    Example::

        pi-tokenjanitor container --template 'default_smartphone'

``--description``
    Find containers with a specific description.

    Example::

        pi-tokenjanitor container --description 'My smartphone container'

``--assigned``
    Find containers that are either assigned to a user or unassigned.

    Example::

        pi-tokenjanitor container --assigned true

``--resolver``
    Find containers that belong to a specific resolver.

    Example::

        pi-tokenjanitor container --resolver 'my_ldap_resolver'

``--info``
    Find containers with specific info key-value pairs. Give the key and value in the format key=value.
    This option can be used multiple times.

    Example::

        pi-tokenjanitor container --info 'os=android'

``--last-auth-delta``
    Find containers where the last authentication of any token in the container happened longer ago than the given value.
    You can use the tags *h* (hours), *d* (day) and *y* (year).

    Example::

        pi-tokenjanitor container --last-auth-delta '90d'

``--last-sync-delta``
    Find containers where the last sync of any token in the container happened longer ago than the given value.
    You can use the tags *h* (hours), *d* (day) and *y* (year).

    Example::

        pi-tokenjanitor container --last-sync-delta '90d'

``--chunksize``
    The number of containers to fetch in one database request (default: 1000).
    This is useful if you have a lot of containers in your database.

    Example::

        pi-tokenjanitor container --chunksize 500

``--orphaned``
    Find containers that are orphaned. Orphaned containers are assigned to a user, but the user does not
    exist in the user store anymore. This can happen, for example, if a user is deleted from an LDAP directory.

    Example::

        pi-tokenjanitor container --orphaned True

    This returns all orphaned containers for later processing.

list
****
List all found containers.
Example::

    pi-tokenjanitor container --type 'smartphone' list

``--key``
    Can be used to select the displayed information about the container.
    This option can be used multiple times.
    The default: ``serial``, ``type``, ``description``, ``realm``, ``user``.
    Possible keys: ``type``, ``serial``, ``description``, ``last_authentication``, ``last_synchronization``,
    ``states``, ``info``, ``internal_info_keys``, ``realms``, ``users``, ``tokens``

    Example::

        pi-tokenjanitor container --type 'smartphone' list --key user --key last_synchronization

delete
******
Delete the found containers.

Example::

    pi-tokenjanitor container --type 'smartphone' delete

update_info
***********
Updates the info for all found containers. A non-existing key is added and the value for an existing key is
overwritten. All other entries remain unchanged.

``key``
    The info key to set.

``value``
    The info value to set.

Example::

    pi-tokenjanitor container --type 'smartphone' update_info 'os' 'android'

delete_info
***********
Delete the info key from all found containers.

``key``
    The info key to delete.

Example::

    pi-tokenjanitor container --type 'smartphone' delete_info 'os'

set_description
***************
Sets a description for all found containers.

``description``
    The description to set.

Example::

    pi-tokenjanitor container --type 'smartphone' set_description 'example description'

set_realm
*********
Sets a list of realms for all found containers.

``realm``
    A comma separated list of realms to set.

``--add``
    If this option is set, the realm will be added to the existing realms.
    If not set, the existing realms will be overwritten.

Example::

    pi-tokenjanitor container --type 'smartphone' set_realm 'defrealm' --add

