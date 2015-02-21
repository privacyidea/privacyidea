This directory contains config information for building packages for different
deployment strategies.

debian
======
This directory contains the privacyidea config file that is used when
deploying privacyidea-nginx or privacyidea-apache2.

debian-ubuntu
=============

To deploy on Ubuntu normal packages are built via "make builddeb".
This directory contains the /debian/ directory to build all packages, which
will be installed into the system.

debian-virtualenv
=================

To deploy on Wheezy one package is built, that installs a virtualenv to
/opt/privacyidea.
This directory contains the /debian/ directory to build this virtualenv package.

apache
======
This directory contains the config files for deploying privacyidea-apache.deb

nginx + uwsgi
=============
These directories contain the config files for deploying privacyidea-nginx.deb

privacyidea
===========
This directory contains some config examples to be deployed from setup.py
into the python package.
