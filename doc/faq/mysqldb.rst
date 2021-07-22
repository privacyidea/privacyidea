.. _mysqldb:

MySQL database connect string
-----------------------------

You can use the python package ``MySQL-python`` or ``PyMySQL``.

``PyMySQL`` is a pure python implementation. ``MySQL-python`` is a wrapper
for a C implementation. I.e. when installing ``MySQL-python`` your python
virtualenv, you also need to install packages like *python-dev* and
*libmysqlclient-dev*.

Depending on whether you are using ``MySQL-python`` or ``PyMySQL`` you need
to specify different connect strings in ``SQLALCHEMY_DATABASE_URI``.

MySQL-python
~~~~~~~~~~~~
**connect string**: ``mysql://u:p@host/db``

Installation
............

Install a package *libmysqlclient-dev* from your distribution. The name may
vary depending on which distribution you are running::

   pip install MySQL-python

PyMySQL
~~~~~~~
**connect string**: ``pymysql://u:p@host/db``

Installation
............

Install in your virtualenv::

   pip install pymysql-sa
   pip install PyMySQL

