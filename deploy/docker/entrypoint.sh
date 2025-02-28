#!/bin/sh
set -e

PI_UPDATE="${PI_UPDATE:-false}"
PI_PORT="${PI_PORT:-8080}"
PI_LOGLEVEL="${PI_LOGLEVEL:-INFO}"

# Database needs a second
echo "waiting for database "
sleep 5

export PATH="/privacyidea/venv/bin:$PATH"

# Activate virtual environment
source activate

# create enckey
if [ ! -s /privacyidea/etc/persistent/enckey ]
then
	echo "### Create enckey ###"
	if [ $PI_ENCKEY ] && [ ! -f /privacyidea/etc/persistent/enckey ]
	then
	    echo "### Use PI_ENCKEY ###"
		echo "$PI_ENCKEY" | base64 -d > /privacyidea/etc/persistent/enckey
		chmod 400 /privacyidea/etc/persistent/enckey
	else
		echo "### Use pi-manage ###"
		pi-manage setup create_enckey
	fi
fi

# bootstrap database
if [ -f /privacyidea/etc/persistent/enckey ] && [ ! -f /privacyidea/etc/persistent/dbcreated ]
then
	echo "### Creating database tables ###"
	pi-manage setup create_tables || exit 1
	touch /privacyidea/etc/persistent/dbcreated
	echo "### Stamp database ###"
	pi-manage db stamp head -d /privacyidea/lib/privacyidea/migrations/
	echo "### Create initial admin user ###"
	pi-manage admin add --password ${PI_ADMIN_PASS:-admin} ${PI_ADMIN:-admin}
fi

# create audit keys if not exists
if [ ! -f /privacyidea/etc/persistent/private.pem ]
then 
	echo "### Create audit keys ###"
	pi-manage setup create_audit_keys
fi

# run DB schema update if requested
if [ "$1" == "PI_UPDATE" ]
then
    echo "### RUNNING DB-SCHEMA UPDATE ###"
	privacyidea-schema-upgrade /privacyidea/lib/privacyidea/migrations/
fi

# Run the app using gunicorn WSGI HTTP server
exec python -m gunicorn -w 4 -b 0.0.0.0:${PI_PORT} "privacyidea.app:create_app(config_name='production')"
