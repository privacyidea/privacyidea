.. _server_tools:

Server Tools
============

.. index:: server tools

``privacyidea-expired-users``, ``privacyidea-usercache-cleanup`` and
``privacyidea-get-serial`` work directly on the database of a privacyIDEA
server, the web server does not need to run. They read the configuration file
``/etc/privacyidea/pi.cfg``, or the file given in the environment variable
``PRIVACYIDEA_CONFIGFILE`` (see :ref:`cfgfile`). Run them as the user
privacyIDEA runs as, so that they can read the configuration and the
encryption key.

.. _privacyidea_expired_users:

privacyidea-expired-users
-------------------------

.. index:: expired users

``privacyidea-expired-users`` looks for users whose account has expired and
unassigns or deletes their tokens. It needs an LDAP resolver with
``"accountExpires": "accountExpires"`` in its attribute mapping, see
:ref:`ldap_expired_users`. Accounts that never expire are skipped::

   privacyidea-expired-users [-r REALM] [-u REGEX] [-d REGEX] [-a KEY] [-n]

``-r REALM``, ``--realm REALM``
    Only check the users of this realm. Without it, the users of all realms
    are checked.

``-u REGEX``, ``--unassign_serial REGEX``
    Unassign the tokens of an expired user whose serial matches the regular
    expression. The default ``.*`` matches every token.

``-d REGEX``, ``--delete_serial REGEX``
    Delete the tokens of an expired user whose serial matches the regular
    expression. By default no token is deleted.

``-a KEY``, ``--attribute_name KEY``
    The key of the attribute mapping that holds the expiration date. The
    default is ``accountExpires``. The LDAP resolver only compares this key as
    a date, so keep the default.

``-n``, ``--noaction``
    Only show which accounts have expired and what would be done with their
    tokens.

A regular expression matches if it is found anywhere in the serial, use ``^``
to match the beginning. If a resolver cannot be queried, the tool skips it and
prints a warning, as the result is then incomplete.

.. warning:: The tool unassigns and deletes tokens without asking. As ``-u``
   defaults to ``.*``, a run without options unassigns **all** tokens of every
   expired user. Run it with ``-n`` first and check the output.

List the expired users of the realm ``ad`` and their tokens, then unassign all
their tokens and delete those whose serial starts with ``TOTP``::

   privacyidea-expired-users -r ad -n
   privacyidea-expired-users -r ad -d '^TOTP'

.. _privacyidea_usercache_cleanup:

privacyidea-usercache-cleanup
-----------------------------

.. index:: user cache

``privacyidea-usercache-cleanup`` deletes the entries of the :ref:`usercache`
that are older than the expiration timeout (see :ref:`user_cache_timeout`).
While the user cache is disabled, it does nothing. Run it regularly, e.g.
daily, see :ref:`cleanup_jobs`.

``-n``, ``--noaction``
    Only list the expired entries, do not delete them.

The tool lists every entry it deletes on stdout. In a crontab, discard the
output with ``> /dev/null``, errors are still written to stderr.

.. _privacyidea_get_serial:

privacyidea-get-serial
----------------------

.. index:: Get Serial (Determine Serial by OTP)

``privacyidea-get-serial`` finds the token that generated a given OTP value,
like :ref:`get_serial` in the WebUI::

   privacyidea-get-serial [-t TYPE] [-s SERIAL] [-a | -u] [-w WINDOW] OTP

``-t TYPE``, ``--type TYPE``
    Only search tokens of this type, e.g. ``hotp`` or ``totp``.

``-s SERIAL``, ``--serial SERIAL``
    Only search tokens whose serial contains this string.

``-a``, ``--assigned``
    Only search tokens that are assigned to a user.

``-u``, ``--unassigned``
    Only search tokens that are not assigned to a user.

``-w WINDOW``, ``--window WINDOW``
    The number of OTP values to check per token, default ``10``: the next
    counter values of HOTP tokens, the time steps around the current time for
    TOTP tokens.

The tool calculates OTP values for every token in the search, which takes a
while with many tokens, so narrow the search down with ``-t`` and ``-s``. If
more than one token matches, it stops with an error. When a token is found,
its counter is moved past the OTP value, so this OTP value can no longer be
used to authenticate.

Search the HOTP tokens whose serial contains ``OATH``::

   privacyidea-get-serial -t hotp -s OATH 123456

.. _privacyidea_standalone:

privacyidea-standalone
----------------------

.. index:: standalone instance

``privacyidea-standalone`` creates a local privacyIDEA instance that needs no
web server, and checks user names and passwords against it on the command
line, e.g. from a script on a single machine. An instance is a directory,
by default ``~/.privacyidea``, that holds the configuration file ``pi.cfg``,
an SQLite database, the encryption key, the audit keys and the log file. All
commands take the directory with ``-i DIR`` (``--instance DIR``).

``privacyidea-standalone create [-i DIR]``
    Creates a new instance. The directory must not exist yet. The command asks
    for the password of the administrator ``super``. It then offers to create
    the resolver ``defresolver`` in the realm ``defrealm``, either as a user
    table in the database of the instance (you manage the users in the WebUI)
    or with the users from ``/etc/passwd``. The command calls ``pi-manage``, so
    run it with the virtual environment activated. If a step fails, the
    directory is removed again.

``privacyidea-standalone configure [-i DIR]``
    Starts a local web server at ``http://127.0.0.1:5000``, where you configure
    the instance in the WebUI, e.g. enroll tokens. Stop it with Ctrl-C when you
    are done. Do not make this server reachable from the network.

``privacyidea-standalone check [-i DIR] [-u USER] [-p PASSWORD] [-r]``
    Checks a user name and password against the instance, like an
    authentication request to ``/validate/check``. The password is the static
    part, e.g. the OTP PIN, followed by the OTP value. The command exits with
    ``0`` if the user authenticated successfully, with ``1`` if the
    authentication failed, and with another non-zero status on errors, e.g. if
    the instance does not exist. ``-r`` (``--response``) prints the JSON
    response.

    If ``-u`` or ``-p`` is missing, the command asks for it. Without a
    terminal, e.g. when called from a script, it reads the missing values from
    standard input, one per line: first the user name, then the password.
    Prefer this over ``-p``, because command line arguments are visible to
    other users in the process list.

.. _privacyidea_diag:

privacyidea-diag
----------------

.. index:: diagnostics, support

``privacyidea-diag`` collects information about the system and the privacyIDEA
installation into one file for your support team. Run it as root, optionally
with the path of the configuration file (default ``/etc/privacyidea/pi.cfg``)::

   privacyidea-diag /etc/privacyidea/pi.cfg

``pi-manage`` has to be in the ``PATH``. The script is written for Debian,
Ubuntu, RHEL and CentOS, on other distributions it collects less. It writes the
file ``/tmp/<yy-mm-dd>_pi_diag_<random>.tar.gz``, which only root can read,
and prints its name. The file contains:

* the distribution, the installed system packages, the Python packages in
  ``/opt/privacyidea``, the processes and the disk usage,
* ``pi.cfg``, the revision of the database schema, the resolvers, realms,
  event handlers and policies, and the SMTP, RADIUS and privacyIDEA server
  definitions,
* the file list of the FreeRADIUS configuration, the Apache configuration,
  the last 100 lines of the Apache or nginx logs and, on CentOS, the SELinux
  denials,
* the privacyIDEA log file and the audit log of the last two days.

``privacyidea-diag`` censors secrets before it writes them into the file:

* ``pi.cfg`` is included without comments. The values of the settings whose
  name contains ``SECRET``, ``PASSWORD``, ``PASSWD``, ``PEPPER`` or
  ``CREDENTIAL``, or ends with ``_KEY``, ``_OPTIONS`` or ``EXTRA_PARAMS``, are
  censored. Of the settings whose name ends with ``_URI`` or ``_URL``, e.g.
  ``SQLALCHEMY_DATABASE_URI``, only the scheme is kept, which shows the
  database driver. ``PI_BASE_URL`` is kept as it is.
* In the exported resolvers, event handlers, policies and server definitions,
  the passwords and secrets that the export itself censors are censored, and
  so are all text values of keys that contain ``secret``, ``passw``,
  ``bindpw``, ``authorization``, ``credential``, ``api_key`` or
  ``private_key`` (also with ``-`` or without a separator), or that end with
  ``token`` (like ``access_token``), regardless of case. This also applies to
  JSON objects inside values, e.g. HTTP headers.

Secrets in free text are not recognised, e.g. in the data of a webhook event
handler, and the privacyIDEA log file and the audit log are included as they
are. So the file still contains your configuration, and user names and IP
addresses from the logs: only give it to recipients you trust.
