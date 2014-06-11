privacyIDEA
===========
privacyIDEA is an open solution for strong two-factor authentication.
privacyIDEA aims to not bind you to any decision of the authentication protocol or 
it does not dictate you where your user information should be stored. 
This is achieved by its totally modular architecture.
privacyIDEA is not only open as far as its modular architecture is concerned. 
But privacyIDEA is completely licensed under the AGPLv3.

privacyIDEA is a fork of LinOTP.

Code test on travis-ci.org
--------------------------
Tests are running on travis-ci.org. See the test coverage at coveralls.io.

[![Build Status][BS img]][Build Status]
[![Coverage Status][CS img]][Coverage Status]

[Build Status]: https://travis-ci.org/privacyidea/privacyidea
[Coverage Status]: https://coveralls.io/r/privacyidea/privacyidea

[BS img]: https://travis-ci.org/privacyidea/privacyidea.svg?branch=master
[CS img]: https://coveralls.io/repos/privacyidea/privacyidea/badge.png?branch=master

Installation
------------

Installing privacyIDEA can be performed easily by issuing the commands::

    $ pip install privacyidea

privacyIDEA comes with its own user authentication for administrators and 
normal users. Thus you can start directly by creating the database.
In the example configuration file the database is an SQLite database::
located at::

    $ paster setup-app config/privacyidea.ini.example

In the config file privacyidea.ini.example the already shipped encryption key "dummy-encKey" is referenced.
Of course, you should create an encryption key and change in in the privacyidea.ini.example:

    $ dd if=/dev/random of=etc/privacyidea/encKey bs=1 count=96

Then start the webserver by issuing::

    $ paster serve config/privacyidea.ini.example

Authentication
--------------
privacyIDEA has one login window at https://localhost:5001 to login for either as normal users or administrators.
You need to create the first administrator to login. This administrator than can
* create UserIdResolvers
* a realm 
* and enroll tokens.
To create an administrator do this:

    $ privacyidea-create-pwidresolver-user -u <admin-name> -p <secret-password> -i 1000 >> config/admin-users

You then can login with the user <admin-name> and the password <secret-password>. 
All the administrators are stored in the file defined in the privacyIDEA.ini entry "privacyideaSuperuserFile".

Options
-------

You can adapt the file **etc/privacyidea/privacyidea.ini.example**. There you need to configure the database connection
with an existing database and user:

    sqlalchemy.url = mysql://user:password@localhost/privacyIDEA

Then  you can create the database like above:

    $ paster setup-app etc/privacyidea/privacyidea.ini.example

You can change the location of your log file:

    $ mkdir /var/log/privacyidea

Authentication
--------------
You can use the web API to authenticate users. If you enrolled a token for a user, you can authenticate
the user by calling the URL::

    http://yourserver:5001/validate/check?user=you&pass=pin123456

Yubikeys
--------
privacyIDEA supports Yubikeys. To enroll yubikeys you need to install the admin client::

    $ pip install privacyideaadm

Tests
-----
If you want to see, if everything works fine, you can run the functional tests.
There are roughly 350 sometimes complex tests, running the tests will take about
30 minutes. Do it like this::

    $ python setup.py build
    $ ./test.sh

Questions
---------
Take a look at http://privacyidea.org and join the google group https://groups.google.com/forum/#!forum/privacyidea.

