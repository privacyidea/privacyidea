.. _installation:

Installation
============

The ways described here to install privacyIDEA are

 * the installation via the :ref:`pip_install`, which can be used on
   any Linux distribution,
 * ready-made :ref:`install_ubuntu` for Ubuntu 22.04 LTS, 24.04 LTS and 26.04 LTS,
 * the :ref:`installation on RHEL 8, 9 and 10 <install_rhel>` and
 * the container deployment with :ref:`install_docker`.

If you want to upgrade please read :ref:`upgrade`.


.. toctree::
   :maxdepth: 1

   pip
   ubuntu
   centos
   upgrade
   system/inifile
   system/logging
   system/wsgiscript
   system/pi-manage
   system/cleanupjobs
   system/securitymodule

After installation you might want to take a look at :ref:`first_steps`.

.. _install_docker:

Docker
------

The source tree contains a Dockerfile and a Docker Compose setup for a
single-node container deployment: one MariaDB and three services built from the
same privacyIDEA image, which initialize the database, serve the requests and
run the scheduled jobs. The setup is described in
`deploy/docker/README.Docker.md
<https://github.com/privacyidea/privacyidea/blob/master/deploy/docker/README.Docker.md>`_.
