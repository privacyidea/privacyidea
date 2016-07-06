
.. _install_wheezy:

Debian Packages
---------------

Wheezy
~~~~~~

You can install privacyIDEA on Debian Wheezy either via the
:ref:`pip_install` or with a ready made Wheezy package.

The available Wheezy package privacyidea-venv_2.1~dev0_amd64.deb contains a
complete virtual environment with all necessary dependent modules. To install
it run::

   dpkg -i privacyidea-venv_2.1~dev0_amd64.deb

This will install privacyIDEA into a virtual environment at
``/opt/privacyidea/privacyidea-venv``.

You can enter the virtual environment by::

   source /opt/privacyidea/privacyidea-venv/bin/activate

Jessie
~~~~~~

At the moment you can use the Ubuntu Trusty packages with Debian Jessie.

Thus you can create a file ``/etc/apt/sources.list.d/privacyidea.list`` with
the content::

   deb http://ppa.launchpad.net/privacyidea/privacyidea/ubuntu trusty main

Add the GPG key to the keyring::

   gpg --keyserver keyserver.ubuntu.com --recv-keys C24DCF7D
   gpg --armor --export C24DCF7D | apt-key add -

Now run::

   apt-get update
   apt-get install privacyidea-apache2

As an alternative you can find a complete guideline how to setup privacyIDEA
including RADIUS here [#jessieHowto]_.


Running privacyIDEA with Apache2 and MySQL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you installed via pip or the Wheezy package
you need to create and fill the config directory ``/etc/privacyidea`` manually::

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

   pi-manage createdb
   pi-manage create_enckey
   pi-manage create_audit_keys

Now you can create the first administrator::

   pi-manage admin add administrator

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
.. [#simpleSAML] https://github.com/privacyidea/privacyidea/tree/master/authmodules/simpleSAMLphp
.. [#jessieHowto] http://www.routerperformance.net/howtos/install-privacyidea-2-13-on-a-clean-debian-8-jessie/
