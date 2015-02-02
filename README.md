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

For installation instructions you can see the internal documentation,
which is also contained in this git repository at

https://github.com/privacyidea/privacyidea/blob/master/doc/installation/index.rst

You can also browse the documentation on the web site, which contains the
latest released documentation and might not be the bleeding edge

https://www.privacyidea.org/doc/current/

Token management
----------------

privacyIDEA has a web management interface to login for either as normal users or administrators.
You need to create the first administrator to login. This administrator then can
* create UserIdResolvers
* a realm 
* and enroll tokens.

To create an administrator do this:

    $ privacyidea-create-pwidresolver-user -u admin_name -p secret_password -i 1000 >> etc/privacyidea/admin-users

You then can login with the user ``admin-name`` and the password ``secret-password``. 
All the administrators are stored in the file defined in the privacyIDEA.ini entry "privacyideaSuperuserFile".

Authentication
--------------
You can use the web API to authenticate users. If you enrolled a token for a user, you can authenticate
the user by calling the URL:

    http://yourserver:5001/validate/check?user=you&pass=pin123456

Yubikeys
--------
privacyIDEA supports Yubikeys. To enroll yubikeys you need to install the admin client "privacyideaadm".

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

