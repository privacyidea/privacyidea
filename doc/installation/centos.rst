.. _install_centos:

.. _install_rhel:

RHEL Installation
-----------------

Step-by-step installation on RHEL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. index:: RHEL, Red Hat, Rocky Linux, AlmaLinux, CentOS

In this chapter we describe a way to install privacyIDEA on Red Hat Enterprise Linux (RHEL) 8, 9 and 10 and on
its rebuilds like Rocky Linux and AlmaLinux, based on the installation via :ref:`pip_install`. It follows the
approach used in the enterprise packages (see `RPM Repository`_).

privacyIDEA needs Python 3.10 or newer. RHEL 10 ships Python 3.12 as its system Python. On RHEL 8 and 9 the
``python3.11`` packages from the AppStream repository are used instead of the system Python.

.. _centos_setup_services:

Setting up the required services
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

First the necessary packages need to be installed. On RHEL 8 and 9::

    $ dnf install mariadb-server httpd mod_ssl python3.11 python3.11-mod_wsgi policycoreutils-python-utils

On RHEL 10::

    $ dnf install mariadb-server httpd mod_ssl python3 python3-mod_wsgi policycoreutils-python-utils

Now enable and configure the services::

    $ systemctl enable --now httpd
    $ systemctl enable --now mariadb
    $ mysql_secure_installation

Setup the database for the privacyIDEA server::

    $ echo 'create database pi;' | mysql -u root -p
    $ echo 'create user "pi"@"localhost" identified by "<dbsecret>";' | mysql -u root -p
    $ echo 'grant all privileges on pi.* to "pi"@"localhost";' | mysql -u root -p

The :ref:`optional features <pip_extras>` build native extensions. If you want to install one of them, install
the system packages listed there as well.

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

Create the virtual environment. On RHEL 8 and 9 use ``python3.11``::

    $ python3.11 -m venv /opt/privacyidea

On RHEL 10 use the system Python::

    $ python3 -m venv /opt/privacyidea

Activate it::

    $ . /opt/privacyidea/bin/activate

and install/update some prerequisites::

    (privacyidea)$ pip install -U pip setuptools

For a pinned installation (that is the environment we use to build and test), install the pinned dependencies
first. They must match the version of privacyIDEA you install. You can get the latest version from the
`GitHub release page <https://github.com/privacyidea/privacyidea/releases>`_ or the
`PyPI package history <https://pypi.org/project/privacyIDEA/#history>`_::

    (privacyidea)$ export PI_VERSION=<version>
    (privacyidea)$ pip install -r https://raw.githubusercontent.com/privacyidea/privacyidea/v${PI_VERSION}/requirements.txt

Replace ``<version>`` with the privacyIDEA version you want to install. Then install this version with::

    (privacyidea)$ pip install privacyidea==${PI_VERSION}

.. _centos_setup_pi:

Setting up privacyIDEA
^^^^^^^^^^^^^^^^^^^^^^

In order to setup privacyIDEA a configuration file must be added in
``/etc/privacyidea/pi.cfg``. It should look something like this::

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
    # The Class for managing the SQL connection pool
    PI_ENGINE_REGISTRY_CLASS = "shared"
    PI_AUDIT_POOL_SIZE = 20
    PI_LOGFILE = '/var/log/privacyidea/privacyidea.log'
    PI_LOGLEVEL = logging.INFO

Make sure the configuration file is not world readable:

.. code-block:: bash

    (privacyidea)$ chmod 640 /etc/privacyidea/pi.cfg

More information on the configuration parameters can be found in :ref:`cfgfile`.

In order to secure the installation a new ``PI_PEPPER`` and ``SECRET_KEY`` must be generated:

.. code-block:: bash

    (privacyidea)$ PEPPER="$(tr -dc A-Za-z0-9_ </dev/urandom | head -c24)"
    (privacyidea)$ echo "PI_PEPPER = '$PEPPER'" >> /etc/privacyidea/pi.cfg
    (privacyidea)$ SECRET="$(tr -dc A-Za-z0-9_ </dev/urandom | head -c24)"
    (privacyidea)$ echo "SECRET_KEY = '$SECRET'" >> /etc/privacyidea/pi.cfg

From now on the ``pi-manage``-tool can be used to configure and manage the privacyIDEA server:

.. code-block:: bash

    (privacyidea)$ pi-manage setup create_enckey  # encryption key for the database
    (privacyidea)$ pi-manage setup create_audit_keys  # key for verification of audit log entries
    (privacyidea)$ pi-manage setup create_tables  # create the database structure

An administrative account is needed to configure and maintain privacyIDEA:

.. code-block:: bash

    (privacyidea)$ pi-manage admin add <admin-user>

Setting up the Apache webserver
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Now we need to set up Apache to forward requests to privacyIDEA, so the next
steps are executed as the ``root``-user again.

First the SELinux settings must be adjusted in order to allow the
``httpd``-process to access the database and write to the privacyIDEA logfile::

    $ semanage fcontext -a -t httpd_sys_rw_content_t "/var/log/privacyidea(/.*)?"
    $ restorecon -R /var/log/privacyidea

and::

    $ setsebool -P httpd_can_network_connect_db 1

If the user store is an LDAP-resolver, the ``httpd``-process also needs to access
the ldap ports::

    $ setsebool -P httpd_can_connect_ldap 1

If something does not seem right, check for "``denied``" entries in
``/var/log/audit/audit.log``

Some LDAP-resolver could be listening on a different port.
In this case SELinux has to be configured accordingly.
Please check the SELinux audit.log to see if SELinux might block any connection.

For testing purposes we use a self-signed certificate. In production environments this should be replaced by a
certificate from a trusted authority. The Apache configuration below expects it in
``/etc/pki/tls/certs/localhost.crt`` with the key in ``/etc/pki/tls/private/localhost.key``. RHEL 8 can create
this pair with ``/usr/libexec/httpd-ssl-gencerts``. On RHEL 9 and 10, create it yourself if it does not exist
(replace ``<fqdn>`` with the host name of the server)::

    $ openssl req -x509 -newkey rsa:3072 -sha256 -nodes -days 3650 \
        -keyout /etc/pki/tls/private/localhost.key -out /etc/pki/tls/certs/localhost.crt \
        -subj "/CN=<fqdn>" -addext "subjectAltName=DNS:<fqdn>"
    $ chmod 600 /etc/pki/tls/private/localhost.key
    $ restorecon /etc/pki/tls/private/localhost.key /etc/pki/tls/certs/localhost.crt

To correctly load the apache config file for privacyIDEA we need to disable some
configuration first::

    $ cd /etc/httpd/conf.d
    $ mv ssl.conf ssl.conf.inactive
    $ mv welcome.conf welcome.conf.inactive
    $ curl -o privacyidea.conf https://raw.githubusercontent.com/NetKnights-GmbH/centos7/master/SOURCES/privacyidea.conf

In order to avoid recreation of the configuration files during an update, you can
create empty dummy files for ``ssl.conf`` and ``welcome.conf``.

And we need a corresponding ``wsgi``-script file in ``/etc/privacyidea/``::

    $ cd /etc/privacyidea
    $ curl -O https://raw.githubusercontent.com/NetKnights-GmbH/centos7/master/SOURCES/privacyideaapp.wsgi

If ``firewalld`` is running (:code:`$ firewall-cmd --state`) you need to open the https
port to allow connections::

    $ firewall-cmd --permanent --add-service=https
    $ firewall-cmd --reload

After a restart of the apache webserver (:code:`$ systemctl restart httpd`)
everything should be up and running.
You can log in with your admin user at ``https://<privacyidea server>`` and start
enrolling tokens.

.. _rpm_installation:

RPM Repository
~~~~~~~~~~~~~~

.. index:: RPM, DNF

For customers with a valid service level agreement [#SLA]_ with NetKnights
there is an RPM repository
that can be used to easily install and update privacyIDEA on RHEL 8, 9 and 10 and their rebuilds.
For more information see [#RPMInstallation]_.

.. rubric:: Footnotes

.. [#SLA] https://netknights.it/en/services/support/
.. [#RPMInstallation] https://netknights.it/en/additional-service-privacyidea-support-customers-centos-7-repository/
