.. _wsgiscript:
.. index:: wsgi

The WSGI Script
===============

Apache2 and Nginx are using a WSGI script to start the application.

This script is usually located at ``/etc/privacyidea/privacyideaapp.py`` or
``/etc/privacyidea/privacyideaapp.wsgi`` and has the following contents:

.. literalinclude:: ../../../deploy/apache/privacyideaapp.wsgi
    :language: python

In the ``create_app``-call you can also select another config file.

.. index:: wsgi

WSGI configuration for the Apache webserver
-------------------------------------------

The site-configuration for the Apache webserver to use WSGI should contain at
least::

  <VirtualHost _default_:443>
      ...
      WSGIScriptAlias /      /etc/privacyidea/privacyideaapp.wsgi
      WSGIDaemonProcess privacyidea processes=1 threads=15 display-name=%{GROUP} user=privacyidea
      WSGIProcessGroup privacyidea
      WSGIApplicationGroup %{GLOBAL}
      WSGIPassAuthorization On
      ...
  </VirtualHost>


.. index:: instances

Running several instances with the Apache webserver
---------------------------------------------------

You can run several instances of privacyIDEA on one Apache2 server by defining
several `WSGIScriptAlias` definitions pointing to different wsgi-scripts,
which again reference different config files with different database definitions.

To run further Apache instances add additional lines in your Apache config::

    WSGIScriptAlias /instance1 /etc/privacyidea1/privacyideaapp.wsgi
    WSGIScriptAlias /instance2 /etc/privacyidea2/privacyideaapp.wsgi
    WSGIScriptAlias /instance3 /etc/privacyidea3/privacyideaapp.wsgi
    WSGIScriptAlias /instance4 /etc/privacyidea4/privacyideaapp.wsgi

It is a good idea to create a subdirectory in */etc* for each instance.
Each wsgi script needs to point to the corresponding config file *pi.cfg*.

Each config file can define its own

 * database
 * encryption key
 * signing key
 * logging configuration
 * ...

To create the new database you need :ref:`pimanage`. The *pi-manage* command
reads the configuration from */etc/privacyidea/pi.cfg* by default.

If you want to use another instance with another config file, you need to set
an environment variable and create the database like this::

   PRIVACYIDEA_CONFIGFILE=/etc/privacyidea3/pi.cfg pi-manage create_tables

This way you can use *pi-manage* for each instance.
