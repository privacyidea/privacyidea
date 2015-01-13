Preface
=======

The new 2.0 branch is based on flask and sqlalchemy as the python backend. The web UI is based
on angularJS and bootstrap.

At the moment the 2.0 branch is not ready for production. You can follow the setup instructions and play around.
You are also welcome to take a look at the hopefully tidy code and contribute.

I try to keep up a good test coverage. So run tests!

Setup
=====

You can setup the system in a virtual environment:

    mkdir privacyidea
    cd privacyidea
    virtualenv venv
    source venv/bin/activate
    pip install -r requirements.txt


Running it
==========

Create the database:

    ./manage.py createdb

Create the first administrator:

    ./manage.py <email> <username>

Run it:

    ./manage.py runserver

Now you can connect to http://localhost:5000 with your browser and login as administrator.

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


