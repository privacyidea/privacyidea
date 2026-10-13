.. index:: wsgi

.. _wsgiscript:

The WSGI Script
===============

A WSGI server, e.g. Apache2 with ``mod_wsgi``, uWSGI or gunicorn, uses a WSGI
script to start the application. nginx is no WSGI server; it forwards the
requests to one of them.

This script is usually located at ``/etc/privacyidea/privacyideaapp.py`` or
``/etc/privacyidea/privacyideaapp.wsgi`` and has the following contents:

.. code-block:: python

    import sys
    sys.stdout = sys.stderr
    from privacyidea.app import create_app
    # Now we can select the config file:
    application = create_app(config_name="production", config_file="/etc/privacyidea/pi.cfg")

In the ``create_app``-call you can also select another config file. The
environment variables ``PRIVACYIDEA_CONFIGFILE`` and ``PI_CONFIG_NAME`` take
precedence over ``config_file`` and ``config_name`` if they are set in the
environment of the web server process (e.g. with ``Environment=`` in a systemd
unit), so do not set them there when you run several instances. Variables set
with Apache's ``SetEnv`` only reach the requests and have no effect here.

WSGI configuration for the Apache webserver
-------------------------------------------

The site-configuration for the Apache webserver to use WSGI should contain at
least::

  <VirtualHost _default_:443>
      ...
      WSGIScriptAlias /      /etc/privacyidea/privacyideaapp.wsgi
      WSGIDaemonProcess privacyidea processes=1 threads=15 display-name=%{GROUP} user=privacyidea python-home=/opt/privacyidea
      WSGIProcessGroup privacyidea
      WSGIApplicationGroup %{GLOBAL}
      WSGIPassAuthorization On
      ...
  </VirtualHost>

``python-home`` points to the virtual environment privacyIDEA is installed in
(see :ref:`pip_install`). The virtual environment must be created from the same
Python installation that mod_wsgi is built for.


.. index:: instances

Running several instances with the Apache webserver
---------------------------------------------------

You can run several instances of privacyIDEA on one Apache2 server by defining
several ``WSGIScriptAlias`` definitions pointing to different wsgi-scripts,
which again reference different config files with different database definitions.

Each instance must run in a daemon process of its own. Instances in the same
process share the process-wide state: all of them log to the logging
configuration of the instance loaded last, and all of them write their metrics
to the database of the instance that records the first metric. So define one
``WSGIDaemonProcess`` per instance and select it on the ``WSGIScriptAlias``,
instead of the ``WSGIProcessGroup`` and ``WSGIApplicationGroup`` lines of the
single-instance configuration above::

    WSGIDaemonProcess pi1 processes=1 threads=15 display-name=%{GROUP} user=privacyidea python-home=/opt/privacyidea
    WSGIScriptAlias /instance1 /etc/privacyidea1/privacyideaapp.wsgi process-group=pi1 application-group=%{GLOBAL}
    WSGIDaemonProcess pi2 processes=1 threads=15 display-name=%{GROUP} user=privacyidea python-home=/opt/privacyidea
    WSGIScriptAlias /instance2 /etc/privacyidea2/privacyideaapp.wsgi process-group=pi2 application-group=%{GLOBAL}
    WSGIPassAuthorization On

Separate application groups in one daemon process are no alternative: the
``cryptography`` package can only be loaded into one Python interpreter per
process.

It is a good idea to create a subdirectory in */etc* for each instance.
Each wsgi script needs to point to the corresponding config file *pi.cfg*.

Each config file can define its own

 * database
 * encryption key
 * signing key
 * logging configuration
 * ...

To create the new database you need :ref:`the pi-manage command <pimanage>`.
The command reads the configuration from */etc/privacyidea/pi.cfg* by default.

If you want to use another instance with another config file, you need to set
an environment variable and create the database like this::

   PRIVACYIDEA_CONFIGFILE=/etc/privacyidea3/pi.cfg pi-manage setup create_tables

This way you can use *pi-manage* for each instance.
