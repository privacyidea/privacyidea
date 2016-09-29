.. _performance:

Performance considerations
--------------------------

You can test performace using the apache bench from the apache utils.
Creating a simple pass token for a user, eases the performance testing.

Then you can run

   ab -n 200 -c 8 -s 30 'https://localhost/validate/check?user=yourUser&pass
 =yourPassword'

The performance depends on several aspects like the connection speed to your
database and the connection speed to your user stores.

Processes
~~~~~~~~~

You should run several processes and threads.

Config caching
~~~~~~~~~~~~~~

PI_CHECK_RELOAD_CONFIG

Logging
~~~~~~~

No debug

Response
~~~~~~~~

No details on success


Clean configuration
~~~~~~~~~~~~~~~~~~~

Remove unused resolvers and policies. Have a realm with several resolvers is
a bit slower than one realm with one resolver. Finding the user in the first
resolver is faster than in the last resolver.
Although e.g. the LDAP resolver utilizes caching.
