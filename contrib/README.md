This folder contains the build environment for python modules that are not
shipped with Ubuntu 14.04LTS or 16.04LTS.

Building ldap3
==============

To build for trusty:

   make ldap3 series=trusty

Upload:

   make ppa-dev series=trusty


To build for xenial:

   make ldap3 series=xenial

Upload:

   make ppa-dev series=xenial
