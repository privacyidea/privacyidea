privacyIDEA and Docker
======================

We provide a Dockerfile to create a simple privacyIDEA docker container which
currently only contains the runnable code with the gunicorn WSGI server.

> **_NOTE:_**  This is currently very much work-in-progress so expect breaking changes!

Build the container image with:
```
docker build . -f deploy/docker/Dockerfile -t <pi-tag>
```

Run the container with:
```
docker run -p 8080:8080 <pi-tag>:latest
```

A volume is automatically created and mounted at `/etc/privacyidea` in the
container. An existing volume can be given at the container start with:
```
docker run -v <volume-id>:/etc/privacyidea -p 8080:8080 <pi-tag>:latest
```
Some configuration data is required and will be checked at the application start.
The data can be passed to the container through environment files and/or secrets.

Some additional configuration data can be set at `/etc/privacyidea` for this
container. See  https://privacyidea.readthedocs.io/en/latest/installation/pip.html#database
and https://privacyidea.readthedocs.io/en/latest/installation/system/inifile.html#cfgfile
for configuration options.

Configuration options can be given as environment variables with the `PRIVACYIDEA_` prefix like:
```
docker run -p 8080:8080 -e PRIVACYIDEA_PI_PEPPER="Never know..." -e PRIVACYIDEA_PI_SECRET="t0p s3cr3t" <pi-tag>:latest
```

Docker compose
--------------

A compose file can be used to start up the complete stack. An example is given
in `deploy/docker/compose.yaml`:
```
SECRET_KEY=$SECRET_KEY PI_PEPPER=$PI_PEPPER docker compose -f deploy/docker/compose.yaml up
```

Setup privacyIDEA
-----------------

Commands can be run inside the container with:
```
docker exec -i <container name> pi-manage ...
```

To set up a running container use:
```
docker exec -i <privacyidea-container> pi-manage setup create_tables
```

Configuration can be imported in the container with:
```
cat <policy template yaml> | docker exec -i <container name> pi-manage config import
```

TODO:
-----
* Add a reverse proxy service (https://github.com/docker/awesome-compose/blob/master/nginx-flask-mysql/compose.yaml)
* Add an example for a `configs` element to the `compose.yaml` (https://docs.docker.com/reference/compose-file/services/#configs)
* Add an example on how to manually mount the secret file into the container using `docker run`
* Add dependencies in the container (PyKCS11, gssapi)
* Extra build step for the new WebUI
* Add recurring tasks runner (cron? via docker? via redis?)
