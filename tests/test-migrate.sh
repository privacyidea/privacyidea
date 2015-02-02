#!/bin/bash
cp tests/token-version-1.5.sqlite data.sqlite
./manage.py db upgrade
./manage.py addadmin -p test admin@cornelinux.de admin
./manage.py runserver
