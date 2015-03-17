.. _installation:

Installation
============

The ways described here to install privacyIDEA are

 * the installation via the :ref:`pip_install`, which can be used on
   any Linux distribution and
 * ready made :ref:`install_ubuntu` for Ubuntu 14.04LTS and
 * ready made :ref:`install_wheezy` for Debian Wheezy.

If you want to upgrade from a privacyIDEA 1.5 installation please read :ref:`upgrade`.

.. _pip_install:

Python Package Index
--------------------

.. index:: pip install, virtual environment

You can install privacyidea on usually any Linux distribution in a python
virtual environment
like this::

  virtualenv /opt/privacyidea

  cd /opt/privacyidea
  source bin/activate

Now you are within the python virtual environment.
Within the environment you can now run::

  pip install privacyidea

.. _configuration:

Please see the section :ref:`cfgfile` for a quick setup of your configuration.


Then create the encryption key and the signing keys::

   pi-manage.py create_enckey
   pi-manage.py create_signkey

Create the database and the first administrator::

   pi-manage.py createdb
   pi-manage.py admin add admin admin@localhost

Now you can run the server for your first test::

   pi-manage.py runserver


Depending on the database you want to use, you may have to install additional packages.


.. _install_ubuntu:

Ubuntu Packages
---------------

.. index:: ubuntu

There are ready made debian packages for Ubuntu 14.04 LTS.
These are available in a public ppa repository [#ppa]_,
so that the installation
will automatically resolve all dependencies. 
Install it like this::

   add-apt-repository ppa:privacyidea/privacyidea
   apt-get update
   apt-get install python-privacyidea privacyideaadm

Optionally you can also install necessary configuration files to run
privacyIDEA within the Nginx Webserver::

   apt-get install privacyidea-nginx

Alternatively you can install privacyIDEA running in an Apache webserver::

   apt-get install privacyidea-apache2

After installing in Nginx or Apache2 you only need to create your first
administrator and you are done::

   pi-manage.py admin add admin admin@localhost


.. _install_ubuntu_freeradius:

FreeRADIUS
..........

privacyIDEA has a perl module to "translate" RADIUS requests to the API of the
privacyIDEA server. This module plugs into FreeRADIUS. The FreeRADIUS does not
have to run on the same machine like privacyIDEA.
To install this module run::

   apt-get install privacyidea-radius

For further details see :ref:`freeradius_plugin`.

.. _install_ubuntu_simplesaml:

SimpleSAMLphp
.............

Starting with 1.4 privacyIDEA also supports SAML via a plugin
for simpleSAMLphp [#simpleSAML]_.
The simpleSAMLphp service does not need to run on the same machine
like the privacyIDEA server.

To install it on a Ubuntu 14.04 system please run::

   apt-get install privacyidea-simplesamlphp

For further details see :ref:`simplesaml_plugin`.


.. _install_wheezy:

Debian Packages
---------------
You can install privacyIDEA on debian Wheezy either via the
:ref:`pip_install` or with a ready made Wheezy package.

The available Wheezy package privacyidea-venv_2.1~dev0_amd64.deb contains a
complete virtual environment with all necessary dependent modules. To install
it run::

   dpkg -i privacyidea-venv_2.1~dev0_amd64.deb

This will install privacyIDEA into a virtual environment at
``/opt/privacyidea/privacyidea-venv``.

You can enter the virtual environment by::

   source /opt/privacyidea/privacyidea-venv/bin/activate

Running privacyIDEA with Apache2 and MySQL
..........................................

You need to create and fill the config directory ``/etc/privacyidea`` manually::

   cp /opt/privacyidea/privacyidea-venv/etc/privacyidea/dictionary \
   /etc/privacyidea/

Create a config ``/etc/privacyidea/pi.cfg`` like this::

   # Your database
   SQLALCHEMY_DATABASE_URI = 'mysql://pi:password@localhost/pi'
   # This is used to encrypt the auth_token
   SECRET_KEY = 'choose one'
   # This is used to encrypt the admin passwords
   PI_PEPPER = "choose one"
   # This is used to encrypt the token data and token passwords
   PI_ENCFILE = '/etc/privacyidea/enckey'
   # This is used to sign the audit log
   PI_AUDIT_KEY_PRIVATE = '/etc/privacyidea/private.pem'
   PI_AUDIT_KEY_PUBLIC = '/etc/privacyidea/public.pem'
   PI_LOGFILE = '/var/log/privacyidea/privacyidea.log'
   #CRITICAL = 50
   #ERROR = 40
   #WARNING = 30
   #INFO = 20
   #DEBUG = 10
   PI_LOGLEVEL = 20

You need to create the above mentioned logging directory
``/var/log/privacyidea``.

You need to create the above mentioned database with the
corresponding user access::

   mysql -u root -p -e "create database pi"
   mysql -u root -p -e "grant all privileges on pi.* to 'pi'@'localhost' \
   identified by 'password'"

With this config file in place you can create the database tables, the
encryption key and the audit keys::

   pi-manage.py createdb
   pi-manage.py create_enckey
   pi-manage.py create_audit_keys

Now you can create the first administrator::

   pi-manage.py admin add administrator email@domain.tld

The system is set up. You now only need to configure the Apache2 webserver.

The Apache2 needs a wsgi script that could be located at
``/etc/privacyidea/piapp.wsgi`` and look like this::

   import sys
   sys.stdout = sys.stderr
   from privacyidea.app import create_app
   # Now we can select the config file:
   application = create_app(config_name="production", \
   config_file="/etc/privacyidea/pi.cfg")

Finally you need to create a Apache2 configuration
``/etc/apache2/sites-available/privacyidea.conf`` which might look like this::

   WSGIPythonHome /opt/privacyidea/privacyidea-venv
   <VirtualHost _default_:443>
	ServerAdmin webmaster@localhost
	# You might want to change this
	ServerName localhost

	DocumentRoot /var/www
	<Directory />
		# For Apache 2.4 you need to set this:
		# Require all granted
		Options FollowSymLinks
		AllowOverride None
	</Directory>

	# We can run several instances on different paths with different configurations
	WSGIScriptAlias /      /etc/privacyidea/piapp.wsgi
	#
	# The daemon is running as user 'privacyidea'
	# This user should have access to the encKey database encryption file
	WSGIDaemonProcess privacyidea processes=1 threads=15 display-name=%{GROUP} user=privacyidea
	WSGIProcessGroup privacyidea
	WSGIPassAuthorization On

	ErrorLog /var/log/apache2/error.log

	LogLevel warn
	LogFormat "%h %l %u %t %>s \"%m %U %H\"  %b \"%{Referer}i\" \"%{User-agent}i\"" privacyIDEA
	CustomLog /var/log/apache2/ssl_access.log privacyIDEA

	#   SSL Engine Switch:
	#   Enable/Disable SSL for this virtual host.
	SSLEngine on

	#   If both key and certificate are stored in the same file, only the
	#   SSLCertificateFile directive is needed.
	SSLCertificateFile    /etc/ssl/certs/privacyideaserver.pem
	SSLCertificateKeyFile /etc/ssl/private/privacyideaserver.key

	<FilesMatch "\.(cgi|shtml|phtml|php)$">
		SSLOptions +StdEnvVars
	</FilesMatch>
	<Directory /usr/lib/cgi-bin>
		SSLOptions +StdEnvVars
	</Directory>
	BrowserMatch ".*MSIE.*" \
		nokeepalive ssl-unclean-shutdown \
		downgrade-1.0 force-response-1.0

   </VirtualHost>

The configuration assumes, a user ``privacyidea``, which you need to create::

   useradd -r -m privacyidea

The files in ``/etc/privacyidea`` and the logfiles in
``/var/log/privacyidea/`` should be restricted to this user.

.. rubric:: Footnotes

.. [#ppa] https://launchpad.net/~privacyidea
.. [#simpleSAML]  https://github.com/privacyidea/privacyidea/tree/master/authmodules/simpleSAMLphp
