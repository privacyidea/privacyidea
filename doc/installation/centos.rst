
.. _install_centos:

CentOS Installation
-------------------

Step-by-Step installation on CentOS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. index:: CentOS, Red Hat, RHEL

In this chapter we describe a way to install privacyIDEA on CentOS 7 based on the
installation via :ref:`pip_install`. It follows the
approach used in the enterprise packages (See `RPM Repository`_).

Setting up the required services
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In this guide we use Python 2.7 even though its end-of-life draws closer.
CentOS 7 will support Python 2 until the end of its support frame.
Basically the steps for using privacyIDEA with Python 3 are the same but several
other packages need to be installed [#py3]_.

First the necessary packages need to be installed::

    $ yum install mariadb-server httpd mod_wsgi mod_ssl python-virtualenv policycoreutils-python

Now enable and configure the services::

    $ systemctl enable --now httpd
    $ systemctl enable --now mariadb
    $ mysql_secure_installation

Setup the database for the privacyIDEA server::

    $ echo 'create database pi;' | mysql -u root -p
    $ echo 'create user "pi"@"localhost" identified by "<dbsecret>";' | mysql -u root -p
    $ echo 'grant all privileges on pi.* to "pi"@"localhost";' | mysql -u root -p

If this should be a pinned installation (i.e. with all the package pinned to
the versions with which we are developing/testing), some more packages need to
be installed for building these packages::

    $ yum install gcc postgresql-devel

Create the necessary directories::

    $ mkdir /etc/privacyidea
    $ mkdir /opt/privacyidea
    $ mkdir /var/log/privacyidea

Add a dedicated user for the privacyIDEA server and change some ownerships::

    $ useradd -r -M -d /opt/privacyidea privacyidea
    $ chown privacyidea:privacyidea /opt/privacyidea /etc/privacyidea /var/log/privacyidea

Install the privacyIDEA server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Now switch to that user and install the virtual environment for the privacyIDEA
server::

    $ su - privacyidea

Create the virtual environment::

    $ virtualenv /opt/privacyidea

and activate it::

    $ . /opt/privacyidea/bin/activate

If this should be a pinned installation (that is the environment we use to build and test),
we need to install some pinned dependencies first. They should match the version of the targeted
privacyIDEA::

        (privacyidea) $ pip install -r https://raw.githubusercontent.com/privacyidea/privacyidea/v3.0.2/requirements.txt

Then just install the targeted privacyIDEA version with::

        (privacyidea) $ pip install privacyidea==3.0.2

Setting up privacyIDEA
^^^^^^^^^^^^^^^^^^^^^^

In order to setup privacyIDEA a configuration is expected in ``/etc/privacyidea/pi.cfg``. It
should look something like this::

    import logging
    # The realm, where users are allowed to login as administrators
    SUPERUSER_REALM = ['super']
    # Your database
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://pi:<dbsecret>@localhost/pi'
    # This is used to encrypt the auth_token
    #SECRET_KEY = 't0p s3cr3t'
    # This is used to encrypt the admin passwords
    #PI_PEPPER = "Never know..."
    # This is used to encrypt the token data and token passwords
    PI_ENCFILE = '/etc/privacyidea/enckey'
    # This is used to sign the audit log
    PI_AUDIT_KEY_PRIVATE = '/etc/privacyidea/private.pem'
    PI_AUDIT_KEY_PUBLIC = '/etc/privacyidea/public.pem'
    PI_AUDIT_SQL_TRUNCATE = True
    # The Class for managing the SQL connection pool
    PI_ENGINE_REGISTRY_CLASS = "shared"
    PI_AUDIT_POOL_SIZE = 20
    PI_LOGFILE = '/var/log/privacyidea/privacyidea.log'
    PI_LOGLEVEL = logging.INFO

Make sure the configuration file is not world readable (``$ chmod 640 /etc/privacyidea/pi.cfg``).
More information on the configuration parameters can be found in :ref:`cfgfile`.

In order to secure the installation a new ``PI_PEPPER`` and ``SECRET_KEY`` must be generated::

    (privacyidea) $ PEPPER="$(tr -dc A-Za-z0-9_ </dev/urandom | head -c24)"
    (privacyidea) $ echo "PI_PEPPER = '$PEPPER'" >> /etc/privacyidea/pi.cfg
    (privacyidea) $ SECRET="$(tr -dc A-Za-z0-9_ </dev/urandom | head -c24)"
    (privacyidea) $ echo "SECRET_KEY = '$SECRET'" >> /etc/privacyidea/pi.cfg

From now on the ``pi-manage``-tool can be used to configure and manage the privacyIDEA server::

    (privacyidea) $ pi-manage create_enckey  # encryption key for the database
    (privacyidea) $ pi-manage create_audit_keys  # key for verification of audit log entries
    (privacyidea) $ pi-manage createdb  # create the database structure
    (privacyidea) $ pi-manage db stamp head -d lib/privacyidea/migrations/  # stamp the db

An administrative account is needed to configure and maintain privacyIDEA::

    (privacyidea) $ pi-manage admin add <admin-user>

Setting up the Apache webserver
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Now We need to set up apache to forward requests to privacyIDEA, so the next
steps are executed as the ``root``-user again.

First the SELinux settings must be adjusted in order to allow the
``httpd``-process to access the database and write to the privacyIDEA logfile::

    $ semanage fcontext -a -t httpd_sys_rw_content_t "/var/log/privacyidea(/.*)?"
    $ restorecon -R /var/log/privacyidea

and::

    $ setsebool -P httpd_can_network_connect_db 1

If something does not seem right, check for "``denied``" entries in
``/var/log/audit/audit.log``

For testing purposes we use a self-signed certificate which should already have
been created. In production environments this should be replaced by a certificate
from a trusted authority.

To correctly load the apache config file for privacyIDEA we need to disable some
configuration first::

    $ cd /etc/httpd/conf.d
    $ mv ssl.conf ssl.conf.inactive
    $ mv welcome.conf welcome.conf.inactive
    $ curl -O https://raw.githubusercontent.com/NetKnights-GmbH/centos7/master/SOURCES/privacyidea.conf

And we need a corresponding ``wsgi``-script file in ``/etc/privacyidea/``::

    $ cd /etc/privacyidea
    $ curl -O https://raw.githubusercontent.com/NetKnights-GmbH/centos7/master/SOURCES/privacyideaapp.wsgi

After a ``$ systemctl restart httpd`` everything should be up and running.
You can log in with Your admin user at ``https://<privacyidea ip>`` and start
enrolling tokens.

.. _rpm_installation:

RPM Repository
~~~~~~~~~~~~~~

.. index:: RPM, YUM

For customers with a valid service level agreement [#SLA]_ with NetKnights
there is an RPM repository,
that can be used to easily install and update privacyIDEA on CentOS 7 / RHEL 7.
For more information see [#RPMInstallation]_.

.. rubric:: Footnotes

.. [#py3] https://stackoverflow.com/questions/42004986/how-to-install-mod-wgsi-for-apache-2-4-with-python3-5-on-centos-7
.. [#SLA] https://netknights.it/en/leistungen/service-level-agreements/
.. [#RPMInstallation] https://netknights.it/en/additional-service-privacyidea-support-customers-centos-7-repository/
