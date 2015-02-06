__doc__ = """
These are the base functions of privacyIDEA app.

app.py
======

contains the constructor of the app. Call

   create_app(config_name, config_file)

to create a new app instance.

config.py
=========
contains configuration objects for development, testing and production.
These configuration probably will not be enough for you, this is why you will
need to add configuration in a config file. You pass the config file to the
create_app() call.

models.py
=========
contains the database models of privacyidea.


Directory structure
===================
The directory /lib/ contains all library functions. These functions are
independent on any request objects and flask components.

The /api/ directory contains the flasked based REST API of privacyidea.

The /static/ and /webui/ directories contain all components that are needed
for the WebUI which is implemented as a single page application using angularJS.
"""
