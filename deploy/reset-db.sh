#!/bin/bash
heroku pg:reset DATABASE_URL --app privacyidea-test
heroku run python ./pi-manage.py createdb --app privacyidea-test
heroku run --app privacyidea-test --  python ./pi-manage.py admin add -p 'Test1234!' admin admin@localhost
heroku run --app privacyidea-test -- python ./pi-manage.py resolver create resolver1 passwdresolver deploy/heroku/default-resolver
heroku run --app privacyidea-test -- python ./pi-manage.py realm create default resolver1
