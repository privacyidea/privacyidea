.. _scripthandler:

Script Handler Module
---------------------

.. index:: Script Handler, Handler Modules

The script event handler module is used to trigger external scripts in case
of certain events.

This way you can even add external actions to your workflows.
You could trigger a database dump, an external printing device, a backup and
much more.

Possible Actions
~~~~~~~~~~~~~~~~

The actions of the script event handler are the scripts located in a certain
script directory. The default script directory is ``/etc/privacyidea/scripts``.

You can change the location of the script directory and give the new
directory in the parameter ``PI_SCRIPT_HANDLER_DIRECTORY`` in your ``pi.cfg``
 file.

Possible Options
~~~~~~~~~~~~~~~~

Options can be passed to the script. Your script has to take care of the
parsing of these parameters.

logged_in_role
..............

Add the role of the logged in user. This can be either *admin* or *user*. If
there is no logged in user, *none* will be passed.

The script will be called with the parameter

   --logged_in_role <role>

logged_in_user
..............

Add the logged in user. If
there is no logged in user, *none* will be passed.

The script will be called with the parameter

   --logged_in_user <username>@<realm>

realm
.....

Add ``--realm <realm>`` as script parameter. If no realm is given, *none*
will be passed.

serial
......

Add ``--serial <serial number>`` as script parameter. If no serial number is
given, *none* will be passed.

user
....

Add ``--serial <username>'`` as script parameter. If no username is given,
*none* will be passed.

.. note:: A possible script you could call is the :ref:`get_unused_tokens`.
