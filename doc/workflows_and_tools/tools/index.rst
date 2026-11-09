.. _tools:

Tools
=====

.. index:: tools

privacyIDEA comes with command line tools for administration and automation.
They are installed with privacyIDEA into the ``bin`` directory of its virtual
environment, ``/opt/privacyidea/bin`` with the Ubuntu packages. Most of them
work directly on the database and read the configuration file
``/etc/privacyidea/pi.cfg``, or the file given in ``PRIVACYIDEA_CONFIGFILE``, so
run them as the user privacyIDEA runs as.

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Tool
     - Purpose
   * - :ref:`pi-manage <pimanage>`
     - Set up an installation, manage administrators, backups, database
       migrations and the configuration, clean up tables
   * - :ref:`pi-tokenjanitor <pi-tokenjanitor>`
     - Find tokens and containers and act on them, import and export tokens,
       clean up orphaned user data
   * - ``privacyidea-token-janitor``
     - Deprecated, use ``pi-tokenjanitor`` instead, see
       :ref:`pi-tokenjanitor_mapping`
   * - :ref:`privacyidea-get-unused-tokens <get_unused_tokens>`
     - Find tokens that have not been used for a while
   * - :ref:`privacyidea-cron <privacyidea_cron>`
     - Run the periodic tasks, called from the system crontab
   * - :ref:`privacyidea-expired-users <privacyidea_expired_users>`
     - Unassign or delete the tokens of expired LDAP accounts
   * - :ref:`privacyidea-usercache-cleanup <privacyidea_usercache_cleanup>`
     - Delete expired user cache entries
   * - :ref:`privacyidea-get-serial <privacyidea_get_serial>`
     - Find the token that generated an OTP value
   * - :ref:`privacyidea-standalone <privacyidea_standalone>`
     - Check user names and passwords against a local instance, e.g. from
       scripts
   * - :ref:`privacyidea-diag <privacyidea_diag>`
     - Collect diagnostic data for support
   * - ``privacyidea-pip-update``, ``privacyidea-schema-upgrade``
     - Upgrade an installation from PyPI, see :ref:`upgrade`
   * - ``privacyidea-authorizedkeys``
     - Fetch the SSH keys of a user for the SSH daemon, see :ref:`application_ssh`
   * - ``privacyidea-create-pwidresolver-user``
     - Create an entry for a :ref:`flatfile_resolver`

The jobs that have to run regularly are described in :ref:`cleanup_jobs`.

.. toctree::
   :hidden:

   servertools

.. _get_unused_tokens:

privacyidea-get-unused-tokens
-----------------------------

.. index:: unused tokens

``privacyidea-get-unused-tokens`` finds the tokens whose last successful authentication is
longer ago than a given age, and lists, disables, deletes or marks them. It checks all tokens,
of every type, assigned or not.

The age is a number followed by one of the units ``s`` (seconds), ``m`` (minutes), ``h``
(hours), ``d`` (days) or ``y`` (years of 365 days). ``180d`` finds the tokens that did not
authenticate within the last 180 days.

The time of the last successful authentication is read from the tokeninfo ``last_auth``. A token
that has never authenticated successfully has no ``last_auth`` and is **never** found. A token
whose ``last_auth`` can not be read as a date, however, counts as unused and is found, so
``delete`` deletes it.

If the age is not valid, e.g. ``180`` without a unit, the script prints an error and does
nothing, but still exits with status ``0``. In a cron job, check the output.

The script has four commands, each takes the age as its argument:

``list AGE``
    Lists the found tokens with the time of their last authentication.
``disable AGE``
    Disables the found tokens.
``delete AGE``
    Deletes the found tokens, without confirmation.
``mark AGE``
    Sets a description with ``-d``/``--description``, a tokeninfo with
    ``-t``/``--tokeninfo key=value`` or both on the found tokens. The value of the tokeninfo is
    everything after the first ``=``. A tokeninfo that the token type maintains itself, e.g.
    ``last_auth`` or ``tokenkind``, is skipped with a message.

Examples::

    privacyidea-get-unused-tokens list 180d
    privacyidea-get-unused-tokens disable 180d
    privacyidea-get-unused-tokens mark 180d --tokeninfo unused=True
    privacyidea-get-unused-tokens delete 1y

Run ``list`` with the same age before ``disable`` or ``delete`` to see which tokens are affected.

To run the script regularly, call it from cron. The :ref:`scripthandler` can not call it
directly: it runs a script from its script directory and can not pass the command and the age.
Put a wrapper script into the script directory, which calls e.g.
``privacyidea-get-unused-tokens disable 180d`` and ignores the arguments the script handler
passes.

.. _pi-tokenjanitor:

The pi-tokenjanitor Script
--------------------------

.. index:: pi-tokenjanitor
.. versionadded:: 3.11

``pi-tokenjanitor`` finds tokens, token containers and orphaned user data in the database and acts
on them. It replaces the older script ``privacyidea-token-janitor``, which is still installed but
deprecated. The section :ref:`pi-tokenjanitor_mapping` maps the options of the older script to
this one.

The script reads the privacyIDEA configuration in the same way as :ref:`pimanage`. It has these
commands:

``find``
    Find tokens and list, export or change them, see :ref:`pi-tokenjanitor_find`.
``container``
    Find token containers and list or change them, see :ref:`pi-tokenjanitor_container`.
``import``
    Import tokens from a PSKC file or from a ``pi-tokenjanitor`` export, see
    :ref:`pi-tokenjanitor_import`.
``update``
    Update existing tokens from a YAML export, see :ref:`pi-tokenjanitor_update`.
``deprecated``
    List or delete tokens whose token type has been removed from privacyIDEA, see
    :ref:`pi-tokenjanitor_deprecated`.
``user-settings``, ``custom-attributes``, ``internal-attributes``
    Find and delete the data of users that no longer exist in the user store, see
    :ref:`pi-tokenjanitor_orphans`.

``pi-tokenjanitor --help`` lists the commands, ``pi-tokenjanitor <command> --help`` and
``pi-tokenjanitor <command> <subcommand> --help`` list their options.

.. _pi-tokenjanitor_usage:

Options and subcommands
~~~~~~~~~~~~~~~~~~~~~~~

``find``, ``container``, ``import``, ``deprecated`` and the three cleanup commands have
subcommands. For ``find`` and ``container`` the options of the command select the objects and the
subcommand says what to do with them. The options of a command go **before** the subcommand, the
options of the subcommand **after** it::

    pi-tokenjanitor find --tokenattribute 'tokentype=^totp$' export --format csv

Here ``--tokenattribute`` belongs to ``find`` and ``--format`` to ``export``. In the wrong place
an option fails with ``No such option``. ``find``, ``container`` and the three cleanup commands
list what they found if no subcommand is given.

.. warning:: The subcommands of ``find`` and ``container`` act on **every** object the options
   select, without confirmation and without a dry run. Without any filter option they act on all
   tokens or containers: ``pi-tokenjanitor find delete`` deletes every token in the database.
   Always run the same command with ``list`` first and check the result.

.. _pi-tokenjanitor_find:

Find
~~~~

``pi-tokenjanitor find`` selects tokens with the options below and passes them to a subcommand.
A token is selected only if it matches all given options. An option that can be given multiple
times has to match every time. The filters with a ``<key><operator><value>`` argument follow the
:ref:`pi-tokenjanitor_matching`.

``--tokenattribute``
    Match a column of the token table, e.g. ``serial``, ``description``, ``tokentype``,
    ``active``, ``locked``, ``revoked``, ``failcount``, ``maxfail``, ``count`` or
    ``rollout_state``. Can be given multiple times.

    Example::

        pi-tokenjanitor find --tokenattribute 'serial=^HOTP123456$'

    Finds the token with the serial ``HOTP123456``. Without ``^`` and ``$`` it would also find
    e.g. ``HOTP1234567`` and ``XHOTP123456``.

``--tokeninfo``
    Match a tokeninfo entry. A token without this tokeninfo key does not match. Can be given
    multiple times.

    Example::

        pi-tokenjanitor find --tokeninfo 'tokenkind=^software$'

    Finds the tokens whose tokeninfo ``tokenkind`` is ``software``.

``--has-tokeninfo-key``, ``--has-not-tokeninfo-key``
    Find the tokens that have, or do not have, a tokeninfo entry with the given key, whatever its
    value. These are two separate options, each takes a key.

    Example::

        pi-tokenjanitor find --has-tokeninfo-key import_time

``--tokenowner``
    Match an attribute of the token owner. ``uid``, ``login``, ``resolver`` and ``realm`` are taken
    from the user object, every other attribute, e.g. ``username``, ``email`` or ``givenname``,
    from the user store. Unassigned tokens never match, and neither do tokens whose owner can not
    be looked up because of a resolver error. Can be given multiple times.

    Example::

        pi-tokenjanitor find --tokenowner 'uid=^642cf598-d9cf-1037-8083-a1df7d38c897$'

``--tokencontainer``
    Match an attribute of the container the token is in, e.g. ``serial``, ``type`` or
    ``description``. Tokens that are in no container never match. Can be given multiple times.

    Example::

        pi-tokenjanitor find --tokencontainer 'serial=^SMPH00009272$'

``--assigned``
    ``true`` finds the tokens that are assigned to a user, ``false`` the unassigned tokens. Like
    ``--active`` and ``--orphaned``, the option also accepts ``1`` and ``0``, ``yes`` and ``no`` or
    ``on`` and ``off``, in upper or lower case. Any other value is rejected with an error.

    Example::

        pi-tokenjanitor find --assigned false

``--active``
    ``true`` finds the enabled tokens, ``false`` the disabled tokens.

``--orphaned``
    ``true`` finds the orphaned tokens, ``false`` the tokens that are not orphaned. An orphaned
    token is assigned to a user who no longer exists in the user store, e.g. because the user was
    deleted in the LDAP directory.

    Example::

        pi-tokenjanitor find --orphaned true

``--orphaned-on-error``
    A flag for ``--orphaned``: a token counts as orphaned if its owner can not be looked up
    because of a resolver error, e.g. because the LDAP server can not be reached. Without the flag
    such a token is not orphaned. Together with ``delete`` the flag deletes the tokens of all users
    of a user store that is down.

``--range-of-serial``
    Find the tokens whose serial lies in the given range, including both limits, given as
    ``<first>-<last>``. The serials are compared as strings, character by character: ``HOTP9``
    lies after ``HOTP10000000``, and lower case letters lie after upper case letters. A serial
    that contains ``-`` can not be used as a limit, and the range always needs both limits.

    Example::

        pi-tokenjanitor find --range-of-serial 'HOTP00000000-HOTP99999999'

``--chunksize``
    The number of tokens read from the database in one query (default: 1000). It limits the
    memory use, all selected tokens are processed.

.. _pi-tokenjanitor_matching:

Matching rules
**************

``--tokenattribute``, ``--tokeninfo``, ``--tokenowner`` and ``--tokencontainer`` take a filter of
the form ``<key><operator><value>``. Quote the filter on the shell, otherwise ``<``, ``>`` and
``!`` are interpreted by the shell.

``=``
    The value is a regular expression that has to occur **somewhere** in the stored value.
    ``serial=OATH`` matches every serial that contains ``OATH``, ``serial=^OATH0004C934$`` only
    this one serial. The match is case sensitive, start the expression with ``(?i)`` to ignore
    case.
``!``
    The opposite of ``=``: the regular expression does not occur in the stored value.
``<``, ``>``
    With an integer the stored value is compared as a number, e.g. ``failcount>3``. Except for
    ``--tokenattribute``, the value can also be a point in time:

    * a date, e.g. ``--tokeninfo 'last_auth<2025-01-01'`` finds the tokens whose last successful
      authentication was before 2025. A date without a time zone is taken as local time.
    * a time relative to now, given as a signed time span with the unit ``s``, ``m``, ``h``,
      ``d`` or ``y`` (365 days): ``--tokeninfo 'last_auth<-180d'`` finds the tokens whose last
      successful authentication was more than 180 days ago, ``--tokeninfo 'last_auth>-180d'``
      those that authenticated within the last 180 days.

    A stored value that is not a number or a date does not match.

The integer and boolean columns of the token table, e.g. ``failcount``, ``active`` or
``locked``, are always compared as integers: use ``active=1`` or ``locked=0``, not
``active=True``. ``<`` and ``>`` in ``--tokenattribute`` only accept integers.

The key and the value can not contain ``=``, ``!``, ``<`` or ``>``. A token for which the key does
not exist, e.g. an unset tokeninfo key or a user attribute the user store does not return, never
matches, not even with ``!``.

list
****

Lists the selected tokens, one line per token with the serial, the token type, the realms and all
tokeninfo entries. ``list`` is the default if no subcommand is given.

Example::

    pi-tokenjanitor find --tokenattribute 'serial=^OATH0004C934$' list

``-t``, ``--show-token-attribute``
    Also show this token attribute or tokeninfo entry. With this option only the requested
    tokeninfo entries are shown instead of all of them. Can be given multiple times.

    Example::

        pi-tokenjanitor find --tokenattribute 'serial=^OATH0004C934$' list -t tokenkind -t failcount

``-u``, ``--show-user-attribute``
    Also show this attribute of the token owner: ``uid``, ``resolver``, ``realm`` or an attribute
    the user store returns, e.g. ``username`` or ``email``. Can be given multiple times.

    Example::

        pi-tokenjanitor find --tokenattribute 'serial=^OATH0004C934$' list -u username -u email

``-s``, ``--summarize``
    Instead of the tokens, list one line per token owner with the number of selected tokens of
    this owner: username, given name, surname, user ID, resolver, realm, the attributes requested
    with ``-u`` and the number of tokens. The unassigned tokens are counted in one line starting
    with ``N/A``.

    Example::

        pi-tokenjanitor find --assigned true list --summarize -u email

``--format``
    ``text`` (default) writes one line per token, or per owner with ``--summarize``, meant to be
    read. ``json`` writes one JSON object per line, meant for scripts: per token its ``serial``,
    ``tokentype``, the list of ``realms``, the tokeninfo in ``info`` and, with ``-u``, the owner
    in ``user``; with ``--summarize`` per owner ``{"user": {...}, "tokens": <number>}``, where
    ``user`` is ``null`` for the unassigned tokens.

    Example::

        pi-tokenjanitor find --tokeninfo 'last_auth<-180d' list --format json

.. _pi-tokenjanitor_export:

export
******

Exports the selected tokens. The export contains the secrets of the tokens: keep it safe and
delete it when it is no longer needed.

``--format``
    The format of the export, upper or lower case:

    ``pi`` (default)
        The tokens with their tokeninfo and, with ``--user``, their owner. The export is encrypted.
        The key to decrypt it is printed to stderr. On a terminal the script then asks whether to
        save the key to a file as well; without a terminal, e.g. in a cron job, it does not ask. Tokens that can not be exported, e.g. mOTP, remote, RADIUS, Yubico and VASCO
        tokens, are listed as failed. Import the export with
        :ref:`import privacyidea <pi-tokenjanitor_import_privacyidea>`.
    ``csv``
        Only HOTP and TOTP tokens, one line per token with the owner (``login@realm`` or ``n/a``),
        the serial, the OTP key, the token type, the OTP length and, for TOTP tokens, the time
        step. The OTP key is **not** encrypted.
    ``yaml``
        The tokens with their tokeninfo and the owner (``login@realm`` or ``n/a``). The OTP key is
        **not** encrypted. This is the input for :ref:`update <pi-tokenjanitor_update>`.
    ``pskc``
        Only HOTP, TOTP and password (PW) tokens. The OTP keys are encrypted with a new AES key,
        which is printed to stderr. Import the file with
        :ref:`import pskc <pi-tokenjanitor_import_pskc>` and this key.

``--file``
    Write the export to this file. Without ``--file`` the export is written to stdout, and all
    messages and keys go to stderr, so the output can be redirected to a file. For the ``pi``
    format with ``--file`` the script also prints the command to import the file.

``--b32``
    For ``csv`` and ``yaml``, write the OTP key base32 encoded instead of hex. Do not use it for a
    YAML export you want to pass to ``update``, which expects the OTP key in hex.

``--user``, ``--no-user``
    Include the token owner in the export (default: ``--user``). With ``--no-user`` the owner of
    the ``csv`` and ``yaml`` formats is ``n/a`` and the ``pi`` format contains no owner.

Examples::

    pi-tokenjanitor find --tokenattribute 'tokentype=^totp$' export --format csv --b32 --file totp.csv
    pi-tokenjanitor find --assigned true export --file tokens.pi

disable
*******

Disables the selected tokens.

Example::

    pi-tokenjanitor find --orphaned true disable

enable
******

Enables the selected tokens.

delete
******

Deletes the selected tokens from the database, together with their tokeninfo and challenges. A
deleted token can only be restored from an export.

Example::

    pi-tokenjanitor find --orphaned true list
    pi-tokenjanitor find --orphaned true delete

A token can look orphaned while the user store is not working correctly. If you do not want to
delete orphaned tokens in one step, mark them first::

    pi-tokenjanitor find --orphaned true set_tokeninfo --tokeninfo "orphaned_since=$(date --iso-8601=minutes)"

A day later, delete the tokens that are still orphaned and have been marked::

    pi-tokenjanitor find --orphaned true --has-tokeninfo-key orphaned_since delete

unassign
********

Removes the owner of the selected tokens and resets their PIN and fail counter.

set_tokenrealms
***************

Sets the realms of the selected tokens. The given realms **replace** the realms of the tokens, only
the realm of the token owner is always kept. A realm that does not exist is skipped.

``--tokenrealm``
    A realm to set. Required, can be given multiple times.

Example::

    pi-tokenjanitor find --tokenattribute 'serial=^OATH0004C934$' set_tokenrealms --tokenrealm defrealm --tokenrealm realmA

set_description
***************

Sets the description of the selected tokens.

``--description``
    The description to set. Required.

Example::

    pi-tokenjanitor find --tokenattribute 'serial=^OATH0004C934$' set_description --description 'example description'

set_tokeninfo
*************

Adds a tokeninfo entry to the selected tokens or overwrites an existing entry with the same key.

``--tokeninfo``
    The entry to set, given as ``<key>=<value>``. Required. The key may only contain letters,
    digits and ``_``. The value is everything after the first ``=``, without the spaces around
    it, and may contain any character, e.g. ``'marked=to delete 2026-10-01'``.

Only free-form entries can be set. An entry that the token type maintains itself is skipped with a
message. Some of these entries can be changed with the ``/token/set`` endpoint, e.g.
``validity_period_end``, ``count_auth_max`` or the phone number of an SMS token; others, like the
public key of a passkey, are only written at enrollment.

Example::

    pi-tokenjanitor find --tokenattribute 'serial=^OATH0004C934$' set_tokeninfo --tokeninfo 'note=spare_key'

remove_tokeninfo
****************

Removes a tokeninfo entry from the selected tokens.

``--tokeninfo_key``
    The key of the entry to remove. Required.

An entry that the token type maintains itself, e.g. the public key of a passkey, is skipped with a
message, because the token needs it. The exceptions are the offline refill entries,
``refilltoken`` of HOTP and TOTP tokens and ``refilltoken_<computer name>`` of passkeys and
WebAuthn tokens: removing them stops the offline refill.

Example::

    pi-tokenjanitor find --tokenattribute 'serial=^OATH0004C934$' remove_tokeninfo --tokeninfo_key import_time

list_containers
***************

Lists the container of each selected token, or that the token is in no container.

``-k``, ``--key``
    The container information to show, see :ref:`container list <pi-tokenjanitor_container_list>`
    for the keys. Can be given multiple times. Default: ``type``, ``tokens``, ``users``,
    ``realms`` and ``description``.

Example::

    pi-tokenjanitor find --tokenattribute 'serial=^OATH0004C934$' list_containers

add_to_container
****************

Adds the selected tokens to the container with the serial ``CONTAINER_SERIAL``. A token that is in
another container is moved. Only the tokens that could not be added are reported.

Example::

    pi-tokenjanitor find --tokenattribute 'serial=^OATH0004C934$' add_to_container SMPH00009272

remove_from_container
*********************

Removes the selected tokens from their container. The tokens are kept.

Example::

    pi-tokenjanitor find --tokenattribute 'serial=^OATH0004C934$' remove_from_container

.. _pi-tokenjanitor_container:

Container
~~~~~~~~~

``pi-tokenjanitor container`` selects token containers with the options below and passes them to
a subcommand. A container is selected only if it matches all given options.

Unlike the filters of ``find``, the text options compare the whole value, ignore upper and lower
case and accept ``*`` as a wildcard: ``--description 'my*'`` finds ``My smartphone`` and
``my tablet``. Only ``--template`` without ``*`` is case sensitive (on MySQL and MariaDB this
depends on the collation of the database).

``-s``, ``--serial``
    The serial of the container.

    Example::

        pi-tokenjanitor container --serial SMPH00009272

``-t``, ``--type``
    The container type: ``generic``, ``smartphone`` or ``yubikey``.
``-ts``, ``--token-serial``
    The serial of a token in the container.
``-r``, ``--realm``
    A realm of the container.
``-T``, ``--template``
    The name of the template the container was created with.
``-d``, ``--description``
    The description of the container.
``-R``, ``--resolver``
    The resolver of the user the container is assigned to.
``-i``, ``--info``
    An entry of the container info, given as ``<key>=<value>``. The key and the value may contain
    ``*``, the value can not contain ``=``. Can only be given once.

    Example::

        pi-tokenjanitor container --info 'os=android'

``-a``, ``--assigned``
    ``true`` finds the containers that are assigned to a user, ``false`` the unassigned ones.
    ``1`` and ``0`` or ``yes`` and ``no`` work as well.
``-o``, ``--orphaned``
    ``true`` finds the orphaned containers, ``false`` all others. An orphaned container is
    assigned to a user who no longer exists in the user store. If the user can not be looked up
    because of a resolver error, the container is skipped with a message on stderr, with ``true``
    as well as with ``false``. There is no ``--orphaned-on-error`` for containers.

    Example::

        pi-tokenjanitor container --orphaned true

``-l``, ``--last-auth-delta``
    The containers that were last used for an authentication **within** the given period, e.g.
    ``90d``. The units are ``s``, ``m`` (minutes), ``h``, ``d`` and ``y``. A container that was
    never used does not match.

    .. warning:: ``--last-auth-delta`` and ``--last-sync-delta`` select the containers that are
       still in use. ``pi-tokenjanitor container --last-auth-delta 90d delete`` deletes every
       container that was used in the last 90 days, not the unused ones.

    Example::

        pi-tokenjanitor container --last-auth-delta 90d list --key last_authentication

``-L``, ``--last-sync-delta``
    The containers that were last synchronized **within** the given period, in the same format. A
    container that was never synchronized does not match.
``-c``, ``--chunksize``
    The number of containers read from the database in one query (default: 100). It limits the
    memory use, all selected containers are processed.

.. _pi-tokenjanitor_container_list:

list
****

Lists the selected containers, one line per container with the serial and the information
selected with ``--key``. ``list`` is the default if no subcommand is given.

``-k``, ``--key``
    The information to show. Can be given multiple times. Default: ``type``, ``tokens``,
    ``users``, ``realms`` and ``description``. Possible keys: ``type``, ``description``,
    ``states``, ``info``, ``internal_info_keys``, ``template``, ``realms``, ``users``,
    ``tokens``, ``last_authentication`` and ``last_synchronization``.

Example::

    pi-tokenjanitor container --type smartphone list --key users --key last_synchronization

delete
******

Deletes the selected containers. By default the tokens in them are kept and are then in no
container.

``-t``, ``--tokens``
    Delete the tokens in the containers as well.

Examples::

    pi-tokenjanitor container --orphaned true delete
    pi-tokenjanitor container --serial SMPH00009272 delete --tokens

update_info
***********

Sets the entry ``KEY`` of the container info to ``VALUE`` in the selected containers. A missing
entry is added, an existing entry is overwritten, all other entries stay unchanged. An entry that
privacyIDEA maintains itself, listed by ``list --key internal_info_keys``, can not be changed: the
container is skipped with a message.

Example::

    pi-tokenjanitor container --type smartphone update_info os android

delete_info
***********

Deletes the entry ``KEY`` from the container info of the selected containers. An entry that
privacyIDEA maintains itself can not be deleted, this is reported for each container.

Example::

    pi-tokenjanitor container --type smartphone delete_info os

set_description
***************

Sets the description of the selected containers to ``DESCRIPTION``.

Example::

    pi-tokenjanitor container --type smartphone set_description 'example description'

set_realm
*********

Sets the realms of the selected containers. ``REALMS`` is a comma-separated list. The given realms
**replace** the realms of the containers, only the realms of the assigned users are always kept.
Realms that can not be set are reported.

``-a``, ``--add``
    Add the realms to the existing realms instead of replacing them. Given realms that the
    container already has are then reported as not set as well; they stay.

Example::

    pi-tokenjanitor container --type smartphone set_realm 'defrealm,realmA' --add

.. _pi-tokenjanitor_import:

Import
~~~~~~

``pi-tokenjanitor import`` imports tokens from a file. A token whose serial does not exist yet is
created. An existing token with the same serial is **overwritten** with the data from the file.

.. _pi-tokenjanitor_import_pskc:

pskc
****

Imports the tokens from the PSKC file ``PSKC_FILE``. The tokens are imported as hardware tokens
without an owner. A token whose serial exists with a different token type is not imported.

``--preshared_key``
    The AES key in hex that the OTP keys in the file are encrypted with, e.g. the key that the
    :ref:`export <pi-tokenjanitor_export>` with ``--format pskc`` printed.
``--validate_mac``
    How the HMAC of the tokens in the file is checked. ``check_fail_hard``, the default, imports no
    token if one HMAC is invalid. ``check_fail_soft`` skips the tokens with an invalid HMAC.
    ``no_check`` imports every token without checking the HMAC.

Example::

    pi-tokenjanitor import pskc tokens.xml --preshared_key 8b3769b889aa22de1a6f5c75d1a6dda3

.. _pi-tokenjanitor_import_privacyidea:

privacyidea
***********

Imports the tokens from ``FILE``, an :ref:`export <pi-tokenjanitor_export>` in the ``pi`` format.
The output counts the imported, the updated and the failed tokens. The causes of failures are
written to the log file.

``--key``
    The key that the export printed.
``--keyfile``
    A file that contains the key, e.g. the file the export offered to save the key to. One of
    ``--key`` and ``--keyfile`` is required.
``--user``, ``--no-user``
    Assign the tokens to the owners stored in the export (default: ``--no-user``). A token whose
    owner can not be found in the user store is neither imported nor updated.

Example::

    pi-tokenjanitor import privacyidea tokens.pi --keyfile tokens.key --user

.. _pi-tokenjanitor_update:

Update
~~~~~~

``pi-tokenjanitor update YAML_FILE`` writes the token data from a YAML export, created with
``find ... export --format yaml`` without ``--b32``, into the existing tokens with the same serial.
The OTP keys are stored encrypted with the current encryption key, so this can be used to
re-encrypt the token data, see :ref:`faq_reencryption`.

A token that does not exist, and an entry without a serial, are skipped with a message on stderr.
An entry the token can not be updated with, e.g. one with an invalid value, is reported on stderr
with the cause. In each case the command goes on with the next entry.
The command does not create tokens and does not change the owners. The fail counter and the token
kind (hardware or software) of a token are kept, and so is its OTP counter, unless the counter in
the file is higher: then the token takes that one. So OTP values that were already used do not
become valid again.

Example::

    pi-tokenjanitor update tokens.yaml

.. _pi-tokenjanitor_deprecated:

Deprecated tokens
~~~~~~~~~~~~~~~~~

When a token type is removed from privacyIDEA, the database migration of the update changes the
existing tokens of this type to the type ``deprecated``, e.g. the U2F tokens in version 3.14. They
remain in the token list but can not authenticate. The tokeninfo ``original_tokentype`` keeps the
original type.

list
****

``pi-tokenjanitor deprecated list [ORIGINAL_TYPE]`` lists the deprecated tokens grouped by their
original type, with the version that removed the type. ``ORIGINAL_TYPE``, e.g. ``u2f``, restricts
the list to this type. The default ``all`` lists all deprecated tokens.

delete
******

``pi-tokenjanitor deprecated delete ORIGINAL_TYPE`` deletes the deprecated tokens of the original
type ``ORIGINAL_TYPE``, or all deprecated tokens with ``all``. It shows the number of tokens per
original type and asks for confirmation.

``-y``, ``--yes``
    Delete without asking.

Examples::

    pi-tokenjanitor deprecated list
    pi-tokenjanitor deprecated delete u2f

.. _pi-tokenjanitor_orphans:

Orphaned user data
~~~~~~~~~~~~~~~~~~

privacyIDEA stores some data per user in its own database. If a user is deleted in the user store,
this data stays behind. Three commands find it:

``user-settings``
    The settings users and administrators store, e.g. the state of the WebUI widgets. This also
    finds the settings of local administrators that no longer exist.
``custom-attributes``
    The :ref:`additional user attributes <user_attributes>`.
``internal-attributes``
    The data privacyIDEA stores per user for its own use, e.g. the FIDO2 user ID.

A row is orphaned if its resolver no longer exists or if the resolver no longer knows the user ID.
Each of the three commands has these subcommands and options:

``list``
    List the orphaned rows. This is the default if no subcommand is given.
``delete``
    Delete the orphaned rows. The command shows the number of orphaned users and asks for
    confirmation, ``--yes`` deletes without asking.
``--orphaned-on-error``
    An option of the command, given before the subcommand: a row counts as orphaned if the user
    store raises an error while looking up the user, e.g. because it can not be reached. Without
    the option such rows are skipped.

Examples::

    pi-tokenjanitor user-settings
    pi-tokenjanitor custom-attributes delete
    pi-tokenjanitor internal-attributes --orphaned-on-error list

The tokens and containers of deleted users are found with ``pi-tokenjanitor find --orphaned true``
and ``pi-tokenjanitor container --orphaned true``.

.. warning:: A resolver with a wrong configuration, e.g. a wrong base DN or search filter, can
   return no user without reporting an error. All users of this resolver then count as orphaned,
   and ``delete`` removes their data. Check the list before you delete anything. See
   :ref:`cleanup_jobs` for why these commands are not scheduled.

.. _pi-tokenjanitor_mapping:
.. _token_janitor:

Migrating from privacyidea-token-janitor
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. index:: privacyidea-token-janitor

``privacyidea-token-janitor`` is deprecated, use ``pi-tokenjanitor`` instead. The table lists the
commands and options of ``privacyidea-token-janitor`` and how to do the same with
``pi-tokenjanitor``. ``A`` stands for a token attribute, ``K`` for a tokeninfo key.

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - privacyidea-token-janitor
     - pi-tokenjanitor
   * - ``find --serial REGEX``
     - ``find --tokenattribute 'serial=REGEX'``
   * - ``find --description REGEX``
     - ``find --tokenattribute 'description=REGEX'``
   * - ``find --tokentype hotp``
     - ``find --tokenattribute 'tokentype=^hotp$'``
   * - ``find --tokenattribute A --tokenattribute-value V``
     - ``find --tokenattribute 'A=V'``
   * - ``--tokenattribute-value-less-than N``, ``--tokenattribute-value-greater-than N``
     - ``--tokenattribute 'A<N'``, ``--tokenattribute 'A>N'``
   * - ``find --tokeninfo-key K --tokeninfo-value V``
     - ``find --tokeninfo 'K=V'``
   * - ``--tokeninfo-value-less-than N``, ``--tokeninfo-value-greater-than N``
     - ``--tokeninfo 'K<N'``, ``--tokeninfo 'K>N'``
   * - ``--tokeninfo-value-before DATE``, ``--tokeninfo-value-after DATE``
     - ``--tokeninfo 'K<DATE'``, ``--tokeninfo 'K>DATE'``
   * - ``find --last_auth 90d``
     - ``find --tokeninfo 'last_auth<-90d'``
   * - ``find`` (without an action), ``find --csv``
     - ``list``, ``list --format json``
   * - ``--has-tokeninfo-key``, ``--has-not-tokeninfo-key``, ``--assigned``, ``--active``,
       ``--orphaned``
     - the same options
   * - ``--orphaned-on-error True``
     - ``--orphaned-on-error``, a flag
   * - ``--chunksize N``
     - ``--chunksize N``, default 1000
   * - ``--action disable``, ``--action delete``, ``--action unassign``
     - the subcommands ``disable``, ``delete`` and ``unassign``
   * - ``--action mark --set-description TEXT``
     - ``set_description --description TEXT``
   * - ``--action mark --set-tokeninfo-key K --set-tokeninfo-value V``
     - ``set_tokeninfo --tokeninfo 'K=V'``
   * - ``--action tokenrealms --tokenrealms realmA,realmB``
     - ``set_tokenrealms --tokenrealm realmA --tokenrealm realmB``
   * - ``--action listuser --attributes email``
     - ``list -u username -u email``
   * - ``--sum --action listuser``
     - ``list --summarize``
   * - ``--action export``
     - ``export --format pskc``
   * - ``--action export --csv``, ``--action export --yaml``
     - ``export --format csv``, ``export --format yaml``
   * - ``--b32``
     - ``export --b32``
   * - ``load FILE --preshared_key_hex KEY``
     - ``import pskc FILE --preshared_key KEY``
   * - ``update FILE``
     - ``update FILE``

