#!/bin/bash
heroku pg:reset DATABASE_URL --app privacyidea-test
heroku run python ./pi-manage create_tables --app privacyidea-test
heroku run --app privacyidea-test --  python ./pi-manage admin add -p 'Test1234!' admin admin@localhost
heroku run --app privacyidea-test -- python ./pi-manage resolver create resolver1 passwdresolver deploy/heroku/default-resolver
heroku run --app privacyidea-test -- python ./pi-manage realm create default resolver1
