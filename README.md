privacyIDEA
===========

[![Build Status][BS img]][Build Status]
[![Coverage Status][CS img]][Coverage Status]
[![Downloads](https://pypip.in/download/privacyidea/badge.svg)](https://pypi.python.org/pypi/privacyidea/)
[![Latest Version](https://pypip.in/version/privacyidea/badge.svg)](https://pypi.python.org/pypi/privacyidea/)
[![License](https://pypip.in/license/privacyidea/badge.svg)](https://pypi.python.org/pypi/privacyidea/)
[![Documentation Status](https://readthedocs.org/projects/privacyidea/badge/?version=latest)](http://privacyidea.readthedocs.org/en/latest/)

[Build Status]: https://travis-ci.org/privacyidea/privacyidea
[Coverage Status]: https://coveralls.io/r/privacyidea/privacyidea

[BS img]: https://travis-ci.org/privacyidea/privacyidea.svg?branch=master
[CS img]: https://coveralls.io/repos/privacyidea/privacyidea/badge.png?branch=master

privacyIDEA is an open solution for strong two-factor authentication.
privacyIDEA does to not bind you to any decision of the authentication
protocol or it does not dictate you where your user information should be
stored. This is achieved by its totally modular architecture.
privacyIDEA is not only open as far as its modular architecture is
concerned. But privacyIDEA is completely licensed under the AGPLv3.

Version 2.0
===========

The new 2.0 branch is based on flask and sqlalchemy as the python backend. The web UI is based
on angularJS and bootstrap.

At the moment the 2.0 branch is not ready for production. 
For productive use please use privacyIDEA 1.5.1.

You can follow the setup instructions and play around.
You are also welcome to take a look at the hopefully tidy code and contribute.

I try to keep up a good test coverage. So run tests!

Setup
=====

You can setup the system in a virtual environment:

    git checkout https://github.com/privacyidea/privacyidea.git
    cd privacyidea
    virtualenv venv
    source venv/bin/activate
    pip install -r requirements.txt


Running it
==========

Create the database:

    ./pi-manage.py createdb

Create the first administrator:

    ./pi-manage.py admin add <username> <email>

Run it:

    ./pi-manage.py runserver

Now you can connect to http://localhost:5000 with your browser and login as administrator.

Run in virtualenv
=================

For running the server in a virtual env see documentation at
https://www.privacyidea.org/doc/current/installation/index.html#python-package-index.

Run tests
=========

    nosetests -v --with-coverage --cover-package=privacyidea --cover-html

Code structure
==============

The database models are defined in ``models.py`` and tested in tests/test_db_model.py.

Based on the database models there are the libraries ``lib/config.py`` which is
responsible for basic configuration in the database table ``config``.
And the library ``lib/resolver.py`` which provides functions for the database
table ``resolver``. This is tested in tests/test_lib_resolver.py.

Based on the resolver there is the library ``lib/realm.py`` which provides functions
for the database table ``realm``. Several resolvers are combined into a realm.

Based on the realm there is the library ``lib/user.py`` which provides functions 
for users. There is no database table user, since users are dynamically read from
the user sources like SQL, LDAP, SCIM or flat files.

Upgrading
=========

The database model has changed, so that you need to upgrade the database.

!! Before upgrading be sure to make a backup !!

To upgrade your database from 1.5 to the new 2.0 schema run:

   ./manage db upgrade

