This directory contains deployment files that are consumed from within this
repository.

Note that the Debian/Ubuntu packages are *not* built from here. The packaging
sources, and the webserver, uWSGI, cron and `pi.cfg` templates that the
`privacyidea-apache2` / `privacyidea-nginx` packages install, live in their own
repository: https://github.com/NetKnights-GmbH/ubuntu

docker
======
Dockerfile, Compose setup and helper scripts for the single-node container
deployment. See `docker/README.Docker.md`. Built and smoke-tested by the
`docker-build` GitHub workflow.

privacyidea
===========
RADIUS dictionaries and the `NetKnights.pem` subscription certificate. Copied
into `/etc/privacyidea/` by the Dockerfile; the dictionaries are also used by
the test suite.

dev
===
Fixtures for the local development stack, e.g. the LDAP seed data mounted by
`compose-dev.yml`.
