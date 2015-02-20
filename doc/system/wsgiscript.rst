.. _wsgiscript:

The WSGI Script
===============

Apache2 and Nginx are using a WSGI script to start the application.

This script is usually located at ``/etc/privacyidea/privacyideaapp.py`` or
``/etc/privacyidea/privacyideaapp.wsgi`` and has the following contents::

   import sys
   sys.stdout = sys.stderr
   from privacyidea.app import create_app
   # Now we can select the config file:
   application = create_app(config_name="production",
                            config_file="/etc/privacyidea/pi.cfg")

In the ``create_app``-call you can also select another config file.

.. note:: This way you can run several instances of privacyIDEA in one
   Apache2 server by defining several WSGIScriptAlias definitions pointing to
   different wsgi-scripts, that again reference different config files with
   different database definitions.


